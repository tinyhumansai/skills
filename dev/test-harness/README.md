# Skill Test Harness & REPL

Interactive testing tools for developing and debugging AlphaHuman skills outside the Tauri runtime.

## Quick Start

```bash
# Build skills first (required before any testing)
yarn build

# Launch the interactive REPL
yarn repl

# Run unit tests (mocked APIs, fast)
yarn test

# Run a live test script against a skill
yarn test:script <skill-id> <script-file>
```

## Testing Modes

The test harness provides three distinct modes, each suited to a different stage of development.

### 1. Interactive REPL (Live Mode)

The REPL drops you into a live session with a loaded skill. You get real HTTP requests, a persistent SQLite database, and real environment variables. State persists across commands and even across REPL restarts.

```bash
# Pick a skill interactively
yarn repl

# Load a specific skill directly
yarn repl notion

# Wipe stored data and start fresh
yarn repl notion --clean
```

On startup, the REPL will:
1. Prompt you to select a skill (or use the one you specified)
2. Ask for a backend URL and JWT token (press Enter to use defaults from `.env`)
3. Load the compiled skill and call `init()` + `start()`
4. Auto-detect if setup is required and offer to run the setup wizard or OAuth flow

**REPL Commands:**

| Command | Description |
|---|---|
| `help` | Show all available commands |
| `tools` | List the skill's registered tools with their parameters |
| `call <tool> [json]` | Execute a tool. Omit the JSON to get interactive prompts for each argument |
| `init` / `start` / `stop` | Trigger lifecycle hooks manually |
| `cron` | List registered cron schedules |
| `cron <id>` | Fire a specific cron trigger |
| `session start [id]` | Trigger `onSessionStart` |
| `session end [id]` | Trigger `onSessionEnd` |
| `setup` | Run the form-based setup wizard |
| `oauth` | Run the OAuth authorization flow |
| `options` | List runtime-configurable options |
| `option <name> <value>` | Change a runtime option |
| `state` | Inspect the skill's published state |
| `store` | Inspect the key-value store |
| `db <sql>` | Run a SQL query against the skill's database |
| `env <key> <value>` | Set an environment variable for the session |
| `backend [path]` | Show backend info, or GET a backend endpoint |
| `socket` | Show Socket.io connection status |
| `emit <event> [json]` | Emit a Socket.io event |
| `disconnect` | Call `onDisconnect()` |
| `reload` | Hot-reload the skill (stop, re-read code, init, start) |
| `exit` | Clean shutdown |

**Example session:**

```
$ yarn repl server-ping

  Available skills:
    1) Gmail (gmail)
    2) Notion (notion)
    3) Server Ping (server-ping)

  Select skill (1-3): 3

  Backend URL (https://api.alphahuman.xyz):
  JWT Token:

  Loading server-ping...
  Loaded Server Ping v1.0.0
    3 tools available
  init() ok
  start() ok

  Type 'help' for commands.

server-ping> tools
  get-status (format)
    Get the current server ping status
  do-ping (url)
    Ping a URL and return the result
  get-stats ()
    Get ping statistics

server-ping> call do-ping {"url": "https://httpbin.org/get"}
  Result:
  { "ok": true, "status": 200, "latency": 342 }

server-ping> state
  { "status": "healthy", "lastPing": "2026-02-06T12:00:00Z", "uptime": 99.9 }

server-ping> cron health-check
  onCronTrigger("health-check") completed

server-ping> store
  { "config": { "serverUrl": "https://httpbin.org", "interval": 30 } }

server-ping> exit
  Shutting down...
  stop() ok
  Bye!
```

### 2. Unit Tests (Mocked Mode)

Fast, isolated tests that run with fully mocked bridge APIs. No network calls, no disk I/O. Ideal for CI and rapid iteration.

```bash
# Run all unit tests
yarn test

# Run tests for a specific skill
yarn test src/server-ping/__tests__/test-server-ping.ts
```

Tests live in `src/<skill>/__tests__/` and use the built-in assertion helpers:

