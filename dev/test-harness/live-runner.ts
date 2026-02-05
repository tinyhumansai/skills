#!/usr/bin/env -S deno run --allow-read --allow-env --allow-net
/**
 * live-runner.ts - V8 Skill Script Runner with REAL network support
 *
 * Unlike the regular runner.ts which mocks network calls, this runner
 * allows real async operations and network connections. Use this for
 * testing skills that require live connections (e.g., Telegram).
 *
 * Usage:
 *   deno run --allow-read --allow-env --allow-net dev/test-harness/live-runner.ts <skill-id> <script-file>
 *   yarn test:live <skill-id> <script-file>
 *
 * Environment Variables (for Telegram):
 *   TELEGRAM_SESSION    - (Optional) Saved session string for auth
 *
 * Example:
 *   yarn test:live telegram scripts/examples/test-telegram-flow.js
 */

import { getMockState, initMockState } from './mock-state.ts';

// Colors for terminal output
const colors = {
  red: '\x1b[31m',
  green: '\x1b[32m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m',
  cyan: '\x1b[36m',
  magenta: '\x1b[35m',
  reset: '\x1b[0m',
  dim: '\x1b[2m',
};

function printBanner(): void {
  console.log(`${colors.magenta}═══════════════════════════════════════════════════════════════${colors.reset}`);
  console.log(`${colors.magenta}           V8 Skill Live Runner (Real Network)                 ${colors.reset}`);
  console.log(`${colors.magenta}═══════════════════════════════════════════════════════════════${colors.reset}`);
}

function printUsage(): void {
  console.log(`
${colors.yellow}Usage:${colors.reset}
  deno run --allow-read --allow-env --allow-net dev/test-harness/live-runner.ts <skill-id> <script-file>

${colors.yellow}Arguments:${colors.reset}
  skill-id      The skill directory name (e.g., "telegram")
  script-file   Path to a JavaScript test script

${colors.yellow}Environment Variables (Telegram):${colors.reset}
  TELEGRAM_API_ID     Your Telegram API ID
  TELEGRAM_API_HASH   Your Telegram API Hash
  TELEGRAM_SESSION    (Optional) Session string for authenticated calls

${colors.yellow}Examples:${colors.reset}
  TELEGRAM_API_ID=12345 TELEGRAM_API_HASH=abc... deno run --allow-all dev/test-harness/live-runner.ts telegram scripts/examples/test-telegram-flow.js

${colors.yellow}Note:${colors.reset}
  This runner executes async code and makes real network connections.
  The script should export an async 'main' function or use top-level await.
`);
}

async function main(): Promise<void> {
  printBanner();

  const args = Deno.args;
  if (args.length < 2) {
    printUsage();
    Deno.exit(1);
  }

  const skillId = args[0];
  const scriptFile = args[1];

  // Resolve paths
  const scriptDir = new URL('.', import.meta.url).pathname;
  const rootDir = scriptDir.replace(/\/dev\/test-harness\/?$/, '');

  // Check script exists
  let resolvedScriptPath = scriptFile;
  if (!scriptFile.startsWith('/')) {
    resolvedScriptPath = `${rootDir}/${scriptFile}`;
  }

  try {
    await Deno.stat(resolvedScriptPath);
  } catch {
    console.error(`${colors.red}Error: Script file not found: ${resolvedScriptPath}${colors.reset}`);
    Deno.exit(1);
  }

  console.log(`${colors.blue}Skill: ${skillId}${colors.reset}`);
  console.log(`${colors.dim}Script: ${resolvedScriptPath}${colors.reset}`);

  // Check for required environment variables for Telegram
  if (skillId === 'telegram') {
    const apiId = Deno.env.get('TELEGRAM_API_ID');
    const apiHash = Deno.env.get('TELEGRAM_API_HASH');

    if (!apiId || !apiHash) {
      console.error(`\n${colors.red}Error: Telegram credentials required${colors.reset}`);
      console.error(`${colors.yellow}Set environment variables:${colors.reset}`);
      console.error(`  TELEGRAM_API_ID=your_api_id`);
      console.error(`  TELEGRAM_API_HASH=your_api_hash`);
      console.error(`\n${colors.dim}Get credentials from https://my.telegram.org${colors.reset}`);
      Deno.exit(1);
    }

    console.log(`${colors.green}✓${colors.reset} Telegram credentials found`);

    const session = Deno.env.get('TELEGRAM_SESSION');
    if (session) {
      console.log(`${colors.green}✓${colors.reset} Session string provided (will attempt authenticated calls)`);
    } else {
      console.log(`${colors.yellow}!${colors.reset} No session string (will test unauthenticated calls only)`);
    }
  }

  // Initialize mock state for bridge APIs that we do mock
  initMockState();
  const mockState = getMockState();

  // Create bridge APIs with real network
  const bridgeAPIs = createLiveBridgeAPIs(mockState);

  // Load and execute the test script as a module
  console.log(`\n${colors.yellow}═══════════════════════════════════════════════════════════════${colors.reset}`);
  console.log(`${colors.yellow}                    Running Live Test Script                    ${colors.reset}`);
  console.log(`${colors.yellow}═══════════════════════════════════════════════════════════════${colors.reset}\n`);

  try {
    // Import the script as a module - this allows async/await
    const scriptUrl = new URL(`file://${resolvedScriptPath}`);
    const scriptModule = await import(scriptUrl.href);

    // If the script exports a main function, call it with bridge APIs
    if (typeof scriptModule.default === 'function') {
      await scriptModule.default(bridgeAPIs);
    } else if (typeof scriptModule.main === 'function') {
      await scriptModule.main(bridgeAPIs);
    }

    console.log(`\n${colors.green}═══════════════════════════════════════════════════════════════${colors.reset}`);
    console.log(`${colors.green}                    Script Completed Successfully              ${colors.reset}`);
    console.log(`${colors.green}═══════════════════════════════════════════════════════════════${colors.reset}`);
  } catch (e) {
    console.error(`\n${colors.red}═══════════════════════════════════════════════════════════════${colors.reset}`);
    console.error(`${colors.red}                    Script Error                               ${colors.reset}`);
    console.error(`${colors.red}═══════════════════════════════════════════════════════════════${colors.reset}`);
    console.error(`${colors.red}${e}${colors.reset}`);
    if (e instanceof Error && e.stack) {
      console.error(`${colors.dim}${e.stack}${colors.reset}`);
    }
    Deno.exit(1);
  }
}

