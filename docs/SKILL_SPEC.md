# Skill Integration Guide

Comprehensive reference for building a new skill for the AlphaHuman platform. Each section documents what the file/module does, why it exists, and includes a checklist to verify completeness.

---

## 1. Project Scaffolding

Every skill lives in its own directory under `src/` with a consistent internal layout.

```
src/<skill-name>/
├── manifest.json          # Skill metadata and capabilities declaration
├── index.ts               # Entry point — lifecycle hooks, wires all modules
├── types.ts               # All TypeScript interfaces and type definitions
├── state.ts               # Mutable runtime state via globalThis pattern
├── setup.ts               # Multi-step setup/auth wizard
├── sync.ts                # Data synchronization engine (local + cloud)
├── helpers.ts             # Shared formatting/utility functions
├── update-handlers.ts     # Real-time event dispatch (if applicable)
├── db/
│   ├── schema.ts          # CREATE TABLE / CREATE INDEX statements
│   └── helpers.ts         # Upsert, query, aggregate functions
├── api/
│   ├── index.ts           # Barrel re-export of all API modules
│   ├── client.ts          # Central fetch wrapper with auth injection
│   └── <domain>.ts        # One file per API domain (messages, users, etc.)
├── tools/
│   ├── index.ts           # Barrel re-export of all tool definitions
│   └── <tool-name>.ts     # One file per tool or logical group
├── package.json           # (Optional) Per-skill npm dependencies
└── __tests__/
    └── test-<skill>.ts    # Unit tests
```

### Checklist

- [ ] Create skill directory: `src/<skill-name>/`
- [ ] Create subdirectories: `api/`, `tools/`, `db/`, `__tests__/`
- [ ] Skill name uses lowercase-hyphens (no underscores)
- [ ] (Optional) `package.json` for per-skill npm dependencies — only `dependencies` are bundled

---

## 2. Manifest (`manifest.json`)

The manifest declares the skill's identity, capabilities, and requirements. The host runtime reads this to discover, configure, and manage skills.

### Required Fields

| Field         | Type     | Description                                                            |
| ------------- | -------- | ---------------------------------------------------------------------- |
| `id`          | string   | Unique kebab-case identifier (e.g., `"telegram"`, `"google-calendar"`) |
| `name`        | string   | Human-readable display name (e.g., `"Google Calendar"`)                |
| `version`     | string   | Semver version string (e.g., `"1.0.0"`)                                |
| `description` | string   | One-line summary of what the skill does                                |
| `platforms`   | string[] | Supported platforms: `windows`, `macos`, `linux`, `android`, `ios`     |

### Optional Fields

| Field                | Type     | Description                                                       |
| -------------------- | -------- | ----------------------------------------------------------------- |
| `auto_start`         | boolean  | Start automatically when app launches (default `false`)           |
| `ignoreInProduction` | boolean  | Hide from production builds (for dev/test skills)                 |
| `env`                | string[] | Required environment variable names (e.g., `["TELEGRAM_API_ID"]`) |
| `setup.required`     | boolean  | Whether setup wizard must complete before use                     |
| `setup.label`        | string   | Button label (e.g., `"Connect Notion"`)                           |
| `setup.oauth`        | object   | OAuth config: `{ provider, scopes, apiBaseUrl }`                  |
| `events_emitted`     | array    | Events the skill can emit (see below)                             |

### Events Declaration

Each event includes a type, description, the entity types involved, and a data schema:

```json
{
  "type": "telegram.message.received",
  "description": "A new message was received in any chat",
  "entities": {
    "chat": { "types": ["telegram.group", "telegram.channel"] },
    "sender": { "types": ["telegram.contact"] }
  },
  "data_schema": {
    "text": "string",
    "content_type": "string",
    "chat_id": "string",
    "message_id": "string"
  }
}
```

### Checklist

- [ ] All required fields present (`id`, `name`, `version`, `description`, `platforms`)
- [ ] `setup` section configured if skill needs authentication
- [ ] `setup.oauth` configured if using OAuth flow
- [ ] `events_emitted` declared for each event the skill can fire
- [ ] `env` lists any required environment variables
- [ ] `ignoreInProduction: true` set for dev/test skills

---

## 3. Types (`types.ts`)

Central location for all TypeScript type definitions. No runtime code — only interfaces, types, and enums. This ensures consistent typing across all modules.

### What to Define

| Category                | Examples                                                                      |
| ----------------------- | ----------------------------------------------------------------------------- |
| **Config interface**    | `SkillConfig` — all user-configurable settings (API keys, toggles, intervals) |
| **Permission flags**    | `allowWriteActions`, `allowGroupAdminActions`, `showSensitiveMessages`        |
| **API response types**  | One per external API object (page, message, user, etc.)                       |
| **Database row types**  | One per SQLite table (`ChatRow`, `MessageRow`, `PageRow`)                     |
| **Domain enums/unions** | Chat types, status codes, content types                                       |
| **Query result types**  | Extended row types for joined queries (`MessageWithSender`)                   |
| **State interfaces**    | `SyncState`, `StorageStats`, `Cache`                                          |

### Checklist

- [ ] Config interface with all user-configurable settings
- [ ] Permission flag types (read/write/admin access levels)
- [ ] API response types for each external service object
- [ ] Database row types matching table schemas
- [ ] Domain-specific enums (status codes, entity types)
- [ ] All types exported; no runtime code in this file

---

## 4. State Management (`state.ts`)

Defines and initializes the skill's mutable runtime state. Uses the `globalThis` pattern so state is accessible across all modules in both the bundled IIFE (production) and the test harness.

