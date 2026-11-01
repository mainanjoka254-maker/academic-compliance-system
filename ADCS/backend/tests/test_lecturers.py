import uuid

from app.core.security import hash_password
from app.core.security import get_current_user
from app.main import app
from app.models.academic import Course
from app.models.department import Department
from app.models.document import AcademicDocument
from app.models.institution import Institution
from app.models.role import Role
from app.models.student import Lecturer
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
    institution = Institution(name=f"Lecturer {suffix}", code=f"L{suffix}")
    db.add(institution)
    db.commit()
    db.refresh(institution)
    return institution


def _manager(db, institution):
    user = User(
        email=f"admin-{uuid.uuid4().hex[:8]}@test.com",
        hashed_password=hash_password("test-password"),
        full_name="University Manager",
        institution_id=institution.id,
        is_active=True,
        is_verified=True,
    )
    user.roles.append(_role(db, "university_admin"))
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def test_lecturer_registration_assignment_compliance_report_and_deactivation(client, db):
    institution = _institution(db)
    manager = _manager(db, institution)
    department = Department(
        institution_id=institution.id,
        name="Computing",
        code=f"CS-{uuid.uuid4().hex[:6]}",
        is_active=True,
    )
    db.add(department)
    db.commit()
    db.refresh(department)
    course = Course(
        institution_id=institution.id,
        department_id=department.id,
        code=f"UNIT-{uuid.uuid4().hex[:6]}",
        name="Academic Compliance",
    )
    db.add(course)
    db.commit()
    db.refresh(course)

    app.dependency_overrides[get_current_user] = lambda: manager
    try:
        created = client.post(
            "/api/v1/lecturers",
            json={
                "email": f"lecturer-{uuid.uuid4().hex[:8]}@test.com",
                "password": "StrongPassword123!",
                "full_name": "Ada Lecturer",
                "staff_number": f"STAFF-{uuid.uuid4().hex[:6]}",
                "department_id": department.id,
                "title": "Dr",
                "specialization": "Academic compliance",
            },
        )
        assert created.status_code == 201
        lecturer_id = created.json()["id"]
        user_id = created.json()["user_id"]
        assert created.json()["institution_id"] == institution.id
        assert created.json()["courses"] == []

        duplicate = client.post(
            "/api/v1/lecturers",
            json={
                "email": created.json()["email"],
                "password": "StrongPassword123!",
                "full_name": "Duplicate Lecturer",
                "staff_number": f"STAFF-{uuid.uuid4().hex[:6]}",
            },
        )
        assert duplicate.status_code == 409

        assigned = client.put(
            f"/api/v1/lecturers/{lecturer_id}/courses",
            json={"course_ids": [course.id]},
        )
        assert assigned.status_code == 200
        assert [item["id"] for item in assigned.json()["courses"]] == [course.id]
        db.refresh(course)
        assert course.lecturer_id == lecturer_id

        compliance = client.get(f"/api/v1/lecturers/{lecturer_id}/compliance")
        assert compliance.status_code == 200
        assert compliance.json()["compliance_status"] == "attention_required"
        assert compliance.json()["assigned_courses"] == 1
        assert compliance.json()["courses_without_submission"][0]["id"] == course.id
        assert "No submission deadlines" in compliance.json()["explanation"]

        user = db.query(User).filter(User.id == user_id).one()
        document = AcademicDocument(
            institution_id=institution.id,
            course_id=course.id,
            uploaded_by_id=user_id,
            purpose="lecturer_submission",
            original_filename="academic-report.pdf",
            storage_key=f"{uuid.uuid4().hex}.pdf",
            content_type="application/pdf",
            size_bytes=100,
            sha256="a" * 64,
            status="pending",
        )
        db.add(document)
        db.commit()
        compliance = client.get(f"/api/v1/lecturers/{lecturer_id}/compliance")
        assert compliance.json()["course_submissions"] == 1
        assert compliance.json()["pending_verification"] == 1
        assert compliance.json()["courses_without_submission"] == []

        report = client.get(f"/api/v1/lecturers/{lecturer_id}/report.csv")
        assert report.status_code == 200
        assert report.headers["content-type"].startswith("text/csv")
        assert "course_submissions,1" in report.text

        updated = client.patch(
            f"/api/v1/lecturers/{lecturer_id}",
            json={"specialization": "Compliance and governance", "is_active": False},
        )
        assert updated.status_code == 200
        assert updated.json()["is_active"] is False
        assert user.is_active is False
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_lecturer_manager_cannot_assign_other_institution_course(client, db):
    home_institution = _institution(db)
    other_institution = _institution(db)
    manager = _manager(db, home_institution)
    foreign_user = User(
        email=f"foreign-{uuid.uuid4().hex[:8]}@test.com",
        full_name="Foreign Lecturer",
        institution_id=home_institution.id,
        is_active=True,
        is_verified=True,
    )
    foreign_user.roles.append(_role(db, "lecturer"))
    db.add(foreign_user)
    db.flush()
    lecturer = Lecturer(
        institution_id=home_institution.id,
        user_id=foreign_user.id,
        staff_number=f"F-{uuid.uuid4().hex[:6]}",
    )
    foreign_course = Course(
        institution_id=other_institution.id,
        code=f"X-{uuid.uuid4().hex[:6]}",
        name="Other institution course",
    )
    db.add_all([lecturer, foreign_course])
    db.commit()

    app.dependency_overrides[get_current_user] = lambda: manager
    try:
        response = client.put(
            f"/api/v1/lecturers/{lecturer.id}/courses",
            json={"course_ids": [foreign_course.id]},
        )
    finally:
        app.dependency_overrides.pop(get_current_user, None)
    assert response.status_code == 403
