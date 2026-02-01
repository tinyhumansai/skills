"""
Base browser client with initialization and lifecycle management.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from playwright.async_api import (
  Browser,
  BrowserContext,
  Page,
  async_playwright,
)

log = logging.getLogger("skill.browser.client")


class BrowserClientBase:
  """Base browser client with initialization and lifecycle."""

  def __init__(self, headless: bool = True, browser_type: str = "chromium"):
    """
    Initialize browser client.

    Args:
      headless: Run browser in headless mode
      browser_type: Browser type ('chromium', 'firefox', 'webkit')
    """
    self.headless = headless
    self.browser_type = browser_type
    self.playwright = None
    self.browser: Browser | None = None
    self.context: BrowserContext | None = None
    self.pages: list[Page] = []
    self.current_page_index = 0
    self.network_logs: list[dict[str, Any]] = []

  async def start(self) -> None:
    """Start the browser."""
    if self.playwright is None:
      self.playwright = await async_playwright().start()
      browser_launcher = getattr(self.playwright, self.browser_type)

      try:
        self.browser = await browser_launcher.launch(headless=self.headless)
      except Exception as e:
        error_msg = str(e).lower()
        # Check if error is related to missing browsers
        if "executable doesn't exist" in error_msg or "browser" in error_msg:
          log.info("Browser not found, installing %s...", self.browser_type)
          try:
            await self._ensure_browsers_installed()
            # Retry launch after installation
            self.browser = await browser_launcher.launch(headless=self.headless)
            log.info("Browser launched successfully after installation")
          except Exception as install_error:
            log.error("Failed to install browser: %s", install_error)
            raise RuntimeError(
              f"Browser '{self.browser_type}' not installed and auto-installation failed. "
              f"Error: {install_error}. "
              f"Please install manually with: python -m playwright install {self.browser_type}"
            ) from install_error
        else:
          # Some other error, re-raise it
          raise

      self.context = await self.browser.new_context()
      # Set up network request interception
      self.context.on("request", self._on_request)
      self.context.on("response", self._on_response)
      # Create initial page
      page = await self.context.new_page()
      self.pages.append(page)
      self.current_page_index = 0
      log.info("Browser started: %s (headless=%s)", self.browser_type, self.headless)

  async def _ensure_browsers_installed(self) -> None:
    """
    Ensure Playwright browsers are installed.

    This runs playwright install in a subprocess to download browser binaries.
    Runs in a thread executor to avoid blocking the event loop.
    """
    import subprocess
    import sys

    log.info(
      "Installing Playwright browser '%s' (this may take a few minutes)...", self.browser_type
    )

    # Run playwright install in a subprocess (it's a sync operation)
    # We'll run it in a thread pool to avoid blocking the event loop
    loop = asyncio.get_event_loop()

    def install():
      """Install browsers synchronously."""
      try:
        # Use playwright's install command via subprocess
        # This is the most reliable way to install browsers
        result = subprocess.run(
          [sys.executable, "-m", "playwright", "install", self.browser_type],
          capture_output=True,
          text=True,
          timeout=600,  # 10 minute timeout for download (browsers can be large)
        )
        if result.returncode == 0:
          log.info("Playwright browser '%s' installed successfully", self.browser_type)
          if result.stdout:
            log.debug("Install output: %s", result.stdout)
        else:
          error_msg = result.stderr or result.stdout or "Unknown error"
          log.error("Playwright install failed: %s", error_msg)
          raise RuntimeError(f"Failed to install browser: {error_msg}")
      except subprocess.TimeoutExpired:
        log.error("Playwright install timed out after 10 minutes")
        raise RuntimeError(
          "Browser installation timed out. "
          "This may be due to slow internet connection. "
          "Please try installing manually: python -m playwright install " + self.browser_type
        )
      except FileNotFoundError:
        log.error("Playwright module not found")
        raise RuntimeError(
          "Playwright not found. The skill requires playwright to be installed. "
          "This should be handled automatically by the skill system."
        )
      except Exception as e:
        log.error("Failed to install Playwright browsers: %s", e)
        raise RuntimeError(f"Browser installation failed: {e}")

    # Run installation in executor to avoid blocking
    await loop.run_in_executor(None, install)
    log.info("Browser installation complete")

  async def stop(self) -> None:
    """Stop the browser and clean up."""
    if self.context:
      await self.context.close()
    if self.browser:
      await self.browser.close()
    if self.playwright:
      await self.playwright.stop()
    self.browser = None
    self.context = None
    self.playwright = None
    self.pages = []
    self.network_logs = []
    log.info("Browser stopped")

  def _on_request(self, request: Any) -> None:
    """Handle network request."""
    self.network_logs.append(
      {
        "type": "request",
        "url": request.url,
        "method": request.method,
        "headers": request.headers,
        "post_data": request.post_data,
        "timestamp": asyncio.get_event_loop().time(),
      }
    )

  def _on_response(self, response: Any) -> None:
    """Handle network response."""
    self.network_logs.append(
      {
        "type": "response",
        "url": response.url,
        "status": response.status,
        "status_text": response.status_text,
        "headers": response.headers,
        "timestamp": asyncio.get_event_loop().time(),
      }
    )

  def _get_current_page(self) -> Page:
    """Get the current active page."""
    if not self.pages:
      raise RuntimeError("No pages available. Call start() first.")
    return self.pages[self.current_page_index]
