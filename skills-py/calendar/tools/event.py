"""
Event management tools (6 tools).
"""

from __future__ import annotations

from mcp.types import Tool

event_tools: list[Tool] = [
  Tool(
    name="list_events",
    description="List events in a calendar within a time range",
    inputSchema={
      "type": "object",
      "properties": {
        "calendar_id": {
          "type": "string",
          "description": "Calendar ID (use 'primary' for primary calendar)",
          "default": "primary",
        },
        "time_min": {
          "type": "string",
          "description": "Lower bound (exclusive) for an event's end time (ISO 8601)",
        },
        "time_max": {
          "type": "string",
          "description": "Upper bound (exclusive) for an event's start time (ISO 8601)",
        },
        "max_results": {
          "type": "number",
          "description": "Maximum number of events to return",
          "default": 50,
        },
        "single_events": {
          "type": "boolean",
          "description": "Whether to expand recurring events into instances",
          "default": True,
        },
        "order_by": {
          "type": "string",
          "description": "Order results by: startTime or updated",
          "default": "startTime",
        },
      },
    },
  ),
  Tool(
    name="get_event",
    description="Get details about a specific event",
    inputSchema={
      "type": "object",
      "properties": {
        "calendar_id": {
          "type": "string",
          "description": "Calendar ID (use 'primary' for primary calendar)",
          "default": "primary",
        },
        "event_id": {
          "type": "string",
          "description": "Event ID",
        },
      },
      "required": ["event_id"],
    },
  ),
  Tool(
    name="create_event",
    description="Create a new calendar event",
    inputSchema={
      "type": "object",
      "properties": {
        "calendar_id": {
          "type": "string",
          "description": "Calendar ID (use 'primary' for primary calendar)",
          "default": "primary",
        },
        "title": {
          "type": "string",
          "description": "Event title/summary",
        },
        "start": {
          "type": "string",
          "description": "Event start time (ISO 8601 format, e.g., '2024-01-15T10:00:00-08:00')",
        },
        "end": {
          "type": "string",
          "description": "Event end time (ISO 8601 format)",
        },
        "description": {
          "type": "string",
          "description": "Event description",
        },
        "location": {
          "type": "string",
          "description": "Event location",
        },
        "all_day": {
          "type": "boolean",
          "description": "Whether this is an all-day event",
          "default": False,
        },
        "attendees": {
          "type": "array",
          "description": "List of attendee email addresses",
          "items": {"type": "string"},
        },
        "timezone": {
          "type": "string",
          "description": "Timezone for the event (e.g., 'America/Los_Angeles')",
        },
      },
      "required": ["title", "start", "end"],
    },
  ),
  Tool(
    name="update_event",
    description="Update an existing calendar event",
    inputSchema={
      "type": "object",
      "properties": {
        "calendar_id": {
          "type": "string",
          "description": "Calendar ID (use 'primary' for primary calendar)",
          "default": "primary",
        },
        "event_id": {
          "type": "string",
          "description": "Event ID",
        },
        "title": {
          "type": "string",
          "description": "Event title/summary",
        },
        "start": {
          "type": "string",
          "description": "Event start time (ISO 8601 format)",
        },
        "end": {
          "type": "string",
          "description": "Event end time (ISO 8601 format)",
        },
        "description": {
          "type": "string",
          "description": "Event description",
        },
        "location": {
          "type": "string",
          "description": "Event location",
        },
        "all_day": {
          "type": "boolean",
          "description": "Whether this is an all-day event",
        },
        "attendees": {
          "type": "array",
          "description": "List of attendee email addresses",
          "items": {"type": "string"},
        },
      },
      "required": ["event_id"],
    },
  ),
  Tool(
    name="delete_event",
    description="Delete a calendar event",
    inputSchema={
      "type": "object",
      "properties": {
        "calendar_id": {
          "type": "string",
          "description": "Calendar ID (use 'primary' for primary calendar)",
          "default": "primary",
        },
        "event_id": {
          "type": "string",
          "description": "Event ID",
        },
      },
      "required": ["event_id"],
    },
  ),
  Tool(
    name="search_events",
    description="Search for events by title, description, or location",
    inputSchema={
      "type": "object",
      "properties": {
        "calendar_id": {
          "type": "string",
          "description": "Calendar ID (use 'primary' for primary calendar)",
          "default": "primary",
        },
        "query": {
          "type": "string",
          "description": "Search query (searches title, description, location)",
        },
        "time_min": {
          "type": "string",
          "description": "Lower bound for event start time (ISO 8601)",
        },
        "time_max": {
          "type": "string",
          "description": "Upper bound for event start time (ISO 8601)",
        },
        "max_results": {
          "type": "number",
          "description": "Maximum number of results",
          "default": 50,
        },
      },
      "required": ["query"],
    },
  ),
]
