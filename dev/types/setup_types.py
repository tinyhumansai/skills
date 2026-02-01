"""
AlphaHuman Setup Flow Types — Pydantic v2 Edition

Type definitions for the interactive skill setup/configuration wizard.
Skills with `has_setup=True` use these types to define multi-step forms
that the host renders as UI.

Usage:
    from dev.types.setup_types import SetupField, SetupStep, SetupResult
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class SetupFieldOption(BaseModel):
  """An option for select/multiselect setup fields."""

  model_config = ConfigDict(frozen=True)

  label: str
  value: str


class SetupField(BaseModel):
  """A single field in a setup step form."""

  model_config = ConfigDict(frozen=True)

  name: str = Field(description="Field key (unique within step)")
  type: Literal["text", "number", "password", "select", "multiselect", "boolean"]
  label: str = Field(description="Display label")
  description: str | None = None
  required: bool = True
  default: str | float | bool | list[str] | None = None
  placeholder: str | None = None
  options: list[SetupFieldOption] | None = None


class SetupStep(BaseModel):
  """A single step in the setup wizard."""

  model_config = ConfigDict(frozen=True)

  id: str
  title: str
  description: str | None = None
  fields: list[SetupField]


class SetupFieldError(BaseModel):
  """A validation error for a specific field."""

  model_config = ConfigDict(frozen=True)

  field: str
  message: str


class SetupResult(BaseModel):
  """Result of a setup/submit call."""

  model_config = ConfigDict(frozen=True)

  status: Literal["next", "error", "complete"]
  next_step: SetupStep | None = None
  errors: list[SetupFieldError] | None = None
  message: str | None = None