### State Structure

Every skill state should cover these concerns:

```typescript
interface SkillState {
  // Persisted configuration
  config: SkillConfig;

  // In-memory cache (current user, entity lists, timestamps)
  cache: { me: User | null; items: Item[]; lastSync: number };

  // Client/connection (reference to API client, connection flags)
  client: ApiClient | null;
  clientConnecting: boolean;
  clientError: string | null;

  // Authentication stage
  authState: 'ready' | 'authenticating' | 'waitCode' | 'waitPassword' | 'unknown';

  // Sync tracking
  sync: {
    inProgress: boolean;
    completed: boolean;
    lastSyncTime: number;
    nextSyncTime: number;
    lastSyncDurationMs: number;
    error: string | null;
  };

  // Entity counts for status reporting
  storage: { itemCount: number; userCount: number; unreadCount: number };
}
```

### globalThis Registration

```typescript
globalThis.__mySkillState = skillState;
globalThis.getMySkillState = function (): MySkillState {
  return globalThis.__mySkillState;
};
```

### Checklist

- [ ] `SkillState` interface defined with config, cache, client, auth, sync, storage sections
- [ ] **Permission flags** included in config (see section 4a)
- [ ] State initialized with sensible defaults
- [ ] `globalThis.get<SkillName>State()` accessor registered
- [ ] `globalThis.__<skillName>State` set for direct access
- [ ] Works in both esbuild IIFE and test harness

---

## 4a. Permission & Access Control Flags

Skills must define explicit permission flags that gate write, admin, and sensitive operations. These flags default to `false` (read-only) and the user must opt-in via skill options.

### Permission Tiers

| Flag                   | Default | Gates                                                                              | Example                                                         |
| ---------------------- | ------- | ---------------------------------------------------------------------------------- | --------------------------------------------------------------- |
| `allowReadActions`     | `true`  | Read-only tools (search, list, get)                                                | Always enabled                                                  |
| `allowWriteActions`    | `false` | Tools that create/modify data (send message, create page, edit)                    | Telegram: send-message, edit-message, delete-messages           |
| `allowAdminActions`    | `false` | Destructive or privileged operations (ban users, delete chats, change permissions) | Telegram: ban-chat-member, promote-member, set-chat-permissions |
| `showSensitiveContent` | `false` | Display filtered content (OTP codes, passwords, financial data)                    | Telegram: messages containing verification codes                |

### How Tools Enforce Permissions

Every write/admin tool must check the relevant flag before executing:

```typescript
execute(args: Record<string, unknown>): string {
  const s = globalThis.getMySkillState();
  if (!s.config.allowWriteActions) {
    return JSON.stringify({
      success: false,
      error: 'Write actions are disabled. Enable "Allow Write Actions" in skill options.',
    });
  }
  // ... proceed with write operation
}
```

For admin tools:

```typescript
if (!s.config.allowAdminActions) {
  return JSON.stringify({
    success: false,
    error: 'Admin actions are disabled. Enable "Allow Admin Actions" in skill options.',
  });
}
```

### How Read Tools Filter Sensitive Content

```typescript
const showSensitive = s.config.showSensitiveContent ?? false;
const filtered = showSensitive
  ? allResults
  : allResults.filter(item => !isSensitiveText(item.text || ''));
```

### Checklist

- [ ] Permission flags defined in config (defaulting to restrictive)
- [ ] Every write tool checks `allowWriteActions` before executing
- [ ] Every admin/destructive tool checks `allowAdminActions` before executing
- [ ] Read tools filter sensitive content unless `showSensitiveContent` is enabled
- [ ] Permission errors return clear, actionable messages telling users how to enable
- [ ] Permissions exposed via `onListOptions()` (see section 12)

---

## 5. Database Schema (`db/schema.ts`)

Defines all SQLite tables, indexes, and migrations. Called once during `init()` to ensure the schema exists. Uses `CREATE TABLE IF NOT EXISTS` for idempotency.

### Common Table Patterns

| Table                  | Purpose                               | Example                               |
| ---------------------- | ------------------------------------- | ------------------------------------- |
| **Primary entities**   | Main objects from the API             | `chats`, `pages`, `files`             |
| **Secondary entities** | Nested/related objects                | `messages`, `blocks`, `database_rows` |
| **Users/contacts**     | People associated with entities       | `contacts`, `users`                   |
| **Summaries**          | AI-generated summaries for cloud sync | `summaries` (with `synced` flag)      |

### Design Rules

- **SQLite is for entity data only** — large, queryable datasets (emails, messages, pages, contacts). Do NOT store sync metadata (last sync time, sync completed flags, history cursors) in SQLite. Use the `state` bridge API (`state.get()`/`state.set()`) for all sync state — it is already persistent and published to the frontend.
- Primary keys: `TEXT` for external IDs (API IDs may exceed JS integer range), composite keys for junction tables
- Every table gets `created_at` and `updated_at` timestamp columns
- Soft-delete via `is_deleted INTEGER DEFAULT 0` instead of SQL DELETE
- Index frequently queried columns (`updated_at`, `type`, foreign keys)
- Use `?` parameter placeholders — never string interpolation

### Registration

```typescript
globalThis.initializeMySkillSchema = initializeSchema;
```

### Checklist

- [ ] `CREATE TABLE IF NOT EXISTS` for each entity table
- [ ] `CREATE INDEX IF NOT EXISTS` for frequently queried columns
- [ ] Primary keys defined (TEXT for external IDs, composite where needed)
- [ ] `created_at` and `updated_at` on all tables
- [ ] **No `sync_state` table** — use `state.get()`/`state.set()` for sync metadata
- [ ] `summaries` table with `synced` flag if skill produces AI summaries
- [ ] Registered on `globalThis.initialize<SkillName>Schema()`
- [ ] All SQL uses parameterized queries