interface MockState {
  store: Record<string, unknown>;
  state: Record<string, unknown>;
  dataFiles: Record<string, string>;
  cronSchedules: Record<string, string>;
  notifications: Array<{ title: string; body?: string }>;
  consoleOutput: Array<{ level: string; message: string }>;
  platformOs: string;
  env: Record<string, string>;
}

/**
 * Create bridge APIs with REAL network support
 */
function createLiveBridgeAPIs(state: MockState): Record<string, unknown> {
  // Store API - uses mock state for persistence during test
  const store = {
    get: (key: string): unknown => state.store[key] ?? null,
    set: (key: string, value: unknown): void => {
      state.store[key] = value;
    },
    delete: (key: string): void => {
      delete state.store[key];
    },
    keys: (): string[] => Object.keys(state.store),
  };

  // Database API - simple in-memory mock
  const dbTables: Record<string, Array<Record<string, unknown>>> = {};
  const db = {
    exec: (sql: string, _params?: unknown[]): void => {
      // Parse CREATE TABLE
      const createMatch = sql.match(/CREATE TABLE IF NOT EXISTS (\w+)/i);
      if (createMatch) {
        const tableName = createMatch[1];
        if (!dbTables[tableName]) {
          dbTables[tableName] = [];
        }
      }
      // Parse INSERT - simplified
      const insertMatch = sql.match(/INSERT INTO (\w+)/i);
      if (insertMatch) {
        // Just acknowledge, actual data not tracked in this simple mock
      }
    },
    get: (_sql: string, _params?: unknown[]): Record<string, unknown> | null => null,
    all: (_sql: string, _params?: unknown[]): Array<Record<string, unknown>> => [],
    kvGet: (key: string): unknown => state.store[`kv:${key}`] ?? null,
    kvSet: (key: string, value: unknown): void => {
      state.store[`kv:${key}`] = value;
    },
  };

  // Platform API - returns real env vars
  const platform = {
    os: (): string => Deno.build.os,
    env: (key: string): string => Deno.env.get(key) ?? '',
    notify: (title: string, body?: string): void => {
      state.notifications.push({ title, body });
      console.log(`[notification] ${title}${body ? ': ' + body : ''}`);
    },
  };

  // State API
  const stateApi = {
    get: (key: string): unknown => state.state[key],
    set: (key: string, value: unknown): void => {
      state.state[key] = value;
    },
    setPartial: (partial: Record<string, unknown>): void => {
      Object.assign(state.state, partial);
    },
  };

  // Data API
  const data = {
    read: (filename: string): string | null => state.dataFiles[filename] ?? null,
    write: (filename: string, content: string): void => {
      state.dataFiles[filename] = content;
    },
  };

  // Cron API
  const cron = {
    register: (scheduleId: string, cronExpr: string): void => {
      state.cronSchedules[scheduleId] = cronExpr;
    },
    unregister: (scheduleId: string): void => {
      delete state.cronSchedules[scheduleId];
    },
    list: (): string[] => Object.keys(state.cronSchedules),
  };

  return {
    store,
    db,
    platform,
    state: stateApi,
    data,
    cron,
    // Environment helper
    getEnv: (key: string): string => Deno.env.get(key) ?? '',
  };
}

main();
