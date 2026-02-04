"""
Folder domain tool handlers.
"""

from __future__ import annotations

from typing import Any

from ..api import folder_api
from ..helpers import ErrorCategory, ToolResult, log_and_format_error
from ..validation import opt_string, req_string


async def list_folders(args: dict[str, Any]) -> ToolResult:
  try:
    pattern = opt_string(args, "pattern")
    folders = await folder_api.list_folders(pattern)
    if not folders:
      return ToolResult(content="No folders found.")
    lines = [f"{f['name']} (flags: {', '.join(f.get('flags', []))})" for f in folders]
    return ToolResult(content="\n".join(lines))
  except Exception as e:
    return log_and_format_error("list_folders", e, ErrorCategory.FOLDER)


async def get_folder_status(args: dict[str, Any]) -> ToolResult:
  try:
    folder = req_string(args, "folder")
    status = await folder_api.get_folder_status(folder)
    lines = [
      f"Folder: {folder}",
      f"Total messages: {status.get('exists', 0)}",
      f"Recent: {status.get('recent', 0)}",
      f"Unseen: {status.get('unseen', 'N/A')}",
      f"UIDVALIDITY: {status.get('uidvalidity', 0)}",
      f"UIDNEXT: {status.get('uidnext', 0)}",
    ]
    return ToolResult(content="\n".join(lines))
  except Exception as e:
    return log_and_format_error("get_folder_status", e, ErrorCategory.FOLDER)


async def create_folder(args: dict[str, Any]) -> ToolResult:
  try:
    folder = req_string(args, "folder")
    result = await folder_api.create_folder(folder)
    if result:
      return ToolResult(content=f'Folder "{folder}" created successfully.')
    return ToolResult(content=f'Failed to create folder "{folder}".', is_error=True)
  except Exception as e:
    return log_and_format_error("create_folder", e, ErrorCategory.FOLDER)


async def rename_folder(args: dict[str, Any]) -> ToolResult:
  try:
    old_name = req_string(args, "old_name")
    new_name = req_string(args, "new_name")
    result = await folder_api.rename_folder(old_name, new_name)
    if result:
      return ToolResult(content=f'Folder renamed from "{old_name}" to "{new_name}".')
    return ToolResult(content="Failed to rename folder.", is_error=True)
  except Exception as e:
    return log_and_format_error("rename_folder", e, ErrorCategory.FOLDER)


async def delete_folder(args: dict[str, Any]) -> ToolResult:
  try:
    folder = req_string(args, "folder")
    result = await folder_api.delete_folder(folder)
    if result:
      return ToolResult(content=f'Folder "{folder}" deleted.')
    return ToolResult(content=f'Failed to delete folder "{folder}".', is_error=True)
  except Exception as e:
    return log_and_format_error("delete_folder", e, ErrorCategory.FOLDER)
