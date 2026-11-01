import re


def validate_super_admin_credentials(email: str, password: str) -> tuple[str, str]:
    normalized_email = email.strip().lower()
    if not normalized_email or not password:
        raise ValueError("Both SUPER_ADMIN_EMAIL and SUPER_ADMIN_PASSWORD must be configured")
    if len(password) < 16:
        raise ValueError("SUPER_ADMIN_PASSWORD must contain at least 16 characters")
    if normalized_email.split("@", 1)[0] in password.lower():
        raise ValueError("SUPER_ADMIN_PASSWORD must not contain the email username")
    if not all(
        (
            re.search(r"[a-z]", password),
            re.search(r"[A-Z]", password),
            re.search(r"\d", password),
            re.search(r"[^A-Za-z0-9]", password),
        )
    ):
        raise ValueError("SUPER_ADMIN_PASSWORD must include lowercase, uppercase, numeric, and symbol characters")
    return normalized_email, password
