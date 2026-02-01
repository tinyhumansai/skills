"""
Content extraction mixin for browser client.
"""

from __future__ import annotations

import base64
from typing import Any


class BrowserContentMixin:
  """Mixin providing content extraction methods."""

  async def screenshot(
    self,
    selector: str | None = None,
    path: str | None = None,
    full_page: bool = False,
    image_type: str = "png",
  ) -> dict[str, Any]:
    """Take a screenshot."""
    page = self._get_current_page()
    try:
      options: dict[str, Any] = {"type": image_type, "full_page": full_page}
      if selector:
        element = page.locator(selector)
        if path:
          await element.screenshot(path=path, **options)
          return {"success": True, "path": path}
        else:
          screenshot_bytes = await element.screenshot(**options)
          return {
            "success": True,
            "base64": base64.b64encode(screenshot_bytes).decode("utf-8"),
            "type": image_type,
          }
      else:
        if path:
          await page.screenshot(path=path, **options)
          return {"success": True, "path": path}
        else:
          screenshot_bytes = await page.screenshot(**options)
          return {
            "success": True,
            "base64": base64.b64encode(screenshot_bytes).decode("utf-8"),
            "type": image_type,
          }
    except Exception as e:
      return {"success": False, "error": str(e)}

  async def get_text(self, selector: str | None = None, inner_text: bool = False) -> dict[str, Any]:
    """Get text content."""
    page = self._get_current_page()
    try:
      if selector:
        element = page.locator(selector)
        if inner_text:
          text = await element.inner_text()
        else:
          text = await element.text_content()
      else:
        if inner_text:
          text = await page.inner_text("body")
        else:
          text = await page.text_content("body")
      return {"success": True, "text": text}
    except Exception as e:
      return {"success": False, "error": str(e)}

  async def get_html(self, selector: str | None = None, outer_html: bool = True) -> dict[str, Any]:
    """Get HTML content."""
    page = self._get_current_page()
    try:
      if selector:
        element = page.locator(selector)
        if outer_html:
          html = await element.evaluate("el => el.outerHTML")
        else:
          html = await element.evaluate("el => el.innerHTML")
      else:
        html = await page.content()
      return {"success": True, "html": html}
    except Exception as e:
      return {"success": False, "error": str(e)}

  async def get_attribute(self, selector: str, attribute: str) -> dict[str, Any]:
    """Get element attribute."""
    page = self._get_current_page()
    try:
      value = await page.get_attribute(selector, attribute)
      return {"success": True, "value": value}
    except Exception as e:
      return {"success": False, "error": str(e)}

  async def evaluate(self, script: str, arg: Any = None) -> dict[str, Any]:
    """Execute JavaScript."""
    page = self._get_current_page()
    try:
      if arg is not None:
        result = await page.evaluate(f"({script})", arg)
      else:
        result = await page.evaluate(script)
      return {"success": True, "result": result}
    except Exception as e:
      return {"success": False, "error": str(e)}
