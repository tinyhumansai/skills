"""
Wait mixin for browser client.
"""

from __future__ import annotations

from typing import Any

from playwright.async_api import TimeoutError as PlaywrightTimeoutError


class BrowserWaitMixin:
  """Mixin providing wait methods."""

  async def wait_for_selector(
    self, selector: str, state: str = "visible", timeout: int = 30000
  ) -> dict[str, Any]:
    """Wait for selector."""
    page = self._get_current_page()
    try:
      await page.wait_for_selector(selector, state=state, timeout=timeout)
      return {"success": True}
    except PlaywrightTimeoutError:
      return {"success": False, "error": f"Timeout waiting for selector: {selector}"}
    except Exception as e:
      return {"success": False, "error": str(e)}

  async def wait_for_url(self, url: str, timeout: int = 30000) -> dict[str, Any]:
    """Wait for URL."""
    page = self._get_current_page()
    try:
      await page.wait_for_url(url, timeout=timeout)
      return {"success": True}
    except PlaywrightTimeoutError:
      return {"success": False, "error": f"Timeout waiting for URL: {url}"}
    except Exception as e:
      return {"success": False, "error": str(e)}
