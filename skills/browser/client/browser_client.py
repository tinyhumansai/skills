"""
Browser client using Playwright for browser automation.

Manages browser instances, pages, and provides methods for all browser operations.
"""

from __future__ import annotations

from .browser_client_base import BrowserClientBase
from .browser_content import BrowserContentMixin
from .browser_interaction import BrowserInteractionMixin
from .browser_navigation import BrowserNavigationMixin
from .browser_network import BrowserNetworkMixin
from .browser_other import BrowserOtherMixin
from .browser_pages import BrowserPagesMixin
from .browser_storage import BrowserStorageMixin
from .browser_wait import BrowserWaitMixin


class BrowserClient(
  BrowserClientBase,
  BrowserNavigationMixin,
  BrowserInteractionMixin,
  BrowserContentMixin,
  BrowserStorageMixin,
  BrowserNetworkMixin,
  BrowserPagesMixin,
  BrowserWaitMixin,
  BrowserOtherMixin,
):
  """Playwright-based browser automation client."""

  pass