---

## 6. Database Helpers (`db/helpers.ts`)

CRUD and query functions for all tables. Each function encapsulates a specific database operation. Registered on `globalThis.<skillName>Db.*` for cross-module access.

### Function Categories

#### Upsert Functions

One per entity table. Uses `INSERT ... ON CONFLICT DO UPDATE` to handle both new inserts and updates:

```typescript
function upsertPage(page: ApiPage): void {
  db.exec(`INSERT INTO pages (...) VALUES (?, ?, ...)
    ON CONFLICT(id) DO UPDATE SET title=?, ...`, [...]);
}
```

#### Update Functions

Granular field updates for real-time events (title changed, status changed, etc.):

```typescript
function updateChatTitle(chatId: string, title: string): void { ... }
function markMessageDeleted(chatId: string, messageId: string): void { ... }
```

#### Query Functions

| Function               | Purpose                              |
| ---------------------- | ------------------------------------ |
| `getById(id)`          | Single entity retrieval              |
| `search(query, limit)` | Full-text search with LIKE           |
| `list(options)`        | Paginated listing with filters       |
| `getEntityCounts()`    | Aggregate stats for status reporting |

#### Summary Functions (for cloud sync)

| Function                      | Purpose                                    |
| ----------------------------- | ------------------------------------------ |
| `insertSummary(opts)`         | Store AI summary with `synced=0`           |
| `getUnsyncedSummaries(limit)` | Batch fetch summaries pending cloud upload |
| `markSummariesSynced(ids)`    | Mark as `synced=1` after successful upload |
| `getSummaryCounts()`          | Total, synced, pending counts              |

#### Utility Functions

| Function                      | Purpose                                          |
| ----------------------------- | ------------------------------------------------ |
| `parseType(apiType)`          | Convert API types → simplified enums             |
| `extractPreview(content)`     | Text preview with emoji prefixes for media types |
| `extractContentType(content)` | Detect content type (text, photo, video, etc.)   |
| `parseStatus(status)`         | API status → display string                      |

### Checklist

- [ ] One upsert function per entity table
- [ ] Granular update functions for individual field changes
- [ ] Soft-delete function (if applicable)
- [ ] Get-by-ID for each entity
- [ ] Search/filter with LIKE queries
- [ ] Paginated list with LIMIT/OFFSET
- [ ] Aggregate stats (`getEntityCounts()`)
- [ ] Summary CRUD functions (insert, get unsynced, mark synced)
- [ ] Type parsers and content extractors
- [ ] All registered on `globalThis.<skillName>Db.*`

---

## 7. API Layer (`api/`)

Pure functions that wrap external API calls. Each domain gets its own file. The client module handles auth injection, error parsing, and rate limiting.

### Client (`api/client.ts`)

Central fetch wrapper that all API functions call:

```typescript
function apiFetch<T>(endpoint: string, options?: RequestOptions): T {
  // 1. Inject auth header (API key, OAuth token, etc.)
  // 2. Set Content-Type and API version headers
  // 3. Execute request with timeout
  // 4. Parse error responses (401, 403, 404, 429)
  // 5. Return parsed response
}
```

**Auth methods to support:**

- **API key/token**: `Authorization: Bearer <token>` header
- **OAuth**: `oauth.fetch()` bridge (token injection handled by platform)
- **Multiple methods**: Detect which is configured and use the appropriate one

**Error handling:**

- 401 → "Unauthorized" (trigger credential revocation)
- 403 → "Forbidden" (permissions issue)
- 404 → "Not found" (share resource with integration)
- 429 → "Rate limited" (respect retry-after)

### Domain Files (one per API domain)

```
api/auth.ts      — authentication/verification
api/messages.ts  — message CRUD
api/chats.ts     — chat/channel operations
api/users.ts     — user/contact operations
api/search.ts    — full-text search
api/members.ts   — group member management
api/media.ts     — file/photo/document operations
```

Each function is a pure function taking explicit parameters and returning a parsed response:

```typescript
export function sendMessage(client: Client, chatId: number, text: string): Message { ... }
export function searchMessages(client: Client, query: string, limit: number): Message[] { ... }
```

### Barrel Export

`api/index.ts` re-exports all functions from all domain files.

### Checklist

- [ ] Central `apiFetch()` or client wrapper with auth injection
- [ ] Multiple auth methods supported if applicable (token vs OAuth)
- [ ] Correct `Content-Type` and API version headers
- [ ] Error response parsing with user-friendly messages
- [ ] Rate limiting detection (429 → retry-after)
- [ ] Timeout configuration on all requests
- [ ] One file per API domain
- [ ] Pure functions with explicit parameters
- [ ] `api/index.ts` barrel re-exports all functions
- [ ] **Verify credentials** endpoint (e.g., `getMe()`, `listUsers(page_size=1)`)
- [ ] Pagination handling (cursor-based or offset-based)

---

## 8. Setup Wizard (`setup.ts`)

Multi-step configuration wizard that guides users through authentication and initial configuration. Supports API key, OAuth, phone+code, and migration flows.

### `onSetupStart()`

Detects current state and returns the appropriate first step:

