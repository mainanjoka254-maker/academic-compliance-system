import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal, engine, init_db
from app.core.config import settings
from app.core.bootstrap import validate_super_admin_credentials
from app.models.role import Role
from app.models.user import User
from app.core.security import hash_password
from sqlalchemy import text

admin_credentials = None
if settings.SUPER_ADMIN_EMAIL or settings.SUPER_ADMIN_PASSWORD:
    try:
        admin_credentials = validate_super_admin_credentials(
            settings.SUPER_ADMIN_EMAIL,
            settings.SUPER_ADMIN_PASSWORD,
        )
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

init_db()
bootstrap_lock_name = "adcs_initial_admin_bootstrap"
lock_connection = engine.connect()
lock_acquired = False
try:
    lock_acquired = lock_connection.execute(
        text("SELECT GET_LOCK(:lock_name, 10)"),
        {"lock_name": bootstrap_lock_name},
    ).scalar_one() == 1
    if not lock_acquired:
        raise SystemExit("Another ADCS seed/bootstrap process is running; retry after it finishes.")

    db = SessionLocal()
    try:
        for name, desc in [
            ("super_admin", "Platform super administrator"),
            ("university_admin", "Institution administrator"),
            ("registrar", "Registrar"),
            ("lecturer", "Lecturer"),
            ("student", "Student"),
            ("compliance_officer", "Compliance officer"),
        ]:
            if not db.query(Role).filter(Role.name == name).first():
                db.add(Role(name=name, description=desc, is_system=True))
        db.commit()

        if admin_credentials:
            admin_email, admin_password = admin_credentials
            existing_admin = db.query(User).filter(User.email == admin_email).first()
            if existing_admin and not existing_admin.is_superuser:
                raise SystemExit(
                    "Configured bootstrap email belongs to a non-superuser account; no role was changed."
                )
            if not existing_admin:
                existing_platform_admin = db.query(User.id).filter(
                    (User.is_superuser.is_(True))
                    | User.roles.any(Role.name == "super_admin")
                ).first()
                if existing_platform_admin:
                    raise SystemExit(
                        "A platform super administrator already exists; initial bootstrap is one-time."
                    )
                administrator = User(
                    email=admin_email,
                    hashed_password=hash_password(admin_password),
                    full_name=settings.SUPER_ADMIN_FULL_NAME,
                    is_active=True,
                    is_verified=True,
                    is_superuser=True,
                )
                db.add(administrator)
                db.commit()
                db.refresh(administrator)
                role = db.query(Role).filter(Role.name == "super_admin").one()
                administrator.roles.append(role)
                db.commit()
                print("Bootstrap super administrator created.")
            else:
                role = db.query(Role).filter(Role.name == "super_admin").one()
                if role not in existing_admin.roles:
                    existing_admin.roles.append(role)
                    db.commit()
                print("Configured bootstrap super administrator already exists.")
        else:
            print("Bootstrap administrator skipped; configure dedicated credentials to create one.")

        print("Seed complete. No institutions are automatically inserted.")
    finally:
        if db.in_transaction():
            db.rollback()
        db.close()
finally:
    if lock_acquired:
        lock_connection.execute(
            text("SELECT RELEASE_LOCK(:lock_name)"),
            {"lock_name": bootstrap_lock_name},
        )
    lock_connection.close()
