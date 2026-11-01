from typing import Dict, List, Any, Optional
from datetime import date
from sqlalchemy.orm import Session

from app.models.student import Student
from app.models.academic import AttendanceRecord, AssessmentRecord
from app.models.compliance import ComplianceRule
from app.core.enums import RiskLevel


class RiskEngine:
    def __init__(self, institution_id: int, db: Session):
        self.institution_id = institution_id
        self.db = db
        self.rules = db.query(ComplianceRule).filter(
            ComplianceRule.institution_id == institution_id, ComplianceRule.is_active == True).all()

    def _rule_threshold(self, rule_type: str, default: float) -> float:
        for r in self.rules:
            if r.rule_type == rule_type and r.threshold_value is not None:
                return float(r.threshold_value)
        return default

    def _weight(self, rule_type: str, default: float = 1.0) -> float:
        for r in self.rules:
            if r.rule_type == rule_type:
                return float(r.weight or 1.0)
        return default

    def assess(self, student: Student) -> Dict[str, Any]:
        factors: List[Dict[str, Any]] = []
        score = 0.0

        attendance_rate = self._attendance_rate(student.id)
        attendance_threshold = self._rule_threshold("attendance", 75.0)
        att_weight = self._weight("attendance", 2.0)
        if attendance_rate is not None:
            if attendance_rate < attendance_threshold:
                deficit = attendance_threshold - attendance_rate
                contribution = min(deficit * att_weight, 40.0)
                score += contribution
                factors.append({"factor": "Attendance below threshold", "value": round(attendance_rate, 2),
                                "threshold": attendance_threshold, "weight": att_weight,
                                "contribution": round(contribution, 2),
                                "explanation": f"Attendance {attendance_rate:.1f}% below required {attendance_threshold:.1f}%."})
            else:
                factors.append({"factor": "Attendance satisfactory", "value": round(attendance_rate, 2),
                                "threshold": attendance_threshold, "weight": att_weight, "contribution": 0.0,
                                "explanation": "Attendance meets institutional requirement."})

        missed = self._missed_assessments(student.id)
        missed_threshold = int(self._rule_threshold("assessment", 2))
        asm_weight = self._weight("assessment", 5.0)
        if missed > 0:
            contribution = min(missed * asm_weight, 30.0)
            score += contribution
            factors.append({"factor": "Missed assessments", "value": missed, "threshold": missed_threshold,
                            "weight": asm_weight, "contribution": round(contribution, 2),
                            "explanation": f"{missed} missed/unsubmitted assessment(s)."})

        if student.gpa is not None:
            gpa_threshold = self._rule_threshold("gpa", 2.0)
            gpa_weight = self._weight("gpa", 8.0)
            if student.gpa < gpa_threshold:
                deficit = gpa_threshold - student.gpa
                contribution = min(deficit * gpa_weight, 20.0)
                score += contribution
                factors.append({"factor": "Academic performance concern", "value": round(student.gpa, 2),
                                "threshold": gpa_threshold, "weight": gpa_weight, "contribution": round(contribution, 2),
                                "explanation": f"GPA {student.gpa:.2f} below threshold {gpa_threshold:.2f}."})

        open_cases = self._open_cases(student.id)
        case_weight = self._weight("compliance_case", 10.0)
        if open_cases > 0:
            contribution = min(open_cases * case_weight, 20.0)
            score += contribution
            factors.append({"factor": "Open compliance cases", "value": open_cases, "threshold": 0,
                            "weight": case_weight, "contribution": round(contribution, 2),
                            "explanation": f"{open_cases} open compliance case(s)."})

        score = round(min(score, 100.0), 2)
        risk_level = self._classify(score)
        recommendations = self._recommendations(risk_level, factors)

        return {
            "risk_score": score,
            "risk_level": risk_level,
            "factors": factors,
            "recommendations": recommendations,
            "attendance_rate": round(attendance_rate, 2) if attendance_rate is not None else None,
            "missed_assessments": missed,
            "threshold_snapshot": {"attendance": attendance_threshold, "missed_assessments": missed_threshold},
        }
    def _classify(self, score: float) -> str:
        if score >= 60:
            return RiskLevel.HIGH.value
        if score >= 30:
            return RiskLevel.MODERATE.value
        return RiskLevel.LOW.value

    def _recommendations(self, level: str, factors: List[Dict[str, Any]]) -> List[str]:
        recs = []
        if level == RiskLevel.HIGH.value:
            recs.append("Schedule an academic advising meeting within one week.")
            recs.append("Provide a structured study plan and attendance contract.")
        elif level == RiskLevel.MODERATE.value:
            recs.append("Send a supportive early-warning notification to the student.")
            recs.append("Monitor attendance and assessment submission weekly.")
        else:
            recs.append("Continue routine monitoring; no immediate intervention required.")
        for f in factors:
            if "Attendance" in f.get("factor", "") and f.get("contribution", 0) > 0:
                recs.append("Encourage improved class attendance; review timetable conflicts.")
            if "missed" in f.get("factor", "").lower():
                recs.append("Offer assessment support / extension guidance where policy permits.")
        seen = set(); out = []
        for r in recs:
            if r not in seen:
                seen.add(r); out.append(r)
        return out

    def _attendance_rate(self, student_id: int) -> Optional[float]:
        records = self.db.query(AttendanceRecord).filter(AttendanceRecord.student_id == student_id).all()
        if not records:
            return None
        present = sum(1 for r in records if r.status in ("present", "late", "excused"))
        return (present / len(records)) * 100.0

    def _missed_assessments(self, student_id: int) -> int:
        return self.db.query(AssessmentRecord).filter(
            AssessmentRecord.student_id == student_id,
            AssessmentRecord.submitted.is_(False),
            AssessmentRecord.due_date.is_not(None),
            AssessmentRecord.due_date < date.today(),
        ).count()

    def _open_cases(self, student_id: int) -> int:
        from app.models.compliance_case import ComplianceCase
        return self.db.query(ComplianceCase).filter(
            ComplianceCase.student_id == student_id,
            ComplianceCase.status.notin_(["resolved", "closed"])).count()
