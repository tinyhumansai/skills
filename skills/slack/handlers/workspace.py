"""Workspace-related tool handlers."""

from __future__ import annotations

import json
import logging
from typing import Any

from ..client.slack_client import get_client
from ..helpers import ErrorCategory, ToolResult, log_and_format_error

log = logging.getLogger("skill.slack.handlers.workspace")


async def get_workspace_info(args: dict[str, Any]) -> ToolResult:
  """Get workspace information."""
  try:
    client = get_client()
    if not client:
      return ToolResult(content="Slack client not initialized", is_error=True)

    result = await client.auth_test()
    team = result.get("team", "")
    team_id = result.get("team_id", "")
    user = result.get("user", "")
    user_id = result.get("user_id", "")

    info = {
      "team": team,
      "team_id": team_id,
      "user": user,
      "user_id": user_id,
      "url": result.get("url", ""),
    }

    return ToolResult(content=json.dumps(info, indent=2))

  except Exception as e:
    return log_and_format_error("get_workspace_info", e, ErrorCategory.API)
