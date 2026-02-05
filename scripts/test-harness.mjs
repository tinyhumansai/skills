#!/usr/bin/env node
/**
 * test-harness.mjs - Simple test harness for QuickJS skills
 *
 * This harness provides mock implementations of the QuickJS bridge APIs
 * and runs basic verification tests on bundled skills.
 */
import { existsSync, readdirSync, readFileSync } from 'fs';
import { basename, dirname, join } from 'path';
import { fileURLToPath } from 'url';
import vm from 'vm';

const __dirname = dirname(fileURLToPath(import.meta.url));
const rootDir = join(__dirname, '..');
const skillsDir = join(rootDir, 'skills');

// Colors for output
const colors = {
  red: '\x1b[31m',
  green: '\x1b[32m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m',
  reset: '\x1b[0m',
};

// Test state
let testsPassed = 0;
let testsFailed = 0;
const errors = [];

// Mock state for bridge APIs
let mockState = {
  store: {},
  db: { tables: {}, data: {} },
  stateValues: {},
  cronSchedules: {},
  notifications: [],
  fetchResponses: {},
  fetchErrors: {},
  dataFiles: {},
  env: {},
  platformOs: 'macos',
};

function resetMockState() {
  mockState = {
    store: {},
    db: { tables: {}, data: {} },
    stateValues: {},
    cronSchedules: {},
    notifications: [],
    fetchResponses: {},
    fetchErrors: {},
    dataFiles: {},
    env: {},
    platformOs: 'macos',
  };
}

// Create mock bridge APIs
function createBridgeAPIs() {
  return {
    // Store API
    store: {
      get: key => mockState.store[key] ?? null,
      set: (key, value) => {
        mockState.store[key] = value;
      },
      delete: key => {
        delete mockState.store[key];
      },
      keys: () => Object.keys(mockState.store),
    },

    // Database API
    db: {
      exec: (sql, params = []) => {
        // Simple CREATE TABLE tracking
        const createMatch = sql.match(/CREATE TABLE IF NOT EXISTS (\w+)/i);
        if (createMatch) {
          mockState.db.tables[createMatch[1]] = { columns: [], rows: [] };
        }
        // Track INSERT
        const insertMatch = sql.match(/INSERT INTO (\w+)/i);
        if (insertMatch) {
          const table = mockState.db.tables[insertMatch[1]];
          if (table) {
            table.rows.push({ params, sql });
          }
        }
      },
      get: (sql, params = []) => {
        return null; // Simplified - return null for now
      },
      all: (sql, params = []) => {
        return []; // Simplified - return empty array
      },
      kvGet: key => mockState.store[`kv:${key}`] ?? null,
      kvSet: (key, value) => {
        mockState.store[`kv:${key}`] = value;
      },
    },

    // State API
    state: {
      get: key => mockState.stateValues[key],
      set: (key, value) => {
        mockState.stateValues[key] = value;
      },
      setPartial: obj => {
        Object.assign(mockState.stateValues, obj);
      },
    },

    // Cron API
    cron: {
      register: (id, schedule) => {
        mockState.cronSchedules[id] = schedule;
      },
      unregister: id => {
        delete mockState.cronSchedules[id];
      },
      list: () =>
        Object.keys(mockState.cronSchedules).map(id => ({
          id,
          schedule: mockState.cronSchedules[id],
        })),
    },

    // Platform API
    platform: {
      os: () => mockState.platformOs,
      env: key => mockState.env[key] ?? null,
      notify: (title, body) => {
        mockState.notifications.push({ title, body });
      },
    },

    // Network API
    net: {
      fetch: (url, options = {}) => {
        if (mockState.fetchErrors[url]) {
          throw new Error(mockState.fetchErrors[url]);
        }
        const response = mockState.fetchResponses[url] || { status: 200, body: '{}', headers: {} };
        return { status: response.status, headers: response.headers || {}, body: response.body };
      },
    },

    // Data API
    data: {
      read: filename => mockState.dataFiles[filename] ?? null,
      write: (filename, content) => {
        mockState.dataFiles[filename] = content;
      },
    },

    // Skills API
    skills: { list: () => [], callTool: () => null },

    // Console
    console: {
      log: (...args) => {
        /* silent */
      },
      warn: (...args) => {
        /* silent */
      },
      error: (...args) => {
        /* silent */
      },
    },
  };
}

