"""
GitHub SkillDefinition — wires setup, tools, and lifecycle hooks
into the unified SkillServer protocol.

Usage:
    from skills.github.skill import skill
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

from dev.types.skill_types import (
  SkillDefinition,
  SkillHooks,
  SkillOptionDefinition,
  SkillTool,
  ToolDefinition,
)
from dev.types.skill_types import (
  ToolResult as SkillToolResult,
)

from .handlers import dispatch_tool
from .setup import on_setup_cancel, on_setup_start, on_setup_submit
from .tools import ALL_TOOLS

log = logging.getLogger("skill.github.skill")


# ---------------------------------------------------------------------------
# Convert MCP Tool objects → SkillTool objects
# ---------------------------------------------------------------------------


def _make_execute(tool_name: str):
  """Create an async execute function for a given tool name."""

  async def execute(args: dict[str, Any]) -> SkillToolResult:
    result = await dispatch_tool(tool_name, args)
    return SkillToolResult(content=result.content, is_error=result.is_error)

  return execute


def _convert_tools() -> list[SkillTool]:
  """Convert MCP Tool definitions to SkillTool objects."""
  skill_tools: list[SkillTool] = []
  for mcp_tool in ALL_TOOLS:
    schema = mcp_tool.inputSchema if isinstance(mcp_tool.inputSchema, dict) else {}
    definition = ToolDefinition(
      name=mcp_tool.name,
      description=mcp_tool.description or "",
      parameters=schema,
    )
    skill_tools.append(
      SkillTool(
        definition=definition,
        execute=_make_execute(mcp_tool.name),
      )
    )
  return skill_tools


# ---------------------------------------------------------------------------
# Lifecycle hooks adapted for SkillContext
# ---------------------------------------------------------------------------


async def _on_load(ctx: Any) -> None:
  """Initialize PyGithub client using SkillContext."""
  from .server import on_skill_load

  # Read config from data dir if it exists
  config: dict[str, Any] = {}
  try:
    raw = await ctx.read_data("config.json")
    if raw:
      config = json.loads(raw)
  except Exception:
    pass

  # Build params dict that on_skill_load expects
  params: dict[str, Any] = {
    "dataDir": ctx.data_dir,
    "token": config.get("token", os.environ.get("GITHUB_TOKEN", "")),
  }

  # Pass set_state as a callback for host sync
  def set_state_fn(partial: dict[str, Any]) -> None:
    ctx.set_state(partial)

  await on_skill_load(params, set_state_fn=set_state_fn)


async def _on_unload(ctx: Any) -> None:
  from .server import on_skill_unload

  await on_skill_unload()


async def _on_tick(ctx: Any) -> None:
  from .server import on_skill_tick

  await on_skill_tick()


async def _on_status(ctx: Any) -> dict[str, Any]:
  """Return current skill status information."""
  from .client.gh_client import get_client

  try:
    client = get_client()
    return {
      "authenticated": client.is_authed if client else False,
      "username": client.username if client and client.is_authed else None,
    }
  except Exception:
    return {
      "authenticated": False,
      "username": None,
    }


# ---------------------------------------------------------------------------
# Disconnect handler
# ---------------------------------------------------------------------------


async def _on_disconnect(ctx: Any) -> None:
  """Clear PyGithub client and credentials."""
  from .server import on_skill_unload

  await on_skill_unload()

  try:
    await ctx.write_data("config.json", "{}")
  except Exception:
    log.warning("Failed to clear config.json on disconnect")


# ---------------------------------------------------------------------------
# Tool-category toggle options
# ---------------------------------------------------------------------------

TOOL_CATEGORY_OPTIONS = [
  SkillOptionDefinition(
    name="enable_repo_tools",
    type="boolean",
    label="Repository Management",
    description="12 tools — create, delete, fork, clone repos, manage collaborators and topics",
    default=True,
    group="tool_categories",
    tool_filter=[
      "add_collaborator",
      "clone_repo",
      "create_repo",
      "delete_repo",
      "fork_repo",
      "get_readme",
      "get_repo",
      "list_collaborators",
      "list_languages",
      "list_repos",
      "list_topics",
      "remove_collaborator",
    ],
  ),
  SkillOptionDefinition(
    name="enable_issue_tools",
    type="boolean",
    label="Issues",
    description="12 tools — create, edit, close, reopen issues, manage labels and assignees",
    default=True,
    group="tool_categories",
    tool_filter=[
      "add_issue_assignees",
      "add_issue_labels",
      "close_issue",
      "comment_on_issue",
      "create_issue",
      "edit_issue",
      "get_issue",
      "list_issue_comments",
      "list_issues",
      "remove_issue_assignees",
      "remove_issue_labels",
      "reopen_issue",
    ],
  ),
  SkillOptionDefinition(
    name="enable_pr_tools",
    type="boolean",
    label="Pull Requests",
    description="16 tools — create, edit, merge, review PRs, view diffs and checks",
    default=True,
    group="tool_categories",
    tool_filter=[
      "close_pr",
      "comment_on_pr",
      "create_pr",
      "create_pr_review",
      "edit_pr",
      "get_pr",
      "get_pr_checks",
      "get_pr_diff",
      "list_pr_comments",
      "list_pr_files",
      "list_pr_reviews",
      "list_prs",
      "mark_pr_ready",
      "merge_pr",
      "reopen_pr",
      "request_pr_reviewers",
    ],
  ),
  SkillOptionDefinition(
    name="enable_search_tools",
    type="boolean",
    label="Search",
    description="4 tools — search repos, issues, code, and commits",
    default=True,
    group="tool_categories",
    tool_filter=[
      "search_code",
      "search_commits",
      "search_issues",
      "search_repos",
    ],
  ),
  SkillOptionDefinition(
    name="enable_code_tools",
    type="boolean",
    label="Code & Files",
    description="3 tools — view files, list directories, set topics",
    default=True,
    group="tool_categories",
    tool_filter=[
      "list_directory",
      "set_topics",
      "view_file",
    ],
  ),
  SkillOptionDefinition(
    name="enable_release_tools",
    type="boolean",
    label="Releases",
    description="6 tools — create, delete, get, list releases and assets",
    default=False,
    group="tool_categories",
    tool_filter=[
      "create_release",
      "delete_release",
      "get_latest_release",
      "get_release",
      "list_release_assets",
      "list_releases",
    ],
  ),
  SkillOptionDefinition(
    name="enable_gist_tools",
    type="boolean",
    label="Gists",
    description="6 tools — create, edit, delete, clone, get, and list gists",
    default=True,
    group="tool_categories",
    tool_filter=[
      "clone_gist",
      "create_gist",
      "delete_gist",
      "edit_gist",
      "get_gist",
      "list_gists",
    ],
  ),
  SkillOptionDefinition(
    name="enable_workflow_tools",
    type="boolean",
    label="Actions & Workflows",
    description="9 tools — list, trigger, rerun, cancel workflows and view run logs",
    default=False,
    group="tool_categories",
    tool_filter=[
      "cancel_workflow_run",
      "get_run_logs",
      "get_workflow_run",
      "list_run_jobs",
      "list_workflow_runs",
      "list_workflows",
      "rerun_workflow",
      "trigger_workflow",
      "view_workflow_yaml",
    ],
  ),
  SkillOptionDefinition(
    name="enable_notification_tools",
    type="boolean",
    label="Notifications",
    description="4 tools — list notifications, mark read, and raw API access",
    default=False,
    group="tool_categories",
    tool_filter=[
      "gh_api",
      "list_notifications",
      "mark_all_notifications_read",
      "mark_notification_read",
    ],
  ),
]


# ---------------------------------------------------------------------------
# Skill definition
# ---------------------------------------------------------------------------

skill = SkillDefinition(
  name="github",
  description="GitHub integration for repos, issues, PRs, releases, gists, actions, search, notifications, and raw API access.",
  version="1.0.0",
  has_setup=True,
  has_disconnect=True,
  tick_interval=300_000,  # 5 minutes
  tools=_convert_tools(),
  options=TOOL_CATEGORY_OPTIONS,
  hooks=SkillHooks(
    on_load=_on_load,
    on_unload=_on_unload,
    on_tick=_on_tick,
    on_status=_on_status,
    on_setup_start=on_setup_start,
    on_setup_submit=on_setup_submit,
    on_setup_cancel=on_setup_cancel,
    on_disconnect=_on_disconnect,
  ),
)
