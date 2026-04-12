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


# ── School provisioning welcome emails (Phase A) ─────────────────────────────

_WELCOME_TEACHER_SUBJECT = "Welcome to StudyBuddy — your teacher account is ready"

_WELCOME_TEACHER_TEXT = """\
Hi {name},

Your StudyBuddy teacher account has been created by your school administrator.

Login URL : {login_url}
Email     : {email}
Password  : {password}

You will be asked to set a new password on your first login.

— The StudyBuddy Team
"""

_WELCOME_TEACHER_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8" /></head>
<body style="font-family:sans-serif;max-width:560px;margin:0 auto;padding:24px">
  <h2 style="color:#1a56db">Welcome to StudyBuddy</h2>
  <p>Hi {name},</p>
  <p>Your teacher account has been created by your school administrator.</p>
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
    You will be asked to set a new password on your first login.
  </p>
  <p style="color:#666;font-size:13px">— The StudyBuddy Team</p>
</body>
</html>
"""

_WELCOME_STUDENT_SUBJECT = "Welcome to StudyBuddy — your student account is ready"

_WELCOME_STUDENT_TEXT = """\
Hi {name},

Your StudyBuddy student account has been created by your school.

Login URL : {login_url}
Email     : {email}
Password  : {password}

You will be asked to set a new password on your first login.

— The StudyBuddy Team
"""

_WELCOME_STUDENT_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8" /></head>
<body style="font-family:sans-serif;max-width:560px;margin:0 auto;padding:24px">
  <h2 style="color:#1a56db">Welcome to StudyBuddy</h2>
  <p>Hi {name},</p>
  <p>Your student account has been created by your school.</p>
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
    You will be asked to set a new password on your first login.
  </p>
  <p style="color:#666;font-size:13px">— The StudyBuddy Team</p>
</body>
</html>
"""

_RESET_PASSWORD_SUBJECT = "StudyBuddy — your password has been reset"

_RESET_PASSWORD_TEXT = """\
Hi {name},

Your StudyBuddy account password has been reset by your school administrator.

Login URL : {login_url}
Email     : {email}
Password  : {password}

You will be asked to set a new password on your next login.

— The StudyBuddy Team
"""

_RESET_PASSWORD_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8" /></head>
<body style="font-family:sans-serif;max-width:560px;margin:0 auto;padding:24px">
  <h2 style="color:#1a56db">Your password has been reset</h2>
  <p>Hi {name},</p>
  <p>Your school administrator has reset your StudyBuddy account password.</p>
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
      <td style="padding:10px;background:#f3f4f6;font-weight:bold">Temp Password</td>
      <td style="padding:10px;background:#f9fafb;font-family:monospace">{password}</td>
    </tr>
  </table>
  <p style="color:#666;font-size:13px">
    You will be asked to set a new password on your next login.
  </p>
  <p style="color:#666;font-size:13px">— The StudyBuddy Team</p>
</body>
</html>
"""


async def send_welcome_teacher_email(to_email: str, name: str, password: str) -> None:
    """Send welcome credentials email to a school-provisioned teacher."""
    login_url = f"{settings.FRONTEND_URL}/login"
    fmt = dict(name=name, login_url=login_url, email=to_email, password=password)
    await _send(
        to_email=to_email,
        subject=_WELCOME_TEACHER_SUBJECT,
        text_body=_WELCOME_TEACHER_TEXT.format(**fmt),
        html_body=_WELCOME_TEACHER_HTML.format(**fmt),
    )


async def send_welcome_student_email(to_email: str, name: str, password: str) -> None:
    """Send welcome credentials email to a school-provisioned student."""
    login_url = f"{settings.FRONTEND_URL}/login"
    fmt = dict(name=name, login_url=login_url, email=to_email, password=password)
    await _send(
        to_email=to_email,
        subject=_WELCOME_STUDENT_SUBJECT,
        text_body=_WELCOME_STUDENT_TEXT.format(**fmt),
        html_body=_WELCOME_STUDENT_HTML.format(**fmt),
    )


async def send_password_reset_email(to_email: str, name: str, password: str) -> None:
    """Send admin-initiated password reset email to a teacher or student."""
    login_url = f"{settings.FRONTEND_URL}/login"
    fmt = dict(name=name, login_url=login_url, email=to_email, password=password)
    await _send(
        to_email=to_email,
        subject=_RESET_PASSWORD_SUBJECT,
        text_body=_RESET_PASSWORD_TEXT.format(**fmt),
        html_body=_RESET_PASSWORD_HTML.format(**fmt),
    )


# ── Retention lifecycle emails ────────────────────────────────────────────────
#
# All five templates are sent to the school_admin contact email.
# The retention dashboard URL is /school/subscription (Phase H UI).
# Placeholders: {grade}, {curriculum_name}, {expires_date}, {grace_date},
#               {days_remaining}, {dashboard_url}
#
# Color scheme: amber/orange (#d97706) for warnings, red (#dc2626) for urgent.


def _retention_dashboard_url() -> str:
    return f"{settings.FRONTEND_URL}/school/subscription"


# ── Template 1: 30-day pre-expiry warning ─────────────────────────────────────

_PRE_EXPIRY_SUBJECT = "Action required: Your Grade {grade} curriculum expires in 30 days"

_PRE_EXPIRY_TEXT = """\
Hi,

