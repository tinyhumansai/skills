"""
Setup step handlers — process each step's form submission.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from dev.types.skill_types import SkillContext
from dev.types.setup_types import (
  SetupField,
  SetupFieldOption,
  SetupResult,
  SetupStep,
)

from .validation import _validate_alert_threshold


def _now() -> str:
  """Get current timestamp."""
  return datetime.now(timezone.utc).isoformat()


async def _handle_profile_step(ctx: SkillContext, values: dict[str, Any]) -> SetupResult:
  """Handle profile step submission."""
  username = values.get("username", "").strip()
  experience = values.get("experience", "")
  preferences = values.get("preferences", [])

  # Basic validation
  if not username:
    return SetupResult(
      status="error",
      errors=[{"field": "username", "message": "Display name is required."}],
    )

  # Save partial state
  ctx.set_state(
    {
      "setup_partial": {
        "username": username,
        "experience": experience,
        "preferences": preferences,
      }
    }
  )

  # Advance to next step
  return SetupResult(
    status="next",
    next_step=SetupStep(
      id="notifications",
      title="Notification Preferences",
      description="Configure how you'd like to receive updates.",
      fields=[
        SetupField(
          name="enable_notifications",
          type="boolean",
          label="Enable Notifications",
          description="Receive alerts for important events.",
          default=True,
        ),
        SetupField(
          name="digest_frequency",
          type="select",
          label="Digest Frequency",
          description="How often to receive summary digests.",
          options=[
            SetupFieldOption(label="Every hour", value="hourly"),
            SetupFieldOption(label="Daily", value="daily"),
            SetupFieldOption(label="Weekly", value="weekly"),
            SetupFieldOption(label="Never", value="never"),
          ],
          default="daily",
        ),
        SetupField(
          name="alert_threshold",
          type="number",
          label="Price Alert Threshold (%)",
          description="Minimum percentage change to trigger a price alert.",
          placeholder="e.g. 5",
          default=5,
          required=False,
        ),
      ],
    ),
  )


async def _handle_notifications_step(ctx: SkillContext, values: dict[str, Any]) -> SetupResult:
  """Validate notifications step and complete setup."""
  enable_notifications = values.get("enable_notifications", True)
  digest_frequency = values.get("digest_frequency", "daily")
  alert_threshold = values.get("alert_threshold", 5)

  # Validate alert threshold
  validation_error = _validate_alert_threshold(alert_threshold)
  if validation_error:
    return validation_error

  # Merge with profile data and persist
  state = ctx.get_state() or {}
  partial = state.get("setup_partial", {})

  config = {
    **partial,
    "enable_notifications": enable_notifications,
    "digest_frequency": digest_frequency,
    "alert_threshold": alert_threshold,
    "setup_completed_at": _now(),
  }

  # Persist config to data directory
  await ctx.write_data("config.json", json.dumps(config, indent=2))

  # Update skill state
  ctx.set_state({"config": config, "setup_partial": None})

  # Emit setup complete event
  ctx.emit_event("setup_completed", {"username": config.get("username")})

  ctx.log(f"kitchen-sink: setup completed for '{config.get('username')}'")

  return SetupResult(
    status="complete",
    message=(
      f"All set, {config['username']}! "
      f"Your preferences have been saved. "
      f"You'll receive {digest_frequency} digests."
    ),
  )
