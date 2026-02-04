"""
Async SMTP client wrapper using aiosmtplib.

Connect-per-send pattern: opens connection, sends, disconnects.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import aiosmtplib

if TYPE_CHECKING:
  from email.mime.multipart import MIMEMultipart
  from email.mime.text import MIMEText

log = logging.getLogger("skill.email.client.smtp")

# Module-level config (set during setup/load)
_config: dict[str, Any] = {}


def configure_smtp(
  host: str,
  port: int,
  email: str,
  password: str,
  use_ssl: bool = True,
) -> None:
  """Store SMTP configuration for connect-per-send."""
  global _config
  _config = {
    "host": host,
    "port": port,
    "email": email,
    "password": password,
    "use_ssl": use_ssl,
  }


def is_configured() -> bool:
  """Check if SMTP is configured."""
  return bool(_config.get("host") and _config.get("email"))


async def send_email(
  to: list[str],
  subject: str,
  body: str,
  html_body: str | None = None,
  cc: list[str] | None = None,
  bcc: list[str] | None = None,
  reply_to: str | None = None,
  in_reply_to: str | None = None,
  references: list[str] | None = None,
  from_name: str | None = None,
) -> bool:
  """Send an email using connect-per-send pattern."""
  if not is_configured():
    raise RuntimeError("SMTP not configured")

  from_addr = _config["email"]
  display_from = f"{from_name} <{from_addr}>" if from_name else from_addr

  # Build message
  from email.mime.multipart import MIMEMultipart
  from email.mime.text import MIMEText

  if html_body:
    msg: MIMEMultipart | MIMEText = MIMEMultipart("alternative")
    msg.attach(MIMEText(body, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))
  else:
    msg = MIMEText(body, "plain", "utf-8")

  msg["From"] = display_from
  msg["To"] = ", ".join(to)
  msg["Subject"] = subject

  if cc:
    msg["Cc"] = ", ".join(cc)
  if reply_to:
    msg["Reply-To"] = reply_to
  if in_reply_to:
    msg["In-Reply-To"] = in_reply_to
  if references:
    msg["References"] = " ".join(references)

  # All recipients
  all_recipients = list(to)
  if cc:
    all_recipients.extend(cc)
  if bcc:
    all_recipients.extend(bcc)

  # Connect and send
  try:
    port = _config["port"]
    use_tls = port == 465

    if use_tls:
      smtp = aiosmtplib.SMTP(
        hostname=_config["host"],
        port=port,
        use_tls=True,
      )
    else:
      smtp = aiosmtplib.SMTP(
        hostname=_config["host"],
        port=port,
        start_tls=True,
      )

    await smtp.connect()
    await smtp.login(_config["email"], _config["password"])
    await smtp.send_message(msg, sender=from_addr, recipients=all_recipients)
    await smtp.quit()

    log.info("Email sent to %s", ", ".join(to))
    return True
  except Exception:
    log.exception("Failed to send email")
    raise


async def test_smtp_connection(
  host: str,
  port: int,
  email: str,
  password: str,
) -> tuple[bool, str]:
  """Test SMTP connectivity. Returns (success, message)."""
  try:
    use_tls = port == 465

    if use_tls:
      smtp = aiosmtplib.SMTP(
        hostname=host,
        port=port,
        use_tls=True,
      )
    else:
      smtp = aiosmtplib.SMTP(
        hostname=host,
        port=port,
        start_tls=True,
      )

    await smtp.connect()
    await smtp.login(email, password)
    await smtp.quit()
    return True, "SMTP connection successful"
  except aiosmtplib.SMTPAuthenticationError:
    return False, "SMTP authentication failed — check email and password"
  except aiosmtplib.SMTPConnectError:
    return False, f"Cannot connect to SMTP server {host}:{port}"
  except Exception as e:
    return False, f"SMTP error: {e}"
