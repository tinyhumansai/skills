"""Actions/workflow domain tool handlers."""

from __future__ import annotations

from typing import Any

from ..client.gh_client import get_client, run_sync
from ..helpers import ErrorCategory, ToolResult, log_and_format_error, truncate
from ..validation import (
  opt_number,
  opt_string,
  req_string,
  validate_positive_int,
  validate_repo_spec,
)


async def list_workflows(args: dict[str, Any]) -> ToolResult:
  try:
    spec = validate_repo_spec(args)
    gh = get_client().gh
    repo = await run_sync(gh.get_repo, spec)
    workflows = await run_sync(repo.get_workflows)
    items = await run_sync(lambda: list(workflows[:30]))

    if not items:
      return ToolResult(content=f"No workflows in {spec}.")
    lines = []
    for w in items:
      state = w.state or ""
      lines.append(f"{w.name} (id: {w.id}) [{state}] - {w.path}")
    return ToolResult(content="\n".join(lines))
  except Exception as e:
    return log_and_format_error("list_workflows", e, ErrorCategory.ACTIONS)


async def list_workflow_runs(args: dict[str, Any]) -> ToolResult:
  try:
    spec = validate_repo_spec(args)
    limit = opt_number(args, "limit", 20)
    workflow_id = opt_string(args, "workflow_id")
    branch = opt_string(args, "branch")
    status = opt_string(args, "status")

    gh = get_client().gh
    repo = await run_sync(gh.get_repo, spec)

    if workflow_id:
      try:
        wf_id = int(workflow_id)
      except ValueError:
        wf_id = workflow_id
      workflow = await run_sync(repo.get_workflow, wf_id)
      kwargs: dict[str, Any] = {}
      if branch:
        kwargs["branch"] = branch
      if status:
        kwargs["status"] = status
      runs = await run_sync(workflow.get_runs, **kwargs)
    else:
      kwargs = {}
      if branch:
        kwargs["branch"] = branch
      if status:
        kwargs["status"] = status
      runs = await run_sync(repo.get_workflow_runs, **kwargs)

    items = await run_sync(lambda: list(runs[:limit]))
    if not items:
      return ToolResult(content="No workflow runs found.")
    lines = []
    for r in items:
      conclusion = r.conclusion or r.status or "in_progress"
      branch_name = r.head_branch or ""
      lines.append(f"#{r.run_number} {r.name} [{conclusion}] on {branch_name} ({r.created_at})")
    return ToolResult(content="\n".join(lines))
  except Exception as e:
    return log_and_format_error("list_workflow_runs", e, ErrorCategory.ACTIONS)


async def get_workflow_run(args: dict[str, Any]) -> ToolResult:
  try:
    spec = validate_repo_spec(args)
    run_id = validate_positive_int(args.get("run_id"), "run_id")

    gh = get_client().gh
    repo = await run_sync(gh.get_repo, spec)
    run = await run_sync(repo.get_workflow_run, run_id)

    lines = [
      f"Run #{run.run_number}: {run.name}",
      f"Status: {run.status}",
      f"Conclusion: {run.conclusion or 'N/A'}",
      f"Branch: {run.head_branch}",
      f"Event: {run.event}",
      f"SHA: {run.head_sha[:7]}",
      f"URL: {run.html_url}",
      f"Created: {run.created_at}",
      f"Updated: {run.updated_at}",
    ]
    if run.run_started_at:
      lines.append(f"Started: {run.run_started_at}")
    return ToolResult(content="\n".join(lines))
  except Exception as e:
    return log_and_format_error("get_workflow_run", e, ErrorCategory.ACTIONS)


async def list_run_jobs(args: dict[str, Any]) -> ToolResult:
  try:
    spec = validate_repo_spec(args)
    run_id = validate_positive_int(args.get("run_id"), "run_id")

    gh = get_client().gh
    repo = await run_sync(gh.get_repo, spec)
    run = await run_sync(repo.get_workflow_run, run_id)
    jobs = await run_sync(run.jobs)
    items = await run_sync(lambda: list(jobs[:30]))

    if not items:
      return ToolResult(content=f"No jobs in run #{run_id}.")
    lines = []
    for j in items:
      conclusion = j.conclusion or j.status or "in_progress"
      lines.append(f"{j.name} [{conclusion}]")
      if hasattr(j, "steps") and j.steps:
        for s in j.steps:
          step_status = s.conclusion or s.status or "?"
          lines.append(f"  - {s.name} [{step_status}]")
    return ToolResult(content="\n".join(lines))
  except Exception as e:
    return log_and_format_error("list_run_jobs", e, ErrorCategory.ACTIONS)


