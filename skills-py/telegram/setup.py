"""
Telegram skill setup flow — multi-step interactive authentication.

Steps:
  1. credentials — API ID + API Hash
  2. phone       — Phone number with country code
  3. code        — Verification code sent by Telegram
  4. 2fa         — Two-factor authentication password (conditional)

Each step validates by actually calling the Telegram API. On completion
the session string is persisted via ctx.write_data("config.json", ...).

Setup state is module-level (transient). If the process restarts
mid-setup the user must restart the flow (half-finished Telegram auth
is invalid after restart).
"""

from __future__ import annotations

import contextlib
import json
import logging
import os
from typing import Any

from telethon import TelegramClient
from telethon.errors import (
  ApiIdInvalidError,
  PasswordHashInvalidError,
  PhoneCodeExpiredError,
  PhoneCodeInvalidError,
  PhoneNumberInvalidError,
  SessionPasswordNeededError,
)
from telethon.sessions import StringSession

from dev.types.setup_types import (
  SetupField,
  SetupFieldError,
  SetupResult,
  SetupStep,
)

log = logging.getLogger("skill.telegram.setup")

# ---------------------------------------------------------------------------
# Module-level transient state (cleared on restart or cancel)
# ---------------------------------------------------------------------------

_client: TelegramClient | None = None
_api_id: int = 0
_api_hash: str = ""
_phone: str = ""
_phone_code_hash: str = ""


def _reset_state() -> None:
  global _client, _api_id, _api_hash, _phone, _phone_code_hash
  _client = None
  _api_id = 0
  _api_hash = ""
  _phone = ""
  _phone_code_hash = ""


# ---------------------------------------------------------------------------
# Step definitions
# ---------------------------------------------------------------------------

STEP_CREDENTIALS = SetupStep(
  id="credentials",
  title="API Credentials",
  description=("Enter your Telegram API credentials. Get them at https://my.telegram.org/apps"),
  fields=[
    SetupField(
      name="api_id",
      type="text",
      label="API ID",
      description="Numeric application ID from my.telegram.org",
      required=True,
      placeholder="12345678",
    ),
    SetupField(
      name="api_hash",
      type="password",
      label="API Hash",
      description="Application secret hash from my.telegram.org",
      required=True,
      placeholder="0123456789abcdef0123456789abcdef",
    ),
  ],
)

STEP_PHONE = SetupStep(
  id="phone",
  title="Phone Number",
  description="Enter the phone number associated with your Telegram account.",
  fields=[
    SetupField(
      name="phone",
      type="text",
      label="Phone Number",
      description="Include country code (e.g. +1234567890)",
      required=True,
      placeholder="+1234567890",
    ),
  ],
)

STEP_CODE = SetupStep(
  id="code",
  title="Verification Code",
  description="Enter the verification code Telegram sent to your device.",
  fields=[
    SetupField(
      name="code",
      type="text",
      label="Verification Code",
      description="The 5-digit code from Telegram",
      required=True,
      placeholder="12345",
    ),
  ],
)

STEP_2FA = SetupStep(
  id="2fa",
  title="Two-Factor Authentication",
  description="Your account has 2FA enabled. Enter your password.",
  fields=[
    SetupField(
      name="password",
      type="password",
      label="2FA Password",
      description="Your Telegram cloud password",
      required=True,
    ),
  ],
)


# ---------------------------------------------------------------------------
# Hook handlers
# ---------------------------------------------------------------------------


async def on_setup_start(ctx: Any) -> SetupStep:
  """Return the first setup step.

  If TELEGRAM_API_ID and TELEGRAM_API_HASH are set in the environment,
  skip the credentials step and jump straight to phone number.
  """
  _reset_state()

  env_id = os.environ.get("TELEGRAM_API_ID", "").strip()
  env_hash = os.environ.get("TELEGRAM_API_HASH", "").strip()

  if env_id and env_id.isdigit() and env_hash:
    global _client, _api_id, _api_hash
    _api_id = int(env_id)
    _api_hash = env_hash

    try:
      _client = TelegramClient(
        StringSession(),
        _api_id,
        _api_hash,
        connection_retries=3,
        request_retries=3,
      )
      await _client.connect()
      log.info("Using API credentials from environment variables")
      return STEP_PHONE
    except Exception as exc:
      log.warning("Env credentials failed (%s), falling back to manual entry", exc)
      _reset_state()

  return STEP_CREDENTIALS


async def on_setup_submit(ctx: Any, step_id: str, values: dict[str, Any]) -> SetupResult:
  """Validate and process a submitted step."""
  if step_id == "credentials":
    return await _handle_credentials(ctx, values)
  if step_id == "phone":
    return await _handle_phone(ctx, values)
  if step_id == "code":
    return await _handle_code(ctx, values)
  if step_id == "2fa":
    return await _handle_2fa(ctx, values)

  return SetupResult(
    status="error",
    errors=[SetupFieldError(field="", message=f"Unknown step: {step_id}")],
  )


async def on_setup_cancel(ctx: Any) -> None:
  """Clean up transient state on cancel."""
  global _client
  if _client and _client.is_connected():
    with contextlib.suppress(Exception):
      await _client.disconnect()
  _reset_state()


# ---------------------------------------------------------------------------
# Step handlers
# ---------------------------------------------------------------------------


