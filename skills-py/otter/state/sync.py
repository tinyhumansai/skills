"""
Push state summary to the host via reverse RPC.

Debounced to avoid flooding the host with updates.
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any

from .store import get_state, subscribe
from .types import OtterHostState

if TYPE_CHECKING:
  from collections.abc import Awaitable, Callable

log = logging.getLogger("skill.otter.sync")

_push_to_host: Callable[[dict[str, Any]], Awaitable[None]] | None = None
_debounce_handle: asyncio.TimerHandle | None = None
DEBOUNCE_S = 0.1


def init_host_sync(
  set_state: Callable[[dict[str, Any]], Awaitable[None]],
) -> None:
  """Initialize the sync-to-host bridge."""
  global _push_to_host
  _push_to_host = set_state

  subscribe(_on_state_change)

  # Push initial state
  loop = asyncio.get_event_loop()
  loop.call_soon(lambda: asyncio.ensure_future(_push_host_state()))


def _on_state_change() -> None:
  global _debounce_handle
  loop = asyncio.get_event_loop()
  if _debounce_handle is not None:
    _debounce_handle.cancel()
  _debounce_handle = loop.call_later(DEBOUNCE_S, lambda: asyncio.ensure_future(_push_host_state()))


def _build_host_state() -> OtterHostState:
  s = get_state()
  return OtterHostState(
    connection_status=s.connection_status,
    is_initialized=s.is_initialized,
    current_user=s.current_user,
    total_meetings=s.total_meetings,
    last_sync=s.last_sync,
  )


async def _push_host_state() -> None:
  if _push_to_host is None:
    return
  try:
    host_state = _build_host_state()
    await _push_to_host(host_state.model_dump())
  except Exception:
    log.exception("Failed to push state to host")
