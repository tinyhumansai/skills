"""Raw GitHub API fallback handler."""

from __future__ import annotations

import json
from typing import Any

from ..client.gh_client import get_client, run_sync
from ..helpers import ErrorCategory, ToolResult, log_and_format_error, truncate
from ..validation import opt_string, req_string


async def gh_api(args: dict[str, Any]) -> ToolResult:
  """Raw GitHub API call — fallback for anything not covered by other tools."""
  try:
    endpoint = req_string(args, "endpoint")
    method = (opt_string(args, "method") or "GET").upper()
    body = args.get("body")

    # Ensure endpoint starts with /
    if not endpoint.startswith("/"):
      endpoint = "/" + endpoint

    gh = get_client().gh
    requester = gh._Github__requester

    headers = {"Accept": "application/vnd.github.v3+json"}
    input_data = None

    if body and method in ("POST", "PUT", "PATCH"):
      input_data = body if isinstance(body, str) else json.dumps(body)
      headers["Content-Type"] = "application/json"

    if method == "GET":
      _response_headers, data = await run_sync(
        requester.requestJsonAndCheck, "GET", endpoint, headers=headers
      )
    elif method == "POST":
      _response_headers, data = await run_sync(
        requester.requestJsonAndCheck, "POST", endpoint, headers=headers, input=input_data
      )
    elif method == "PUT":
      _response_headers, data = await run_sync(
        requester.requestJsonAndCheck, "PUT", endpoint, headers=headers, input=input_data
      )
    elif method == "PATCH":
      _response_headers, data = await run_sync(
        requester.requestJsonAndCheck, "PATCH", endpoint, headers=headers, input=input_data
      )
    elif method == "DELETE":
      _response_headers, data = await run_sync(
        requester.requestJsonAndCheck, "DELETE", endpoint, headers=headers
      )
    else:
      return ToolResult(content=f"Unsupported HTTP method: {method}", is_error=True)

    if data is None:
      return ToolResult(content="(no content)")
    return ToolResult(content=truncate(json.dumps(data, indent=2)))
  except Exception as e:
    return log_and_format_error("gh_api", e, ErrorCategory.API)
