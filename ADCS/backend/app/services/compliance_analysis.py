from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.ai.risk_engine import RiskEngine
from app.models.academic import AssessmentRecord, Course
from app.models.document import AcademicDocument
from app.models.student import Student


def analyze_institution_compliance(
    db: Session,
    institution_id: int,
    as_of: date | None = None,
) -> dict:
    today = as_of or date.today()
    students = db.query(Student).filter(
        Student.institution_id == institution_id,
        Student.status == "active",
    ).order_by(Student.id).all()
    documents = db.query(AcademicDocument).filter(
        AcademicDocument.institution_id == institution_id,
    ).all()
    documented_students = {
        document.student_id
        for document in documents
        if document.student_id is not None and document.purpose == "student_document"
    }
    students_without_documents = [
        {"student_id": student.id, "student_number": student.student_number}
        for student in students
        if student.id not in documented_students
    ]

    assessments = db.query(AssessmentRecord).filter(
        AssessmentRecord.institution_id == institution_id,
        AssessmentRecord.submitted.is_(False),
    ).order_by(AssessmentRecord.due_date, AssessmentRecord.id).all()
    incomplete_assessments = [
        {
            "assessment_id": record.id,
            "student_id": record.student_id,
            "course_id": record.course_id,
            "title": record.title,
            "due_date": record.due_date.isoformat() if record.due_date else None,
            "status": "overdue" if record.due_date and record.due_date < today else "incomplete",
        }
        for record in assessments
    ]
    upcoming_assessments = [
        {
            "assessment_id": record.id,
            "student_id": record.student_id,
            "course_id": record.course_id,
            "title": record.title,
            "due_date": record.due_date.isoformat(),
        }
        for record in db.query(AssessmentRecord).filter(
            AssessmentRecord.institution_id == institution_id,
            AssessmentRecord.submitted.is_(False),
            AssessmentRecord.due_date >= today,
            AssessmentRecord.due_date <= today + timedelta(days=30),
        ).order_by(AssessmentRecord.due_date, AssessmentRecord.id).all()
        if record.due_date is not None
    ]

    courses = db.query(Course).filter(
        Course.institution_id == institution_id,
        Course.is_active.is_(True),
        Course.lecturer_id.is_not(None),
    ).order_by(Course.id).all()
    course_submission_docs = {
        document.course_id
        for document in documents
        if document.course_id is not None and document.purpose == "lecturer_submission"
    }
    courses_without_submissions = [
        {
            "course_id": course.id,
            "course_code": course.code,
            "course_name": course.name,
            "lecturer_id": course.lecturer_id,
        }
        for course in courses
        if course.id not in course_submission_docs
    ]

    engine = RiskEngine(institution_id, db)
    risk_findings = []
    for student in students:
        assessment = engine.assess(student)
        if assessment["risk_level"] in ("moderate", "high"):
            risk_findings.append(
                {
                    "student_id": student.id,
                    "student_number": student.student_number,
                    "risk_level": assessment["risk_level"],
                    "risk_score": assessment["risk_score"],
                    "factors": assessment["factors"],
                    "recommendations": assessment["recommendations"],
                }
            )

    recommendations = []
    if students_without_documents:
        recommendations.append(
            "Request academic-document uploads from the listed students; no required-document checklist is configured."
        )
    if incomplete_assessments:
        recommendations.append(
            "Contact students and course lecturers about incomplete or overdue assessment records."
        )
    if upcoming_assessments:
        recommendations.append(
            "Send reminders for incomplete assessments with due dates in the next 30 days."
        )
    if courses_without_submissions:
        recommendations.append(
            "Ask assigned lecturers to submit a course report for courses without an uploaded lecturer submission."
        )
    recommendations.extend(
        recommendation
        for finding in risk_findings
        for recommendation in finding["recommendations"]
    )
    recommendations = list(dict.fromkeys(recommendations))

    return {
        "institution_id": institution_id,
        "as_of": today.isoformat(),
        "analysis_method": "deterministic_rules",
        "summary": {
            "active_students": len(students),
            "students_without_documents": len(students_without_documents),
            "incomplete_assessments": len(incomplete_assessments),
            "overdue_assessments": sum(item["status"] == "overdue" for item in incomplete_assessments),
            "upcoming_assessments": len(upcoming_assessments),
            "courses_without_lecturer_submissions": len(courses_without_submissions),
            "students_at_elevated_risk": len(risk_findings),
        },
        "findings": {
            "students_without_documents": students_without_documents,
            "incomplete_assessments": incomplete_assessments,
            "upcoming_assessments": upcoming_assessments,
            "courses_without_lecturer_submissions": courses_without_submissions,
            "elevated_risk_students": risk_findings,
        },
        "recommendations": recommendations,
        "limitations": [
            "This report uses institution records and deterministic rules; it does not change official academic results.",
            "Student-document findings mean no document upload is recorded; mandatory document types are not configured.",
            "Lecturer submission findings mean no course report is uploaded; submission deadlines are not configured.",
            "Assessment deadlines are analyzed only when a due date is present in the academic record.",
        ],
    }
