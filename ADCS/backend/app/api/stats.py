from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.student import Student
from app.models.student import Lecturer
from app.models.institution import Institution
from app.models.compliance import ComplianceIncident

router = APIRouter(prefix="/stats", tags=["Stats"])


@router.get("/homepage")
def homepage_stats(db: Session = Depends(get_db)):
    total_students = db.query(Student).count()
    total_lecturers = db.query(Lecturer).count()
    total_institutions = db.query(Institution).filter(Institution.is_active.is_(True)).count()
    incidents = db.query(ComplianceIncident).count()
    compliance_rate = 100.0 if incidents == 0 else max(0.0, 100.0 - incidents)
    return {
        "total_students": total_students,
        "total_lecturers": total_lecturers,
        "total_institutions": total_institutions,
        "compliance_rate": round(compliance_rate, 1),
    }