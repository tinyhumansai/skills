"""
Other browser operations mixin (dialogs, file upload/download).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


class BrowserOtherMixin:
  """Mixin providing other browser operations."""

  async def handle_dialog(self, action: str, prompt_text: str | None = None) -> dict[str, Any]:
    """Handle browser dialogs."""
    page = self._get_current_page()

    async def handle_dialog_event(dialog: Any) -> None:
      if action == "accept":
        if prompt_text:
          await dialog.accept(prompt_text)
        else:
          await dialog.accept()
      else:
        await dialog.dismiss()

    try:
      page.on("dialog", handle_dialog_event)
      return {"success": True}
    except Exception as e:
      return {"success": False, "error": str(e)}

  async def upload_file(
    self, selector: str, file_path: str, multiple: bool = False
  ) -> dict[str, Any]:
    """Upload a file."""
    page = self._get_current_page()
    try:
      path = Path(file_path)
      if not path.exists():
        return {"success": False, "error": f"File not found: {file_path}"}
      if multiple:
        await page.set_input_files(selector, [str(path)])
      else:
        await page.set_input_files(selector, str(path))
      return {"success": True}
    except Exception as e:
      return {"success": False, "error": str(e)}

  async def download_file(
    self, save_path: str, url: str | None = None, timeout: int = 30000
  ) -> dict[str, Any]:
    """Download a file."""
    page = self._get_current_page()
    try:
      if url:
        async with page.expect_download(timeout=timeout) as download_info:
          await page.goto(url)
        download = await download_info.value
      else:
        async with page.expect_download(timeout=timeout) as download_info:
          pass  # Wait for next download
        download = await download_info.value
      await download.save_as(save_path)
      return {"success": True, "path": save_path}
    except Exception as e:
      return {"success": False, "error": str(e)}
