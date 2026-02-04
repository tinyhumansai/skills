"""
Page management mixin for browser client.
"""

from __future__ import annotations

from typing import Any


class BrowserPagesMixin:
  """Mixin providing page management methods."""

  async def new_page(self, url: str | None = None) -> dict[str, Any]:
    """Create new page."""
    if not self.context:
      return {"success": False, "error": "Browser context not initialized"}
    try:
      page = await self.context.new_page()
      self.pages.append(page)
      self.current_page_index = len(self.pages) - 1
      if url:
        await page.goto(url)
      return {"success": True, "page_index": self.current_page_index, "url": page.url}
    except Exception as e:
      return {"success": False, "error": str(e)}

  async def get_pages(self) -> dict[str, Any]:
    """Get list of pages."""
    pages_info = []
    for i, page in enumerate(self.pages):
      pages_info.append({"index": i, "url": page.url, "title": await page.title()})
    return {"success": True, "pages": pages_info, "current_index": self.current_page_index}

  async def switch_page(self, index: int | None = None, url: str | None = None) -> dict[str, Any]:
    """Switch to a different page."""
    if index is not None:
      if 0 <= index < len(self.pages):
        self.current_page_index = index
        return {"success": True, "page_index": index, "url": self.pages[index].url}
      else:
        return {"success": False, "error": f"Invalid page index: {index}"}
    elif url:
      for i, page in enumerate(self.pages):
        if url in page.url:
          self.current_page_index = i
          return {"success": True, "page_index": i, "url": page.url}
      return {"success": False, "error": f"Page with URL not found: {url}"}
    else:
      return {"success": False, "error": "Must provide index or url"}

  async def close_page(self) -> dict[str, Any]:
    """Close current page."""
    if len(self.pages) <= 1:
      return {"success": False, "error": "Cannot close the last page"}
    page = self.pages.pop(self.current_page_index)
    await page.close()
    if self.current_page_index >= len(self.pages):
      self.current_page_index = len(self.pages) - 1
    return {"success": True, "pages_remaining": len(self.pages)}
