"""
Other browser tools (dialogs, file upload/download).
"""

from __future__ import annotations

from mcp.types import Tool

OTHER_TOOLS: list[Tool] = [
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
