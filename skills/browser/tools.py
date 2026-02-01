"""
Tool definitions for the browser skill.

Comprehensive browser automation tools for navigating, interacting,
and controlling web browsers via Playwright.
"""

from __future__ import annotations

from mcp.types import Tool

ALL_TOOLS: list[Tool] = [
  Tool(
    name="navigate",
    description="Navigate to a URL in the browser",
    inputSchema={
      "type": "object",
      "properties": {
        "url": {
          "type": "string",
          "description": "URL to navigate to",
        },
        "wait_until": {
          "type": "string",
          "enum": ["load", "domcontentloaded", "networkidle", "commit"],
          "description": "When to consider navigation successful",
          "default": "load",
        },
        "timeout": {
          "type": "number",
          "description": "Navigation timeout in milliseconds",
          "default": 30000,
        },
      },
      "required": ["url"],
    },
  ),
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
  Tool(
    name="screenshot",
    description="Take a screenshot of the page or element",
    inputSchema={
      "type": "object",
      "properties": {
        "selector": {
          "type": "string",
          "description": "CSS selector for element to screenshot (optional, full page if omitted)",
        },
        "path": {
          "type": "string",
          "description": "File path to save screenshot (optional, returns base64 if omitted)",
        },
        "full_page": {
          "type": "boolean",
          "description": "Capture full scrollable page",
          "default": False,
        },
        "type": {
          "type": "string",
          "enum": ["png", "jpeg"],
          "description": "Image format",
          "default": "png",
        },
      },
      "required": [],
    },
  ),
  Tool(
    name="get_text",
    description="Get text content from an element or page",
    inputSchema={
      "type": "object",
      "properties": {
        "selector": {
          "type": "string",
          "description": "CSS selector for element (optional, gets page text if omitted)",
        },
        "inner_text": {
          "type": "boolean",
          "description": "Get innerText instead of textContent",
          "default": False,
        },
      },
      "required": [],
    },
  ),
  Tool(
    name="get_html",
    description="Get HTML content from an element or page",
    inputSchema={
      "type": "object",
      "properties": {
        "selector": {
          "type": "string",
          "description": "CSS selector for element (optional, gets page HTML if omitted)",
        },
        "outer_html": {
          "type": "boolean",
          "description": "Include the element itself in HTML",
          "default": True,
        },
      },
      "required": [],
    },
  ),
  Tool(
    name="get_attribute",
    description="Get an attribute value from an element",
    inputSchema={
      "type": "object",
      "properties": {
        "selector": {
          "type": "string",
          "description": "CSS selector for the element",
        },
        "attribute": {
          "type": "string",
          "description": "Attribute name (e.g., 'href', 'src', 'class')",
        },
      },
      "required": ["selector", "attribute"],
    },
  ),
  Tool(
    name="evaluate",
    description="Execute JavaScript in the page context and return the result",
    inputSchema={
      "type": "object",
      "properties": {
        "script": {
          "type": "string",
          "description": "JavaScript code to execute",
        },
        "arg": {
          "description": "Argument to pass to the script (will be available as 'arg' in script)",
        },
      },
      "required": ["script"],
    },
  ),
  Tool(
    name="wait_for_selector",
    description="Wait for an element to appear on the page",
    inputSchema={
      "type": "object",
      "properties": {
        "selector": {
          "type": "string",
          "description": "CSS selector to wait for",
        },
        "state": {
          "type": "string",
          "enum": ["attached", "detached", "visible", "hidden"],
          "description": "Element state to wait for",
          "default": "visible",
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
    name="wait_for_url",
    description="Wait for the page URL to match a pattern",
    inputSchema={
      "type": "object",
      "properties": {
        "url": {
          "type": "string",
          "description": "URL pattern (supports glob or regex)",
        },
        "timeout": {
          "type": "number",
          "description": "Timeout in milliseconds",
          "default": 30000,
        },
      },
      "required": ["url"],
    },
  ),
  Tool(
    name="get_cookies",
    description="Get all cookies for the current page",
    inputSchema={
      "type": "object",
      "properties": {
        "urls": {
          "type": "array",
          "items": {"type": "string"},
          "description": "Optional list of URLs to get cookies for",
        },
      },
      "required": [],
    },
  ),
  Tool(
    name="set_cookie",
    description="Set a cookie",
    inputSchema={
      "type": "object",
      "properties": {
        "name": {
          "type": "string",
          "description": "Cookie name",
        },
        "value": {
          "type": "string",
          "description": "Cookie value",
        },
        "url": {
          "type": "string",
          "description": "URL to set cookie for",
        },
        "domain": {
          "type": "string",
          "description": "Cookie domain",
        },
        "path": {
          "type": "string",
          "description": "Cookie path",
          "default": "/",
        },
        "expires": {
          "type": "number",
          "description": "Cookie expiration timestamp (Unix seconds)",
        },
        "http_only": {
          "type": "boolean",
          "description": "HTTP-only flag",
          "default": False,
        },
        "secure": {
          "type": "boolean",
          "description": "Secure flag (HTTPS only)",
          "default": False,
        },
        "same_site": {
          "type": "string",
          "enum": ["Strict", "Lax", "None"],
          "description": "SameSite attribute",
        },
      },
      "required": ["name", "value", "url"],
    },
  ),
  Tool(
    name="clear_cookies",
    description="Clear all cookies",
    inputSchema={
      "type": "object",
      "properties": {
        "urls": {
          "type": "array",
          "items": {"type": "string"},
          "description": "Optional list of URLs to clear cookies for",
        },
      },
      "required": [],
    },
  ),
  Tool(
    name="get_local_storage",
    description="Get localStorage value",
    inputSchema={
      "type": "object",
      "properties": {
        "key": {
          "type": "string",
          "description": "localStorage key (optional, returns all if omitted)",
        },
      },
      "required": [],
    },
  ),
  Tool(
    name="set_local_storage",
    description="Set localStorage value",
    inputSchema={
      "type": "object",
      "properties": {
        "key": {
          "type": "string",
          "description": "localStorage key",
        },
        "value": {
          "type": "string",
          "description": "localStorage value",
        },
      },
      "required": ["key", "value"],
    },
  ),
  Tool(
    name="clear_local_storage",
    description="Clear all localStorage",
    inputSchema={
      "type": "object",
      "properties": {},
      "required": [],
    },
  ),
  Tool(
    name="get_session_storage",
    description="Get sessionStorage value",
    inputSchema={
      "type": "object",
      "properties": {
        "key": {
          "type": "string",
          "description": "sessionStorage key (optional, returns all if omitted)",
        },
      },
      "required": [],
    },
  ),
  Tool(
    name="set_session_storage",
    description="Set sessionStorage value",
    inputSchema={
      "type": "object",
      "properties": {
        "key": {
          "type": "string",
          "description": "sessionStorage key",
        },
        "value": {
          "type": "string",
          "description": "sessionStorage value",
        },
      },
      "required": ["key", "value"],
    },
  ),
  Tool(
    name="clear_session_storage",
    description="Clear all sessionStorage",
    inputSchema={
      "type": "object",
      "properties": {},
      "required": [],
    },
  ),
  Tool(
    name="intercept_request",
    description="Intercept and modify network requests",
    inputSchema={
      "type": "object",
      "properties": {
        "url_pattern": {
          "type": "string",
          "description": "URL pattern to intercept (supports glob or regex)",
        },
        "action": {
          "type": "string",
          "enum": ["abort", "continue", "fulfill", "respond"],
          "description": "Action to take: abort, continue, fulfill with custom response, or respond with custom data",
          "default": "continue",
        },
        "response_status": {
          "type": "number",
          "description": "HTTP status code for fulfill/respond action",
          "default": 200,
        },
        "response_body": {
          "type": "string",
          "description": "Response body for fulfill/respond action",
        },
        "response_headers": {
          "type": "object",
          "description": "Custom response headers",
        },
      },
      "required": ["url_pattern"],
    },
  ),
  Tool(
    name="get_network_logs",
    description="Get network request/response logs",
    inputSchema={
      "type": "object",
      "properties": {
        "url_pattern": {
          "type": "string",
          "description": "Filter logs by URL pattern (optional)",
        },
        "method": {
          "type": "string",
          "description": "Filter by HTTP method (optional)",
        },
        "status": {
          "type": "number",
          "description": "Filter by status code (optional)",
        },
      },
      "required": [],
    },
  ),
  Tool(
    name="go_back",
    description="Navigate back in browser history",
    inputSchema={
      "type": "object",
      "properties": {
        "timeout": {
          "type": "number",
          "description": "Navigation timeout in milliseconds",
          "default": 30000,
        },
      },
      "required": [],
    },
  ),
  Tool(
    name="go_forward",
    description="Navigate forward in browser history",
    inputSchema={
      "type": "object",
      "properties": {
        "timeout": {
          "type": "number",
          "description": "Navigation timeout in milliseconds",
          "default": 30000,
        },
      },
      "required": [],
    },
  ),
  Tool(
    name="reload",
    description="Reload the current page",
    inputSchema={
      "type": "object",
      "properties": {
        "wait_until": {
          "type": "string",
          "enum": ["load", "domcontentloaded", "networkidle", "commit"],
          "description": "When to consider reload successful",
          "default": "load",
        },
        "timeout": {
          "type": "number",
          "description": "Navigation timeout in milliseconds",
          "default": 30000,
        },
      },
      "required": [],
    },
  ),
  Tool(
    name="get_url",
    description="Get the current page URL",
    inputSchema={
      "type": "object",
      "properties": {},
      "required": [],
    },
  ),
  Tool(
    name="get_title",
    description="Get the current page title",
    inputSchema={
      "type": "object",
      "properties": {},
      "required": [],
    },
  ),
  Tool(
    name="close_page",
    description="Close the current page",
    inputSchema={
      "type": "object",
      "properties": {},
      "required": [],
    },
  ),
  Tool(
    name="new_page",
    description="Open a new page/tab",
    inputSchema={
      "type": "object",
      "properties": {
        "url": {
          "type": "string",
          "description": "URL to navigate to in the new page (optional)",
        },
      },
      "required": [],
    },
  ),
  Tool(
    name="get_pages",
    description="Get list of all open pages/tabs",
    inputSchema={
      "type": "object",
      "properties": {},
      "required": [],
    },
  ),
  Tool(
    name="switch_page",
    description="Switch to a different page/tab",
    inputSchema={
      "type": "object",
      "properties": {
        "index": {
          "type": "number",
          "description": "Page index (0-based)",
        },
        "url": {
          "type": "string",
          "description": "Page URL to switch to (alternative to index)",
        },
      },
      "required": [],
    },
  ),
  Tool(
    name="handle_dialog",
    description="Handle browser dialogs (alert, confirm, prompt)",
    inputSchema={
      "type": "object",
      "properties": {
        "action": {
          "type": "string",
          "enum": ["accept", "dismiss"],
          "description": "Whether to accept or dismiss the dialog",
          "default": "accept",
        },
        "prompt_text": {
          "type": "string",
          "description": "Text to enter for prompt dialogs",
        },
      },
      "required": ["action"],
    },
  ),
  Tool(
    name="upload_file",
    description="Upload a file to a file input",
    inputSchema={
      "type": "object",
      "properties": {
        "selector": {
          "type": "string",
          "description": "CSS selector for the file input element",
        },
        "file_path": {
          "type": "string",
          "description": "Path to the file to upload",
        },
        "multiple": {
          "type": "boolean",
          "description": "Whether to upload multiple files",
          "default": False,
        },
      },
      "required": ["selector", "file_path"],
    },
  ),
  Tool(
    name="download_file",
    description="Wait for and download a file",
    inputSchema={
      "type": "object",
      "properties": {
        "url": {
          "type": "string",
          "description": "URL to download (optional, waits for next download if omitted)",
        },
        "save_path": {
          "type": "string",
          "description": "Path to save the downloaded file",
        },
        "timeout": {
          "type": "number",
          "description": "Timeout in milliseconds",
          "default": 30000,
        },
      },
      "required": ["save_path"],
    },
  ),
]
