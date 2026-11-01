import pytest

from app.core.bootstrap import validate_super_admin_credentials
from app.core.config import Settings
from pydantic import ValidationError


def test_seed_settings_do_not_supply_default_super_admin_credentials():
    settings = Settings(
        _env_file=None,
        DB_HOST="localhost",
        DB_USER="test",
        DB_PASSWORD="test",
        DB_NAME="test",
    )

    assert settings.SUPER_ADMIN_EMAIL == ""
    assert settings.SUPER_ADMIN_PASSWORD == ""


@pytest.mark.parametrize(
    ("email", "password"),
    [
        ("", "Strong-Admin-Pass-012345"),
        ("admin@example.test", ""),
        ("admin@example.test", "ChangeMe123!"),
        ("admin@example.test", "admin-Strong-Pass-012345"),
        ("admin@example.test", "alllowercasepassword123456!"),
    ],
)
def test_seed_rejects_missing_or_weak_super_admin_credentials(email, password):
    with pytest.raises(ValueError):
        validate_super_admin_credentials(email, password)


def test_seed_normalizes_explicit_super_admin_email():
    email, password = validate_super_admin_credentials(
        "  Admin@Example.test ",
        "7s!Rz-ep2gV@LmXc-2035",
    )

    assert email == "admin@example.test"
    assert password == "7s!Rz-ep2gV@LmXc-2035"


def test_production_settings_reject_debug_and_placeholder_secrets():
    required = {
        "DB_HOST": "localhost",
        "DB_USER": "test",
        "DB_PASSWORD": "test",
        "DB_NAME": "test",
        "APP_ENV": "production",
        "DEBUG": False,
    }

    with pytest.raises(ValidationError, match="Production SECRET_KEY"):
        Settings(_env_file=None, **required)
    with pytest.raises(ValidationError, match="DEBUG must be false"):
        Settings(
            _env_file=None,
            **{
                **required,
                "SECRET_KEY": "unit-test-production-secret-key-0123456789",
                "DEBUG": True,
            },
        )
    settings = Settings(
        _env_file=None,
        **{
            **required,
            "SECRET_KEY": "unit-test-production-secret-key-0123456789",
        },
    )
    assert settings.APP_ENV == "production"
