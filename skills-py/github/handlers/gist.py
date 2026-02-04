"""Gist domain tool handlers."""

from __future__ import annotations

from typing import Any

from github import InputFileContent

from ..client.gh_client import get_client, run_sync
from ..helpers import ErrorCategory, ToolResult, log_and_format_error, truncate
from ..validation import opt_boolean, opt_number, opt_string, req_string


async def list_gists(args: dict[str, Any]) -> ToolResult:
  try:
    limit = opt_number(args, "limit", 20)
    username = opt_string(args, "username")

    gh = get_client().gh
    if username:
      user = await run_sync(gh.get_user, username)
    else:
      user = await run_sync(gh.get_user)
    gists = await run_sync(user.get_gists)
    items = await run_sync(lambda: list(gists[:limit]))

    if not items:
      return ToolResult(content="No gists found.")
    lines = []
    for g in items:
      files = list(g.files.keys()) if g.files else []
      file_str = ", ".join(files[:3])
      if len(files) > 3:
        file_str += f" (+{len(files) - 3} more)"
      public = "public" if g.public else "private"
      desc = (g.description or "")[:60]
      lines.append(f"{g.id} [{public}] {file_str}" + (f" - {desc}" if desc else ""))
    return ToolResult(content="\n".join(lines))
  except Exception as e:
    return log_and_format_error("list_gists", e, ErrorCategory.GIST)


async def get_gist(args: dict[str, Any]) -> ToolResult:
  try:
    gist_id = req_string(args, "gist_id")
    gh = get_client().gh
    gist = await run_sync(gh.get_gist, gist_id)

    owner = gist.owner.login if gist.owner else ""
    files = list(gist.files.keys()) if gist.files else []
    public = "public" if gist.public else "private"

    lines = [
      f"Gist: {gist.id}",
      f"URL: {gist.html_url}",
      f"Owner: @{owner}" if owner else "",
      f"Visibility: {public}",
      f"Description: {gist.description or 'N/A'}",
      f"Files: {', '.join(files)}",
      f"Comments: {gist.comments}",
      f"Created: {gist.created_at}",
      f"Updated: {gist.updated_at}",
    ]

    # Show file contents
    for fname, fobj in (gist.files or {}).items():
      content = fobj.content or ""
      lines.append(f"\n--- {fname} ({fobj.language or 'text'}, {fobj.size} bytes) ---")
      lines.append(truncate(content, 1500))

    return ToolResult(content="\n".join(l for l in lines if l or l == ""))
  except Exception as e:
    return log_and_format_error("get_gist", e, ErrorCategory.GIST)


async def create_gist(args: dict[str, Any]) -> ToolResult:
  try:
    description = opt_string(args, "description") or ""
    public = opt_boolean(args, "public", False)
    files_arg = args.get("files", {})

    if not isinstance(files_arg, dict) or not files_arg:
      return ToolResult(content="files must be a dict of {filename: content}.", is_error=True)

    gh = get_client().gh
    user = await run_sync(gh.get_user)

    input_files = {
      name: InputFileContent(content=str(content)) for name, content in files_arg.items()
    }

    gist = await run_sync(user.create_gist, public, input_files, description)
    return ToolResult(content=f"Gist created: {gist.html_url}")
  except Exception as e:
    return log_and_format_error("create_gist", e, ErrorCategory.GIST)


async def edit_gist(args: dict[str, Any]) -> ToolResult:
  try:
    gist_id = req_string(args, "gist_id")
    description = opt_string(args, "description")
    files_arg = args.get("files")

    gh = get_client().gh
    gist = await run_sync(gh.get_gist, gist_id)

    kwargs: dict[str, Any] = {}
    if description is not None:
      kwargs["description"] = description
    if isinstance(files_arg, dict) and files_arg:
      input_files = {
        name: InputFileContent(content=str(content)) for name, content in files_arg.items()
      }
      kwargs["files"] = input_files

    if not kwargs:
      return ToolResult(content="Provide description or files to edit.", is_error=True)

    await run_sync(gist.edit, **kwargs)
    return ToolResult(content=f"Gist {gist_id} updated.")
  except Exception as e:
    return log_and_format_error("edit_gist", e, ErrorCategory.GIST)


async def delete_gist(args: dict[str, Any]) -> ToolResult:
  try:
    gist_id = req_string(args, "gist_id")
    gh = get_client().gh
    gist = await run_sync(gh.get_gist, gist_id)
    await run_sync(gist.delete)
    return ToolResult(content=f"Gist {gist_id} deleted.")
  except Exception as e:
    return log_and_format_error("delete_gist", e, ErrorCategory.GIST)


async def clone_gist(args: dict[str, Any]) -> ToolResult:
  try:
    gist_id = req_string(args, "gist_id")
    gh = get_client().gh
    gist = await run_sync(gh.get_gist, gist_id)
    return ToolResult(
      content=f"Clone URL: {gist.git_pull_url}\n\nRun: git clone {gist.git_pull_url}"
    )
  except Exception as e:
    return log_and_format_error("clone_gist", e, ErrorCategory.GIST)
