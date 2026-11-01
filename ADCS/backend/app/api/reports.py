from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.deps import require_roles
from app.core.deps import is_super_admin
from app.models.student import Student
from app.models.compliance_case import ComplianceCase
from app.models.risk import RiskAssessment, RiskAlert
from app.models.user import User

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get("/institution-summary")
def institution_summary(db: Session = Depends(get_db), current_user=Depends(require_roles("university_admin", "registrar", "compliance_officer", "super_admin"))):
    inst_id = current_user.institution_id
    if is_super_admin(current_user):
        from app.models.institution import Institution
        return {
            "total_institutions": db.query(Institution).count(),
            "total_students": db.query(Student).count(),
            "total_users": db.query(User).count(),
            "active_cases": db.query(ComplianceCase).filter(ComplianceCase.status.notin_(["resolved", "closed"])).count(),
            "resolved_cases": db.query(ComplianceCase).filter(ComplianceCase.status.in_(["resolved", "closed"])).count(),
            "high_risk_students": db.query(RiskAssessment).filter(RiskAssessment.risk_level == "high").count(),
            "unread_alerts": db.query(RiskAlert).filter(RiskAlert.is_read.is_(False)).count(),
        }
    if inst_id is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="An institution is required")
    return {
        "total_students": db.query(Student).filter(Student.institution_id == inst_id).count(),
        "total_users": db.query(User).filter(User.institution_id == inst_id).count(),
        "active_cases": db.query(ComplianceCase).filter(ComplianceCase.institution_id == inst_id, ComplianceCase.status.notin_(["resolved", "closed"])).count(),
        "resolved_cases": db.query(ComplianceCase).filter(ComplianceCase.institution_id == inst_id, ComplianceCase.status.in_(["resolved", "closed"])).count(),
        "high_risk_students": db.query(RiskAssessment).filter(RiskAssessment.institution_id == inst_id, RiskAssessment.risk_level == "high").count(),
        "unread_alerts": db.query(RiskAlert).filter(RiskAlert.institution_id == inst_id, RiskAlert.is_read == False).count(),
    }


@router.get("/platform-summary")
def platform_summary(db: Session = Depends(get_db), current_user=Depends(require_roles("super_admin"))):
    from app.models.institution import Institution
    return {
        "total_institutions": db.query(Institution).count(),
        "active_institutions": db.query(Institution).filter(Institution.is_active == True).count(),
        "total_users": db.query(User).count(),
    }
