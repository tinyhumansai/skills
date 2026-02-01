"""
Shared types for Telegram API modules.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, TypeVar

T = TypeVar("T")


@dataclass
class ApiResult(Generic[T]):
  """Result wrapper for API calls with optional caching."""

  data: T
  from_cache: bool = False
