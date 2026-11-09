import uuid

from app.core.security import get_current_user, hash_password, verify_password
from app.models.institution import Institution
from app.models.notification import EmailVerificationToken
from app.models.role import Role
from app.models.student import Lecturer, Student
from app.models.user import User


def _admin(db, role_name="super_admin", is_superuser=True):
    role = db.query(Role).filter(Role.name == role_name).first()
    if role is None:
        role = Role(name=role_name, description=role_name, is_system=True)
        db.add(role)
    user = User(
        email=f"{role_name}-{uuid.uuid4().hex[:8]}@test.com",
        hashed_password=hash_password("StrongTestPassword123!"),
        full_name="Setup Administrator",
        is_active=True,
        is_verified=True,
        is_superuser=is_superuser,
    )
    user.roles.append(role)
    db.add(user)
    db.commit()
    return user


def test_only_super_admin_can_create_first_institution_and_manage_it(client, db):
    assert client.post(
        "/api/v1/institutions",
        json={"name": "First University", "code": "FIRST"},
    ).status_code == 401

    administrator = _admin(db)
    app_override = get_current_user
    from app.main import app

    app.dependency_overrides[app_override] = lambda: administrator
    try:
        created = client.post(
            "/api/v1/institutions",
            json={
                "name": "First University",
                "code": "first-uni",
                "type": "university",
                "country": "Kenya",
            },
        )
        assert created.status_code == 201, created.text
        assert "id" in created.json(), created.text
        institution_id = created.json()["id"]
        assert created.json()["code"] == "FIRST-UNI"
        assert created.json()["is_active"] is True
        options = client.get("/api/v1/institutions/registration-options").json()
        assert {"id": institution_id, "name": "First University"} in options

        updated = client.patch(
            f"/api/v1/institutions/{institution_id}",
            json={"name": "Updated University", "country": "Uganda"},
        )
        assert updated.status_code == 200
        assert updated.json()["name"] == "Updated University"
        assert updated.json()["country"] == "Uganda"

        deactivated = client.patch(
            f"/api/v1/institutions/{institution_id}/activate",
            params={"is_active": "false"},
        )
        assert deactivated.status_code == 200
        options_after_deactivation = client.get("/api/v1/institutions/registration-options").json()
        assert institution_id not in {option["id"] for option in options_after_deactivation}
        assert client.post(
            "/api/v1/auth/register",
            json={
                "email": f"inactive-{uuid.uuid4().hex[:8]}@test.com",
                "password": "StrongTestPassword123!",
                "full_name": "Inactive Student",
                "institution_id": institution_id,
                "role_requested": "student",
            },
        ).status_code == 400
    finally:
        from app.main import app
        app.dependency_overrides.pop(app_override, None)


def test_registration_persists_student_and_approved_lecturer_to_selected_institution(client, db, monkeypatch):
    monkeypatch.setattr("app.api.auth.send_email", lambda *args, **kwargs: True)
    institution = Institution(
        name=f"Onboarding University {uuid.uuid4().hex[:8]}",
        code=f"ON{uuid.uuid4().hex[:8]}",
        is_active=True,
    )
    db.add(institution)
    db.commit()
    db.refresh(institution)
    student_email = f"student-{uuid.uuid4().hex[:8]}@test.com"
    lecturer_email = f"lecturer-{uuid.uuid4().hex[:8]}@test.com"

    student_response = client.post(
        "/api/v1/auth/register",
        json={
            "email": student_email,
            "password": "StrongTestPassword123!",
            "full_name": "Institution Student",
            "institution_id": institution.id,
            "role_requested": "student",
        },
    )
    assert student_response.status_code == 201, student_response.text
    student_user = db.query(User).filter_by(email=student_email).one()
    student_profile = db.query(Student).filter_by(user_id=student_user.id).one()
    assert student_user.institution_id == institution.id
    assert student_profile.institution_id == institution.id

    lecturer_response = client.post(
        "/api/v1/auth/register",
        json={
            "email": lecturer_email,
            "password": "StrongTestPassword123!",
            "full_name": "Institution Lecturer",
            "institution_id": institution.id,
            "role_requested": "lecturer",
            "staff_number": "STAFF-ONBOARD",
        },
    )
    assert lecturer_response.status_code == 201, lecturer_response.text
    lecturer_user = db.query(User).filter_by(email=lecturer_email).one()
    assert lecturer_user.institution_id == institution.id
    assert lecturer_user.is_active is False
    assert lecturer_user.approval_status == "pending"
    assert not any(role.name == "lecturer" for role in lecturer_user.roles)
    otp = db.query(EmailVerificationToken).filter_by(user_id=lecturer_user.id).one()
    verification = client.post(
        "/api/v1/auth/verify-otp",
        json={"email": lecturer_email, "otp": otp.token},
    )
    assert verification.status_code == 200
    db.refresh(lecturer_user)
    assert lecturer_user.is_verified is True
    assert lecturer_user.is_active is False

    administrator = _admin(db)
    from app.main import app

    app.dependency_overrides[get_current_user] = lambda: administrator
    try:
        pending = client.get("/api/v1/lecturers/registration-requests")
        assert pending.status_code == 200
        assert any(row["user_id"] == lecturer_user.id for row in pending.json())
        approved = client.post(
            f"/api/v1/lecturers/{lecturer_user.id}/registration-request/approve",
        )
        assert approved.status_code == 200, approved.text
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    db.refresh(lecturer_user)
    lecturer_profile = db.query(Lecturer).filter_by(user_id=lecturer_user.id).one()
    assert lecturer_user.institution_id == institution.id
    assert lecturer_profile.institution_id == institution.id
    assert lecturer_profile.staff_number == "STAFF-ONBOARD"
    assert lecturer_user.is_active is True
    assert "lecturer" in {role.name for role in lecturer_user.roles}


