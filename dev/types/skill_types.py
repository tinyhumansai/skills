"""
AlphaHuman Skill Types — Pydantic v2 Edition

Type definitions for skill development. Skills import these types
for type checking, validation, and JSON-RPC serialization.

Usage:
    from dev.types.skill_types import SkillDefinition, SkillContext, SkillTool
"""

from __future__ import annotations

from typing import Any, Literal, Protocol, runtime_checkable, Callable, Awaitable, Optional

from pydantic import BaseModel, ConfigDict, Field

from dev.types.setup_types import (  # noqa: F401  — re-exported
    SetupFieldOption,
    SetupField,
    SetupStep,
    SetupFieldError,
    SetupResult,
)


# ---------------------------------------------------------------------------
# Tool Definition & Result
# ---------------------------------------------------------------------------


class ToolDefinition(BaseModel):
    """Schema for an AI-callable tool."""

    model_config = ConfigDict(frozen=True)

    name: str = Field(description="Tool name (snake_case, unique per skill)")
    description: str = Field(description="Human-readable description")
    parameters: dict[str, Any] = Field(
        description="JSON Schema for tool parameters",
        default_factory=lambda: {"type": "object", "properties": {}},
    )


class ToolResult(BaseModel):
    """Result returned by a tool's execute function."""

    content: str
    is_error: bool = False


# ---------------------------------------------------------------------------
# Skill Tool
# ---------------------------------------------------------------------------


class SkillTool(BaseModel):
    """A tool the skill exposes to the AI."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    definition: ToolDefinition
    execute: Callable[..., Awaitable[ToolResult]] = Field(
        description="Async function that executes the tool"
    )


# ---------------------------------------------------------------------------
# Entity
# ---------------------------------------------------------------------------


class Entity(BaseModel):
    """An entity in the platform's entity graph."""

    model_config = ConfigDict(frozen=True)

    id: str
    type: str
    name: str
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Entity Schema Declarations
# ---------------------------------------------------------------------------


class EntityPropertySchema(BaseModel):
    """Describes a property on an entity type."""

    model_config = ConfigDict(frozen=True)

    name: str = Field(description="Property name")
    type: str = Field(description="JSON Schema type: string, number, boolean, array, object")
    description: str
    optional: bool = False


class EntityTypeDeclaration(BaseModel):
    """Declares an entity type a skill produces."""

    model_config = ConfigDict(frozen=True)

    type: str = Field(description='Namespaced type identifier, e.g. "telegram.contact"')
    label: str = Field(description='Human-readable label, e.g. "Telegram Contact"')
    description: str
    properties: list[EntityPropertySchema] = Field(default_factory=list)


class RelationshipTypeDeclaration(BaseModel):
    """Declares a relationship type between entity types."""

    model_config = ConfigDict(frozen=True)

    type: str = Field(description='Relationship identifier, e.g. "member_of"')
    source_type: str = Field(description='Source entity type, e.g. "telegram.contact"')
    target_type: str = Field(description='Target entity type, e.g. "telegram.group"')
    description: str
    cardinality: Literal[
        "one_to_one", "one_to_many", "many_to_one", "many_to_many"
    ] = "many_to_many"


class EntitySchema(BaseModel):
    """Full entity schema for a skill — declares what entity and relationship types it surfaces."""

    model_config = ConfigDict(frozen=True)

    entity_types: list[EntityTypeDeclaration] = Field(default_factory=list)
    relationship_types: list[RelationshipTypeDeclaration] = Field(default_factory=list)


class Relationship(BaseModel):
    """A concrete edge between two entities."""

    model_config = ConfigDict(frozen=True)

    source_id: str
    target_id: str
    type: str
    metadata: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Manager Protocols (interfaces skill authors implement against)
# ---------------------------------------------------------------------------


@runtime_checkable
class MemoryManager(Protocol):
    """Read/write/search the shared memory system."""

    async def read(self, name: str) -> str | None: ...
    async def write(self, name: str, content: str) -> None: ...
    async def search(self, query: str) -> list[dict[str, str]]: ...
    async def list(self) -> list[str]: ...
    async def delete(self, name: str) -> None: ...


@runtime_checkable
class SessionManager(Protocol):
    """Current session manager."""

    @property
    def id(self) -> str: ...
    def get(self, key: str) -> Any: ...
    def set(self, key: str, value: Any) -> None: ...


