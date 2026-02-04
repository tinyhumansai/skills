"""
In-process state store for the Otter.ai runtime skill.

Uses immutable Pydantic models. After each mutation, listeners are notified.
"""

from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING

from .types import (
  OtterConnectionStatus,
  OtterSpeaker,
  OtterSpeech,
  OtterState,
  OtterUser,
  initial_state,
)

if TYPE_CHECKING:
  from collections.abc import Callable

_state: OtterState = initial_state()
_listeners: list[Callable[[], None]] = []


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def get_state() -> OtterState:
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


def set_connection_status(status: OtterConnectionStatus) -> None:
  global _state
  updates: dict = {"connection_status": status}
  if status != "error":
    updates["connection_error"] = None
  _state = _state.model_copy(update=updates)
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


def set_current_user(user: OtterUser | None) -> None:
  global _state
  _state = _state.model_copy(update={"current_user": user})
  _notify()


# ---------------------------------------------------------------------------
# Speeches
# ---------------------------------------------------------------------------


def set_speeches(speeches: dict[str, OtterSpeech], order: list[str]) -> None:
  global _state
  _state = _state.model_copy(
    update={
      "speeches": speeches,
      "speeches_order": order,
      "total_meetings": len(order),
    }
  )
  _notify()


def add_speech(speech: OtterSpeech) -> None:
  global _state
  speeches = {**_state.speeches, speech.speech_id: speech}
  order = (
    _state.speeches_order
    if speech.speech_id in _state.speeches_order
    else [speech.speech_id, *_state.speeches_order]
  )
  _state = _state.model_copy(
    update={
      "speeches": speeches,
      "speeches_order": order,
      "total_meetings": len(order),
    }
  )
  _notify()


def update_speech(speech_id: str, updates: dict) -> None:
  global _state
  existing = _state.speeches.get(speech_id)
  if not existing:
    return
  updated = existing.model_copy(update=updates)
  _state = _state.model_copy(update={"speeches": {**_state.speeches, speech_id: updated}})
  _notify()


def get_speech(speech_id: str) -> OtterSpeech | None:
  return _state.speeches.get(speech_id)


# ---------------------------------------------------------------------------
# Speakers
# ---------------------------------------------------------------------------


def set_speakers(speakers: dict[str, OtterSpeaker]) -> None:
  global _state
  _state = _state.model_copy(update={"speakers": speakers})
  _notify()


def add_speaker(speaker: OtterSpeaker) -> None:
  global _state
  speakers = {**_state.speakers, speaker.speaker_id: speaker}
  _state = _state.model_copy(update={"speakers": speakers})
  _notify()


# ---------------------------------------------------------------------------
# Sync
# ---------------------------------------------------------------------------


def set_sync_status(is_syncing: bool | None = None, last_sync: float | None = None) -> None:
  global _state
  updates: dict = {}
  if is_syncing is not None:
    updates["is_syncing"] = is_syncing
  if last_sync is not None:
    updates["last_sync"] = last_sync
  _state = _state.model_copy(update=updates)
  _notify()


# ---------------------------------------------------------------------------
# Reset
# ---------------------------------------------------------------------------


def reset_state() -> None:
  global _state
  _state = initial_state()
  _notify()
