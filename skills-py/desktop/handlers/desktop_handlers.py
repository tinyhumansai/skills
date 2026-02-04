"""
Tool handlers for desktop automation operations.

Dispatches tool calls to the desktop client.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from dev.types.skill_types import ToolResult

log = logging.getLogger("skill.desktop.handlers")

# Global desktop client (set during on_load)
_desktop_client: Any = None


def set_desktop_client(client: Any) -> None:
  """Set the global desktop client."""
  global _desktop_client
  _desktop_client = client


async def dispatch_tool(tool_name: str, args: dict[str, Any]) -> ToolResult:
  """Dispatch tool calls to appropriate handlers."""
  global _desktop_client

  if not _desktop_client:
    return ToolResult(
      content="Desktop client not initialized. Please wait for client to start.",
      is_error=True,
    )

  try:
    # Mouse operations
    if tool_name == "mouse_move":
      result = _desktop_client.mouse_move(
        args.get("x"),
        args.get("y"),
        absolute=args.get("absolute", True),
        duration=args.get("duration", 0),
      )
    elif tool_name == "mouse_click":
      result = _desktop_client.mouse_click(
        button=args.get("button", "left"),
        clicks=args.get("clicks", 1),
        x=args.get("x"),
        y=args.get("y"),
        interval=args.get("interval", 0.1),
      )
    elif tool_name == "mouse_press":
      result = _desktop_client.mouse_press(button=args.get("button", "left"))
    elif tool_name == "mouse_release":
      result = _desktop_client.mouse_release(button=args.get("button", "left"))
    elif tool_name == "mouse_scroll":
      result = _desktop_client.mouse_scroll(
        dx=args.get("dx", 0),
        dy=args.get("dy", 0),
        x=args.get("x"),
        y=args.get("y"),
      )
    elif tool_name == "mouse_drag":
      result = _desktop_client.mouse_drag(
        args.get("x1"),
        args.get("y1"),
        args.get("x2"),
        args.get("y2"),
        button=args.get("button", "left"),
        duration=args.get("duration", 0.5),
      )
    elif tool_name == "mouse_position":
      result = _desktop_client.mouse_position()

    # Keyboard operations
    elif tool_name == "keyboard_type":
      result = _desktop_client.keyboard_type(args.get("text"), interval=args.get("interval", 0.05))
    elif tool_name == "keyboard_press":
      result = _desktop_client.keyboard_press(args.get("key"))
    elif tool_name == "keyboard_release":
      result = _desktop_client.keyboard_release(args.get("key"))
    elif tool_name == "keyboard_tap":
      result = _desktop_client.keyboard_tap(args.get("key"))
    elif tool_name == "keyboard_hotkey":
      result = _desktop_client.keyboard_hotkey(args.get("keys", []))
    elif tool_name == "keyboard_write":
      result = _desktop_client.keyboard_write(args.get("text"))

    # Screen operations
    elif tool_name == "screen_capture":
      result = _desktop_client.screen_capture(
        x=args.get("x"),
        y=args.get("y"),
        width=args.get("width"),
        height=args.get("height"),
        save_path=args.get("save_path"),
      )
    elif tool_name == "screen_size":
      result = _desktop_client.screen_size()

    # Utility operations
    elif tool_name == "wait":
      result = _desktop_client.wait(args.get("seconds"))

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
