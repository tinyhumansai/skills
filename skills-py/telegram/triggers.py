"""
Telegram trigger registry & evaluation.

In-memory storage for trigger instances. Evaluates incoming Telegram events
against registered triggers using the condition evaluator from dev.utils.

Rate-limits trigger fires to prevent flooding (5-second per-trigger cooldown).
"""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING, Any

from dev.utils.conditions import evaluate_condition

if TYPE_CHECKING:
  from dev.types.trigger_types import TriggerInstance

log = logging.getLogger("skill.telegram.triggers")

# ---------------------------------------------------------------------------
# In-memory registry
# ---------------------------------------------------------------------------

_triggers: dict[str, TriggerInstance] = {}
_last_fired: dict[str, float] = {}  # trigger_id → last fire timestamp

COOLDOWN_SECONDS = 5.0


def register_trigger(trigger: TriggerInstance) -> None:
  """Register a trigger in the in-memory store."""
  _triggers[trigger.id] = trigger
  log.debug("Registered trigger %s (%s)", trigger.id, trigger.name)


def remove_trigger(trigger_id: str) -> None:
  """Remove a trigger from the in-memory store."""
  _triggers.pop(trigger_id, None)
  _last_fired.pop(trigger_id, None)
  log.debug("Removed trigger %s", trigger_id)


def clear_all() -> None:
  """Remove all triggers (called on skill unload)."""
  _triggers.clear()
  _last_fired.clear()


def get_active_triggers(trigger_type: str) -> list[TriggerInstance]:
  """Return enabled triggers of a given type."""
  return [t for t in _triggers.values() if t.type == trigger_type and t.enabled]


# ---------------------------------------------------------------------------
# Message trigger evaluation
# ---------------------------------------------------------------------------


def evaluate_message_triggers(
  message_data: dict[str, Any],
  chat_name: str,
) -> list[tuple[TriggerInstance, dict[str, Any]]]:
  """Evaluate all message_match triggers against incoming message data.

  Returns a list of (trigger, matched_data) for triggers whose conditions matched.
  Applies config filters (chat_filter, sender_filter, exclude_outgoing) and rate limiting.
  """
  results: list[tuple[TriggerInstance, dict[str, Any]]] = []
  now = time.monotonic()

  for trigger in get_active_triggers("message_match"):
    # Rate limiting
    last = _last_fired.get(trigger.id, 0.0)
    if now - last < COOLDOWN_SECONDS:
      continue

    # Config-based pre-filters
    config = trigger.config
    if config.get("exclude_outgoing", True):
      msg = message_data.get("message", {})
      if msg.get("is_outgoing"):
        continue

    chat_filter = config.get("chat_filter", "")
    if chat_filter and chat_filter.lower() not in chat_name.lower():
      continue

    sender_filter = config.get("sender_filter", "")
    if sender_filter:
      sender_name = message_data.get("message", {}).get("sender_name", "")
      if sender_filter.lower() not in str(sender_name).lower():
        continue

    # Evaluate conditions
    all_matched = True
    for cond in trigger.conditions:
      if not evaluate_condition(cond, message_data):
        all_matched = False
        break

    if all_matched:
      _last_fired[trigger.id] = now
      matched = {
        "message_text": message_data.get("message", {}).get("text", ""),
        "sender_name": message_data.get("message", {}).get("sender_name", ""),
        "chat_name": chat_name,
        "chat_id": message_data.get("message", {}).get("chat_id", ""),
      }
      results.append((trigger, matched))

  return results


# ---------------------------------------------------------------------------
# Chat event trigger evaluation
# ---------------------------------------------------------------------------


def evaluate_chat_event_triggers(
  event_data: dict[str, Any],
) -> list[tuple[TriggerInstance, dict[str, Any]]]:
  """Evaluate all chat_event triggers against incoming chat action data.

  Returns a list of (trigger, matched_data) for triggers whose conditions matched.
  """
  results: list[tuple[TriggerInstance, dict[str, Any]]] = []
  now = time.monotonic()

  for trigger in get_active_triggers("chat_event"):
    last = _last_fired.get(trigger.id, 0.0)
    if now - last < COOLDOWN_SECONDS:
      continue

    # Config-based pre-filter
    chat_filter = trigger.config.get("chat_filter", "")
    if chat_filter:
      chat_name = event_data.get("event", {}).get("chat_name", "")
      if chat_filter.lower() not in str(chat_name).lower():
        continue

    # Evaluate conditions
    all_matched = True
    for cond in trigger.conditions:
      if not evaluate_condition(cond, event_data):
        all_matched = False
        break

    if all_matched:
      _last_fired[trigger.id] = now
      matched = {
        "action": event_data.get("event", {}).get("action", ""),
        "chat_name": event_data.get("event", {}).get("chat_name", ""),
        "chat_id": event_data.get("event", {}).get("chat_id", ""),
      }
      results.append((trigger, matched))

  return results
