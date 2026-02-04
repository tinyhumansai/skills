"""
1Password skill setup flow — configure account and vault access.

Steps:
  1. account — Optional 1Password account identifier
  2. vault — Optional default vault name
  3. (automatic) — Connection test on completion
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

log = logging.getLogger("skill.onepassword.setup")

# Module-level transient state
_account: str = ""
_vault: str = ""


def _reset_state() -> None:
  global _account, _vault
  _account = ""
  _vault = ""


STEP_ACCOUNT = SetupStep(
  id="account",
  title="1Password Configuration",
  description="Configure access to your local 1Password vault. You must have the 1Password CLI (op) installed and be signed in.\n\nRun 'op signin' in your terminal first if you haven't already.",
  fields=[
    SetupField(
      name="account",
      type="text",
      label="Account (Optional)",
      description="Your 1Password account identifier (e.g., 'myaccount.1password.com'). Leave empty to use default.",
      required=False,
      placeholder="myaccount.1password.com",
    ),
    SetupField(
      name="vault",
      type="text",
      label="Default Vault (Optional)",
      description="Default vault name to use. Leave empty to access all vaults.",
      required=False,
      placeholder="Personal",
    ),
  ],
)


async def on_setup_start(ctx: Any) -> SetupStep:
  """Return the first setup step."""
  _reset_state()
  return STEP_ACCOUNT


async def on_setup_submit(ctx: Any, step_id: str, values: dict[str, Any]) -> SetupResult:
  """Validate and process a submitted step."""
  if step_id == "account":
    return await _handle_account(ctx, values)

  return SetupResult(
    status="error",
    errors=[SetupFieldError(field="", message=f"Unknown step: {step_id}")],
  )


async def on_setup_cancel(ctx: Any) -> None:
  """Clean up transient state on cancel."""
  _reset_state()


async def _handle_account(ctx: Any, values: dict[str, Any]) -> SetupResult:
  global _account, _vault

  account = str(values.get("account", "")).strip()
  vault = str(values.get("vault", "")).strip()

  _account = account if account else ""
  _vault = vault if vault else ""

  # Test connection
  try:
    from ..client.onepassword_client import OnePasswordClient

    client = OnePasswordClient(
      account=_account if _account else None, vault=_vault if _vault else None
    )

    if not client.check_authentication():
      return SetupResult(
        status="error",
        errors=[
          SetupFieldError(
            field="account",
            message="Not authenticated with 1Password CLI. Please run 'op signin' first.",
          )
        ],
      )

    # Store config
    config = {
      "account": _account,
      "vault": _vault,
    }

    await ctx.write_data("config.json", json.dumps(config, indent=2))

    _reset_state()

    return SetupResult(
      status="complete",
      message="1Password configuration saved successfully.",
    )
  except Exception as e:
    log.error("Failed to test connection: %s", e)
    error_msg = str(e)
    if "not found" in error_msg.lower():
      # TODO: Automate installation of 1Password CLI (op)
      # Could detect OS and provide installation instructions or auto-install via package manager
      error_msg = "1Password CLI (op) not found. Please install it first."
    return SetupResult(
      status="error",
      errors=[SetupFieldError(field="account", message=f"Connection test failed: {error_msg}")],
    )
