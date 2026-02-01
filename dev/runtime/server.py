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
from typing import Any

from dev.types.skill_types import SkillDefinition, SkillTool, SkillOptionDefinition
from dev.types.setup_types import SetupStep, SetupResult


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
      loop,  # type: ignore[arg-type]
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
      asyncio.create_task(self._handle_message(message))

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
          for t in self._tools.values()
        ]
      }

    if method == "tools/call":
      name = p.get("name", "")
      args = p.get("arguments", {})
      tool = self._tools.get(name)
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
        result = await self._hooks.on_before_message(self._create_context(), msg)
        return {"message": result if isinstance(result, str) else None}
      return {"message": None}

    if method == "skill/afterResponse":
      response = p.get("response", "")
      if self._hooks and self._hooks.on_after_response:
        result = await self._hooks.on_after_response(self._create_context(), response)
        return {"response": result if isinstance(result, str) else None}
      return {"response": None}

    if method == "skill/tick":
      if self._hooks and self._hooks.on_tick:
        await self._hooks.on_tick(self._create_context())
      return {"ok": True}

    if method == "skill/status":
      if not self._hooks or not self._hooks.on_status:
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
      result = await self._hooks.on_setup_submit(self._create_context(), step_id, values)
      payload: dict[str, Any] = {
        "status": result.status,
        "nextStep": self._serialize_step(result.next_step) if result.next_step else None,
        "errors": [{"field": e.field, "message": e.message} for e in result.errors]
        if result.errors
        else None,
        "message": result.message,
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
        asyncio.ensure_future(server.set_state(partial))

      def emit_event(self, event_name: str, data: Any) -> None:
        asyncio.ensure_future(server.emit_event(event_name, data))

      def get_options(self) -> dict[str, Any]:
        return dict(server._options)

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

  async def _reverse_rpc(self, method: str, params: Any = None) -> Any:
    msg_id = self._next_id
    self._next_id += 1
    request = {"jsonrpc": "2.0", "id": msg_id, "method": method}
    if params is not None:
      request["params"] = params

    future: asyncio.Future[Any] = asyncio.get_event_loop().create_future()
    self._pending[msg_id] = future

    self._write_message(request)

    try:
      return await asyncio.wait_for(future, timeout=30.0)
    except asyncio.TimeoutError:
      self._pending.pop(msg_id, None)
      raise RuntimeError(f"Reverse RPC timeout: {method}")
