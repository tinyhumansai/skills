"""
IMAP folder operations API.
"""

from __future__ import annotations

import logging
from typing import Any

from ..client.imap_client import get_imap_client

log = logging.getLogger("skill.email.api.folder")


async def list_folders(pattern: str | None = None) -> list[dict[str, Any]]:
  """List all IMAP folders."""
  client = get_imap_client()
  if not client:
    raise RuntimeError("IMAP client not initialized")
  if not await client.ensure_connected():
    raise RuntimeError("IMAP not connected")

  folders = await client.list_folders()
  if pattern:
    pattern_lower = pattern.lower()
    folders = [f for f in folders if pattern_lower in f["name"].lower()]
  return folders


async def get_folder_status(folder: str) -> dict[str, Any]:
  """Get message counts for a folder."""
  client = get_imap_client()
  if not client:
    raise RuntimeError("IMAP client not initialized")
  if not await client.ensure_connected():
    raise RuntimeError("IMAP not connected")

  status = await client.select_folder(folder)
  if not status:
    raise RuntimeError(f"Cannot select folder: {folder}")
  return status


async def create_folder(folder: str) -> bool:
  """Create a new IMAP folder."""
  client = get_imap_client()
  if not client:
    raise RuntimeError("IMAP client not initialized")
  if not await client.ensure_connected():
    raise RuntimeError("IMAP not connected")

  return await client.create_folder(folder)


async def rename_folder(old_name: str, new_name: str) -> bool:
  """Rename an IMAP folder."""
  client = get_imap_client()
  if not client:
    raise RuntimeError("IMAP client not initialized")
  if not await client.ensure_connected():
    raise RuntimeError("IMAP not connected")

  return await client.rename_folder(old_name, new_name)


async def delete_folder(folder: str) -> bool:
  """Delete an IMAP folder."""
  client = get_imap_client()
  if not client:
    raise RuntimeError("IMAP client not initialized")
  if not await client.ensure_connected():
    raise RuntimeError("IMAP not connected")

  return await client.delete_folder(folder)
