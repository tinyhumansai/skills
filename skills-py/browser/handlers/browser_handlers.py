"""
Tool handlers for browser operations.

Dispatches tool calls to the browser client.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from dev.types.skill_types import ToolResult

log = logging.getLogger("skill.browser.handlers")

# Global browser client (set during on_load)
_browser_client: Any = None


def set_browser_client(client: Any) -> None:
  """Set the global browser client."""
  global _browser_client
  _browser_client = client


async def dispatch_tool(tool_name: str, args: dict[str, Any]) -> ToolResult:
  """Dispatch tool calls to appropriate handlers."""
  global _browser_client

  if not _browser_client:
    return ToolResult(
      content="Browser not initialized. Please wait for browser to start.",
      is_error=True,
    )

  try:
    # Navigation
    if tool_name == "navigate":
      result = await _browser_client.navigate(
        args.get("url"),
        wait_until=args.get("wait_until", "load"),
        timeout=args.get("timeout", 30000),
      )
    elif tool_name == "go_back":
      result = await _browser_client.go_back(timeout=args.get("timeout", 30000))
    elif tool_name == "go_forward":
      result = await _browser_client.go_forward(timeout=args.get("timeout", 30000))
    elif tool_name == "reload":
      result = await _browser_client.reload(
        wait_until=args.get("wait_until", "load"), timeout=args.get("timeout", 30000)
      )
    elif tool_name == "get_url":
      result = await _browser_client.get_url()
    elif tool_name == "get_title":
      result = await _browser_client.get_title()

    # Interaction
    elif tool_name == "click":
      result = await _browser_client.click(
        args.get("selector"),
        button=args.get("button", "left"),
        click_count=args.get("click_count", 1),
        delay=args.get("delay", 0),
        force=args.get("force", False),
      )
    elif tool_name == "fill":
      result = await _browser_client.fill(
        args.get("selector"), args.get("text"), timeout=args.get("timeout", 30000)
      )
    elif tool_name == "type":
      result = await _browser_client.type_text(
        args.get("selector"),
        args.get("text"),
        delay=args.get("delay", 0),
        timeout=args.get("timeout", 30000),
      )
    elif tool_name == "press_key":
      result = await _browser_client.press_key(args.get("key"), delay=args.get("delay", 0))
    elif tool_name == "select_option":
      result = await _browser_client.select_option(
        args.get("selector"),
        value=args.get("value"),
        label=args.get("label"),
        index=args.get("index"),
        multiple=args.get("multiple", False),
      )
    elif tool_name == "check":
      result = await _browser_client.check(args.get("selector"), checked=args.get("checked", True))
    elif tool_name == "hover":
      result = await _browser_client.hover(args.get("selector"), timeout=args.get("timeout", 30000))
    elif tool_name == "scroll":
      result = await _browser_client.scroll(
        selector=args.get("selector"),
        direction=args.get("direction", "down"),
        amount=args.get("amount", 500),
      )

    # Content extraction
    elif tool_name == "get_text":
      result = await _browser_client.get_text(
        selector=args.get("selector"), inner_text=args.get("inner_text", False)
      )
    elif tool_name == "get_html":
      result = await _browser_client.get_html(
        selector=args.get("selector"), outer_html=args.get("outer_html", True)
      )
    elif tool_name == "get_attribute":
      result = await _browser_client.get_attribute(args.get("selector"), args.get("attribute"))
    elif tool_name == "screenshot":
      result = await _browser_client.screenshot(
        selector=args.get("selector"),
        path=args.get("path"),
        full_page=args.get("full_page", False),
        image_type=args.get("type", "png"),
      )

    # JavaScript execution
    elif tool_name == "evaluate":
      result = await _browser_client.evaluate(args.get("script"), arg=args.get("arg"))

    # Waiting
    elif tool_name == "wait_for_selector":
      result = await _browser_client.wait_for_selector(
        args.get("selector"),
        state=args.get("state", "visible"),
        timeout=args.get("timeout", 30000),
      )
    elif tool_name == "wait_for_url":
      result = await _browser_client.wait_for_url(
        args.get("url"), timeout=args.get("timeout", 30000)
      )

    # Cookies
    elif tool_name == "get_cookies":
      result = await _browser_client.get_cookies(urls=args.get("urls"))
    elif tool_name == "set_cookie":
      result = await _browser_client.set_cookie(
        args.get("name"),
        args.get("value"),
        args.get("url"),
        domain=args.get("domain"),
        path=args.get("path", "/"),
        expires=args.get("expires"),
        http_only=args.get("http_only", False),
        secure=args.get("secure", False),
        same_site=args.get("same_site"),
      )
    elif tool_name == "clear_cookies":
      result = await _browser_client.clear_cookies(urls=args.get("urls"))

    # Storage
    elif tool_name == "get_local_storage":
      result = await _browser_client.get_local_storage(key=args.get("key"))
    elif tool_name == "set_local_storage":
      result = await _browser_client.set_local_storage(args.get("key"), args.get("value"))
    elif tool_name == "clear_local_storage":
      result = await _browser_client.clear_local_storage()
    elif tool_name == "get_session_storage":
      result = await _browser_client.get_session_storage(key=args.get("key"))
    elif tool_name == "set_session_storage":
      result = await _browser_client.set_session_storage(args.get("key"), args.get("value"))
    elif tool_name == "clear_session_storage":
      result = await _browser_client.clear_session_storage()

    # Network
    elif tool_name == "intercept_request":
      result = await _browser_client.intercept_request(
        args.get("url_pattern"),
        action=args.get("action", "continue"),
        response_status=args.get("response_status", 200),
        response_body=args.get("response_body"),
        response_headers=args.get("response_headers"),
      )
    elif tool_name == "get_network_logs":
      result = await _browser_client.get_network_logs(
        url_pattern=args.get("url_pattern"),
        method=args.get("method"),
        status=args.get("status"),
      )

    # Pages/tabs
    elif tool_name == "new_page":
      result = await _browser_client.new_page(url=args.get("url"))
    elif tool_name == "get_pages":
      result = await _browser_client.get_pages()
    elif tool_name == "switch_page":
      result = await _browser_client.switch_page(index=args.get("index"), url=args.get("url"))
    elif tool_name == "close_page":
      result = await _browser_client.close_page()

    # Dialogs
    elif tool_name == "handle_dialog":
      result = await _browser_client.handle_dialog(
        args.get("action"), prompt_text=args.get("prompt_text")
      )

    # Files
    elif tool_name == "upload_file":
      result = await _browser_client.upload_file(
        args.get("selector"),
        args.get("file_path"),
        multiple=args.get("multiple", False),
      )
    elif tool_name == "download_file":
      result = await _browser_client.download_file(
        args.get("save_path"), url=args.get("url"), timeout=args.get("timeout", 30000)
      )

    else:
      return ToolResult(
        content=f"Unknown tool: {tool_name}",
        is_error=True,
      )

    # Format result
    if result.get("success"):
      content = json.dumps(result, indent=2)
      return ToolResult(content=content, is_error=False)
    else:
      error_msg = result.get("error", "Unknown error")
      return ToolResult(content=f"Error: {error_msg}", is_error=True)

  except Exception as exc:
    log.exception("Tool execution failed: %s", exc)
    return ToolResult(
      content=f"Error: {exc!s}",
      is_error=True,
    )
