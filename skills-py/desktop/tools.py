"""
Tool definitions for the desktop automation skill.

Comprehensive mouse and keyboard control tools for autonomous desktop navigation.
"""

from __future__ import annotations

from mcp.types import Tool

ALL_TOOLS: list[Tool] = [
  Tool(
    name="mouse_move",
    description="Move the mouse cursor to absolute coordinates or relative to current position",
    inputSchema={
      "type": "object",
      "properties": {
        "x": {
          "type": "number",
          "description": "X coordinate (absolute if absolute=true, relative if absolute=false)",
        },
        "y": {
          "type": "number",
          "description": "Y coordinate (absolute if absolute=true, relative if absolute=false)",
        },
        "absolute": {
          "type": "boolean",
          "description": "Whether coordinates are absolute (screen coordinates) or relative to current position",
          "default": True,
        },
        "duration": {
          "type": "number",
          "description": "Duration of movement in seconds (for smooth movement)",
          "default": 0,
        },
      },
      "required": ["x", "y"],
    },
  ),
  Tool(
    name="mouse_click",
    description="Click the mouse button at current position or specified coordinates",
    inputSchema={
      "type": "object",
      "properties": {
        "button": {
          "type": "string",
          "enum": ["left", "right", "middle"],
          "description": "Mouse button to click",
          "default": "left",
        },
        "clicks": {
          "type": "number",
          "description": "Number of clicks",
          "default": 1,
        },
        "x": {
          "type": "number",
          "description": "X coordinate to click at (optional, uses current position if omitted)",
        },
        "y": {
          "type": "number",
          "description": "Y coordinate to click at (optional, uses current position if omitted)",
        },
        "interval": {
          "type": "number",
          "description": "Interval between clicks in seconds",
          "default": 0.1,
        },
      },
      "required": [],
    },
  ),
  Tool(
    name="mouse_press",
    description="Press down a mouse button (without releasing)",
    inputSchema={
      "type": "object",
      "properties": {
        "button": {
          "type": "string",
          "enum": ["left", "right", "middle"],
          "description": "Mouse button to press",
          "default": "left",
        },
      },
      "required": ["button"],
    },
  ),
  Tool(
    name="mouse_release",
    description="Release a mouse button",
    inputSchema={
      "type": "object",
      "properties": {
        "button": {
          "type": "string",
          "enum": ["left", "right", "middle"],
          "description": "Mouse button to release",
          "default": "left",
        },
      },
      "required": ["button"],
    },
  ),
  Tool(
    name="mouse_scroll",
    description="Scroll the mouse wheel vertically or horizontally",
    inputSchema={
      "type": "object",
      "properties": {
        "dx": {
          "type": "number",
          "description": "Horizontal scroll amount (positive = right, negative = left)",
          "default": 0,
        },
        "dy": {
          "type": "number",
          "description": "Vertical scroll amount (positive = up, negative = down)",
          "default": 0,
        },
        "x": {
          "type": "number",
          "description": "X coordinate to scroll at (optional, uses current position if omitted)",
        },
        "y": {
          "type": "number",
          "description": "Y coordinate to scroll at (optional, uses current position if omitted)",
        },
      },
      "required": [],
    },
  ),
  Tool(
    name="mouse_drag",
    description="Drag the mouse from one position to another while holding a button",
    inputSchema={
      "type": "object",
      "properties": {
        "x1": {
          "type": "number",
          "description": "Starting X coordinate",
        },
        "y1": {
          "type": "number",
          "description": "Starting Y coordinate",
        },
        "x2": {
          "type": "number",
          "description": "Ending X coordinate",
        },
        "y2": {
          "type": "number",
          "description": "Ending Y coordinate",
        },
        "button": {
          "type": "string",
          "enum": ["left", "right", "middle"],
          "description": "Mouse button to hold during drag",
          "default": "left",
        },
        "duration": {
          "type": "number",
          "description": "Duration of drag in seconds",
          "default": 0.5,
        },
      },
      "required": ["x1", "y1", "x2", "y2"],
    },
  ),
  Tool(
    name="mouse_position",
    description="Get the current mouse cursor position",
    inputSchema={
      "type": "object",
      "properties": {},
      "required": [],
    },
  ),
  Tool(
    name="keyboard_type",
    description="Type text character by character (simulates real typing)",
    inputSchema={
      "type": "object",
      "properties": {
        "text": {
          "type": "string",
          "description": "Text to type",
        },
        "interval": {
          "type": "number",
          "description": "Interval between keystrokes in seconds",
          "default": 0.05,
        },
      },
      "required": ["text"],
    },
  ),
  Tool(
    name="keyboard_press",
    description="Press a keyboard key (without releasing)",
    inputSchema={
      "type": "object",
      "properties": {
        "key": {
          "type": "string",
          "description": "Key to press (e.g., 'a', 'enter', 'ctrl', 'shift', 'alt', 'space', 'tab', 'esc', 'backspace', 'delete', 'up', 'down', 'left', 'right', 'f1'-'f12')",
        },
      },
      "required": ["key"],
    },
  ),
  Tool(
    name="keyboard_release",
    description="Release a keyboard key",
    inputSchema={
      "type": "object",
      "properties": {
        "key": {
          "type": "string",
          "description": "Key to release (e.g., 'a', 'enter', 'ctrl', 'shift', 'alt', 'space', 'tab', 'esc', 'backspace', 'delete', 'up', 'down', 'left', 'right', 'f1'-'f12')",
        },
      },
      "required": ["key"],
    },
  ),
  Tool(
    name="keyboard_tap",
    description="Press and release a keyboard key (single key press)",
    inputSchema={
      "type": "object",
      "properties": {
        "key": {
          "type": "string",
          "description": "Key to tap (e.g., 'a', 'enter', 'ctrl', 'shift', 'alt', 'space', 'tab', 'esc', 'backspace', 'delete', 'up', 'down', 'left', 'right', 'f1'-'f12')",
        },
      },
      "required": ["key"],
    },
  ),
  Tool(
    name="keyboard_hotkey",
    description="Press a combination of keys simultaneously (e.g., Ctrl+C, Alt+Tab)",
    inputSchema={
      "type": "object",
      "properties": {
        "keys": {
          "type": "array",
          "items": {"type": "string"},
          "description": "List of keys to press simultaneously (e.g., ['ctrl', 'c'] for Ctrl+C)",
        },
      },
      "required": ["keys"],
    },
  ),
  Tool(
    name="keyboard_write",
    description="Write text instantly (faster than type, but less realistic)",
    inputSchema={
      "type": "object",
      "properties": {
        "text": {
          "type": "string",
          "description": "Text to write",
        },
      },
      "required": ["text"],
    },
  ),
  Tool(
    name="screen_capture",
    description="Capture a screenshot of the entire screen or a specific region",
    inputSchema={
      "type": "object",
      "properties": {
        "x": {
          "type": "number",
          "description": "Left coordinate of region to capture (optional, captures full screen if omitted)",
        },
        "y": {
          "type": "number",
          "description": "Top coordinate of region to capture (optional, captures full screen if omitted)",
        },
        "width": {
          "type": "number",
          "description": "Width of region to capture (optional, captures full screen if omitted)",
        },
        "height": {
          "type": "number",
          "description": "Height of region to capture (optional, captures full screen if omitted)",
        },
        "save_path": {
          "type": "string",
          "description": "File path to save screenshot (optional, returns base64 if omitted)",
        },
      },
      "required": [],
    },
  ),
  Tool(
    name="screen_size",
    description="Get the screen size (resolution)",
    inputSchema={
      "type": "object",
      "properties": {},
      "required": [],
    },
  ),
  Tool(
    name="wait",
    description="Wait for a specified duration (useful for timing automation)",
    inputSchema={
      "type": "object",
      "properties": {
        "seconds": {
          "type": "number",
          "description": "Number of seconds to wait",
        },
      },
      "required": ["seconds"],
    },
  ),
]