| Scenario                               | Returned Step                                  |
| -------------------------------------- | ---------------------------------------------- |
| Fresh install, no OAuth available      | `token` step (API key input)                   |
| Fresh install, OAuth available         | `oauth` step (start OAuth flow)                |
| Already connected via OAuth            | `already-connected` step (keep/reconnect)      |
| Legacy token user, OAuth now available | `migrate` step (keep token / upgrade to OAuth) |
| Interrupted auth (mid-flow)            | Resume at `code` or `password` step            |

### `onSetupSubmit(stepId, values)`

Processes each step with validation:

```typescript
// Validation error
return { status: 'error', errors: [{ field: 'token', message: 'Required' }] };

// Multi-step: advance to next step
return { status: 'next', nextStep: { id: 'code', title: '...', fields: [...] } };

// Complete
return { status: 'complete' };
```

### Field Types

| Type       | Use Case                                  |
| ---------- | ----------------------------------------- |
| `password` | API keys, tokens (masked)                 |
| `text`     | Names, labels, URLs                       |
| `select`   | Region, workspace, plan selection         |
| `boolean`  | Feature toggles                           |
| `number`   | Numeric configuration (intervals, limits) |

### Auth Flows

| Flow                   | Steps                                               | Example                              |
| ---------------------- | --------------------------------------------------- | ------------------------------------ |
| **API Key**            | `token` → validate → complete                       | Notion legacy token                  |
| **OAuth**              | `oauth` → `oauth-pending` → complete                | Notion OAuth, Gmail, Google Calendar |
| **Phone + Code + 2FA** | `phone` → `code` → (optional) `password` → complete | Telegram                             |
| **Migration**          | `migrate` → (keep / oauth) → complete               | Token → OAuth upgrade                |

### `onSetupCancel()`

Cleans up partial state, resets pending flags.

### Checklist

- [ ] `onSetupStart()` detects current auth state and returns correct first step
- [ ] Supports resuming interrupted setup (returns mid-flow step)
- [ ] Handles "already connected" scenario (keep/reconnect options)
- [ ] Handles migration from legacy to modern auth
- [ ] Each field has proper validation (required, format, API verification)
- [ ] Returns field-level errors with clear messages
- [ ] Persists config to `state.set('config', ...)` on completion
- [ ] Calls `publishState()` after successful setup
- [ ] `onSetupCancel()` cleans up partial state

---

## 9. Data Sync (`sync.ts`)

Synchronizes data from the external service into the local SQLite database, then optionally pushes processed data (summaries, signals) to the AlphaHuman backend.

### Sync Architecture (Multi-Phase)

The Notion skill demonstrates a production-grade 4-phase sync:

```
Phase 1: Users          → API paginated list → upsert to users table
Phase 2: Primary entities → API search (incremental) → upsert to pages/databases
Phase 2.5: Secondary entities → Per-parent batch query → upsert to database_rows
Phase 3: Content extraction  → Recursive block fetch → update content_text
Phase 4: Cloud sync     → Unsynced summaries → POST to backend → mark synced
```

The Telegram skill demonstrates a real-time sync with event-driven updates:

```
Initial sync: Load chats (100) → Load messages (100/chat, top 20) → Load contacts
Ongoing: TDLib update loop → dispatchUpdate() → upsert to DB per event
```

### Incremental Sync

Avoid re-fetching unchanged data:

```typescript
// Skip items not modified since last sync
if (editedMs <= lastSyncTime) { break; }

// Skip items identical to what's already stored
if (existing && existing.last_edited_time === newLastEdited) { skipped++; continue; }

// 30-day window to manage data volume
if (editedMs < cutoffMs) { break; }
```

### Cloud Sync (Phase 4)

Push processed data to the AlphaHuman backend:

```typescript
// 1. Fetch unsynced summaries from local DB
const summaries = getUnsyncedSummaries(100);

// 2. Transform to submission format
const submission = {
  summary: s.summary,
  url: s.url,
  dataSource: 'notion',
  sentiment: s.sentiment,
  keyPoints: JSON.parse(s.topics),
  entities: JSON.parse(s.entities),
  createdAt: s.sourceCreatedAt,
  updatedAt: s.sourceUpdatedAt,
};

// 3. POST to backend with auth
const response = net.fetch(`${BACKEND_URL}/api/summaries`, {
  method: 'POST',
  headers: { Authorization: `Bearer ${AUTH_TOKEN}`, 'Content-Type': 'application/json' },
  body: JSON.stringify(submission),
  timeout: 10000,
});

// 4. Mark as synced on success
if (response.status < 400) {
  markSummariesSynced([s.id]);
}
```

### Progress Reporting

```typescript
function performInitialSync(client, onProgress?: (msg: string) => void): void {
  onProgress?.('Loading chats...');
  // ... load chats
  onProgress?.(`Synced ${count} chats, loading messages...`);
  // ... load messages
}
```

### Registration

```typescript
globalThis.<skillName>Sync = {
  performInitialSync,
  isSyncCompleted,
  getLastSyncTime,
  incrementalSync,
};
```

### Checklist

- [ ] `performInitialSync()` with paginated entity fetching
- [ ] Upserts each entity to database via `db/helpers.ts`
- [ ] Loads secondary entities for top N primary entities
- [ ] Progress reported via `onProgress()` callback
- [ ] Marks sync as complete via `state.set('initial_sync_completed', true)`
- [ ] Records `last_sync_time` via `state.set('last_sync_time', Date.now())`
- [ ] **Incremental sync** — only fetches changed/new data since last sync
- [ ] **Deduplication** — skips items identical to stored version
- [ ] **Time window** — limits data volume (e.g., last 30 days)
- [ ] **Resilient error handling** — individual failures don't abort batch
- [ ] **Cloud sync phase** — pushes summaries/signals to backend
- [ ] **Backend auth** — uses `BACKEND_URL` and `AUTH_TOKEN` env vars
- [ ] **Batch processing** — fetches unsynced summaries in batches
- [ ] **Sync tracking** — marks summaries as synced after successful upload
- [ ] Post-sync state update (counts, timing, next sync time)
- [ ] Registered on `globalThis.<skillName>Sync.*`

