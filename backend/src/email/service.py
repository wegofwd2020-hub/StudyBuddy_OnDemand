"""
backend/src/email/service.py

Async email delivery via SMTP (Gmail by default).

Public API (student demo):
  send_verification_email(to_email, token)          — demo student verification link
  send_credentials_email(to_email, password)        — demo student login credentials

Public API (teacher demo):
  send_teacher_verification_email(to_email, token)  — demo teacher verification link
  send_teacher_credentials_email(to_email, password)— demo teacher login credentials

Uses aiosmtplib for async SMTP; STARTTLS on port 587.
When SMTP_USER / SMTP_PASSWORD are not configured, logs a warning and skips
delivery (useful in development without a mail account set up).
"""

from __future__ import annotations

import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import aiosmtplib
from config import settings

from src.utils.logger import get_logger

log = get_logger("email.service")

# ── Demo verification email ───────────────────────────────────────────────────

_VERIFICATION_SUBJECT = "Verify your StudyBuddy demo account"

_VERIFICATION_TEXT = """\
Hi there,

Someone requested a free StudyBuddy demo using this email address.

Click the link below to verify your email and receive your login credentials:

{verify_url}

This link expires in {ttl_minutes} minutes.

If you didn't request this, you can safely ignore this message.

— The StudyBuddy Team
"""

_VERIFICATION_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8" /></head>
<body style="font-family:sans-serif;max-width:560px;margin:0 auto;padding:24px">
  <h2 style="color:#1a56db">Verify your StudyBuddy demo account</h2>
  <p>Someone requested a free demo using this email address.</p>
  <p>Click the button below to verify your email and receive your login credentials:</p>
  <p style="text-align:center;margin:32px 0">
    <a href="{verify_url}"
       style="background:#1a56db;color:#fff;padding:12px 28px;border-radius:6px;
              text-decoration:none;font-weight:bold">
      Verify Email
    </a>
  </p>
  <p style="color:#666;font-size:13px">
    This link expires in {ttl_minutes} minutes.<br />
    If you didn't request this, you can safely ignore this message.
  </p>
  <p style="color:#666;font-size:13px">— The StudyBuddy Team</p>
</body>
</html>
"""

# ── Demo credentials email ────────────────────────────────────────────────────

_CREDENTIALS_SUBJECT = "Your StudyBuddy demo is ready"

_CREDENTIALS_TEXT = """\
Your free StudyBuddy demo account is ready!

Login URL : {login_url}
Email     : {email}
Password  : {password}

Your account is active for {ttl_hours} hours.

Grade 8 STEM content is pre-loaded and ready to explore.

— The StudyBuddy Team
"""

_CREDENTIALS_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8" /></head>
<body style="font-family:sans-serif;max-width:560px;margin:0 auto;padding:24px">
  <h2 style="color:#1a56db">Your StudyBuddy demo is ready!</h2>
  <p>Here are your login credentials:</p>
  <table style="border-collapse:collapse;width:100%;margin:16px 0">
    <tr>
      <td style="padding:10px;background:#f3f4f6;font-weight:bold;width:120px">Login URL</td>
      <td style="padding:10px;background:#f9fafb">
        <a href="{login_url}" style="color:#1a56db">{login_url}</a>
      </td>
    </tr>
    <tr>
      <td style="padding:10px;background:#f3f4f6;font-weight:bold">Email</td>
      <td style="padding:10px;background:#f9fafb">{email}</td>
    </tr>
    <tr>
      <td style="padding:10px;background:#f3f4f6;font-weight:bold">Password</td>
      <td style="padding:10px;background:#f9fafb;font-family:monospace">{password}</td>
    </tr>
  </table>
  <p style="color:#666;font-size:13px">
    Your account is active for <strong>{ttl_hours} hours</strong>.<br />
    Grade 8 STEM content is pre-loaded and ready to explore.
  </p>
  <p style="color:#666;font-size:13px">— The StudyBuddy Team</p>
</body>
</html>
"""


# ── Core send helper ──────────────────────────────────────────────────────────