async def _handle_credentials(ctx: Any, values: dict[str, Any]) -> SetupResult:
  global _client, _api_id, _api_hash

  raw_id = str(values.get("api_id", "")).strip()
  raw_hash = str(values.get("api_hash", "")).strip()

  # Local validation
  errors: list[SetupFieldError] = []
  if not raw_id:
    errors.append(SetupFieldError(field="api_id", message="API ID is required"))
  elif not raw_id.isdigit():
    errors.append(SetupFieldError(field="api_id", message="API ID must be a number"))
  if not raw_hash:
    errors.append(SetupFieldError(field="api_hash", message="API Hash is required"))
  if errors:
    return SetupResult(status="error", errors=errors)

  _api_id = int(raw_id)
  _api_hash = raw_hash

  # Try to connect to validate credentials
  try:
    _client = TelegramClient(
      StringSession(),
      _api_id,
      _api_hash,
      connection_retries=3,
      request_retries=3,
    )
    await _client.connect()
  except ApiIdInvalidError:
    _client = None
    return SetupResult(
      status="error",
      errors=[SetupFieldError(field="api_id", message="Invalid API ID or API Hash")],
    )
  except Exception as exc:
    _client = None
    return SetupResult(
      status="error",
      errors=[SetupFieldError(field="api_id", message=f"Connection failed: {exc}")],
    )

  return SetupResult(status="next", next_step=STEP_PHONE)


async def _handle_phone(ctx: Any, values: dict[str, Any]) -> SetupResult:
  global _phone, _phone_code_hash

  raw_phone = str(values.get("phone", "")).strip()
  if not raw_phone:
    return SetupResult(
      status="error",
      errors=[SetupFieldError(field="phone", message="Phone number is required")],
    )
  if not raw_phone.startswith("+"):
    raw_phone = "+" + raw_phone

  if not _client:
    return SetupResult(
      status="error",
      errors=[SetupFieldError(field="phone", message="Not connected — restart setup")],
    )

  _phone = raw_phone
  try:
    result = await _client.send_code_request(_phone)
    _phone_code_hash = result.phone_code_hash
  except PhoneNumberInvalidError:
    return SetupResult(
      status="error",
      errors=[SetupFieldError(field="phone", message="Invalid phone number")],
    )
  except Exception as exc:
    return SetupResult(
      status="error",
      errors=[SetupFieldError(field="phone", message=f"Failed to send code: {exc}")],
    )

  return SetupResult(status="next", next_step=STEP_CODE)


async def _handle_code(ctx: Any, values: dict[str, Any]) -> SetupResult:
  raw_code = str(values.get("code", "")).strip()
  if not raw_code:
    return SetupResult(
      status="error",
      errors=[SetupFieldError(field="code", message="Verification code is required")],
    )

  if not _client:
    return SetupResult(
      status="error",
      errors=[SetupFieldError(field="code", message="Not connected — restart setup")],
    )

  try:
    await _client.sign_in(
      phone=_phone,
      code=raw_code,
      phone_code_hash=_phone_code_hash,
    )
    # Success — no 2FA needed
    return await _complete_setup(ctx)
  except SessionPasswordNeededError:
    # Account has 2FA — need password
    return SetupResult(status="next", next_step=STEP_2FA)
  except PhoneCodeInvalidError:
    return SetupResult(
      status="error",
      errors=[SetupFieldError(field="code", message="Invalid verification code")],
    )
  except PhoneCodeExpiredError:
    return SetupResult(
      status="error",
      errors=[SetupFieldError(field="code", message="Code expired — restart setup")],
    )
  except Exception as exc:
    return SetupResult(
      status="error",
      errors=[SetupFieldError(field="code", message=f"Sign-in failed: {exc}")],
    )


async def _handle_2fa(ctx: Any, values: dict[str, Any]) -> SetupResult:
  raw_password = str(values.get("password", ""))
  if not raw_password:
    return SetupResult(
      status="error",
      errors=[SetupFieldError(field="password", message="Password is required")],
    )

  if not _client:
    return SetupResult(
      status="error",
      errors=[SetupFieldError(field="password", message="Not connected — restart setup")],
    )

  try:
    await _client.sign_in(password=raw_password)
    return await _complete_setup(ctx)
  except PasswordHashInvalidError:
    return SetupResult(
      status="error",
      errors=[SetupFieldError(field="password", message="Incorrect 2FA password")],
    )
  except Exception as exc:
    return SetupResult(
      status="error",
      errors=[SetupFieldError(field="password", message=f"2FA failed: {exc}")],
    )


# ---------------------------------------------------------------------------
# Completion
# ---------------------------------------------------------------------------


async def _complete_setup(ctx: Any) -> SetupResult:
  """Save session and return completion."""
  if not _client:
    return SetupResult(
      status="error",
      errors=[SetupFieldError(field="", message="Client not connected")],
    )

  session_string = _client.session.save()
  me = await _client.get_me()

  # Persist config
  config = {
    "api_id": _api_id,
    "api_hash": _api_hash,
    "session_string": session_string,
    "user": {
      "id": me.id if me else None,
      "username": me.username if me else None,
      "first_name": me.first_name if me else None,
      "phone": me.phone if me else None,
    },
  }

  try:
    await ctx.write_data("config.json", json.dumps(config, indent=2))
  except Exception:
    log.warning("Could not persist config.json via ctx.write_data")

  display_name = ""
  if me:
    display_name = me.first_name or me.username or str(me.id)

  await _client.disconnect()
  _reset_state()

  return SetupResult(
    status="complete",
    message=f"Connected as {display_name}! Session saved.",
  )