---

## 10. Update/Event Handlers (`update-handlers.ts`)

_Required for real-time integrations (WebSocket, long-polling, push updates). Not needed for poll-only skills._

Processes incoming events from the external service and persists changes to the local database.

### Handler Registry Pattern

```typescript
const handlers: Record<string, (update: any) => void> = {
  updateNewMessage: handleNewMessage,
  updateMessageEdited: handleMessageEdited,
  updateDeleteMessages: handleDeleteMessages,
  updateNewChat: handleNewChat,
  updateChatTitle: handleChatTitle,
  updateUserStatus: handleUserStatus,
  // ... one per update type
};

function dispatchUpdate(update: any): boolean {
  const handler = handlers[update['@type']];
  if (handler) {
    try {
      handler(update);
      return true;
    } catch (err) {
      console.error(`Handler error: ${err}`);
    }
  }
  return false;
}
```

### What Each Handler Does

1. **Persist to DB** — upsert or update the affected entity
2. **Emit event** — fire a skill event via `hooks.emit()` for the broader system
3. **Enrich context** — include sender names, chat titles, content previews in the event payload

### Event Emission Format

```typescript
hooks.emit({
  type: 'telegram.message.received',
  source: 'telegram',
  timestamp: Date.now(),
  entities: {
    chat: { id: chatId, type: 'telegram.group' },
    sender: { id: senderId, type: 'telegram.contact' },
  },
  data: { text, content_type, is_outgoing, chat_id, message_id },
});
```

### Checklist

- [ ] Handler registry maps update types → handler functions
- [ ] `dispatchUpdate()` central dispatcher with error catching
- [ ] Each entity type handled: created → upsert, updated → update fields, deleted → soft-delete
- [ ] Events emitted via `hooks.emit()` matching manifest `events_emitted`
- [ ] Events include entity IDs, types, and enriched context data
- [ ] Registered on `globalThis.<skillName>DispatchUpdate`

---

## 11. Tools (`tools/`)

Tools are the primary interface between the AI and the skill. Each tool defines a name, description, input schema, and execute function. Tools are organized into permission tiers.

### Tool Structure

```typescript
export const myToolDefinition: ToolDefinition = {
  name: 'skill-name-action', // kebab-case, prefixed with skill name
  description: 'Clear description for the AI including when/how to use it.',
  input_schema: {
    type: 'object',
    properties: { param: { type: 'string', description: 'What this param does' } },
    required: ['param'],
  },
  execute(args: Record<string, unknown>): string {
    // 1. Check permissions
    // 2. Validate params
    // 3. Call API
    // 4. Return JSON string
  },
};
```

### Tool Permission Tiers

Organize tools by the permission level they require:

#### Read Tools (no permission check needed)

- **Status** — Skill connection/health/sync status
- **Search** — Full-text search across entities
- **Get by ID** — Single entity retrieval
- **List** — Paginated entity listing
- **Get stats** — Aggregate statistics

#### Write Tools (require `allowWriteActions`)

- **Create** — New entity creation
- **Update/Edit** — Modify existing entity
- **Send** — Post messages, comments, etc.
- **Append** — Add content to existing entity

#### Admin Tools (require `allowAdminActions`)

- **Delete/Archive** — Remove entities
- **Member management** — Add/remove/ban members, change roles
- **Permission changes** — Modify group/channel permissions
- **Settings changes** — Modify entity properties (title, description, etc.)

### Execute Function Pattern

```typescript
execute(args: Record<string, unknown>): string {
  try {
    const s = globalThis.getMySkillState();

    // 1. Connection check
    if (!s.client) throw new Error('Not connected. Complete setup first.');

    // 2. Permission check (for write/admin tools)
    if (!s.config.allowWriteActions) {
      return JSON.stringify({
        success: false,
        error: 'Write actions are disabled. Enable in skill options.',
      });
    }

    // 3. Parameter validation
    const id = args.id as string;
    if (!id) return JSON.stringify({ error: 'id is required' });

    // 4. API call
    const result = api.doSomething(s.client, id);

    // 5. Success response with context
    return JSON.stringify({ success: true, data: result, count: 1 });
  } catch (err) {
    return JSON.stringify({
      success: false,
      error: err instanceof Error ? err.message : String(err),
    });
  }
}
```

### Sensitive Content Filtering in Read Tools

```typescript
const s = globalThis.getMySkillState();
const showSensitive = s.config.showSensitiveContent ?? false;
const results = showSensitive ? allResults : allResults.filter(r => !isSensitiveText(r.text || ''));
```

### Checklist

- [ ] Each tool has `name`, `description`, `input_schema`, `execute`
- [ ] Tool names are kebab-case, prefixed with skill name
- [ ] Descriptions are clear and actionable for AI
- [ ] `input_schema` has `properties` and `required` arrays
- [ ] `execute` returns JSON strings (not objects)
- [ ] **Connection check** — verifies client exists before API calls
- [ ] **Permission checks** — write tools check `allowWriteActions`, admin tools check `allowAdminActions`
- [ ] **Parameter validation** — required params checked, clear error if missing
- [ ] **Sensitive filtering** — read tools respect `showSensitiveContent` flag
- [ ] **Error handling** — try/catch with `{ success: false, error: "..." }` response
- [ ] **Context in responses** — counts, previews, links, IDs included
- [ ] `tools/index.ts` barrel re-exports all tool definitions

