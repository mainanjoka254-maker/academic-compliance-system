import uuid
from datetime import date, timedelta

from app.core.security import get_current_user, hash_password
from app.main import app
from app.models.academic import AssessmentRecord, Course
from app.models.institution import Institution
from app.models.role import Role
from app.models.student import Lecturer, Student
from app.models.user import User


def _role(db, name):
    role = db.query(Role).filter(Role.name == name).first()
    if role is None:
        role = Role(name=name, description=name, is_system=True)
        db.add(role)
        db.flush()
    return role


def _institution(db):
    suffix = uuid.uuid4().hex[:8]
    institution = Institution(name=f"Analysis {suffix}", code=f"A{suffix}")
    db.add(institution)
    db.commit()
    db.refresh(institution)
    return institution


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


def test_compliance_analysis_uses_institution_records_and_exports_csv(client, db):
    institution = _institution(db)
    officer = _user(db, institution, "compliance_officer")
    student_user = _user(db, institution, "student")
    student = Student(
        user_id=student_user.id,
        institution_id=institution.id,
        student_number=f"STU-{student_user.id}",
        status="active",
    )
    db.add(student)
    db.flush()
    lecturer_user = User(
        email=f"lecturer-{uuid.uuid4().hex[:8]}@test.com",
        full_name="Assigned Lecturer",
        institution_id=institution.id,
        is_active=True,
        is_verified=True,
    )
    db.add(lecturer_user)
    db.flush()
    lecturer = Lecturer(
        institution_id=institution.id,
        user_id=lecturer_user.id,
        staff_number=f"STAFF-{uuid.uuid4().hex[:6]}",
    )
    db.add(lecturer)
    db.flush()
    course = Course(
        institution_id=institution.id,
        code=f"COURSE-{uuid.uuid4().hex[:6]}",
        name="Compliance testing",
        lecturer_id=lecturer.id,
        is_active=True,
    )
    db.add(course)
    db.flush()
    db.add_all(
        [
            AssessmentRecord(
                institution_id=institution.id,
                student_id=student.id,
                course_id=course.id,
                title="Past due work",
                submitted=False,
                due_date=date.today() - timedelta(days=1),
            ),
            AssessmentRecord(
                institution_id=institution.id,
                student_id=student.id,
                course_id=course.id,
                title="Upcoming work",
                submitted=False,
                due_date=date.today() + timedelta(days=7),
            ),
        ]
    )
    db.commit()

    app.dependency_overrides[get_current_user] = lambda: officer
    try:
        report_response = client.get("/api/v1/compliance/analysis")
        csv_response = client.get("/api/v1/compliance/analysis.csv")
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert report_response.status_code == 200
    report = report_response.json()
    assert report["analysis_method"] == "deterministic_rules"
    assert report["summary"]["students_without_documents"] == 1
    assert report["summary"]["incomplete_assessments"] == 2
    assert report["summary"]["overdue_assessments"] == 1
    assert report["summary"]["upcoming_assessments"] == 1
    assert report["summary"]["courses_without_lecturer_submissions"] == 1
    assert report["findings"]["incomplete_assessments"][0]["status"] == "overdue"
    assert csv_response.status_code == 200
    assert csv_response.headers["content-type"].startswith("text/csv")
    assert "Past due work" in csv_response.text


def test_compliance_analysis_enforces_role_and_institution_scope(client, db):
    institution = _institution(db)
    another_institution = _institution(db)
    registrar = _user(db, institution, "registrar")
    student = _user(db, institution, "student")

    app.dependency_overrides[get_current_user] = lambda: registrar
    try:
        cross_tenant = client.get(
            "/api/v1/compliance/analysis",
            params={"institution_id": another_institution.id},
        )
    finally:
        app.dependency_overrides.pop(get_current_user, None)
    assert cross_tenant.status_code == 403

    app.dependency_overrides[get_current_user] = lambda: student
    try:
        forbidden = client.get("/api/v1/compliance/analysis")
    finally:
        app.dependency_overrides.pop(get_current_user, None)
    assert forbidden.status_code == 403
