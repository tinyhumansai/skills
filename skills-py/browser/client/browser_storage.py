"""
Storage mixin for browser client (cookies, localStorage, sessionStorage).
"""

from __future__ import annotations

import json
from typing import Any


class BrowserStorageMixin:
  """Mixin providing storage methods."""

  async def get_cookies(self, urls: list[str] | None = None) -> dict[str, Any]:
    """Get cookies."""
    if not self.context:
      return {"success": False, "error": "Browser context not initialized"}
    try:
      cookies = await self.context.cookies(urls)
      return {"success": True, "cookies": cookies}
    except Exception as e:
      return {"success": False, "error": str(e)}

  async def set_cookie(
    self,
    name: str,
    value: str,
    url: str,
    domain: str | None = None,
    path: str = "/",
    expires: float | None = None,
    http_only: bool = False,
    secure: bool = False,
    same_site: str | None = None,
  ) -> dict[str, Any]:
    """Set a cookie."""
    if not self.context:
      return {"success": False, "error": "Browser context not initialized"}
    try:
      cookie: dict[str, Any] = {
        "name": name,
        "value": value,
        "url": url,
        "path": path,
        "httpOnly": http_only,
        "secure": secure,
      }
      if domain:
        cookie["domain"] = domain
      if expires:
        cookie["expires"] = expires
      if same_site:
        cookie["sameSite"] = same_site
      await self.context.add_cookies([cookie])
      return {"success": True}
    except Exception as e:
      return {"success": False, "error": str(e)}

  async def clear_cookies(self, urls: list[str] | None = None) -> dict[str, Any]:
    """Clear cookies."""
    if not self.context:
      return {"success": False, "error": "Browser context not initialized"}
    try:
      await self.context.clear_cookies()
      return {"success": True}
    except Exception as e:
      return {"success": False, "error": str(e)}

  async def get_local_storage(self, key: str | None = None) -> dict[str, Any]:
    """Get localStorage."""
    page = self._get_current_page()
    try:
      if key:
        value = await page.evaluate(f"localStorage.getItem('{key}')")
        return {"success": True, "key": key, "value": value}
      else:
        storage = await page.evaluate("() => { return {...localStorage}; }")
        return {"success": True, "storage": storage}
    except Exception as e:
      return {"success": False, "error": str(e)}

  async def set_local_storage(self, key: str, value: str) -> dict[str, Any]:
    """Set localStorage."""
    page = self._get_current_page()
    try:
      await page.evaluate(f"localStorage.setItem('{key}', {json.dumps(value)})")
      return {"success": True}
    except Exception as e:
      return {"success": False, "error": str(e)}

  async def clear_local_storage(self) -> dict[str, Any]:
    """Clear localStorage."""
    page = self._get_current_page()
    try:
      await page.evaluate("localStorage.clear()")
      return {"success": True}
    except Exception as e:
      return {"success": False, "error": str(e)}

  async def get_session_storage(self, key: str | None = None) -> dict[str, Any]:
    """Get sessionStorage."""
    page = self._get_current_page()
    try:
      if key:
        value = await page.evaluate(f"sessionStorage.getItem('{key}')")
        return {"success": True, "key": key, "value": value}
      else:
        storage = await page.evaluate("() => { return {...sessionStorage}; }")
        return {"success": True, "storage": storage}
    except Exception as e:
      return {"success": False, "error": str(e)}

  async def set_session_storage(self, key: str, value: str) -> dict[str, Any]:
    """Set sessionStorage."""
    page = self._get_current_page()
    try:
      await page.evaluate(f"sessionStorage.setItem('{key}', {json.dumps(value)})")
      return {"success": True}
    except Exception as e:
      return {"success": False, "error": str(e)}

  async def clear_session_storage(self) -> dict[str, Any]:
    """Clear sessionStorage."""
    page = self._get_current_page()
    try:
      await page.evaluate("sessionStorage.clear()")
      return {"success": True}
    except Exception as e:
      return {"success": False, "error": str(e)}
