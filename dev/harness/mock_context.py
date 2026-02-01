"""
Mock SkillContext for testing skills outside the AlphaHuman runtime.

Usage:
    from dev.harness.mock_context import create_mock_context

    ctx, inspect = create_mock_context()
    await skill.hooks.on_load(ctx)
    print(inspect.get_logs())
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from dev.types.skill_types import Entity, Relationship, SkillTool


# ---------------------------------------------------------------------------
# Options
# ---------------------------------------------------------------------------


@dataclass
class MockContextOptions:
  """Options for creating a mock context."""

  initial_data: dict[str, str] = field(default_factory=dict)
  initial_memory: dict[str, str] = field(default_factory=dict)
  initial_entities: list[Entity] = field(default_factory=list)
  initial_relationships: list[Relationship] = field(default_factory=list)
  initial_state: dict[str, Any] = field(default_factory=dict)
  session_id: str = "test-session-001"
  data_dir: str = "/mock/data"


# ---------------------------------------------------------------------------
# Inspector — lets tests peek into mock state
# ---------------------------------------------------------------------------


class MockInspector:
  """Inspect the internal state of a mock context."""

  def __init__(
    self,
    logs: list[str],
    data_store: dict[str, str],
    memory_store: dict[str, str],
    state: list[dict[str, Any]],
    registered_tools: dict[str, SkillTool],
    emitted_events: list[dict[str, Any]],
    session_values: dict[str, Any],
    relationship_store: list[Relationship] | None = None,
  ) -> None:
    self._logs = logs
    self._data_store = data_store
    self._memory_store = memory_store
    self._state = state
    self._registered_tools = registered_tools
    self._emitted_events = emitted_events
    self._session_values = session_values
    self._relationship_store = relationship_store if relationship_store is not None else []

  def get_logs(self) -> list[str]:
    return list(self._logs)

  def get_data(self) -> dict[str, str]:
    return dict(self._data_store)

  def get_memory(self) -> dict[str, str]:
    return dict(self._memory_store)

  def get_state(self) -> dict[str, Any]:
    return dict(self._state[0])

  def get_registered_tools(self) -> list[str]:
    return list(self._registered_tools.keys())

  def get_emitted_events(self) -> list[dict[str, Any]]:
    return list(self._emitted_events)

  def get_session_values(self) -> dict[str, Any]:
    return dict(self._session_values)

  def get_relationships(self) -> list[Relationship]:
    return list(self._relationship_store)


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def create_mock_context(
  options: MockContextOptions | None = None,
) -> tuple[Any, MockInspector]:
  """Create a mock SkillContext and an inspector for test assertions."""

  opts = options or MockContextOptions()

  # Internal stores
  data_store: dict[str, str] = dict(opts.initial_data)
  memory_store: dict[str, str] = dict(opts.initial_memory)
  entity_store: list[Entity] = list(opts.initial_entities)
  relationship_store: list[Relationship] = list(opts.initial_relationships)
  logs: list[str] = []
  registered_tools: dict[str, SkillTool] = {}
  emitted_events: list[dict[str, Any]] = []
  session_values: dict[str, Any] = {}
  # Wrap in list so nested class can mutate via reference
  state: list[dict[str, Any]] = [dict(opts.initial_state)]

  # --- Memory Manager ---
  class _Memory:
    async def read(self, name: str) -> str | None:
      return memory_store.get(name)

    async def write(self, name: str, content: str) -> None:
      memory_store[name] = content

    async def search(self, query: str) -> list[dict[str, str]]:
      results: list[dict[str, str]] = []
      q = query.lower()
      for name, content in memory_store.items():
        idx = content.lower().find(q)
        if idx != -1:
          start = max(0, idx - 40)
          end = min(len(content), idx + len(query) + 40)
          results.append({"name": name, "excerpt": content[start:end]})
      return results

    async def list(self) -> list[str]:
      return list(memory_store.keys())

    async def delete(self, name: str) -> None:
      memory_store.pop(name, None)

  # --- Session Manager ---
  class _Session:
    @property
    def id(self) -> str:
      return opts.session_id

    def get(self, key: str) -> Any:
      return session_values.get(key)

    def set(self, key: str, value: Any) -> None:
      session_values[key] = value

  # --- Tool Registry ---
  class _Tools:
    def register(self, tool: SkillTool) -> None:
      registered_tools[tool.definition.name] = tool

    def unregister(self, name: str) -> None:
      registered_tools.pop(name, None)

    def list(self) -> list[str]:
      return list(registered_tools.keys())

  # --- Entity Manager ---
  class _Entities:
    async def get_by_tag(self, tag: str, type: str | None = None) -> list[Entity]:
      return [e for e in entity_store if tag in e.tags and (type is None or e.type == type)]

    async def get_by_id(self, id: str) -> Entity | None:
      for e in entity_store:
        if e.id == id:
          return e
      return None

    async def search(self, query: str) -> list[Entity]:
      q = query.lower()
      return [e for e in entity_store if q in e.name.lower() or q in str(e.metadata).lower()]

    async def get_relationships(
      self, entity_id: str, type: str | None = None, direction: str = "outgoing"
    ) -> list[Relationship]:
      results: list[Relationship] = []
      for r in relationship_store:
        if type is not None and r.type != type:
          continue
        if direction == "outgoing" and r.source_id == entity_id:
          results.append(r)
        elif direction == "incoming" and r.target_id == entity_id:
          results.append(r)
        elif direction == "both" and (r.source_id == entity_id or r.target_id == entity_id):
          results.append(r)
      return results

  # --- Context ---
  class _Context:
    memory = _Memory()
    session = _Session()
    tools = _Tools()
    entities = _Entities()
    data_dir = opts.data_dir

    async def read_data(self, filename: str) -> str:
      content = data_store.get(filename)
      if content is None:
        raise FileNotFoundError(f"No such file: '{filename}'")
      return content

    async def write_data(self, filename: str, content: str) -> None:
      data_store[filename] = content

    def log(self, message: str) -> None:
      logs.append(message)

    def get_state(self) -> Any:
      return state[0]

    def set_state(self, partial: dict[str, Any]) -> None:
      state[0] = {**state[0], **partial}

    def emit_event(self, event_name: str, data: Any) -> None:
      emitted_events.append({"name": event_name, "data": data})

  ctx = _Context()

  inspector = MockInspector(
    logs=logs,
    data_store=data_store,
    memory_store=memory_store,
    state=state,
    registered_tools=registered_tools,
    emitted_events=emitted_events,
    session_values=session_values,
    relationship_store=relationship_store,
  )

  return ctx, inspector
