"""
Email skill setup flow — multi-step interactive configuration.

Steps:
  1. provider  — Select email provider
  2. credentials — Server settings + email/password
  3. (automatic) — Connection test on step 2 submit

The setup tests both IMAP and SMTP connections. On completion,
config is persisted via ctx.write_data("config.json", ...).

Setup state is module-level (transient). If the process restarts
mid-setup the user must restart the flow.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from dev.types.setup_types import (
  SetupField,
  SetupFieldError,
  SetupFieldOption,
  SetupResult,
  SetupStep,
)

from .client.providers import get_provider
from .client.smtp_client import test_smtp_connection

log = logging.getLogger("skill.email.setup")

# ---------------------------------------------------------------------------
# Module-level transient state (cleared on restart or cancel)
# ---------------------------------------------------------------------------

_provider: str = ""
_imap_host: str = ""
_imap_port: int = 993
_smtp_host: str = ""
_smtp_port: int = 587
_use_ssl: bool = True
_email: str = ""
_password: str = ""


def _reset_state() -> None:
  global _provider, _imap_host, _imap_port, _smtp_host, _smtp_port, _use_ssl, _email, _password
  _provider = ""
  _imap_host = ""
  _imap_port = 993
  _smtp_host = ""
  _smtp_port = 587
  _use_ssl = True
  _email = ""
  _password = ""


# ---------------------------------------------------------------------------
# Step definitions
# ---------------------------------------------------------------------------

STEP_PROVIDER = SetupStep(
  id="provider",
  title="Email Provider",
  description="Select your email provider, or choose Custom for any IMAP/SMTP server.",
  fields=[
    SetupField(
      name="provider",
      type="select",
      label="Provider",
      description="Select your email provider",
      required=True,
      options=[
        SetupFieldOption(value="gmail", label="Gmail"),
        SetupFieldOption(value="outlook", label="Outlook / Office 365"),
        SetupFieldOption(value="yahoo", label="Yahoo Mail"),
        SetupFieldOption(value="icloud", label="iCloud Mail"),
        SetupFieldOption(value="custom", label="Custom IMAP/SMTP"),
      ],
    ),
  ],
)


def _make_credentials_step(
  provider_id: str,
  imap_host: str = "",
  imap_port: int = 993,
  smtp_host: str = "",
  smtp_port: int = 587,
) -> SetupStep:
  """Build the credentials step with pre-filled server settings."""
  preset = get_provider(provider_id)
  notes = ""
  if preset:
    notes = f"\n\n{preset.notes}"

  return SetupStep(
    id="credentials",
    title="Server & Credentials",
    description=f"Enter your email server settings and credentials.{notes}",
    fields=[
      SetupField(
        name="imap_host",
        type="text",
        label="IMAP Host",
        description="IMAP server hostname",
        required=True,
        default=imap_host,
        placeholder="imap.example.com",
      ),
      SetupField(
        name="imap_port",
        type="number",
        label="IMAP Port",
        description="IMAP port (993 for SSL)",
        required=True,
        default=float(imap_port),
        placeholder="993",
      ),
      SetupField(
        name="smtp_host",
        type="text",
        label="SMTP Host",
        description="SMTP server hostname",
        required=True,
        default=smtp_host,
        placeholder="smtp.example.com",
      ),
      SetupField(
        name="smtp_port",
        type="number",
        label="SMTP Port",
        description="SMTP port (587 for STARTTLS, 465 for SSL)",
        required=True,
        default=float(smtp_port),
        placeholder="587",
      ),
      SetupField(
        name="use_ssl",
        type="boolean",
        label="Use SSL/TLS",
        description="Enable SSL/TLS for IMAP connection",
        required=False,
        default=True,
      ),
      SetupField(
        name="email",
        type="text",
        label="Email Address",
        description="Your email address",
        required=True,
        placeholder="you@example.com",
      ),
      SetupField(
        name="password",
        type="password",
        label="Password",
        description="Your password or App Password",
        required=True,
      ),
    ],
  )


# ---------------------------------------------------------------------------
# Hook handlers
# ---------------------------------------------------------------------------


async def on_setup_start(ctx: Any) -> SetupStep:
  """Return the first setup step."""
  _reset_state()
  return STEP_PROVIDER


async def on_setup_submit(ctx: Any, step_id: str, values: dict[str, Any]) -> SetupResult:
  """Validate and process a submitted step."""
  if step_id == "provider":
    return await _handle_provider(ctx, values)
  if step_id == "credentials":
    return await _handle_credentials(ctx, values)

  return SetupResult(
    status="error",
    errors=[SetupFieldError(field="", message=f"Unknown step: {step_id}")],
  )


async def on_setup_cancel(ctx: Any) -> None:
  """Clean up transient state on cancel."""
  _reset_state()


# ---------------------------------------------------------------------------
# Step handlers
# ---------------------------------------------------------------------------


async def _handle_provider(ctx: Any, values: dict[str, Any]) -> SetupResult:
  global _provider, _imap_host, _imap_port, _smtp_host, _smtp_port

  provider_id = str(values.get("provider", "")).strip().lower()
  if not provider_id:
    return SetupResult(
      status="error",
      errors=[SetupFieldError(field="provider", message="Please select a provider")],
    )

  _provider = provider_id

  # Pre-fill from preset
  preset = get_provider(provider_id)
  if preset:
    _imap_host = preset.imap_host
    _imap_port = preset.imap_port
    _smtp_host = preset.smtp_host
    _smtp_port = preset.smtp_port

  return SetupResult(
    status="next",
    next_step=_make_credentials_step(
      provider_id,
      _imap_host,
      _imap_port,
      _smtp_host,
      _smtp_port,
    ),
  )


async def _handle_credentials(ctx: Any, values: dict[str, Any]) -> SetupResult:
  global _imap_host, _imap_port, _smtp_host, _smtp_port, _use_ssl, _email, _password

  # Validate required fields
  errors: list[SetupFieldError] = []

  imap_host = str(values.get("imap_host", "")).strip()
  if not imap_host:
    errors.append(SetupFieldError(field="imap_host", message="IMAP host is required"))

  smtp_host = str(values.get("smtp_host", "")).strip()
  if not smtp_host:
    errors.append(SetupFieldError(field="smtp_host", message="SMTP host is required"))

  email_addr = str(values.get("email", "")).strip()
  if not email_addr:
    errors.append(SetupFieldError(field="email", message="Email address is required"))

  password = str(values.get("password", ""))
  if not password:
    errors.append(SetupFieldError(field="password", message="Password is required"))

  if errors:
    return SetupResult(status="error", errors=errors)

  imap_port = int(values.get("imap_port", 993))
  smtp_port = int(values.get("smtp_port", 587))
  use_ssl = bool(values.get("use_ssl", True))

  _imap_host = imap_host
  _imap_port = imap_port
  _smtp_host = smtp_host
  _smtp_port = smtp_port
  _use_ssl = use_ssl
  _email = email_addr
  _password = password

  # Test IMAP connection
  try:
    from aioimaplib import IMAP4, IMAP4_SSL

    if use_ssl:
      imap = IMAP4_SSL(host=imap_host, port=imap_port)
    else:
      imap = IMAP4(host=imap_host, port=imap_port)

    await imap.wait_hello_from_server()
    response = await imap.login(email_addr, password)
    if response.result != "OK":
      return SetupResult(
        status="error",
        errors=[
          SetupFieldError(
            field="password",
            message="IMAP authentication failed — check email and password",
          )
        ],
      )

    # Quick test: select INBOX
    sel_response = await imap.select("INBOX")
    if sel_response.result != "OK":
      await imap.logout()
      return SetupResult(
        status="error",
        errors=[
          SetupFieldError(field="imap_host", message="IMAP connected but cannot select INBOX")
        ],
      )

    await imap.logout()
  except Exception as exc:
    log.warning("IMAP test failed: %s", exc)
    error_msg = str(exc)
    if "authentication" in error_msg.lower() or "login" in error_msg.lower():
      return SetupResult(
        status="error",
        errors=[
          SetupFieldError(field="password", message=f"IMAP auth failed — {_provider_hint()}")
        ],
      )
    return SetupResult(
      status="error",
      errors=[SetupFieldError(field="imap_host", message=f"IMAP connection failed: {exc}")],
    )

  # Test SMTP connection
  smtp_ok, smtp_msg = await test_smtp_connection(smtp_host, smtp_port, email_addr, password)
  if not smtp_ok:
    return SetupResult(
      status="error",
      errors=[SetupFieldError(field="smtp_host", message=smtp_msg)],
    )

  # Save config
  config = {
    "provider": _provider,
    "imap_host": _imap_host,
    "imap_port": _imap_port,
    "smtp_host": _smtp_host,
    "smtp_port": _smtp_port,
    "use_ssl": _use_ssl,
    "email": _email,
    "password": _password,
  }

  try:
    await ctx.write_data("config.json", json.dumps(config, indent=2))
  except Exception:
    log.warning("Could not persist config.json via ctx.write_data")

  _reset_state()

  return SetupResult(
    status="complete",
    message=f"Connected as {email_addr}! Email is ready to use.",
  )


def _provider_hint() -> str:
  """Return a provider-specific hint for auth failures."""
  if _provider == "gmail":
    return "Gmail requires an App Password (not your regular password)"
  if _provider == "yahoo":
    return "Yahoo requires an App Password"
  if _provider == "icloud":
    return "iCloud requires an App-Specific Password"
  return "check your email and password"
