// Ambient type declarations for the AlphaHuman V8 skill runtime.
// These match the friendly API layer injected by v8_skill_instance.rs.

// ---------------------------------------------------------------------------
// Bridge namespaces
// ---------------------------------------------------------------------------

/** SQLite database scoped to this skill. */
declare const db: {
  /** Execute a SQL statement (INSERT, UPDATE, DELETE, CREATE, etc.). */
  exec(sql: string, params?: unknown[]): void;
  /** Query a single row. Returns the row object or `null`. */
  get(sql: string, params?: unknown[]): Record<string, unknown> | null;
  /** Query multiple rows. Returns an array of row objects. */
  all(sql: string, params?: unknown[]): Record<string, unknown>[];
  /** Get a value from the built-in key-value table. */
  kvGet(key: string): unknown;
  /** Set a value in the built-in key-value table. */
  kvSet(key: string, value: unknown): void;
};

/** Persistent key-value store scoped to this skill. */
declare const store: {
  /** Get a value by key. Returns the parsed value or `null`. */
  get(key: string): unknown;
  /** Set a value by key (JSON-serializable). */
  set(key: string, value: unknown): void;
  /** Delete a key. */
  delete(key: string): void;
  /** List all keys. */
  keys(): string[];
};

/** HTTP networking. */
declare const net: {
  /** Synchronous HTTP fetch. Returns the parsed response. */
  fetch(url: string, options?: NetFetchOptions): NetFetchResponse;
};

/** Cron scheduling. */
declare const cron: {
  /** Register a cron schedule. `cronExpr` uses 6-field syntax (seconds). */
  register(scheduleId: string, cronExpr: string): void;
  /** Unregister a previously registered schedule. */
  unregister(scheduleId: string): void;
  /** List all registered schedules for this skill. */
  list(): string[];
};

/** Inter-skill communication. */
declare const skills: {
  /** List all registered skills. */
  list(): SkillInfo[];
  /** Call a tool exposed by another skill. */
  callTool(skillId: string, toolName: string, args?: Record<string, unknown>): unknown;
};

/** Platform information and OS integration. */
declare const platform: {
  /** Current OS: "windows", "macos", "linux", "android", "ios". */
  os(): string;
  /** Read a whitelisted environment variable. Returns the value or `""`. */
  env(key: string): string;
  /** Send a desktop notification. */
  notify(title: string, body?: string): void;
};

/** Skill state published to the frontend in real time. */
declare const state: {
  /** Get a single state value by key. */
  get(key: string): unknown;
  /** Set a single state value by key. */
  set(key: string, value: unknown): void;
  /** Merge a partial object into the current state. */
  setPartial(partial: Record<string, unknown>): void;
};

/** File I/O in the skill's isolated data directory. */
declare const data: {
  /** Read a file. Returns the content string or `null` if not found. */
  read(filename: string): string | null;
  /** Write a file (creates or overwrites). */
  write(filename: string, content: string): void;
};

// ---------------------------------------------------------------------------
// Tools (assigned by skills on globalThis)
// ---------------------------------------------------------------------------

/** Tool definitions exposed to the AI and other skills. */
declare var tools: ToolDefinition[];

// ---------------------------------------------------------------------------
// Supporting interfaces
// ---------------------------------------------------------------------------

interface ToolDefinition {
  name: string;
  description: string;
  input_schema: ToolInputSchema;
  execute: (args: Record<string, unknown>) => string;
}

interface ToolInputSchema {
  type: 'object';
  properties: Record<string, ToolPropertySchema>;
  required?: string[];
}

interface ToolPropertySchema {
  type: string;
  description?: string;
  enum?: string[];
  default?: unknown;
  items?: { type: string };
}

interface NetFetchOptions {
  method?: string;
  headers?: Record<string, string>;
  body?: string;
  timeout?: number;
}

interface NetFetchResponse {
  status: number;
  headers: Record<string, string>;
  body: string;
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
  placeholder?: string;
  options?: SetupFieldOption[];
}

interface SetupFieldOption {
  label: string;
  value: string;
}

interface SetupFieldError {
  field: string;
  message: string;
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
  description?: string;
  value: unknown;
  options?: SetupFieldOption[];
}

interface SkillInfo {
  id: string;
  name: string;
  version?: string;
  status?: string;
}
