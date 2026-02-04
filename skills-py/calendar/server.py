"""
Calendar skill server — lifecycle hooks and initialization.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from .client.google_client import GoogleCalendarClient
from .state.store import (
  reset_state,
  set_client,
  set_connection_error,
  set_connection_status,
  set_provider,
)

log = logging.getLogger("skill.calendar.server")


async def on_skill_load(params: dict[str, Any], set_state_fn: Any | None = None) -> None:
  """Initialize calendar client from config."""
  data_dir = params.get("dataDir", "")
  config = params.get("config", {})

  try:
    # Read config from data directory
    config_path = Path(data_dir) / "config.json"
    if config_path.exists():
      config = json.loads(config_path.read_text())

    provider = config.get("provider", "")

    if provider == "google":
      # Config structure: {"provider": "google", "credentials": {...}}
      credentials = config.get("credentials", {})
      if credentials:
        try:
          # Initialize Google Calendar client
          client = GoogleCalendarClient(credentials_data=credentials)
          if client.is_authenticated():
            set_client(client)
            set_provider("google")
            set_connection_status("connected")
            log.info("Google Calendar client initialized")
          else:
            set_connection_error("Failed to authenticate with Google Calendar")
            set_connection_status("error")
        except Exception as e:
          log.error("Failed to initialize Google Calendar client: %s", e)
          set_connection_error(f"Failed to initialize: {e!s}")
          set_connection_status("error")
      else:
        set_connection_error("No credentials found in config")
        set_connection_status("error")
    else:
      set_connection_error(f"Unsupported provider: {provider}")
      set_connection_status("error")

  except Exception as e:
    log.error("Failed to load calendar skill: %s", e)
    set_connection_error(str(e))
    set_connection_status("error")


async def on_skill_unload() -> None:
  """Clean up on skill unload."""
  reset_state()
  log.info("Calendar skill unloaded")


async def on_skill_tick() -> None:
  """Periodic tick handler."""
  # Could sync calendars, check for new events, etc.
  pass