async def _send(to_email: str, subject: str, text_body: str, html_body: str) -> None:
    """
    Send a single email via SMTP STARTTLS.

    Skips silently (logs a warning) when SMTP credentials are not configured —
    useful in development where no mail account is needed.
    """
    if not settings.SMTP_USER or not settings.SMTP_PASSWORD:
        log.warning(
            "smtp_not_configured_skipping",
            to=to_email,
            subject=subject,
        )
        return

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_USER}>"
    msg["To"] = to_email
    msg.attach(MIMEText(text_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    tls_context = ssl.create_default_context()
    try:
        await aiosmtplib.send(
            msg,
            hostname=settings.SMTP_HOST,
            port=settings.SMTP_PORT,
            username=settings.SMTP_USER,
            password=settings.SMTP_PASSWORD,
            start_tls=True,
            tls_context=tls_context,
        )
        log.info("email_sent", to=to_email, subject=subject)
    except aiosmtplib.SMTPException as exc:
        log.error("email_send_failed", to=to_email, error=str(exc))
        raise


# ── Public API ────────────────────────────────────────────────────────────────


async def send_verification_email(to_email: str, token: str) -> None:
    """Send the demo email-verification link."""
    verify_url = f"{settings.FRONTEND_URL}/demo/verify/{token}"
    ttl = settings.DEMO_VERIFICATION_TOKEN_TTL_MINUTES

    await _send(
        to_email=to_email,
        subject=_VERIFICATION_SUBJECT,
        text_body=_VERIFICATION_TEXT.format(verify_url=verify_url, ttl_minutes=ttl),
        html_body=_VERIFICATION_HTML.format(verify_url=verify_url, ttl_minutes=ttl),
    )


async def send_credentials_email(to_email: str, password: str) -> None:
    """Send demo account login credentials after email verification."""
    login_url = f"{settings.FRONTEND_URL}/demo/login"

    await _send(
        to_email=to_email,
        subject=_CREDENTIALS_SUBJECT,
        text_body=_CREDENTIALS_TEXT.format(
            login_url=login_url,
            email=to_email,
            password=password,
            ttl_hours=settings.DEMO_ACCOUNT_TTL_HOURS,
        ),
        html_body=_CREDENTIALS_HTML.format(
            login_url=login_url,
            email=to_email,
            password=password,
            ttl_hours=settings.DEMO_ACCOUNT_TTL_HOURS,
        ),
    )


# ── Demo teacher verification email ──────────────────────────────────────────

_TEACHER_VERIFICATION_SUBJECT = "Verify your StudyBuddy teacher demo account"

_TEACHER_VERIFICATION_TEXT = """\
Hi there,

Someone requested a free StudyBuddy teacher demo using this email address.

Click the link below to verify your email and receive your login credentials:

{verify_url}

This link expires in {ttl_minutes} minutes.

If you didn't request this, you can safely ignore this message.

— The StudyBuddy Team
"""

_TEACHER_VERIFICATION_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8" /></head>
<body style="font-family:sans-serif;max-width:560px;margin:0 auto;padding:24px">
  <h2 style="color:#0e7490">Verify your StudyBuddy teacher demo account</h2>
  <p>Someone requested a free teacher demo using this email address.</p>
  <p>Click the button below to verify your email and receive your login credentials:</p>
  <p style="text-align:center;margin:32px 0">
    <a href="{verify_url}"
       style="background:#0e7490;color:#fff;padding:12px 28px;border-radius:6px;
              text-decoration:none;font-weight:bold">
      Verify Email
    </a>
  </p>
  <p style="color:#666;font-size:13px">
    This link expires in {ttl_minutes} minutes.<br />
    If you didn't request this, you can safely ignore this message.
  </p>
  <p style="color:#666;font-size:13px">— The StudyBuddy Team</p>
</body>
</html>
"""

# ── Demo teacher credentials email ────────────────────────────────────────────

_TEACHER_CREDENTIALS_SUBJECT = "Your StudyBuddy teacher demo is ready"

_TEACHER_CREDENTIALS_TEXT = """\
Your free StudyBuddy teacher demo account is ready!

Login URL : {login_url}
Email     : {email}
Password  : {password}

Your account is active for {ttl_hours} hours.

A sample Grade 8 class with synthetic students is pre-loaded so you can
explore reports, assignments, and the teacher dashboard straight away.

— The StudyBuddy Team
"""

_TEACHER_CREDENTIALS_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8" /></head>
<body style="font-family:sans-serif;max-width:560px;margin:0 auto;padding:24px">
  <h2 style="color:#0e7490">Your StudyBuddy teacher demo is ready!</h2>
  <p>Here are your login credentials:</p>
  <table style="border-collapse:collapse;width:100%;margin:16px 0">
    <tr>
      <td style="padding:10px;background:#f3f4f6;font-weight:bold;width:120px">Login URL</td>
      <td style="padding:10px;background:#f9fafb">
        <a href="{login_url}" style="color:#0e7490">{login_url}</a>
      </td>
    </tr>
    <tr>
      <td style="padding:10px;background:#f3f4f6;font-weight:bold">Email</td>
      <td style="padding:10px;background:#f9fafb">{email}</td>
    </tr>
    <tr>
      <td style="padding:10px;background:#f3f4f6;font-weight:bold">Password</td>
      <td style="padding:10px;background:#f9fafb;font-family:monospace">{password}</td>
    </tr>
  </table>
  <p style="color:#666;font-size:13px">
    Your account is active for <strong>{ttl_hours} hours</strong>.<br />
    A sample Grade 8 class with synthetic students is pre-loaded so you can
    explore reports, assignments, and the teacher dashboard straight away.
  </p>
  <p style="color:#666;font-size:13px">— The StudyBuddy Team</p>
</body>
</html>
"""


async def send_teacher_verification_email(to_email: str, token: str) -> None:
    """Send the demo teacher email-verification link."""
    verify_url = f"{settings.FRONTEND_URL}/demo/teacher/verify/{token}"
    ttl = settings.DEMO_VERIFICATION_TOKEN_TTL_MINUTES

    await _send(
        to_email=to_email,
        subject=_TEACHER_VERIFICATION_SUBJECT,
        text_body=_TEACHER_VERIFICATION_TEXT.format(verify_url=verify_url, ttl_minutes=ttl),
        html_body=_TEACHER_VERIFICATION_HTML.format(verify_url=verify_url, ttl_minutes=ttl),
    )


async def send_teacher_credentials_email(to_email: str, password: str) -> None:
    """Send demo teacher login credentials after email verification."""
    login_url = f"{settings.FRONTEND_URL}/demo/teacher/login"

    await _send(
        to_email=to_email,
        subject=_TEACHER_CREDENTIALS_SUBJECT,
        text_body=_TEACHER_CREDENTIALS_TEXT.format(
            login_url=login_url,
            email=to_email,
            password=password,
            ttl_hours=settings.DEMO_TEACHER_ACCOUNT_TTL_HOURS,
        ),
        html_body=_TEACHER_CREDENTIALS_HTML.format(
            login_url=login_url,
            email=to_email,
            password=password,
            ttl_hours=settings.DEMO_TEACHER_ACCOUNT_TTL_HOURS,
        ),
    )
