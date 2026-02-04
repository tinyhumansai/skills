"""
Google Calendar API client.
"""

from __future__ import annotations

import logging
from typing import Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

log = logging.getLogger("skill.calendar.client.google")


# Google Calendar API scopes
SCOPES = ["https://www.googleapis.com/auth/calendar"]


class GoogleCalendarClient:
  """Client for Google Calendar API."""

  def __init__(self, credentials_data: dict[str, Any] | None = None):
    """Initialize with credentials data (from config.json)."""
    self.service: Any = None
    self.credentials: Credentials | None = None

    if credentials_data:
      self._load_credentials(credentials_data)

  def _load_credentials(self, credentials_data: dict[str, Any]) -> None:
    """Load credentials from stored data.

    Expected format:
    - If credentials_data contains 'token', 'refresh_token', etc. (authorized user info)
    - Or if it contains 'installed' or 'web' (OAuth client config), we need to complete OAuth flow
    """
    try:
      # Check if this is authorized user info (already authenticated)
      if "token" in credentials_data or "refresh_token" in credentials_data:
        creds = Credentials.from_authorized_user_info(credentials_data)

        # Refresh if expired
        if creds.expired and creds.refresh_token:
          creds.refresh(Request())

        self.credentials = creds
        self.service = build("calendar", "v3", credentials=creds)
      else:
        # This is OAuth client config, not authorized credentials
        # In a real implementation, you'd need to complete OAuth flow
        raise ValueError(
          "OAuth flow not yet implemented. Please provide authorized user credentials."
        )
    except Exception as e:
      log.error("Failed to load Google credentials: %s", e)
      raise

  def is_authenticated(self) -> bool:
    """Check if client is authenticated."""
    return self.service is not None and self.credentials is not None

  def get_credentials_dict(self) -> dict[str, Any]:
    """Get credentials as dict for storage."""
    if not self.credentials:
      return {}
    return {
      "token": self.credentials.token,
      "refresh_token": self.credentials.refresh_token,
      "token_uri": self.credentials.token_uri,
      "client_id": self.credentials.client_id,
      "client_secret": self.credentials.client_secret,
      "scopes": self.credentials.scopes,
    }

  async def list_calendars(self, show_hidden: bool = False) -> list[dict[str, Any]]:
    """List all calendars."""
    if not self.service:
      raise RuntimeError("Not authenticated")

    try:
      result = self.service.calendarList().list(showHidden=show_hidden).execute()
      return result.get("items", [])
    except HttpError as e:
      log.error("Failed to list calendars: %s", e)
      raise

  async def get_calendar(self, calendar_id: str) -> dict[str, Any]:
    """Get calendar details."""
    if not self.service:
      raise RuntimeError("Not authenticated")

    try:
      return self.service.calendars().get(calendarId=calendar_id).execute()
    except HttpError as e:
      log.error("Failed to get calendar %s: %s", calendar_id, e)
      raise

  async def list_events(
    self,
    calendar_id: str = "primary",
    time_min: str | None = None,
    time_max: str | None = None,
    max_results: int = 50,
    single_events: bool = True,
    order_by: str = "startTime",
  ) -> list[dict[str, Any]]:
    """List events in a calendar."""
    if not self.service:
      raise RuntimeError("Not authenticated")

    try:
      events_result = (
        self.service.events()
        .list(
          calendarId=calendar_id,
          timeMin=time_min,
          timeMax=time_max,
          maxResults=max_results,
          singleEvents=single_events,
          orderBy=order_by,
        )
        .execute()
      )
      return events_result.get("items", [])
    except HttpError as e:
      log.error("Failed to list events: %s", e)
      raise

  async def get_event(self, calendar_id: str, event_id: str) -> dict[str, Any]:
    """Get event details."""
    if not self.service:
      raise RuntimeError("Not authenticated")

    try:
      return self.service.events().get(calendarId=calendar_id, eventId=event_id).execute()
    except HttpError as e:
      if e.resp.status == 404:
        raise ValueError(f"Event {event_id} not found")
      log.error("Failed to get event: %s", e)
      raise

  async def create_event(
    self,
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
    if not self.service:
      raise RuntimeError("Not authenticated")

    event_body: dict[str, Any] = {
      "summary": title,
    }

    # Set start/end times
    if all_day:
      event_body["start"] = {"date": start.split("T")[0]}
      event_body["end"] = {"date": end.split("T")[0]}
    else:
      event_body["start"] = {"dateTime": start, "timeZone": timezone}
      event_body["end"] = {"dateTime": end, "timeZone": timezone}

    if description:
      event_body["description"] = description
    if location:
      event_body["location"] = location
    if attendees:
      event_body["attendees"] = [{"email": email} for email in attendees]

    try:
      return self.service.events().insert(calendarId=calendar_id, body=event_body).execute()
    except HttpError as e:
      log.error("Failed to create event: %s", e)
      raise

  async def update_event(
    self,
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
    if not self.service:
      raise RuntimeError("Not authenticated")

    # Get existing event first
    try:
      event = await self.get_event(calendar_id, event_id)
    except ValueError:
      raise

    # Update fields
    if title is not None:
      event["summary"] = title
    if description is not None:
      event["description"] = description
    if location is not None:
      event["location"] = location
    if attendees is not None:
      event["attendees"] = [{"email": email} for email in attendees]

    # Update start/end times
    if start is not None or end is not None or all_day is not None:
      if all_day is True or (all_day is None and "date" in event.get("start", {})):
        # All-day event
        if start:
          event["start"] = {"date": start.split("T")[0]}
        if end:
          event["end"] = {"date": end.split("T")[0]}
      else:
        # Timed event
        if start:
          event["start"] = {"dateTime": start, "timeZone": event.get("start", {}).get("timeZone")}
        if end:
          event["end"] = {"dateTime": end, "timeZone": event.get("end", {}).get("timeZone")}

    try:
      return (
        self.service.events().update(calendarId=calendar_id, eventId=event_id, body=event).execute()
      )
    except HttpError as e:
      log.error("Failed to update event: %s", e)
      raise

  async def delete_event(self, calendar_id: str, event_id: str) -> None:
    """Delete an event."""
    if not self.service:
      raise RuntimeError("Not authenticated")

    try:
      self.service.events().delete(calendarId=calendar_id, eventId=event_id).execute()
    except HttpError as e:
      if e.resp.status == 404:
        raise ValueError(f"Event {event_id} not found")
      log.error("Failed to delete event: %s", e)
      raise

  async def search_events(
    self,
    calendar_id: str,
    query: str,
    time_min: str | None = None,
    time_max: str | None = None,
    max_results: int = 50,
  ) -> list[dict[str, Any]]:
    """Search for events by query."""
    if not self.service:
      raise RuntimeError("Not authenticated")

    try:
      events_result = (
        self.service.events()
        .list(
          calendarId=calendar_id,
          q=query,
          timeMin=time_min,
          timeMax=time_max,
          maxResults=max_results,
          singleEvents=True,
          orderBy="startTime",
        )
        .execute()
      )
      return events_result.get("items", [])
    except HttpError as e:
      log.error("Failed to search events: %s", e)
      raise
