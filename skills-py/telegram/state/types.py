"""
Telegram state types for the runtime skill.

Ported from state/types.ts.
These types are used in-process by the skill and a summary
is pushed to the host via reverse RPC for React UI consumption.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

TelegramConnectionStatus = Literal["disconnected", "connecting", "connected", "error"]

TelegramAuthStatus = Literal["not_authenticated", "authenticating", "authenticated", "error"]


class TelegramUser(BaseModel):
  id: str
  first_name: str = ""
  last_name: str | None = None
  username: str | None = None
  phone_number: str | None = None
  is_bot: bool = False
  is_verified: bool | None = None
  is_premium: bool | None = None
  access_hash: str | None = None


class TelegramChat(BaseModel):
  id: str
  title: str | None = None
  type: Literal["private", "group", "supergroup", "channel"] = "private"
  username: str | None = None
  access_hash: str | None = None
  unread_count: int = 0
  last_message: TelegramMessage | None = None
  last_message_date: float | None = None
  is_pinned: bool = False
  is_muted: bool = False
  is_archived: bool = False
  draft_message: str | None = None
  photo: dict[str, str | None] | None = None
  participants_count: int | None = None


class TelegramMessage(BaseModel):
  id: str
  chat_id: str
  thread_id: str | None = None
  date: float = 0
  message: str = ""
  from_id: str | None = None
  from_name: str | None = None
  is_outgoing: bool = False
  is_edited: bool = False
  is_forwarded: bool = False
  reply_to_message_id: str | None = None
  media: dict[str, Any] | None = None
  reactions: list[dict[str, Any]] | None = None
  views: int | None = None


class TelegramThread(BaseModel):
  id: str
  chat_id: str
  title: str = ""
  message_count: int = 0
  last_message: TelegramMessage | None = None
  last_message_date: float | None = None
  unread_count: int = 0
  is_pinned: bool = False


# Forward ref resolution
TelegramChat.model_rebuild()

MAIN_THREAD_ID = "__main__"


class TelegramState(BaseModel):
  """Full in-process state."""

  # Connection
  connection_status: TelegramConnectionStatus = "disconnected"
  connection_error: str | None = None
  # Auth
  auth_status: TelegramAuthStatus = "not_authenticated"
  auth_error: str | None = None
  is_initialized: bool = False
  phone_number: str | None = None
  session_string: str | None = None
  # Sync
  is_syncing: bool = False
  is_synced: bool = False
  initial_sync_complete: bool = False
  sync_pts: int = 0
  sync_qts: int = 0
  sync_date: int = 0
  sync_seq: int = 0
  # User
  current_user: TelegramUser | None = None
  # Users map
  users: dict[str, TelegramUser] = Field(default_factory=dict)
  # Chats
  chats: dict[str, TelegramChat] = Field(default_factory=dict)
  chats_order: list[str] = Field(default_factory=list)
  selected_chat_id: str | None = None
  # Messages — nested by chat_id
  messages: dict[str, dict[str, TelegramMessage]] = Field(default_factory=dict)
  messages_order: dict[str, list[str]] = Field(default_factory=dict)
  # Threads
  threads: dict[str, dict[str, TelegramThread]] = Field(default_factory=dict)
  threads_order: dict[str, list[str]] = Field(default_factory=dict)
  selected_thread_id: str | None = None
  # Loading
  is_loading_chats: bool = False
  is_loading_messages: bool = False
  is_loading_threads: bool = False
  # Pagination
  has_more_chats: bool = True
  has_more_messages: dict[str, bool] = Field(default_factory=dict)
  has_more_threads: dict[str, bool] = Field(default_factory=dict)
  # Search
  search_query: str | None = None
  filtered_chat_ids: list[str] | None = None


class TelegramHostState(BaseModel):
  """Subset pushed to host for React UI consumption."""

  connection_status: TelegramConnectionStatus = "disconnected"
  auth_status: TelegramAuthStatus = "not_authenticated"
  is_initialized: bool = False
  is_syncing: bool = False
  initial_sync_complete: bool = False
  current_user: TelegramUser | None = None
  chats_order: list[str] = Field(default_factory=list)
  chats: dict[str, TelegramChat] = Field(default_factory=dict)
  total_unread: int = 0


def initial_state() -> TelegramState:
  return TelegramState()
