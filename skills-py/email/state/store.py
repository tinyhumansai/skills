"""
In-process state store for the Email runtime skill.

State mutations are synchronous. After each mutation, listeners are notified.
"""

from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING

from .types import (
  EmailAccount,
  EmailConnectionStatus,
  EmailFolder,
  EmailState,
  initial_state,
)

if TYPE_CHECKING:
  from collections.abc import Callable

_state: EmailState = initial_state()
_listeners: list[Callable[[], None]] = []


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def get_state() -> EmailState:
  return _state


def subscribe(listener: Callable[[], None]) -> Callable[[], None]:
  _listeners.append(listener)

  def unsubscribe() -> None:
    with contextlib.suppress(ValueError):
      _listeners.remove(listener)

  return unsubscribe


def _notify() -> None:
  for fn in _listeners:
    fn()


# ---------------------------------------------------------------------------
# Connection
# ---------------------------------------------------------------------------


def set_connection_status(status: EmailConnectionStatus) -> None:
  global _state
  _state = _state.model_copy(update={"connection_status": status})
  if status != "error":
    _state = _state.model_copy(update={"connection_error": None})
  _notify()


def set_connection_error(error: str | None) -> None:
  global _state
  updates: dict = {"connection_error": error}
  if error:
    updates["connection_status"] = "error"
  _state = _state.model_copy(update=updates)
  _notify()


def set_is_initialized(value: bool) -> None:
  global _state
  _state = _state.model_copy(update={"is_initialized": value})
  _notify()


def set_account(account: EmailAccount | None) -> None:
  global _state
  _state = _state.model_copy(update={"account": account})
  _notify()


# ---------------------------------------------------------------------------
# Folders
# ---------------------------------------------------------------------------


def set_folders(folders: dict[str, EmailFolder]) -> None:
  global _state
  total_unread = sum(f.unseen_messages for f in folders.values())
  _state = _state.model_copy(update={"folders": folders, "total_unread": total_unread})
  _notify()


def update_folder(name: str, folder: EmailFolder) -> None:
  global _state
  folders = {**_state.folders, name: folder}
  total_unread = sum(f.unseen_messages for f in folders.values())
  _state = _state.model_copy(update={"folders": folders, "total_unread": total_unread})
  _notify()


def get_folder(name: str) -> EmailFolder | None:
  return _state.folders.get(name)


# ---------------------------------------------------------------------------
# Sync
# ---------------------------------------------------------------------------


def set_sync_status(is_syncing: bool) -> None:
  global _state
  _state = _state.model_copy(update={"is_syncing": is_syncing})
  _notify()


def set_last_sync(timestamp: float) -> None:
  global _state
  _state = _state.model_copy(update={"last_sync": timestamp})
  _notify()


# ---------------------------------------------------------------------------
# Reset
# ---------------------------------------------------------------------------


def reset_state() -> None:
  global _state
  _state = initial_state()
  _notify()
