import csv
import io
import json

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import is_super_admin, require_roles
from app.models.institution import Institution
from app.models.user import User
from app.services.compliance_analysis import analyze_institution_compliance

router = APIRouter(prefix="/compliance", tags=["Compliance Analysis"])


def _institution_scope(
    db: Session,
    current_user: User,
    requested_institution_id: int | None,
) -> int:
    if is_super_admin(current_user):
        institution_id = requested_institution_id
    else:
        institution_id = current_user.institution_id
        if requested_institution_id is not None and requested_institution_id != institution_id:
            raise HTTPException(status_code=403, detail="Cross-institution analysis is not permitted")
    if institution_id is None:
        raise HTTPException(status_code=422, detail="institution_id is required")
    if not db.query(Institution.id).filter(Institution.id == institution_id).first():
        raise HTTPException(status_code=404, detail="Institution not found")
    return institution_id


@router.get("/analysis")
def institution_analysis(
    institution_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles("university_admin", "registrar", "compliance_officer", "super_admin")
    ),
):
    scope_id = _institution_scope(db, current_user, institution_id)
    return analyze_institution_compliance(db, scope_id)


@router.get("/analysis.csv")
def download_institution_analysis(
    institution_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles("university_admin", "registrar", "compliance_officer", "super_admin")
    ),
):
    scope_id = _institution_scope(db, current_user, institution_id)
    report = analyze_institution_compliance(db, scope_id)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["institution_id", report["institution_id"]])
    writer.writerow(["as_of", report["as_of"]])
    writer.writerow(["analysis_method", report["analysis_method"]])
    writer.writerow([])
    writer.writerow(["finding_type", "details"])
    for finding_type, records in report["findings"].items():
        for record in records:
            writer.writerow([finding_type, json.dumps(record, sort_keys=True)])
    writer.writerow([])
    writer.writerow(["recommendation"])
    writer.writerows([[recommendation] for recommendation in report["recommendations"]])
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="adcs-compliance-{scope_id}.csv"',
            "Cache-Control": "private, no-store",
        },
    )
