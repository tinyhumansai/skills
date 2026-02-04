"""
Message domain tool handlers.

Ported from handlers/message.ts.
"""

from __future__ import annotations

from typing import Any

from ..api import message_api
from ..helpers import ErrorCategory, ToolResult, format_message, log_and_format_error
from ..validation import opt_boolean, opt_number, opt_string, validate_id, validate_positive_int


async def get_messages(args: dict[str, Any]) -> ToolResult:
  try:
    chat_id = validate_id(args.get("chat_id"), "chat_id")
    limit = opt_number(args, "limit", 20)
    offset = opt_number(args, "offset", 0)

    result = await message_api.get_messages(str(chat_id), limit, offset)
    if not result.data:
      return ToolResult(content=f"No messages found in chat {chat_id}.")

    lines = []
    for m in result.data:
      f = format_message(m)
      from_str = f" [from: {f.from_id}]" if f.from_id else ""
      media_str = f" [{f.media_type}]" if f.has_media else ""
      lines.append(f"{f.date}{from_str}: {f.text}{media_str}")
    return ToolResult(content="\n".join(lines))
  except Exception as e:
    return log_and_format_error("get_messages", e, ErrorCategory.MSG)


async def list_messages(args: dict[str, Any]) -> ToolResult:
  try:
    chat_id = validate_id(args.get("chat_id"), "chat_id")
    limit = opt_number(args, "limit", 20)

    result = await message_api.get_messages(str(chat_id), limit)
    if not result.data:
      return ToolResult(content=f"No messages in chat {chat_id}.")

    lines = []
    for m in result.data:
      f = format_message(m)
      from_str = f" <{f.from_id}>" if f.from_id else ""
      lines.append(f"[{f.id}] {f.date}{from_str} {f.text}")
    return ToolResult(content="\n".join(lines))
  except Exception as e:
    return log_and_format_error("list_messages", e, ErrorCategory.MSG)


async def list_topics(args: dict[str, Any]) -> ToolResult:
  try:
    chat_id = validate_id(args.get("chat_id"), "chat_id")
    result = await message_api.list_topics(str(chat_id))

    if not result.data:
      return ToolResult(content=f"No topics found in chat {chat_id}.")
    return ToolResult(content="\n".join(str(t) for t in result.data))
  except Exception as e:
    return log_and_format_error("list_topics", e, ErrorCategory.MSG)


async def send_message(args: dict[str, Any]) -> ToolResult:
  try:
    chat_id = validate_id(args.get("chat_id"), "chat_id")
    message = args.get("message", "")
    if not isinstance(message, str) or not message:
      return ToolResult(content="Message content is required", is_error=True)

    await message_api.send_message(str(chat_id), message)
    return ToolResult(content="Message sent successfully.")
  except Exception as e:
    return log_and_format_error("send_message", e, ErrorCategory.MSG)


async def reply_to_message(args: dict[str, Any]) -> ToolResult:
  try:
    chat_id = validate_id(args.get("chat_id"), "chat_id")
    message_id = validate_positive_int(args.get("message_id"), "message_id")
    text = args.get("text", "")
    if not isinstance(text, str) or not text:
      return ToolResult(content="Reply text is required", is_error=True)

    await message_api.reply_to_message(str(chat_id), message_id, text)
    return ToolResult(content="Reply sent successfully.")
  except Exception as e:
    return log_and_format_error("reply_to_message", e, ErrorCategory.MSG)


async def edit_message(args: dict[str, Any]) -> ToolResult:
  try:
    chat_id = validate_id(args.get("chat_id"), "chat_id")
    message_id = validate_positive_int(args.get("message_id"), "message_id")
    new_text = args.get("new_text", "")
    if not isinstance(new_text, str) or not new_text:
      return ToolResult(content="New text is required", is_error=True)

    await message_api.edit_message(str(chat_id), message_id, new_text)
    return ToolResult(content="Message edited successfully.")
  except Exception as e:
    return log_and_format_error("edit_message", e, ErrorCategory.MSG)


async def delete_message(args: dict[str, Any]) -> ToolResult:
  try:
    chat_id = validate_id(args.get("chat_id"), "chat_id")
    message_id = validate_positive_int(args.get("message_id"), "message_id")
    revoke = opt_boolean(args, "revoke", True)

    await message_api.delete_message(str(chat_id), message_id, revoke)
    return ToolResult(content="Message deleted successfully.")
  except Exception as e:
    return log_and_format_error("delete_message", e, ErrorCategory.MSG)


