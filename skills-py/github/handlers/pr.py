"""Pull request domain tool handlers."""

from __future__ import annotations

from typing import Any

from ..client.gh_client import get_client, run_sync
from ..helpers import ErrorCategory, ToolResult, log_and_format_error, truncate
from ..validation import (
  opt_boolean,
  opt_number,
  opt_string,
  opt_string_list,
  req_string,
  validate_positive_int,
  validate_repo_spec,
)


async def list_prs(args: dict[str, Any]) -> ToolResult:
  try:
    spec = validate_repo_spec(args)
    limit = opt_number(args, "limit", 30)
    state = opt_string(args, "state") or "open"
    base = opt_string(args, "base")

    gh = get_client().gh
    repo = await run_sync(gh.get_repo, spec)

    kwargs: dict[str, Any] = {"state": state}
    if base:
      kwargs["base"] = base
    pulls = await run_sync(repo.get_pulls, **kwargs)
    items = await run_sync(lambda: list(pulls[:limit]))

    if not items:
      return ToolResult(content=f"No {state} pull requests in {spec}.")

    lines = []
    for p in items:
      author = p.user.login if p.user else ""
      draft = " [draft]" if p.draft else ""
      labels = ", ".join(l.name for l in p.labels) if p.labels else ""
      line = f"#{p.number} [{p.state.upper()}] {p.title[:80]}"
      if author:
        line += f" (by @{author})"
      line += f" ({p.head.ref} -> {p.base.ref})"
      line += draft
      if labels:
        line += f" [{labels}]"
      lines.append(line)
    return ToolResult(content="\n".join(lines))
  except Exception as e:
    return log_and_format_error("list_prs", e, ErrorCategory.PR)


async def get_pr(args: dict[str, Any]) -> ToolResult:
  try:
    spec = validate_repo_spec(args)
    number = validate_positive_int(args.get("number"), "number")

    gh = get_client().gh
    repo = await run_sync(gh.get_repo, spec)
    pr = await run_sync(repo.get_pull, number)

    author = pr.user.login if pr.user else ""
    labels = [l.name for l in pr.labels] if pr.labels else []
    assignees = [a.login for a in pr.assignees] if pr.assignees else []

    lines = [
      f"PR #{pr.number}: {pr.title}",
      f"State: {pr.state}" + (" [draft]" if pr.draft else ""),
      f"Author: @{author}" if author else "",
      f"Branch: {pr.head.ref} -> {pr.base.ref}",
      f"Changes: +{pr.additions} -{pr.deletions} ({pr.changed_files} files)",
      f"Mergeable: {pr.mergeable}",
      f"Labels: {', '.join(labels)}" if labels else "",
      f"Assignees: {', '.join('@' + a for a in assignees)}" if assignees else "",
      f"Comments: {pr.comments}",
      f"Review Comments: {pr.review_comments}",
      f"Created: {pr.created_at}",
      f"Updated: {pr.updated_at}",
      f"Merged: {pr.merged_at}" if pr.merged_at else "",
      "",
      truncate(pr.body or "(no description)", 3000),
    ]
    return ToolResult(content="\n".join(l for l in lines if l or l == ""))
  except Exception as e:
    return log_and_format_error("get_pr", e, ErrorCategory.PR)


async def create_pr(args: dict[str, Any]) -> ToolResult:
  try:
    spec = validate_repo_spec(args)
    title = req_string(args, "title")
    head = req_string(args, "head")
    base = opt_string(args, "base") or "main"
    body = opt_string(args, "body")
    draft = opt_boolean(args, "draft", False)

    gh = get_client().gh
    repo = await run_sync(gh.get_repo, spec)

    kwargs: dict[str, Any] = {"title": title, "head": head, "base": base, "draft": draft}
    if body:
      kwargs["body"] = body

    pr = await run_sync(repo.create_pull, **kwargs)
    return ToolResult(content=f"PR created: {pr.html_url}")
  except Exception as e:
    return log_and_format_error("create_pr", e, ErrorCategory.PR)


async def close_pr(args: dict[str, Any]) -> ToolResult:
  try:
    spec = validate_repo_spec(args)
    number = validate_positive_int(args.get("number"), "number")

    gh = get_client().gh
    repo = await run_sync(gh.get_repo, spec)
    pr = await run_sync(repo.get_pull, number)
    await run_sync(pr.edit, state="closed")
    return ToolResult(content=f"PR #{number} closed.")
  except Exception as e:
    return log_and_format_error("close_pr", e, ErrorCategory.PR)


