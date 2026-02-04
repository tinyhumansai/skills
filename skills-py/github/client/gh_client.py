"""
GitHub client wrapper using PyGithub.

PyGithub is synchronous, so all calls are wrapped with asyncio.to_thread
to keep the skill's async contract intact.
"""

from __future__ import annotations

import asyncio
import contextlib
import functools
import logging
from typing import TYPE_CHECKING, Any, TypeVar

from github import Auth, Github, GithubException

if TYPE_CHECKING:
  from collections.abc import Callable

log = logging.getLogger("skill.github.client")

T = TypeVar("T")


async def _run_sync(fn: Callable[..., T], *args: Any, **kwargs: Any) -> T:
  """Run a synchronous PyGithub call in a thread."""
  return await asyncio.to_thread(functools.partial(fn, *args, **kwargs))


class GhClient:
  """Async-compatible wrapper around PyGithub."""

  def __init__(self) -> None:
    self._gh: Github | None = None
    self._token: str = ""
    self._is_authed: bool = False
    self._username: str = ""

  async def initialize(self, token: str) -> None:
    """Initialize with a Personal Access Token."""
    self._token = token
    auth = Auth.Token(token)
    self._gh = Github(auth=auth, per_page=100)
    log.info("PyGithub client initialized")

  async def check_auth(self) -> bool:
    """Verify authentication by fetching the authenticated user."""
    if not self._gh:
      return False
    try:
      user = await _run_sync(self._gh.get_user)
      self._username = user.login
      self._is_authed = True
      log.info("Authenticated as %s", self._username)
      return True
    except GithubException as exc:
      log.error("Auth check failed: %s", exc)
      self._is_authed = False
      return False

  @property
  def gh(self) -> Github:
    if not self._gh:
      raise RuntimeError("GhClient not initialized. Call initialize() first.")
    return self._gh

  @property
  def is_authed(self) -> bool:
    return self._is_authed

  @property
  def username(self) -> str:
    return self._username

  async def close(self) -> None:
    """Close the underlying connection."""
    if self._gh:
      with contextlib.suppress(Exception):
        await _run_sync(self._gh.close)
      self._gh = None
      self._is_authed = False


# ---------------------------------------------------------------------------
# Module-level helper
# ---------------------------------------------------------------------------


async def run_sync(fn: Callable[..., T], *args: Any, **kwargs: Any) -> T:
  """Public helper to run any synchronous PyGithub call in a thread."""
  return await _run_sync(fn, *args, **kwargs)


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_client_instance: GhClient | None = None


def create_client() -> GhClient:
  """Create and return the singleton GhClient."""
  global _client_instance
  _client_instance = GhClient()
  return _client_instance


def get_client() -> GhClient:
  """Return the singleton GhClient. Raises if not initialized."""
  if _client_instance is None:
    raise RuntimeError("GhClient not initialized. Call create_client() first.")
  return _client_instance
