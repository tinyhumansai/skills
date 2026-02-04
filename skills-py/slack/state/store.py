"""
State store for Slack skill — connection status, workspace info, etc.
"""

from __future__ import annotations

from dataclasses import dataclass

from pydantic import BaseModel


class SlackUser(BaseModel):
  """Slack user info."""

  id: str
  name: str
  team_id: str | None = None


@dataclass
class SlackState:
  """Slack skill state."""

  connection_status: str = "disconnected"  # disconnected, connecting, connected
  is_initialized: bool = False
  connection_error: str | None = None
  current_user: SlackUser | None = None
  workspace_name: str | None = None
  workspace_id: str | None = None


_state = SlackState()


def get_state() -> SlackState:
  """Get current state."""
  return _state


def set_connection_status(status: str) -> None:
  """Set connection status."""
  _state.connection_status = status


def set_connection_error(error: str | None) -> None:
  """Set connection error."""
  _state.connection_error = error


def set_is_initialized(value: bool) -> None:
  """Set initialization status."""
  _state.is_initialized = value


def set_current_user(user: SlackUser | None) -> None:
  """Set current user."""
  _state.current_user = user


def set_workspace_info(name: str | None, workspace_id: str | None) -> None:
  """Set workspace info."""
  _state.workspace_name = name
  _state.workspace_id = workspace_id


def reset_state() -> None:
  """Reset state to defaults."""
  global _state
  _state = SlackState()
