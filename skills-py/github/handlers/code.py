"""Code/file viewing tool handlers."""

from __future__ import annotations

import base64
from typing import Any

from ..client.gh_client import get_client, run_sync
from ..helpers import ErrorCategory, ToolResult, log_and_format_error, truncate
from ..validation import opt_string, req_string, validate_repo_spec


async def view_file(args: dict[str, Any]) -> ToolResult:
  try:
    spec = validate_repo_spec(args)
    path = req_string(args, "path")
    ref = opt_string(args, "ref")

    gh = get_client().gh
    repo = await run_sync(gh.get_repo, spec)

    kwargs: dict[str, Any] = {}
    if ref:
      kwargs["ref"] = ref
    content_file = await run_sync(repo.get_contents, path, **kwargs)

    if isinstance(content_file, list):
      return ToolResult(content=f"{path} is a directory, not a file. Use list_directory instead.")

    if content_file.encoding == "base64" and content_file.content:
      decoded = base64.b64decode(content_file.content).decode("utf-8", errors="replace")
      return ToolResult(content=truncate(decoded))
    elif content_file.decoded_content:
      return ToolResult(
        content=truncate(content_file.decoded_content.decode("utf-8", errors="replace"))
      )
    else:
      return ToolResult(content="(binary or empty file)")
  except Exception as e:
    return log_and_format_error("view_file", e, ErrorCategory.CODE)


async def list_directory(args: dict[str, Any]) -> ToolResult:
  try:
    spec = validate_repo_spec(args)
    path = opt_string(args, "path") or ""
    ref = opt_string(args, "ref")

    gh = get_client().gh
    repo = await run_sync(gh.get_repo, spec)

    kwargs: dict[str, Any] = {}
    if ref:
      kwargs["ref"] = ref
    contents = await run_sync(repo.get_contents, path or "/", **kwargs)

    if not isinstance(contents, list):
      # Single file
      return ToolResult(content=f"{path} is a file, not a directory.")

    lines = []
    for entry in sorted(contents, key=lambda e: (e.type != "dir", e.name)):
      indicator = "/" if entry.type == "dir" else ""
      size_str = f" ({entry.size} bytes)" if entry.type == "file" and entry.size else ""
      lines.append(f"{entry.type:4s} {entry.name}{indicator}{size_str}")
    return ToolResult(content="\n".join(lines) or "Empty directory.")
  except Exception as e:
    return log_and_format_error("list_directory", e, ErrorCategory.CODE)


async def get_readme(args: dict[str, Any]) -> ToolResult:
  try:
    spec = validate_repo_spec(args)
    gh = get_client().gh
    repo = await run_sync(gh.get_repo, spec)
    readme = await run_sync(repo.get_readme)

    if readme.decoded_content:
      content = readme.decoded_content.decode("utf-8", errors="replace")
      return ToolResult(content=truncate(content))
    return ToolResult(content="(empty README)")
  except Exception as e:
    return log_and_format_error("get_readme", e, ErrorCategory.CODE)
