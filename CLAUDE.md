# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Summary

This is the **AlphaHuman Skills** repository — a plugin/extension system for the AlphaHuman AI agent. Skills extend the agent with domain-specific capabilities for the crypto community platform. This repo is a git submodule of the main AlphaHuman Tauri app.

## Architecture

Skills are written in **TypeScript** and compiled to **JavaScript** for execution in a sandboxed **QuickJS** runtime embedded in the Rust host application.

### Directory Structure

```
skills/                          # Repo root
├── src/                         # TypeScript source files
│   ├── example-skill/           # Comprehensive example (kitchen sink)
│   ├── server-ping/             # Server health monitoring skill
│   ├── simple-skill/            # Minimal skill template
│   ├── gmail/                   # Gmail integration
│   ├── notion/                  # Notion API integration
│   └── telegram/                # Telegram integration
├── skills/                      # Compiled JavaScript output (git-ignored)
├── types/
│   └── globals.d.ts             # Ambient type declarations for bridge APIs
├── dev/
│   └── test-harness/            # Node.js test harness (tsx)
│       ├── runner-node.ts       # Test runner
│       ├── bootstrap-node.ts    # Mock bridge APIs
│       ├── live-runner-node.ts  # Live test runner
│       ├── mock-state.ts        # Mock state management
│       └── mock-db.ts           # Mock SQLite database
├── scripts/
│   ├── build-bundle.mjs         # esbuild bundler
│   ├── strip-exports.mjs        # Post-build processing
│   ├── validate.mjs             # Skill validation checks
│   ├── scan-secrets.mjs         # Secret scanner
│   ├── install-skill-deps.mjs   # Per-skill dependency installer
│   └── test-harness.mjs         # Test orchestrator
├── package.json                 # Build scripts
├── tsconfig.json                # Base TypeScript config
├── tsconfig.build.json          # Production build config
└── tsconfig.test.json           # Test build config
```

### Skill Structure

Each skill is a directory under `src/` containing:

- **index.ts** — TypeScript source with lifecycle hooks, tools, and business logic
- **manifest.json** — Metadata (id, name, version, runtime, platforms, setup config)
- \***\*tests**/\*\* _(optional)_ — Unit tests

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

## Build Commands

```bash
# Install dependencies
yarn install

# Full build: clean, install skill deps, compile TypeScript, bundle, post-process
yarn build

# Type checking only (no emit)
yarn typecheck

# Watch mode for development
yarn build:watch

# Validate skills (manifest, secrets, code quality)
yarn validate

# Secret scanning only
yarn validate:secrets

# Run all tests
yarn test

# Run specific test
yarn test src/server-ping/__tests__/test-server-ping.ts

# Lint and format
yarn lint
yarn format:check

# Download local model for inference testing
yarn model:download

# Run test script with real local model
yarn test:model <skill-id> <script-file>
```

## Bridge APIs

Skills have access to these global namespaces (defined in `types/globals.d.ts`):

| Namespace  | Purpose                                   |
| ---------- | ----------------------------------------- |
| `db`       | SQLite database scoped to skill           |
| `store`    | Persistent key-value store                |
| `net`      | HTTP networking (synchronous)             |
| `cron`     | Cron scheduling (6-field syntax)          |
| `skills`   | Inter-skill communication                 |
| `platform` | OS info, env vars, notifications          |
| `state`    | Real-time frontend state publishing       |
| `data`     | File I/O in skill's data directory        |
| `model`    | Local LLM inference (generate, summarize) |

### Database (`db`)

```typescript
db.exec('CREATE TABLE IF NOT EXISTS logs (...)', []);
db.exec('INSERT INTO logs (msg) VALUES (?)', ['hello']);
const row = db.get('SELECT * FROM logs WHERE id = ?', [1]);
const rows = db.all('SELECT * FROM logs LIMIT 10', []);
db.kvSet('key', { any: 'value' });
const value = db.kvGet('key');
```

### Store (`store`)

```typescript
store.set('config', { apiKey: 'xxx' });
const config = store.get('config');
store.delete('config');
const keys = store.keys();
```

### HTTP (`net`)

```typescript
const response = net.fetch('https://api.example.com/data', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ query: 'test' }),
  timeout: 10000,
});
// response: { status: number, headers: Record<string, string>, body: string }
```

### Cron (`cron`)

```typescript
// 6-field syntax: seconds minutes hours day month dow
cron.register('every-10s', '*/10 * * * * *');
cron.unregister('every-10s');
const schedules = cron.list();
```

### State (`state`)

