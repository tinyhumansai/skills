"""
Calendar API layer.
"""

from __future__ import annotations

from typing import Any

from ..client.google_client import GoogleCalendarClient
from ..state.store import get_client


async def list_calendars(show_hidden: bool = False) -> list[dict[str, Any]]:
  """List all calendars."""
  client = get_client()
  if not client or not isinstance(client, GoogleCalendarClient):
    raise RuntimeError("Calendar client not initialized")

  return await client.list_calendars(show_hidden=show_hidden)


async def get_calendar(calendar_id: str) -> dict[str, Any]:
  """Get calendar details."""
  client = get_client()
  if not client or not isinstance(client, GoogleCalendarClient):
    raise RuntimeError("Calendar client not initialized")

  return await client.get_calendar(calendar_id)
