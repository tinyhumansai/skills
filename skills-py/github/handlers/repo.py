"""Repository domain tool handlers."""

from __future__ import annotations

from typing import Any

from ..client.gh_client import get_client, run_sync
from ..helpers import ErrorCategory, ToolResult, log_and_format_error
from ..validation import (
  opt_boolean,
  opt_number,
  opt_string,
  opt_string_list,
  req_string,
  validate_repo_spec,
  validate_username,
)


async def list_repos(args: dict[str, Any]) -> ToolResult:
  try:
    limit = opt_number(args, "limit", 30)
    owner = opt_string(args, "owner")
    visibility = opt_string(args, "visibility")
    sort = opt_string(args, "sort") or "updated"

    gh = get_client().gh
    if owner:
      user = await run_sync(gh.get_user, owner)
      repos = await run_sync(user.get_repos, sort=sort)
    else:
      user = await run_sync(gh.get_user)
      kwargs: dict[str, Any] = {"sort": sort}
      if visibility:
        kwargs["visibility"] = visibility
      repos = await run_sync(user.get_repos, **kwargs)

    items = await run_sync(lambda: list(repos[:limit]))
    if not items:
      return ToolResult(content="No repositories found.")

    lines = []
    for r in items:
      vis = "private" if r.private else "public"
      desc = r.description or ""
      lang = r.language or ""
      line = f"{r.full_name} [{vis}] ({r.stargazers_count} stars)"
      if lang:
        line += f" [{lang}]"
      if desc:
        line += f" - {desc[:80]}"
      lines.append(line)
    return ToolResult(content="\n".join(lines))
  except Exception as e:
    return log_and_format_error("list_repos", e, ErrorCategory.REPO)


async def get_repo(args: dict[str, Any]) -> ToolResult:
  try:
    spec = validate_repo_spec(args)
    gh = get_client().gh
    repo = await run_sync(gh.get_repo, spec)

    lines = [
      f"Repository: {repo.full_name}",
      f"URL: {repo.html_url}",
      f"Visibility: {'private' if repo.private else 'public'}",
      f"Description: {repo.description or 'N/A'}",
      f"Stars: {repo.stargazers_count}",
      f"Forks: {repo.forks_count}",
      f"Open Issues: {repo.open_issues_count}",
      f"Language: {repo.language or 'N/A'}",
      f"Default Branch: {repo.default_branch}",
      f"License: {repo.license.name if repo.license else 'N/A'}",
      f"Archived: {repo.archived}",
      f"Fork: {repo.fork}",
      f"Created: {repo.created_at}",
      f"Updated: {repo.updated_at}",
    ]
    if repo.homepage:
      lines.append(f"Homepage: {repo.homepage}")
    topics = await run_sync(repo.get_topics)
    if topics:
      lines.append(f"Topics: {', '.join(topics)}")
    return ToolResult(content="\n".join(lines))
  except Exception as e:
    return log_and_format_error("get_repo", e, ErrorCategory.REPO)


async def create_repo(args: dict[str, Any]) -> ToolResult:
  try:
    name = req_string(args, "name")
    description = opt_string(args, "description")
    visibility = opt_string(args, "visibility") or "private"
    auto_init = opt_boolean(args, "auto_init", False)

    gh = get_client().gh
    user = await run_sync(gh.get_user)

    kwargs: dict[str, Any] = {
      "name": name,
      "private": visibility == "private",
      "auto_init": auto_init,
    }
    if description:
      kwargs["description"] = description

    repo = await run_sync(user.create_repo, **kwargs)
    return ToolResult(content=f"Repository created: {repo.html_url}")
  except Exception as e:
    return log_and_format_error("create_repo", e, ErrorCategory.REPO)


async def fork_repo(args: dict[str, Any]) -> ToolResult:
  try:
    spec = validate_repo_spec(args)
    fork_name = opt_string(args, "fork_name")

    gh = get_client().gh
    repo = await run_sync(gh.get_repo, spec)

    kwargs: dict[str, Any] = {}
    if fork_name:
      kwargs["name"] = fork_name
    fork = await run_sync(repo.create_fork, **kwargs)
    return ToolResult(content=f"Forked to: {fork.html_url}")
  except Exception as e:
    return log_and_format_error("fork_repo", e, ErrorCategory.REPO)


async def delete_repo(args: dict[str, Any]) -> ToolResult:
  try:
    spec = validate_repo_spec(args)
    confirm = opt_boolean(args, "confirm", False)
    if not confirm:
      return ToolResult(
        content=f"Deleting {spec} is irreversible. Set confirm=true to proceed.",
        is_error=True,
      )
    gh = get_client().gh
    repo = await run_sync(gh.get_repo, spec)
    await run_sync(repo.delete)
    return ToolResult(content=f"Repository {spec} deleted.")
  except Exception as e:
    return log_and_format_error("delete_repo", e, ErrorCategory.REPO)