// Test a skill bundle
function testSkill(skillDir, skillName) {
  console.log(`\n${colors.blue}Testing skill: ${skillName}${colors.reset}`);

  const indexPath = join(skillDir, 'index.js');
  const manifestPath = join(skillDir, 'manifest.json');

  // Check files exist
  if (!existsSync(indexPath)) {
    console.log(`  ${colors.red}✗${colors.reset} index.js not found`);
    testsFailed++;
    return;
  }

  if (!existsSync(manifestPath)) {
    console.log(`  ${colors.red}✗${colors.reset} manifest.json not found`);
    testsFailed++;
    return;
  }
  console.log(`  ${colors.green}✓${colors.reset} Files exist`);
  testsPassed++;

  // Load manifest
  let manifest;
  try {
    manifest = JSON.parse(readFileSync(manifestPath, 'utf-8'));
    console.log(`  ${colors.green}✓${colors.reset} Manifest is valid JSON`);
    testsPassed++;
  } catch (e) {
    console.log(`  ${colors.red}✗${colors.reset} Invalid manifest: ${e.message}`);
    testsFailed++;
    return;
  }

  // Validate manifest
  if (!manifest.id || !manifest.name || !manifest.version) {
    console.log(`  ${colors.red}✗${colors.reset} Manifest missing required fields`);
    testsFailed++;
    return;
  }
  console.log(
    `  ${colors.green}✓${colors.reset} Manifest has required fields (id: ${manifest.id}, version: ${manifest.version})`
  );
  testsPassed++;

  // Load and evaluate skill
  resetMockState();
  const bridgeAPIs = createBridgeAPIs();

  try {
    const code = readFileSync(indexPath, 'utf-8');

    // Create a sandboxed context with bridge APIs
    const sandbox = {
      ...bridgeAPIs,
      globalThis: {},
      Buffer: globalThis.Buffer,
      Uint8Array: globalThis.Uint8Array,
      ArrayBuffer: globalThis.ArrayBuffer,
      TextEncoder: globalThis.TextEncoder,
      TextDecoder: globalThis.TextDecoder,
      crypto: globalThis.crypto,
      // Browser globals that gramjs expects
      window: {
        location: {
          protocol: 'https:',
          hostname: 'localhost',
          port: '',
          href: 'https://localhost/',
        },
        WebSocket: class MockWebSocket {
          constructor() {
            this.readyState = 0;
          }
          send() {}
          close() {}
        },
      },
      location: { protocol: 'https:', hostname: 'localhost', port: '', href: 'https://localhost/' },
      WebSocket: class MockWebSocket {
        constructor() {
          this.readyState = 0;
        }
        send() {}
        close() {}
      },
      navigator: { userAgent: 'QuickJSTestHarness' },
      setTimeout: fn => {
        return 1;
      },
      clearTimeout: () => {},
      setInterval: fn => {
        return 1;
      },
      clearInterval: () => {},
      Date,
      JSON,
      Object,
      Array,
      String,
      Number,
      Boolean,
      Math,
      Error,
      TypeError,
      ReferenceError,
      Map,
      Set,
      WeakMap,
      WeakSet,
      Promise,
      RegExp,
      Symbol,
      BigInt,
      parseInt,
      parseFloat,
      isNaN,
      isFinite,
      encodeURIComponent,
      decodeURIComponent,
      btoa: str => Buffer.from(str, 'binary').toString('base64'),
      atob: str => Buffer.from(str, 'base64').toString('binary'),
    };

    // Make globalThis self-referential, but preserve window.location
    const windowLocation = sandbox.window.location;
    const windowWebSocket = sandbox.window.WebSocket;
    sandbox.globalThis = sandbox;
    sandbox.self = sandbox;
    // Keep window as a proper object with location
    sandbox.window = { ...sandbox, location: windowLocation, WebSocket: windowWebSocket };

    // Pre-declare skill globals that will be assigned by the skill code
    sandbox.tools = [];
    sandbox.init = undefined;
    sandbox.start = undefined;
    sandbox.stop = undefined;
    sandbox.onCronTrigger = undefined;
    sandbox.onSessionStart = undefined;
    sandbox.onSessionEnd = undefined;
    sandbox.onSetupStart = undefined;
    sandbox.onSetupSubmit = undefined;
    sandbox.onSetupCancel = undefined;
    sandbox.onDisconnect = undefined;
    sandbox.onListOptions = undefined;
    sandbox.onSetOption = undefined;

    const context = vm.createContext(sandbox);

    // Run the skill code
    vm.runInContext(code, context, { filename: indexPath, timeout: 30000 });

    console.log(`  ${colors.green}✓${colors.reset} Skill code evaluates without errors`);
    testsPassed++;

    // Check lifecycle hooks are exported
    const hooks = ['init', 'start', 'stop'];
    let hasHooks = true;
    for (const hook of hooks) {
      if (typeof sandbox.globalThis[hook] === 'function') {
        console.log(`  ${colors.green}✓${colors.reset} ${hook}() exported`);
        testsPassed++;
      } else {
        console.log(`  ${colors.yellow}○${colors.reset} ${hook}() not found (optional)`);
      }
    }

    // Check tools
    if (Array.isArray(sandbox.globalThis.tools)) {
      console.log(
        `  ${colors.green}✓${colors.reset} tools array exported (${sandbox.globalThis.tools.length} tools)`
      );
      testsPassed++;

      // List tools
      for (const tool of sandbox.globalThis.tools) {
        if (tool.name && tool.description && typeof tool.execute === 'function') {
          console.log(`    - ${tool.name}`);
        }
      }
    } else {
      console.log(`  ${colors.yellow}○${colors.reset} tools array not found`);
    }

    // Try calling init()
    if (typeof sandbox.globalThis.init === 'function') {
      try {
        sandbox.globalThis.init();
        console.log(`  ${colors.green}✓${colors.reset} init() runs without error`);
        testsPassed++;
      } catch (e) {
        console.log(`  ${colors.red}✗${colors.reset} init() threw: ${e.message}`);
        testsFailed++;
        errors.push({ skill: skillName, error: `init() error: ${e.message}` });
      }
    }
  } catch (e) {
    console.log(`  ${colors.red}✗${colors.reset} Failed to evaluate skill: ${e.message}`);
    testsFailed++;
    errors.push({ skill: skillName, error: e.message });
    if (e.stack) {
      console.log(`    ${e.stack.split('\n').slice(0, 3).join('\n    ')}`);
    }
  }
}

