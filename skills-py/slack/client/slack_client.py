"""
Async HTTP client for the Slack Web API.

Uses aiohttp with bearer token auth. Auto-retries on 429 with Retry-After.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import aiohttp

log = logging.getLogger("skill.slack.client")

BASE_URL = "https://slack.com/api"
REQUEST_TIMEOUT = 30


class SlackApiError(Exception):
  """General API error."""

  def __init__(self, status: int, message: str, error: str | None = None):
    self.status = status
    self.error = error
    super().__init__(f"Slack API error {status}: {message}")


class SlackAuthError(SlackApiError):
  """Authentication error (invalid_auth, account_inactive, etc.)."""

  pass


# Global client instance
_client: SlackClient | None = None


def get_client() -> SlackClient | None:
  """Get the global Slack client instance."""
  return _client


def set_client(client: SlackClient | None) -> None:
  """Set the global Slack client instance."""
  global _client
  _client = client


class SlackClient:
  """Async HTTP client for the Slack Web API."""

  def __init__(self, bot_token: str) -> None:
    self._bot_token = bot_token
    self._session: aiohttp.ClientSession | None = None

  @property
  def is_connected(self) -> bool:
    return self._session is not None and not self._session.closed

  async def connect(self) -> None:
    """Create the aiohttp session."""
    if self._session and not self._session.closed:
      return
    self._session = aiohttp.ClientSession(
      base_url=BASE_URL,
      headers={
        "Authorization": f"Bearer {self._bot_token}",
        "Content-Type": "application/json",
      },
      timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT),
    )

  async def close(self) -> None:
    """Close the aiohttp session."""
    if self._session and not self._session.closed:
      await self._session.close()
      self._session = None

  async def _request(self, method: str, endpoint: str, **kwargs: Any) -> dict[str, Any]:
    """Make an API request with retry on 429."""
    if not self._session:
      raise SlackApiError(0, "Client not connected. Call connect() first.")

    max_retries = 3
    for attempt in range(max_retries):
      try:
        async with self._session.request(method, endpoint, **kwargs) as resp:
          if resp.status == 429:
            retry_after = int(resp.headers.get("Retry-After", "5"))
            retry_after = min(retry_after, 60)
            log.warning("Rate limited. Retrying after %ds", retry_after)
            await asyncio.sleep(retry_after)
            continue

          data = await resp.json()

          # Slack API returns errors in the JSON response
          if not data.get("ok", False):
            error = data.get("error", "unknown_error")
            error_msg = data.get("error_description", error)

            if error in ("invalid_auth", "account_inactive", "token_revoked"):
              raise SlackAuthError(resp.status, error_msg, error)

            raise SlackApiError(resp.status, error_msg, error)

          return data

      except (SlackAuthError, SlackApiError):
        raise
      except (TimeoutError, aiohttp.ClientError) as e:
        if attempt < max_retries - 1:
          log.warning("Request failed (attempt %d): %s", attempt + 1, e)
          await asyncio.sleep(2**attempt)
          continue
        raise SlackApiError(0, f"Request failed after {max_retries} attempts: {e}")

    raise SlackApiError(0, "Request failed after max retries")

  async def get(self, endpoint: str, **params: Any) -> dict[str, Any]:
    """GET request."""
    return await self._request("GET", endpoint, params=params)

  async def post(self, endpoint: str, **json_data: Any) -> dict[str, Any]:
    """POST request."""
    return await self._request("POST", endpoint, json=json_data)

  # ---------------------------------------------------------------------------
  # Auth & Test
  # ---------------------------------------------------------------------------

  async def auth_test(self) -> dict[str, Any]:
    """Test authentication and get user/team info."""
    return await self.get("/auth.test")

  async def validate_token(self) -> bool:
    """Validate the bot token by calling auth.test."""
    try:
      result = await self.auth_test()
      return result.get("ok", False)
    except (SlackAuthError, SlackApiError):
      return False

  # ---------------------------------------------------------------------------
  # Conversations (Channels)
  # ---------------------------------------------------------------------------

  async def conversations_list(
    self,
    types: str = "public_channel,private_channel",
    exclude_archived: bool = True,
    limit: int = 200,
    cursor: str | None = None,
  ) -> dict[str, Any]:
    """List conversations (channels)."""
    params: dict[str, Any] = {
      "types": types,
      "exclude_archived": exclude_archived,
      "limit": limit,
    }
    if cursor:
      params["cursor"] = cursor
    return await self.get("/conversations.list", **params)

  async def conversations_info(self, channel: str) -> dict[str, Any]:
    """Get information about a conversation."""
    return await self.get("/conversations.info", channel=channel)

  async def conversations_create(self, name: str, is_private: bool = False) -> dict[str, Any]:
    """Create a conversation."""
    return await self.post(
      "/conversations.create",
      name=name,
      is_private=is_private,
    )

  async def conversations_archive(self, channel: str) -> dict[str, Any]:
    """Archive a conversation."""
    return await self.post("/conversations.archive", channel=channel)

  async def conversations_unarchive(self, channel: str) -> dict[str, Any]:
    """Unarchive a conversation."""
    return await self.post("/conversations.unarchive", channel=channel)

  async def conversations_join(self, channel: str) -> dict[str, Any]:
    """Join a conversation."""
    return await self.post("/conversations.join", channel=channel)

  async def conversations_leave(self, channel: str) -> dict[str, Any]:
    """Leave a conversation."""
    return await self.post("/conversations.leave", channel=channel)

  async def conversations_members(
    self, channel: str, limit: int = 200, cursor: str | None = None
  ) -> dict[str, Any]:
    """Get members of a conversation."""
    params: dict[str, Any] = {"channel": channel, "limit": limit}
    if cursor:
      params["cursor"] = cursor
    return await self.get("/conversations.members", **params)

  async def conversations_set_topic(self, channel: str, topic: str) -> dict[str, Any]:
    """Set the topic of a conversation."""
    return await self.post("/conversations.setTopic", channel=channel, topic=topic)

  async def conversations_set_purpose(self, channel: str, purpose: str) -> dict[str, Any]:
    """Set the purpose of a conversation."""
    return await self.post("/conversations.setPurpose", channel=channel, purpose=purpose)

  # ---------------------------------------------------------------------------
  # Messages
  # ---------------------------------------------------------------------------

  async def conversations_history(
    self,
    channel: str,
    limit: int = 100,
    cursor: str | None = None,
    oldest: str | None = None,
    latest: str | None = None,
  ) -> dict[str, Any]:
    """Get conversation history."""
    params: dict[str, Any] = {"channel": channel, "limit": limit}
    if cursor:
      params["cursor"] = cursor
    if oldest:
      params["oldest"] = oldest
    if latest:
      params["latest"] = latest
    return await self.get("/conversations.history", **params)

  async def chat_post_message(
    self,
    channel: str,
    text: str,
    thread_ts: str | None = None,
    reply_broadcast: bool = False,
  ) -> dict[str, Any]:
    """Post a message to a channel."""
    data: dict[str, Any] = {"channel": channel, "text": text}
    if thread_ts:
      data["thread_ts"] = thread_ts
      data["reply_broadcast"] = reply_broadcast
    return await self.post("/chat.postMessage", **data)

  async def chat_update(self, channel: str, ts: str, text: str) -> dict[str, Any]:
    """Update a message."""
    return await self.post("/chat.update", channel=channel, ts=ts, text=text)

  async def chat_delete(self, channel: str, ts: str) -> dict[str, Any]:
    """Delete a message."""
    return await self.post("/chat.delete", channel=channel, ts=ts)

  async def chat_get_permalink(self, channel: str, message_ts: str) -> dict[str, Any]:
    """Get a permalink for a message."""
    return await self.get("/chat.getPermalink", channel=channel, message_ts=message_ts)

  # ---------------------------------------------------------------------------
  # Users
  # ---------------------------------------------------------------------------

  async def users_list(self, limit: int = 200, cursor: str | None = None) -> dict[str, Any]:
    """List users."""
    params: dict[str, Any] = {"limit": limit}
    if cursor:
      params["cursor"] = cursor
    return await self.get("/users.list", **params)

  async def users_info(self, user: str) -> dict[str, Any]:
    """Get user information."""
    return await self.get("/users.info", user=user)

  async def users_lookup_by_email(self, email: str) -> dict[str, Any]:
    """Look up a user by email."""
    return await self.get("/users.lookupByEmail", email=email)

  # ---------------------------------------------------------------------------
  # Search
  # ---------------------------------------------------------------------------

  async def search_messages(self, query: str, count: int = 20, page: int = 1) -> dict[str, Any]:
    """Search messages."""
    return await self.get("/search.messages", query=query, count=count, page=page)

  async def search_all(self, query: str, count: int = 20, page: int = 1) -> dict[str, Any]:
    """Search messages and files."""
    return await self.get("/search.all", query=query, count=count, page=page)

  # ---------------------------------------------------------------------------
  # DMs
  # ---------------------------------------------------------------------------

  async def conversations_open(self, users: str) -> dict[str, Any]:
    """Open or resume a direct message conversation."""
    return await self.post("/conversations.open", users=users)

  async def im_list(self) -> dict[str, Any]:
    """List direct message conversations."""
    return await self.get("/im.list")
