"""
AsyncClient singleton wrapper for the Notion API.

Uses the `notion-client` package (https://github.com/ramnes/notion-sdk-py).
The client is created during setup validation and skill load.
"""

from __future__ import annotations

import logging

from notion_client import AsyncClient

log = logging.getLogger("skill.notion.client")

_client: AsyncClient | None = None


def create_client(token: str) -> AsyncClient:
  """Create and store the global AsyncClient singleton."""
  global _client
  _client = AsyncClient(auth=token)
  log.info("Notion AsyncClient created")
  return _client


def get_client() -> AsyncClient:
  """Return the global AsyncClient. Raises if not yet created."""
  if _client is None:
    raise RuntimeError("Notion client not initialized — call create_client() first")
  return _client


def close_client() -> None:
  """Clear the global client reference."""
  global _client
  _client = None
  log.info("Notion client cleared")
