"""
Telethon client wrapper for the Telegram runtime skill.

Ported from mtproto/client.ts. Manages lifecycle, connection,
authentication, and FloodWait handling.
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any, TypeVar

from telethon import TelegramClient
from telethon.errors import FloodWaitError
from telethon.sessions import StringSession

from ..state import store

if TYPE_CHECKING:
  from collections.abc import Awaitable, Callable

log = logging.getLogger("skill.telegram.client")

T = TypeVar("T")


class MTProtoClient:
  def __init__(self, api_id: int, api_hash: str) -> None:
    self._client: TelegramClient | None = None
    self._is_initialized = False
    self._is_connected = False
    self._session_string = ""
    self._api_id = api_id
    self._api_hash = api_hash
    self._init_lock = asyncio.Lock()
    self._connect_lock = asyncio.Lock()

  async def initialize(self, session_string: str = "") -> None:
    """Initialize with an optional session string."""
    if self._is_initialized and self._client:
      return
    async with self._init_lock:
      if self._is_initialized and self._client:
        return
      await self._do_initialize(session_string)

  async def _do_initialize(self, session: str) -> None:
    try:
      string_session = StringSession(session)
      self._session_string = session

      self._client = TelegramClient(
        string_session,
        self._api_id,
        self._api_hash,
        connection_retries=5,
        request_retries=5,
        flood_sleep_threshold=60,
      )

      self._is_initialized = True
      log.info("MTProto client initialized")
    except Exception:
      log.exception("Failed to initialize MTProto client")
      raise

  async def connect(self) -> None:
    """Connect to Telegram servers."""
    if not self._client:
      raise RuntimeError("MTProto client not initialized. Call initialize() first.")
    if self._is_connected:
      return
    async with self._connect_lock:
      # Double-check locking pattern - another coroutine may have connected
      # between the outer check and acquiring the lock
      # Check again inside lock to prevent race condition
      if self._is_connected:  # type: ignore[unreachable]
        return
      await self._do_connect()

  async def _do_connect(self) -> None:
    try:
      await self._client.connect()  # type: ignore[union-attr]
      self._is_connected = True
      log.info("Connected to Telegram")
      self._save_session_if_changed()
    except Exception:
      log.exception("Failed to connect")
      raise

  async def start(self, **kwargs: Any) -> None:
    """Start authentication."""
    if not self._client:
      raise RuntimeError("MTProto client not initialized.")
    try:
      await self._client.start(**kwargs)
      self._save_session_if_changed()
      log.info("Authentication successful")
    except Exception:
      log.exception("Authentication failed")
      raise

  def get_client(self) -> TelegramClient:
    """Get the raw TelegramClient instance."""
    if not self._client or not self._is_initialized:
      raise RuntimeError("MTProto client not initialized.")
    return self._client

  def is_ready(self) -> bool:
    return self._is_initialized and self._client is not None

  def is_client_connected(self) -> bool:
    return self._is_connected and self.is_ready()

  def get_session_string(self) -> str:
    return self._session_string

  async def ensure_connected(self) -> TelegramClient:
    """Return the client, connecting if needed."""
    if not self.is_client_connected():
      await self.connect()
    return self.get_client()

  async def check_connection(self) -> bool:
    """Check connection + authorization."""
    try:
      if not self._is_initialized or not self._client:
        return False
      if not self._is_connected:
        await self.connect()

      is_authorized = await self._client.is_user_authorized()
      if not is_authorized:
        return False

      await self.with_flood_wait_handling(self._client.get_me)
      return True
    except FloodWaitError as e:
      log.warning("Connection check: FLOOD_WAIT %ds", e.seconds)
      return False
    except Exception:
      log.exception("Connection check failed")
      return False

  async def disconnect(self) -> None:
    """Disconnect from Telegram."""
    if self._client and self._is_connected:
      try:
        await self._client.disconnect()
        self._is_connected = False
        log.info("Disconnected from Telegram")
      except Exception:
        log.exception("Error disconnecting")
        raise

  async def clear_session_and_disconnect(self) -> None:
    """Clear session and disconnect."""
    await self.disconnect()
    self._client = None
    self._is_initialized = False
    self._is_connected = False
    self._session_string = ""

  async def invoke(self, request: Any) -> Any:
    """Invoke a raw Telegram API method with FloodWait handling."""
    client = await self.ensure_connected()
    return await self.with_flood_wait_handling(lambda: client(request))

  async def with_flood_wait_handling(
    self,
    operation: Callable[..., Awaitable[T]],
    max_retries: int = 3,
    retry_count: int = 0,
  ) -> T:
    """Execute with FloodWait retry."""
    try:
      return await operation()
    except FloodWaitError as e:
      wait_seconds = e.seconds
      if wait_seconds > 300:
        raise RuntimeError(
          f"FLOOD_WAIT: Too long wait time ({wait_seconds}s). Please try again later."
        )
      if retry_count >= max_retries:
        raise RuntimeError(
          f"FLOOD_WAIT: Maximum retries exceeded. Wait {wait_seconds}s before trying again."
        )
      log.warning(
        "FLOOD_WAIT: Waiting %ds before retry (attempt %d/%d)",
        wait_seconds,
        retry_count + 1,
        max_retries,
      )
      await asyncio.sleep(wait_seconds)
      return await self.with_flood_wait_handling(operation, max_retries, retry_count + 1)

  def _save_session_if_changed(self) -> None:
    if not self._client:
      return
    new_session = self._client.session.save()
    if isinstance(new_session, str) and new_session != self._session_string:
      self._session_string = new_session
      store.set_session_string(new_session)
      log.info("Session updated and saved")


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_instance: MTProtoClient | None = None


def create_client(api_id: int, api_hash: str) -> MTProtoClient:
  global _instance
  _instance = MTProtoClient(api_id, api_hash)
  return _instance


def get_client() -> MTProtoClient:
  if _instance is None:
    raise RuntimeError("MTProto client not created yet.")
  return _instance
