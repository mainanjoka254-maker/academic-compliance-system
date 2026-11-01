import uuid

from app.core.security import get_current_user, hash_password
from app.main import app
from app.models.academic_structure import AcademicProgram
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
    institution = Institution(name=f"Structure {suffix}", code=f"S{suffix}")
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


def test_faculty_department_programme_course_and_lecturer_assignment(client, db):
    institution = _institution(db)
    manager = _user(db, institution, "university_admin")
    lecturer_user = _user(db, institution, "lecturer")
    lecturer = Lecturer(
        institution_id=institution.id,
        user_id=lecturer_user.id,
        staff_number=f"STAFF-{uuid.uuid4().hex[:6]}",
    )
    db.add(lecturer)
    db.commit()
    db.refresh(lecturer)

    app.dependency_overrides[get_current_user] = lambda: manager
    try:
        faculty_response = client.post(
            "/api/v1/academic-structure/faculties",
            json={"name": "Faculty of Science", "code": f"SCI-{uuid.uuid4().hex[:5]}"},
        )
        assert faculty_response.status_code == 201
        faculty_id = faculty_response.json()["id"]

        department_response = client.post(
            "/api/v1/academic-structure/departments",
            json={
                "name": "Computing",
                "code": f"COMP-{uuid.uuid4().hex[:5]}",
                "faculty_id": faculty_id,
            },
        )
        assert department_response.status_code == 201
        department_id = department_response.json()["id"]

        programme_response = client.post(
            "/api/v1/academic-structure/programmes",
            json={
                "name": "BSc Computing",
                "code": f"BSC-{uuid.uuid4().hex[:5]}",
                "faculty_id": faculty_id,
                "department_id": department_id,
                "award_level": "Bachelor",
            },
        )
        assert programme_response.status_code == 201
        program_id = programme_response.json()["id"]
        assert programme_response.json()["faculty_id"] == faculty_id

        course_response = client.post(
            "/api/v1/courses",
            json={
                "code": f"CS-{uuid.uuid4().hex[:5]}",
                "name": "Academic Compliance",
                "department_id": department_id,
                "program_id": program_id,
            },
        )
        assert course_response.status_code == 201
        assert course_response.json()["program_id"] == program_id

        assignment = client.put(
            f"/api/v1/lecturers/{lecturer.id}/programs",
            json={"program_ids": [program_id]},
        )
        assert assignment.status_code == 200
        assert assignment.json()["programs"] == [
            {
                "id": program_id,
                "code": programme_response.json()["code"],
                "name": "BSc Computing",
            }
        ]
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_academic_structure_rejects_cross_institution_references(client, db):
    institution = _institution(db)
    other_institution = _institution(db)
    manager = _user(db, institution, "university_admin")
    foreign_program = AcademicProgram(
        institution_id=other_institution.id,
        name="Foreign programme",
        code=f"F-{uuid.uuid4().hex[:6]}",
        is_active=True,
    )
    db.add(foreign_program)
    lecturer_user = _user(db, institution, "lecturer")
    lecturer = Lecturer(
        institution_id=institution.id,
        user_id=lecturer_user.id,
        staff_number=f"STAFF-{uuid.uuid4().hex[:6]}",
    )
    db.add(lecturer)
    db.commit()
    db.refresh(foreign_program)

    app.dependency_overrides[get_current_user] = lambda: manager
    try:
        cross_tenant_assignment = client.put(
            f"/api/v1/lecturers/{lecturer.id}/programs",
            json={"program_ids": [foreign_program.id]},
        )
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert cross_tenant_assignment.status_code == 403
