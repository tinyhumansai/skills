"""
Async IMAP client wrapper using aioimaplib.

Singleton pattern with automatic reconnection.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import re
from typing import TYPE_CHECKING, Any

from aioimaplib import IMAP4, IMAP4_SSL

from .parsers import parse_fetch_response, parse_full_message

if TYPE_CHECKING:
  from ..state.types import ParsedEmail

log = logging.getLogger("skill.email.client.imap")

_client: ImapClient | None = None


class ImapClient:
  """Async IMAP client with connection management."""

  def __init__(
    self,
    host: str,
    port: int,
    use_ssl: bool = True,
  ) -> None:
    self.host = host
    self.port = port
    self.use_ssl = use_ssl
    self._imap: IMAP4_SSL | IMAP4 | None = None
    self._email: str = ""
    self._password: str = ""
    self._current_folder: str | None = None
    self._lock = asyncio.Lock()
    self.is_connected: bool = False

  async def connect(self, email: str, password: str) -> bool:
    """Connect and authenticate."""
    self._email = email
    self._password = password
    return await self._do_connect()

  async def _do_connect(self) -> bool:
    """Internal connect logic."""
    async with self._lock:
      try:
        if self.use_ssl:
          self._imap = IMAP4_SSL(host=self.host, port=self.port)
        else:
          self._imap = IMAP4(host=self.host, port=self.port)

        await self._imap.wait_hello_from_server()
        response = await self._imap.login(self._email, self._password)
        if response.result != "OK":
          log.error("IMAP login failed: %s", response.lines)
          self.is_connected = False
          return False

        self.is_connected = True
        self._current_folder = None
        log.info("IMAP connected to %s as %s", self.host, self._email)
        return True
      except Exception:
        log.exception("IMAP connection failed")
        self.is_connected = False
        return False

  async def ensure_connected(self) -> bool:
    """Ensure the client is connected, reconnecting if needed."""
    if self.is_connected and self._imap:
      try:
        response = await self._imap.noop()
        if response.result == "OK":
          return True
      except Exception:
        pass
      self.is_connected = False

    if self._email and self._password:
      return await self._do_connect()
    return False

  async def disconnect(self) -> None:
    """Disconnect from the server."""
    if self._imap:
      with contextlib.suppress(Exception):
        await self._imap.logout()
      self._imap = None
      self.is_connected = False
      self._current_folder = None

  async def noop(self) -> bool:
    """Send NOOP keepalive."""
    if not self._imap or not self.is_connected:
      return False
    try:
      response = await self._imap.noop()
      return response.result == "OK"
    except Exception:
      self.is_connected = False
      return False

  async def select_folder(self, folder: str = "INBOX") -> dict[str, Any] | None:
    """Select a folder, caching to avoid redundant SELECT calls."""
    if not await self.ensure_connected():
      return None

    if self._current_folder == folder:
      # Re-examine to get fresh counts
      response = await self._imap.examine(folder)
    else:
      response = await self._imap.select(folder)

    if response.result != "OK":
      log.error("Failed to select folder %s: %s", folder, response.lines)
      return None

    self._current_folder = folder
    return _parse_select_response(response.lines)

  async def list_folders(self) -> list[dict[str, str]]:
    """List all IMAP folders."""
    if not await self.ensure_connected():
      return []

    response = await self._imap.list('""', "*")
    if response.result != "OK":
      return []

    folders: list[dict[str, str]] = []
    for line in response.lines:
      if not isinstance(line, str) or not line.strip():
        continue
      parsed = _parse_list_response(line)
      if parsed:
        folders.append(parsed)
    return folders

  async def search_uids_since(self, since_uid: int) -> list[int]:
    """Search for UIDs >= since_uid."""
    if not self._imap or not self.is_connected:
      return []

    try:
      response = await self._imap.uid("search", f"UID {since_uid}:*")
      if response.result != "OK":
        return []

      uids: list[int] = []
      for line in response.lines:
        if isinstance(line, str) and line.strip():
          for part in line.split():
            if part.isdigit():
              uid = int(part)
              if uid >= since_uid:
                uids.append(uid)
      return sorted(uids)
    except Exception:
      log.exception("Error searching UIDs")
      return []

  async def search_messages(
    self,
    criteria: str = "ALL",
  ) -> list[int]:
    """Search messages with IMAP criteria, return UIDs."""
    if not self._imap or not self.is_connected:
      return []

    try:
      response = await self._imap.uid("search", criteria)
      if response.result != "OK":
        return []

      uids: list[int] = []
      for line in response.lines:
        if isinstance(line, str) and line.strip():
          for part in line.split():
            if part.isdigit():
              uids.append(int(part))
      return sorted(uids)
    except Exception:
      log.exception("Error searching messages")
      return []

  async def fetch_envelopes(self, uids: list[int]) -> list[ParsedEmail]:
    """Fetch envelope + flags + bodystructure for given UIDs."""
    if not self._imap or not self.is_connected or not uids:
      return []

    uid_str = ",".join(str(u) for u in uids)
    try:
      response = await self._imap.uid(
        "fetch",
        uid_str,
        "(UID FLAGS ENVELOPE BODYSTRUCTURE RFC822.SIZE)",
      )
      if response.result != "OK":
        return []
      return parse_fetch_response(response.lines, uids)
    except Exception:
      log.exception("Error fetching envelopes")
      return []

  async def fetch_full_message(self, uid: int) -> ParsedEmail | None:
    """Fetch the full RFC822 message for a UID."""
    if not self._imap or not self.is_connected:
      return None

    try:
      response = await self._imap.uid("fetch", str(uid), "(UID FLAGS RFC822)")
      if response.result != "OK":
        return None
      return parse_full_message(response.lines, uid)
    except Exception:
      log.exception("Error fetching message UID %d", uid)
      return None

  async def store_flags(
    self,
    uids: list[int],
    flags: str,
    action: str = "+FLAGS",
  ) -> bool:
    """Set/unset flags on messages."""
    if not self._imap or not self.is_connected:
      return False

    uid_str = ",".join(str(u) for u in uids)
    try:
      response = await self._imap.uid("store", uid_str, action, flags)
      return response.result == "OK"
    except Exception:
      log.exception("Error storing flags")
      return False

  async def copy_messages(self, uids: list[int], dest_folder: str) -> bool:
    """Copy messages to another folder."""
    if not self._imap or not self.is_connected:
      return False

    uid_str = ",".join(str(u) for u in uids)
    try:
      response = await self._imap.uid("copy", uid_str, dest_folder)
      return response.result == "OK"
    except Exception:
      log.exception("Error copying messages")
      return False

  async def move_messages(self, uids: list[int], dest_folder: str) -> bool:
    """Move messages to another folder (copy + delete)."""
    if not await self.copy_messages(uids, dest_folder):
      return False
    return await self.store_flags(uids, r"(\Deleted)", "+FLAGS")

  async def expunge(self) -> bool:
    """Expunge deleted messages."""
    if not self._imap or not self.is_connected:
      return False
    try:
      response = await self._imap.expunge()
      return response.result == "OK"
    except Exception:
      log.exception("Error expunging")
      return False

  async def create_folder(self, folder: str) -> bool:
    """Create a new folder."""
    if not self._imap or not self.is_connected:
      return False
    try:
      response = await self._imap.create(folder)
      return response.result == "OK"
    except Exception:
      log.exception("Error creating folder %s", folder)
      return False

  async def rename_folder(self, old_name: str, new_name: str) -> bool:
    """Rename a folder."""
    if not self._imap or not self.is_connected:
      return False
    try:
      response = await self._imap.rename(old_name, new_name)
      return response.result == "OK"
    except Exception:
      log.exception("Error renaming folder %s -> %s", old_name, new_name)
      return False

  async def delete_folder(self, folder: str) -> bool:
    """Delete a folder."""
    if not self._imap or not self.is_connected:
      return False
    try:
      response = await self._imap.delete(folder)
      return response.result == "OK"
    except Exception:
      log.exception("Error deleting folder %s", folder)
      return False

  async def append_message(self, folder: str, message: bytes, flags: str = "") -> bool:
    """Append a message to a folder (for saving drafts)."""
    if not self._imap or not self.is_connected:
      return False
    try:
      response = await self._imap.append(folder, message, flags)
      return response.result == "OK"
    except Exception:
      log.exception("Error appending message to %s", folder)
      return False


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------


def create_imap_client(host: str, port: int, use_ssl: bool = True) -> ImapClient:
  """Create and register the singleton IMAP client."""
  global _client
  _client = ImapClient(host, port, use_ssl)
  return _client


def get_imap_client() -> ImapClient | None:
  """Get the singleton IMAP client."""
  return _client


# ---------------------------------------------------------------------------
# Response parsing helpers
# ---------------------------------------------------------------------------


def _parse_select_response(lines: list[str]) -> dict[str, Any]:
  """Parse SELECT/EXAMINE response for counts and UIDVALIDITY."""
  result: dict[str, Any] = {}
  for line in lines:
    if not isinstance(line, str):
      continue
    line_upper = line.upper()
    # Parse "N EXISTS"
    m = re.search(r"(\d+)\s+EXISTS", line_upper)
    if m:
      result["exists"] = int(m.group(1))
    # Parse "N RECENT"
    m = re.search(r"(\d+)\s+RECENT", line_upper)
    if m:
      result["recent"] = int(m.group(1))
    # Parse "UIDVALIDITY N"
    m = re.search(r"UIDVALIDITY\s+(\d+)", line_upper)
    if m:
      result["uidvalidity"] = int(m.group(1))
    # Parse "UIDNEXT N"
    m = re.search(r"UIDNEXT\s+(\d+)", line_upper)
    if m:
      result["uidnext"] = int(m.group(1))
    # Parse "UNSEEN N"
    m = re.search(r"UNSEEN\s+(\d+)", line_upper)
    if m:
      result["unseen"] = int(m.group(1))
  return result


def _parse_list_response(line: str) -> dict[str, str] | None:
  """Parse a single LIST response line."""
  # Format: (\flags) "delimiter" "name"
  m = re.match(r'\(([^)]*)\)\s+"([^"]+)"\s+"?([^"]+)"?', line)
  if not m:
    # Try without quotes on name
    m = re.match(r'\(([^)]*)\)\s+"([^"]+)"\s+(.+)', line)
  if not m:
    return None

  flags_str, delimiter, name = m.group(1), m.group(2), m.group(3)
  flags: list[str] = [f.strip() for f in flags_str.split() if f.strip()]
  return {"name": name.strip('"'), "delimiter": delimiter, "flags": flags}