This is a reminder that your Grade {grade} curriculum ({curriculum_name}) \
will expire on {expires_date}.

After expiry, students will immediately lose access to this curriculum's content.

To keep your content active, please renew from your retention dashboard:
{dashboard_url}

Renewal extends access for one year from the expiry date — no overlap, no gap.

— The StudyBuddy Team
"""

_PRE_EXPIRY_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8" /></head>
<body style="font-family:sans-serif;max-width:560px;margin:0 auto;padding:24px">
  <div style="background:#fef3c7;border-left:4px solid #d97706;padding:12px 16px;margin-bottom:20px">
    <strong style="color:#92400e">Action required — 30-day expiry warning</strong>
  </div>
  <h2 style="color:#1f2937">Your Grade {grade} curriculum expires in 30 days</h2>
  <p>
    <strong>{curriculum_name}</strong> will expire on
    <strong>{expires_date}</strong>.
  </p>
  <p>
    After expiry, students will <strong>immediately lose access</strong> to this
    curriculum's content. Renew before the deadline to keep your class on track.
  </p>
  <p style="text-align:center;margin:28px 0">
    <a href="{dashboard_url}"
       style="background:#d97706;color:#fff;padding:12px 28px;border-radius:6px;
              text-decoration:none;font-weight:bold">
      Renew Now
    </a>
  </p>
  <p style="color:#6b7280;font-size:13px">
    Renewal extends access for one year from the expiry date — no overlap, no gap.
  </p>
  <p style="color:#6b7280;font-size:13px">— The StudyBuddy Team</p>
</body>
</html>
"""

# ── Template 2: expiry notification (content marked unavailable) ──────────────

_EXPIRY_SUBJECT = "Your Grade {grade} curriculum has expired — student access suspended"

_EXPIRY_TEXT = """\
Hi,

Your Grade {grade} curriculum ({curriculum_name}) expired on {expires_date}.

Student access to this curriculum has been suspended immediately.

You have until {grace_date} (180 days) to renew before the content is
permanently deleted.

Renew from your retention dashboard to restore student access:
{dashboard_url}

— The StudyBuddy Team
"""

_EXPIRY_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8" /></head>
<body style="font-family:sans-serif;max-width:560px;margin:0 auto;padding:24px">
  <div style="background:#fef2f2;border-left:4px solid #dc2626;padding:12px 16px;margin-bottom:20px">
    <strong style="color:#991b1b">Curriculum expired — student access suspended</strong>
  </div>
  <h2 style="color:#1f2937">Grade {grade} curriculum has expired</h2>
  <p>
    <strong>{curriculum_name}</strong> expired on <strong>{expires_date}</strong>.
    Students can no longer access its lessons, quizzes, or activities.
  </p>
  <p>
    Your content will be <strong>permanently deleted on {grace_date}</strong>
    unless you renew before that date.
  </p>
  <p style="text-align:center;margin:28px 0">
    <a href="{dashboard_url}"
       style="background:#dc2626;color:#fff;padding:12px 28px;border-radius:6px;
              text-decoration:none;font-weight:bold">
      Renew to Restore Access
    </a>
  </p>
  <p style="color:#6b7280;font-size:13px">
    Renewing will immediately restore student access and extend the
    curriculum for one year from the original expiry date.
  </p>
  <p style="color:#6b7280;font-size:13px">— The StudyBuddy Team</p>
