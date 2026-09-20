"""Transactional email delivery over SMTP, with a file-based dev transport."""
import json
import logging
import smtplib
import ssl
from datetime import datetime, timezone
from email.message import EmailMessage
from email.utils import formataddr, make_msgid
from pathlib import Path

import httpx

from modules.backend.src.config import settings

logger = logging.getLogger(__name__)

BRAND = "#2A3FA0"
ACCENT = "#0FA3A3"


def _outbox_dir() -> Path:
    path = settings.project_root / "data" / "outbox"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _shell(title: str, intro: str, body_html: str, footer: str) -> str:
    """Table-based layout — the only thing every mail client renders consistently."""
    return f"""\
<!DOCTYPE html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#f4f6fb;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f4f6fb;padding:32px 12px;">
    <tr><td align="center">
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:520px;background:#ffffff;border-radius:16px;overflow:hidden;box-shadow:0 2px 12px rgba(20,28,60,0.08);">
        <tr><td style="background:linear-gradient(135deg,{BRAND},{ACCENT});padding:28px 32px;">
          <div style="color:#ffffff;font-size:20px;font-weight:700;letter-spacing:-0.3px;">Shikshak<span style="opacity:.75;">AI</span></div>
          <div style="color:rgba(255,255,255,.85);font-size:13px;margin-top:4px;">Your adaptive AI teacher</div>
        </td></tr>
        <tr><td style="padding:32px;">
          <h1 style="margin:0 0 12px;font-size:22px;color:#141c3c;font-weight:700;">{title}</h1>
          <p style="margin:0 0 24px;font-size:15px;line-height:1.6;color:#4a5578;">{intro}</p>
          {body_html}
        </td></tr>
        <tr><td style="padding:20px 32px 28px;border-top:1px solid #eceff6;">
          <p style="margin:0;font-size:12px;line-height:1.6;color:#8b93ad;">{footer}</p>
        </td></tr>
      </table>
      <p style="margin:16px 0 0;font-size:11px;color:#a0a7bd;">© Shikshak AI · Sent automatically, please do not reply.</p>
    </td></tr>
  </table>
</body></html>"""


def _otp_block(code: str) -> str:
    spaced = " ".join(code)
    return f"""\
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin:0 0 24px;">
  <tr><td align="center" style="background:#f4f6fb;border:1px dashed #c9d0e4;border-radius:12px;padding:22px;">
    <div style="font-size:11px;letter-spacing:1.4px;text-transform:uppercase;color:#8b93ad;font-weight:600;">Your code</div>
    <div style="font-size:34px;letter-spacing:8px;font-weight:700;color:{BRAND};font-family:'SF Mono',Menlo,Consolas,monospace;margin-top:8px;">{spaced}</div>
    <div style="font-size:12px;color:#8b93ad;margin-top:10px;">Expires in {settings.otp_ttl_min} minutes</div>
  </td></tr>
</table>"""


