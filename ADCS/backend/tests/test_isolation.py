import uuid
from datetime import date

import pytest
from pydantic import ValidationError

from app.models.academic import AttendanceRecord, Course, CourseEnrollment
from app.models.institution import Institution
from app.models.user import User
from app.models.role import Role
from app.models.student import Lecturer, Student
from app.schemas.academic import AcademicTermCreate, AssessmentCreate
from app.core.security import hash_password
from app.core.security import get_current_user
from app.main import app


def test_institution_isolation_students(db):
    inst1 = Institution(name="I1", code=f"I{uuid.uuid4().hex[:6]}", is_active=True)
    inst2 = Institution(name="I2", code=f"I{uuid.uuid4().hex[:6]}", is_active=True)
    db.add_all([inst1, inst2]); db.commit(); db.refresh(inst1); db.refresh(inst2)

    u1 = User(email=f"a{uuid.uuid4().hex[:6]}@t.com", hashed_password=hash_password("p"), full_name="A", institution_id=inst1.id, is_active=True, is_verified=True)
    u2 = User(email=f"b{uuid.uuid4().hex[:6]}@t.com", hashed_password=hash_password("p"), full_name="B", institution_id=inst2.id, is_active=True, is_verified=True)
    db.add_all([u1, u2]); db.commit(); db.refresh(u1); db.refresh(u2)

    s1 = Student(user_id=u1.id, institution_id=inst1.id, student_number=f"S{u1.id}", status="active")
    s2 = Student(user_id=u2.id, institution_id=inst2.id, student_number=f"S{u2.id}", status="active")
    db.add_all([s1, s2]); db.commit()

    # Query scoped to inst1 should not include inst2 student
    scoped = db.query(Student).filter(Student.institution_id == inst1.id).all()
    ids = [s.id for s in scoped]
    assert s1.id in ids
    assert s2.id not in ids


def test_student_api_only_exposes_own_profile(client, db):
    inst = Institution(name="Scoped", code=f"SC{uuid.uuid4().hex[:6]}", is_active=True)
    db.add(inst)
    db.commit()
    db.refresh(inst)

    role = db.query(Role).filter(Role.name == "student").first()
    if role is None:
        role = Role(name="student", description="Student", is_system=True)
        db.add(role)

    current_user = User(
        email=f"self{uuid.uuid4().hex[:6]}@t.com",
        hashed_password=hash_password("test-password"),
        full_name="Current Student",
        institution_id=inst.id,
        is_active=True,
        is_verified=True,
    )
    other_user = User(
        email=f"other{uuid.uuid4().hex[:6]}@t.com",
        hashed_password=hash_password("test-password"),
        full_name="Other Student",
        institution_id=inst.id,
        is_active=True,
        is_verified=True,
    )
    current_user.roles.append(role)
    db.add_all([current_user, other_user])
    db.commit()
    db.refresh(current_user)
    db.refresh(other_user)

    own_profile = Student(
        user_id=current_user.id,
        institution_id=inst.id,
        student_number=f"S{current_user.id}",
        status="active",
    )
    other_profile = Student(
        user_id=other_user.id,
        institution_id=inst.id,
        student_number=f"S{other_user.id}",
        status="active",
    )
    db.add_all([own_profile, other_profile])
    db.commit()

    app.dependency_overrides[get_current_user] = lambda: current_user
    try:
        response = client.get("/api/v1/students")
        detail_response = client.get(f"/api/v1/students/{other_profile.id}")
        enrollment_response = client.post(
            "/api/v1/courses/enroll",
            json={"student_id": other_profile.id, "course_id": 1},
        )
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 200
    assert [student["id"] for student in response.json()] == [own_profile.id]
    assert detail_response.status_code == 403
    assert enrollment_response.status_code == 403


def test_institution_access_and_admin_role_escalation_are_denied(client, db):
    inst1 = Institution(name="Boundary A", code=f"BA{uuid.uuid4().hex[:6]}", is_active=True)
    inst2 = Institution(name="Boundary B", code=f"BB{uuid.uuid4().hex[:6]}", is_active=True)
    db.add_all([inst1, inst2])
    db.commit()
    db.refresh(inst1)
    db.refresh(inst2)

    student_role = db.query(Role).filter(Role.name == "student").first()
    if student_role is None:
        student_role = Role(name="student", description="Student", is_system=True)
        db.add(student_role)
    student_user = User(
        email=f"boundary-student-{uuid.uuid4().hex[:6]}@test.com",
        hashed_password=hash_password("test-password"),
        full_name="Boundary Student",
        institution_id=inst1.id,
        is_active=True,
        is_verified=True,
    )
    student_user.roles.append(student_role)
    db.add(student_user)
    db.commit()

    app.dependency_overrides[get_current_user] = lambda: student_user
    try:
        cross_institution = client.get(f"/api/v1/institutions/{inst2.id}")
    finally:
        app.dependency_overrides.pop(get_current_user, None)
    assert cross_institution.status_code == 403

    admin_role = db.query(Role).filter(Role.name == "university_admin").first()
    if admin_role is None:
        admin_role = Role(name="university_admin", description="University administrator", is_system=True)
        db.add(admin_role)
    admin_user = User(
        email=f"boundary-admin-{uuid.uuid4().hex[:6]}@test.com",
        hashed_password=hash_password("test-password"),
        full_name="Boundary Administrator",
        institution_id=inst1.id,
        is_active=True,
        is_verified=True,
    )
    admin_user.roles.append(admin_role)
    db.add(admin_user)
    db.commit()

    app.dependency_overrides[get_current_user] = lambda: admin_user
    try:
        role_assignment = client.post(
            "/api/v1/users/assign-role",
            json={"user_id": student_user.id, "role_name": "super_admin"},
        )
        user_creation = client.post(
            "/api/v1/users",
            json={
                "email": f"escalation-{uuid.uuid4().hex[:6]}@test.com",
                "password": "test-password",
                "full_name": "Unauthorized Platform Admin",
                "role": "super_admin",
            },
        )
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert role_assignment.status_code == 403
    assert user_creation.status_code == 403