// Main
console.log(
  `${colors.yellow}═══════════════════════════════════════════════════════════════${colors.reset}`
);
console.log(
  `${colors.yellow}                 QuickJS Skills Test Harness                    ${colors.reset}`
);
console.log(
  `${colors.yellow}═══════════════════════════════════════════════════════════════${colors.reset}`
);

// Find and test skills
const specificSkill = process.argv[2];

if (!existsSync(skillsDir)) {
  console.log(
    `\n${colors.red}Error: skills directory not found. Run 'yarn build' first.${colors.reset}`
  );
  process.exit(1);
}

const skillDirs = readdirSync(skillsDir, { withFileTypes: true })
  .filter(d => d.isDirectory())
  .map(d => d.name);

if (skillDirs.length === 0) {
  console.log(`\n${colors.red}Error: No skills found. Run 'yarn build' first.${colors.reset}`);
  process.exit(1);
}

for (const skillName of skillDirs) {
  if (specificSkill && skillName !== specificSkill) {
    continue;
  }
  testSkill(join(skillsDir, skillName), skillName);
}

// Summary
console.log(
  `\n${colors.yellow}═══════════════════════════════════════════════════════════════${colors.reset}`
);
console.log(
  `${colors.yellow}                        Summary                                ${colors.reset}`
);
console.log(
  `${colors.yellow}═══════════════════════════════════════════════════════════════${colors.reset}`
);
console.log(`  ${colors.green}Passed: ${testsPassed}${colors.reset}`);
console.log(`  ${colors.red}Failed: ${testsFailed}${colors.reset}`);

if (errors.length > 0) {
  console.log(`\n${colors.red}Errors:${colors.reset}`);
  for (const { skill, error } of errors) {
    console.log(`  - ${skill}: ${error}`);
  }
}

process.exit(testsFailed > 0 ? 1 : 0);
