"""
1Password CLI client for accessing local vault.
"""

from __future__ import annotations

import json
import logging
import subprocess
from typing import Any

log = logging.getLogger("skill.onepassword.client")


class OnePasswordClient:
  """Client for interacting with 1Password CLI."""

  def __init__(self, account: str | None = None, vault: str | None = None):
    """Initialize client with optional account and vault."""
    self.account = account
    self.vault = vault
    self._session_token: str | None = None

  def _run_op_command(self, args: list[str], capture_output: bool = True) -> dict[str, Any]:
    """Run an op CLI command and return parsed JSON output."""
    cmd = ["op", *args]

    # Add account if specified
    if self.account:
      cmd.extend(["--account", self.account])

    # Add vault if specified
    if self.vault:
      cmd.extend(["--vault", self.vault])

    # Add session token if available
    if self._session_token:
      cmd.extend(["--session", self._session_token])

    try:
      result = subprocess.run(
        cmd,
        capture_output=capture_output,
        text=True,
        check=True,
        timeout=30,
      )

      if capture_output and result.stdout:
        try:
          return json.loads(result.stdout)
        except json.JSONDecodeError:
          # Some commands return non-JSON (like op read)
          return {"output": result.stdout.strip()}

      return {}
    except subprocess.TimeoutExpired:
      raise RuntimeError("1Password CLI command timed out")
    except subprocess.CalledProcessError as e:
      error_msg = e.stderr or e.stdout or "Unknown error"
      log.error("op command failed: %s", error_msg)
      raise RuntimeError(f"1Password CLI error: {error_msg}")
    except FileNotFoundError:
      # TODO: Automate installation of 1Password CLI (op)
      # Could detect OS and install via: brew (macOS), apt/yum (Linux), winget/choco (Windows)
      raise RuntimeError("1Password CLI (op) not found. Please install 1Password CLI.")

  def check_authentication(self) -> bool:
    """Check if user is authenticated with 1Password."""
    try:
      self._run_op_command(["whoami"])
      return True
    except Exception:
      return False

  def list_items(
    self, vault: str | None = None, categories: list[str] | None = None
  ) -> list[dict[str, Any]]:
    """List items in vault."""
    args = ["item", "list", "--format", "json"]

    if vault:
      args.extend(["--vault", vault])

    if categories:
      for category in categories:
        args.extend(["--categories", category])

    result = self._run_op_command(args)

    if isinstance(result, list):
      return result
    return []

  def get_item(
    self, item_id: str | None = None, item_name: str | None = None, vault: str | None = None
  ) -> dict[str, Any]:
    """Get item details by ID or name."""
    args = ["item", "get", "--format", "json"]

    if item_id:
      args.append(item_id)
    elif item_name:
      args.append(item_name)
    else:
      raise ValueError("Either item_id or item_name must be provided")

    if vault:
      args.extend(["--vault", vault])

    result = self._run_op_command(args)
    return result if isinstance(result, dict) else {}

  def get_field(
    self,
    item_id: str | None = None,
    item_name: str | None = None,
    field_label: str | None = None,
    vault: str | None = None,
  ) -> str:
    """Get a specific field value from an item."""
    if not field_label:
      raise ValueError("field_label is required")

    # First get the item
    item = self.get_item(item_id=item_id, item_name=item_name, vault=vault)

    # Find the field
    fields = item.get("fields", [])
    for field in fields:
      if field.get("label", "").lower() == field_label.lower():
        return field.get("value", "")

    raise ValueError(f"Field '{field_label}' not found in item")

  def get_password(
    self, item_id: str | None = None, item_name: str | None = None, vault: str | None = None
  ) -> str:
    """Get password field from an item."""
    return self.get_field(item_id=item_id, item_name=item_name, field_label="password", vault=vault)

  def search_items(self, query: str, vault: str | None = None) -> list[dict[str, Any]]:
    """Search for items by query."""
    args = ["item", "list", "--format", "json"]

    if vault:
      args.extend(["--vault", vault])

    # Get all items and filter by query
    all_items = self.list_items(vault=vault)

    query_lower = query.lower()
    matching_items = []

    for item in all_items:
      title = item.get("title", "").lower()
      if query_lower in title:
        matching_items.append(item)

    return matching_items