def test_lecturer_access_is_limited_to_assigned_courses(client, db):
    institution = Institution(
        name="Teaching Scope",
        code=f"TS{uuid.uuid4().hex[:6]}",
        is_active=True,
    )
    db.add(institution)
    db.commit()
    db.refresh(institution)

    lecturer_role = db.query(Role).filter(Role.name == "lecturer").first()
    if lecturer_role is None:
        lecturer_role = Role(name="lecturer", description="Lecturer", is_system=True)
        db.add(lecturer_role)
    student_role = db.query(Role).filter(Role.name == "student").first()
    if student_role is None:
        student_role = Role(name="student", description="Student", is_system=True)
        db.add(student_role)

    lecturer_user = User(
        email=f"lecturer-{uuid.uuid4().hex[:8]}@test.com",
        hashed_password=hash_password("test-password"),
        full_name="Assigned Lecturer",
        institution_id=institution.id,
        is_active=True,
        is_verified=True,
    )
    other_lecturer_user = User(
        email=f"lecturer-other-{uuid.uuid4().hex[:8]}@test.com",
        hashed_password=hash_password("test-password"),
        full_name="Other Lecturer",
        institution_id=institution.id,
        is_active=True,
        is_verified=True,
    )
    student_user = User(
        email=f"student-{uuid.uuid4().hex[:8]}@test.com",
        hashed_password=hash_password("test-password"),
        full_name="Enrolled Student",
        institution_id=institution.id,
        is_active=True,
        is_verified=True,
    )
    lecturer_user.roles.append(lecturer_role)
    student_user.roles.append(student_role)
    db.add_all([lecturer_user, other_lecturer_user, student_user])
    db.commit()
    db.refresh(lecturer_user)
    db.refresh(other_lecturer_user)
    db.refresh(student_user)

    lecturer = Lecturer(
        user_id=lecturer_user.id,
        institution_id=institution.id,
        staff_number=f"L{lecturer_user.id}",
    )
    other_lecturer = Lecturer(
        user_id=other_lecturer_user.id,
        institution_id=institution.id,
        staff_number=f"L{other_lecturer_user.id}",
    )
    student = Student(
        user_id=student_user.id,
        institution_id=institution.id,
        student_number=f"S{student_user.id}",
        status="active",
    )
    db.add_all([lecturer, other_lecturer, student])
    db.commit()
    db.refresh(lecturer)
    db.refresh(other_lecturer)
    db.refresh(student)

    assigned_course = Course(
        institution_id=institution.id,
        code="ASSIGNED-1",
        name="Assigned Course",
        lecturer_id=lecturer.id,
    )
    other_course = Course(
        institution_id=institution.id,
        code="OTHER-1",
        name="Other Course",
        lecturer_id=other_lecturer.id,
    )
    db.add_all([assigned_course, other_course])
    db.commit()
    db.refresh(assigned_course)
    db.refresh(other_course)
    db.add_all(
        [
            CourseEnrollment(
                institution_id=institution.id,
                student_id=student.id,
                course_id=assigned_course.id,
            ),
            CourseEnrollment(
                institution_id=institution.id,
                student_id=student.id,
                course_id=other_course.id,
            ),
            AttendanceRecord(
                institution_id=institution.id,
                student_id=student.id,
                course_id=assigned_course.id,
                date=date(2026, 1, 1),
                status="present",
            ),
            AttendanceRecord(
                institution_id=institution.id,
                student_id=student.id,
                course_id=other_course.id,
                date=date(2026, 1, 2),
                status="absent",
            ),
        ]
    )
    db.commit()

    app.dependency_overrides[get_current_user] = lambda: lecturer_user
    try:
        courses = client.get("/api/v1/courses")
        unauthorized_course = client.get(f"/api/v1/courses/{other_course.id}")
        attendance = client.get(f"/api/v1/academic/attendance/{student.id}")
        unauthorized_write = client.post(
            "/api/v1/academic/attendance",
            json={
                "student_id": student.id,
                "course_id": other_course.id,
                "date": "2026-01-03",
                "status": "present",
            },
        )
        authorized_write = client.post(
            "/api/v1/academic/attendance",
            json={
                "student_id": student.id,
                "course_id": assigned_course.id,
                "date": "2026-01-03",
                "status": "present",
            },
        )
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert courses.status_code == 200
    assert [course["id"] for course in courses.json()] == [assigned_course.id]
    assert unauthorized_course.status_code == 403
    assert attendance.status_code == 200
    assert {record["course_id"] for record in attendance.json()} == {assigned_course.id}
    assert unauthorized_write.status_code == 403
    assert authorized_write.status_code == 201


def test_academic_payloads_reject_invalid_score_and_term_ranges():
    with pytest.raises(ValidationError):
        AssessmentCreate(
            student_id=1,
            course_id=1,
            title="Final exam",
            max_score=100,
            score=101,
        )

    with pytest.raises(ValidationError):
        AcademicTermCreate(
            name="Invalid term",
            start_date=date(2026, 9, 1),
            end_date=date(2026, 8, 31),
        )
