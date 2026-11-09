import uuid
from unittest.mock import patch

from app.models.institution import Institution
from app.models.notification import EmailVerificationToken
from app.models.role import Role
from app.models.user import User
from app.core.security import hash_password


def _make_institution(db):
    inst = Institution(name=f"Inst {uuid.uuid4().hex[:6]}", code=f"I{uuid.uuid4().hex[:6]}", is_active=True)
    db.add(inst); db.commit(); db.refresh(inst)
    return inst


def _make_admin(db, inst, role_name="university_admin"):
    role = db.query(Role).filter(Role.name == role_name).first()
    if not role:
        role = Role(name=role_name, description=role_name, is_system=True)
        db.add(role); db.commit(); db.refresh(role)
    u = User(email=f"{role_name}-{uuid.uuid4().hex[:6]}@test.com", hashed_password=hash_password("StrongTestPassword123!"),
             full_name="Admin", institution_id=inst.id, is_active=True, is_verified=True, approval_status="approved")
    u.roles.append(role)
    db.add(u); db.commit(); db.refresh(u)
    return u


def _login(client, email):
    r = client.post("/api/v1/auth/login", json={"email": email, "password": "StrongTestPassword123!"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@patch("app.api.auth.send_email", return_value=True)
@patch("app.api.admin.send_email", return_value=True)
def test_staff_request_approval_flow_registrar(_ae, _aa, client, db):
    inst = _make_institution(db)
    admin = _make_admin(db, inst, "university_admin")
    email = f"reg-{uuid.uuid4().hex[:6]}@test.com"
    r = client.post("/api/v1/auth/register", json={"email": email, "password": "StrongTestPassword123!",
                     "full_name": "Pending Registrar", "institution_id": inst.id, "role_requested": "registrar",
                     "staff_number": f"R-{uuid.uuid4().hex[:5]}"})
    assert r.status_code == 201
    user = db.query(User).filter(User.email == email).one()
    otp = db.query(EmailVerificationToken).filter_by(user_id=user.id, used=False).first()
    assert client.post("/api/v1/auth/verify-otp", json={"email": email, "otp": otp.token}).status_code == 200
    headers = _login(client, admin.email)
    reqs = client.get("/api/v1/admin/account-requests", headers=headers)
    assert reqs.status_code == 200
    ids = [x["user_id"] for x in reqs.json()]
    assert user.id in ids
    appr = client.post(f"/api/v1/admin/account-requests/{user.id}/approve", headers=headers, json={"reason": "Verified staff record"})
    assert appr.status_code == 200
    assert appr.json().get("reason") == "Verified staff record"
    login = client.post("/api/v1/auth/login", json={"email": email, "password": "StrongTestPassword123!"})
    assert login.status_code == 200
    assert login.json()["role"] == "registrar"


@patch("app.api.auth.send_email", return_value=True)
@patch("app.api.admin.send_email", return_value=True)
def test_staff_request_approval_flow_compliance_officer(_ae, _aa, client, db):
    inst = _make_institution(db)
    admin = _make_admin(db, inst, "university_admin")
    email = f"co-{uuid.uuid4().hex[:6]}@test.com"
    r = client.post("/api/v1/auth/register", json={"email": email, "password": "StrongTestPassword123!",
                     "full_name": "Pending CO", "institution_id": inst.id, "role_requested": "compliance_officer",
                     "staff_number": f"C-{uuid.uuid4().hex[:5]}"})
    assert r.status_code == 201
    user = db.query(User).filter(User.email == email).one()
    otp = db.query(EmailVerificationToken).filter_by(user_id=user.id, used=False).first()
    client.post("/api/v1/auth/verify-otp", json={"email": email, "otp": otp.token})
    headers = _login(client, admin.email)
    assert client.post(f"/api/v1/admin/account-requests/{user.id}/approve", headers=headers).status_code == 200
    login = client.post("/api/v1/auth/login", json={"email": email, "password": "StrongTestPassword123!"})
    assert login.status_code == 200 and login.json()["role"] == "compliance_officer"


@patch("app.api.auth.send_email", return_value=True)
@patch("app.api.admin.send_email", return_value=True)
def test_university_admin_requires_super_admin_approval(_ae, _aa, client, db):
    inst = _make_institution(db)
    uni_admin = _make_admin(db, inst, "university_admin")
    super_role = db.query(Role).filter(Role.name == "super_admin").first() or Role(name="super_admin", description="super", is_system=True)
    db.add(super_role); db.commit()
    su = User(email=f"su-{uuid.uuid4().hex[:6]}@test.com", hashed_password=hash_password("StrongTestPassword123!"),
              full_name="Super", is_active=True, is_verified=True, is_superuser=True, approval_status="approved")
    su.roles.append(super_role); db.add(su); db.commit()
    email = f"ua-{uuid.uuid4().hex[:6]}@test.com"
    client.post("/api/v1/auth/register", json={"email": email, "password": "StrongTestPassword123!",
                 "full_name": "Pending UA", "institution_id": inst.id, "role_requested": "university_admin",
                 "staff_number": f"U-{uuid.uuid4().hex[:5]}"})
    user = db.query(User).filter(User.email == email).one()
    otp = db.query(EmailVerificationToken).filter_by(user_id=user.id, used=False).first()
    client.post("/api/v1/auth/verify-otp", json={"email": email, "otp": otp.token})
    # uni admin cannot approve university_admin
    assert client.post(f"/api/v1/admin/account-requests/{user.id}/approve", headers=_login(client, uni_admin.email)).status_code == 403
    # super admin can
    assert client.post(f"/api/v1/admin/account-requests/{user.id}/approve", headers=_login(client, su.email)).status_code == 200
    login = client.post("/api/v1/auth/login", json={"email": email, "password": "StrongTestPassword123!"})
    assert login.status_code == 200 and login.json()["role"] == "university_admin"


@patch("app.api.auth.send_email", return_value=True)
def test_account_status_non_enumerating(_ae, client, db):
    inst = _make_institution(db)
    email = f"st-{uuid.uuid4().hex[:6]}@test.com"
    client.post("/api/v1/auth/register", json={"email": email, "password": "StrongTestPassword123!",
                 "full_name": "Status User", "institution_id": inst.id, "role_requested": "registrar",
                 "staff_number": f"S-{uuid.uuid4().hex[:5]}"})
    r = client.get("/api/v1/auth/account-status", params={"email": email})
    assert r.status_code == 200 and r.json()["found"] is True
    r2 = client.get("/api/v1/auth/account-status", params={"email": "nobody@example.com"})
    assert r2.status_code == 200 and r2.json()["found"] is False