async def reopen_pr(args: dict[str, Any]) -> ToolResult:
  try:
    spec = validate_repo_spec(args)
    number = validate_positive_int(args.get("number"), "number")

    gh = get_client().gh
    repo = await run_sync(gh.get_repo, spec)
    pr = await run_sync(repo.get_pull, number)
    await run_sync(pr.edit, state="open")
    return ToolResult(content=f"PR #{number} reopened.")
  except Exception as e:
    return log_and_format_error("reopen_pr", e, ErrorCategory.PR)


async def merge_pr(args: dict[str, Any]) -> ToolResult:
  try:
    spec = validate_repo_spec(args)
    number = validate_positive_int(args.get("number"), "number")
    method = opt_string(args, "method") or "merge"
    delete_branch = opt_boolean(args, "delete_branch", False)
    commit_message = opt_string(args, "commit_message")

    gh = get_client().gh
    repo = await run_sync(gh.get_repo, spec)
    pr = await run_sync(repo.get_pull, number)

    kwargs: dict[str, Any] = {"merge_method": method}
    if commit_message:
      kwargs["commit_message"] = commit_message
    await run_sync(pr.merge, **kwargs)

    msg = f"PR #{number} merged via {method}."
    if delete_branch:
      try:
        ref = await run_sync(repo.get_git_ref, f"heads/{pr.head.ref}")
        await run_sync(ref.delete)
        msg += f" Branch '{pr.head.ref}' deleted."
      except Exception:
        msg += f" (could not delete branch '{pr.head.ref}')"
    return ToolResult(content=msg)
  except Exception as e:
    return log_and_format_error("merge_pr", e, ErrorCategory.PR)


async def edit_pr(args: dict[str, Any]) -> ToolResult:
  try:
    spec = validate_repo_spec(args)
    number = validate_positive_int(args.get("number"), "number")
    title = opt_string(args, "title")
    body = opt_string(args, "body")
    base = opt_string(args, "base")

    if not title and not body and not base:
      return ToolResult(content="Provide at least one field to edit.", is_error=True)

    gh = get_client().gh
    repo = await run_sync(gh.get_repo, spec)
    pr = await run_sync(repo.get_pull, number)

    kwargs: dict[str, Any] = {}
    if title:
      kwargs["title"] = title
    if body:
      kwargs["body"] = body
    if base:
      kwargs["base"] = base
    await run_sync(pr.edit, **kwargs)
    return ToolResult(content=f"PR #{number} updated.")
  except Exception as e:
    return log_and_format_error("edit_pr", e, ErrorCategory.PR)


async def comment_on_pr(args: dict[str, Any]) -> ToolResult:
  try:
    spec = validate_repo_spec(args)
    number = validate_positive_int(args.get("number"), "number")
    body = req_string(args, "body")

    gh = get_client().gh
    repo = await run_sync(gh.get_repo, spec)
    # PR comments go through the issue API
    issue = await run_sync(repo.get_issue, number)
    comment = await run_sync(issue.create_comment, body)
    return ToolResult(content=f"Comment added to PR #{number}: {comment.html_url}")
  except Exception as e:
    return log_and_format_error("comment_on_pr", e, ErrorCategory.PR)


async def list_pr_comments(args: dict[str, Any]) -> ToolResult:
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
      return ToolResult(content=f"No comments on PR #{number}.")
    lines = []
    for c in items:
      author = c.user.login if c.user else "unknown"
      body = (c.body or "")[:200]
      created = str(c.created_at)
      lines.append(f"@{author} ({created}):\n{body}\n")
    return ToolResult(content=truncate("\n".join(lines)))
  except Exception as e:
    return log_and_format_error("list_pr_comments", e, ErrorCategory.PR)


async def list_pr_reviews(args: dict[str, Any]) -> ToolResult:
  try:
    spec = validate_repo_spec(args)
    number = validate_positive_int(args.get("number"), "number")

    gh = get_client().gh
    repo = await run_sync(gh.get_repo, spec)
    pr = await run_sync(repo.get_pull, number)
    reviews = await run_sync(pr.get_reviews)
    items = await run_sync(lambda: list(reviews[:30]))

    if not items:
      return ToolResult(content=f"No reviews on PR #{number}.")
    lines = []
    for r in items:
      user = r.user.login if r.user else "unknown"
      state = r.state or ""
      body = (r.body or "")[:150]
      lines.append(f"@{user}: {state}" + (f" - {body}" if body else ""))
    return ToolResult(content="\n".join(lines))
  except Exception as e:
    return log_and_format_error("list_pr_reviews", e, ErrorCategory.PR)