async def get_run_logs(args: dict[str, Any]) -> ToolResult:
  try:
    spec = validate_repo_spec(args)
    run_id = validate_positive_int(args.get("run_id"), "run_id")

    gh = get_client().gh
    repo = await run_sync(gh.get_repo, spec)
    run = await run_sync(repo.get_workflow_run, run_id)

    # PyGithub doesn't support downloading logs directly
    # Return the URL instead
    logs_url = f"https://github.com/{spec}/actions/runs/{run_id}"
    return ToolResult(
      content=f"Run #{run.run_number} ({run.conclusion or run.status})\nView logs at: {logs_url}"
    )
  except Exception as e:
    return log_and_format_error("get_run_logs", e, ErrorCategory.ACTIONS)


async def rerun_workflow(args: dict[str, Any]) -> ToolResult:
  try:
    spec = validate_repo_spec(args)
    run_id = validate_positive_int(args.get("run_id"), "run_id")

    gh = get_client().gh
    repo = await run_sync(gh.get_repo, spec)
    run = await run_sync(repo.get_workflow_run, run_id)
    await run_sync(run.rerun)
    return ToolResult(content=f"Workflow run #{run.run_number} rerun initiated.")
  except Exception as e:
    return log_and_format_error("rerun_workflow", e, ErrorCategory.ACTIONS)


async def cancel_workflow_run(args: dict[str, Any]) -> ToolResult:
  try:
    spec = validate_repo_spec(args)
    run_id = validate_positive_int(args.get("run_id"), "run_id")

    gh = get_client().gh
    repo = await run_sync(gh.get_repo, spec)
    run = await run_sync(repo.get_workflow_run, run_id)
    await run_sync(run.cancel)
    return ToolResult(content=f"Workflow run #{run.run_number} cancelled.")
  except Exception as e:
    return log_and_format_error("cancel_workflow_run", e, ErrorCategory.ACTIONS)


async def trigger_workflow(args: dict[str, Any]) -> ToolResult:
  try:
    spec = validate_repo_spec(args)
    workflow_id = req_string(args, "workflow_id")
    ref = opt_string(args, "ref") or "main"
    inputs = args.get("inputs", {})
    if not isinstance(inputs, dict):
      inputs = {}

    gh = get_client().gh
    repo = await run_sync(gh.get_repo, spec)

    try:
      wf_id = int(workflow_id)
    except ValueError:
      wf_id = workflow_id
    workflow = await run_sync(repo.get_workflow, wf_id)
    await run_sync(workflow.create_dispatch, ref, inputs)
    return ToolResult(content=f"Workflow '{workflow.name}' triggered on {ref}.")
  except Exception as e:
    return log_and_format_error("trigger_workflow", e, ErrorCategory.ACTIONS)


async def view_workflow_yaml(args: dict[str, Any]) -> ToolResult:
  try:
    spec = validate_repo_spec(args)
    workflow_id = req_string(args, "workflow_id")

    gh = get_client().gh
    repo = await run_sync(gh.get_repo, spec)

    try:
      wf_id = int(workflow_id)
    except ValueError:
      wf_id = workflow_id
    workflow = await run_sync(repo.get_workflow, wf_id)

    # Get the workflow file content
    path = workflow.path
    content_file = await run_sync(repo.get_contents, path)
    if isinstance(content_file, list):
      return ToolResult(content="Workflow file is a directory (unexpected).", is_error=True)

    if content_file.decoded_content:
      content = content_file.decoded_content.decode("utf-8", errors="replace")
      return ToolResult(content=f"--- {path} ---\n{truncate(content)}")
    return ToolResult(content="(empty workflow file)")
  except Exception as e:
    return log_and_format_error("view_workflow_yaml", e, ErrorCategory.ACTIONS)