</body>
</html>
"""

# ── Template 3: 90-day grace reminder ────────────────────────────────────────

_GRACE_90_SUBJECT = "Reminder: {days_remaining} days until Grade {grade} curriculum is permanently deleted"

_GRACE_90_TEXT = """\
Hi,

This is a reminder that your Grade {grade} curriculum ({curriculum_name})
is unavailable and will be permanently deleted on {grace_date}
({days_remaining} days from today).

Students cannot access this content until it is renewed.

Renew from your retention dashboard:
{dashboard_url}

After permanent deletion, restoring the curriculum requires running the full
content pipeline again (Anthropic token cost applies).

— The StudyBuddy Team
"""

_GRACE_90_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8" /></head>
<body style="font-family:sans-serif;max-width:560px;margin:0 auto;padding:24px">
  <div style="background:#fef3c7;border-left:4px solid #d97706;padding:12px 16px;margin-bottom:20px">
    <strong style="color:#92400e">
      Reminder — {days_remaining} days until permanent deletion
    </strong>
  </div>
  <h2 style="color:#1f2937">Grade {grade} curriculum: {days_remaining} days remaining</h2>
  <p>
    <strong>{curriculum_name}</strong> will be permanently deleted on
    <strong>{grace_date}</strong>.
  </p>
  <p>
    Students have been unable to access this content since it expired.
    Renewing now will restore access and extend the curriculum by one year.
  </p>
  <p style="text-align:center;margin:28px 0">
    <a href="{dashboard_url}"
       style="background:#d97706;color:#fff;padding:12px 28px;border-radius:6px;
              text-decoration:none;font-weight:bold">
      Renew Curriculum
    </a>
  </p>
  <p style="color:#6b7280;font-size:13px">
    After permanent deletion, you will need to regenerate the curriculum from
    scratch (Anthropic token cost applies).
  </p>
  <p style="color:#6b7280;font-size:13px">— The StudyBuddy Team</p>
</body>
</html>
"""

# ── Template 4: 30-days-to-purge urgent warning (day 150) ────────────────────

_PURGE_WARNING_SUBJECT = "URGENT: Grade {grade} curriculum content deleted in {days_remaining} days"

_PURGE_WARNING_TEXT = """\
URGENT NOTICE

Your Grade {grade} curriculum ({curriculum_name}) will be permanently and
irreversibly deleted on {grace_date} — {days_remaining} days from today.

After deletion there is no recovery. Generating new content requires a full
pipeline rebuild (Anthropic token cost applies).

Renew NOW from your retention dashboard:
{dashboard_url}

— The StudyBuddy Team
"""

_PURGE_WARNING_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8" /></head>
<body style="font-family:sans-serif;max-width:560px;margin:0 auto;padding:24px">
  <div style="background:#fef2f2;border-left:4px solid #dc2626;padding:12px 16px;margin-bottom:20px">
    <strong style="color:#991b1b">
      URGENT — Permanent deletion in {days_remaining} days
    </strong>
  </div>
  <h2 style="color:#dc2626">Grade {grade} curriculum deleted in {days_remaining} days</h2>
  <p>
    <strong>{curriculum_name}</strong> will be <strong>permanently and
    irreversibly deleted</strong> on <strong>{grace_date}</strong>.
  </p>
  <p>
    There is <strong>no recovery</strong> after deletion. Generating new content
    requires a full pipeline rebuild (Anthropic token cost applies).
  </p>
  <p style="text-align:center;margin:28px 0">
    <a href="{dashboard_url}"
       style="background:#dc2626;color:#fff;padding:12px 28px;border-radius:6px;
              text-decoration:none;font-weight:bold;font-size:16px">
      Renew Now — Last Chance
    </a>
  </p>
  <p style="color:#6b7280;font-size:13px">— The StudyBuddy Team</p>
</body>
</html>
"""

# ── Template 5: purge complete ────────────────────────────────────────────────

_PURGE_COMPLETE_SUBJECT = "Grade {grade} curriculum content permanently deleted"

_PURGE_COMPLETE_TEXT = """\
Hi,

The content for your Grade {grade} curriculum ({curriculum_name}) has been
permanently deleted as of {purge_date}.

The version slot has been freed and is now available for a new curriculum build.

To regenerate content for this grade, upload a new curriculum JSON file and
trigger the pipeline from your school portal.

{dashboard_url}