async def clone_repo(args: dict[str, Any]) -> ToolResult:
  try:
    spec = validate_repo_spec(args)
    gh = get_client().gh
    repo = await run_sync(gh.get_repo, spec)
    return ToolResult(
      content=f"Clone URL (HTTPS): {repo.clone_url}\nClone URL (SSH): {repo.ssh_url}\n\nRun: git clone {repo.clone_url}"
    )
  except Exception as e:
    return log_and_format_error("clone_repo", e, ErrorCategory.REPO)


async def list_collaborators(args: dict[str, Any]) -> ToolResult:
  try:
    spec = validate_repo_spec(args)
    limit = opt_number(args, "limit", 30)
    gh = get_client().gh
    repo = await run_sync(gh.get_repo, spec)
    collabs = await run_sync(repo.get_collaborators)
    items = await run_sync(lambda: list(collabs[:limit]))

    if not items:
      return ToolResult(content="No collaborators found.")
    lines = []
    for c in items:
      perms = []
      if hasattr(c, "permissions") and c.permissions:
        if c.permissions.admin:
          perms.append("admin")
        elif c.permissions.maintain:
          perms.append("maintain")
        elif c.permissions.push:
          perms.append("push")
        elif c.permissions.pull:
          perms.append("pull")
      perm_str = f" [{', '.join(perms)}]" if perms else ""
      lines.append(f"@{c.login}{perm_str}")
    return ToolResult(content="\n".join(lines))
  except Exception as e:
    return log_and_format_error("list_collaborators", e, ErrorCategory.REPO)


async def add_collaborator(args: dict[str, Any]) -> ToolResult:
  try:
    spec = validate_repo_spec(args)
    username = validate_username(req_string(args, "username"))
    permission = opt_string(args, "permission") or "push"

    gh = get_client().gh
    repo = await run_sync(gh.get_repo, spec)
    collab_user = await run_sync(gh.get_user, username)
    await run_sync(repo.add_to_collaborators, collab_user, permission)
    return ToolResult(content=f"Invited @{username} to {spec} with {permission} permission.")
  except Exception as e:
    return log_and_format_error("add_collaborator", e, ErrorCategory.REPO)


async def remove_collaborator(args: dict[str, Any]) -> ToolResult:
  try:
    spec = validate_repo_spec(args)
    username = validate_username(req_string(args, "username"))

    gh = get_client().gh
    repo = await run_sync(gh.get_repo, spec)
    collab_user = await run_sync(gh.get_user, username)
    await run_sync(repo.remove_from_collaborators, collab_user)
    return ToolResult(content=f"Removed @{username} from {spec}.")
  except Exception as e:
    return log_and_format_error("remove_collaborator", e, ErrorCategory.REPO)


async def list_topics(args: dict[str, Any]) -> ToolResult:
  try:
    spec = validate_repo_spec(args)
    gh = get_client().gh
    repo = await run_sync(gh.get_repo, spec)
    topics = await run_sync(repo.get_topics)
    if not topics:
      return ToolResult(content=f"No topics set on {spec}.")
    return ToolResult(content=", ".join(topics))
  except Exception as e:
    return log_and_format_error("list_topics", e, ErrorCategory.REPO)


async def set_topics(args: dict[str, Any]) -> ToolResult:
  try:
    spec = validate_repo_spec(args)
    topics = opt_string_list(args, "topics")
    if not topics:
      return ToolResult(content="At least one topic is required.", is_error=True)

    gh = get_client().gh
    repo = await run_sync(gh.get_repo, spec)
    await run_sync(repo.replace_topics, topics)
    return ToolResult(content=f"Topics set on {spec}: {', '.join(topics)}")
  except Exception as e:
    return log_and_format_error("set_topics", e, ErrorCategory.REPO)


async def list_languages(args: dict[str, Any]) -> ToolResult:
  try:
    spec = validate_repo_spec(args)
    gh = get_client().gh
    repo = await run_sync(gh.get_repo, spec)
    languages = await run_sync(repo.get_languages)

    if not languages:
      return ToolResult(content=f"No languages detected in {spec}.")
    total = sum(languages.values())
    lines = []
    for lang, bytes_count in sorted(languages.items(), key=lambda x: x[1], reverse=True):
      pct = (bytes_count / total * 100) if total else 0
      lines.append(f"{lang}: {pct:.1f}%")
    return ToolResult(content="\n".join(lines))
  except Exception as e:
    return log_and_format_error("list_languages", e, ErrorCategory.REPO)
