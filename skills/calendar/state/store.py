"""
In-process state store for the Calendar runtime skill.
"""

from __future__ import annotations

from typing import Any

from .types import CalendarState, initial_state

_state: CalendarState = initial_state()


def get_state() -> CalendarState:
  """Get current state."""
  return _state


def get_client() -> Any:
  """Get calendar client."""
  return _state.client


def set_client(client: Any) -> None:
  """Set calendar client."""
  global _state
  _state.client = client
  _state.is_initialized = client is not None
  if client:
    _state.connection_status = "connected"
  else:
    _state.connection_status = "disconnected"


def set_connection_status(status: str) -> None:
  """Set connection status."""
  global _state
  _state.connection_status = status
  if status != "error":
    _state.connection_error = None


def set_connection_error(error: str | None) -> None:
  """Set connection error."""
  global _state
  _state.connection_error = error
  if error:
    _state.connection_status = "error"


def set_provider(provider: str | None) -> None:
  """Set provider."""
  global _state
  _state.provider = provider


def reset_state() -> None:
  """Reset state to initial."""
  global _state
  _state = initial_state()