— The StudyBuddy Team
"""

_PURGE_COMPLETE_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8" /></head>
<body style="font-family:sans-serif;max-width:560px;margin:0 auto;padding:24px">
  <div style="background:#f3f4f6;border-left:4px solid #6b7280;padding:12px 16px;margin-bottom:20px">
    <strong style="color:#374151">Content permanently deleted</strong>
  </div>
  <h2 style="color:#1f2937">Grade {grade} curriculum deleted</h2>
  <p>
    The content for <strong>{curriculum_name}</strong> was permanently deleted
    on <strong>{purge_date}</strong>.
  </p>
  <p>
    The version slot has been freed. You can now upload and build a new
    curriculum for Grade {grade}.
  </p>
  <p style="text-align:center;margin:28px 0">
    <a href="{dashboard_url}"
       style="background:#4b5563;color:#fff;padding:12px 28px;border-radius:6px;
              text-decoration:none;font-weight:bold">
      Go to School Portal
    </a>
  </p>
  <p style="color:#6b7280;font-size:13px">
    Student progress records (quiz scores, session history) have been retained
    in accordance with FERPA requirements.
  </p>
  <p style="color:#6b7280;font-size:13px">— The StudyBuddy Team</p>
</body>
</html>
"""


# ── Retention email dispatcher ────────────────────────────────────────────────


async def send_retention_email(
    to_email: str,
    template: str,
    grade: int,
    curriculum_name: str,
    *,
    expires_date: str = "",
    grace_date: str = "",
    purge_date: str = "",
    days_remaining: int = 0,
) -> None:
    """
    Send one of the five retention lifecycle emails to a school_admin contact.

    template must be one of:
      retention_pre_expiry_warning
      retention_expiry_notification
      retention_grace_90day_reminder
      retention_purge_warning_30day
      retention_purge_complete

    Dates should be ISO-format strings (YYYY-MM-DD) or human-readable dates.
    Delegates to _send() which skips silently when SMTP is not configured.
    """
    dashboard_url = _retention_dashboard_url()

    fmt = dict(
        grade=grade,
        curriculum_name=curriculum_name,
        expires_date=expires_date,
        grace_date=grace_date,
        purge_date=purge_date,
        days_remaining=days_remaining,
        dashboard_url=dashboard_url,
    )

    templates: dict[str, tuple[str, str, str]] = {
        "retention_pre_expiry_warning": (
            _PRE_EXPIRY_SUBJECT.format(**fmt),
            _PRE_EXPIRY_TEXT.format(**fmt),
            _PRE_EXPIRY_HTML.format(**fmt),
        ),
        "retention_expiry_notification": (
            _EXPIRY_SUBJECT.format(**fmt),
            _EXPIRY_TEXT.format(**fmt),
            _EXPIRY_HTML.format(**fmt),
        ),
        "retention_grace_90day_reminder": (
            _GRACE_90_SUBJECT.format(**fmt),
            _GRACE_90_TEXT.format(**fmt),
            _GRACE_90_HTML.format(**fmt),
        ),
        "retention_purge_warning_30day": (
            _PURGE_WARNING_SUBJECT.format(**fmt),
            _PURGE_WARNING_TEXT.format(**fmt),
            _PURGE_WARNING_HTML.format(**fmt),
        ),
        "retention_purge_complete": (
            _PURGE_COMPLETE_SUBJECT.format(**fmt),
            _PURGE_COMPLETE_TEXT.format(**fmt),
            _PURGE_COMPLETE_HTML.format(**fmt),
        ),
    }

    if template not in templates:
        log.warning("retention_email_unknown_template template=%s", template)
        return

    subject, text_body, html_body = templates[template]
    await _send(to_email=to_email, subject=subject,
                text_body=text_body, html_body=html_body)


# ── Payment action required (SCA / 3DS) ──────────────────────────────────────

_SCA_SUBJECT = "Action required: complete your StudyBuddy payment"

_SCA_TEXT = """\
Hi there,

Your bank requires additional verification to complete the payment for your
StudyBuddy school subscription.

Click the link below to complete the 3D Secure verification step:

{action_url}

This link was provided by Stripe and expires shortly — please act now to avoid
your subscription being declined.

If you have any questions, reply to this email or contact us at {support_email}.

— The StudyBuddy Team
"""

