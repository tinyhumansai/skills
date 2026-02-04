"""Release domain tool handlers."""

from __future__ import annotations

from typing import Any

from ..client.gh_client import get_client, run_sync
from ..helpers import ErrorCategory, ToolResult, log_and_format_error, truncate
from ..validation import (
  opt_boolean,
  opt_number,
  opt_string,
  req_string,
  validate_repo_spec,
)


async def list_releases(args: dict[str, Any]) -> ToolResult:
  try:
    spec = validate_repo_spec(args)
    limit = opt_number(args, "limit", 10)

    gh = get_client().gh
    repo = await run_sync(gh.get_repo, spec)
    releases = await run_sync(repo.get_releases)
    items = await run_sync(lambda: list(releases[:limit]))

    if not items:
      return ToolResult(content=f"No releases in {spec}.")
    lines = []
    for r in items:
      tag = r.tag_name or "?"
      name = r.title or tag
      flags = []
      if r.draft:
        flags.append("draft")
      if r.prerelease:
        flags.append("pre-release")
      flag_str = f" [{', '.join(flags)}]" if flags else ""
      date = str(r.published_at or r.created_at or "")
      lines.append(f"{tag} - {name}{flag_str} ({date})")
    return ToolResult(content="\n".join(lines))
  except Exception as e:
    return log_and_format_error("list_releases", e, ErrorCategory.RELEASE)


async def get_release(args: dict[str, Any]) -> ToolResult:
  try:
    spec = validate_repo_spec(args)
    tag = req_string(args, "tag")

    gh = get_client().gh
    repo = await run_sync(gh.get_repo, spec)
    release = await run_sync(repo.get_release, tag)

    author = release.author.login if release.author else ""
    assets = await run_sync(release.get_assets)
    asset_items = await run_sync(lambda: list(assets[:20]))
    asset_lines = []
    for a in asset_items:
      asset_lines.append(f"  - {a.name} ({a.size} bytes, {a.download_count} downloads)")

    lines = [
      f"Release: {release.title or release.tag_name}",
      f"Tag: {release.tag_name}",
      f"Author: @{author}" if author else "",
      f"Draft: {release.draft}",
      f"Pre-release: {release.prerelease}",
      f"Published: {release.published_at or ''}",
    ]
    if asset_lines:
      lines.append(f"Assets ({len(asset_lines)}):")
      lines.extend(asset_lines)
    lines.append("")
    lines.append(truncate(release.body or "(no release notes)", 3000))
    return ToolResult(content="\n".join(l for l in lines if l or l == ""))
  except Exception as e:
    return log_and_format_error("get_release", e, ErrorCategory.RELEASE)


async def create_release(args: dict[str, Any]) -> ToolResult:
  try:
    spec = validate_repo_spec(args)
    tag = req_string(args, "tag")
    title = opt_string(args, "title") or tag
    notes = opt_string(args, "notes") or ""
    draft = opt_boolean(args, "draft", False)
    prerelease = opt_boolean(args, "prerelease", False)
    target = opt_string(args, "target")
    generate_notes = opt_boolean(args, "generate_notes", False)

    gh = get_client().gh
    repo = await run_sync(gh.get_repo, spec)

    kwargs: dict[str, Any] = {
      "tag": tag,
      "name": title,
      "message": notes,
      "draft": draft,
      "prerelease": prerelease,
      "generate_release_notes": generate_notes,
    }
    if target:
      kwargs["target_commitish"] = target

    release = await run_sync(repo.create_git_release, **kwargs)
    return ToolResult(content=f"Release created: {release.html_url}")
  except Exception as e:
    return log_and_format_error("create_release", e, ErrorCategory.RELEASE)


async def delete_release(args: dict[str, Any]) -> ToolResult:
  try:
    spec = validate_repo_spec(args)
    tag = req_string(args, "tag")
    cleanup_tag = opt_boolean(args, "cleanup_tag", False)

    gh = get_client().gh
    repo = await run_sync(gh.get_repo, spec)
    release = await run_sync(repo.get_release, tag)
    await run_sync(release.delete_release)

    msg = f"Release {tag} deleted."
    if cleanup_tag:
      try:
        ref = await run_sync(repo.get_git_ref, f"tags/{tag}")
        await run_sync(ref.delete)
        msg += f" Tag {tag} also deleted."
      except Exception:
        msg += f" (could not delete tag {tag})"
    return ToolResult(content=msg)
  except Exception as e:
    return log_and_format_error("delete_release", e, ErrorCategory.RELEASE)


async def list_release_assets(args: dict[str, Any]) -> ToolResult:
  try:
    spec = validate_repo_spec(args)
    tag = req_string(args, "tag")

    gh = get_client().gh
    repo = await run_sync(gh.get_repo, spec)
    release = await run_sync(repo.get_release, tag)
    assets = await run_sync(release.get_assets)
    items = await run_sync(lambda: list(assets[:30]))

    if not items:
      return ToolResult(content=f"No assets for release {tag}.")
    lines = []
    for a in items:
      lines.append(f"{a.name} ({a.size} bytes, {a.download_count} downloads)")
    return ToolResult(content="\n".join(lines))
  except Exception as e:
    return log_and_format_error("list_release_assets", e, ErrorCategory.RELEASE)


async def get_latest_release(args: dict[str, Any]) -> ToolResult:
  try:
    spec = validate_repo_spec(args)
    gh = get_client().gh
    repo = await run_sync(gh.get_repo, spec)
    release = await run_sync(repo.get_latest_release)

    author = release.author.login if release.author else ""
    lines = [
      f"Latest Release: {release.title or release.tag_name}",
      f"Tag: {release.tag_name}",
      f"Author: @{author}" if author else "",
      f"Published: {release.published_at or ''}",
      "",
      truncate(release.body or "(no release notes)", 2000),
    ]
    return ToolResult(content="\n".join(l for l in lines if l or l == ""))
  except Exception as e:
    return log_and_format_error("get_latest_release", e, ErrorCategory.RELEASE)
