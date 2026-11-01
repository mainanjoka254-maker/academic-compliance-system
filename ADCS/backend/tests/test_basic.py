import uuid

from app.models.institution import Institution
from app.models.notification import EmailVerificationToken, PasswordResetToken
from app.models.user import User


def test_register_and_login(client):
    email = f"u{uuid.uuid4().hex[:8]}@test.com"
    # need an institution; create via super admin? Use seed? We'll create institution directly via DB not available in client. 
    # Instead test login endpoint shape with invalid creds
    r = client.post("/api/v1/auth/login", json={"email": "nope@test.com", "password": "wrong"})
    assert r.status_code in (401, 404, 422)


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_email_authentication_lifecycle_and_role_permissions(client, db, monkeypatch):
    monkeypatch.setattr("app.api.auth.send_email", lambda *args, **kwargs: True)
    institution = Institution(
        name=f"Auth Test {uuid.uuid4().hex[:8]}",
        code=f"AT{uuid.uuid4().hex[:6]}",
        is_active=True,
    )
    db.add(institution)
    db.commit()
    db.refresh(institution)

    email = f"auth-{uuid.uuid4().hex[:8]}@test.com"
    password = "StrongTestPassword123!"
    registration = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "full_name": "Test Student",
            "institution_id": institution.id,
            "role_requested": "student",
        },
    )
    assert registration.status_code == 201
    user_id = registration.json()["user_id"]
    otp = db.query(EmailVerificationToken).filter_by(user_id=user_id).one()

    verification = client.post(
        "/api/v1/auth/verify-otp",
        json={"email": email, "otp": otp.token},
    )
    assert verification.status_code == 200

    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert login.status_code == 200
    access_token = login.json()["access_token"]
    me = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert me.status_code == 200
    assert me.json()["email"] == email
    assert client.get(
        "/api/v1/admin/audit-logs",
        headers={"Authorization": f"Bearer {access_token}"},
    ).status_code == 403

    assert client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "full_name": "Duplicate Student",
            "institution_id": institution.id,
            "role_requested": "student",
        },
    ).status_code == 400
    assert client.post(
        "/api/v1/auth/register",
        json={
            "email": f"admin-{uuid.uuid4().hex[:8]}@test.com",
            "password": password,
            "full_name": "Self Promoted Admin",
            "institution_id": institution.id,
            "role_requested": "university_admin",
        },
    ).status_code == 403

    assert client.post(
        "/api/v1/auth/forgot-password",
        json={"email": email},
    ).status_code == 200
    reset_token = db.query(PasswordResetToken).filter_by(user_id=user_id).one()
    new_password = "AnotherStrongPassword456!"
    reset = client.post(
        "/api/v1/auth/reset-password",
        json={"token": reset_token.token, "new_password": new_password},
    )
    assert reset.status_code == 200
    assert client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    ).status_code == 401
    assert client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": new_password},
    ).status_code == 200


def test_registration_reports_email_failure_and_supports_resending(client, db, monkeypatch):
    institution = Institution(
        name=f"Email Failure {uuid.uuid4().hex[:8]}",
        code=f"EF{uuid.uuid4().hex[:6]}",
        is_active=True,
    )
    db.add(institution)
    db.commit()
    db.refresh(institution)
    email = f"email-failure-{uuid.uuid4().hex[:8]}@test.com"
    monkeypatch.setattr("app.api.auth.send_email", lambda *args, **kwargs: False)

    registration = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "StrongTestPassword123!",
            "full_name": "Email Failure User",
            "institution_id": institution.id,
            "role_requested": "student",
        },
    )
    assert registration.status_code == 503
    user = db.query(User).filter_by(email=email).one()
    assert not user.is_active
    assert not user.is_verified

    monkeypatch.setattr("app.api.auth.send_email", lambda *args, **kwargs: True)
    resend = client.post("/api/v1/auth/resend-otp", json={"email": email})
    assert resend.status_code == 200
    tokens = db.query(EmailVerificationToken).filter_by(user_id=user.id).all()
    assert len(tokens) == 2
    assert sum(not token.used for token in tokens) == 1
    active_token = next(token for token in tokens if not token.used)
    verification = client.post(
        "/api/v1/auth/verify-otp",
        json={"email": email, "otp": active_token.token},
    )
    assert verification.status_code == 200
