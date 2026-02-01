"""
Element interaction tools (click, fill, type, etc.).
"""

from __future__ import annotations

from mcp.types import Tool

INTERACTION_TOOLS: list[Tool] = [
  Tool(
    name="click",
    description="Click an element on the page by selector, text, or coordinates",
    inputSchema={
      "type": "object",
      "properties": {
        "selector": {
          "type": "string",
          "description": "CSS selector, text content, or 'xpath:' prefix for XPath",
        },
        "button": {
          "type": "string",
          "enum": ["left", "right", "middle"],
          "description": "Mouse button to use",
          "default": "left",
        },
        "click_count": {
          "type": "number",
          "description": "Number of clicks",
          "default": 1,
        },
        "delay": {
          "type": "number",
          "description": "Delay between mousedown and mouseup in milliseconds",
          "default": 0,
        },
        "force": {
          "type": "boolean",
          "description": "Force click even if element is not visible",
          "default": False,
        },
      },
      "required": ["selector"],
    },
  ),
  Tool(
    name="fill",
    description="Fill an input field with text (clears existing content first)",
    inputSchema={
      "type": "object",
      "properties": {
        "selector": {
          "type": "string",
          "description": "CSS selector for the input element",
        },
        "text": {
          "type": "string",
          "description": "Text to fill",
        },
        "timeout": {
          "type": "number",
          "description": "Timeout in milliseconds",
          "default": 30000,
        },
      },
      "required": ["selector", "text"],
    },
  ),
  Tool(
    name="type",
    description="Type text into an element character by character (simulates real typing)",
    inputSchema={
      "type": "object",
      "properties": {
        "selector": {
          "type": "string",
          "description": "CSS selector for the element",
        },
        "text": {
          "type": "string",
          "description": "Text to type",
        },
        "delay": {
          "type": "number",
          "description": "Delay between keystrokes in milliseconds",
          "default": 0,
        },
        "timeout": {
          "type": "number",
          "description": "Timeout in milliseconds",
          "default": 30000,
        },
      },
      "required": ["selector", "text"],
    },
  ),
  Tool(
    name="press_key",
    description="Press a keyboard key (e.g., Enter, Escape, Tab, Arrow keys)",
    inputSchema={
      "type": "object",
      "properties": {
        "key": {
          "type": "string",
          "description": "Key to press (e.g., 'Enter', 'Escape', 'Tab', 'ArrowDown', 'Control+a')",
        },
        "delay": {
          "type": "number",
          "description": "Delay before releasing the key in milliseconds",
          "default": 0,
        },
      },
      "required": ["key"],
    },
  ),
  Tool(
    name="select_option",
    description="Select option(s) in a select dropdown",
    inputSchema={
      "type": "object",
      "properties": {
        "selector": {
          "type": "string",
          "description": "CSS selector for the select element",
        },
        "value": {
          "type": "string",
          "description": "Option value to select",
        },
        "label": {
          "type": "string",
          "description": "Option label to select (alternative to value)",
        },
        "index": {
          "type": "number",
          "description": "Option index to select (0-based)",
        },
        "multiple": {
          "type": "boolean",
          "description": "Whether to allow multiple selections",
          "default": False,
        },
      },
      "required": ["selector"],
    },
  ),
  Tool(
    name="check",
    description="Check a checkbox or radio button",
    inputSchema={
      "type": "object",
      "properties": {
        "selector": {
          "type": "string",
          "description": "CSS selector for the checkbox/radio",
        },
        "checked": {
          "type": "boolean",
          "description": "Whether to check or uncheck",
          "default": True,
        },
      },
      "required": ["selector"],
    },
  ),
  Tool(
    name="hover",
    description="Hover over an element",
    inputSchema={
      "type": "object",
      "properties": {
        "selector": {
          "type": "string",
          "description": "CSS selector for the element",
        },
        "timeout": {
          "type": "number",
          "description": "Timeout in milliseconds",
          "default": 30000,
        },
      },
      "required": ["selector"],
    },
  ),
  Tool(
    name="scroll",
    description="Scroll the page or an element",
    inputSchema={
      "type": "object",
      "properties": {
        "selector": {
          "type": "string",
          "description": "CSS selector for element to scroll (optional, scrolls page if omitted)",
        },
        "direction": {
          "type": "string",
          "enum": ["up", "down", "left", "right"],
          "description": "Scroll direction",
          "default": "down",
        },
        "amount": {
          "type": "number",
          "description": "Number of pixels to scroll",
          "default": 500,
        },
      },
      "required": [],
    },
  ),
]
