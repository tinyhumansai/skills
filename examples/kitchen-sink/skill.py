"""
Kitchen Sink Skill — Comprehensive Example
============================================

This skill demonstrates every capability available in the AlphaHuman
skill system:

  1. Lifecycle hooks       — on_load, on_unload, on_session_start/end
  2. Message hooks         — on_before_message, on_after_response
  3. Memory flush hook     — on_memory_flush
  4. Periodic tick         — on_tick (runs every 60 seconds)
  5. AI tools              — multiple tools with JSON Schema parameters
  6. Interactive setup     — multi-step configuration wizard
  7. State management      — get_state / set_state for persistent state
  8. Data persistence      — read_data / write_data for file storage
  9. Memory system         — read / write / search / list / delete
 10. Session store         — session-scoped key-value storage
 11. Entity graph          — querying contacts, chats, wallets
 12. Event emission        — emitting events for intelligence rules
 13. Tool registry         — dynamic tool registration/unregistration

Usage:
    from dev.types.skill_types import SkillDefinition
    # This module exports `skill: SkillDefinition`
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from dev.types.skill_types import (
    SkillContext,
    SkillDefinition,
    SkillHooks,
    SkillTool,
    ToolDefinition,
    ToolResult,
)
from dev.types.setup_types import (
    SetupField,
    SetupFieldError,
    SetupFieldOption,
    SetupResult,
    SetupStep,
)


# ===========================================================================
# Tools
# ===========================================================================
# Each tool has a `definition` (schema the AI sees) and an async `execute`
# function. Tools are the primary way skills extend the AI's capabilities.


async def execute_add_note(args: dict) -> ToolResult:
    """Save a note to the skill's persistent data directory.

    Demonstrates: write_data, get_state, set_state, emit_event
    """
    ctx: SkillContext = args.pop("__context__")
    title = args.get("title", "Untitled")
    body = args.get("body", "")

    # Read existing notes index from persistent state
    state = ctx.get_state() or {}
    notes: list[dict] = state.get("notes_index", [])

    note_id = f"note_{len(notes) + 1}"
    note = {
        "id": note_id,
        "title": title,
        "body": body,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    # Persist the note content as a file in data_dir
    await ctx.write_data(f"{note_id}.json", json.dumps(note, indent=2))

    # Update the index in skill state
    notes.append({"id": note_id, "title": title})
    ctx.set_state({"notes_index": notes})

    # Emit an event so intelligence rules can react
    ctx.emit_event("note_created", {"note_id": note_id, "title": title})

    return ToolResult(content=f"Note '{title}' saved as {note_id}.")


async def execute_get_note(args: dict) -> ToolResult:
    """Retrieve a note by its ID.

    Demonstrates: read_data, error handling
    """
    ctx: SkillContext = args.pop("__context__")
    note_id = args.get("note_id", "")

    try:
        raw = await ctx.read_data(f"{note_id}.json")
        note = json.loads(raw)
        return ToolResult(
            content=f"**{note['title']}**\n\n{note['body']}\n\n_Created: {note['created_at']}_"
        )
    except Exception as e:
        return ToolResult(content=f"Note not found: {e}", is_error=True)


async def execute_list_notes(args: dict) -> ToolResult:
    """List all saved notes.

    Demonstrates: get_state
    """
    ctx: SkillContext = args.pop("__context__")
    state = ctx.get_state() or {}
    notes = state.get("notes_index", [])

    if not notes:
        return ToolResult(content="No notes saved yet.")

    lines = [f"- **{n['id']}**: {n['title']}" for n in notes]
    return ToolResult(content=f"Notes ({len(notes)}):\n" + "\n".join(lines))


async def execute_search_memory(args: dict) -> ToolResult:
    """Search the shared memory system.

    Demonstrates: memory.search
    """
    ctx: SkillContext = args.pop("__context__")
    query = args.get("query", "")

    results = await ctx.memory.search(query)

    if not results:
        return ToolResult(content=f"No memory results for '{query}'.")

    lines = []
    for r in results[:10]:
        name = r.get("name", "unknown")
        snippet = r.get("content", "")[:120]
        lines.append(f"- **{name}**: {snippet}")

    return ToolResult(content=f"Memory search results ({len(results)}):\n" + "\n".join(lines))


async def execute_save_memory(args: dict) -> ToolResult:
    """Write to the shared memory system.

    Demonstrates: memory.write
    """
    ctx: SkillContext = args.pop("__context__")
    name = args.get("name", "")
    content = args.get("content", "")

    await ctx.memory.write(name, content)
    return ToolResult(content=f"Memory '{name}' saved.")


async def execute_find_entities(args: dict) -> ToolResult:
    """Query the platform entity graph.

    Demonstrates: entities.search, entities.get_by_tag
    """
    ctx: SkillContext = args.pop("__context__")
    query = args.get("query", "")
    entity_type = args.get("type")

    if query.startswith("#"):
        # Tag-based search
        tag = query.lstrip("#")
        results = await ctx.entities.get_by_tag(tag, type=entity_type)
    else:
        # Free-text search
        results = await ctx.entities.search(query)

    if not results:
        return ToolResult(content="No entities found.")

    lines = []
    for e in results[:10]:
        tags = ", ".join(e.tags) if e.tags else "none"
        lines.append(f"- [{e.type}] **{e.name}** (id={e.id}, tags={tags})")

    return ToolResult(content=f"Entities ({len(results)}):\n" + "\n".join(lines))


async def execute_get_session_info(args: dict) -> ToolResult:
    """Return current session information.

    Demonstrates: session.id, session.get
    """
    ctx: SkillContext = args.pop("__context__")

    session_id = ctx.session.id
    message_count = ctx.session.get("message_count") or 0

    return ToolResult(content=f"Session ID: {session_id}\nMessages in session: {message_count}")


# ---------------------------------------------------------------------------
# Tool definitions (JSON Schema)
# ---------------------------------------------------------------------------

TOOLS: list[SkillTool] = [
    SkillTool(
        definition=ToolDefinition(
            name="add_note",
            description="Save a note with a title and body. Persists across sessions.",
            parameters={
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Short title for the note",
                    },
                    "body": {
                        "type": "string",
                        "description": "Full body text of the note",
                    },
                },
                "required": ["title", "body"],
            },
        ),
        execute=execute_add_note,
    ),
    SkillTool(
        definition=ToolDefinition(
            name="get_note",
            description="Retrieve a previously saved note by its ID.",
            parameters={
                "type": "object",
                "properties": {
                    "note_id": {
                        "type": "string",
                        "description": "Note ID (e.g. 'note_1')",
                    },
                },
                "required": ["note_id"],
            },
        ),
        execute=execute_get_note,
    ),
    SkillTool(
        definition=ToolDefinition(
            name="list_notes",
            description="List all saved notes with their IDs and titles.",
            parameters={"type": "object", "properties": {}},
        ),
        execute=execute_list_notes,
    ),
    SkillTool(
        definition=ToolDefinition(
            name="search_memory",
            description="Search the shared memory system for relevant context.",
            parameters={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query",
                    },
                },
                "required": ["query"],
            },
        ),
        execute=execute_search_memory,
    ),
    SkillTool(
        definition=ToolDefinition(
            name="save_memory",
            description="Save information to the shared memory system for future recall.",
            parameters={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Memory key/name",
                    },
                    "content": {
                        "type": "string",
                        "description": "Content to remember",
                    },
                },
                "required": ["name", "content"],
            },
        ),
        execute=execute_save_memory,
    ),
    SkillTool(
        definition=ToolDefinition(
            name="find_entities",
            description=(
                "Search the platform entity graph for contacts, chats, or wallets. "
                "Prefix query with '#' to search by tag."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query or '#tag'",
                    },
                    "type": {
                        "type": "string",
                        "description": "Filter by entity type (contact, chat, wallet)",
                        "enum": ["contact", "chat", "wallet"],
                    },
                },
                "required": ["query"],
            },
        ),
        execute=execute_find_entities,
    ),
    SkillTool(
        definition=ToolDefinition(
            name="get_session_info",
            description="Get information about the current session.",
            parameters={"type": "object", "properties": {}},
        ),
        execute=execute_get_session_info,
    ),
]


# ===========================================================================
# Lifecycle Hooks
# ===========================================================================


async def on_load(ctx: SkillContext) -> None:
    """Called once when the skill is loaded at app startup.

    Use this to initialize state, read config, set up connections.

    Demonstrates: read_data, set_state, log
    """
    ctx.log("kitchen-sink: on_load — initializing skill")

    # Load configuration from the setup flow (if completed)
    try:
        raw = await ctx.read_data("config.json")
        config = json.loads(raw)
        ctx.set_state({"config": config, "loaded_at": _now()})
        ctx.log(f"kitchen-sink: loaded config for user '{config.get('username')}'")
    except Exception:
        ctx.set_state({"config": None, "loaded_at": _now()})
        ctx.log("kitchen-sink: no config found (setup not completed)")

    # Initialize notes index if not present
    state = ctx.get_state() or {}
    if "notes_index" not in state:
        ctx.set_state({"notes_index": []})


async def on_unload(ctx: SkillContext) -> None:
    """Called once when the skill is unloaded at app shutdown.

    Use this to clean up resources, flush buffers, close connections.

    Demonstrates: log, set_state
    """
    ctx.log("kitchen-sink: on_unload — cleaning up")
    ctx.set_state({"unloaded_at": _now()})


async def on_session_start(ctx: SkillContext, session_id: str) -> None:
    """Called when a new conversation session begins.

    Use this to initialize session-scoped state, greet the user, or
    load session-specific context.

    Demonstrates: session.set, log
    """
    ctx.log(f"kitchen-sink: session started — {session_id}")
    ctx.session.set("message_count", 0)
    ctx.session.set("session_started_at", _now())


async def on_session_end(ctx: SkillContext, session_id: str) -> None:
    """Called when a conversation session ends.

    Use this to persist session summaries, flush analytics, etc.

    Demonstrates: session.get, memory.write, log
    """
    message_count = ctx.session.get("message_count") or 0
    started_at = ctx.session.get("session_started_at") or "unknown"

    ctx.log(
        f"kitchen-sink: session ended — {session_id} ({message_count} messages since {started_at})"
    )

    # Save a session summary to memory for future context
    if message_count > 0:
        await ctx.memory.write(
            f"session-summary/{session_id}",
            json.dumps(
                {
                    "session_id": session_id,
                    "message_count": message_count,
                    "started_at": started_at,
                    "ended_at": _now(),
                }
            ),
        )


async def on_before_message(ctx: SkillContext, message: str) -> str | None:
    """Called before each user message is sent to the AI.

    Return a string to transform/augment the message.
    Return None to pass it through unchanged.

    Demonstrates: session.get/set, get_state, message transformation
    """
    # Track message count in session
    count = (ctx.session.get("message_count") or 0) + 1
    ctx.session.set("message_count", count)

    # Example: inject context from config into the first message
    state = ctx.get_state() or {}
    config = state.get("config")
    if count == 1 and config:
        username = config.get("username", "User")
        preferences = config.get("preferences", [])
        prefs_str = ", ".join(preferences) if preferences else "none set"
        context_block = (
            f"\n\n[System context from kitchen-sink skill: "
            f"User is '{username}', preferences: {prefs_str}]"
        )
        return message + context_block

    return None  # No transformation


async def on_after_response(ctx: SkillContext, response: str) -> str | None:
    """Called after the AI generates a response, before it's shown to the user.

    Return a string to transform the response.
    Return None to pass it through unchanged.

    Demonstrates: response transformation
    """
    # Example: append a subtle footer on every 5th message
    count = ctx.session.get("message_count") or 0
    if count > 0 and count % 5 == 0:
        return response + "\n\n---\n_Tip: Use `list_notes` to see your saved notes._"

    return None  # No transformation


async def on_memory_flush(ctx: SkillContext) -> None:
    """Called before the memory system compacts/flushes.

    Use this to save any in-memory state that should survive compaction.

    Demonstrates: memory.write, get_state, log
    """
    ctx.log("kitchen-sink: on_memory_flush — persisting volatile state")

    state = ctx.get_state() or {}
    notes_index = state.get("notes_index", [])

    # Persist the notes index to memory so it survives compaction
    if notes_index:
        await ctx.memory.write(
            "kitchen-sink/notes-index",
            json.dumps(notes_index),
        )


async def on_tick(ctx: SkillContext) -> None:
    """Called periodically at the configured tick_interval (60 seconds).

    Use this for background tasks: polling APIs, syncing data,
    generating summaries, cleaning up stale data.

    Demonstrates: get_state, set_state, memory.list, log, emit_event
    """
    state = ctx.get_state() or {}
    tick_count = state.get("tick_count", 0) + 1
    ctx.set_state({"tick_count": tick_count, "last_tick": _now()})

    ctx.log(f"kitchen-sink: tick #{tick_count}")

    # Example: every 10 ticks (~10 minutes), emit a summary event
    if tick_count % 10 == 0:
        notes_count = len(state.get("notes_index", []))
        memories = await ctx.memory.list()

        ctx.emit_event(
            "periodic_summary",
            {
                "tick_count": tick_count,
                "notes_count": notes_count,
                "memory_count": len(memories),
                "timestamp": _now(),
            },
        )
        ctx.log(
            f"kitchen-sink: emitted periodic_summary "
            f"(notes={notes_count}, memories={len(memories)})"
        )


# ===========================================================================
# Interactive Setup Flow
# ===========================================================================
# Skills with has_setup=True define a multi-step wizard that the host
# renders as a form UI. The flow:
#   on_setup_start → returns first SetupStep
#   on_setup_submit(step_id, values) → returns SetupResult
#     status="next"     → show next_step
#     status="error"    → show field errors, stay on current step
#     status="complete" → setup is done
#   on_setup_cancel → cleanup if user aborts


async def on_setup_start(ctx: SkillContext) -> SetupStep:
    """Return the first step of the setup wizard.

    Demonstrates: SetupStep, SetupField, multiple field types
    """
    return SetupStep(
        id="profile",
        title="Your Profile",
        description="Tell us a bit about yourself to personalize the experience.",
        fields=[
            SetupField(
                name="username",
                type="text",
                label="Display Name",
                description="How should the AI address you?",
                placeholder="e.g. Satoshi",
                required=True,
            ),
            SetupField(
                name="experience",
                type="select",
                label="Crypto Experience",
                description="Your level of experience in crypto.",
                options=[
                    SetupFieldOption(label="Beginner", value="beginner"),
                    SetupFieldOption(label="Intermediate", value="intermediate"),
                    SetupFieldOption(label="Advanced", value="advanced"),
                    SetupFieldOption(label="Degen", value="degen"),
                ],
                required=True,
            ),
            SetupField(
                name="preferences",
                type="multiselect",
                label="Interests",
                description="Select topics you're interested in.",
                options=[
                    SetupFieldOption(label="DeFi", value="defi"),
                    SetupFieldOption(label="NFTs", value="nfts"),
                    SetupFieldOption(label="Trading", value="trading"),
                    SetupFieldOption(label="Development", value="development"),
                    SetupFieldOption(label="Research", value="research"),
                    SetupFieldOption(label="Governance", value="governance"),
                ],
                required=False,
                default=[],
            ),
        ],
    )


async def on_setup_submit(ctx: SkillContext, step_id: str, values: dict[str, Any]) -> SetupResult:
    """Handle form submission for each setup step.

    Demonstrates: validation, multi-step flow, data persistence, SetupResult
    """
    if step_id == "profile":
        return await _handle_profile_step(ctx, values)
    elif step_id == "notifications":
        return await _handle_notifications_step(ctx, values)
    else:
        return SetupResult(
            status="error",
            errors=[SetupFieldError(field="", message=f"Unknown step: {step_id}")],
        )


async def on_setup_cancel(ctx: SkillContext) -> None:
    """Handle user cancellation of the setup wizard.

    Demonstrates: cleanup of partial setup state
    """
    ctx.log("kitchen-sink: setup cancelled — cleaning up partial state")
    # Clear any partial config that may have been saved mid-flow
    ctx.set_state({"setup_partial": None})


# ---------------------------------------------------------------------------
# Setup step handlers
# ---------------------------------------------------------------------------


async def _handle_profile_step(ctx: SkillContext, values: dict[str, Any]) -> SetupResult:
    """Validate the profile step and advance to notifications."""
    username = (values.get("username") or "").strip()
    experience = values.get("experience", "")
    preferences = values.get("preferences", [])

    # --- Validation ---
    errors: list[SetupFieldError] = []

    if not username:
        errors.append(SetupFieldError(field="username", message="Display name is required."))
    elif len(username) < 2:
        errors.append(
            SetupFieldError(field="username", message="Display name must be at least 2 characters.")
        )

    if not experience:
        errors.append(
            SetupFieldError(field="experience", message="Please select your experience level.")
        )

    if errors:
        return SetupResult(status="error", errors=errors)

    # --- Save partial state ---
    ctx.set_state(
        {
            "setup_partial": {
                "username": username,
                "experience": experience,
                "preferences": preferences,
            }
        }
    )

    # --- Advance to next step ---
    return SetupResult(
        status="next",
        next_step=SetupStep(
            id="notifications",
            title="Notification Preferences",
            description="Configure how you'd like to receive updates.",
            fields=[
                SetupField(
                    name="enable_notifications",
                    type="boolean",
                    label="Enable Notifications",
                    description="Receive alerts for important events.",
                    default=True,
                ),
                SetupField(
                    name="digest_frequency",
                    type="select",
                    label="Digest Frequency",
                    description="How often to receive summary digests.",
                    options=[
                        SetupFieldOption(label="Every hour", value="hourly"),
                        SetupFieldOption(label="Daily", value="daily"),
                        SetupFieldOption(label="Weekly", value="weekly"),
                        SetupFieldOption(label="Never", value="never"),
                    ],
                    default="daily",
                ),
                SetupField(
                    name="alert_threshold",
                    type="number",
                    label="Price Alert Threshold (%)",
                    description="Minimum percentage change to trigger a price alert.",
                    placeholder="e.g. 5",
                    default=5,
                    required=False,
                ),
            ],
        ),
    )


async def _handle_notifications_step(ctx: SkillContext, values: dict[str, Any]) -> SetupResult:
    """Validate notifications step and complete setup."""
    enable_notifications = values.get("enable_notifications", True)
    digest_frequency = values.get("digest_frequency", "daily")
    alert_threshold = values.get("alert_threshold", 5)

    # --- Validation ---
    if alert_threshold is not None:
        try:
            alert_threshold = float(alert_threshold)
            if alert_threshold < 0 or alert_threshold > 100:
                return SetupResult(
                    status="error",
                    errors=[
                        SetupFieldError(
                            field="alert_threshold",
                            message="Threshold must be between 0 and 100.",
                        )
                    ],
                )
        except (ValueError, TypeError):
            return SetupResult(
                status="error",
                errors=[
                    SetupFieldError(
                        field="alert_threshold",
                        message="Must be a valid number.",
                    )
                ],
            )

    # --- Merge with profile data and persist ---
    state = ctx.get_state() or {}
    partial = state.get("setup_partial", {})

    config = {
        **partial,
        "enable_notifications": enable_notifications,
        "digest_frequency": digest_frequency,
        "alert_threshold": alert_threshold,
        "setup_completed_at": _now(),
    }

    # Persist config to data directory
    await ctx.write_data("config.json", json.dumps(config, indent=2))

    # Update skill state
    ctx.set_state({"config": config, "setup_partial": None})

    # Emit setup complete event
    ctx.emit_event("setup_completed", {"username": config.get("username")})

    ctx.log(f"kitchen-sink: setup completed for '{config.get('username')}'")

    return SetupResult(
        status="complete",
        message=(
            f"All set, {config['username']}! "
            f"Your preferences have been saved. "
            f"You'll receive {digest_frequency} digests."
        ),
    )


# ===========================================================================
# Dynamic Tool Registration (Advanced)
# ===========================================================================
# Skills can register/unregister tools at runtime, e.g. based on setup
# config or feature flags. This is done in lifecycle hooks using
# ctx.tools.register() and ctx.tools.unregister().


async def execute_dynamic_tool(args: dict) -> ToolResult:
    """A tool registered dynamically at runtime."""
    ctx: SkillContext = args.pop("__context__")
    state = ctx.get_state() or {}
    config = state.get("config", {})
    username = config.get("username", "User")
    return ToolResult(content=f"Hello {username}! This tool was registered dynamically.")


async def _register_dynamic_tools(ctx: SkillContext) -> None:
    """Register tools based on config (called from on_load)."""
    state = ctx.get_state() or {}
    config = state.get("config")

    if not config:
        return

    # Example: register an extra tool only for advanced/degen users
    if config.get("experience") in ("advanced", "degen"):
        ctx.tools.register(
            SkillTool(
                definition=ToolDefinition(
                    name="advanced_analytics",
                    description="Run advanced on-chain analytics (advanced users only).",
                    parameters={
                        "type": "object",
                        "properties": {
                            "protocol": {
                                "type": "string",
                                "description": "Protocol to analyze",
                            },
                        },
                        "required": ["protocol"],
                    },
                ),
                execute=execute_dynamic_tool,
            )
        )
        ctx.log("kitchen-sink: registered advanced_analytics tool")


# ===========================================================================
# Helpers
# ===========================================================================


def _now() -> str:
    """Current UTC timestamp as ISO string."""
    return datetime.now(timezone.utc).isoformat()


# ===========================================================================
# Skill Definition — the main export
# ===========================================================================

skill = SkillDefinition(
    name="kitchen-sink",
    description=(
        "Comprehensive example skill demonstrating every capability: "
        "lifecycle hooks, tools, setup flow, state, memory, entities, "
        "events, and periodic tasks."
    ),
    version="1.0.0",
    tools=TOOLS,
    tick_interval=60_000,  # 60 seconds, in milliseconds
    has_setup=True,
    hooks=SkillHooks(
        on_load=on_load,
        on_unload=on_unload,
        on_session_start=on_session_start,
        on_session_end=on_session_end,
        on_before_message=on_before_message,
        on_after_response=on_after_response,
        on_memory_flush=on_memory_flush,
        on_tick=on_tick,
        on_setup_start=on_setup_start,
        on_setup_submit=on_setup_submit,
        on_setup_cancel=on_setup_cancel,
    ),
)
