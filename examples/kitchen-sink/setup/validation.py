"""
Setup validation functions.
"""

from __future__ import annotations

from typing import Any

from dev.types.setup_types import SetupFieldError, SetupResult


def _validate_alert_threshold(alert_threshold: Any) -> SetupResult | None:
  """Validate alert threshold."""
  if alert_threshold is not None:
    try:
      alert_threshold = float(alert_threshold)
      if alert_threshold < 0 or alert_threshold > 100:
        return SetupResult(
          status="error",
          errors=[
            SetupFieldError(
              field="alert_threshold",
              message="Threshold must be between 0 and 100.",
            )
          ],
        )
    except (ValueError, TypeError):
      return SetupResult(
        status="error",
        errors=[
          SetupFieldError(
            field="alert_threshold",
            message="Must be a valid number.",
          )
        ],
      )
  return None
