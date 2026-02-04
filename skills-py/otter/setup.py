"""
Otter.ai skill setup flow — API key collection and validation.

Steps:
  1. api_key — Enter Otter.ai API key

The key is validated by making a test API call. On success the key
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

from .client.otter_client import OtterAuthError, OtterClient

log = logging.getLogger("skill.otter.setup")


# ---------------------------------------------------------------------------
# Step definitions
# ---------------------------------------------------------------------------

STEP_API_KEY = SetupStep(
  id="api_key",
  title="Otter.ai API Key",
  description=(
    "Enter your Otter.ai API key from Settings > Developer > API Keys. Keys start with 'ott_live_'."
  ),
  fields=[
    SetupField(
      name="api_key",
      type="password",
      label="API Key",
      description="Your Otter.ai Connect API key",
      required=True,
      placeholder="ott_live_xxxxxxxxxxxxxxxxxxxx",
    ),
  ],
)


# ---------------------------------------------------------------------------
# Hook handlers
# ---------------------------------------------------------------------------


async def on_setup_start(ctx: Any) -> SetupStep:
  """Return the first (and only) setup step."""
  return STEP_API_KEY


async def on_setup_submit(ctx: Any, step_id: str, values: dict[str, Any]) -> SetupResult:
  """Validate API key and persist config."""
  if step_id != "api_key":
    return SetupResult(
      status="error",
      errors=[SetupFieldError(field="", message=f"Unknown step: {step_id}")],
    )

  raw_key = str(values.get("api_key", "")).strip()

  # Local validation
  errors: list[SetupFieldError] = []
  if not raw_key:
    errors.append(SetupFieldError(field="api_key", message="API key is required"))
  elif not raw_key.startswith("ott_live_"):
    errors.append(
      SetupFieldError(
        field="api_key",
        message="API key should start with 'ott_live_'. Check your Otter.ai developer settings.",
      )
    )

  if errors:
    return SetupResult(status="error", errors=errors)

  # Validate by making a test API call
  client = OtterClient(raw_key)
  try:
    await client.connect()
    is_valid = await client.validate_key()
  except OtterAuthError:
    is_valid = False
  except Exception as exc:
    log.warning("API key validation failed: %s", exc)
    await client.close()
    return SetupResult(
      status="error",
      errors=[
        SetupFieldError(
          field="api_key",
          message=f"Could not connect to Otter.ai: {exc}",
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
          field="api_key",
          message="Invalid API key. Please check your key and try again.",
        )
      ],
    )

  # Persist config
  config = {"api_key": raw_key}
  try:
    await ctx.write_data("config.json", json.dumps(config, indent=2))
  except Exception:
    log.warning("Could not persist config.json via ctx.write_data")

  return SetupResult(
    status="complete",
    message="Otter.ai connected successfully! Your meetings will be synced.",
  )


async def on_setup_cancel(ctx: Any) -> None:
  """Nothing to clean up for Otter setup."""
  pass
