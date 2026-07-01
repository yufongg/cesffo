"""
This file contains functionality for the password reset feature.
It utilizes a personal GMAIL account created in the name of cesffo to send password reset emails that the user can click
Clicking it will redirect the user to a webpage for them to enter their new credentials.
"""

import html
import os
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formataddr

# Publicly available info
GMAIL_SMTP_HOST = "smtp.gmail.com"
GMAIL_SMTP_PORT = 587

GMAIL_ADDRESS = os.getenv("GMAIL_ADDRESS", "").strip()
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "")
EMAIL_FROM_NAME = os.getenv("EMAIL_FROM_NAME", "Cesffo")

IS_PRODUCTION = os.getenv("APP_ENV", "development") == "production"


class EmailConfigError(RuntimeError):
    """Raised when an email must be sent but Gmail credentials are not configured."""
    pass


def _gmail_configured() -> bool:
    return bool(GMAIL_ADDRESS and GMAIL_APP_PASSWORD)


def send_email(to_email: str, subject: str, text_body: str, html_body: str | None = None) -> None:
    #* Send one multipart email (plain-text, plus an optional HTML alternative) through Gmail.
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = formataddr((EMAIL_FROM_NAME, GMAIL_ADDRESS or "no-reply@cesffo.local"))
    msg["To"] = to_email
    msg.set_content(text_body)
    if html_body:
        msg.add_alternative(html_body, subtype="html")

    #! No Gmail credentials configured: fail hard in production, but in dev just
    #^ print the email to the console so local flows aren't blocked on SMTP setup.
    if not _gmail_configured():
        if IS_PRODUCTION:
            raise EmailConfigError(
                "Gmail is not configured (set GMAIL_ADDRESS and GMAIL_APP_PASSWORD)"
            )
        print(  # noqa: T201 - intentional dev-only console fallback
            "\n----- [DEV EMAIL] Gmail not configured; printing instead -----\n"
            f"To: {to_email}\nSubject: {subject}\n\n{text_body}\n"
            "--------------------------------------------------------------\n",
            flush=True,
        )
        return

    context = ssl.create_default_context()
    with smtplib.SMTP(GMAIL_SMTP_HOST, GMAIL_SMTP_PORT, timeout=10) as server:
        server.starttls(context=context)
        server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
        server.send_message(msg)


def send_password_reset_email(to_email: str, username: str, reset_link: str, expires_minutes: int) -> None:
    #* Build and send the one-time password-reset email (plain-text + HTML versions).
    subject = "Reset your Cesffo password"

    text_body = (
        f"Hi {username},\n\n"
        "We received a request to reset the password for your Cesffo account.\n"
        "Click the link below to choose a new password:\n\n"
        f"{reset_link}\n\n"
        f"This link expires in {expires_minutes} minutes and can only be used once.\n"
        "If you didn't request this, you can safely ignore this email — your "
        "password will not change.\n\n"
        "— The Cesffo team"
    )

    #! Escape both values before dropping them into HTML — username and link are
    #! interpolated into markup, so unescaped input would be an email XSS vector.
    safe_user = html.escape(username)
    safe_link = html.escape(reset_link, quote=True)
    html_body = (
        f"<p>Hi {safe_user},</p>"
        "<p>We received a request to reset the password for your Cesffo account. "
        "Click the button below to choose a new password:</p>"
        f'<p><a href="{safe_link}" '
        'style="display:inline-block;padding:10px 18px;background:#2563eb;'
        'color:#ffffff;text-decoration:none;border-radius:6px;">'
        "Reset my password</a></p>"
        f"<p>Or paste this link into your browser:<br>"
        f'<a href="{safe_link}">{safe_link}</a></p>'
        f"<p>This link expires in {expires_minutes} minutes and can only be used "
        "once. If you didn't request this, you can safely ignore this email — "
        "your password will not change.</p>"
        "<p>— The Cesffo team</p>"
    )

    send_email(to_email, subject, text_body, html_body)
