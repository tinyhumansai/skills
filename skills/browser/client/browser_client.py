"""
Browser client using Playwright for browser automation.

Manages browser instances, pages, and provides methods for all browser operations.
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
from pathlib import Path
from typing import Any

from playwright.async_api import (
  Browser,
  BrowserContext,
  Page,
  async_playwright,
  TimeoutError as PlaywrightTimeoutError,
)

log = logging.getLogger("skill.browser.client")


class BrowserClient:
  """Playwright-based browser automation client."""

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
    
    log.info("Installing Playwright browser '%s' (this may take a few minutes)...", self.browser_type)
    
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

  async def get_html(
    self, selector: str | None = None, outer_html: bool = True
  ) -> dict[str, Any]:
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

  async def intercept_request(
    self,
    url_pattern: str,
    action: str = "continue",
    response_status: int = 200,
    response_body: str | None = None,
    response_headers: dict[str, str] | None = None,
  ) -> dict[str, Any]:
    """Intercept network requests."""
    page = self._get_current_page()

    async def handle_route(route: Any) -> None:
      if action == "abort":
        await route.abort()
      elif action == "fulfill":
        await route.fulfill(
          status=response_status,
          body=response_body or "",
          headers=response_headers or {},
        )
      elif action == "respond":
        await route.fulfill(
          status=response_status,
          body=response_body or "",
          headers=response_headers or {},
        )
      else:
        await route.continue_()

    try:
      await page.route(url_pattern, handle_route)
      return {"success": True}
    except Exception as e:
      return {"success": False, "error": str(e)}

  async def get_network_logs(
    self,
    url_pattern: str | None = None,
    method: str | None = None,
    status: int | None = None,
  ) -> dict[str, Any]:
    """Get network logs."""
    logs = self.network_logs
    if url_pattern:
      import re

      pattern = re.compile(url_pattern.replace("*", ".*"))
      logs = [log for log in logs if pattern.search(log.get("url", ""))]
    if method:
      logs = [log for log in logs if log.get("method") == method.upper()]
    if status:
      logs = [log for log in logs if log.get("status") == status]
    return {"success": True, "logs": logs, "count": len(logs)}

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

  async def reload(
    self, wait_until: str = "load", timeout: int = 30000
  ) -> dict[str, Any]:
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

  async def close_page(self) -> dict[str, Any]:
    """Close current page."""
    if len(self.pages) <= 1:
      return {"success": False, "error": "Cannot close the last page"}
    page = self.pages.pop(self.current_page_index)
    await page.close()
    if self.current_page_index >= len(self.pages):
      self.current_page_index = len(self.pages) - 1
    return {"success": True, "pages_remaining": len(self.pages)}

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

  async def handle_dialog(
    self, action: str, prompt_text: str | None = None
  ) -> dict[str, Any]:
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
