"""
Thin persistence wrapper for Telegram update state tracking.

Stores pts/qts/date/seq in SQLite for resumable sync across restarts.
Also tracks per-channel pts for channel-specific gap filling.
"""

from __future__ import annotations

import logging

from ..db.connection import get_db
from ..db.queries import (
  get_all_channel_pts as db_get_all_channel_pts,
)
from ..db.queries import (
  get_channel_pts as db_get_channel_pts,
)
from ..db.queries import (
  get_update_state as db_get_update_state,
)
from ..db.queries import (
  set_channel_pts as db_set_channel_pts,
)
from ..db.queries import (
  set_update_state as db_set_update_state,
)
from ..state import store

log = logging.getLogger("skill.telegram.sync.update_state")


async def save_update_state(pts: int, qts: int, date: int, seq: int) -> None:
  """Persist global update state to SQLite and update in-memory store."""
  try:
    db = await get_db()
    await db_set_update_state(db, pts, qts, date, seq)
    store.set_sync_pts(pts, qts, date, seq)
    log.debug("Saved update state: pts=%d qts=%d date=%d seq=%d", pts, qts, date, seq)
  except Exception:
    log.exception("Failed to save update state")


async def load_update_state() -> dict[str, int] | None:
  """Load global update state from SQLite. Returns None if no state saved."""
  try:
    db = await get_db()
    state = await db_get_update_state(db)
    if state:
      store.set_sync_pts(state["pts"], state["qts"], state["date"], state["seq"])
    return state
  except Exception:
    log.exception("Failed to load update state")
    return None


async def save_channel_pts(channel_id: str, pts: int) -> None:
  """Persist a single channel's pts to SQLite."""
  try:
    db = await get_db()
    await db_set_channel_pts(db, channel_id, pts)
  except Exception:
    log.exception("Failed to save channel pts for %s", channel_id)


async def load_channel_pts(channel_id: str) -> int | None:
  """Load a single channel's pts from SQLite."""
  try:
    db = await get_db()
    return await db_get_channel_pts(db, channel_id)
  except Exception:
    log.exception("Failed to load channel pts for %s", channel_id)
    return None


async def load_all_channel_pts() -> dict[str, int]:
  """Load all saved channel pts from SQLite."""
  try:
    db = await get_db()
    return await db_get_all_channel_pts(db)
  except Exception:
    log.exception("Failed to load all channel pts")
    return {}


async def save_channel_pts_batch(channel_pts: dict[str, int]) -> None:
  """Persist multiple channel pts in one go."""
  if not channel_pts:
    return
  try:
    db = await get_db()
    for channel_id, pts in channel_pts.items():
      await db_set_channel_pts(db, channel_id, pts)
  except Exception:
    log.exception("Failed to save channel pts batch")