@runtime_checkable
class ToolRegistry(Protocol):
    """Register/unregister AI tools at runtime."""

    def register(self, tool: SkillTool) -> None: ...
    def unregister(self, name: str) -> None: ...
    def list(self) -> list[str]: ...


@runtime_checkable
class EntityManager(Protocol):
    """Query the platform entity graph."""

    async def get_by_tag(self, tag: str, type: str | None = None) -> list[Entity]: ...
    async def get_by_id(self, id: str) -> Entity | None: ...
    async def search(self, query: str) -> list[Entity]: ...
    async def get_relationships(
        self, entity_id: str, type: str | None = None, direction: str = "outgoing"
    ) -> list[Relationship]: ...


# ---------------------------------------------------------------------------
# Skill Context (Protocol — passed to every hook)
# ---------------------------------------------------------------------------


@runtime_checkable
class SkillContext(Protocol):
    """Context object passed to skill lifecycle hooks."""

    memory: MemoryManager
    session: SessionManager
    tools: ToolRegistry
    entities: EntityManager
    data_dir: str

    async def read_data(self, filename: str) -> str: ...
    async def write_data(self, filename: str, content: str) -> None: ...
    def log(self, message: str) -> None: ...
    def get_state(self) -> Any: ...
    def set_state(self, partial: dict[str, Any]) -> None: ...
    def emit_event(self, event_name: str, data: Any) -> None: ...


# ---------------------------------------------------------------------------
# Hook type aliases
# ---------------------------------------------------------------------------

LoadHook = Callable[[SkillContext], Awaitable[None]]
UnloadHook = Callable[[SkillContext], Awaitable[None]]
SessionHook = Callable[[SkillContext, str], Awaitable[None]]
MessageHook = Callable[[SkillContext, str], Awaitable[str | None]]
TickHook = Callable[[SkillContext], Awaitable[None]]
StatusHook = Callable[[SkillContext], Awaitable[dict[str, Any]]]

SetupStartHandler = Callable[[SkillContext], Awaitable[SetupStep]]
SetupSubmitHandler = Callable[[SkillContext, str, dict[str, Any]], Awaitable[SetupResult]]
SetupCancelHandler = Callable[[SkillContext], Awaitable[None]]


# ---------------------------------------------------------------------------
# Skill Hooks
# ---------------------------------------------------------------------------


class SkillHooks(BaseModel):
    """Lifecycle hooks for a skill."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    on_load: Optional[LoadHook] = None
    on_unload: Optional[UnloadHook] = None
    on_session_start: Optional[SessionHook] = None
    on_session_end: Optional[SessionHook] = None
    on_before_message: Optional[MessageHook] = None
    on_after_response: Optional[MessageHook] = None
    on_memory_flush: Optional[LoadHook] = None
    on_tick: Optional[TickHook] = None
    on_status: StatusHook = Field(description="Returns current skill status information")
    on_setup_start: Optional[SetupStartHandler] = None
    on_setup_submit: Optional[SetupSubmitHandler] = None
    on_setup_cancel: Optional[SetupCancelHandler] = None


# ---------------------------------------------------------------------------
# Skill Tier & Runtime Config
# ---------------------------------------------------------------------------


class SkillRuntimeConfig(BaseModel):
    """Runtime configuration for subprocess skills."""

    model_config = ConfigDict(frozen=True)

    command: str = Field(description='Command to execute (e.g., "python3")')
    args: list[str] = Field(default_factory=list)
    env: dict[str, str] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Skill Definition (the main export from skill.py)
# ---------------------------------------------------------------------------


class SkillDefinition(BaseModel):
    """Top-level skill definition — the `skill` object exported by skill.py."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str = Field(description="Skill name (lowercase-hyphens, matches directory)")
    description: str = Field(description="Brief description")
    version: str = Field(default="1.0.0", description="Semver version string")
    tier: str | None = Field(default=None, description='"bundled" or "runtime"')
    runtime: SkillRuntimeConfig | None = None
    hooks: SkillHooks | None = None
    tools: list[SkillTool] = Field(default_factory=list)
    tick_interval: int | None = Field(
        default=None,
        description="Periodic tick interval in milliseconds (minimum 1000)",
    )
    has_setup: bool = Field(
        default=False,
        description="Whether this skill has an interactive setup flow",
    )
    entity_schema: EntitySchema | None = Field(
        default=None,
        description="Declares entity and relationship types this skill surfaces",
    )
