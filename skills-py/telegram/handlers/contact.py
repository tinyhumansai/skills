"""
Contact domain tool handlers.

Ported from handlers/contact.ts.
"""

from __future__ import annotations

from typing import Any

from ..api import contact_api
from ..helpers import ErrorCategory, ToolResult, format_entity, log_and_format_error
from ..validation import opt_number, validate_id


async def list_contacts(args: dict[str, Any]) -> ToolResult:
  try:
    limit = opt_number(args, "limit", 20)
    result = await contact_api.list_contacts(limit)

    if not result.data:
      return ToolResult(content="No contacts found.")

    lines = []
    for u in result.data:
      name = " ".join(p for p in [u.first_name, u.last_name] if p) or "Unknown"
      username = f" @{u.username}" if u.username else ""
      phone = f" {u.phone_number}" if u.phone_number else ""
      lines.append(f"{name} (ID: {u.id}){username}{phone}")
    return ToolResult(content="\n".join(lines))
  except Exception as e:
    return log_and_format_error("list_contacts", e, ErrorCategory.CONTACT)


async def search_contacts(args: dict[str, Any]) -> ToolResult:
  try:
    query = args.get("query", "")
    if not isinstance(query, str) or not query:
      return ToolResult(content="Search query is required", is_error=True)
    limit = opt_number(args, "limit", 20)

    result = await contact_api.search_contacts(query, limit)
    if not result.data:
      return ToolResult(content=f'No contacts found matching "{query}".')

    lines = []
    for u in result.data:
      name = " ".join(p for p in [u.first_name, u.last_name] if p) or "Unknown"
      username = f" @{u.username}" if u.username else ""
      lines.append(f"{name} (ID: {u.id}){username}")
    return ToolResult(content="\n".join(lines))
  except Exception as e:
    return log_and_format_error("search_contacts", e, ErrorCategory.CONTACT)


async def add_contact(args: dict[str, Any]) -> ToolResult:
  try:
    first_name = args.get("first_name", "")
    if not isinstance(first_name, str) or not first_name:
      return ToolResult(content="First name is required", is_error=True)
    last_name = args.get("last_name", "") if isinstance(args.get("last_name"), str) else ""
    phone_number = args.get("phone_number", "") if isinstance(args.get("phone_number"), str) else ""
    user_id = args.get("user_id") if isinstance(args.get("user_id"), str) else None
    if not phone_number and not user_id:
      return ToolResult(content="Phone number or user ID is required", is_error=True)

    await contact_api.add_contact(first_name, last_name, phone_number, user_id)
    return ToolResult(content=f"Contact {first_name} {last_name} added successfully.")
  except Exception as e:
    return log_and_format_error("add_contact", e, ErrorCategory.CONTACT)


async def delete_contact(args: dict[str, Any]) -> ToolResult:
  try:
    user_id = validate_id(args.get("user_id"), "user_id")
    await contact_api.delete_contact(str(user_id))
    return ToolResult(content=f"Contact {user_id} deleted.")
  except Exception as e:
    return log_and_format_error("delete_contact", e, ErrorCategory.CONTACT)


async def block_user(args: dict[str, Any]) -> ToolResult:
  try:
    user_id = validate_id(args.get("user_id"), "user_id")
    await contact_api.block_user(str(user_id))
    return ToolResult(content=f"User {user_id} blocked.")
  except Exception as e:
    return log_and_format_error("block_user", e, ErrorCategory.CONTACT)


async def unblock_user(args: dict[str, Any]) -> ToolResult:
  try:
    user_id = validate_id(args.get("user_id"), "user_id")
    await contact_api.unblock_user(str(user_id))
    return ToolResult(content=f"User {user_id} unblocked.")
  except Exception as e:
    return log_and_format_error("unblock_user", e, ErrorCategory.CONTACT)


async def get_blocked_users(args: dict[str, Any]) -> ToolResult:
  try:
    limit = opt_number(args, "limit", 100)
    result = await contact_api.get_blocked_users(limit)

    if not result.data:
      return ToolResult(content="No blocked users.")

    lines = [f"{u.first_name} (ID: {u.id})" for u in result.data]
    return ToolResult(content="\n".join(lines))
  except Exception as e:
    return log_and_format_error("get_blocked_users", e, ErrorCategory.CONTACT)


async def get_contact_ids(args: dict[str, Any]) -> ToolResult:
  try:
    result = await contact_api.get_contact_ids()
    if not result.data:
      return ToolResult(content="No contacts found.")
    return ToolResult(content=f"Contact IDs: {', '.join(result.data)}")
  except Exception as e:
    return log_and_format_error("get_contact_ids", e, ErrorCategory.CONTACT)


async def import_contacts(args: dict[str, Any]) -> ToolResult:
  try:
    contacts = args.get("contacts", [])
    if not isinstance(contacts, list) or not contacts:
      return ToolResult(content="No contacts to import", is_error=True)

    contact_list = [
      {
        "phone": str(c.get("phone", "")),
        "firstName": str(c.get("first_name", "")),
        "lastName": str(c.get("last_name", "")),
      }
      for c in contacts
    ]

    result = await contact_api.import_contacts(contact_list)
    return ToolResult(content=f"Imported {len(result.data)} contacts.")
  except Exception as e:
    return log_and_format_error("import_contacts", e, ErrorCategory.CONTACT)


async def export_contacts(args: dict[str, Any]) -> ToolResult:
  try:
    result = await contact_api.export_contacts()
    if not result.data:
      return ToolResult(content="No contacts to export.")

    lines = []
    for c in result.data:
      name = " ".join(p for p in [c.get("firstName"), c.get("lastName")] if p)
      phone = f" ({c['phone']})" if c.get("phone") else ""
      lines.append(f"{name}{phone}")
    return ToolResult(content="\n".join(lines))
  except Exception as e:
    return log_and_format_error("export_contacts", e, ErrorCategory.CONTACT)


async def get_direct_chat_by_contact(args: dict[str, Any]) -> ToolResult:
  try:
    user_id = validate_id(args.get("user_id"), "user_id")
    result = await contact_api.get_direct_chat_by_contact(str(user_id))
    if not result.data:
      return ToolResult(content=f"No direct chat found with user {user_id}.")
    e = format_entity(result.data)
    return ToolResult(content=f"Direct chat: {e.name} (ID: {e.id})")
  except Exception as e:
    return log_and_format_error("get_direct_chat_by_contact", e, ErrorCategory.CONTACT)


async def get_contact_chats(args: dict[str, Any]) -> ToolResult:
  try:
    limit = opt_number(args, "limit", 20)
    result = await contact_api.get_contact_chats(limit)

    if not result.data:
      return ToolResult(content="No contact chats found.")

    lines = [f"{format_entity(c).name} (ID: {format_entity(c).id})" for c in result.data]
    return ToolResult(content="\n".join(lines))
  except Exception as e:
    return log_and_format_error("get_contact_chats", e, ErrorCategory.CONTACT)


async def get_last_interaction(args: dict[str, Any]) -> ToolResult:
  try:
    user_id = validate_id(args.get("user_id"), "user_id")
    result = await contact_api.get_last_interaction(str(user_id))
    if not result.data:
      return ToolResult(content=f"No interaction found with user {user_id}.")
    return ToolResult(content=str(result.data))
  except Exception as e:
    return log_and_format_error("get_last_interaction", e, ErrorCategory.CONTACT)
