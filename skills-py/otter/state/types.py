"""
Otter.ai state types for the runtime skill.

These types are used in-process by the skill and a summary
is pushed to the host via reverse RPC for React UI consumption.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

OtterConnectionStatus = Literal["disconnected", "connecting", "connected", "error"]


class OtterUser(BaseModel):
  id: str = ""
  email: str = ""
  name: str = ""


class OtterSpeaker(BaseModel):
  speaker_id: str
  name: str = ""


class OtterSpeech(BaseModel):
  speech_id: str
  title: str = ""
  created_at: float = 0
  duration: float = 0
  summary: str | None = None
  speaker_count: int = 0
  word_count: int = 0
  folder_id: str | None = None
  is_processed: bool = False
  raw_json: dict[str, Any] | None = None


class OtterTranscriptSegment(BaseModel):
  text: str = ""
  start_offset: float = 0
  end_offset: float = 0
  speaker_id: str | None = None
  speaker_name: str | None = None


class OtterState(BaseModel):
  """Full in-process state."""

  connection_status: OtterConnectionStatus = "disconnected"
  connection_error: str | None = None
  is_initialized: bool = False
  is_syncing: bool = False
  last_sync: float | None = None
  current_user: OtterUser | None = None
  speeches: dict[str, OtterSpeech] = Field(default_factory=dict)
  speeches_order: list[str] = Field(default_factory=list)
  speakers: dict[str, OtterSpeaker] = Field(default_factory=dict)
  total_meetings: int = 0


class OtterHostState(BaseModel):
  """Subset pushed to host for React UI consumption."""

  connection_status: OtterConnectionStatus = "disconnected"
  is_initialized: bool = False
  current_user: OtterUser | None = None
  total_meetings: int = 0
  last_sync: float | None = None


def initial_state() -> OtterState:
  return OtterState()