async def create_pr_review(args: dict[str, Any]) -> ToolResult:
  try:
    spec = validate_repo_spec(args)
    number = validate_positive_int(args.get("number"), "number")
    event = req_string(args, "event").upper()  # APPROVE, REQUEST_CHANGES, COMMENT
    body = opt_string(args, "body") or ""

    gh = get_client().gh
    repo = await run_sync(gh.get_repo, spec)
    pr = await run_sync(repo.get_pull, number)
    await run_sync(pr.create_review, body=body, event=event)
    return ToolResult(content=f"Review ({event}) submitted on PR #{number}.")
  except Exception as e:
    return log_and_format_error("create_pr_review", e, ErrorCategory.PR)


async def list_pr_files(args: dict[str, Any]) -> ToolResult:
  try:
    spec = validate_repo_spec(args)
    number = validate_positive_int(args.get("number"), "number")

    gh = get_client().gh
    repo = await run_sync(gh.get_repo, spec)
    pr = await run_sync(repo.get_pull, number)
    files = await run_sync(pr.get_files)
    items = await run_sync(lambda: list(files[:100]))

    if not items:
      return ToolResult(content=f"No files changed in PR #{number}.")
    lines = []
    for f in items:
      status = f.status or ""
      lines.append(f"{status:12s} +{f.additions} -{f.deletions}  {f.filename}")
    return ToolResult(content="\n".join(lines))
  except Exception as e:
    return log_and_format_error("list_pr_files", e, ErrorCategory.PR)


async def get_pr_diff(args: dict[str, Any]) -> ToolResult:
  try:
    spec = validate_repo_spec(args)
    number = validate_positive_int(args.get("number"), "number")

    gh = get_client().gh
    repo = await run_sync(gh.get_repo, spec)
    pr = await run_sync(repo.get_pull, number)
    # PyGithub doesn't have a direct diff method; use the files list
    files = await run_sync(pr.get_files)
    items = await run_sync(lambda: list(files[:50]))

    if not items:
      return ToolResult(content="(empty diff)")
    lines = []
    for f in items:
      lines.append(f"--- {f.filename} ({f.status})")
      if f.patch:
        lines.append(f.patch[:2000])
      lines.append("")
    return ToolResult(content=truncate("\n".join(lines)))
  except Exception as e:
    return log_and_format_error("get_pr_diff", e, ErrorCategory.PR)


async def get_pr_checks(args: dict[str, Any]) -> ToolResult:
  try:
    spec = validate_repo_spec(args)
    number = validate_positive_int(args.get("number"), "number")

    gh = get_client().gh
    repo = await run_sync(gh.get_repo, spec)
    pr = await run_sync(repo.get_pull, number)
    commits = await run_sync(pr.get_commits)
    last_commit = await run_sync(lambda: list(commits)[-1] if commits.totalCount > 0 else None)

    if not last_commit:
      return ToolResult(content="No commits found on this PR.")

    check_runs = await run_sync(last_commit.get_check_runs)
    items = await run_sync(lambda: list(check_runs[:30]))

    if not items:
      return ToolResult(content=f"No checks on PR #{number}.")
    lines = []
    for c in items:
      conclusion = c.conclusion or c.status or "pending"
      lines.append(f"{conclusion:12s} {c.name}")
    return ToolResult(content="\n".join(lines))
  except Exception as e:
    return log_and_format_error("get_pr_checks", e, ErrorCategory.PR)


async def request_pr_reviewers(args: dict[str, Any]) -> ToolResult:
  try:
    spec = validate_repo_spec(args)
    number = validate_positive_int(args.get("number"), "number")
    reviewers = opt_string_list(args, "reviewers")
    if not reviewers:
      return ToolResult(content="At least one reviewer is required.", is_error=True)

    gh = get_client().gh
    repo = await run_sync(gh.get_repo, spec)
    pr = await run_sync(repo.get_pull, number)
    await run_sync(pr.create_review_request, reviewers=reviewers)
    return ToolResult(content=f"Review requested from: {', '.join(reviewers)}")
  except Exception as e:
    return log_and_format_error("request_pr_reviewers", e, ErrorCategory.PR)


async def mark_pr_ready(args: dict[str, Any]) -> ToolResult:
  try:
    spec = validate_repo_spec(args)
    number = validate_positive_int(args.get("number"), "number")

    # PyGithub doesn't have a direct "ready for review" method
    # Use the GraphQL API via the requester
    gh = get_client().gh
    repo = await run_sync(gh.get_repo, spec)
    pr = await run_sync(repo.get_pull, number)

    if not pr.draft:
      return ToolResult(content=f"PR #{number} is already marked as ready.")

    # Use the REST API endpoint
    _headers, _data = await run_sync(
      gh._Github__requester.requestJsonAndCheck,
      "PUT",
      f"{pr.url}/ready_for_review",
    )
    return ToolResult(content=f"PR #{number} marked as ready for review.")
  except Exception as e:
    return log_and_format_error("mark_pr_ready", e, ErrorCategory.PR)