---

## 12. Entry Point (`index.ts`)

The orchestrator that imports all modules, implements lifecycle hooks, and wires everything together.

### Import Order

```typescript
// 4. Sync (registers sync operations)
import * as api from './api';
// 2. DB schema (registers initializeSchema)
import './db/helpers';
// 1. State first (registers globalThis getter)
import './db/schema';
// 5. API layer
import { onSetupStart, onSetupSubmit } from './setup';
import './state';
// 3. DB helpers (registers db operations)
import './sync';
// 6. Setup
import { tool1, tool2 } from './tools';
// 7. Tools
import './update-handlers';

// 8. Update handlers (if applicable)
```

### Lifecycle Hooks

#### `init()`

Called once when the skill is loaded. Sets up database and loads persisted state.

```typescript
function init(): void {
  // 1. Initialize database schema
  globalThis.initializeMySkillSchema();

  // 2. Load persisted config
  const saved = state.get('config');
  if (saved) {
    s.config = { ...s.config, ...saved };
  }

  // 3. Load sync state from database
  s.sync.completed = globalThis.mySkillSync.isSyncCompleted();
  s.sync.lastSyncTime = globalThis.mySkillSync.getLastSyncTime();

  // 4. Update storage stats if sync was completed
  if (s.sync.completed) {
    updateStorageStats();
  }

  // 5. Initialize client (non-blocking)
  initClient();

  // 6. Publish initial state
  publishState();
}
```

#### `start()`

Called when the skill becomes active. Registers schedules and begins work.

```typescript
function start(): void {
  // Register cron for periodic sync
  cron.register('my-sync', `0 */${s.config.syncIntervalMinutes} * * * *`);

  // Trigger initial sync if not yet completed
  if (!s.sync.completed) {
    onSync();
  }

  publishState();
}
```

#### `stop()`

Cleanup when the skill is deactivated.

```typescript
function stop(): void {
  cron.unregister('my-sync');
  // Close client connection
  // Persist current config
  state.set('config', s.config);
  publishState();
}
```

#### `onCronTrigger(scheduleId)`

Handle periodic tasks:

```typescript
function onCronTrigger(scheduleId: string): void {
  if (scheduleId === 'my-sync') {
    try {
      performSync();
      publishState();
    } catch (e) {
      console.error(`Sync error: ${e}`);
      platform.notify('Sync Failed', String(e));
    }
  }
}
```

#### `onListOptions()` — Runtime Configuration

Returns user-configurable options including permission flags:

```typescript
function onListOptions(): { options: SkillOption[] } {
  return {
    options: [
      // Permission flags
      {
        name: 'allowWriteActions',
        type: 'boolean',
        label: 'Allow Write Actions',
        value: s.config.allowWriteActions ?? false,
      },
      {
        name: 'allowAdminActions',
        type: 'boolean',
        label: 'Allow Admin Actions',
        value: s.config.allowAdminActions ?? false,
      },
      {
        name: 'showSensitiveContent',
        type: 'boolean',
        label: 'Show Sensitive Content',
        value: s.config.showSensitiveContent ?? false,
      },
      // Sync settings
      {
        name: 'syncInterval',
        type: 'select',
        label: 'Sync Interval',
        value: String(s.config.syncIntervalMinutes),
        options: [
          { label: 'Every 10 minutes', value: '10' },
          { label: 'Every 20 minutes', value: '20' },
          { label: 'Every 30 minutes', value: '30' },
          { label: 'Every hour', value: '60' },
        ],
      },
    ],
  };
}
```

#### `onSetOption(args)` — Apply Option Changes

Must handle ALL listed options:

```typescript
function onSetOption(args: { name: string; value: unknown }): void {
  const s = globalThis.getMySkillState();
  switch (args.name) {
    case 'allowWriteActions':
      s.config.allowWriteActions = Boolean(args.value);
      break;
    case 'allowAdminActions':
      s.config.allowAdminActions = Boolean(args.value);
      break;
    case 'showSensitiveContent':
      s.config.showSensitiveContent = Boolean(args.value);
      break;
    case 'syncInterval':
      s.config.syncIntervalMinutes = parseInt(args.value as string);
      cron.unregister('my-sync');
      cron.register('my-sync', `0 */${s.config.syncIntervalMinutes} * * * *`);
      break;
  }
  state.set('config', s.config);
  publishState();
}
```

#### `onPing()` — Health Check

Verify connection and credentials are still valid:

```typescript
function onPing(): { ok: boolean; errorType?: string; errorMessage?: string } {
  try {
    const result = api.getMe(s.client);
    return { ok: true };
  } catch (err) {
    return { ok: false, errorType: 'auth', errorMessage: String(err) };
  }
}
```

#### `onDisconnect()` — User Disconnects Skill

Clear all credentials and reset state:

```typescript
function onDisconnect(): void {
  // Revoke OAuth credentials if applicable
  oauth.revoke();
  // Clear config
  s.config = defaultConfig;
  state.set('config', s.config);
  state.delete('config');
  // Unregister schedules
  cron.unregister('my-sync');
  // Publish disconnected state
  publishState();
}
```

#### `onOAuthComplete(args)` / `onOAuthRevoked(args)`

Handle OAuth lifecycle events:

