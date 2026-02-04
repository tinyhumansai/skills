"""
Email state types for the runtime skill.

These types are used in-process by the skill and a summary
is pushed to the host via reverse RPC for React UI consumption.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

EmailConnectionStatus = Literal["disconnected", "connecting", "connected", "error"]


class EmailAccount(BaseModel):
  email: str
  provider: str = "custom"
  display_name: str | None = None
  imap_host: str = ""
  imap_port: int = 993
  smtp_host: str = ""
  smtp_port: int = 587
  use_ssl: bool = True


class EmailFolder(BaseModel):
  name: str
  delimiter: str = "/"
  flags: list[str] = Field(default_factory=list)
  total_messages: int = 0
  unseen_messages: int = 0
  recent_messages: int = 0
  uidvalidity: int = 0
  uidnext: int = 0


class EmailAddress(BaseModel):
  email: str
  display_name: str | None = None


class EmailAttachment(BaseModel):
  index: int
  filename: str
  content_type: str
  size: int = 0


class ParsedEmail(BaseModel):
  uid: int
  message_id: str = ""
  in_reply_to: str | None = None
  references: list[str] = Field(default_factory=list)
  thread_id: str = ""
  from_addr: EmailAddress | None = None
  to_addrs: list[EmailAddress] = Field(default_factory=list)
  cc_addrs: list[EmailAddress] = Field(default_factory=list)
  bcc_addrs: list[EmailAddress] = Field(default_factory=list)
  subject: str = ""
  date: float = 0
  body_text: str = ""
  body_html: str = ""
  body_preview: str = ""
  is_read: bool = False
  is_flagged: bool = False
  is_answered: bool = False
  is_draft: bool = False
  has_attachments: bool = False
  attachment_count: int = 0
  attachments: list[EmailAttachment] = Field(default_factory=list)
  raw_size: int = 0


class EmailContact(BaseModel):
  email: str
  display_name: str | None = None
  last_seen: float = 0
  message_count: int = 0


class SyncState(BaseModel):
  folder: str
  uidvalidity: int = 0
  last_seen_uid: int = 0
  last_full_sync: float = 0


class EmailState(BaseModel):
  """Full in-process state."""

  # Connection
  connection_status: EmailConnectionStatus = "disconnected"
  connection_error: str | None = None
  is_initialized: bool = False
  # Account
  account: EmailAccount | None = None
  # Folders
  folders: dict[str, EmailFolder] = Field(default_factory=dict)
  # Sync
  is_syncing: bool = False
  last_sync: float = 0
  sync_states: dict[str, SyncState] = Field(default_factory=dict)
  # Stats
  total_unread: int = 0


class EmailHostState(BaseModel):
  """Subset pushed to host for React UI consumption."""

  connection_status: EmailConnectionStatus = "disconnected"
  is_initialized: bool = False
  account: EmailAccount | None = None
  total_unread: int = 0
  folder_count: int = 0


def initial_state() -> EmailState:
  return EmailState()
