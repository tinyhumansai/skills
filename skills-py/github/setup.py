"""
GitHub skill setup flow — PAT authentication.

Single step: personal access token entry. Skips if GITHUB_TOKEN env
is set and valid.
"""

from __future__ import annotations

import contextlib
import json
import logging
import os
from typing import Any

from dev.types.setup_types import (
  SetupField,
  SetupFieldError,
  SetupResult,
  SetupStep,
)

log = logging.getLogger("skill.github.setup")

# ---------------------------------------------------------------------------
# Module-level transient state (cleared on restart or cancel)
# ---------------------------------------------------------------------------

_token: str = ""


def _reset_state() -> None:
  global _token
  _token = ""


# ---------------------------------------------------------------------------
# Step definitions
# ---------------------------------------------------------------------------

STEP_TOKEN = SetupStep(
  id="token",
  title="GitHub Personal Access Token",
  description=(
    "Enter a GitHub Personal Access Token (classic or fine-grained). "
    "Create one at https://github.com/settings/tokens with repo, "
    "workflow, gist, and notifications scopes."
  ),
  fields=[
    SetupField(
      name="token",
      type="password",
      label="Personal Access Token",
      description="Starts with ghp_ or github_pat_",
      required=True,
      placeholder="ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
    ),
  ],
)


# ---------------------------------------------------------------------------
# Hook handlers
# ---------------------------------------------------------------------------


async def on_setup_start(ctx: Any) -> SetupStep | SetupResult:
  """Return the first setup step, or skip if already authenticated."""
  _reset_state()

  # Check environment variable first
  env_token = os.environ.get("GITHUB_TOKEN", "").strip()
  if env_token:
    try:
      from github import Auth, Github

      gh = Github(auth=Auth.Token(env_token))
      user = gh.get_user()
      username = user.login
      gh.close()

      # Persist config
      config = {"token": env_token, "username": username}
      with contextlib.suppress(Exception):
        await ctx.write_data("config.json", json.dumps(config, indent=2))

      log.info("Using GITHUB_TOKEN from environment — authenticated as %s", username)
      return SetupResult(
        status="complete",
        message=f"Connected as @{username} (from GITHUB_TOKEN env).",
      )
    except Exception as exc:
      log.warning("GITHUB_TOKEN env invalid (%s), falling back to manual entry", exc)

  # Check existing config
  try:
    raw = await ctx.read_data("config.json")
    if raw:
      config = json.loads(raw)
      saved_token = config.get("token", "")
      if saved_token:
        from github import Auth, Github

        gh = Github(auth=Auth.Token(saved_token))
        user = gh.get_user()
        username = user.login
        gh.close()

        log.info("Existing config valid — authenticated as %s", username)
        return SetupResult(
          status="complete",
          message=f"Already connected as @{username}.",
        )
  except Exception:
    pass

  return STEP_TOKEN


async def on_setup_submit(ctx: Any, step_id: str, values: dict[str, Any]) -> SetupResult:
  """Validate and process a submitted step."""
  if step_id == "token":
    return await _handle_token(ctx, values)

  return SetupResult(
    status="error",
    errors=[SetupFieldError(field="", message=f"Unknown step: {step_id}")],
  )


async def on_setup_cancel(ctx: Any) -> None:
  """Clean up transient state on cancel."""
  _reset_state()


# ---------------------------------------------------------------------------
# Step handlers
# ---------------------------------------------------------------------------


async def _handle_token(ctx: Any, values: dict[str, Any]) -> SetupResult:
  global _token

  raw_token = str(values.get("token", "")).strip()
  if not raw_token:
    return SetupResult(
      status="error",
      errors=[SetupFieldError(field="token", message="Token is required")],
    )

  # Basic format check
  if not (
    raw_token.startswith("ghp_")
    or raw_token.startswith("github_pat_")
    or raw_token.startswith("gho_")
    or raw_token.startswith("ghu_")
    or raw_token.startswith("ghs_")
  ):
    return SetupResult(
      status="error",
      errors=[
        SetupFieldError(
          field="token",
          message="Token should start with ghp_, github_pat_, gho_, ghu_, or ghs_",
        )
      ],
    )

  # Validate by calling the API
  try:
    from github import Auth, Github, GithubException

    gh = Github(auth=Auth.Token(raw_token))
    user = gh.get_user()
    username = user.login
    gh.close()
  except GithubException as exc:
    return SetupResult(
      status="error",
      errors=[
        SetupFieldError(
          field="token",
          message=f"Invalid token: {exc.data.get('message', str(exc)) if hasattr(exc, 'data') and exc.data else str(exc)}",
        )
      ],
    )
  except Exception as exc:
    return SetupResult(
      status="error",
      errors=[SetupFieldError(field="token", message=f"Validation failed: {exc}")],
    )

  # Persist config
  config = {"token": raw_token, "username": username}
  try:
    await ctx.write_data("config.json", json.dumps(config, indent=2))
  except Exception:
    log.warning("Could not persist config.json via ctx.write_data")

  _reset_state()

  return SetupResult(
    status="complete",
    message=f"Connected as @{username}! Token saved.",
  )
