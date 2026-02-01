"""
Actions / Workflow tools (9 tools).
"""

from __future__ import annotations

from mcp.types import Tool

actions_tools: list[Tool] = [
  Tool(
    name="list_workflows",
    description="List GitHub Actions workflows defined in a repository",
    inputSchema={
      "type": "object",
      "properties": {
        "owner": {"type": "string", "description": "Repository owner"},
        "repo": {"type": "string", "description": "Repository name"},
      },
      "required": ["owner", "repo"],
    },
  ),
  Tool(
    name="list_workflow_runs",
    description="List recent workflow runs for a repository",
    inputSchema={
      "type": "object",
      "properties": {
        "owner": {"type": "string", "description": "Repository owner"},
        "repo": {"type": "string", "description": "Repository name"},
        "limit": {
          "type": "number",
          "description": "Maximum number of runs to return",
          "default": 20,
        },
        "workflow_id": {
          "type": "string",
          "description": "Filter by workflow ID or filename (e.g. 'ci.yml')",
        },
        "branch": {"type": "string", "description": "Filter by branch name"},
        "status": {
          "type": "string",
          "description": "Filter by status",
          "enum": ["queued", "in_progress", "completed", "waiting", "requested"],
        },
      },
      "required": ["owner", "repo"],
    },
  ),
  Tool(
    name="get_workflow_run",
    description="Get detailed information about a specific workflow run",
    inputSchema={
      "type": "object",
      "properties": {
        "owner": {"type": "string", "description": "Repository owner"},
        "repo": {"type": "string", "description": "Repository name"},
        "run_id": {"type": "number", "description": "Workflow run ID"},
      },
      "required": ["owner", "repo", "run_id"],
    },
  ),
  Tool(
    name="list_run_jobs",
    description="List jobs for a specific workflow run",
    inputSchema={
      "type": "object",
      "properties": {
        "owner": {"type": "string", "description": "Repository owner"},
        "repo": {"type": "string", "description": "Repository name"},
        "run_id": {"type": "number", "description": "Workflow run ID"},
      },
      "required": ["owner", "repo", "run_id"],
    },
  ),
  Tool(
    name="get_run_logs",
    description="Download logs for a specific workflow run",
    inputSchema={
      "type": "object",
      "properties": {
        "owner": {"type": "string", "description": "Repository owner"},
        "repo": {"type": "string", "description": "Repository name"},
        "run_id": {"type": "number", "description": "Workflow run ID"},
      },
      "required": ["owner", "repo", "run_id"],
    },
  ),
  Tool(
    name="rerun_workflow",
    description="Re-run an entire workflow run",
    inputSchema={
      "type": "object",
      "properties": {
        "owner": {"type": "string", "description": "Repository owner"},
        "repo": {"type": "string", "description": "Repository name"},
        "run_id": {"type": "number", "description": "Workflow run ID to re-run"},
      },
      "required": ["owner", "repo", "run_id"],
    },
  ),
  Tool(
    name="cancel_workflow_run",
    description="Cancel a workflow run that is in progress",
    inputSchema={
      "type": "object",
      "properties": {
        "owner": {"type": "string", "description": "Repository owner"},
        "repo": {"type": "string", "description": "Repository name"},
        "run_id": {"type": "number", "description": "Workflow run ID to cancel"},
      },
      "required": ["owner", "repo", "run_id"],
    },
  ),
  Tool(
    name="trigger_workflow",
    description="Manually trigger a workflow dispatch event",
    inputSchema={
      "type": "object",
      "properties": {
        "owner": {"type": "string", "description": "Repository owner"},
        "repo": {"type": "string", "description": "Repository name"},
        "workflow_id": {
          "type": "string",
          "description": "Workflow ID or filename (e.g. 'deploy.yml')",
        },
        "ref": {
          "type": "string",
          "description": "Git ref (branch or tag) to run the workflow on",
          "default": "main",
        },
        "inputs": {
          "type": "object",
          "description": "Input key-value pairs for the workflow_dispatch event",
          "additionalProperties": {"type": "string"},
        },
      },
      "required": ["owner", "repo", "workflow_id"],
    },
  ),
  Tool(
    name="view_workflow_yaml",
    description="View the YAML source of a workflow definition",
    inputSchema={
      "type": "object",
      "properties": {
        "owner": {"type": "string", "description": "Repository owner"},
        "repo": {"type": "string", "description": "Repository name"},
        "workflow_id": {
          "type": "string",
          "description": "Workflow ID or filename (e.g. 'ci.yml')",
        },
      },
      "required": ["owner", "repo", "workflow_id"],
    },
  ),
]
