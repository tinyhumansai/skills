"""
Async HTTP client for the Otter.ai Connect API v2.

Uses aiohttp with bearer token auth. Auto-retries on 429 with Retry-After.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import aiohttp

log = logging.getLogger("skill.otter.client")

BASE_URL = "https://api.otter.ai/v2"
REQUEST_TIMEOUT = 30


class OtterApiError(Exception):
  """General API error."""

  def __init__(self, status: int, message: str):
    self.status = status
    super().__init__(f"Otter API error {status}: {message}")


class OtterAuthError(OtterApiError):
  """Authentication error (401/403)."""

  pass


class OtterClient:
  """Async HTTP client for the Otter.ai API."""

  def __init__(self, api_key: str) -> None:
    self._api_key = api_key
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
        "Authorization": f"Bearer {self._api_key}",
        "Content-Type": "application/json",
      },
      timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT),
    )

  async def close(self) -> None:
    """Close the aiohttp session."""
    if self._session and not self._session.closed:
      await self._session.close()
      self._session = None

  async def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any] | list[Any]:
    """Make an API request with retry on 429."""
    if not self._session:
      raise OtterApiError(0, "Client not connected. Call connect() first.")

    max_retries = 3
    for attempt in range(max_retries):
      try:
        async with self._session.request(method, path, **kwargs) as resp:
          if resp.status == 429:
            retry_after = int(resp.headers.get("Retry-After", "5"))
            retry_after = min(retry_after, 60)
            log.warning("Rate limited. Retrying after %ds", retry_after)
            await asyncio.sleep(retry_after)
            continue

          if resp.status in (401, 403):
            text = await resp.text()
            raise OtterAuthError(resp.status, text)

          if resp.status >= 400:
            text = await resp.text()
            raise OtterApiError(resp.status, text)

          if resp.content_type == "application/json":
            return await resp.json()
          # Some endpoints may return plain text
          text = await resp.text()
          return {"text": text}

      except (TimeoutError, aiohttp.ClientError) as e:
        if attempt < max_retries - 1:
          log.warning("Request failed (attempt %d): %s", attempt + 1, e)
          await asyncio.sleep(2**attempt)
          continue
        raise OtterApiError(0, f"Request failed after {max_retries} attempts: {e}")

    raise OtterApiError(0, "Max retries exceeded")

  # ------------------------------------------------------------------
  # API methods
  # ------------------------------------------------------------------

  async def get_speeches(self, limit: int = 20, folder: str | None = None) -> dict[str, Any]:
    """List speeches (meetings)."""
    params: dict[str, Any] = {"limit": limit}
    if folder:
      params["folder"] = folder
    return await self._request("GET", "/speeches", params=params)

  async def get_speech(self, speech_id: str) -> dict[str, Any]:
    """Get a single speech by ID."""
    return await self._request("GET", f"/speeches/{speech_id}")

  async def get_transcript(self, speech_id: str) -> dict[str, Any]:
    """Get the transcript for a speech."""
    return await self._request("GET", f"/speeches/{speech_id}/transcript")

  async def get_user(self) -> dict[str, Any]:
    """Get the current user profile."""
    return await self._request("GET", "/user")

  async def get_speakers(self) -> dict[str, Any]:
    """Get recognized speakers."""
    return await self._request("GET", "/speakers")

  async def search_speeches(self, query: str, limit: int = 20) -> dict[str, Any]:
    """Search across all speeches."""
    params: dict[str, Any] = {"query": query, "limit": limit}
    return await self._request("GET", "/speeches/search", params=params)

  async def validate_key(self) -> bool:
    """Validate the API key by making a minimal request."""
    try:
      await self.get_speeches(limit=1)
      return True
    except OtterAuthError:
      return False
    except OtterApiError:
      # Non-auth errors mean the key is valid but something else went wrong
      return True