async def forward_message(args: dict[str, Any]) -> ToolResult:
  try:
    from_chat_id = validate_id(args.get("from_chat_id"), "from_chat_id")
    to_chat_id = validate_id(args.get("to_chat_id"), "to_chat_id")
    message_id = validate_positive_int(args.get("message_id"), "message_id")

    await message_api.forward_message(str(from_chat_id), str(to_chat_id), message_id)
    return ToolResult(content="Message forwarded successfully.")
  except Exception as e:
    return log_and_format_error("forward_message", e, ErrorCategory.MSG)


async def pin_message(args: dict[str, Any]) -> ToolResult:
  try:
    chat_id = validate_id(args.get("chat_id"), "chat_id")
    message_id = validate_positive_int(args.get("message_id"), "message_id")
    notify = opt_boolean(args, "notify", True)

    await message_api.pin_message(str(chat_id), message_id, notify)
    return ToolResult(content="Message pinned successfully.")
  except Exception as e:
    return log_and_format_error("pin_message", e, ErrorCategory.MSG)


async def unpin_message(args: dict[str, Any]) -> ToolResult:
  try:
    chat_id = validate_id(args.get("chat_id"), "chat_id")
    message_id = validate_positive_int(args.get("message_id"), "message_id")

    await message_api.unpin_message(str(chat_id), message_id)
    return ToolResult(content="Message unpinned successfully.")
  except Exception as e:
    return log_and_format_error("unpin_message", e, ErrorCategory.MSG)


async def mark_as_read(args: dict[str, Any]) -> ToolResult:
  try:
    chat_id = validate_id(args.get("chat_id"), "chat_id")
    await message_api.mark_as_read(str(chat_id))
    return ToolResult(content="Messages marked as read.")
  except Exception as e:
    return log_and_format_error("mark_as_read", e, ErrorCategory.MSG)


async def get_message_context(args: dict[str, Any]) -> ToolResult:
  try:
    chat_id = validate_id(args.get("chat_id"), "chat_id")
    message_id = validate_positive_int(args.get("message_id"), "message_id")
    limit = opt_number(args, "limit", 5)

    result = await message_api.get_history(str(chat_id), limit * 2 + 1, message_id)
    if not result.data:
      return ToolResult(content=f"No context found for message {message_id}.")

    lines = []
    for m in result.data:
      f = format_message(m)
      marker = " >>> " if str(m.id) == str(message_id) else "     "
      lines.append(f"{marker}[{f.id}] {f.date}: {f.text}")
    return ToolResult(content="\n".join(lines))
  except Exception as e:
    return log_and_format_error("get_message_context", e, ErrorCategory.MSG)


async def get_history(args: dict[str, Any]) -> ToolResult:
  try:
    chat_id = validate_id(args.get("chat_id"), "chat_id")
    limit = opt_number(args, "limit", 20)
    offset_id = args.get("offset_id") if isinstance(args.get("offset_id"), (int, float)) else None

    result = await message_api.get_history(
      str(chat_id), limit, int(offset_id) if offset_id else None
    )
    if not result.data:
      return ToolResult(content=f"No message history in chat {chat_id}.")

    lines = [
      f"[{format_message(m).id}] {format_message(m).date}: {format_message(m).text}"
      for m in result.data
    ]
    return ToolResult(content="\n".join(lines))
  except Exception as e:
    return log_and_format_error("get_history", e, ErrorCategory.MSG)


async def get_pinned_messages(args: dict[str, Any]) -> ToolResult:
  try:
    chat_id = validate_id(args.get("chat_id"), "chat_id")
    result = await message_api.get_pinned_messages(str(chat_id))

    if not result.data:
      return ToolResult(content=f"No pinned messages in chat {chat_id}.")

    lines = [
      f"[{format_message(m).id}] {format_message(m).date}: {format_message(m).text}"
      for m in result.data
    ]
    return ToolResult(content="\n".join(lines))
  except Exception as e:
    return log_and_format_error("get_pinned_messages", e, ErrorCategory.MSG)


async def send_reaction(args: dict[str, Any]) -> ToolResult:
  try:
    chat_id = validate_id(args.get("chat_id"), "chat_id")
    message_id = validate_positive_int(args.get("message_id"), "message_id")
    reaction = args.get("reaction", "\U0001f44d")
    if not isinstance(reaction, str):
      reaction = "\U0001f44d"

    await message_api.send_reaction(str(chat_id), message_id, reaction)
    return ToolResult(content=f"Reaction {reaction} added.")
  except Exception as e:
    return log_and_format_error("send_reaction", e, ErrorCategory.MSG)