```typescript
state.set('status', 'healthy');
state.setPartial({ lastPing: Date.now(), uptime: 99.9 });
const status = state.get('status');
```

### Data (`data`)

```typescript
data.write('config.json', JSON.stringify(config, null, 2));
const content = data.read('config.json'); // null if not found
```

### Model (`model`)

```typescript
// Check if a local model is available
const available = model.isAvailable();
const status = model.getStatus(); // { available, loaded, loading, downloaded, error? }

// Generate text from a prompt
const response = model.generate('What is Bitcoin?', {
  maxTokens: 200, // default: 2048
  temperature: 0.7, // default: 0.7
  topP: 0.9, // default: 0.9
});

// Summarize a block of text
const summary = model.summarize(longText, { maxTokens: 100 });
```

### Platform (`platform`)

```typescript
const os = platform.os(); // "windows", "macos", "linux", "android", "ios"
const apiKey = platform.env('MY_API_KEY');
platform.notify('Title', 'Body');
```

### Skills Interop (`skills`)

```typescript
const allSkills = skills.list();
const result = skills.callTool('other-skill', 'tool-name', { arg: 'value' });
```

## Lifecycle Hooks

Skills implement these functions (all synchronous):

```typescript
function init(): void; // Load config, create DB tables
function start(): void; // Register cron schedules, begin work
function stop(): void; // Cleanup, persist state
function onCronTrigger(scheduleId: string): void; // Handle cron triggers
function onSessionStart(args: { sessionId: string }): void; // User started conversation
function onSessionEnd(args: { sessionId: string }): void; // Conversation ended
function onSetupStart(): SetupStartResult; // Return first setup step
function onSetupSubmit(args): SetupSubmitResult; // Process setup step
function onSetupCancel(): void; // Cleanup on cancel
function onDisconnect(): void; // User disconnected skill
function onListOptions(): { options: SkillOption[] }; // Runtime options
function onSetOption(args: { name: string; value: unknown }): void;
```

### Lifecycle Flow

```
Skill Load ── init()
                │
        ┌── start()
        │       │
        │   onCronTrigger(scheduleId) ← fires on schedule
        │       │
        │   onSessionStart/End
        │       │
        └── stop()
```

## Tool Registration

Tools are exposed to the AI via the global `tools` array:

```typescript
tools = [
  {
    name: 'get-status',
    description: 'Get current skill status',
    input_schema: {
      type: 'object',
      properties: {
        format: { type: 'string', enum: ['json', 'text'], description: 'Output format' },
      },
      required: [],
    },
    execute(args): string {
      // Must return JSON string
      return JSON.stringify({ status: 'ok', uptime: 99.9 });
    },
  },
];
```

**Important**: Tool `execute` functions must return **JSON strings**, not objects.

## Setup Flow

Multi-step configuration wizard:

```typescript
function onSetupStart(): SetupStartResult {
  return {
    step: {
      id: "credentials",
      title: "API Credentials",
      description: "Enter your credentials",
      fields: [
        { name: "apiKey", type: "password", label: "API Key", required: true },
        { name: "region", type: "select", label: "Region", options: [...] },
      ],
    },
  };
}

function onSetupSubmit(args: { stepId: string; values: Record<string, unknown> }): SetupSubmitResult {
  if (args.stepId === "credentials") {
    if (!args.values.apiKey) {
      return { status: "error", errors: [{ field: "apiKey", message: "Required" }] };
    }
    // Multi-step: return next step
    return { status: "next", nextStep: { id: "step2", ... } };
    // Or complete:
    return { status: "complete" };
  }
}
```

Field types: `text`, `password`, `number`, `select`, `boolean`.

## Options System

Runtime-configurable settings:

```typescript
function onListOptions(): { options: SkillOption[] } {
  return {
    options: [
      {
        name: 'interval',
        type: 'select',
        label: 'Check Interval',
        value: String(CONFIG.interval),
        options: [
          { label: 'Every 10s', value: '10' },
          { label: 'Every 30s', value: '30' },
        ],
      },
    ],
  };
}

function onSetOption(args: { name: string; value: unknown }): void {
  if (args.name === 'interval') {
    CONFIG.interval = parseInt(args.value as string);
    // Update cron schedule
    cron.unregister('work');
    cron.register('work', `*/${CONFIG.interval} * * * * *`);
  }
}
```

## Testing

Tests use a Node.js harness (tsx) with mocked bridge APIs.

### Test Structure

