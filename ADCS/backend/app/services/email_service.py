import smtplib
import logging
from email.message import EmailMessage
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


def send_email(to_email: str, subject: str, body: str, html: Optional[str] = None) -> bool:
    """Send an email via SMTP. Returns True on success, False on failure (never raises)."""
    if not settings.SMTP_USER or not settings.SMTP_PASSWORD:
        if settings.DEBUG:
            logger.warning("SMTP not configured; development email body for %s:\n%s", to_email, body)
        else:
            logger.warning("SMTP delivery skipped because SMTP credentials are not configured")
        return False
    msg = EmailMessage()
    msg["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.set_content(body)
    if html:
        msg.add_alternative(html, subtype="html")

    try:
        if settings.SMTP_PORT == 465:
            server_context = smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15)
        else:
            server_context = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15)
        with server_context as server:
            if settings.SMTP_TLS and settings.SMTP_PORT != 465:
                server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(msg)
        return True
    except smtplib.SMTPAuthenticationError:
        logger.exception("SMTP authentication failed; check SMTP_USER and the Gmail App Password")
        return False
    except smtplib.SMTPException as exc:
        logger.exception("SMTP delivery failed: %s", type(exc).__name__)
        return False
    except OSError as exc:
        logger.exception("SMTP connection failed: %s", type(exc).__name__)
        return False