async def remove_reaction(args: dict[str, Any]) -> ToolResult:
  try:
    chat_id = validate_id(args.get("chat_id"), "chat_id")
    message_id = validate_positive_int(args.get("message_id"), "message_id")
    reaction = opt_string(args, "reaction")

    await message_api.remove_reaction(str(chat_id), message_id, reaction)
    return ToolResult(content="Reaction removed.")
  except Exception as e:
    return log_and_format_error("remove_reaction", e, ErrorCategory.MSG)


async def get_message_reactions(args: dict[str, Any]) -> ToolResult:
  try:
    chat_id = validate_id(args.get("chat_id"), "chat_id")
    message_id = validate_positive_int(args.get("message_id"), "message_id")

    result = await message_api.get_message_reactions(str(chat_id), message_id)
    if not result.data:
      return ToolResult(content="No reactions on this message.")
    return ToolResult(content="\n".join(str(r) for r in result.data))
  except Exception as e:
    return log_and_format_error("get_message_reactions", e, ErrorCategory.MSG)


async def list_inline_buttons(args: dict[str, Any]) -> ToolResult:
  try:
    chat_id = validate_id(args.get("chat_id"), "chat_id")
    message_id = validate_positive_int(args.get("message_id"), "message_id")
    return ToolResult(
      content=f"Inline buttons for message {message_id} in chat {chat_id}: check message media/replyMarkup."
    )
  except Exception as e:
    return log_and_format_error("list_inline_buttons", e, ErrorCategory.MSG)


async def press_inline_button(args: dict[str, Any]) -> ToolResult:
  try:
    chat_id = validate_id(args.get("chat_id"), "chat_id")
    message_id = validate_positive_int(args.get("message_id"), "message_id")
    return ToolResult(
      content=f"Inline button press for message {message_id} in chat {chat_id} — requires raw message data."
    )
  except Exception as e:
    return log_and_format_error("press_inline_button", e, ErrorCategory.MSG)


async def save_draft(args: dict[str, Any]) -> ToolResult:
  try:
    chat_id = validate_id(args.get("chat_id"), "chat_id")
    text = args.get("text", "")
    if not isinstance(text, str) or not text:
      return ToolResult(content="Draft text is required", is_error=True)
    reply_to_msg_id = (
      args.get("reply_to_message_id")
      if isinstance(args.get("reply_to_message_id"), (int, float))
      else None
    )

    await message_api.save_draft(
      str(chat_id), text, int(reply_to_msg_id) if reply_to_msg_id else None
    )
    return ToolResult(content="Draft saved.")
  except Exception as e:
    return log_and_format_error("save_draft", e, ErrorCategory.DRAFT)


async def get_drafts(args: dict[str, Any]) -> ToolResult:
  try:
    result = await message_api.get_drafts()
    if not result.data:
      return ToolResult(content="No drafts found.")
    return ToolResult(content="\n".join(str(d) for d in result.data))
  except Exception as e:
    return log_and_format_error("get_drafts", e, ErrorCategory.DRAFT)


async def clear_draft(args: dict[str, Any]) -> ToolResult:
  try:
    chat_id = validate_id(args.get("chat_id"), "chat_id")
    await message_api.clear_draft(str(chat_id))
    return ToolResult(content="Draft cleared.")
  except Exception as e:
    return log_and_format_error("clear_draft", e, ErrorCategory.DRAFT)


async def create_poll(args: dict[str, Any]) -> ToolResult:
  try:
    chat_id = validate_id(args.get("chat_id"), "chat_id")
    question = args.get("question", "")
    if not isinstance(question, str) or not question:
      return ToolResult(content="Question is required", is_error=True)
    options = (
      [str(o) for o in args.get("options", [])] if isinstance(args.get("options"), list) else []
    )
    if len(options) < 2:
      return ToolResult(content="At least 2 options are required", is_error=True)

    anonymous = opt_boolean(args, "anonymous", True)
    multiple_choice = opt_boolean(args, "multiple_choice", False)

    await message_api.create_poll(str(chat_id), question, options, anonymous, multiple_choice)
    return ToolResult(content="Poll created successfully.")
  except Exception as e:
    return log_and_format_error("create_poll", e, ErrorCategory.MSG)