def test_super_admin_manages_institution_administrators_and_regular_user_cannot_create_institution(client, db):
    institution = Institution(
        name=f"Admin Management {uuid.uuid4().hex[:8]}",
        code=f"AM{uuid.uuid4().hex[:8]}",
        is_active=True,
    )
    db.add(institution)
    db.commit()
    db.refresh(institution)
    administrator = _admin(db)
    from app.main import app

    app.dependency_overrides[get_current_user] = lambda: administrator
    try:
        created = client.post(
            f"/api/v1/institutions/{institution.id}/administrators",
            json={
                "email": f"inst-admin-{uuid.uuid4().hex[:8]}@test.com",
                "password": "LongAndStrongAdminPassword123!",
                "full_name": "Institution Administrator",
            },
        )
        assert created.status_code == 201, created.text
        admin_id = created.json()["id"]
        admin_user = db.query(User).filter_by(id=admin_id).one()
        assert admin_user.institution_id == institution.id
        assert verify_password("LongAndStrongAdminPassword123!", admin_user.hashed_password)

        listed = client.get(f"/api/v1/institutions/{institution.id}/administrators")
        assert listed.status_code == 200
        assert [row["id"] for row in listed.json()] == [admin_id]
        deactivated = client.patch(
            f"/api/v1/institutions/{institution.id}/administrators/{admin_id}",
            json={"is_active": False},
        )
        assert deactivated.status_code == 200
        assert deactivated.json()["is_active"] is False
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    student_role = db.query(Role).filter(Role.name == "student").first()
    if student_role is None:
        student_role = Role(name="student", description="student", is_system=True)
        db.add(student_role)
    student = User(
        email=f"regular-{uuid.uuid4().hex[:8]}@test.com",
        hashed_password=hash_password("StrongTestPassword123!"),
        full_name="Ordinary Student",
        institution_id=institution.id,
        is_active=True,
        is_verified=True,
    )
    student.roles.append(student_role)
    db.add(student)
    db.commit()
    app.dependency_overrides[get_current_user] = lambda: student
    try:
        forbidden = client.post(
            "/api/v1/institutions",
            json={"name": "Unauthorized Institution", "code": "NOPE"},
        )
        assert forbidden.status_code == 403
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_public_registration_cannot_request_privileged_roles(client, db):
    institution = Institution(
        name=f"Role Guard {uuid.uuid4().hex[:8]}",
        code=f"RG{uuid.uuid4().hex[:8]}",
        is_active=True,
    )
    db.add(institution)
    db.commit()
    # Staff roles may be requested, but remain pending approval (no privilege escalation).
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": f"admin-request-{uuid.uuid4().hex[:8]}@test.com",
            "password": "StrongTestPassword123!",
            "full_name": "Pending Admin Request",
            "institution_id": institution.id,
            "role_requested": "university_admin",
            "staff_number": f"ADM-{uuid.uuid4().hex[:6]}",
        },
    )
    assert response.status_code == 201
    assert "approval" in response.json()["message"].lower()
    # A non-requestable role is rejected.
    bad = client.post(
        "/api/v1/auth/register",
        json={
            "email": f"bad-{uuid.uuid4().hex[:8]}@test.com",
            "password": "StrongTestPassword123!",
            "full_name": "Bad Role",
            "institution_id": institution.id,
            "role_requested": "super_admin",
        },
    )
    assert bad.status_code == 422