```typescript
const _describe = (globalThis as any).describe;
const _it = (globalThis as any).it;
const _assertEqual = (globalThis as any).assertEqual;
const _assertNotNull = (globalThis as any).assertNotNull;
const _setup = (globalThis as any).setupSkillTest;
const _callTool = (globalThis as any).callTool;

_describe('My Skill', () => {
  _it('should initialize with default config', () => {
    _setup({ storeData: { config: { apiKey: 'test-key' } } });
    (globalThis as any).init();
    _assertNotNull(store.get('config'));
  });

  _it('should call the API', () => {
    _setup({
      fetchResponses: {
        'https://api.example.com/status': { status: 200, body: '{"ok":true}' },
      },
    });
    (globalThis as any).init();
    const result = _callTool('get-status', { format: 'json' });
    _assertEqual(result.ok, true);
  });
});
```

**What you can mock:**

| Option | Purpose |
|---|---|
| `storeData` | Pre-populate the key-value store |
| `fetchResponses` | Map URLs to canned HTTP responses |
| `fetchErrors` | Map URLs to network errors |
| `env` | Set environment variables |
| `platformOs` | Override `platform.os()` return value |
| `dataFiles` | Pre-populate filesystem files |
| `modelResponses` | Mock local LLM responses by prompt substring |
| `modelAvailable` | Control whether `model.isAvailable()` returns true |
| `oauthCredential` | Provide a mock OAuth credential |
| `oauthFetchResponses` | Mock `oauth.fetch()` responses |

### 3. Live Script Runner

Run a JavaScript test script against a skill with real HTTP, a persistent SQLite database, and real platform APIs. Useful for integration testing and debugging flows that involve actual network calls.

```bash
# Run a test script
yarn test:script server-ping scripts/examples/test-server-ping.js

# Clean persisted data before running
yarn test:script notion scripts/examples/test-notion.js --clean

# Async-capable runner (for skills using timers/WebSocket)
yarn test:live telegram scripts/examples/test-telegram.js --wait=5000
```

**Available helpers in test scripts:**

```javascript
// Call a tool by name
const result = callTool('get-status', { format: 'json' });

// Trigger lifecycle events
triggerCron('health-check');
triggerSetupStart();
triggerSetupSubmit('credentials', { apiKey: 'xxx' });
triggerSessionStart('session-123');
triggerSessionEnd('session-123');

// Timer management
const timers = listTimers();
triggerTimer(timerId);

// Tool inspection
const toolNames = listTools();

// Mock HTTP (override real curl for specific URLs)
__mockFetch('https://api.example.com', { status: 200, body: '{"ok":true}' });
__mockFetchError('https://api.example.com', 'Connection refused');

// State inspection
const liveState = __getLiveState();
__resetLiveState();

// Environment
__setEnv('API_KEY', 'test-value');
```

## Persistent Data

The REPL and live script runner store data in `skills/<skill-id>/data/`:

```
skills/<skill-id>/data/
  skill.db        # SQLite database (better-sqlite3)
  store.json      # Key-value store
  state.json      # Published frontend state
  files/           # Filesystem I/O (data.read/write)
```

Use `--clean` to wipe this directory and start fresh. Data persists across REPL restarts, which is useful for testing setup flows or accumulated state.

## Environment Variables

The test harness reads from `.env` at the repo root. Useful variables:

| Variable | Purpose |
|---|---|
| `BACKEND_URL` / `VITE_BACKEND_URL` | Backend API URL (REPL default) |
| `JWT_TOKEN` / `VITE_DEV_JWT_TOKEN` | Auth token for backend/OAuth flows |

Skill-specific variables (e.g. API keys) can also be placed in `.env` and accessed via `platform.env('KEY')` in live mode.

## When to Use What

| Scenario | Mode | Command |
|---|---|---|
| Rapid iteration on tool logic | Unit tests | `yarn test` |
| Debugging a setup wizard | REPL | `yarn repl my-skill --clean` |
| Testing OAuth integration | REPL | `yarn repl gmail` then `oauth` |
| Verifying real HTTP calls work | Live script | `yarn test:script my-skill test.js` |
| Testing cron-triggered behavior | REPL | `yarn repl my-skill` then `cron <id>` |
| Checking published state shape | REPL | `yarn repl my-skill` then `state` |
| Inspecting database contents | REPL | `yarn repl my-skill` then `db SELECT * FROM logs` |
| CI pipeline | Unit tests | `yarn test` |
| Testing with a local LLM | Model runner | `yarn test:model my-skill test.js` |
