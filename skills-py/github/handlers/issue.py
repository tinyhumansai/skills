"""Issue domain tool handlers."""

from __future__ import annotations

from typing import Any

from ..client.gh_client import get_client, run_sync
from ..helpers import ErrorCategory, ToolResult, log_and_format_error, truncate
from ..validation import (
  opt_number,
  opt_string,
  opt_string_list,
  req_string,
  validate_positive_int,
  validate_repo_spec,
)


async def list_issues(args: dict[str, Any]) -> ToolResult:
  try:
    spec = validate_repo_spec(args)
    limit = opt_number(args, "limit", 30)
    state = opt_string(args, "state") or "open"
    label_filter = opt_string(args, "label")
    assignee = opt_string(args, "assignee")

    gh = get_client().gh
    repo = await run_sync(gh.get_repo, spec)

    kwargs: dict[str, Any] = {"state": state}
    if assignee:
      kwargs["assignee"] = assignee
    if label_filter:
      labels = [await run_sync(repo.get_label, label_filter)]
      kwargs["labels"] = labels

    issues = await run_sync(repo.get_issues, **kwargs)
    # Filter out PRs (GitHub API returns PRs as issues too)
    items = []
    for issue in await run_sync(lambda: list(issues[: limit * 2])):
      if issue.pull_request is None:
        items.append(issue)
      if len(items) >= limit:
        break

    if not items:
      return ToolResult(content=f"No {state} issues in {spec}.")

    lines = []
    for i in items:
      labels = ", ".join(l.name for l in i.labels) if i.labels else ""
      author = i.user.login if i.user else ""
      state_str = i.state.upper()
      line = f"#{i.number} [{state_str}] {i.title[:80]}"
      if author:
        line += f" (by @{author})"
      if labels:
        line += f" [{labels}]"
      lines.append(line)
    return ToolResult(content="\n".join(lines))
  except Exception as e:
    return log_and_format_error("list_issues", e, ErrorCategory.ISSUE)


async def get_issue(args: dict[str, Any]) -> ToolResult:
  try:
    spec = validate_repo_spec(args)
    number = validate_positive_int(args.get("number"), "number")

    gh = get_client().gh
    repo = await run_sync(gh.get_repo, spec)
    issue = await run_sync(repo.get_issue, number)

    author = issue.user.login if issue.user else ""
    labels = [l.name for l in issue.labels] if issue.labels else []
    assignees = [a.login for a in issue.assignees] if issue.assignees else []
    milestone = issue.milestone.title if issue.milestone else ""

    lines = [
      f"Issue #{issue.number}: {issue.title}",
      f"State: {issue.state}",
      f"Author: @{author}" if author else "",
      f"Labels: {', '.join(labels)}" if labels else "",
      f"Assignees: {', '.join('@' + a for a in assignees)}" if assignees else "",
      f"Milestone: {milestone}" if milestone else "",
      f"Comments: {issue.comments}",
      f"Created: {issue.created_at}",
      f"Updated: {issue.updated_at}",
      "",
      truncate(issue.body or "(no description)", 3000),
    ]
    return ToolResult(content="\n".join(l for l in lines if l or l == ""))
  except Exception as e:
    return log_and_format_error("get_issue", e, ErrorCategory.ISSUE)


async def create_issue(args: dict[str, Any]) -> ToolResult:
  try:
    spec = validate_repo_spec(args)
    title = req_string(args, "title")
    body = opt_string(args, "body")
    label_names = opt_string_list(args, "labels")
    assignee_names = opt_string_list(args, "assignees")

    gh = get_client().gh
    repo = await run_sync(gh.get_repo, spec)

    kwargs: dict[str, Any] = {"title": title}
    if body:
      kwargs["body"] = body
    if label_names:
      kwargs["labels"] = label_names
    if assignee_names:
      kwargs["assignees"] = assignee_names

    issue = await run_sync(repo.create_issue, **kwargs)
    return ToolResult(content=f"Issue created: {issue.html_url}")
  except Exception as e:
    return log_and_format_error("create_issue", e, ErrorCategory.ISSUE)


async def close_issue(args: dict[str, Any]) -> ToolResult:
  try:
    spec = validate_repo_spec(args)
    number = validate_positive_int(args.get("number"), "number")
    reason = opt_string(args, "reason")

    gh = get_client().gh
    repo = await run_sync(gh.get_repo, spec)
    issue = await run_sync(repo.get_issue, number)

    kwargs: dict[str, Any] = {"state": "closed"}
    if reason:
      kwargs["state_reason"] = reason
    await run_sync(issue.edit, **kwargs)
    return ToolResult(content=f"Issue #{number} closed.")
  except Exception as e:
    return log_and_format_error("close_issue", e, ErrorCategory.ISSUE)


async def reopen_issue(args: dict[str, Any]) -> ToolResult:
  try:
    spec = validate_repo_spec(args)
    number = validate_positive_int(args.get("number"), "number")

    gh = get_client().gh
    repo = await run_sync(gh.get_repo, spec)
    issue = await run_sync(repo.get_issue, number)
    await run_sync(issue.edit, state="open")
    return ToolResult(content=f"Issue #{number} reopened.")
  except Exception as e:
    return log_and_format_error("reopen_issue", e, ErrorCategory.ISSUE)


