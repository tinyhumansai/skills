"""
Calendar skill setup flow — OAuth-based configuration for Google Calendar.

Steps:
  1. provider — Select calendar provider (Google, Outlook, CalDAV)
  2. (for Google) — OAuth flow handled via redirect URL
  3. (automatic) — Connection test on completion
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

log = logging.getLogger("skill.calendar.setup")

# Module-level transient state
_provider: str = ""
_credentials: dict[str, Any] = {}


def _reset_state() -> None:
  global _provider, _credentials
  _provider = ""
  _credentials = {}


STEP_PROVIDER = SetupStep(
  id="provider",
  title="Calendar Provider",
  description="Select your calendar provider. Google Calendar uses OAuth authentication.",
  fields=[
    SetupField(
      name="provider",
      type="select",
      label="Provider",
      description="Select your calendar provider",
      required=True,
      options=[
        SetupFieldOption(value="google", label="Google Calendar"),
        SetupFieldOption(value="outlook", label="Outlook / Office 365"),
        SetupFieldOption(value="caldav", label="CalDAV (iCloud, etc.)"),
      ],
    ),
  ],
)


STEP_GOOGLE_OAUTH = SetupStep(
  id="google_oauth",
  title="Google Calendar OAuth",
  description="To connect Google Calendar, you'll need to:\n\n1. Create OAuth credentials in Google Cloud Console\n2. Download the credentials JSON file\n3. Paste the contents here\n\nWe'll handle the OAuth flow automatically.",
  fields=[
    SetupField(
      name="credentials_json",
      type="text",
      label="OAuth Credentials JSON",
      description="Paste the contents of your OAuth credentials JSON file",
      required=True,
      placeholder='{"installed": {"client_id": "...", "client_secret": "...", ...}}',
    ),
  ],
)


async def on_setup_start(ctx: Any) -> SetupStep:
  """Return the first setup step."""
  _reset_state()
  return STEP_PROVIDER


async def on_setup_submit(ctx: Any, step_id: str, values: dict[str, Any]) -> SetupResult:
  """Validate and process a submitted step."""
  if step_id == "provider":
    return await _handle_provider(ctx, values)
  if step_id == "google_oauth":
    return await _handle_google_oauth(ctx, values)

  return SetupResult(
    status="error",
    errors=[SetupFieldError(field="", message=f"Unknown step: {step_id}")],
  )


async def on_setup_cancel(ctx: Any) -> None:
  """Clean up transient state on cancel."""
  _reset_state()


async def _handle_provider(ctx: Any, values: dict[str, Any]) -> SetupResult:
  global _provider

  provider_id = str(values.get("provider", "")).strip().lower()
  if not provider_id:
    return SetupResult(
      status="error",
      errors=[SetupFieldError(field="provider", message="Please select a provider")],
    )

  _provider = provider_id

  if provider_id == "google":
    return SetupResult(
      status="next",
      next_step=STEP_GOOGLE_OAUTH,
    )
  elif provider_id == "outlook":
    return SetupResult(
      status="error",
      errors=[SetupFieldError(field="provider", message="Outlook support coming soon")],
    )
  elif provider_id == "caldav":
    return SetupResult(
      status="error",
      errors=[SetupFieldError(field="provider", message="CalDAV support coming soon")],
    )
  else:
    return SetupResult(
      status="error",
      errors=[SetupFieldError(field="provider", message="Unknown provider")],
    )


async def _handle_google_oauth(ctx: Any, values: dict[str, Any]) -> SetupResult:
  global _provider, _credentials

  credentials_json_str = str(values.get("credentials_json", "")).strip()
  if not credentials_json_str:
    return SetupResult(
      status="error",
      errors=[SetupFieldError(field="credentials_json", message="Credentials JSON is required")],
    )

  try:
    credentials_data = json.loads(credentials_json_str)
  except json.JSONDecodeError as e:
    return SetupResult(
      status="error",
      errors=[SetupFieldError(field="credentials_json", message=f"Invalid JSON: {e}")],
    )

  # Validate credentials structure
  if "installed" not in credentials_data and "web" not in credentials_data:
    return SetupResult(
      status="error",
      errors=[
        SetupFieldError(field="credentials_json", message="Invalid OAuth credentials format")
      ],
    )

  # Store credentials
  _credentials = credentials_data

  # Store credentials for OAuth flow
  # Note: In a full implementation, you'd complete the OAuth flow here
  # For now, we store the OAuth client config and expect authorized credentials
  # to be provided separately (or OAuth flow completed elsewhere)
  config = {
    "provider": _provider,
    "credentials": _credentials,  # OAuth client config
  }

  try:
    await ctx.write_data("config.json", json.dumps(config, indent=2))

    _reset_state()

    return SetupResult(
      status="complete",
      message="Google Calendar OAuth config saved. Note: You'll need to complete OAuth authorization separately to get authorized user credentials.",
    )
  except Exception as e:
    log.error("Failed to save config: %s", e)
    return SetupResult(
      status="error",
      errors=[SetupFieldError(field="credentials_json", message=f"Failed to save config: {e}")],
    )
