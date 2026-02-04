"""Search domain tool handlers."""

from __future__ import annotations

from typing import Any

from ..client.gh_client import get_client, run_sync
from ..helpers import ErrorCategory, ToolResult, log_and_format_error
from ..validation import opt_number, opt_string, req_string


async def search_repos(args: dict[str, Any]) -> ToolResult:
  try:
    query = req_string(args, "query")
    limit = opt_number(args, "limit", 20)
    sort = opt_string(args, "sort") or "stars"
    order = opt_string(args, "order") or "desc"

    gh = get_client().gh
    results = await run_sync(gh.search_repositories, query, sort=sort, order=order)
    items = await run_sync(lambda: list(results[:limit]))

    if not items:
      return ToolResult(content=f"No repos found for: {query}")
    lines = []
    for r in items:
      vis = "private" if r.private else "public"
      desc = (r.description or "")[:80]
      lang = r.language or ""
      line = f"{r.full_name} [{vis}] ({r.stargazers_count} stars)"
      if lang:
        line += f" [{lang}]"
      if desc:
        line += f" - {desc}"
      lines.append(line)
    return ToolResult(content="\n".join(lines))
  except Exception as e:
    return log_and_format_error("search_repos", e, ErrorCategory.SEARCH)


async def search_issues(args: dict[str, Any]) -> ToolResult:
  try:
    query = req_string(args, "query")
    limit = opt_number(args, "limit", 20)
    sort = opt_string(args, "sort") or "created"

    gh = get_client().gh
    results = await run_sync(gh.search_issues, query, sort=sort)
    items = await run_sync(lambda: list(results[:limit]))

    if not items:
      return ToolResult(content=f"No issues found for: {query}")
    lines = []
    for i in items:
      repo_name = i.repository.full_name if i.repository else ""
      author = i.user.login if i.user else ""
      prefix = f"[{repo_name}] " if repo_name else ""
      line = f"{prefix}#{i.number} [{i.state.upper()}] {i.title[:80]}"
      if author:
        line += f" (by @{author})"
      lines.append(line)
    return ToolResult(content="\n".join(lines))
  except Exception as e:
    return log_and_format_error("search_issues", e, ErrorCategory.SEARCH)


async def search_code(args: dict[str, Any]) -> ToolResult:
  try:
    query = req_string(args, "query")
    limit = opt_number(args, "limit", 20)
    repo = opt_string(args, "repo")
    language = opt_string(args, "language")

    # Build search qualifiers
    full_query = query
    if repo:
      full_query += f" repo:{repo}"
    if language:
      full_query += f" language:{language}"

    gh = get_client().gh
    results = await run_sync(gh.search_code, full_query)
    items = await run_sync(lambda: list(results[:limit]))

    if not items:
      return ToolResult(content=f"No code matches for: {query}")
    lines = []
    for c in items:
      repo_name = c.repository.full_name if c.repository else ""
      lines.append(f"[{repo_name}] {c.path}")
    return ToolResult(content="\n".join(lines))
  except Exception as e:
    return log_and_format_error("search_code", e, ErrorCategory.SEARCH)


async def search_commits(args: dict[str, Any]) -> ToolResult:
  try:
    query = req_string(args, "query")
    limit = opt_number(args, "limit", 20)
    repo = opt_string(args, "repo")

    full_query = query
    if repo:
      full_query += f" repo:{repo}"

    gh = get_client().gh
    results = await run_sync(gh.search_commits, full_query)
    items = await run_sync(lambda: list(results[:limit]))

    if not items:
      return ToolResult(content=f"No commits found for: {query}")
    lines = []
    for c in items:
      sha = c.sha[:7] if c.sha else "?"
      msg = (c.commit.message or "").split("\n")[0][:80]
      author = c.commit.author.name if c.commit.author else ""
      repo_name = c.repository.full_name if hasattr(c, "repository") and c.repository else ""
      prefix = f"[{repo_name}] " if repo_name else ""
      lines.append(f"{prefix}{sha} {msg}" + (f" (by {author})" if author else ""))
    return ToolResult(content="\n".join(lines))
  except Exception as e:
    return log_and_format_error("search_commits", e, ErrorCategory.SEARCH)
