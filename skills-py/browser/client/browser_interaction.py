"""
Element interaction mixin for browser client.
"""

from __future__ import annotations

from typing import Any


class BrowserInteractionMixin:
  """Mixin providing element interaction methods."""

  async def click(
    self,
    selector: str,
    button: str = "left",
    click_count: int = 1,
    delay: int = 0,
    force: bool = False,
  ) -> dict[str, Any]:
    """Click an element."""
    page = self._get_current_page()
    try:
      # Handle XPath selectors
      if selector.startswith("xpath:"):
        selector = selector[6:]
        await page.locator(f"xpath={selector}").click(
          button=button, click_count=click_count, delay=delay, force=force
        )
      # Handle text selectors
      elif not selector.startswith(("#", ".", "[", "/")):
        await page.get_by_text(selector, exact=False).click(
          button=button, click_count=click_count, delay=delay, force=force
        )
      else:
        await page.click(selector, button=button, click_count=click_count, delay=delay, force=force)
      return {"success": True}
    except Exception as e:
      return {"success": False, "error": str(e)}

  async def fill(self, selector: str, text: str, timeout: int = 30000) -> dict[str, Any]:
    """Fill an input field."""
    page = self._get_current_page()
    try:
      await page.fill(selector, text, timeout=timeout)
      return {"success": True}
    except Exception as e:
      return {"success": False, "error": str(e)}

  async def type_text(
    self, selector: str, text: str, delay: int = 0, timeout: int = 30000
  ) -> dict[str, Any]:
    """Type text character by character."""
    page = self._get_current_page()
    try:
      await page.type(selector, text, delay=delay, timeout=timeout)
      return {"success": True}
    except Exception as e:
      return {"success": False, "error": str(e)}

  async def press_key(self, key: str, delay: int = 0) -> dict[str, Any]:
    """Press a keyboard key."""
    page = self._get_current_page()
    try:
      await page.keyboard.press(key, delay=delay)
      return {"success": True}
    except Exception as e:
      return {"success": False, "error": str(e)}

  async def select_option(
    self,
    selector: str,
    value: str | None = None,
    label: str | None = None,
    index: int | None = None,
    multiple: bool = False,
  ) -> dict[str, Any]:
    """Select option in a dropdown."""
    page = self._get_current_page()
    try:
      select_element = page.locator(selector)
      if value:
        await select_element.select_option(value=value)
      elif label:
        await select_element.select_option(label=label)
      elif index is not None:
        await select_element.select_option(index=index)
      else:
        return {"success": False, "error": "Must provide value, label, or index"}
      return {"success": True}
    except Exception as e:
      return {"success": False, "error": str(e)}

  async def check(self, selector: str, checked: bool = True) -> dict[str, Any]:
    """Check or uncheck a checkbox/radio."""
    page = self._get_current_page()
    try:
      if checked:
        await page.check(selector)
      else:
        await page.uncheck(selector)
      return {"success": True}
    except Exception as e:
      return {"success": False, "error": str(e)}

  async def hover(self, selector: str, timeout: int = 30000) -> dict[str, Any]:
    """Hover over an element."""
    page = self._get_current_page()
    try:
      await page.hover(selector, timeout=timeout)
      return {"success": True}
    except Exception as e:
      return {"success": False, "error": str(e)}

  async def scroll(
    self, selector: str | None = None, direction: str = "down", amount: int = 500
  ) -> dict[str, Any]:
    """Scroll the page or element."""
    page = self._get_current_page()
    try:
      if selector:
        element = page.locator(selector)
        if direction == "down":
          await element.scroll_into_view_if_needed()
        elif direction == "up":
          await element.evaluate("el => el.scrollTop -= arguments[0]", amount)
        elif direction == "left":
          await element.evaluate("el => el.scrollLeft -= arguments[0]", amount)
        elif direction == "right":
          await element.evaluate("el => el.scrollLeft += arguments[0]", amount)
      else:
        if direction == "down":
          await page.evaluate(f"window.scrollBy(0, {amount})")
        elif direction == "up":
          await page.evaluate(f"window.scrollBy(0, -{amount})")
        elif direction == "left":
          await page.evaluate(f"window.scrollBy(-{amount}, 0)")
        elif direction == "right":
          await page.evaluate(f"window.scrollBy({amount}, 0)")
      return {"success": True}
    except Exception as e:
      return {"success": False, "error": str(e)}
