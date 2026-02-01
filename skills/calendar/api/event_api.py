"""
Event API layer.
"""

from __future__ import annotations

from typing import Any

from ..client.google_client import GoogleCalendarClient
from ..state.store import get_client


async def list_events(
  calendar_id: str = "primary",
  time_min: str | None = None,
  time_max: str | None = None,
  max_results: int = 50,
  single_events: bool = True,
  order_by: str = "startTime",
) -> list[dict[str, Any]]:
  """List events in a calendar."""
  client = get_client()
  if not client or not isinstance(client, GoogleCalendarClient):
    raise RuntimeError("Calendar client not initialized")
  
  return await client.list_events(
    calendar_id=calendar_id,
    time_min=time_min,
    time_max=time_max,
    max_results=max_results,
    single_events=single_events,
    order_by=order_by,
  )


async def get_event(calendar_id: str, event_id: str) -> dict[str, Any]:
  """Get event details."""
  client = get_client()
  if not client or not isinstance(client, GoogleCalendarClient):
    raise RuntimeError("Calendar client not initialized")
  
  return await client.get_event(calendar_id, event_id)


async def create_event(
  calendar_id: str,
  title: str,
  start: str,
  end: str,
  description: str | None = None,
  location: str | None = None,
  all_day: bool = False,
  attendees: list[str] | None = None,
  timezone: str | None = None,
) -> dict[str, Any]:
  """Create a new event."""
  client = get_client()
  if not client or not isinstance(client, GoogleCalendarClient):
    raise RuntimeError("Calendar client not initialized")
  
  return await client.create_event(
    calendar_id=calendar_id,
    title=title,
    start=start,
    end=end,
    description=description,
    location=location,
    all_day=all_day,
    attendees=attendees,
    timezone=timezone,
  )


async def update_event(
  calendar_id: str,
  event_id: str,
  title: str | None = None,
  start: str | None = None,
  end: str | None = None,
  description: str | None = None,
  location: str | None = None,
  all_day: bool | None = None,
  attendees: list[str] | None = None,
) -> dict[str, Any]:
  """Update an existing event."""
  client = get_client()
  if not client or not isinstance(client, GoogleCalendarClient):
    raise RuntimeError("Calendar client not initialized")
  
  return await client.update_event(
    calendar_id=calendar_id,
    event_id=event_id,
    title=title,
    start=start,
    end=end,
    description=description,
    location=location,
    all_day=all_day,
    attendees=attendees,
  )


async def delete_event(calendar_id: str, event_id: str) -> None:
  """Delete an event."""
  client = get_client()
  if not client or not isinstance(client, GoogleCalendarClient):
    raise RuntimeError("Calendar client not initialized")
  
  await client.delete_event(calendar_id, event_id)


async def search_events(
  calendar_id: str,
  query: str,
  time_min: str | None = None,
  time_max: str | None = None,
  max_results: int = 50,
) -> list[dict[str, Any]]:
  """Search for events."""
  client = get_client()
  if not client or not isinstance(client, GoogleCalendarClient):
    raise RuntimeError("Calendar client not initialized")
  
  return await client.search_events(
    calendar_id=calendar_id,
    query=query,
    time_min=time_min,
    time_max=time_max,
    max_results=max_results,
  )
