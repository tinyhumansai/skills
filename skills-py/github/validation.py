"""
Input validation helpers for GitHub tool arguments.
"""

from __future__ import annotations

import re
from typing import Any


class ValidationError(Exception):
  pass


_OWNER_REPO_RE = re.compile(r"^[a-zA-Z0-9._-]+/[a-zA-Z0-9._-]+$")
_USERNAME_RE = re.compile(r"^[a-zA-Z0-9](?:[a-zA-Z0-9._-]*[a-zA-Z0-9])?$")


def req_string(args: dict[str, Any], key: str) -> str:
  """Read a required string from args."""
  v = args.get(key)
  if not isinstance(v, str) or not v.strip():
    raise ValidationError(f"Missing required parameter: {key}")
  return v.strip()


def opt_string(args: dict[str, Any], key: str) -> str | None:
  """Read an optional string from args."""
  v = args.get(key)
  if isinstance(v, str) and v.strip():
    return v.strip()
  return None


def opt_number(args: dict[str, Any], key: str, fallback: int) -> int:
  """Read an optional number from args with a fallback."""
  v = args.get(key)
  if isinstance(v, (int, float)):
    return int(v)
  return fallback


def opt_boolean(args: dict[str, Any], key: str, fallback: bool = False) -> bool:
  """Read an optional boolean from args."""
  v = args.get(key)
  return v if isinstance(v, bool) else fallback


def opt_string_list(args: dict[str, Any], key: str) -> list[str]:
  """Read an optional list of strings from args."""
  v = args.get(key)
  if isinstance(v, list):
    return [str(item).strip() for item in v if item]
  if isinstance(v, str) and v.strip():
    return [s.strip() for s in v.split(",") if s.strip()]
  return []


def validate_owner_repo(args: dict[str, Any]) -> tuple[str, str]:
  """Extract and validate owner and repo from args."""
  owner = req_string(args, "owner")
  repo = req_string(args, "repo")
  if not _USERNAME_RE.match(owner):
    raise ValidationError(f"Invalid owner: '{owner}'")
  return owner, repo


def validate_repo_spec(args: dict[str, Any]) -> str:
  """Return 'owner/repo' string from args."""
  owner, repo = validate_owner_repo(args)
  return f"{owner}/{repo}"


def validate_username(value: str) -> str:
  """Validate a GitHub username."""
  value = value.strip().lstrip("@")
  if not value or not _USERNAME_RE.match(value):
    raise ValidationError(f"Invalid GitHub username: '{value}'")
  return value


def validate_positive_int(value: Any, param_name: str) -> int:
  """Validate a positive integer parameter."""
  if isinstance(value, (int, float)):
    iv = int(value)
    if iv <= 0:
      raise ValidationError(f"Invalid {param_name}: must be a positive integer.")
    return iv
  if isinstance(value, str):
    try:
      iv = int(value)
    except ValueError:
      raise ValidationError(f"Invalid {param_name}: must be a positive integer.")
    if iv <= 0:
      raise ValidationError(f"Invalid {param_name}: must be a positive integer.")
    return iv
  raise ValidationError(f"Invalid {param_name}: must be a positive integer.")
