"""
Python Runtime SDK — asyncio JSON-RPC 2.0 Server for Runtime Skills

Runtime skills use this as their entry point. The SDK handles:
- Reading JSON-RPC requests from stdin
- Dispatching to tool handlers and lifecycle hooks
- Writing JSON-RPC responses to stdout
- Reverse RPC to the host for state, data, entities, events

Usage:
    from dev.runtime.server import SkillServer
    from dev.types.skill_types import SkillDefinition

    server = SkillServer(skill_definition)
    server.start()
"""

from __future__ import annotations

import asyncio
import json
import sys
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
  from dev.types.setup_types import SetupResult, SetupStep
  from dev.types.skill_types import SkillDefinition, SkillOptionDefinition, SkillTool
  from dev.types.trigger_types import TriggerInstance, TriggerSchema


class SkillServer:
  """JSON-RPC 2.0 server that bridges a Python skill to the AlphaHuman host."""

  def __init__(self, skill: SkillDefinition) -> None:
    self._all_tools: dict[str, SkillTool] = {t.definition.name: t for t in skill.tools}
    self._tools: dict[str, SkillTool] = dict(self._all_tools)
    self._hooks = skill.hooks
    self._skill = skill
    self._option_defs: dict[str, SkillOptionDefinition] = {o.name: o for o in skill.options}
    self._options: dict[str, Any] = {o.name: o.default for o in skill.options}
    self._pending: dict[int | str, asyncio.Future[Any]] = {}
    self._next_id = 1
    self._manifest: dict[str, str] | None = None
    self._data_dir = ""
    self._writer: asyncio.StreamWriter | None = None
    # Trigger system
    self._triggers: dict[str, TriggerInstance] = {}
    self._trigger_schema: TriggerSchema | None = skill.trigger_schema
    self._trigger_tools: dict[str, SkillTool] = {}
    if self._trigger_schema:
      self._trigger_tools = self._build_trigger_tools()

  # --------------------------------------------------------------------- #
  # Public API
  # --------------------------------------------------------------------- #

  def start(self) -> None:
    """Start the server (blocking). Reads stdin, dispatches, writes stdout."""
    asyncio.run(self._run())

  # --------------------------------------------------------------------- #
  # Reverse RPC — call host
  # --------------------------------------------------------------------- #

  async def get_state(self) -> Any:
    result = await self._reverse_rpc("state/get")
    return result.get("state") if isinstance(result, dict) else result

  async def set_state(self, partial: dict[str, Any]) -> None:
    await self._reverse_rpc("state/set", {"partial": partial})

  async def read_data(self, filename: str) -> str:
    result = await self._reverse_rpc("data/read", {"filename": filename})
    return result["content"] if isinstance(result, dict) else str(result)

  async def write_data(self, filename: str, content: str) -> None:
    await self._reverse_rpc("data/write", {"filename": filename, "content": content})

  async def emit_event(self, event_type: str, data: Any) -> None:
    await self._reverse_rpc("intelligence/emitEvent", {"eventType": event_type, "data": data})

  async def upsert_entity(
    self,
    *,
    type: str,
    source: str,
    id: str | None = None,
    source_id: str | None = None,
    title: str | None = None,
    summary: str | None = None,
    metadata: dict[str, Any] | None = None,
  ) -> None:
    params: dict[str, Any] = {"type": type, "source": source}
    if id is not None:
      params["id"] = id
    if source_id is not None:
      params["sourceId"] = source_id
    if title is not None:
      params["title"] = title
    if summary is not None:
      params["summary"] = summary
    if metadata is not None:
      params["metadata"] = metadata
    await self._reverse_rpc("entities/upsert", params)

  async def search_entities(
    self,
    query: str,
    types: list[str] | None = None,
    limit: int | None = None,
  ) -> list[Any]:
    params: dict[str, Any] = {"query": query}
    if types is not None:
      params["types"] = types
    if limit is not None:
      params["limit"] = limit
    result = await self._reverse_rpc("entities/search", params)
    return result.get("results", []) if isinstance(result, dict) else []

  async def upsert_relationship(
    self,
    *,
    source_id: str,
    target_id: str,
    type: str,
    source: str,
    metadata: dict[str, Any] | None = None,
  ) -> None:
    params: dict[str, Any] = {
      "sourceId": source_id,
      "targetId": target_id,
      "type": type,
      "source": source,
    }
    if metadata is not None:
      params["metadata"] = metadata
    await self._reverse_rpc("entities/upsertRelationship", params)

  async def get_relationships(
    self,
    entity_id: str,
    relationship_type: str | None = None,
    direction: str = "outgoing",
  ) -> list[Any]:
    params: dict[str, Any] = {"entityId": entity_id, "direction": direction}
    if relationship_type is not None:
      params["type"] = relationship_type
    result = await self._reverse_rpc("entities/getRelationships", params)
    return result.get("results", []) if isinstance(result, dict) else []

  def log(self, message: str) -> None:
    sys.stderr.write(f"[skill] {message}\n")
    sys.stderr.flush()

  # --------------------------------------------------------------------- #
  # Internal — main loop
  # --------------------------------------------------------------------- #

  async def _run(self) -> None:
    loop = asyncio.get_event_loop()
    reader = asyncio.StreamReader()
    protocol = asyncio.StreamReaderProtocol(reader)
    await loop.connect_read_pipe(lambda: protocol, sys.stdin)

    transport, _ = await loop.connect_write_pipe(asyncio.BaseProtocol, sys.stdout)
    self._writer = asyncio.StreamWriter(
      transport,
      protocol,
      reader,
      loop,
    )

    while True:
      line = await reader.readline()
      if not line:
        break
      trimmed = line.decode().strip()
      if not trimmed:
        continue
      try:
        message = json.loads(trimmed)
      except json.JSONDecodeError:
        self.log(f"Failed to parse JSON-RPC message: {trimmed}")
        continue

      # Responses to our reverse RPC must be handled inline so the
      # read loop keeps consuming stdin while handlers await futures.
      if "result" in message or "error" in message:
        msg_id = message.get("id")
        future = self._pending.pop(msg_id, None)
        if future and not future.done():
          if "error" in message:
            future.set_exception(RuntimeError(message["error"].get("message", "Reverse RPC error")))
          else:
            future.set_result(message.get("result"))
        continue

      # Host requests are dispatched as concurrent tasks so the read
      # loop can keep processing reverse-RPC replies.
      _ = asyncio.create_task(self._handle_message(message))  # noqa: RUF006

  # --------------------------------------------------------------------- #
  # Internal — message dispatch
  # --------------------------------------------------------------------- #

  async def _handle_message(self, message: dict[str, Any]) -> None:
    # Reverse RPC responses are handled inline in _run(); this method
    # only receives host requests and notifications.
    method = message.get("method", "")
    params = message.get("params")
    msg_id = message.get("id")

    try:
      result = await self._dispatch(method, params)
      if msg_id is not None:
        self._send_response(msg_id, result)
    except Exception as exc:
      if msg_id is not None:
        self._send_error(msg_id, -32603, str(exc))
      else:
        self.log(f"Notification handler error: {exc}")

  async def _dispatch(self, method: str, params: Any) -> Any:
    p = params if isinstance(params, dict) else {}

    # -- Tool methods --
    if method == "tools/list":
      all_visible = list(self._tools.values()) + list(self._trigger_tools.values())
      return {
        "tools": [
          {
            "name": t.definition.name,
            "description": t.definition.description,
            "inputSchema": {
              "type": "object",
              "properties": t.definition.parameters.get("properties", {}),
              "required": t.definition.parameters.get("required"),
            },
          }
          for t in all_visible
        ]
      }

    if method == "tools/call":
      name = p.get("name", "")
      args = p.get("arguments", {})
      tool = self._tools.get(name) or self._trigger_tools.get(name)
      if not tool:
        raise ValueError(f"Unknown tool: {name}")
      result = await tool.execute(args)
      return {
        "content": [{"type": "text", "text": result.content}],
        "isError": result.is_error,
      }

    # -- Lifecycle methods --
    if method == "skill/load":
      if p.get("manifest"):
        self._manifest = p["manifest"]
      if p.get("dataDir"):
        self._data_dir = p["dataDir"]
      # Load persisted options and apply tool filter
      await self._load_options()
      await self._load_triggers()
      if self._hooks and self._hooks.on_load:
        await self._hooks.on_load(self._create_context())
      return {"ok": True}

    if method == "skill/unload":
      if self._hooks and self._hooks.on_unload:
        await self._hooks.on_unload(self._create_context())
      return {"ok": True}

    if method == "skill/activate":
      return {"ok": True}

    if method == "skill/deactivate":
      return {"ok": True}

    if method == "skill/sessionStart":
      session_id = p.get("sessionId", "")
      if self._hooks and self._hooks.on_session_start:
        await self._hooks.on_session_start(self._create_context(), session_id)
      return {"ok": True}

    if method == "skill/sessionEnd":
      session_id = p.get("sessionId", "")
      if self._hooks and self._hooks.on_session_end:
        await self._hooks.on_session_end(self._create_context(), session_id)
      return {"ok": True}

    if method == "skill/beforeMessage":
      msg = p.get("message", "")
      if self._hooks and self._hooks.on_before_message:
        transformed_msg: str | None = await self._hooks.on_before_message(
          self._create_context(), msg
        )
        return {"message": transformed_msg}
      return {"message": None}

    if method == "skill/afterResponse":
      response = p.get("response", "")
      if self._hooks and self._hooks.on_after_response:
        transformed_response: str | None = await self._hooks.on_after_response(
          self._create_context(), response
        )
        return {"response": transformed_response}
      return {"response": None}

    if method == "skill/tick":
      if self._hooks and self._hooks.on_tick:
        await self._hooks.on_tick(self._create_context())
      return {"ok": True}

    if method == "skill/status":
      if not self._hooks or not self._hooks.on_status:  # type: ignore[truthy-function]
        raise ValueError("Skill must implement on_status hook")
      status = await self._hooks.on_status(self._create_context())
      return {"status": status}

    if method == "skill/shutdown":
      # Schedule exit after responding
      asyncio.get_event_loop().call_later(0.1, lambda: sys.exit(0))
      return {"ok": True}

    # -- Setup methods --
    if method == "setup/start":
      if not self._hooks or not self._hooks.on_setup_start:
        raise ValueError("Skill does not implement setup flow")
      step = await self._hooks.on_setup_start(self._create_context())
      return {"step": self._serialize_step(step)}

    if method == "setup/submit":
      if not self._hooks or not self._hooks.on_setup_submit:
        raise ValueError("Skill does not implement setup flow")
      step_id = p.get("stepId", "")
      values = p.get("values", {})

      setup_result: SetupResult = await self._hooks.on_setup_submit(
        self._create_context(), step_id, values
      )
      payload: dict[str, Any] = {
        "status": setup_result.status,
        "nextStep": self._serialize_step(setup_result.next_step)
        if setup_result.next_step
        else None,
        "errors": [{"field": e.field, "message": e.message} for e in setup_result.errors]
        if setup_result.errors
        else None,
        "message": setup_result.message,
      }
      return payload

    if method == "setup/cancel":
      if self._hooks and self._hooks.on_setup_cancel:
        await self._hooks.on_setup_cancel(self._create_context())
      return {"ok": True}

    # -- Options methods --
    if method == "options/list":
      return {
        "options": [
          {
            "name": od.name,
            "type": od.type,
            "label": od.label,
            "description": od.description,
            "default": od.default,
            "options": (
              [{"label": o.label, "value": o.value} for o in od.options] if od.options else None
            ),
            "group": od.group,
            "toolFilter": od.tool_filter,
            "value": self._options.get(od.name, od.default),
          }
          for od in self._option_defs.values()
        ]
      }

    if method == "options/get":
      return {"options": dict(self._options)}

    if method == "options/set":
      name = p.get("name", "")
      value = p.get("value")
      od = self._option_defs.get(name)
      if not od:
        raise ValueError(f"Unknown option: {name}")
      # Basic type validation
      if od.type == "boolean" and not isinstance(value, bool):
        raise ValueError(f"Option '{name}' requires a boolean value")
      if od.type == "number" and not isinstance(value, (int, float)):
        raise ValueError(f"Option '{name}' requires a numeric value")
      if od.type == "text" and not isinstance(value, str):
        raise ValueError(f"Option '{name}' requires a string value")
      if od.type == "select":
        valid_values = [o.value for o in (od.options or [])]
        if str(value) not in valid_values:
          raise ValueError(f"Option '{name}' must be one of: {valid_values}")
      self._options[name] = value
      self._apply_tool_filter()
      await self._persist_options()
      if self._hooks and self._hooks.on_options_change:
        await self._hooks.on_options_change(self._create_context(), dict(self._options))
      return {"ok": True}

    if method == "options/reset":
      self._options = {o.name: o.default for o in self._option_defs.values()}
      self._apply_tool_filter()
      await self._persist_options()
      if self._hooks and self._hooks.on_options_change:
        await self._hooks.on_options_change(self._create_context(), dict(self._options))
      return {"ok": True}

    # -- Disconnect method --
    if method == "skill/disconnect":
      if not self._skill.has_disconnect:
        raise ValueError("Skill does not support disconnect")
      if not self._hooks or not self._hooks.on_disconnect:
        raise ValueError("Skill has no on_disconnect hook")
      await self._hooks.on_disconnect(self._create_context())
      return {"ok": True}

    # -- Trigger methods --
    if method == "triggers/types":
      return self._list_trigger_types()

    if method == "triggers/list":
      return self._list_triggers()

    if method == "triggers/get":
      return self._get_trigger(p.get("id", ""))

    if method == "triggers/create":
      return await self._create_trigger(p)

    if method == "triggers/update":
      return await self._update_trigger(p)

    if method == "triggers/delete":
      return await self._delete_trigger(p)

    raise ValueError(f"Unknown method: {method}")

  # --------------------------------------------------------------------- #
  # Internal — setup serialization
  # --------------------------------------------------------------------- #

  @staticmethod
  def _serialize_step(step: SetupStep) -> dict[str, Any]:
    """Serialize a SetupStep to a JSON-compatible dict."""
    return {
      "id": step.id,
      "title": step.title,
      "description": step.description,
      "fields": [
        {
          "name": f.name,
          "type": f.type,
          "label": f.label,
          "description": f.description,
          "required": f.required,
          "default": f.default,
          "placeholder": f.placeholder,
          "options": (
            [{"label": o.label, "value": o.value} for o in f.options] if f.options else None
          ),
        }
        for f in step.fields
      ],
    }

  # --------------------------------------------------------------------- #
  # Internal — options persistence & tool filtering
  # --------------------------------------------------------------------- #

  def _apply_tool_filter(self) -> None:
    """Rebuild self._tools based on current option values and tool_filter lists."""
    excluded: set[str] = set()
    for od in self._option_defs.values():
      if od.type == "boolean" and od.tool_filter:
        if not self._options.get(od.name, od.default):
          excluded.update(od.tool_filter)
    self._tools = {name: tool for name, tool in self._all_tools.items() if name not in excluded}

  async def _persist_options(self) -> None:
    """Persist current option values to options.json via reverse RPC."""
    try:
      await self.write_data("options.json", json.dumps(self._options))
    except Exception:
      self.log("Failed to persist options")

  async def _load_options(self) -> None:
    """Load persisted option values from options.json, merge with defaults."""
    if not self._option_defs:
      return
    try:
      raw = await self.read_data("options.json")
      persisted = json.loads(raw) if raw else {}
    except Exception:
      persisted = {}
    # Merge: persisted values win over defaults, but only for known options
    for name, od in self._option_defs.items():
      if name in persisted:
        self._options[name] = persisted[name]
      else:
        self._options[name] = od.default
    self._apply_tool_filter()

  # --------------------------------------------------------------------- #
  # Internal — trigger management
  # --------------------------------------------------------------------- #

  def _build_trigger_tools(self) -> dict[str, SkillTool]:
    """Build auto-generated tools for trigger CRUD operations."""
    from dev.types.skill_types import SkillTool, ToolDefinition, ToolResult

    server = self
    tools: dict[str, SkillTool] = {}

    async def _list_types(args: dict[str, Any]) -> ToolResult:
      result = server._list_trigger_types()
      return ToolResult(content=json.dumps(result, indent=2))

    tools["list-trigger-types"] = SkillTool(
      definition=ToolDefinition(
        name="list-trigger-types",
        description="List available trigger types and their condition field schemas",
        parameters={"type": "object", "properties": {}},
      ),
      execute=_list_types,
    )

    async def _list(args: dict[str, Any]) -> ToolResult:
      result = server._list_triggers()
      return ToolResult(content=json.dumps(result, indent=2))

    tools["list-triggers"] = SkillTool(
      definition=ToolDefinition(
        name="list-triggers",
        description="List all registered triggers",
        parameters={"type": "object", "properties": {}},
      ),
      execute=_list,
    )

    async def _create(args: dict[str, Any]) -> ToolResult:
      try:
        result = await server._create_trigger(args)
        return ToolResult(content=json.dumps(result, indent=2))
      except ValueError as exc:
        return ToolResult(content=str(exc), is_error=True)

    tools["create-trigger"] = SkillTool(
      definition=ToolDefinition(
        name="create-trigger",
        description="Create a new trigger with conditions and config",
        parameters={
          "type": "object",
          "properties": {
            "type": {"type": "string", "description": "Trigger type (must match a declared type)"},
            "name": {"type": "string", "description": "Human-readable trigger name"},
            "description": {"type": "string", "description": "Trigger description"},
            "conditions": {
              "type": "array",
              "description": "Condition objects (at least one required)",
              "items": {"type": "object"},
            },
            "config": {"type": "object", "description": "Trigger-type-specific config"},
            "enabled": {"type": "boolean", "description": "Whether trigger is enabled (default true)"},
            "metadata": {"type": "object", "description": "Optional metadata"},
          },
          "required": ["type", "name", "conditions"],
        },
      ),
      execute=_create,
    )

    async def _update(args: dict[str, Any]) -> ToolResult:
      try:
        result = await server._update_trigger(args)
        return ToolResult(content=json.dumps(result, indent=2))
      except ValueError as exc:
        return ToolResult(content=str(exc), is_error=True)

    tools["update-trigger"] = SkillTool(
      definition=ToolDefinition(
        name="update-trigger",
        description="Update an existing trigger's fields",
        parameters={
          "type": "object",
          "properties": {
            "id": {"type": "string", "description": "Trigger ID to update"},
            "name": {"type": "string", "description": "New name"},
            "description": {"type": "string", "description": "New description"},
            "conditions": {"type": "array", "items": {"type": "object"}},
            "config": {"type": "object"},
            "enabled": {"type": "boolean"},
            "metadata": {"type": "object"},
          },
          "required": ["id"],
        },
      ),
      execute=_update,
    )

    async def _delete(args: dict[str, Any]) -> ToolResult:
      try:
        result = await server._delete_trigger(args)
        return ToolResult(content=json.dumps(result, indent=2))
      except ValueError as exc:
        return ToolResult(content=str(exc), is_error=True)

    tools["delete-trigger"] = SkillTool(
      definition=ToolDefinition(
        name="delete-trigger",
        description="Delete a trigger by ID",
        parameters={
          "type": "object",
          "properties": {
            "id": {"type": "string", "description": "Trigger ID to delete"},
          },
          "required": ["id"],
        },
      ),
      execute=_delete,
    )

    async def _get(args: dict[str, Any]) -> ToolResult:
      try:
        result = server._get_trigger(args.get("id", ""))
        return ToolResult(content=json.dumps(result, indent=2))
      except ValueError as exc:
        return ToolResult(content=str(exc), is_error=True)

    tools["get-trigger"] = SkillTool(
      definition=ToolDefinition(
        name="get-trigger",
        description="Get details of a specific trigger",
        parameters={
          "type": "object",
          "properties": {
            "id": {"type": "string", "description": "Trigger ID"},
          },
          "required": ["id"],
        },
      ),
      execute=_get,
    )

    return tools

  def _list_trigger_types(self) -> dict[str, Any]:
    if not self._trigger_schema:
      return {"triggerTypes": []}
    return {
      "triggerTypes": [
        {
          "type": tt.type,
          "label": tt.label,
          "description": tt.description,
          "conditionFields": [
            {"name": f.name, "type": f.type, "description": f.description}
            for f in tt.condition_fields
          ],
          "configSchema": tt.config_schema,
        }
        for tt in self._trigger_schema.trigger_types
      ]
    }

  def _list_triggers(self) -> dict[str, Any]:
    return {"triggers": [self._serialize_trigger(t) for t in self._triggers.values()]}

  def _get_trigger(self, trigger_id: str) -> dict[str, Any]:
    trigger = self._triggers.get(trigger_id)
    if not trigger:
      raise ValueError(f"Unknown trigger: {trigger_id}")
    return {"trigger": self._serialize_trigger(trigger)}

  async def _create_trigger(self, params: dict[str, Any]) -> dict[str, Any]:
    import datetime
    import uuid

    from dev.types.trigger_types import TriggerCondition, TriggerInstance

    trigger_type = params.get("type", "")
    name = params.get("name", "")
    conditions_raw = params.get("conditions", [])

    if not trigger_type:
      raise ValueError("Trigger type is required")
    if not name:
      raise ValueError("Trigger name is required")
    if not conditions_raw:
      raise ValueError("At least one condition is required")

    # Validate trigger type exists
    if self._trigger_schema:
      valid_types = {tt.type for tt in self._trigger_schema.trigger_types}
      if trigger_type not in valid_types:
        raise ValueError(f"Unknown trigger type: {trigger_type}. Valid: {sorted(valid_types)}")

    # Parse and validate conditions
    conditions = self._validate_conditions(conditions_raw, trigger_type)

    trigger = TriggerInstance(
      id=str(uuid.uuid4()),
      type=trigger_type,
      name=name,
      description=params.get("description", ""),
      conditions=conditions,
      config=params.get("config", {}),
      enabled=params.get("enabled", True),
      created_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
      metadata=params.get("metadata", {}),
    )

    self._triggers[trigger.id] = trigger
    await self._persist_triggers()

    # Call hook
    if self._hooks and self._hooks.on_trigger_register:
      await self._hooks.on_trigger_register(self._create_context(), trigger)

    return {"trigger": self._serialize_trigger(trigger)}

  async def _update_trigger(self, params: dict[str, Any]) -> dict[str, Any]:
    from dev.types.trigger_types import TriggerInstance

    trigger_id = params.get("id", "")
    existing = self._triggers.get(trigger_id)
    if not existing:
      raise ValueError(f"Unknown trigger: {trigger_id}")

    updates: dict[str, Any] = {}
    if "name" in params:
      updates["name"] = params["name"]
    if "description" in params:
      updates["description"] = params["description"]
    if "config" in params:
      updates["config"] = params["config"]
    if "enabled" in params:
      updates["enabled"] = params["enabled"]
    if "metadata" in params:
      updates["metadata"] = params["metadata"]
    if "conditions" in params:
      updates["conditions"] = self._validate_conditions(params["conditions"], existing.type)

    updated = TriggerInstance(
      id=existing.id,
      type=existing.type,
      name=updates.get("name", existing.name),
      description=updates.get("description", existing.description),
      conditions=updates.get("conditions", existing.conditions),
      config=updates.get("config", existing.config),
      enabled=updates.get("enabled", existing.enabled),
      created_at=existing.created_at,
      metadata=updates.get("metadata", existing.metadata),
    )
    self._triggers[trigger_id] = updated
    await self._persist_triggers()
    return {"trigger": self._serialize_trigger(updated)}

  async def _delete_trigger(self, params: dict[str, Any]) -> dict[str, Any]:
    trigger_id = params.get("id", "")
    if trigger_id not in self._triggers:
      raise ValueError(f"Unknown trigger: {trigger_id}")
    del self._triggers[trigger_id]
    await self._persist_triggers()

    # Call hook
    if self._hooks and self._hooks.on_trigger_remove:
      await self._hooks.on_trigger_remove(self._create_context(), trigger_id)

    return {"ok": True}

  def _validate_conditions(
    self, conditions_raw: list[Any], trigger_type: str
  ) -> list[Any]:
    """Parse and validate condition dicts into TriggerCondition objects."""
    from dev.types.trigger_types import TriggerCondition

    # Get valid field names for this trigger type
    valid_fields: set[str] | None = None
    if self._trigger_schema:
      for tt in self._trigger_schema.trigger_types:
        if tt.type == trigger_type:
          valid_fields = {f.name for f in tt.condition_fields}
          break

    conditions: list[TriggerCondition] = []
    for raw in conditions_raw:
      cond = TriggerCondition.model_validate(raw) if isinstance(raw, dict) else raw
      self._check_condition_depth(cond, 0)
      if valid_fields is not None:
        self._check_condition_fields(cond, valid_fields)
      conditions.append(cond)

    # Validate regex patterns at creation time
    import re

    for cond in conditions:
      self._validate_regex_in_condition(cond, re)

    return conditions

  def _check_condition_depth(self, cond: Any, depth: int) -> None:
    if depth > 5:
      raise ValueError("Condition nesting depth exceeds maximum of 5")
    if cond.conditions:
      for sub in cond.conditions:
        self._check_condition_depth(sub, depth + 1)

  def _check_condition_fields(self, cond: Any, valid_fields: set[str]) -> None:
    if cond.field and cond.type in ("regex", "keyword", "threshold"):
      if cond.field not in valid_fields:
        self.log(f"Warning: condition field '{cond.field}' not in declared fields")
    if cond.conditions:
      for sub in cond.conditions:
        self._check_condition_fields(sub, valid_fields)

  def _validate_regex_in_condition(self, cond: Any, re_module: Any) -> None:
    if cond.type == "regex" and cond.pattern:
      try:
        re_module.compile(cond.pattern)
      except re_module.error as exc:
        raise ValueError(f"Invalid regex pattern '{cond.pattern}': {exc}")
    if cond.conditions:
      for sub in cond.conditions:
        self._validate_regex_in_condition(sub, re_module)

  @staticmethod
  def _serialize_trigger(trigger: TriggerInstance) -> dict[str, Any]:
    return {
      "id": trigger.id,
      "type": trigger.type,
      "name": trigger.name,
      "description": trigger.description,
      "conditions": [c.model_dump(exclude_none=True) for c in trigger.conditions],
      "config": trigger.config,
      "enabled": trigger.enabled,
      "createdAt": trigger.created_at,
      "metadata": trigger.metadata,
    }

  async def _persist_triggers(self) -> None:
    """Persist current triggers to triggers.json via reverse RPC."""
    try:
      data = [
        {
          "id": t.id,
          "type": t.type,
          "name": t.name,
          "description": t.description,
          "conditions": [c.model_dump(exclude_none=True) for c in t.conditions],
          "config": t.config,
          "enabled": t.enabled,
          "created_at": t.created_at,
          "metadata": t.metadata,
        }
        for t in self._triggers.values()
      ]
      await self.write_data("triggers.json", json.dumps(data))
    except Exception:
      self.log("Failed to persist triggers")

  async def _load_triggers(self) -> None:
    """Load persisted triggers from triggers.json."""
    if not self._trigger_schema:
      return
    try:
      raw = await self.read_data("triggers.json")
      triggers_data = json.loads(raw) if raw else []
    except Exception:
      triggers_data = []

    if not isinstance(triggers_data, list):
      return

    from dev.types.trigger_types import TriggerCondition, TriggerInstance

    valid_types = {tt.type for tt in self._trigger_schema.trigger_types}

    for item in triggers_data:
      if not isinstance(item, dict):
        continue
      trigger_type = item.get("type", "")
      if trigger_type not in valid_types:
        self.log(f"Warning: persisted trigger type '{trigger_type}' no longer declared, loading anyway")

      conditions = [
        TriggerCondition.model_validate(c)
        for c in item.get("conditions", [])
        if isinstance(c, dict)
      ]
      trigger = TriggerInstance(
        id=item.get("id", ""),
        type=trigger_type,
        name=item.get("name", ""),
        description=item.get("description", ""),
        conditions=conditions,
        config=item.get("config", {}),
        enabled=item.get("enabled", True),
        created_at=item.get("created_at", ""),
        metadata=item.get("metadata", {}),
      )
      self._triggers[trigger.id] = trigger

      # Call on_trigger_register for each loaded trigger
      if self._hooks and self._hooks.on_trigger_register:
        try:
          await self._hooks.on_trigger_register(self._create_context(), trigger)
        except Exception:
          self.log(f"Warning: on_trigger_register failed for trigger {trigger.id}")

  # --------------------------------------------------------------------- #
  # Internal — context factory
  # --------------------------------------------------------------------- #

  def _create_context(self) -> Any:
    """Build a SkillContext-compatible object wired to reverse RPC."""
    server = self

    class _Memory:
      async def read(self, name: str) -> str | None:
        try:
          return await server.read_data(name)
        except Exception:
          return None

      async def write(self, name: str, content: str) -> None:
        await server.write_data(name, content)

      async def search(self, query: str) -> list[dict[str, str]]:
        return []

      async def list(self) -> list[str]:
        return []

      async def delete(self, name: str) -> None:
        pass

    class _Session:
      @property
      def id(self) -> str:
        return "runtime"

      def get(self, key: str) -> Any:
        return None

      def set(self, key: str, value: Any) -> None:
        pass

    class _Tools:
      def register(self, tool: Any) -> None:
        pass

      def unregister(self, name: str) -> None:
        pass

      def list(self) -> list[str]:
        return list(server._tools.keys())

    class _Entities:
      async def get_by_tag(self, tag: str, type: str | None = None) -> list:
        return []

      async def get_by_id(self, id: str) -> None:
        return None

      async def search(self, query: str) -> list:
        return await server.search_entities(query)

      async def get_relationships(
        self, entity_id: str, type: str | None = None, direction: str = "outgoing"
      ) -> list:
        return await server.get_relationships(entity_id, type, direction)

    class _Context:
      memory = _Memory()
      session = _Session()
      tools = _Tools()
      entities = _Entities()

      # Expose server-level callbacks for skills that need direct access
      _upsert_entity = staticmethod(server.upsert_entity)
      _upsert_relationship = staticmethod(server.upsert_relationship)
      _request_summarization = staticmethod(server.request_summarization)

      @property
      def data_dir(self) -> str:
        return server._data_dir or f"skills/{(server._manifest or {}).get('id', 'unknown')}/data"

      async def read_data(self, filename: str) -> str:
        return await server.read_data(filename)

      async def write_data(self, filename: str, content: str) -> None:
        await server.write_data(filename, content)

      def log(self, message: str) -> None:
        server.log(message)

      def get_state(self) -> Any:
        # Synchronous wrapper — caller should use await get_state() from server
        # For hook context, we return a coroutine the caller can await
        return server.get_state()

      def set_state(self, partial: dict[str, Any]) -> None:
        # Fire-and-forget
        _ = asyncio.ensure_future(server.set_state(partial))  # noqa: RUF006

      def emit_event(self, event_name: str, data: Any) -> None:
        _ = asyncio.ensure_future(server.emit_event(event_name, data))  # noqa: RUF006

      def get_options(self) -> dict[str, Any]:
        return dict(server._options)

      def fire_trigger(
        self,
        trigger_id: str,
        matched_data: dict[str, Any],
        context: dict[str, Any] | None = None,
      ) -> None:
        _ = asyncio.ensure_future(  # noqa: RUF006
          server.fire_trigger(trigger_id, matched_data, context)
        )

      def get_triggers(self) -> list[Any]:
        return list(server._triggers.values())

      # Expose async fire_trigger for skills that want to await the result
      _fire_trigger = staticmethod(server.fire_trigger)

    return _Context()

  # --------------------------------------------------------------------- #
  # Internal — JSON-RPC I/O
  # --------------------------------------------------------------------- #

  def _send_response(self, msg_id: int | str, result: Any) -> None:
    response = {"jsonrpc": "2.0", "id": msg_id, "result": result}
    self._write_message(response)

  def _send_error(self, msg_id: int | str, code: int, message: str) -> None:
    response = {
      "jsonrpc": "2.0",
      "id": msg_id,
      "error": {"code": code, "message": message},
    }
    self._write_message(response)

  def _write_message(self, message: dict[str, Any]) -> None:
    data = json.dumps(message) + "\n"
    if self._writer:
      self._writer.write(data.encode())
    else:
      sys.stdout.write(data)
      sys.stdout.flush()

  async def request_summarization(
    self,
    *,
    messages: list[dict[str, Any]],
    chats: list[dict[str, Any]],
    current_user: dict[str, Any] | None = None,
  ) -> dict[str, Any]:
    """Send messages to host for AI summarization. Returns summaries + graph suggestions."""
    result = await self._reverse_rpc(
      "intelligence/summarize",
      {
        "messages": messages,
        "chats": chats,
        "currentUser": current_user,
      },
      timeout=120.0,
    )
    return result if isinstance(result, dict) else {}

  async def fire_trigger(
    self,
    trigger_id: str,
    matched_data: dict[str, Any],
    context: dict[str, Any] | None = None,
  ) -> None:
    """Send triggers/fired reverse RPC to the host to start a new conversation."""
    import datetime

    trigger = self._triggers.get(trigger_id)
    if not trigger:
      self.log(f"fire_trigger: unknown trigger {trigger_id}")
      return
    await self._reverse_rpc(
      "triggers/fired",
      {
        "triggerId": trigger.id,
        "triggerName": trigger.name,
        "triggerType": trigger.type,
        "firedAt": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "matchedData": matched_data,
        "context": context or {},
      },
    )

  async def _reverse_rpc(self, method: str, params: Any = None, timeout: float = 30.0) -> Any:
    msg_id = self._next_id
    self._next_id += 1
    request = {"jsonrpc": "2.0", "id": msg_id, "method": method}
    if params is not None:
      request["params"] = params

    future: asyncio.Future[Any] = asyncio.get_event_loop().create_future()
    self._pending[msg_id] = future

    self._write_message(request)

    try:
      return await asyncio.wait_for(future, timeout=timeout)
    except TimeoutError:
      self._pending.pop(msg_id, None)
      raise RuntimeError(f"Reverse RPC timeout: {method}")
