# AlphaHuman Skills

A plugin system for the [AlphaHuman](https://github.com/bnbpad/alphahuman) platform. Skills give the AI agent domain-specific knowledge, custom tools, and automated behaviors.

## Features

- **Near real-time capabilities via events.** Skills hook into lifecycle events (`on_tick`, `on_before_message`, `on_after_response`) to react to changes as they happen, monitoring Telegram chats, tracking prices, or surfacing alerts without the user asking. The `on_tick` hook runs on a configurable interval (as low as 1 second), enabling continuous background monitoring.

- **Powerful memory through bulk summaries.** Skills persist data to SQLite and JSON files within their isolated `data/` directory. The `on_memory_flush` hook lets skills compress and summarize accumulated data before memory compaction, keeping context rich without ballooning token usage. Skills read and write structured data directly, no round-trips through the LLM.

- **Cost efficient by keeping logic in Python code.** Tool handlers, data transformations, API calls, and business logic are all written in Python, they execute as native code, not as LLM-generated text. The AI only sees tool definitions (name, description, JSON Schema parameters) and tool results (compact strings). This keeps prompts small and avoids spending tokens on logic that code handles better.

## How Skills Work

A skill is a Python directory under `skills/` containing:

| File            | Required | Purpose                                                                   |
| --------------- | -------- | ------------------------------------------------------------------------- |
| `skill.py`      | Yes      | Python module exporting a `SkillDefinition` with hooks, tools, and config |
| `setup.py`      | No       | Interactive setup flow for configuration wizards (e.g., Telegram auth)    |
| `manifest.json` | No       | Metadata for runtime skills (id, dependencies, env vars, setup config)    |

Skills register tools the AI can call, react to lifecycle events, persist data, and run periodic background tasks.

```
skills/<SKILLNAME>/
├── skill.py          # SkillDefinition with hooks and tools
├── setup.py          # Multi-step Telegram auth wizard
├── manifest.json     # Runtime config, dependencies, env vars
├── client/           # Telethon client wrapper
├── handlers/         # Tool handler functions
├── api/              # Domain-specific API wrappers
├── state/            # In-process state management
├── db/               # SQLite persistence
└── data/             # Auto-created persistent storage
```

## Available Skills

| Skill                          | Description                                                                                                    | Setup    |
| ------------------------------ | -------------------------------------------------------------------------------------------------------------- | -------- |
| [`telegram`](skills/telegram/) | Telegram integration via Telethon MTProto, 75+ tools for chats, messages, contacts, admin, media, and settings | Required |

## Quick Start

### Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) or pip

### Install dev tools

```bash
pip install -e dev/
# or with uv:
uv venv .venv && source .venv/bin/activate && uv pip install -e dev/
```

### Create a skill

```bash
# Scaffold a new skill interactively
python -m dev.scaffold.new_skill my-skill

# Or copy from an example
cp -r examples/tool-skill/ skills/my-skill/
```

### Validate and test

```bash
# Validate all skills
python -m dev.validate.validator

# Test a specific skill with mock context
python -m dev.harness.runner skills/my-skill --verbose

# Test a skill's interactive setup flow
python test-setup.py skills/my-skill

# Interactive server REPL, connect, browse tools, call them live
python test-server.py
```

## skill.py Format

```python
from dev.types.skill_types import SkillDefinition, SkillHooks, SkillTool, ToolDefinition, ToolResult

async def on_load(ctx):
    ctx.log("Skill loaded")

async def my_tool_execute(args):
    return ToolResult(content=f"Result: {args.get('input', '')}")

skill = SkillDefinition(
    name="my-skill",
    description="What this skill does",
    version="1.0.0",
    hooks=SkillHooks(
        on_load=on_load,
    ),
    tools=[
        SkillTool(
            definition=ToolDefinition(
                name="my_tool",
                description="What the tool does",
                parameters={
                    "type": "object",
                    "properties": {
                        "input": {"type": "string", "description": "Input value"},
                    },
                    "required": ["input"],
                },
            ),
            execute=my_tool_execute,
        ),
    ],
    tick_interval=60_000,  # optional: periodic on_tick every 60s
)
```

## Setup Flow (Optional)

Skills that need interactive configuration (API keys, authentication, etc.) can define a setup flow. The host renders multi-step forms and the skill validates each step.

```python
# setup.py
from dev.types.setup_types import SetupStep, SetupField, SetupResult, SetupFieldError

async def on_setup_start(ctx):
    return SetupStep(
        id="credentials",
        title="API Credentials",
        fields=[
            SetupField(name="api_key", type="password", label="API Key", required=True),
        ],
    )

async def on_setup_submit(ctx, step_id, values):
    if not values.get("api_key"):
        return SetupResult(
            status="error",
            errors=[SetupFieldError(field="api_key", message="Required")],
        )
    await ctx.write_data("config.json", json.dumps({"api_key": values["api_key"]}))
    return SetupResult(status="complete", message="Connected!")

async def on_setup_cancel(ctx):
    pass  # Clean up transient state
```

Field types: `text`, `number`, `password`, `select`, `multiselect`, `boolean`.

Test interactively: `python test-setup.py skills/my-skill`

## Lifecycle Hooks

```
App Start ── on_load
                │
        ┌── on_session_start
        │       │
        │   on_before_message  ← can transform user message
        │       │
        │   [AI processes]
        │       │
        │   on_after_response  ← can transform AI response
        │       │
        └── on_session_end
                │
App Stop ── on_unload           on_tick ← runs every tick_interval ms
```

| Hook                | Can Transform? | Use Case                               |
| ------------------- | :------------: | -------------------------------------- |
| `on_load`           |                | Load cached data at startup            |
| `on_unload`         |                | Persist state on shutdown              |
| `on_session_start`  |                | Report cached alerts, load prefs       |
| `on_session_end`    |                | Save session summary                   |
| `on_before_message` |      Yes       | Annotate messages with context         |
| `on_after_response` |      Yes       | Append disclaimers to responses        |
| `on_memory_flush`   |                | Save data before memory compaction     |
| `on_tick`           |                | Background monitoring, periodic checks |
| `on_setup_start`    |                | Return first setup step                |
| `on_setup_submit`   |                | Validate and process step submission   |
| `on_setup_cancel`   |                | Clean up on user cancel                |

All hooks have a **10-second timeout**. See [Lifecycle docs](docs/lifecycle.md) for details.

## SkillContext API

Every hook receives a `ctx` object:

```python
ctx.memory           # Read/write/search shared memory
ctx.session          # Session-scoped key-value store
ctx.tools            # Register/unregister tools at runtime
ctx.entities         # Query entity graph (contacts, wallets, chats)
ctx.data_dir         # Path to skill's data directory
ctx.read_data(file)  # Read from data directory
ctx.write_data(file) # Write to data directory
ctx.log(msg)         # Debug logging
ctx.get_state()      # Read skill state store
ctx.set_state(patch) # Update skill state store
ctx.emit_event(name) # Emit events for intelligence rules
```

See [API Reference](docs/api-reference.md) for the full type definitions.

## Dev Tooling

All tools live in `dev/`. Install once: `pip install -e dev/`

```bash
python -m dev.validate.validator                    # Validate all skills
python -m dev.harness.runner skills/my-skill         # Test a specific skill
python test-setup.py skills/my-skill                 # Test setup flow interactively
python test-server.py                                # Interactive server REPL (Telegram)
python -m dev.security.scan_secrets                  # Security scan all skills
python -m dev.scaffold.new_skill                     # Scaffold a new skill
python -m dev.catalog.build_catalog                  # Build skills catalog
```

Or use CLI entry points: `skill-validate`, `skill-test`, `skill-scan`, `skill-new`, `skill-catalog`.

### Validator

Checks every skill's `skill.py` (exports, types, tool schemas, tick interval, setup hook consistency).

### Test Harness

Loads a skill into a mock context, runs all lifecycle hooks in order, exercises the setup flow if `has_setup=True`, and auto-tests every tool with generated arguments from its JSON Schema.

### Security Scanner

Regex-based scanner that flags hardcoded secrets, `eval()`, direct filesystem access, network requests, and other patterns that don't belong in skills.

## Examples

| Example                                | Pattern      | Description                                                |
| -------------------------------------- | ------------ | ---------------------------------------------------------- |
| [`prompt-only`](examples/prompt-only/) | Prompt only  | Gas optimizer using SKILL.md instructions (legacy format)  |
| [`tool-skill`](examples/tool-skill/)   | Python skill | Gas estimator with `gas_estimate` tool and lifecycle hooks |

## Documentation

| Doc                                        | Description                                             |
| ------------------------------------------ | ------------------------------------------------------- |
| [Getting Started](docs/getting-started.md) | Prerequisites, first skill, test, submit                |
| [Architecture](docs/architecture.md)       | How the skill system loads, isolates, and runs skills   |
| [API Reference](docs/api-reference.md)     | Complete SkillDefinition, SkillContext, SkillTool types |
| [Lifecycle](docs/lifecycle.md)             | Hook timing, execution order, timeout rules             |
| [Testing](docs/testing.md)                 | Validator, harness, mock context, security scanner      |
| [Python Skills](docs/python-skills.md)     | Subprocess runtime and JSON-RPC protocol                |
| [Publishing](docs/publishing.md)           | PR workflow, naming conventions, common rejections      |

## Repository Structure

```
skills/                          # Repo root
├── skills/                      # Production skills
│   └── telegram/                # Telegram integration (75+ tools)
├── dev/                         # Developer tooling (Python)
│   ├── pyproject.toml           # Dependencies: pydantic>=2.0
│   ├── types/
│   │   ├── skill_types.py       # Pydantic v2 type definitions
│   │   └── setup_types.py       # Setup flow types
│   ├── runtime/server.py        # asyncio JSON-RPC 2.0 server
│   ├── harness/                 # Mock context + test runner
│   ├── validate/                # skill.py validator
│   ├── scaffold/                # Interactive skill scaffolder
│   ├── security/                # Secret/pattern scanner
│   └── catalog/                 # Skills catalog builder
├── examples/                    # Example skills
│   ├── prompt-only/             # Prompt-only example
│   └── tool-skill/              # Python tool example
├── prompts/                     # AI prompt templates for non-coders
│   └── categories/              # Domain-specific generators
├── docs/                        # Developer documentation
├── test-setup.py                # Interactive setup flow tester
├── test-server.py               # Interactive server REPL for tools
├── .github/                     # CI workflows + PR template
├── CONTRIBUTING.md              # How to contribute
└── CLAUDE.md                    # Guidance for Claude Code
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for the full guide. The short version:

1. Fork and clone
2. `pip install -e dev/`
3. `python -m dev.scaffold.new_skill my-skill`
4. Write your `skill.py` (and optionally `setup.py`)
5. `python -m dev.validate.validator`
6. Submit a pull request
