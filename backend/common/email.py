"""Outbound email via Gmail SMTP.

Sends through Gmail's SMTP relay (smtp.gmail.com:587, STARTTLS) using a Gmail
account plus an App Password. Standard library only — no extra dependency.

One-time setup on the Gmail account:
  1. Enable 2-Step Verification (required before App Passwords are available).
  2. Create an App Password:  Google Account -> Security -> App passwords.
  3. Put the 16-character App Password in GMAIL_APP_PASSWORD and the address in
     GMAIL_ADDRESS (see .env.example). The normal account password will NOT work
     for SMTP once 2-Step Verification is on.

Dev convenience: if GMAIL_ADDRESS / GMAIL_APP_PASSWORD are unset and the app is
not running in production, the email (including the reset link) is printed to the
backend console instead of being sent, so the flow is demoable without creds.
"""

import html
import os
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formataddr

# Gmail's submission endpoint. STARTTLS on 587 is the recommended setup.
GMAIL_SMTP_HOST = "smtp.gmail.com"
GMAIL_SMTP_PORT = 587

GMAIL_ADDRESS = os.getenv("GMAIL_ADDRESS", "").strip()
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "")
# Display name shown to recipients. The From address is always the Gmail account
# (Gmail rejects/rewrites a From that isn't the authenticated mailbox).
EMAIL_FROM_NAME = os.getenv("EMAIL_FROM_NAME", "Cesffo")

IS_PRODUCTION = os.getenv("APP_ENV", "development") == "production"


class EmailConfigError(RuntimeError):
    """Raised when an email must be sent but Gmail credentials are not configured."""
    pass


def _gmail_configured() -> bool:
    return bool(GMAIL_ADDRESS and GMAIL_APP_PASSWORD)


def send_email(to_email: str, subject: str, text_body: str, html_body: str | None = None) -> None:
    """Send a single multipart (plain-text + optional HTML) email via Gmail.

    Blocking (uses smtplib); call it from a background task / threadpool, never
    inline in a request handler. Raises EmailConfigError in production if Gmail is
    not configured; in development it prints the message instead.
    """
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = formataddr((EMAIL_FROM_NAME, GMAIL_ADDRESS or "no-reply@cesffo.local"))
    msg["To"] = to_email
    msg.set_content(text_body)
    if html_body:
        msg.add_alternative(html_body, subtype="html")

    if not _gmail_configured():
        if IS_PRODUCTION:
            # Fail loudly in logs (the request already returned 200) rather than
            # silently dropping a real user's reset email.
            raise EmailConfigError(
                "Gmail is not configured (set GMAIL_ADDRESS and GMAIL_APP_PASSWORD)"
            )
        # Development fallback: surface the message (incl. the reset link) so the
        # flow can be exercised end-to-end without credentials.
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
    """Compose and send the one-time password-reset email.

    The email carries only a short-lived, single-use reset *link* (a capability),
    never a password. Both the username and the link are HTML-escaped before being
    placed in the HTML part to prevent injection into the message body.
    """
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
