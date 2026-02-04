"""
Slack skill setup flow — Bot token collection and validation.

Steps:
  1. bot_token — Enter Slack bot token (xoxb-...)

The token is validated by calling auth.test. On success the token
is persisted via ctx.write_data("config.json", ...).
"""

from __future__ import annotations

import json
import logging
from typing import Any

from dev.types.setup_types import (
  SetupField,
  SetupFieldError,
  SetupResult,
  SetupStep,
)

from .client.slack_client import SlackAuthError, SlackClient

log = logging.getLogger("skill.slack.setup")


# ---------------------------------------------------------------------------
# Step definitions
# ---------------------------------------------------------------------------

STEP_BOT_TOKEN = SetupStep(
  id="bot_token",
  title="Slack Bot Token",
  description=(
    "Enter your Slack bot token (xoxb-...). "
    "Create a bot at https://api.slack.com/apps and install it to your workspace. "
    "Find the token under OAuth & Permissions > Bot User OAuth Token."
  ),
  fields=[
    SetupField(
      name="bot_token",
      type="password",
      label="Bot Token",
      description="Your Slack bot token (starts with xoxb-)",
      required=True,
      placeholder="xoxb-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
    ),
  ],
)


# ---------------------------------------------------------------------------
# Hook handlers
# ---------------------------------------------------------------------------


async def on_setup_start(ctx: Any) -> SetupStep:
  """Return the first (and only) setup step."""
  return STEP_BOT_TOKEN


async def on_setup_submit(ctx: Any, step_id: str, values: dict[str, Any]) -> SetupResult:
  """Validate bot token and persist config."""
  if step_id != "bot_token":
    return SetupResult(
      status="error",
      errors=[SetupFieldError(field="", message=f"Unknown step: {step_id}")],
    )

  raw_token = str(values.get("bot_token", "")).strip()

  # Local validation
  errors: list[SetupFieldError] = []
  if not raw_token:
    errors.append(SetupFieldError(field="bot_token", message="Bot token is required"))
  elif not raw_token.startswith("xoxb-"):
    errors.append(
      SetupFieldError(
        field="bot_token",
        message="Bot token should start with 'xoxb-'. Check your Slack app settings.",
      )
    )

  if errors:
    return SetupResult(status="error", errors=errors)

  # Validate by making a test API call
  client = SlackClient(raw_token)
  try:
    await client.connect()
    is_valid = await client.validate_token()
  except SlackAuthError:
    is_valid = False
  except Exception as exc:
    log.warning("Bot token validation failed: %s", exc)
    await client.close()
    return SetupResult(
      status="error",
      errors=[
        SetupFieldError(
          field="bot_token",
          message=f"Could not connect to Slack: {exc}",
        )
      ],
    )
  finally:
    await client.close()

  if not is_valid:
    return SetupResult(
      status="error",
      errors=[
        SetupFieldError(
          field="bot_token",
          message="Invalid bot token. Please check your token and try again.",
        )
      ],
    )

  # Persist config
  config = {"bot_token": raw_token}
  try:
    await ctx.write_data("config.json", json.dumps(config, indent=2))
  except Exception:
    log.warning("Could not persist config.json via ctx.write_data")

  return SetupResult(
    status="complete",
    message="Slack connected successfully! Your workspace is ready to use.",
  )


async def on_setup_cancel(ctx: Any) -> None:
  """Nothing to clean up for Slack setup."""
  pass