```typescript
// src/my-skill/__tests__/test-my-skill.ts

function freshInit(overrides?: Partial<Config>): void {
  setupSkillTest({
    storeData: { config: { ...defaultConfig, ...overrides } },
    fetchResponses: { 'https://api.example.com': { status: 200, body: '{"ok":true}' } },
  });
  init();
}

_describe('My Skill', () => {
  _it('should initialize', () => {
    freshInit();
    _assertNotNull(store.get('config'));
  });

  _it('should call API', () => {
    freshInit({ apiKey: 'test' });
    start();
    const result = callTool('get-status', {});
    _assertEqual(result.status, 'ok');
  });
});
```

### Test Helpers

```typescript
setupSkillTest(options?: {
  storeData?: Record<string, unknown>;
  fetchResponses?: Record<string, { status: number; body: string }>;
  env?: Record<string, string>;
  platformOs?: string;
});

callTool(name: string, args?: Record<string, unknown>): unknown;
getMockState(): { store, fetchCalls, notifications, cronSchedules, ... };
mockFetchResponse(url: string, status: number, body: string): void;
mockFetchError(url: string, message?: string): void;
```

### Running Tests

```bash
# Run all tests
yarn test

# Run specific test
yarn test src/server-ping/__tests__/test-server-ping.ts

# Compile only (for debugging)
npx tsc -p tsconfig.test.json
```

## Creating a New Skill

1. Create directory: `mkdir src/my-skill`

2. Create `manifest.json`:

```json
{
  "id": "my-skill",
  "name": "My Skill",
  "runtime": "quickjs",
  "entry": "index.js",
  "version": "1.0.0",
  "description": "What this skill does",
  "platforms": ["windows", "macos", "linux"]
}
```

3. Create `index.ts` with lifecycle hooks and tools

4. (Optional) Add per-skill dependencies by creating a `package.json` in your skill directory:

```json
{
  "name": "@alphahuman/skill-my-skill",
  "private": true,
  "dependencies": { "some-library": "^1.0.0" }
}
```

Only `dependencies` are bundled — esbuild inlines them into the single output file.

5. Build, validate, and test:

```bash
yarn build
yarn typecheck
yarn validate
yarn test src/my-skill/__tests__/test-my-skill.ts
```

See [`src/example-skill/`](src/example-skill/) for a complete working example demonstrating all bridge APIs, lifecycle hooks, setup wizard, options, and tools.

## Key Constraints

- **TypeScript only** — Skills are TypeScript compiled to JavaScript
- **QuickJS runtime** — Sandboxed JS environment with bridge APIs
- **Synchronous execution** — No async/await; `net.fetch()` is sync with timeout
- **JSON string results** — Tool execute functions must return JSON strings
- **6-field cron** — Cron includes seconds: `sec min hour day month dow`
- **SQL params required** — Always use `?` placeholders, never interpolation
- **No underscores in skill names** — Use lowercase-hyphens (e.g., `my-skill`)
- **Isolated data** — Skills cannot access other skills' databases or files
- **Globals via globalThis** — Tools must access shared state via `globalThis.getSkillState()`, not bare variable names (see Skill State Management pattern)

## Build Process

1. **Install skill dependencies**: `node scripts/install-skill-deps.mjs`
   - Runs `yarn install` in each `src/<skill>/` that has a `package.json`

2. **TypeScript Compilation**: `tsc -p tsconfig.build.json`
   - Input: `src/*/index.ts`
   - Output: `skills/*/index.js`

3. **esbuild Bundling**: `node scripts/build-bundle.mjs`
   - Bundles each skill into a single IIFE file with all dependencies inlined

4. **Post-Processing** (`strip-exports.mjs`):
   - Removes `export {};` module boundaries
   - Normalizes indentation (4-space → 2-space)
   - Copies `manifest.json` to output

5. **Output**: Ready-to-run JavaScript in `skills/`

## Common Patterns

### Skill State Management (Recommended Pattern)

For skills with tools that need to access mutable state, use the **globalThis state pattern**. This ensures state is accessible in both the production QuickJS runtime and the test harness.

**1. Create a `skill-state.ts` module:**

```typescript
// skill-state.ts
import type { SkillConfig } from './types';

export interface MySkillState {
  config: SkillConfig;
  counter: number;
  isRunning: boolean;
}

// Extend globalThis type
declare global {
  function getSkillState(): MySkillState;
  var __skillState: MySkillState;
}

// Initialize state on module load
const state: MySkillState = {
  config: { serverUrl: '', interval: 30 },
  counter: 0,
  isRunning: false,
};
globalThis.__skillState = state;

// Expose getter function globally
globalThis.getSkillState = function (): MySkillState {
  return globalThis.__skillState;
};
```