```typescript
function onOAuthComplete(args: { credentialId: string; accountLabel?: string }): void {
  s.config.credentialId = args.credentialId;
  s.config.workspaceName = args.accountLabel || '';
  state.set('config', s.config);
  cron.register('my-sync', `0 */${s.config.syncIntervalMinutes} * * * *`);
  publishState();
}

function onOAuthRevoked(): void {
  s.config.credentialId = '';
  state.delete('config');
  cron.unregister('my-sync');
  publishState();
}
```

### State Publishing (`publishState()`)

Maps internal state to frontend-visible key-value pairs:

```typescript
function publishState(): void {
  const isConnected = /* ... */;
  state.setPartial({
    // Standard fields (all skills must publish these)
    connection_status: isConnected ? 'connected' : 'disconnected',
    auth_status: isAuthenticated ? 'authenticated' : 'not_authenticated',
    connection_error: s.clientError || null,
    is_initialized: isConnected,

    // Sync status
    syncInProgress: s.sync.inProgress,
    syncCompleted: s.sync.completed,
    lastSyncTime: s.sync.lastSyncTime || null,
    nextSyncTime: s.sync.nextSyncTime || null,
    lastSyncError: s.sync.error || null,
    lastSyncDurationMs: s.sync.lastSyncDurationMs || 0,

    // Entity counts
    totalItems: s.storage.itemCount,
    totalUsers: s.storage.userCount,

    // Skill-specific
    workspaceName: s.config.workspaceName || null,
  });
}
```

### Tool Registration

```typescript
tools = [statusTool, searchTool, getByIdTool, createTool, ...allTools];
```

### Checklist

- [ ] Imports in correct order (state → schema → helpers → sync → api → setup → tools)
- [ ] `init()` — schema, load config, load sync state, init client, publish state
- [ ] `start()` — register cron, trigger initial sync if needed
- [ ] `stop()` — unregister cron, close client, persist config
- [ ] `onCronTrigger()` — handle sync and maintenance with error catching
- [ ] `onListOptions()` — returns ALL permission flags and sync settings
- [ ] `onSetOption()` — handles ALL options (not just some)
- [ ] `onPing()` — health check verifying connection and credentials
- [ ] `onDisconnect()` — clears credentials, revokes OAuth, resets state
- [ ] `onOAuthComplete()` / `onOAuthRevoked()` — OAuth lifecycle
- [ ] `onSessionStart()` / `onSessionEnd()` — session tracking (optional)
- [ ] `onError()` — error handling with flag resets
- [ ] `publishState()` — maps state to frontend with standard + skill-specific fields
- [ ] `tools` array assembled from all imported tool definitions
- [ ] Status tool included that reports comprehensive health info

---

## 13. Helper Utilities (`helpers.ts`)

_Optional file for shared utility functions used across multiple modules._

| Function                        | Purpose                       | Example                              |
| ------------------------------- | ----------------------------- | ------------------------------------ |
| `formatRichText(rt)`            | Rich text → plain text        | Notion rich text arrays → string     |
| `formatPageTitle(page)`         | Extract title from properties | Title property → string              |
| `formatEntitySummary(entity)`   | Compact entity representation | `{ id, title, url, type }`           |
| `buildRichText(text)`           | Plain text → rich text format | String → Notion rich text block      |
| `isSensitiveText(text)`         | Detect sensitive content      | OTP codes, passwords, financial data |
| `maskPhoneNumber(phone)`        | Mask for display              | `+1555****123`                       |
| `formatApiError(error)`         | User-friendly error messages  | 429 → "Rate limited. Try again."     |
| `fetchBlockTreeText(id, depth)` | Recursive content extraction  | Block children → plain text lines    |

### Checklist

- [ ] Content formatters (rich text → plain text, markdown)
- [ ] Entity summary formatters (compact representations for tool responses)
- [ ] Sensitive content detection (`isSensitiveText()`)
- [ ] Data masking for display (phone numbers, tokens, keys)
- [ ] API error formatting (status codes → user-friendly messages)
- [ ] Registered on `globalThis` if needed cross-module

---

## 14. Tests (`__tests__/test-<skill>.ts`)

### Test Infrastructure

#### `freshInit(overrides?)` Helper

Resets all mocks and reinitializes the skill:

```typescript
function freshInit(overrides?: {
  config?: Record<string, unknown>;
  fetchResponses?: Record<string, { status: number; body: string }>;
  fetchErrors?: Record<string, string>;
  env?: Record<string, string>;
  oauthAvailable?: boolean;
  oauthCredentials?: Record<string, unknown> | null;
}): void {
  _setup({ stateData: { config: overrides?.config || {} }, ...overrides });
  (globalThis as any).init();
}
```

#### `configuredInit(additionalFetchResponses?)` Helper

Pre-configures with valid credentials:

```typescript
function configuredInitWithToken(extra?) {
  freshInit({
    config: { token: VALID_TOKEN, authMethod: 'token' },
    fetchResponses: { 'api/users/me': { status: 200, body: '...' }, ...extra },
  });
}

function configuredInitWithOAuth(extra?) {
  freshInit({
    config: { authMethod: 'oauth' },
    oauthAvailable: true,
    oauthCredentials: { mySkill: MOCK_OAUTH },
    fetchResponses: { 'api/users/me': { status: 200, body: '...' }, ...extra },
  });
}
```

### Test Categories

#### Initialization Tests

- [ ] Loads config from store when available
- [ ] Handles missing config gracefully (no errors)
- [ ] Detects OAuth credentials on init
- [ ] Prefers OAuth over legacy token when both available
- [ ] Initializes database schema without errors

#### Start/Stop Tests