_SCA_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8" /></head>
<body style="font-family:sans-serif;max-width:560px;margin:0 auto;padding:24px">
  <h2 style="color:#dc2626">Action required: complete your payment</h2>
  <p>
    Your bank requires additional verification to process the payment for your
    <strong>StudyBuddy school subscription</strong>.
  </p>
  <p>
    Click the button below to complete the 3D Secure (SCA) step. This link
    was provided by Stripe and <strong>expires shortly</strong> — please act
    now to avoid your subscription being declined.
  </p>
  <p style="text-align:center;margin:32px 0">
    <a href="{action_url}"
       style="background:#dc2626;color:#fff;padding:12px 28px;border-radius:6px;
              text-decoration:none;font-weight:bold">
      Complete Payment Verification
    </a>
  </p>
  <p style="color:#6b7280;font-size:13px">
    If you did not initiate this subscription or have questions, contact us at
    <a href="mailto:{support_email}">{support_email}</a>.
  </p>
  <p style="color:#6b7280;font-size:13px">— The StudyBuddy Team</p>
</body>
</html>
"""


async def send_demo_approval_email(
    to_email: str,
    name: str,
    school_org: str,
    url_admin: str,
    url_teacher: str,
    url_student: str,
    expires_at: object,
) -> None:
    """
    Send a personalised demo tour approval email.

    Includes three tour links (school admin / teacher / student) each carrying
    the same signed demo_token so the tour page can greet the requester by name.
    """
    from datetime import datetime

    expires_str = expires_at.strftime("%B %d, %Y at %H:%M UTC") if isinstance(expires_at, datetime) else str(expires_at)

    subject = f"Your StudyBuddy demo is ready, {name}"
    text_body = (
        f"Hi {name},\n\n"
        f"Your personalised StudyBuddy demo for {school_org} is ready.\n\n"
        f"Explore each role using the links below. Your demo expires on {expires_str}.\n\n"
        f"School Admin tour:  {url_admin}\n"
        f"Teacher tour:       {url_teacher}\n"
        f"Student tour:       {url_student}\n\n"
        "These links are personalised for you — please do not share them.\n\n"
        "— The StudyBuddy Team"
    )
    html_body = f"""<!DOCTYPE html>
<html>
<body style="font-family:sans-serif;max-width:560px;margin:0 auto;padding:24px;color:#111827">
  <h2 style="color:#4f46e5">Your StudyBuddy demo is ready</h2>
  <p>Hi <strong>{name}</strong>,</p>
  <p>Your personalised demo for <strong>{school_org}</strong> is ready to explore.</p>
  <p style="color:#6b7280;font-size:13px">Your demo expires on <strong>{expires_str}</strong>.</p>
  <table style="width:100%;border-collapse:collapse;margin:24px 0">
    <tr>
      <td style="padding:12px;background:#f5f3ff;border-radius:8px 8px 0 0;border-bottom:1px solid #e5e7eb">
        <strong style="color:#4f46e5">School Admin tour</strong><br>
        <a href="{url_admin}" style="color:#4f46e5;font-size:13px">{url_admin}</a>
      </td>
    </tr>
    <tr>
      <td style="padding:12px;background:#eff6ff;border-bottom:1px solid #e5e7eb">
        <strong style="color:#2563eb">Teacher tour</strong><br>
        <a href="{url_teacher}" style="color:#2563eb;font-size:13px">{url_teacher}</a>
      </td>
    </tr>
    <tr>
      <td style="padding:12px;background:#f0fdf4;border-radius:0 0 8px 8px">
        <strong style="color:#16a34a">Student tour</strong><br>
        <a href="{url_student}" style="color:#16a34a;font-size:13px">{url_student}</a>
      </td>
    </tr>
  </table>
  <p style="color:#6b7280;font-size:13px">
    These links are personalised for you — please do not share them.
  </p>
  <p style="color:#6b7280;font-size:13px">— The StudyBuddy Team</p>
</body>
</html>"""
    await _send(to_email=to_email, subject=subject, text_body=text_body, html_body=html_body)


async def send_payment_action_required_email(
    to_email: str,
    action_url: str,
) -> None:
    """
    Notify a school admin that their bank requires SCA / 3DS verification.

    action_url is the Stripe-hosted invoice URL (hosted_invoice_url) which
    contains the 3DS challenge link.  Skips silently if SMTP is not configured.
    """
    support_email = getattr(settings, "EMAIL_FROM", "support@studybuddy.app")
    fmt = dict(action_url=action_url, support_email=support_email)
    await _send(
        to_email=to_email,
        subject=_SCA_SUBJECT,
        text_body=_SCA_TEXT.format(**fmt),
        html_body=_SCA_HTML.format(**fmt),
    )
