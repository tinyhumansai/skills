"""
State store for 1Password skill.
"""

from __future__ import annotations

from typing import Any

from .types import OnePasswordState

_state = OnePasswordState()
_client: Any = None


def get_state() -> OnePasswordState:
  """Get current state."""
  return _state


def get_client() -> Any:
  """Get 1Password client."""
  return _client


def set_client(client: Any) -> None:
  """Set 1Password client."""
  global _client
  _client = client
  if client:
    _state.is_initialized = True
    _state.connection_status = "connected"
  else:
    _state.is_initialized = False
    _state.connection_status = "disconnected"


def update_state(partial: dict) -> None:
  """Update state with partial data."""
  global _state
  for key, value in partial.items():
    if hasattr(_state, key):
      setattr(_state, key, value)
