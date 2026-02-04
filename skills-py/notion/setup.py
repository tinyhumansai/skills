"""
Notion skill setup flow — single-step token configuration.

Steps:
  1. token — Enter Integration Token from notion.so/my-integrations

The token is validated by calling the Notion API (users.me()).
On success the token and workspace info are persisted to config.json.

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
  SetupResult,
  SetupStep,
)

log = logging.getLogger("skill.notion.setup")

# ---------------------------------------------------------------------------
# Module-level transient state (cleared on restart or cancel)
# ---------------------------------------------------------------------------

_token: str = ""


def _reset_state() -> None:
  global _token
  _token = ""


# ---------------------------------------------------------------------------
# Step definitions
# ---------------------------------------------------------------------------

STEP_TOKEN = SetupStep(
  id="token",
  title="Connect Notion Workspace",
  description=(
    "Enter your Notion Internal Integration Token. "
    "Create one at https://www.notion.so/my-integrations — "
    "then share the pages/databases you want to access with the integration."
  ),
  fields=[
    SetupField(
      name="token",
      type="password",
      label="Integration Token",
      description="Starts with ntn_ or secret_",
      required=True,
      placeholder="ntn_...",
    ),
    SetupField(
      name="workspace_name",
      type="text",
      label="Workspace Label (optional)",
      description="A friendly name for this workspace",
      required=False,
      placeholder="My Workspace",
    ),
  ],
)


# ---------------------------------------------------------------------------
# Hook handlers
# ---------------------------------------------------------------------------


async def on_setup_start(ctx: Any) -> SetupStep:
  """Return the first (and only) step."""
  _reset_state()
  return STEP_TOKEN


async def on_setup_submit(ctx: Any, step_id: str, values: dict[str, Any]) -> SetupResult:
  """Handle form submission."""
  if step_id == "token":
    return await _handle_token(ctx, values)

  return SetupResult(
    status="error",
    errors=[SetupFieldError(field="token", message=f"Unknown step: {step_id}")],
  )


async def on_setup_cancel(ctx: Any) -> None:
  """User cancelled setup."""
  _reset_state()
  log.info("Setup cancelled")


# ---------------------------------------------------------------------------
# Step handler
# ---------------------------------------------------------------------------


async def _handle_token(ctx: Any, values: dict[str, Any]) -> SetupResult:
  """Validate the integration token by calling users.me()."""
  global _token

  token = (values.get("token") or "").strip()
  workspace_name = (values.get("workspace_name") or "").strip()

  if not token:
    return SetupResult(
      status="error",
      errors=[SetupFieldError(field="token", message="Token is required")],
    )

  # Validate token format (optional — Notion tokens start with ntn_ or secret_)
  if not (token.startswith("ntn_") or token.startswith("secret_")):
    return SetupResult(
      status="error",
      errors=[
        SetupFieldError(
          field="token",
          message="Token should start with 'ntn_' or 'secret_'. Check your integration page.",
        )
      ],
    )

  # Validate by calling the API
  from notion_client import APIResponseError, AsyncClient

  client = AsyncClient(auth=token)
  try:
    me = await client.users.me()
  except APIResponseError as e:
    status = e.status if hasattr(e, "status") else 0
    if status == 401:
      return SetupResult(
        status="error",
        errors=[
          SetupFieldError(
            field="token",
            message="Invalid token — Notion returned 401 Unauthorized.",
          )
        ],
      )
    return SetupResult(
      status="error",
      errors=[SetupFieldError(field="token", message=f"Notion API error: {e}")],
    )
  except Exception as e:
    log.exception("Connection error during setup")
    return SetupResult(
      status="error",
      errors=[
        SetupFieldError(
          field="token",
          message=f"Connection failed: {e}",
        )
      ],
    )

  _token = token

  # Persist config
  return await _complete_setup(ctx, me, workspace_name)


async def _complete_setup(ctx: Any, bot_user: dict[str, Any], workspace_name: str) -> SetupResult:
  """Save config and return completion."""
  config = {
    "token": _token,
    "workspace_name": workspace_name or bot_user.get("name", "Notion"),
    "bot_user": {
      "id": bot_user.get("id", ""),
      "name": bot_user.get("name", ""),
      "type": bot_user.get("type", "bot"),
    },
  }

  await ctx.write_data("config.json", json.dumps(config, indent=2))

  _reset_state()

  bot_name = bot_user.get("name", "integration")
  return SetupResult(
    status="complete",
    message=f"Connected to Notion as '{bot_name}'. Share pages with your integration to give it access.",
  )
