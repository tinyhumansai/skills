"""
Calendar state types.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class CalendarState:
  """In-memory state for calendar skill."""

  is_initialized: bool = False
  connection_status: str = "disconnected"  # disconnected, connected, error
  connection_error: str | None = None
  provider: str | None = None  # google, outlook, caldav
  client: Any = None  # Calendar client instance


def initial_state() -> CalendarState:
  """Create initial state."""
  return CalendarState()
