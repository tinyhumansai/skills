"""
Trigger condition evaluator.

Pure functions for evaluating trigger conditions against data dicts.
Used by skills to check whether incoming events match registered triggers.

Usage:
    from dev.utils.conditions import evaluate_condition

    matched = evaluate_condition(condition, {"message": {"text": "BTC pump!"}})
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
  from dev.types.trigger_types import TriggerCondition

MAX_NESTING_DEPTH = 5


def resolve_field(data: dict[str, Any], dot_path: str) -> Any:
  """Resolve a dot-separated path into a nested dict value.

  Examples:
      resolve_field({"message": {"text": "hello"}}, "message.text") → "hello"
      resolve_field({}, "missing.key") → None
  """
  current: Any = data
  for part in dot_path.split("."):
    if isinstance(current, dict):
      current = current.get(part)
    else:
      return None
    if current is None:
      return None
  return current


def evaluate_condition(
  condition: TriggerCondition,
  data: dict[str, Any],
  _depth: int = 0,
) -> bool:
  """Evaluate a trigger condition against a data dict.

  Returns True if the condition matches, False otherwise.
  Gracefully handles missing fields, invalid regex, type errors.
  """
  if _depth > MAX_NESTING_DEPTH:
    return False

  ctype = condition.type

  if ctype == "regex":
    return _eval_regex(condition, data)
  if ctype == "keyword":
    return _eval_keyword(condition, data)
  if ctype == "threshold":
    return _eval_threshold(condition, data)
  if ctype == "and":
    return _eval_and(condition, data, _depth)
  if ctype == "or":
    return _eval_or(condition, data, _depth)
  if ctype == "not":
    return _eval_not(condition, data, _depth)

  return False


# ---------------------------------------------------------------------------
# Leaf evaluators
# ---------------------------------------------------------------------------


def _eval_regex(condition: TriggerCondition, data: dict[str, Any]) -> bool:
  if not condition.field or not condition.pattern:
    return False
  value = resolve_field(data, condition.field)
  if value is None:
    return False
  text = str(value)
  flags = 0
  if condition.flags:
    if "i" in condition.flags:
      flags |= re.IGNORECASE
    if "m" in condition.flags:
      flags |= re.MULTILINE
    if "s" in condition.flags:
      flags |= re.DOTALL
  try:
    return re.search(condition.pattern, text, flags) is not None
  except re.error:
    return False


def _eval_keyword(condition: TriggerCondition, data: dict[str, Any]) -> bool:
  if not condition.field or not condition.keywords:
    return False
  value = resolve_field(data, condition.field)
  if value is None:
    return False
  text = str(value).lower()
  mode = condition.match_mode or "any"
  if mode == "all":
    return all(kw.lower() in text for kw in condition.keywords)
  return any(kw.lower() in text for kw in condition.keywords)


def _eval_threshold(condition: TriggerCondition, data: dict[str, Any]) -> bool:
  if not condition.field or condition.operator is None or condition.value is None:
    return False
  value = resolve_field(data, condition.field)
  if value is None:
    return False
  try:
    num = float(value)
  except (TypeError, ValueError):
    return False
  op = condition.operator
  threshold = condition.value
  if op == "gt":
    return num > threshold
  if op == "lt":
    return num < threshold
  if op == "eq":
    return num == threshold
  if op == "gte":
    return num >= threshold
  if op == "lte":
    return num <= threshold
  if op == "neq":
    return num != threshold
  return False


# ---------------------------------------------------------------------------
# Compound evaluators
# ---------------------------------------------------------------------------


def _eval_and(condition: TriggerCondition, data: dict[str, Any], depth: int) -> bool:
  if not condition.conditions:
    return False
  return all(evaluate_condition(c, data, depth + 1) for c in condition.conditions)


def _eval_or(condition: TriggerCondition, data: dict[str, Any], depth: int) -> bool:
  if not condition.conditions:
    return False
  return any(evaluate_condition(c, data, depth + 1) for c in condition.conditions)


def _eval_not(condition: TriggerCondition, data: dict[str, Any], depth: int) -> bool:
  if not condition.conditions or len(condition.conditions) == 0:
    return False
  return not evaluate_condition(condition.conditions[0], data, depth + 1)
