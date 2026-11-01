import uuid

from app.core.security import hash_password
from app.core.security import get_current_user
from app.main import app
from app.models.academic import Course, CourseEnrollment
from app.models.compliance import ComplianceIncident
from app.models.compliance_case import ComplianceCase
from app.models.institution import Institution
from app.models.risk import RiskAlert, RiskAssessment
from app.models.role import Role
from app.models.student import Student
from app.models.user import User


def _role(db, name):
    role = db.query(Role).filter(Role.name == name).first()
    if role is None:
        role = Role(name=name, description=name, is_system=True)
        db.add(role)
        db.flush()
    return role


def _user(db, institution, role_name):
    user = User(
        email=f"{role_name}-{uuid.uuid4().hex[:8]}@test.com",
        hashed_password=hash_password("test-password"),
        full_name=f"Test {role_name}",
        institution_id=institution.id,
        is_active=True,
        is_verified=True,
    )
    user.roles.append(_role(db, role_name))
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _institution(db):
    suffix = uuid.uuid4().hex[:8]
    institution = Institution(name=f"Audit {suffix}", code=f"A{suffix}")
    db.add(institution)
    db.commit()
    db.refresh(institution)
    return institution


def test_student_cannot_read_other_students_cases_or_risk(client, db):
    institution = _institution(db)
    student_a = _user(db, institution, "student")
    student_b = _user(db, institution, "student")
    profile_a = Student(user_id=student_a.id, institution_id=institution.id, student_number=f"A{student_a.id}")
    profile_b = Student(user_id=student_b.id, institution_id=institution.id, student_number=f"B{student_b.id}")
    db.add_all([profile_a, profile_b])
    db.commit()
    db.refresh(profile_a)
    db.refresh(profile_b)

    case = ComplianceCase(
        institution_id=institution.id,
        student_id=profile_b.id,
        case_number=f"CASE-{uuid.uuid4().hex[:8]}",
        title="Private case",
    )
    assessment = RiskAssessment(
        institution_id=institution.id,
        student_id=profile_b.id,
        risk_score=65,
        risk_level="high",
        factors=[],
        recommendations=[],
    )
    db.add_all([case, assessment])
    db.commit()
    db.refresh(case)
    alert = RiskAlert(
        institution_id=institution.id,
        student_id=profile_b.id,
        risk_assessment_id=assessment.id,
        level="high",
        message="Private risk alert",
    )
    db.add(alert)
    db.commit()

    app.dependency_overrides[get_current_user] = lambda: student_a
    try:
        cases = client.get("/api/v1/compliance/cases")
        case_detail = client.get(f"/api/v1/compliance/cases/{case.id}")
        risk_detail = client.get(f"/api/v1/risk/assessments/{profile_b.id}")
        alerts = client.get("/api/v1/risk/alerts")
        read_alert = client.patch(f"/api/v1/risk/alerts/{alert.id}/read")
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert cases.status_code == 200 and cases.json() == []
    assert case_detail.status_code == 404
    assert risk_detail.status_code == 403
    assert alerts.status_code == 200 and alerts.json() == []
    assert read_alert.status_code == 403


def test_student_and_lecturer_incident_creation_is_scoped(client, db):
    institution = _institution(db)
    student = _user(db, institution, "student")
    other_student = _user(db, institution, "student")
    student_profile = Student(
        user_id=student.id,
        institution_id=institution.id,
        student_number=f"STU-{student.id}",
    )
    other_profile = Student(
        user_id=other_student.id,
        institution_id=institution.id,
        student_number=f"STU-{other_student.id}",
    )
    db.add_all([student_profile, other_profile])
    db.commit()

    app.dependency_overrides[get_current_user] = lambda: student
    try:
        forbidden = client.post(
            "/api/v1/compliance/incidents",
            json={
                "student_id": other_profile.id,
                "incident_type": "attendance",
                "title": "Arbitrary student report",
            },
        )
    finally:
        app.dependency_overrides.pop(get_current_user, None)
    assert forbidden.status_code == 403
    assert db.query(ComplianceIncident).count() == 0


def test_students_endpoint_rejects_cross_institution_profile_creation(client, db):
    institution_a = _institution(db)
    institution_b = _institution(db)
    registrar = _user(db, institution_a, "registrar")
    student = _user(db, institution_b, "student")

    app.dependency_overrides[get_current_user] = lambda: registrar
    try:
        response = client.post(
            "/api/v1/students",
            json={
                "user_id": student.id,
                "student_number": f"STU-{student.id}",
            },
        )
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 403
    assert db.query(Student).filter_by(user_id=student.id).count() == 0
