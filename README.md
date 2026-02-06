# AlphaHuman Skills

A plugin system for the [AlphaHuman](https://github.com/bnbpad/alphahuman) platform. Skills give the AI agent domain-specific knowledge, custom tools, and automated behaviors.

## Features

- **Near real-time capabilities via cron scheduling.** Skills register cron schedules with 6-field syntax (including seconds) for background monitoring, periodic health checks, and automated tasks. Schedules can run as frequently as every second.

- **Powerful persistence through SQLite and key-value stores.** Each skill has an isolated SQLite database and a persistent key-value store. Query with SQL, store structured data, and maintain state across restarts — all without round-trips through the LLM.

- **Cost efficient by keeping logic in code.** Tool handlers, data transformations, API calls, and business logic are written in TypeScript, compiled to JavaScript, and run in a sandboxed QuickJS runtime. The AI only sees tool definitions and results. This keeps prompts small and avoids spending tokens on logic that code handles better.

- **Real-time state publishing to the frontend.** Skills can push state updates to the frontend in real time via the `state` API. Perfect for dashboards, status indicators, and live monitoring displays.

- **Cross-platform support.** Skills declare which platforms they support (Windows, macOS, Linux, Android, iOS). The runtime automatically handles platform-specific behaviors.

- **Per-skill dependencies.** Each skill can declare its own npm dependencies via an optional `package.json`. Dependencies are installed automatically during the build and bundled into the single output file.

## How Skills Work

A skill is a TypeScript directory under `src/` that compiles to JavaScript in `skills/`:

| File            | Required | Purpose                                             |
| --------------- | -------- | --------------------------------------------------- |
| `index.ts`      | Yes      | TypeScript source with lifecycle hooks and tools    |
| `manifest.json` | Yes      | Metadata (id, name, version, runtime, setup config) |
| `package.json`  | No       | Per-skill npm dependencies (bundled by esbuild)     |
| `__tests__/`    | No       | Test files for the skill                            |

Skills register tools the AI can call, react to lifecycle events, persist data, and run scheduled background tasks.

```
src/<skill-name>/
├── index.ts          # Main skill code (TypeScript)
├── manifest.json     # Metadata (id, runtime, entry, setup config)
├── package.json      # Optional per-skill dependencies
└── __tests__/
    └── test-<name>.ts  # Unit tests
```

## Available Skills

| Skill                                 | Description                                                    | Setup    |
| ------------------------------------- | -------------------------------------------------------------- | -------- |
| [`server-ping`](src/server-ping/)     | Monitors server health with configurable ping intervals        | Required |
| [`notion`](src/notion/)               | Notion integration with 22+ tools for pages, databases, blocks | Required |
| [`telegram`](src/telegram/)           | Telegram integration via TDLib with 50+ tools                  | Required |
| [`gmail`](src/gmail/)                 | Gmail integration with OAuth2 and email management             | Required |
| [`example-skill`](src/example-skill/) | Kitchen-sink example demonstrating all APIs and patterns       | Required |

## Quick Start

### Prerequisites

- Node.js 22+

### Install dependencies

```bash
yarn install
```

### Build skills

```bash
# Full build: clean, install skill deps, compile, bundle, post-process
yarn build

# Type checking only
yarn typecheck

# Watch mode for development
yarn build:watch
```

### Interactive REPL

```bash
# Pick a skill from a list
yarn repl

# Load a specific skill directly
yarn repl server-ping

# Wipe persisted data and start fresh
yarn repl example-skill --clean
```

See [Testing & Development](#testing--development) below for full REPL documentation.

### Run tests

```bash
# Run smoke tests on all built skills
yarn test

# Run a test script against a specific skill
yarn test:script <skill-id> <script-file>

# Example:
yarn test:script server-ping scripts/examples/test-ping-flow.js
```

### Validate skills

```bash
# Run all validation checks (manifest, secrets, code quality)
yarn validate

# Secret scanning only
yarn validate:secrets
```

## Skill Structure

### manifest.json

```json
{
  "id": "my-skill",
  "name": "My Skill",
  "runtime": "quickjs",
  "entry": "index.js",
  "version": "1.0.0",
  "description": "What this skill does",
  "auto_start": false,
  "platforms": ["windows", "macos", "linux"],
  "setup": { "required": true, "label": "Configure My Skill" }
}
```

### index.ts Structure

```typescript
// Configuration interface
interface SkillConfig {
  apiKey: string;
  refreshInterval: number;
}

const CONFIG: SkillConfig = { apiKey: '', refreshInterval: 60 };

// ---------------------------------------------------------------------------
// Lifecycle hooks
// ---------------------------------------------------------------------------

function init(): void {
  // Called when skill is loaded
  // Initialize database tables, load config from store
  db.exec('CREATE TABLE IF NOT EXISTS logs (...)', []);

  const saved = store.get('config') as Partial<SkillConfig> | null;
  if (saved) {
    CONFIG.apiKey = saved.apiKey ?? CONFIG.apiKey;
  }
}

function start(): void {
  // Called when skill should begin active work
  // Register cron schedules, publish initial state
  cron.register('refresh', `*/${CONFIG.refreshInterval} * * * * *`);
  publishState();
}

function stop(): void {
  // Called on shutdown
  // Unregister cron schedules, persist state
  cron.unregister('refresh');
  store.set('config', CONFIG);
}

function onCronTrigger(scheduleId: string): void {
  // Called when a registered cron schedule fires
  if (scheduleId === 'refresh') {
    doRefresh();
  }
}

function onSessionStart(args: { sessionId: string }): void {
  // Called when user starts a conversation
}

function onSessionEnd(args: { sessionId: string }): void {
  // Called when conversation ends
}

// ---------------------------------------------------------------------------
// Setup flow (multi-step wizard)
// ---------------------------------------------------------------------------

function onSetupStart(): SetupStartResult {
  return {
    step: {
      id: 'credentials',
      title: 'API Credentials',
      description: 'Enter your API key',
      fields: [{ name: 'apiKey', type: 'password', label: 'API Key', required: true }],
    },
  };
}

function onSetupSubmit(args: {
  stepId: string;
  values: Record<string, unknown>;
}): SetupSubmitResult {
  if (args.stepId === 'credentials') {
    const apiKey = args.values.apiKey as string;
    if (!apiKey) {
      return { status: 'error', errors: [{ field: 'apiKey', message: 'Required' }] };
    }
    CONFIG.apiKey = apiKey;
    store.set('config', CONFIG);
    return { status: 'complete' };
  }
  return { status: 'error', errors: [] };
}

function onSetupCancel(): void {
  // Clean up transient state
}

function onDisconnect(): void {
  // Called when user disconnects the skill
  store.delete('config');
}

// ---------------------------------------------------------------------------
// Options (runtime-configurable settings)
// ---------------------------------------------------------------------------

function onListOptions(): { options: SkillOption[] } {
  return {
    options: [
      {
        name: 'refreshInterval',
        type: 'select',
        label: 'Refresh Interval',
        value: String(CONFIG.refreshInterval),
        options: [
          { label: 'Every 30 seconds', value: '30' },
          { label: 'Every 60 seconds', value: '60' },
        ],
      },
    ],
  };
}

function onSetOption(args: { name: string; value: unknown }): void {
  if (args.name === 'refreshInterval') {
    CONFIG.refreshInterval = parseInt(args.value as string);
    cron.unregister('refresh');
    cron.register('refresh', `*/${CONFIG.refreshInterval} * * * * *`);
    store.set('config', CONFIG);
  }
}

// ---------------------------------------------------------------------------
// Tools (exposed to AI)
// ---------------------------------------------------------------------------

tools = [
  {
    name: 'get-status',
    description: 'Get current status',
    input_schema: { type: 'object', properties: {} },
    execute(args): string {
      return JSON.stringify({ status: 'ok', config: CONFIG });
    },
  },
];
```

## Bridge APIs

Skills have access to these global namespaces:

### `db` — SQLite Database

```typescript
db.exec('CREATE TABLE logs (id INTEGER PRIMARY KEY, msg TEXT)', []);
db.exec('INSERT INTO logs (msg) VALUES (?)', ['hello']);
const row = db.get('SELECT * FROM logs WHERE id = ?', [1]);
const rows = db.all('SELECT * FROM logs LIMIT 10', []);
db.kvSet('key', { any: 'value' });
const value = db.kvGet('key');
```

### `store` — Persistent Key-Value Store

```typescript
store.set('config', { apiKey: 'xxx' });
const config = store.get('config');
store.delete('config');
const keys = store.keys();
```

### `net` — HTTP Networking

```typescript
const response = net.fetch('https://api.example.com/data', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ query: 'test' }),
  timeout: 10000,
});
// response: { status: number, headers: Record<string, string>, body: string }
```

### `cron` — Scheduling

```typescript
// 6-field cron syntax: seconds minutes hours day month dow
cron.register('every-10s', '*/10 * * * * *');
cron.register('every-minute', '0 * * * * *');
cron.register('daily-9am', '0 0 9 * * *');
cron.unregister('every-10s');
const schedules = cron.list();
```

### `state` — Frontend State Publishing

```typescript
state.set('status', 'healthy');
state.setPartial({ lastPing: Date.now(), uptime: 99.9 });
const status = state.get('status');
```

### `data` — File I/O

```typescript
data.write('config.json', JSON.stringify(config, null, 2));
const content = data.read('config.json'); // returns null if not found
```

### `platform` — OS Integration

```typescript
const os = platform.os(); // "windows", "macos", "linux", "android", "ios"
const apiKey = platform.env('MY_API_KEY'); // whitelisted env vars only
platform.notify('Server Down', 'api.example.com is not responding');
```

### `skills` — Inter-Skill Communication

```typescript
const allSkills = skills.list();
const result = skills.callTool('other-skill', 'tool-name', { arg: 'value' });
```

## Lifecycle Hooks

```
Skill Load ── init()
                │
        ┌── start()
        │       │
        │   onCronTrigger(scheduleId) ← fires on schedule
        │       │
        │   onSessionStart({ sessionId })
        │       │
        │   [AI conversation]
        │       │
        │   onSessionEnd({ sessionId })
        │       │
        └── stop()
```

| Hook                        | Purpose                                    |
| --------------------------- | ------------------------------------------ |
| `init()`                    | Initialize DB, load config                 |
| `start()`                   | Begin active work, register cron schedules |
| `stop()`                    | Clean shutdown, persist state              |
| `onCronTrigger(scheduleId)` | Handle cron schedule triggers              |
| `onSessionStart(args)`      | User started a conversation                |
| `onSessionEnd(args)`        | Conversation ended                         |
| `onSetupStart()`            | Return first setup step                    |
| `onSetupSubmit(args)`       | Validate and process setup step            |
| `onSetupCancel()`           | Clean up on user cancel                    |
| `onDisconnect()`            | Clean disconnection (clear credentials)    |
| `onListOptions()`           | Return runtime-configurable options        |
| `onSetOption(args)`         | Handle option changes                      |

## Setup Flow

Skills that need interactive configuration define a multi-step setup wizard:

```typescript
function onSetupStart(): SetupStartResult {
  return {
    step: {
      id: "step1",
      title: "Step 1",
      description: "Configure basic settings",
      fields: [
        { name: "url", type: "text", label: "URL", required: true },
        { name: "interval", type: "select", label: "Interval", options: [...] },
      ],
    },
  };
}

function onSetupSubmit(args: { stepId: string; values: Record<string, unknown> }): SetupSubmitResult {
  if (args.stepId === "step1") {
    // Validate
    if (!args.values.url) {
      return { status: "error", errors: [{ field: "url", message: "Required" }] };
    }
    // Move to next step
    return { status: "next", nextStep: { id: "step2", ... } };
  }
  if (args.stepId === "step2") {
    // Final step
    store.set("config", finalConfig);
    return { status: "complete" };
  }
}
```

Field types: `text`, `password`, `number`, `select`, `boolean`.

## Per-Skill Dependencies

Skills can declare their own npm dependencies via a `package.json` in their directory:

```json
// src/my-skill/package.json
{
  "name": "@alphahuman/skill-my-skill",
  "private": true,
  "dependencies": { "some-library": "^1.0.0" }
}
```

- Only `dependencies` are bundled (not `devDependencies`)
- `node_modules` inside skill directories are gitignored
- esbuild bundles all imports into the single IIFE output file
- Dependencies are installed automatically during `yarn build`

## Testing & Development

### Interactive REPL (`yarn repl`)

The REPL is the primary tool for interactive skill development and debugging. It loads a compiled skill and gives you a prompt to call tools, walk through setup wizards, and inspect state.

```bash
yarn repl                        # Pick a skill from a list
yarn repl server-ping            # Load a specific skill
yarn repl example-skill --clean  # Wipe data and start fresh
```

Once loaded, the REPL calls `init()` and `start()` automatically. If the skill requires setup and no config is found, it prompts you to walk through the setup wizard interactively.

#### REPL Commands

| Command                            | Description                                                  |
| ---------------------------------- | ------------------------------------------------------------ |
| `help`                             | Show all commands                                            |
| `tools`                            | List available tools with descriptions and parameters        |
| `call <tool> [json]`               | Call a tool; prompts for args interactively if no JSON given |
| `init` / `start` / `stop`          | Call lifecycle hooks                                         |
| `cron [id]`                        | List cron schedules, or trigger `onCronTrigger(id)`          |
| `session start [id]`               | Trigger `onSessionStart`                                     |
| `session end [id]`                 | Trigger `onSessionEnd`                                       |
| `setup`                            | Run (or re-run) the setup wizard                             |
| `options`                          | List runtime options via `onListOptions()`                   |
| `option <name> <value>`            | Set a runtime option via `onSetOption()`                     |
| `state`                            | Show published state (pretty-printed)                        |
| `store`                            | Show persistent store contents                               |
| `db <sql>`                         | Run SQL (SELECT uses `db.all()`, others use `db.exec()`)     |
| `mock fetch <url> <status> <body>` | Mock an HTTP response for `net.fetch`                        |
| `env <key> <value>`                | Set environment variable for `platform.env()`                |
| `disconnect`                       | Call `onDisconnect()`                                        |
| `reload`                           | Stop, re-read `index.js`, re-init, re-start                  |
| `exit` / `quit`                    | Clean exit (calls `stop()` and persists data)                |

When `call <tool>` is invoked without JSON, the REPL inspects the tool's `input_schema` and prompts for each parameter interactively (enum fields show a numbered list, numbers are validated, optional fields can be skipped).

#### Example REPL Session

```
$ yarn repl server-ping --clean
Loaded Server Ping v2.0.0
  3 tools available
init() ok
start() ok

Setup required but no config found.
Run setup wizard? [Y/n]: y

Setup Wizard
──────────────────────────────────────────────────
Server URL
  Server URL *: https://example.com
Setup complete!

server-ping> tools
Tools (3):
  do-ping ()
  get-status (format)
  get-history (limit)

server-ping> call get-status {"format": "json"}
Result:
{ "status": "unknown", "pingCount": 0 }

server-ping> cron health-check
onCronTrigger("health-check") completed

server-ping> state
{ "status": "healthy", "lastPing": "2026-02-06T..." }

server-ping> exit
stop() ok
Bye!
```

### Script Runner (`yarn test:script`)

Run a JavaScript test script against a compiled skill. The script has access to helper functions for calling tools, triggering lifecycle events, and mocking.

```bash
yarn test:script <skill-id> <script-file> [--clean] [--wait=<ms>]
```

**Options:**

- `--clean` — wipe the skill's data directory before running
- `--wait=<ms>` — wait for async operations before cleanup (useful for WebSocket skills)

**Available helpers in scripts:**

| Helper                                              | Description                                  |
| --------------------------------------------------- | -------------------------------------------- |
| `callTool(name, args)`                              | Call a skill tool, returns parsed result     |
| `triggerCron(scheduleId)`                           | Trigger `onCronTrigger`                      |
| `triggerSetupStart()`                               | Call `onSetupStart`, returns step definition |
| `triggerSetupSubmit(stepId, values)`                | Submit setup step values                     |
| `triggerSessionStart(id)` / `triggerSessionEnd(id)` | Session events                               |
| `triggerTimer(timerId)`                             | Fire a mock timer callback                   |
| `listTools()`                                       | Get array of tool names                      |
| `__mockFetch(url, response)`                        | Set mock HTTP response                       |
| `__mockFetchError(url, message)`                    | Set mock HTTP error                          |
| `__getMockState()`                                  | Inspect full mock state                      |
| `__resetMockState()`                                | Reset all mocks                              |
| `__setEnv(key, value)`                              | Set environment variable                     |
| `__setPlatformOs(os)`                               | Set `platform.os()` return value             |
| `__mockModelResponse(sub, resp)`                    | Mock model response for prompt substring     |
| `__setModelAvailable(bool)`                         | Set model availability                       |

**Example:**

```bash
yarn test:script server-ping scripts/examples/test-ping-flow.js
yarn test:script simple-skill scripts/examples/test-simple-skill.js --clean
yarn test:script telegram scripts/examples/test-telegram-setup.js --wait=10000
```

### Live Runner (`yarn test:live`)

Like `test:script`, but with real network support instead of mocked `net.fetch`. Use this for skills that require live connections (e.g., Telegram WebSocket).

```bash
yarn test:live <skill-id> <script-file> [--wait=<ms>]
```

Environment variables like `TELEGRAM_BOT_TOKEN` and `NOTION_API_KEY` are forwarded automatically.

### Smoke Tests (`yarn test`)

Runs `scripts/test-harness.mjs` which does automated verification of all compiled skills: loads each skill in a `vm` context, calls `init()`, checks for tool registration, and validates basic invariants.

```bash
yarn test                                              # Run all smoke tests
yarn test src/server-ping/__tests__/test-server-ping.ts  # Specific skill tests
```

### Model Testing (`yarn test:model`)

Run a test script with a real local LLM backend (via `node-llama-cpp`). Requires downloading a model first.

```bash
yarn model:download                        # Download the model (~2GB)
yarn test:model <skill-id> <script-file>   # Run with real inference
```

### Example Test Scripts

Pre-built example scripts in `scripts/examples/`:

| Script                   | Description                      |
| ------------------------ | -------------------------------- |
| `test-simple.js`         | Basic skill loading test         |
| `test-simple-skill.js`   | Simple skill lifecycle test      |
| `test-ping-flow.js`      | Server ping setup + cron flow    |
| `test-setup-flow.js`     | Multi-step setup wizard test     |
| `test-options-flow.js`   | Runtime options configuration    |
| `test-debug.js`          | Debug output and mock inspection |
| `test-telegram-setup.js` | Telegram skill setup flow        |
| `test-telegram-live.js`  | Telegram with live connections   |

### Data Persistence

All runners (REPL, script runner, live runner) use persistent file-backed storage in `skills/<skill-id>/data/`:

```
skills/<skill-id>/data/
  skill.db          # SQLite database
  store.json        # Key-value store
  state.json        # Published state
  files/            # data.read/write files
```

Use `--clean` to wipe this directory for a fresh start.

### Writing Unit Tests

```typescript
// src/my-skill/__tests__/test-my-skill.ts

function freshInit(overrides?: Partial<Config>): void {
  setupSkillTest({
    storeData: { config: { ...defaultConfig, ...overrides } },
    fetchResponses: { 'https://api.example.com/health': { status: 200, body: '{"ok":true}' } },
  });
  init();
}

_describe('My Skill', () => {
  _it('should initialize correctly', () => {
    freshInit();
    _assertNotNull(db.get('SELECT 1', []));
  });

  _it('should handle API calls', () => {
    freshInit({ apiKey: 'test' });
    start();
    const result = callTool('get-status', {});
    _assertEqual(result.status, 'ok');
  });
});
```

## Validation

Run `yarn validate` to check all skills for:

- **Manifest validation** — required fields, correct runtime, naming conventions
- **Secret scanning** — API keys, tokens, private keys in source code
- **Code quality** — no async/await, no eval(), no new Function()
- **Setup flow completeness** — if setup is required, hooks must be defined
- **Entry file exists** — `index.ts` must exist

Quick secret scan only: `yarn validate:secrets`

## Repository Structure

```
skills/                          # Repo root
├── src/                         # TypeScript source
│   ├── server-ping/             # Server health monitoring
│   ├── telegram/                # Telegram integration
│   ├── notion/                  # Notion integration
│   ├── gmail/                   # Gmail integration
│   ├── example-skill/           # Kitchen-sink example
│   └── simple-skill/            # Minimal test skill
├── skills/                      # Compiled JavaScript output (gitignored)
├── types/
│   └── globals.d.ts             # Ambient type declarations for bridge APIs
├── dev/
│   └── test-harness/            # Node.js test harness (tsx)
│       ├── repl-node.ts         # Interactive REPL
│       ├── runner-node.ts       # Script runner
│       ├── bootstrap-node.ts    # Bridge API mocks
│       ├── live-runner-node.ts  # Live network runner
│       ├── mock-state.ts        # Shared mock state
│       └── mock-db.ts           # SQLite mock
├── scripts/
│   ├── bundle-skills.mjs        # esbuild bundler
│   ├── strip-exports.mjs        # Post-build processing
│   ├── install-skill-deps.mjs   # Per-skill dependency installer
│   ├── validate.mjs             # Skill validator
│   ├── scan-secrets.mjs         # Secret scanner
│   ├── test-harness.mjs         # Smoke test runner
│   ├── test-js.sh               # Test runner script
│   └── examples/                # Example test scripts
├── skills-py/                   # Legacy Python skills (deprecated)
├── .github/workflows/           # CI pipeline
├── package.json                 # Build scripts and dependencies
├── tsconfig.json                # Base TypeScript config
├── tsconfig.build.json          # Production build config
├── tsconfig.test.json           # Test build config
├── eslint.config.js             # ESLint configuration
├── CLAUDE.md                    # Guidance for Claude Code
├── CONTRIBUTING.md              # Contributor guide
└── README.md                    # This file
```

## Build Process

1. **Install skill deps**: `node scripts/install-skill-deps.mjs` — installs per-skill `node_modules`
2. **TypeScript Compilation**: `tsc -p tsconfig.build.json` — compiles `src/*/index.ts`
3. **esbuild Bundling**: `node scripts/bundle-skills.mjs` — bundles tools into single IIFE
4. **Post-Processing** (`strip-exports.mjs`):
   - Removes `export {};` module boundaries
   - Normalizes indentation (4-space → 2-space)
   - Copies `manifest.json` to output

Output: Ready-to-run JavaScript in `skills/`

## Creating a New Skill

1. Create directory: `mkdir src/my-skill`
2. Create `manifest.json` with skill metadata (see [`example-skill`](src/example-skill/) for reference)
3. Create `index.ts` with lifecycle hooks and tools
4. Optionally add `package.json` for npm dependencies
5. Build: `yarn build`
6. Validate: `yarn validate`
7. Test: `yarn test src/my-skill/__tests__/test-my-skill.ts`

## Key Constraints

- **TypeScript only** — All skills are written in TypeScript, compiled to JavaScript
- **QuickJS runtime** — Skills run in a sandboxed QuickJS environment
- **Synchronous execution** — No async/await; `net.fetch()` is synchronous with timeout
- **JSON string results** — Tools must return JSON strings, not objects
- **6-field cron** — Cron expressions include seconds: `sec min hour day month dow`
- **SQL params required** — Always use `?` placeholders, never string interpolation
- **No underscores in skill names** — Use lowercase-hyphens (e.g., `my-skill`)
- **Isolated data** — Skills cannot access other skills' databases or data directories

## Contributing

1. Fork and clone
2. `yarn install`
3. Create your skill in `src/` (see [`example-skill`](src/example-skill/) for a complete reference)
4. `yarn build && yarn typecheck`
5. `yarn validate` (must pass)
6. Add tests and run `yarn test`
7. Submit a pull request