**2. Access state via `globalThis.getSkillState()` everywhere:**

```typescript
// In index.ts
import './skill-state';

// Initializes state

function init(): void {
  const s = globalThis.getSkillState();
  const saved = store.get('config');
  if (saved) s.config = { ...s.config, ...saved };
}

function doPing(): void {
  const s = globalThis.getSkillState();
  s.counter++;
  // ... use s.config, s.counter, etc.
}
```

**3. Tools access state the same way:**

```typescript
// In tools/get-stats.ts
import '../skill-state';

// Ensures initialization

export const getStatsTool: ToolDefinition = {
  name: 'get-stats',
  execute(): string {
    const s = globalThis.getSkillState();
    return JSON.stringify({ counter: s.counter });
  },
};
```

**4. Expose helper functions on globalThis for tools:**

```typescript
// In index.ts - expose functions for tools to call
const _g = globalThis as Record<string, unknown>;
_g.doPing = doPing;
_g.publishState = publishState;

// In tools that call these functions
(globalThis as { doPing?: () => void }).doPing?.();
```

**Why this pattern?**

- Bundled skills use esbuild IIFE format, which creates module-local scopes
- The test harness uses `new Function()` which has its own scope limitations
- Accessing state via `globalThis.getSkillState()` works in both environments
- The production Rust QuickJS runtime handles this correctly via `execute_script`

### Config Persistence (Simple Pattern)

For simple skills without tools that need state access:

```typescript
interface SkillConfig {
  serverUrl: string;
  interval: number;
}

const CONFIG: SkillConfig = { serverUrl: '', interval: 30 };

function init(): void {
  const saved = store.get('config') as Partial<SkillConfig> | null;
  if (saved) {
    CONFIG.serverUrl = saved.serverUrl ?? CONFIG.serverUrl;
    CONFIG.interval = saved.interval ?? CONFIG.interval;
  }
}

function stop(): void {
  store.set('config', CONFIG);
}
```

### API Integration

```typescript
function callApi(endpoint: string, data?: unknown): unknown {
  try {
    const response = net.fetch(`https://api.example.com${endpoint}`, {
      method: data ? 'POST' : 'GET',
      headers: { Authorization: `Bearer ${CONFIG.apiKey}`, 'Content-Type': 'application/json' },
      body: data ? JSON.stringify(data) : undefined,
      timeout: 10000,
    });

    if (response.status >= 400) {
      throw new Error(`API error: ${response.status}`);
    }

    return JSON.parse(response.body);
  } catch (e) {
    console.error(`API call failed: ${e}`);
    throw e;
  }
}
```

### State Publishing

```typescript
function publishState(): void {
  state.setPartial({
    status: isHealthy ? 'healthy' : 'down',
    lastCheck: new Date().toISOString(),
    uptime: calculateUptime(),
    errorCount: FAIL_COUNT,
  });
}
```

### Error Handling with Notifications

```typescript
function onCronTrigger(scheduleId: string): void {
  if (scheduleId === 'health-check') {
    try {
      const result = checkHealth();
      if (!result.ok && CONFIG.notifyOnError) {
        platform.notify('Health Check Failed', result.message);
      }
    } catch (e) {
      console.error(`Health check error: ${e}`);
      if (CONFIG.notifyOnError) {
        platform.notify('Health Check Error', String(e));
      }
    }
  }
}
```

## Type Definitions

All bridge API types are in `types/globals.d.ts`. Key interfaces:

```typescript
interface ToolDefinition {
  name: string;
  description: string;
  input_schema: ToolInputSchema;
  execute: (args: Record<string, unknown>) => string;
}

interface SetupStep {
  id: string;
  title: string;
  description: string;
  fields: SetupField[];
}

interface SetupField {
  name: string;
  type: 'text' | 'select' | 'boolean' | 'number' | 'password';
  label: string;
  description?: string;
  required?: boolean;
  default?: unknown;
  options?: SetupFieldOption[];
}

interface SetupStartResult {
  step: SetupStep;
}

interface SetupSubmitResult {
  status: 'next' | 'complete' | 'error';
  nextStep?: SetupStep;
  errors?: SetupFieldError[];
}

interface SkillOption {
  name: string;
  type: 'boolean' | 'text' | 'number' | 'select';
  label: string;
  value: unknown;
  options?: SetupFieldOption[];
}
```

## Legacy Python Skills

The `skills-py/` directory contains legacy Python skills that are being migrated to TypeScript. Do not create new Python skills — all new skills should be TypeScript.