- [ ] Publishes connected state when configured
- [ ] Does not fail when not configured
- [ ] Registers cron schedules on start
- [ ] Cleans up on stop

#### Setup Flow Tests — Token/API Key Auth

- [ ] Returns correct first step (field names, types)
- [ ] Validates empty/missing credentials
- [ ] Validates credential format (regex patterns like `ntn_*` prefix)
- [ ] Completes with valid credentials
- [ ] Handles unauthorized/invalid credentials (401 from API)
- [ ] Persists config and writes backup file on success

#### Setup Flow Tests — OAuth

- [ ] Returns OAuth step when OAuth available
- [ ] Shows "already connected" when credentials exist
- [ ] Offers migration from legacy to OAuth
- [ ] Handles keep/reconnect actions
- [ ] Starts OAuth flow and returns pending step with flow ID
- [ ] Completes when flow succeeds
- [ ] Errors when flow fails (user denied)
- [ ] Errors when flow expires (timeout)

#### Disconnect Tests

- [ ] Clears legacy token config
- [ ] Revokes OAuth credentials
- [ ] Publishes disconnected state
- [ ] Resets auth method to null

#### API Call Tests

- [ ] Uses correct auth header (token vs OAuth)
- [ ] Handles 401 by revoking credentials and disconnecting

#### Permission Tests

- [ ] Write tools blocked when `allowWriteActions` is false
- [ ] Admin tools blocked when `allowAdminActions` is false
- [ ] Write tools succeed when `allowWriteActions` is true
- [ ] Admin tools succeed when `allowAdminActions` is true
- [ ] Sensitive content filtered when `showSensitiveContent` is false
- [ ] Sensitive content shown when `showSensitiveContent` is true

#### Tool Tests — Per Tool

- [ ] Returns expected data on success
- [ ] Requires connection (errors when not connected)
- [ ] Validates required parameters
- [ ] Handles empty results gracefully
- [ ] Handles API errors (4xx, 5xx)
- [ ] Filters/paginates correctly

#### Tool Tests — Read Operations

- [ ] Search returns matching results with count
- [ ] Filter by type/category works
- [ ] Get by ID returns entity details
- [ ] Get by ID validates ID parameter
- [ ] List returns array with count
- [ ] Stats return aggregate numbers

#### Tool Tests — Write Operations

- [ ] Create returns success with created entity
- [ ] Create validates required fields
- [ ] Update/edit modifies entity
- [ ] Delete/archive marks entity correctly
- [ ] Append/add content works

#### Sync Tests

- [ ] Initial sync loads all primary entities
- [ ] Incremental sync fetches only changes
- [ ] Sync marks completion in database
- [ ] Sync handles API errors gracefully
- [ ] Cloud sync sends summaries to backend
- [ ] Cloud sync marks summaries as synced

#### Update Handler Tests _(real-time integrations)_

- [ ] New entity event → upserts to DB
- [ ] Entity updated event → updates DB fields
- [ ] Entity deleted event → soft-deletes in DB
- [ ] Events emit with correct payload shape

---

## 15. Build & Validation

- [ ] `yarn build` compiles without errors
- [ ] `yarn typecheck` passes
- [ ] `yarn validate` passes (manifest checks, code quality)
- [ ] `yarn validate:secrets` passes (no secrets in source)
- [ ] `yarn test src/<skill>/__tests__/test-<skill>.ts` — all tests pass
- [ ] Output in `skills/<skill-name>/` contains `index.js` and `manifest.json`
- [ ] Bundled JS is a single IIFE file with no external imports

---

## 16. Final Review

### Code Quality

- [ ] All tool execute functions return JSON strings
- [ ] All SQL uses parameterized queries
- [ ] No hardcoded secrets or API keys
- [ ] No dynamic imports
- [ ] Error messages are user-friendly and actionable

### Permission Completeness

- [ ] All write tools gate on `allowWriteActions`
- [ ] All admin tools gate on `allowAdminActions`
- [ ] All read tools respect `showSensitiveContent`
- [ ] `onListOptions()` exposes all permission flags
- [ ] `onSetOption()` handles ALL options (not a subset)
- [ ] Permission error messages tell the user how to enable

### State Consistency

- [ ] State published to frontend after every meaningful change
- [ ] Config persisted after every modification
- [ ] Database updated in sync with API responses
- [ ] Disconnect clears all credentials and resets state
- [ ] `publishState()` includes standard fields (`connection_status`, `auth_status`, `is_initialized`)

### Sync Completeness

- [ ] Initial sync loads comprehensive data set
- [ ] Incremental sync respects `lastSyncTime`
- [ ] Deduplication skips unchanged entities
- [ ] Time window limits data volume
- [ ] Cloud sync pushes summaries/signals to backend
- [ ] Sync errors don't abort the entire batch
- [ ] Post-sync state includes counts, timing, next sync time

### API Robustness

- [ ] All API calls have timeout set
- [ ] Rate limiting detected and handled (429)
- [ ] Auth expiry triggers credential revocation
- [ ] Network errors produce clear error messages
- [ ] Pagination loops have safety limits (max iterations)

### User Experience

- [ ] Setup wizard has clear labels and descriptions
- [ ] Setup validates input before making API calls
- [ ] Setup allows resuming interrupted flows
- [ ] Tools have descriptive names and descriptions for AI
- [ ] Tool responses include counts, previews, links
- [ ] Status tool reports comprehensive health info
- [ ] `platform.notify()` sent for critical errors

---

_Last updated: 2026-02-11_
_Derived from: `src/telegram/` (v2.0.0) and `src/notion/` (v1.1.0) reference implementations_
