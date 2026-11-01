from urllib.parse import parse_qs, urlparse
import uuid

from app.api import auth_google
from app.core.config import settings
from app.core.security import hash_password
from app.models.institution import Institution
from app.models.role import Role
from app.models.student import Student
from app.models.user import User


def test_google_oauth_stays_disabled_without_server_credentials(client, monkeypatch):
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_ID", "")
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_SECRET", "")
    monkeypatch.setattr(settings, "GOOGLE_REDIRECT_URI", "")

    assert client.get("/api/v1/auth/google/status").json() == {"enabled": False}
    response = client.get("/api/v1/auth/google", follow_redirects=False)
    assert response.status_code == 503
    assert response.json()["detail"] == "Google Sign-In is not configured"


def _configure_google(monkeypatch):
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_ID", "test-client-id")
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_SECRET", "test-client-secret")
    monkeypatch.setattr(
        settings,
        "GOOGLE_REDIRECT_URI",
        "http://localhost:8000/api/v1/auth/google/callback",
    )
    monkeypatch.setattr(settings, "FRONTEND_BASE_URL", "http://localhost:5173")
    monkeypatch.setattr(settings, "APP_ENV", "development")
    monkeypatch.setattr(
        auth_google,
        "_exchange_google_code",
        lambda code, code_verifier: "verified-test-id-token",
    )


def _start_google_flow(client, institution_id=None):
    params = {}
    if institution_id is not None:
        params["institution_id"] = institution_id
    response = client.get(
        "/api/v1/auth/google",
        params=params,
        follow_redirects=False,
    )
    assert response.status_code == 302
    query = parse_qs(urlparse(response.headers["location"]).query)
    return response, query


def test_google_registration_uses_verified_identity_and_only_student_role(
    client, db, monkeypatch
):
    _configure_google(monkeypatch)
    institution = Institution(
        name="Google Registration",
        code=f"GR{uuid.uuid4().hex[:6]}",
        is_active=True,
    )
    db.add(institution)
    db.commit()
    db.refresh(institution)
    email = f"google-{uuid.uuid4().hex[:8]}@test.com"
    google_sub = f"google-sub-{uuid.uuid4().hex}"
    monkeypatch.setattr(
        auth_google,
        "_verify_google_id_token",
        lambda _token, expected_nonce: {
            "sub": google_sub,
            "email": email,
            "email_verified": True,
            "name": "Google Test User",
            "nonce": expected_nonce,
        },
    )

    _, query = _start_google_flow(client, institution.id)
    assert query["code_challenge_method"] == ["S256"]
    callback = client.get(
        "/api/v1/auth/google/callback",
        params={"code": "authorization-code", "state": query["state"][0]},
        follow_redirects=False,
    )
    assert callback.status_code == 302
    assert callback.headers["location"] == "http://localhost:5173/auth/callback"

    session = client.post(
        "/api/v1/auth/google/session",
        headers={"Origin": "http://localhost:5173"},
    )
    assert session.status_code == 200
    user = db.query(User).filter(User.email == email).one()
    assert user.google_sub == google_sub
    assert user.auth_provider == "google"
    assert user.is_verified and user.is_active
    assert [role.name for role in user.roles] == ["student"]
    assert db.query(Student).filter(Student.user_id == user.id).count() == 1
    assert session.json()["user_id"] == user.id
    replay = client.post(
        "/api/v1/auth/google/session",
        headers={"Origin": "http://localhost:5173"},
    )
    assert replay.status_code == 401


def test_google_verified_email_links_existing_account_without_duplicate(
    client, db, monkeypatch
):
    _configure_google(monkeypatch)
    role = db.query(Role).filter(Role.name == "university_admin").first()
    if role is None:
        role = Role(
            name="university_admin",
            description="University administrator",
            is_system=True,
        )
        db.add(role)
    email = f"existing-{uuid.uuid4().hex[:8]}@test.com"
    existing_user = User(
        email=email,
        hashed_password=hash_password("test-password"),
        full_name="Existing Administrator",
        is_active=True,
        is_verified=True,
    )
    existing_user.roles.append(role)
    db.add(existing_user)
    db.commit()
    db.refresh(existing_user)
    google_sub = f"google-sub-{uuid.uuid4().hex}"
    monkeypatch.setattr(
        auth_google,
        "_verify_google_id_token",
        lambda _token, expected_nonce: {
            "sub": google_sub,
            "email": email,
            "email_verified": True,
            "name": "Verified Existing User",
            "nonce": expected_nonce,
        },
    )

    _, query = _start_google_flow(client)
    callback = client.get(
        "/api/v1/auth/google/callback",
        params={"code": "authorization-code", "state": query["state"][0]},
        follow_redirects=False,
    )
    assert callback.status_code == 302
    session = client.post(
        "/api/v1/auth/google/session",
        headers={"Origin": "http://localhost:5173"},
    )

    db.refresh(existing_user)
    assert session.status_code == 200
    assert session.json()["user_id"] == existing_user.id
    assert db.query(User).filter(User.email == email).count() == 1
    assert existing_user.google_sub == google_sub
    assert existing_user.auth_provider == "password+google"
    assert [assigned_role.name for assigned_role in existing_user.roles] == [
        "university_admin"
    ]

    _, linked_query = _start_google_flow(client)
    linked_callback = client.get(
        "/api/v1/auth/google/callback",
        params={"code": "authorization-code", "state": linked_query["state"][0]},
        follow_redirects=False,
    )
    assert linked_callback.status_code == 302
    linked_session = client.post(
        "/api/v1/auth/google/session",
        headers={"Origin": "http://localhost:5173"},
    )
    assert linked_session.status_code == 200
    assert linked_session.json()["user_id"] == existing_user.id
    assert db.query(User).filter(User.email == email).count() == 1