class EmailService:
    """Sends real email over Resend's HTTPS API (preferred) or SMTP; falls back
    to data/outbox/ when neither is configured or delivery fails.

    Render — and several other PaaS hosts — block outbound SMTP entirely, so
    smtplib to smtp.gmail.com fails with "Network is unreachable" no matter how
    correct the credentials are. Resend sends over plain HTTPS, which those
    hosts do allow, so it is tried first whenever a key is present.
    """

    def send(self, to_email: str, subject: str, html: str, text: str) -> bool:
        if not settings.enable_smtp_send or not settings.email_transport_configured:
            return self._write_to_outbox(to_email, subject, html, text)

        if settings.resend_configured:
            ok, error = self._send_via_resend(to_email, subject, html, text)
            if ok:
                return True
            logger.error("Resend delivery to %s failed: %s", to_email, error)
            if settings.smtp_configured:
                ok, error = self._send_via_smtp(to_email, subject, html, text)
                if ok:
                    return True
                logger.error("SMTP delivery to %s failed: %s", to_email, error)
            if settings.email_dev_fallback:
                return self._write_to_outbox(to_email, subject, html, text, error=str(error))
            return False

        ok, error = self._send_via_smtp(to_email, subject, html, text)
        if ok:
            return True
        logger.error("SMTP delivery to %s failed: %s", to_email, error)
        if settings.email_dev_fallback:
            return self._write_to_outbox(to_email, subject, html, text, error=str(error))
        return False

    def _send_via_resend(self, to_email: str, subject: str, html: str, text: str) -> tuple[bool, str]:
        try:
            resp = httpx.post(
                "https://api.resend.com/emails",
                headers={"Authorization": f"Bearer {settings.resend_api_key}"},
                json={
                    "from": formataddr((settings.smtp_from_name, settings.sender_address)),
                    "to": [to_email],
                    "subject": subject,
                    "html": html,
                    "text": text,
                },
                timeout=20.0,
            )
            resp.raise_for_status()
            logger.info("Sent %r to %s via Resend", subject, to_email)
            return True, ""
        except Exception as exc:
            return False, str(exc)

    def _send_via_smtp(self, to_email: str, subject: str, html: str, text: str) -> tuple[bool, str]:
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = formataddr((settings.smtp_from_name, settings.sender_address))
        msg["To"] = to_email
        msg["Message-ID"] = make_msgid(domain="shikshak.ai")
        msg.set_content(text)
        msg.add_alternative(html, subtype="html")

        try:
            context = ssl.create_default_context()
            if settings.smtp_port == 465:
                with smtplib.SMTP_SSL(
                    settings.smtp_host, settings.smtp_port, context=context, timeout=20
                ) as server:
                    server.login(settings.smtp_user, settings.smtp_password)
                    server.send_message(msg)
            else:
                with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as server:
                    server.ehlo()
                    if settings.smtp_starttls:
                        server.starttls(context=context)
                        server.ehlo()
                    server.login(settings.smtp_user, settings.smtp_password)
                    server.send_message(msg)
            logger.info("Sent %r to %s via SMTP", subject, to_email)
            return True, ""
        except Exception as exc:
            return False, str(exc)

    def _write_to_outbox(
        self, to_email: str, subject: str, html: str, text: str, error: str = ""
    ) -> bool:
        """Dev transport: persist the message so the flow stays testable offline."""
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f")
        safe = to_email.replace("@", "_at_").replace("/", "_")
        base = _outbox_dir() / f"{stamp}_{safe}"
        base.with_suffix(".html").write_text(html, encoding="utf-8")
        base.with_suffix(".json").write_text(
            json.dumps(
                {
                    "to": to_email,
                    "subject": subject,
                    "text": text,
                    "smtp_error": error,
                    "sent_at": datetime.now(timezone.utc).isoformat(),
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        logger.warning(
            "EMAIL NOT SENT over SMTP — written to %s. Subject: %s", base.with_suffix(".json"), subject
        )
        # Surface the code in logs so a local demo can still complete the flow.
        logger.warning("DEV EMAIL BODY for %s:\n%s", to_email, text)
        return True

    # ---- Templated messages -------------------------------------------------

    def send_verification_otp(self, to_email: str, full_name: str, code: str) -> bool:
        first = (full_name or "there").split()[0]
        html = _shell(
            "Verify your email",
            f"Hi {first}, welcome to Shikshak AI. Enter this code to activate your account "
            "and start your first lesson.",
            _otp_block(code),
            "If you did not create a Shikshak AI account, you can safely ignore this email. "
            "Never share this code with anyone.",
        )
        text = (
            f"Hi {first},\n\nYour Shikshak AI verification code is: {code}\n"
            f"It expires in {settings.otp_ttl_min} minutes.\n\n"
            "If you did not sign up, ignore this email."
        )
        return self.send(to_email, f"{code} is your Shikshak AI verification code", html, text)

    def send_password_reset_otp(self, to_email: str, full_name: str, code: str) -> bool:
        first = (full_name or "there").split()[0]
        html = _shell(
            "Reset your password",
            f"Hi {first}, we received a request to reset your Shikshak AI password. "
            "Use the code below to choose a new one.",
            _otp_block(code),
            "If you did not request a password reset, ignore this email — your password "
            "stays unchanged. Never share this code with anyone.",
        )
        text = (
            f"Hi {first},\n\nYour Shikshak AI password reset code is: {code}\n"
            f"It expires in {settings.otp_ttl_min} minutes.\n\n"
            "If you did not request this, ignore this email."
        )
        return self.send(to_email, f"{code} is your Shikshak AI password reset code", html, text)

    def send_password_changed_notice(self, to_email: str, full_name: str) -> bool:
        first = (full_name or "there").split()[0]
        when = datetime.now(timezone.utc).strftime("%d %b %Y at %H:%M UTC")
        html = _shell(
            "Your password was changed",
            f"Hi {first}, the password for your Shikshak AI account was changed on {when}. "
            "All other signed-in devices have been signed out.",
            "",
            "If this wasn't you, reset your password immediately and contact support.",
        )
        text = (
            f"Hi {first},\n\nYour Shikshak AI password was changed on {when}. "
            "All other devices were signed out.\n\nIf this wasn't you, reset your password now."
        )
        return self.send(to_email, "Your Shikshak AI password was changed", html, text)

    def send_welcome(self, to_email: str, full_name: str) -> bool:
        first = (full_name or "there").split()[0]
        cta = f"""\
<table role="presentation" cellpadding="0" cellspacing="0" style="margin:0 0 8px;">
  <tr><td style="background:{BRAND};border-radius:10px;">
    <a href="{settings.public_base_url}/dashboard.html"
       style="display:inline-block;padding:13px 26px;color:#fff;text-decoration:none;font-weight:600;font-size:15px;">
       Start your first lesson</a>
  </td></tr>
</table>"""
        html = _shell(
            f"You're all set, {first}",
            "Your account is verified. Upload a chapter or just name a topic — Shikshak will "
            "plan the lesson, teach it on video, quiz you, and adapt when you get stuck.",
            cta,
            "Every lesson you complete is tracked so your dashboard shows exactly which "
            "concepts you've mastered.",
        )
        text = (
            f"Hi {first},\n\nYour Shikshak AI account is verified. "
            f"Start learning: {settings.public_base_url}/dashboard.html"
        )
        return self.send(to_email, "Welcome to Shikshak AI", html, text)


email_service = EmailService()