async def edit_issue(args: dict[str, Any]) -> ToolResult:
  try:
    spec = validate_repo_spec(args)
    number = validate_positive_int(args.get("number"), "number")
    title = opt_string(args, "title")
    body = opt_string(args, "body")

    if not title and not body:
      return ToolResult(
        content="Provide at least one field to edit (title or body).", is_error=True
      )

    gh = get_client().gh
    repo = await run_sync(gh.get_repo, spec)
    issue = await run_sync(repo.get_issue, number)

    kwargs: dict[str, Any] = {}
    if title:
      kwargs["title"] = title
    if body:
      kwargs["body"] = body
    await run_sync(issue.edit, **kwargs)
    return ToolResult(content=f"Issue #{number} updated.")
  except Exception as e:
    return log_and_format_error("edit_issue", e, ErrorCategory.ISSUE)


async def comment_on_issue(args: dict[str, Any]) -> ToolResult:
  try:
    spec = validate_repo_spec(args)
    number = validate_positive_int(args.get("number"), "number")
    body = req_string(args, "body")

    gh = get_client().gh
    repo = await run_sync(gh.get_repo, spec)
    issue = await run_sync(repo.get_issue, number)
    comment = await run_sync(issue.create_comment, body)
    return ToolResult(content=f"Comment added to issue #{number}: {comment.html_url}")
  except Exception as e:
    return log_and_format_error("comment_on_issue", e, ErrorCategory.ISSUE)


async def list_issue_comments(args: dict[str, Any]) -> ToolResult:
  try:
    spec = validate_repo_spec(args)
    number = validate_positive_int(args.get("number"), "number")
    limit = opt_number(args, "limit", 30)

    gh = get_client().gh
    repo = await run_sync(gh.get_repo, spec)
    issue = await run_sync(repo.get_issue, number)
    comments = await run_sync(issue.get_comments)
    items = await run_sync(lambda: list(comments[:limit]))

    if not items:
      return ToolResult(content=f"No comments on issue #{number}.")
    lines = []
    for c in items:
      author = c.user.login if c.user else "unknown"
      body = (c.body or "")[:200]
      created = str(c.created_at)
      lines.append(f"@{author} ({created}):\n{body}\n")
    return ToolResult(content=truncate("\n".join(lines)))
  except Exception as e:
    return log_and_format_error("list_issue_comments", e, ErrorCategory.ISSUE)


async def add_issue_labels(args: dict[str, Any]) -> ToolResult:
  try:
    spec = validate_repo_spec(args)
    number = validate_positive_int(args.get("number"), "number")
    labels = opt_string_list(args, "labels")
    if not labels:
      return ToolResult(content="At least one label is required.", is_error=True)

    gh = get_client().gh
    repo = await run_sync(gh.get_repo, spec)
    issue = await run_sync(repo.get_issue, number)
    for label in labels:
      await run_sync(issue.add_to_labels, label)
    return ToolResult(content=f"Labels added to issue #{number}: {', '.join(labels)}")
  except Exception as e:
    return log_and_format_error("add_issue_labels", e, ErrorCategory.ISSUE)


async def remove_issue_labels(args: dict[str, Any]) -> ToolResult:
  try:
    spec = validate_repo_spec(args)
    number = validate_positive_int(args.get("number"), "number")
    labels = opt_string_list(args, "labels")
    if not labels:
      return ToolResult(content="At least one label is required.", is_error=True)

    gh = get_client().gh
    repo = await run_sync(gh.get_repo, spec)
    issue = await run_sync(repo.get_issue, number)
    for label in labels:
      await run_sync(issue.remove_from_labels, label)
    return ToolResult(content=f"Labels removed from issue #{number}: {', '.join(labels)}")
  except Exception as e:
    return log_and_format_error("remove_issue_labels", e, ErrorCategory.ISSUE)


async def add_issue_assignees(args: dict[str, Any]) -> ToolResult:
  try:
    spec = validate_repo_spec(args)
    number = validate_positive_int(args.get("number"), "number")
    assignees = opt_string_list(args, "assignees")
    if not assignees:
      return ToolResult(content="At least one assignee is required.", is_error=True)

    gh = get_client().gh
    repo = await run_sync(gh.get_repo, spec)
    issue = await run_sync(repo.get_issue, number)
    for assignee in assignees:
      user = await run_sync(gh.get_user, assignee)
      await run_sync(issue.add_to_assignees, user)
    return ToolResult(content=f"Assignees added to issue #{number}: {', '.join(assignees)}")
  except Exception as e:
    return log_and_format_error("add_issue_assignees", e, ErrorCategory.ISSUE)


async def remove_issue_assignees(args: dict[str, Any]) -> ToolResult:
  try:
    spec = validate_repo_spec(args)
    number = validate_positive_int(args.get("number"), "number")
    assignees = opt_string_list(args, "assignees")
    if not assignees:
      return ToolResult(content="At least one assignee is required.", is_error=True)

    gh = get_client().gh
    repo = await run_sync(gh.get_repo, spec)
    issue = await run_sync(repo.get_issue, number)
    for assignee in assignees:
      user = await run_sync(gh.get_user, assignee)
      await run_sync(issue.remove_from_assignees, user)
    return ToolResult(content=f"Assignees removed from issue #{number}: {', '.join(assignees)}")
  except Exception as e:
    return log_and_format_error("remove_issue_assignees", e, ErrorCategory.ISSUE)
