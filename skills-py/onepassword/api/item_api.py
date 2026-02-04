"""
1Password item API layer.
"""

from __future__ import annotations

from typing import Any

from ..state.store import get_client


async def list_items(
  vault: str | None = None, categories: list[str] | None = None
) -> list[dict[str, Any]]:
  """List items in vault."""
  client = get_client()
  if not client:
    raise RuntimeError("1Password client not initialized. Please complete setup.")

  return client.list_items(vault=vault, categories=categories)


async def get_item(
  item_id: str | None = None, item_name: str | None = None, vault: str | None = None
) -> dict[str, Any]:
  """Get item details."""
  client = get_client()
  if not client:
    raise RuntimeError("1Password client not initialized. Please complete setup.")

  return client.get_item(item_id=item_id, item_name=item_name, vault=vault)


async def get_field(
  item_id: str | None = None,
  item_name: str | None = None,
  field_label: str | None = None,
  vault: str | None = None,
) -> str:
  """Get a specific field value from an item."""
  client = get_client()
  if not client:
    raise RuntimeError("1Password client not initialized. Please complete setup.")

  return client.get_field(
    item_id=item_id, item_name=item_name, field_label=field_label, vault=vault
  )


async def get_password(
  item_id: str | None = None, item_name: str | None = None, vault: str | None = None
) -> str:
  """Get password from an item."""
  client = get_client()
  if not client:
    raise RuntimeError("1Password client not initialized. Please complete setup.")

  return client.get_password(item_id=item_id, item_name=item_name, vault=vault)


async def search_items(query: str, vault: str | None = None) -> list[dict[str, Any]]:
  """Search for items."""
  client = get_client()
  if not client:
    raise RuntimeError("1Password client not initialized. Please complete setup.")

  return client.search_items(query=query, vault=vault)
