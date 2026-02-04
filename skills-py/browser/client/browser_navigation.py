"""
Navigation mixin for browser client.
"""

from __future__ import annotations

from typing import Any

from playwright.async_api import TimeoutError as PlaywrightTimeoutError


class BrowserNavigationMixin:
  """Mixin providing navigation methods."""

  async def navigate(
    self, url: str, wait_until: str = "load", timeout: int = 30000
  ) -> dict[str, Any]:
    """Navigate to a URL."""
    page = self._get_current_page()
    try:
      response = await page.goto(url, wait_until=wait_until, timeout=timeout)
      return {
        "success": True,
        "url": page.url,
        "status": response.status if response else None,
        "title": await page.title(),
      }
    except PlaywrightTimeoutError as e:
      return {"success": False, "error": f"Navigation timeout: {e}"}
    except Exception as e:
      return {"success": False, "error": str(e)}

  async def go_back(self, timeout: int = 30000) -> dict[str, Any]:
    """Go back in history."""
    page = self._get_current_page()
    try:
      await page.go_back(timeout=timeout)
      return {"success": True, "url": page.url}
    except Exception as e:
      return {"success": False, "error": str(e)}

  async def go_forward(self, timeout: int = 30000) -> dict[str, Any]:
    """Go forward in history."""
    page = self._get_current_page()
    try:
      await page.go_forward(timeout=timeout)
      return {"success": True, "url": page.url}
    except Exception as e:
      return {"success": False, "error": str(e)}

  async def reload(self, wait_until: str = "load", timeout: int = 30000) -> dict[str, Any]:
    """Reload page."""
    page = self._get_current_page()
    try:
      await page.reload(wait_until=wait_until, timeout=timeout)
      return {"success": True, "url": page.url}
    except Exception as e:
      return {"success": False, "error": str(e)}

  async def get_url(self) -> dict[str, Any]:
    """Get current URL."""
    page = self._get_current_page()
    return {"success": True, "url": page.url}

  async def get_title(self) -> dict[str, Any]:
    """Get page title."""
    page = self._get_current_page()
    return {"success": True, "title": await page.title()}
