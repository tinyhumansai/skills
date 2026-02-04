"""
1Password skill server lifecycle hooks.
"""

from __future__ import annotations

import logging
from typing import Any

from .client.onepassword_client import OnePasswordClient
from .state.store import get_state, set_client, update_state

log = logging.getLogger("skill.onepassword.server")


async def on_skill_load(params: dict[str, Any], set_state_fn: Any | None = None) -> None:
  """Initialize 1Password client on skill load."""
  # TODO: Automate installation of 1Password CLI (op) if not found
  # Could check for 'op' command availability and install via:
  # - macOS: brew install 1password-cli
  # - Linux: Download from 1Password website or use package manager
  # - Windows: Download installer or use winget/choco
  config = params.get("config", {})

  account = config.get("account") or None
  vault = config.get("vault") or None

  try:
    client = OnePasswordClient(account=account, vault=vault)

    # Test authentication
    if not client.check_authentication():
      log.warning("1Password authentication check failed")
      update_state(
        {
          "is_initialized": False,
          "connection_status": "error",
          "connection_error": "Not authenticated with 1Password CLI. Run 'op signin' first.",
        }
      )
      if set_state_fn:
        set_state_fn(get_state().__dict__)
      return

    set_client(client)
    update_state(
      {
        "is_initialized": True,
        "connection_status": "connected",
        "connection_error": None,
        "account": account,
        "vault": vault,
      }
    )

    if set_state_fn:
      set_state_fn(get_state().__dict__)

    log.info("1Password skill loaded successfully")
  except Exception as e:
    log.error("Failed to initialize 1Password client: %s", e)
    update_state(
      {
        "is_initialized": False,
        "connection_status": "error",
        "connection_error": str(e),
      }
    )
    if set_state_fn:
      set_state_fn(get_state().__dict__)


async def on_skill_unload() -> None:
  """Clean up on skill unload."""
  set_client(None)
  log.info("1Password skill unloaded")


async def on_skill_tick() -> None:
  """Periodic tick handler."""
  # Check connection status periodically
  state = get_state()
  if state and state.is_initialized:
    try:
      from .state.store import get_client

      op_client = get_client()
      if op_client:
        # Test authentication
        if not op_client.check_authentication():
          update_state(
            {
              "connection_status": "error",
              "connection_error": "Authentication expired. Run 'op signin' again.",
            }
          )
    except Exception:
      pass
