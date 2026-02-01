"""
AlphaHuman Trigger Types — Pydantic v2 Edition

Type definitions for the skill trigger/automation system. Skills declare
trigger types they support, the LLM creates trigger instances via
auto-generated tools, and skills evaluate conditions in their event handlers.

Usage:
    from dev.types.trigger_types import (
        TriggerCondition, TriggerFieldSchema, TriggerTypeDefinition,
        TriggerSchema, TriggerInstance, TriggerFiredEvent,
    )
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Trigger Condition (recursive — supports compound AND/OR/NOT)
# ---------------------------------------------------------------------------


class TriggerCondition(BaseModel):
  """A condition node in a trigger's condition tree.

  Leaf types: regex, keyword, threshold
  Compound types: and, or, not
  """

  model_config = ConfigDict(frozen=True)

  type: Literal["regex", "keyword", "threshold", "and", "or", "not"] = Field(
    description="Condition type"
  )

  # --- Leaf fields (regex / keyword / threshold) ---
  field: str | None = Field(
    default=None, description='Dot-path to the data field, e.g. "message.text"'
  )
  # regex
  pattern: str | None = Field(default=None, description="Regex pattern (for type=regex)")
  flags: str | None = Field(
    default=None, description='Regex flags string, e.g. "i" for case-insensitive'
  )
  # keyword
  keywords: list[str] | None = Field(default=None, description="Keywords to match (for type=keyword)")
  match_mode: Literal["any", "all"] | None = Field(
    default=None, description='Whether any or all keywords must match (default "any")'
  )
  # threshold
  operator: Literal["gt", "lt", "eq", "gte", "lte", "neq"] | None = Field(
    default=None, description="Comparison operator (for type=threshold)"
  )
  value: float | None = Field(default=None, description="Threshold value to compare against")

  # --- Compound fields ---
  conditions: list[TriggerCondition] | None = Field(
    default=None, description="Sub-conditions (for type=and/or/not)"
  )


# Rebuild the model to resolve the self-referencing `conditions` field
TriggerCondition.model_rebuild()


# ---------------------------------------------------------------------------
# Trigger Type Declaration (what a skill says it supports)
# ---------------------------------------------------------------------------


class TriggerFieldSchema(BaseModel):
  """Describes a field usable in trigger conditions."""

  model_config = ConfigDict(frozen=True)

  name: str = Field(description='Dot-path field name, e.g. "message.text"')
  type: str = Field(description="JSON Schema type: string, number, boolean")
  description: str


class TriggerTypeDefinition(BaseModel):
  """Declares a trigger type the skill supports."""

  model_config = ConfigDict(frozen=True)

  type: str = Field(description='Trigger type identifier, e.g. "message_match"')
  label: str = Field(description="Human-readable label")
  description: str
  condition_fields: list[TriggerFieldSchema] = Field(
    default_factory=list,
    description="Fields available for conditions in this trigger type",
  )
  config_schema: dict[str, Any] = Field(
    default_factory=dict,
    description="JSON Schema for trigger-type-specific config",
  )


class TriggerSchema(BaseModel):
  """Collection of trigger types a skill supports (analogous to EntitySchema)."""

  model_config = ConfigDict(frozen=True)

  trigger_types: list[TriggerTypeDefinition] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Trigger Instance (a registered, active trigger)
# ---------------------------------------------------------------------------


class TriggerInstance(BaseModel):
  """A registered trigger instance with conditions and config."""

  id: str = Field(description="Unique trigger ID")
  type: str = Field(description="Trigger type (must match a TriggerTypeDefinition.type)")
  name: str = Field(description="Human-readable trigger name")
  description: str = Field(default="")
  conditions: list[TriggerCondition] = Field(
    default_factory=list,
    description="Conditions that must be met to fire this trigger",
  )
  config: dict[str, Any] = Field(
    default_factory=dict,
    description="Trigger-type-specific configuration",
  )
  enabled: bool = Field(default=True)
  created_at: str = Field(default="")
  metadata: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Trigger Fired Event (reverse RPC payload)
# ---------------------------------------------------------------------------


class TriggerFiredEvent(BaseModel):
  """Payload sent to the host when a trigger fires."""

  model_config = ConfigDict(frozen=True)

  trigger_id: str
  trigger_name: str
  trigger_type: str
  fired_at: str
  matched_data: dict[str, Any] = Field(default_factory=dict)
  context: dict[str, Any] = Field(default_factory=dict)
