#!/usr/bin/env tsx
/**
 * repl-node.ts - Interactive REPL for skill testing (live mode)
 *
 * Loads a compiled skill and provides an interactive prompt to call tools,
 * lifecycle hooks, walk through setup wizards, and inspect state.
 *
 * Uses real HTTP (via curl), persistent SQLite, and real platform APIs.
 * For unit testing with mocked APIs, use the test harness (yarn test) instead.
 *
 * Usage:
 *   yarn repl [skill-id] [--clean]
 *   npx tsx dev/test-harness/repl-node.ts [skill-id] [--clean]
 */

import * as readline from 'readline/promises';
import { existsSync, readFileSync, readdirSync, rmSync } from 'fs';
import { resolve, dirname } from 'path';
import { fileURLToPath } from 'url';
import vm from 'vm';
import { config as loadDotenv } from 'dotenv';
import { createBridgeAPIs, getLiveState } from './bootstrap-live';
import { createGhostInput, type SuggestionSource } from './ghost-input';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const rootDir = resolve(__dirname, '../..');

// Load .env from the repo root
loadDotenv({ path: resolve(rootDir, '.env') });

const c = {
  red: '\x1b[31m',
  green: '\x1b[32m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m',
  cyan: '\x1b[36m',
  magenta: '\x1b[35m',
  bold: '\x1b[1m',
  dim: '\x1b[2m',
  reset: '\x1b[0m',
};

/** Validates that s is a MongoDB ObjectId (24 hex chars). Rejects values like "oauth" that cause CastError. */
function isValidIntegrationId(s: string): boolean {
  return /^[a-f0-9]{24}$/i.test(s);
}

// ─── Types ─────────────────────────────────────────────────────────

interface Manifest {
  id: string;
  name: string;
  version: string;
  description?: string;
  setup?: {
    required?: boolean;
    label?: string;
    oauth?: {
      provider: string;
      scopes: string[];
      apiBaseUrl: string;
    };
  };
}

interface ToolDef {
  name: string;
  description: string;
  input_schema: {
    type: string;
    properties?: Record<string, {
      type?: string;
      description?: string;
      enum?: string[];
      default?: unknown;
    }>;
    required?: string[];
  };
  execute: (args: Record<string, unknown>) => string | Promise<string>;
}

interface SetupField {
  name: string;
  type: 'text' | 'password' | 'number' | 'select' | 'boolean';
  label: string;
  description?: string;
  required?: boolean;
  default?: unknown;
  options?: Array<{ label: string; value: string }>;
}

interface SetupStep {
  id: string;
  title: string;
  description: string;
  fields: SetupField[];
}

// The global context shared between REPL and skill code
type G = Record<string, unknown>;

// ─── Helpers ───────────────────────────────────────────────────────

function prettyJson(value: unknown): string {
  const json = JSON.stringify(value, null, 2);
  // Colorize keys and strings lightly
  return json
    .replace(/"([^"]+)":/g, `${c.cyan}"$1"${c.reset}:`)
    .replace(/: "(.*?)"/g, `: ${c.green}"$1"${c.reset}`);
}

function discoverSkills(): Array<{ id: string; manifest: Manifest }> {
  const skillsDir = resolve(rootDir, 'skills');
  if (!existsSync(skillsDir)) return [];
  const entries = readdirSync(skillsDir, { withFileTypes: true });
  const result: Array<{ id: string; manifest: Manifest }> = [];
  for (const entry of entries) {
    if (!entry.isDirectory()) continue;
    const manifestPath = resolve(skillsDir, entry.name, 'manifest.json');
    const indexPath = resolve(skillsDir, entry.name, 'index.js');
    if (existsSync(manifestPath) && existsSync(indexPath)) {
      try {
        const manifest = JSON.parse(readFileSync(manifestPath, 'utf-8'));
        result.push({ id: entry.name, manifest });
      } catch {
        // skip malformed manifests
      }
    }
  }
  return result.sort((a, b) => a.id.localeCompare(b.id));
}

// ─── Skill Loader ──────────────────────────────────────────────────

function runInContext(G: G, code: string): void {
  // Use vm.createContext for QuickJS-like sandboxing.
  // All properties on G become globals in the sandbox context.
  // The skill code accesses bridge APIs (state, db, net, oauth, etc.)
  // directly as globals, matching QuickJS runtime behavior.
  const context = vm.createContext(G);
  vm.runInContext(code, context, { filename: 'skill.js', timeout: 30000 });
}

function extractSkillExports(G: G): void {
  // Pattern 1: skill uses export default { tools, init, ... } → stored in __skill.default
  const skillExport = G.__skill as { default?: Record<string, unknown> } | undefined;
  const skill = skillExport?.default;
  const hooks = [
    'init', 'start', 'stop', 'onCronTrigger', 'onSync', 'onSetupStart',
    'onSetupSubmit', 'onSetupCancel', 'onDisconnect',
    'onSessionStart', 'onSessionEnd', 'onListOptions', 'onSetOption',
    'onOAuthComplete', 'onOAuthRevoked', 'onHookTriggered',
  ];
  if (skill) {
    if (skill.tools) G.tools = skill.tools;
    for (const hook of hooks) {
      if (skill[hook] && !G[hook]) G[hook] = skill[hook];
    }
  }

  // Pattern 2: skill puts hooks on globalThis via _g.init = init etc.
  // (already on G since G is the vm context — no extra work needed for hooks)

  // Fix tools array: esbuild CommonJS interop can leave tool references undefined
  // when __esm wrappers create isolated module scopes. Tools end up on the outer
  // 'exports' object instead. Rebuild from exports if tools has undefined entries.
  const tools = G.tools as Array<{ name?: string; execute?: unknown } | undefined> | undefined;
  const hasUndefined = tools && tools.length > 0 && tools.some(t => !t);
  if (hasUndefined || (tools && tools.length === 0 && !skill)) {
    const exports = G.exports as Record<string, { name?: string; execute?: (...args: unknown[]) => string }> | undefined;
    if (exports) {
      const fixedTools: unknown[] = [];
      for (const key of Object.keys(exports)) {
        const val = exports[key];
        if (val && typeof val === 'object' && typeof val.name === 'string' && typeof val.execute === 'function') {
          fixedTools.push(val);
        }
      }
      if (fixedTools.length > 0) {
        G.tools = fixedTools;
      }
    }
  }
}

async function loadSkill(
  skillId: string,
  cleanFlag: boolean,
  connectionOpts?: { jwtToken?: string; backendUrl?: string },
): Promise<{ G: G; manifest: Manifest; cleanup: () => void }> {
  const skillDir = resolve(rootDir, 'skills', skillId);
  const skillIndexPath = resolve(skillDir, 'index.js');
  const skillManifestPath = resolve(skillDir, 'manifest.json');

  if (!existsSync(skillIndexPath)) {
    throw new Error(`Skill "${skillId}" not found at ${skillDir}. Run 'yarn build' first.`);
  }

  const manifest: Manifest = JSON.parse(readFileSync(skillManifestPath, 'utf-8'));
  const dataDir = resolve(rootDir, 'data', skillId);

  if (cleanFlag && existsSync(dataDir)) {
    rmSync(dataDir, { recursive: true, force: true });
    console.log(`${c.yellow}Cleaned data directory${c.reset}`);
  }

  // Create live bridge APIs (real HTTP, persistent storage, real platform APIs)
  const bridgeAPIs = await createBridgeAPIs({
    dataDir,
    jwtToken: connectionOpts?.jwtToken,
    backendUrl: connectionOpts?.backendUrl,
  });

  const G: G = { ...bridgeAPIs };
  G.globalThis = G;
  G.self = G;
  G.window = G;
  G.__helpers = { getLiveState };

  if (bridgeAPIs.WebSocket) {
    // @ts-ignore
    globalThis.WebSocket = bridgeAPIs.WebSocket;
    // @ts-ignore
    globalThis.window = globalThis;
  }

  const skillCode = readFileSync(skillIndexPath, 'utf-8');
  runInContext(G, skillCode);
  extractSkillExports(G);

  const cleanup = () => {
    if (typeof bridgeAPIs.__cleanup === 'function') {
      (bridgeAPIs.__cleanup as () => void)();
    }
  };

  return { G, manifest, cleanup };
}

// ─── Setup Wizard ──────────────────────────────────────────────────

async function runSetupWizard(G: G, rl: readline.Interface): Promise<void> {
  const onSetupStart = G.onSetupStart as (() => { step: SetupStep }) | undefined;
  const onSetupSubmit = G.onSetupSubmit as ((args: {
    stepId: string;
    values: Record<string, unknown>;
  }) => { status: string; nextStep?: SetupStep; errors?: Array<{ field: string; message: string }> } | Promise<{ status: string; nextStep?: SetupStep; errors?: Array<{ field: string; message: string }> }>) | undefined;

  if (!onSetupStart) {
    console.log(`${c.yellow}This skill does not implement onSetupStart${c.reset}`);
    return;
  }

  console.log(`\n${c.magenta}${c.bold}Setup Wizard${c.reset}`);
  console.log(`${c.dim}${'─'.repeat(50)}${c.reset}`);

  let result = onSetupStart();
  let step = result.step;

  while (step) {
    console.log(`\n${c.bold}${step.title}${c.reset}`);
    if (step.description) console.log(`${c.dim}${step.description}${c.reset}\n`);

    const values: Record<string, unknown> = {};

    for (const field of step.fields) {
      const value = await promptField(field, rl);
      values[field.name] = value;
    }

    if (!onSetupSubmit) {
      console.log(`${c.yellow}onSetupSubmit not implemented${c.reset}`);
      return;
    }

    const submitResult = await onSetupSubmit({ stepId: step.id, values });

    if (submitResult.status === 'error') {
      console.log(`\n${c.red}Setup errors:${c.reset}`);
      for (const err of submitResult.errors ?? []) {
        console.log(`  ${c.red}- ${err.field}: ${err.message}${c.reset}`);
      }
      console.log(`${c.yellow}Re-running step...${c.reset}`);
      // Re-run same step
      continue;
    }

    if (submitResult.status === 'complete') {
      console.log(`\n${c.green}Setup complete!${c.reset}`);
      return;
    }

    if (submitResult.status === 'next' && submitResult.nextStep) {
      step = submitResult.nextStep;
      continue;
    }

    // Unknown status
    console.log(`${c.yellow}Unknown setup status: ${submitResult.status}${c.reset}`);
    return;
  }
}

// ─── OAuth Flow ─────────────────────────────────────────────────

async function runOAuthFlow(
  G: G,
  manifest: Manifest,
  rl: readline.Interface,
  backendUrl: string,
  jwtToken: string,
): Promise<void> {
  const oauthConfig = manifest.setup?.oauth;
  if (!oauthConfig) {
    console.log(`${c.yellow}This skill does not have OAuth configuration in manifest${c.reset}`);
    return;
  }

  console.log(`\n${c.magenta}${c.bold}OAuth Setup${c.reset}`);
  console.log(`${c.dim}${'─'.repeat(50)}${c.reset}`);
  console.log(`  ${c.cyan}Provider${c.reset}: ${oauthConfig.provider}`);
  console.log(`  ${c.cyan}Scopes${c.reset}: ${oauthConfig.scopes.join(', ') || '(default)'}`);
  console.log(`  ${c.cyan}API Base${c.reset}: ${oauthConfig.apiBaseUrl}`);

  if (!jwtToken) {
    console.log(`\n${c.red}No JWT token set. Cannot initiate OAuth flow.${c.reset}`);
    console.log(`${c.dim}Restart the REPL and provide a JWT token to use OAuth.${c.reset}`);
    return;
  }

  // Call backend to get the real OAuth URL
  // GET /auth/:provider/connect (requires JWT auth)
  let oauthUrl: string;
  try {
    console.log(`\n${c.dim}Requesting OAuth URL from backend...${c.reset}`);
    const connectUrl = `${backendUrl}/auth/${oauthConfig.provider}/connect?responseType=json&skillId=${manifest.id}`;
    console.log(`[connectUrl] ${connectUrl}`);
    const resp = await globalThis.fetch(connectUrl, {
      headers: { Authorization: `Bearer ${jwtToken}` },
    });
    if (!resp.ok) {
      const errBody = await resp.text();
      console.log(`${c.red}Backend error (${resp.status}): ${errBody}${c.reset}`);
      return;
    }
    const data = (await resp.json()) as { success?: boolean; oauthUrl?: string; state?: string };
    if (!data.oauthUrl) {
      console.log(`${c.red}Backend did not return an oauthUrl: ${JSON.stringify(data)}${c.reset}`);
      return;
    }
    oauthUrl = data.oauthUrl;
  } catch (e) {
    console.log(`${c.red}Failed to call backend: ${e}${c.reset}`);
    return;
  }

  console.log(`\n${c.bold}Open this URL in your browser to authorize:${c.reset}`);
  console.log(`  ${c.cyan}${oauthUrl}${c.reset}\n`);
  console.log(`${c.dim}After completing authorization, copy the ${c.bold}integrationId${c.reset}${c.dim} from the redirect URL and paste it below.${c.reset}`);
  console.log(`${c.dim}(The redirect URL looks like: .../#auth/${oauthConfig.provider}/success?integrationId=<ID>)${c.reset}\n`);

  const credentialId = await rl.question(`${c.cyan}Integration ID:${c.reset} `);
  const trimmedId = credentialId.trim();
  if (!trimmedId) {
    console.log(`${c.yellow}OAuth setup cancelled (no integration ID provided)${c.reset}`);
    return;
  }
  if (!isValidIntegrationId(trimmedId)) {
    console.log(`${c.red}Invalid integration ID. Expected a 24-character hex string (e.g. 69876e9b6197df74de78d89a), not "${trimmedId}".${c.reset}`);
    return;
  }

  // Set the credential on the bridge
  const oauthApi = G.oauth as { __setCredential?: (cred: unknown) => void } | undefined;
  if (oauthApi?.__setCredential) {
    oauthApi.__setCredential({
      credentialId: trimmedId,
      provider: oauthConfig.provider,
      scopes: oauthConfig.scopes,
      isValid: true,
      createdAt: Date.now(),
    });
  }

  // Call onOAuthComplete on the skill
  const onOAuthComplete = G.onOAuthComplete as ((args: {
    credentialId: string;
    provider: string;
    grantedScopes: string[];
    accountLabel?: string;
  }) => unknown | Promise<unknown>) | undefined;

  if (typeof onOAuthComplete === 'function') {
    try {
      const result = await onOAuthComplete({
        credentialId: trimmedId,
        provider: oauthConfig.provider,
        grantedScopes: oauthConfig.scopes,
      });
      console.log(`${c.green}OAuth complete!${c.reset}`);
      if (result) {
        console.log(prettyJson(result));
      }
    } catch (e) {
      console.log(`${c.red}onOAuthComplete error: ${e}${c.reset}`);
    }
  } else {
    console.log(`${c.yellow}onOAuthComplete not defined — credential set on bridge only${c.reset}`);
  }
}

async function promptField(field: SetupField, rl: readline.Interface): Promise<unknown> {
  const defaultHint = field.default !== undefined ? ` ${c.dim}(default: ${field.default})${c.reset}` : '';
  const requiredHint = field.required ? ` ${c.red}*${c.reset}` : '';
  const label = `${field.label}${requiredHint}${defaultHint}`;

  if (field.description) {
    console.log(`  ${c.dim}${field.description}${c.reset}`);
  }

  switch (field.type) {
    case 'select': {
      const options = field.options ?? [];
      console.log(`  ${label}`);
      for (let i = 0; i < options.length; i++) {
        const isDefault = String(field.default) === options[i].value;
        console.log(`    ${c.cyan}${i + 1}${c.reset}) ${options[i].label}${isDefault ? ` ${c.dim}(default)${c.reset}` : ''}`);
      }
      while (true) {
        const answer = await rl.question(`  ${c.cyan}>${c.reset} `);
        if (answer === '' && field.default !== undefined) return field.default;
        const idx = parseInt(answer, 10);
        if (idx >= 1 && idx <= options.length) return options[idx - 1].value;
        console.log(`  ${c.red}Enter a number 1-${options.length}${c.reset}`);
      }
    }

    case 'boolean': {
      const def = field.default === true;
      const hint = def ? '[Y/n]' : '[y/N]';
      const answer = await rl.question(`  ${label} ${hint}: `);
      if (answer === '') return def;
      return answer.toLowerCase().startsWith('y');
    }

    case 'number': {
      while (true) {
        const answer = await rl.question(`  ${label}: `);
        if (answer === '' && field.default !== undefined) return field.default;
        const num = parseFloat(answer);
        if (!isNaN(num)) return num;
        console.log(`  ${c.red}Enter a valid number${c.reset}`);
      }
    }

    case 'password': {
      console.log(`  ${c.yellow}(input is visible - dev tooling)${c.reset}`);
      const answer = await rl.question(`  ${label}: `);
      if (answer === '' && field.default !== undefined) return field.default;
      return answer;
    }

    case 'text':
    default: {
      const answer = await rl.question(`  ${label}: `);
      if (answer === '' && field.default !== undefined) return field.default;
      return answer;
    }
  }
}

// ─── Interactive Tool Args ─────────────────────────────────────────

async function promptToolArgs(
  tool: ToolDef,
  rl: readline.Interface,
): Promise<Record<string, unknown>> {
  const props = tool.input_schema.properties;
  if (!props || Object.keys(props).length === 0) return {};

  const required = new Set(tool.input_schema.required ?? []);
  const args: Record<string, unknown> = {};

  console.log(`${c.dim}Enter arguments for ${tool.name}:${c.reset}`);

  for (const [name, prop] of Object.entries(props)) {
    const reqHint = required.has(name) ? ` ${c.red}*${c.reset}` : '';
    const descHint = prop.description ? ` ${c.dim}(${prop.description})${c.reset}` : '';
    const typeHint = prop.type ? ` ${c.dim}[${prop.type}]${c.reset}` : '';

    if (prop.enum && prop.enum.length > 0) {
      console.log(`  ${c.cyan}${name}${c.reset}${reqHint}${descHint}`);
      for (let i = 0; i < prop.enum.length; i++) {
        const isDefault = prop.default === prop.enum[i];
        console.log(`    ${c.cyan}${i + 1}${c.reset}) ${prop.enum[i]}${isDefault ? ` ${c.dim}(default)${c.reset}` : ''}`);
      }
      const answer = await rl.question(`  ${c.cyan}>${c.reset} `);
      if (answer === '' && prop.default !== undefined) {
        args[name] = prop.default;
      } else {
        const idx = parseInt(answer, 10);
        if (idx >= 1 && idx <= prop.enum.length) {
          args[name] = prop.enum[idx - 1];
        } else if (answer !== '') {
          args[name] = answer;
        }
      }
    } else {
      const answer = await rl.question(`  ${c.cyan}${name}${c.reset}${typeHint}${reqHint}${descHint}: `);
      if (answer === '' && !required.has(name)) continue;
      if (answer === '' && prop.default !== undefined) {
        args[name] = prop.default;
        continue;
      }
      // Coerce types
      if (prop.type === 'number' || prop.type === 'integer') {
        args[name] = parseFloat(answer);
      } else if (prop.type === 'boolean') {
        args[name] = answer.toLowerCase().startsWith('y') || answer === 'true' || answer === '1';
      } else {
        // Try JSON parse for objects/arrays, fall back to string
        if (answer.startsWith('{') || answer.startsWith('[')) {
          try { args[name] = JSON.parse(answer); } catch { args[name] = answer; }
        } else {
          args[name] = answer;
        }
      }
    }
  }

  return args;
}

// ─── Command Handlers ──────────────────────────────────────────────

function getTools(G: G): ToolDef[] {
  const tools = G.tools as ToolDef[] | undefined;
  return (tools ?? []).filter(t => t && t.name);
}

function cmdHelp(): void {
  console.log(`
${c.bold}Commands:${c.reset}
  ${c.cyan}help${c.reset}                        Show this help
  ${c.cyan}tools${c.reset}                       List available tools
  ${c.cyan}call <tool> [json]${c.reset}          Call a tool (prompts for args if no JSON given)
  ${c.cyan}load <json>${c.reset}                 Call onLoad(params) — e.g. load {"walletAddress":"0x..."}
  ${c.cyan}init${c.reset}                        Call init()
  ${c.cyan}start${c.reset}                       Call start()
  ${c.cyan}stop${c.reset}                        Call stop()
  ${c.cyan}sync${c.reset}                        Trigger onSync() — run data sync
  ${c.cyan}cron <id>${c.reset}                   Trigger onCronTrigger(id)
  ${c.cyan}session start [id]${c.reset}          Trigger onSessionStart
  ${c.cyan}session end [id]${c.reset}            Trigger onSessionEnd
  ${c.cyan}setup${c.reset}                       Run setup wizard (traditional form-based)
  ${c.cyan}oauth${c.reset}                       Run OAuth flow (redirect + paste credential ID)
  ${c.cyan}options${c.reset}                     List runtime options
  ${c.cyan}option <name> <value>${c.reset}       Set a runtime option
  ${c.cyan}state${c.reset}                       Show state contents
  ${c.cyan}db <sql>${c.reset}                    Run SQL query
  ${c.cyan}env <key> <value>${c.reset}           Set environment variable
  ${c.cyan}backend [path]${c.reset}              Show backend info or GET a path
  ${c.cyan}socket${c.reset}                      Show socket.io connection status
  ${c.cyan}emit <event> [json]${c.reset}         Emit a socket.io event
  ${c.cyan}disconnect${c.reset}                  Call onDisconnect()
  ${c.cyan}tdlib${c.reset}                       Show TDLib availability and client status
  ${c.cyan}tdlib send <json>${c.reset}           Send raw TDLib request and print response
  ${c.cyan}tdlib receive${c.reset}               Wait 3s for next TDLib update
  ${c.cyan}reload${c.reset}                      Reload skill (stop + re-read + init + start)
  ${c.cyan}exit${c.reset} / ${c.cyan}quit${c.reset}                  Clean exit

${c.dim}Mode: live (real HTTP via curl, persistent storage, socket.io)${c.reset}
${c.dim}Tip: Tab or Right arrow accepts ghost text suggestions${c.reset}
`);
}

function cmdTools(G: G): void {
  const tools = getTools(G);
  if (tools.length === 0) {
    console.log(`${c.dim}No tools registered${c.reset}`);
    return;
  }
  console.log(`\n${c.bold}Tools (${tools.length}):${c.reset}`);
  for (const tool of tools) {
    const params = tool.input_schema.properties
      ? Object.keys(tool.input_schema.properties).join(', ')
      : '';
    console.log(`  ${c.cyan}${tool.name}${c.reset}${params ? ` (${c.dim}${params}${c.reset})` : ''}`);
    if (tool.description) {
      console.log(`    ${c.dim}${tool.description}${c.reset}`);
    }
  }
  console.log();
}

async function cmdCall(G: G, rest: string, rl: readline.Interface): Promise<void> {
  const tools = getTools(G);
  const spaceIdx = rest.indexOf(' ');
  const toolName = spaceIdx === -1 ? rest : rest.substring(0, spaceIdx);
  const jsonStr = spaceIdx === -1 ? '' : rest.substring(spaceIdx + 1).trim();

  if (!toolName) {
    console.log(`${c.red}Usage: call <tool-name> [json-args]${c.reset}`);
    return;
  }

  const tool = tools.find(t => t.name === toolName);
  if (!tool) {
    console.log(`${c.red}Tool "${toolName}" not found.${c.reset} Available: ${tools.map(t => t.name).join(', ')}`);
    return;
  }

  let args: Record<string, unknown>;
  if (jsonStr) {
    try {
      args = JSON.parse(jsonStr);
    } catch (e) {
      console.log(`${c.red}Invalid JSON: ${e}${c.reset}`);
      return;
    }
  } else {
    args = await promptToolArgs(tool, rl);
  }

  try {
    const rawResult = await tool.execute(args);
    let parsed: unknown;
    try { parsed = JSON.parse(rawResult); } catch { parsed = rawResult; }
    console.log(`\n${c.green}Result:${c.reset}`);
    console.log(prettyJson(parsed));
  } catch (e) {
    console.log(`${c.red}Tool error: ${e}${c.reset}`);
  }
}

function cmdLoad(G: G, rest: string): void {
  const onLoad = G.onLoad as ((params: Record<string, unknown>) => void) | undefined;
  if (typeof onLoad !== 'function') {
    console.log(`${c.yellow}onLoad not defined${c.reset}`);
    return;
  }
  const json = rest.trim();
  if (!json) {
    console.log(`${c.red}Usage: load <json> — e.g. load {"walletAddress":"0x73Eb66364AeF6A131b92EF15C72BE8222c54Ab1e"}${c.reset}`);
    return;
  }
  let params: Record<string, unknown>;
  try {
    params = JSON.parse(json);
  } catch (e) {
    console.log(`${c.red}Invalid JSON: ${e}${c.reset}`);
    return;
  }
  try {
    onLoad(params);
    console.log(`${c.green}onLoad() completed${c.reset}`);
  } catch (e) {
    console.log(`${c.red}onLoad() error: ${e}${c.reset}`);
  }
}

async function cmdLifecycle(G: G, hookName: string): Promise<void> {
  const fn = G[hookName] as (() => void | Promise<void>) | undefined;
  if (typeof fn !== 'function') {
    console.log(`${c.yellow}${hookName}() not defined${c.reset}`);
    return;
  }
  try {
    await fn();
    console.log(`${c.green}${hookName}() completed${c.reset}`);
  } catch (e) {
    console.log(`${c.red}${hookName}() error: ${e}${c.reset}`);
  }
}

async function cmdCron(G: G, scheduleId: string): Promise<void> {
  if (!scheduleId) {
    const schedules = getLiveState().cronSchedules;
    const ids = Object.keys(schedules);
    if (ids.length === 0) {
      console.log(`${c.dim}No cron schedules registered${c.reset}`);
    } else {
      console.log(`${c.bold}Cron schedules:${c.reset}`);
      for (const [id, expr] of Object.entries(schedules)) {
        console.log(`  ${c.cyan}${id}${c.reset}: ${expr}`);
      }
      console.log(`\n${c.dim}Usage: cron <schedule-id>${c.reset}`);
    }
    return;
  }
  const fn = G.onCronTrigger as ((id: string) => void | Promise<void>) | undefined;
  if (typeof fn !== 'function') {
    console.log(`${c.yellow}onCronTrigger not defined${c.reset}`);
    return;
  }
  try {
    await fn(scheduleId);
    console.log(`${c.green}onCronTrigger("${scheduleId}") completed${c.reset}`);
  } catch (e) {
    console.log(`${c.red}onCronTrigger error: ${e}${c.reset}`);
  }
}

async function cmdSession(G: G, rest: string): Promise<void> {
  const parts = rest.split(/\s+/);
  const action = parts[0];
  const sessionId = parts[1] || `session-${Date.now()}`;

  if (action === 'start') {
    const fn = G.onSessionStart as ((args: { sessionId: string }) => void | Promise<void>) | undefined;
    if (typeof fn !== 'function') {
      console.log(`${c.yellow}onSessionStart not defined${c.reset}`);
      return;
    }
    try {
      await fn({ sessionId });
      console.log(`${c.green}onSessionStart("${sessionId}") completed${c.reset}`);
    } catch (e) {
      console.log(`${c.red}onSessionStart error: ${e}${c.reset}`);
    }
  } else if (action === 'end') {
    const fn = G.onSessionEnd as ((args: { sessionId: string }) => void | Promise<void>) | undefined;
    if (typeof fn !== 'function') {
      console.log(`${c.yellow}onSessionEnd not defined${c.reset}`);
      return;
    }
    try {
      await fn({ sessionId });
      console.log(`${c.green}onSessionEnd("${sessionId}") completed${c.reset}`);
    } catch (e) {
      console.log(`${c.red}onSessionEnd error: ${e}${c.reset}`);
    }
  } else {
    console.log(`${c.red}Usage: session start [id] | session end [id]${c.reset}`);
  }
}

async function cmdOptions(G: G): Promise<void> {
  const fn = G.onListOptions as (() => { options: Array<{
    name: string; type: string; label: string; value: unknown;
    options?: Array<{ label: string; value: string }>;
  }> } | Promise<{ options: Array<{
    name: string; type: string; label: string; value: unknown;
    options?: Array<{ label: string; value: string }>;
  }> }>) | undefined;
  if (typeof fn !== 'function') {
    console.log(`${c.yellow}onListOptions not defined${c.reset}`);
    return;
  }
  try {
    const result = await fn();
    if (!result.options || result.options.length === 0) {
      console.log(`${c.dim}No options available${c.reset}`);
      return;
    }
    console.log(`\n${c.bold}Options:${c.reset}`);
    for (const opt of result.options) {
      const choices = opt.options ? ` [${opt.options.map(o => o.value).join('|')}]` : '';
      console.log(`  ${c.cyan}${opt.name}${c.reset} = ${c.green}${opt.value}${c.reset} ${c.dim}(${opt.type}${choices})${c.reset}`);
      if (opt.label) console.log(`    ${c.dim}${opt.label}${c.reset}`);
    }
    console.log();
  } catch (e) {
    console.log(`${c.red}onListOptions error: ${e}${c.reset}`);
  }
}

async function cmdSetOption(G: G, rest: string): Promise<void> {
  const spaceIdx = rest.indexOf(' ');
  if (spaceIdx === -1) {
    console.log(`${c.red}Usage: option <name> <value>${c.reset}`);
    return;
  }
  const name = rest.substring(0, spaceIdx);
  const rawValue = rest.substring(spaceIdx + 1).trim();

  const fn = G.onSetOption as ((args: { name: string; value: unknown }) => void | Promise<void>) | undefined;
  if (typeof fn !== 'function') {
    console.log(`${c.yellow}onSetOption not defined${c.reset}`);
    return;
  }

  // Try to parse as JSON, then number, then boolean, else string
  let value: unknown = rawValue;
  if (rawValue === 'true') value = true;
  else if (rawValue === 'false') value = false;
  else if (!isNaN(Number(rawValue)) && rawValue !== '') value = Number(rawValue);
  else {
    try { value = JSON.parse(rawValue); } catch { /* keep as string */ }
  }

  try {
    await fn({ name, value });
    console.log(`${c.green}Set ${name} = ${JSON.stringify(value)}${c.reset}`);
  } catch (e) {
    console.log(`${c.red}onSetOption error: ${e}${c.reset}`);
  }
}

function cmdState(G: G): void {
  const stateApi = G.state as {
    __getAll?: () => Record<string, unknown>;
    keys?: () => string[];
    get?: (key: string) => unknown;
  } | undefined;

  // Prefer __getAll debug method (reads directly from file)
  if (stateApi?.__getAll) {
    const data = stateApi.__getAll();
    if (Object.keys(data).length === 0) {
      console.log(`${c.dim}(state is empty)${c.reset}`);
    } else {
      console.log(prettyJson(data));
    }
  } else if (stateApi?.keys && stateApi?.get) {
    // Fallback: enumerate via keys/get
    const keys = stateApi.keys();
    if (keys.length === 0) {
      console.log(`${c.dim}(state is empty)${c.reset}`);
      return;
    }
    const data: Record<string, unknown> = {};
    for (const key of keys) {
      data[key] = stateApi.get(key);
    }
    console.log(prettyJson(data));
  } else {
    console.log(`${c.dim}(state inspection not available)${c.reset}`);
  }
}

function cmdDb(G: G, sql: string): void {
  if (!sql) {
    console.log(`${c.red}Usage: db <sql-query>${c.reset}`);
    return;
  }

  const dbApi = G.db as {
    exec?: (sql: string, params: unknown[]) => void;
    all?: (sql: string, params: unknown[]) => Array<Record<string, unknown>>;
  } | undefined;

  if (!dbApi) {
    console.log(`${c.yellow}Database API not available${c.reset}`);
    return;
  }

  const isSelect = sql.trim().toUpperCase().startsWith('SELECT');

  try {
    if (isSelect && dbApi.all) {
      const rows = dbApi.all(sql, []);
      if (rows.length === 0) {
        console.log(`${c.dim}(no rows returned)${c.reset}`);
      } else {
        console.log(prettyJson(rows));
      }
    } else if (dbApi.exec) {
      dbApi.exec(sql, []);
      console.log(`${c.green}SQL executed${c.reset}`);
    }
  } catch (e) {
    console.log(`${c.red}SQL error: ${e}${c.reset}`);
  }
}

function cmdEnv(rest: string): void {
  const spaceIdx = rest.indexOf(' ');
  if (spaceIdx === -1) {
    console.log(`${c.red}Usage: env <key> <value>${c.reset}`);
    return;
  }
  const key = rest.substring(0, spaceIdx);
  const value = rest.substring(spaceIdx + 1).trim();
  process.env[key] = value;
  console.log(`${c.green}Set env ${key}${c.reset}`);
}

// ─── Backend / Socket Commands ─────────────────────────────────────

function cmdBackend(G: G, path: string): void {
  const backendApi = G.backend as {
    url?: string;
    token?: string;
    fetch?: (path: string, opts?: unknown) => { status: number; headers: Record<string, string>; body: string };
  } | undefined;

  if (!backendApi) {
    console.log(`${c.yellow}Backend API not available${c.reset}`);
    return;
  }

  if (!path) {
    console.log(`${c.bold}Backend:${c.reset}`);
    console.log(`  ${c.cyan}URL${c.reset}: ${backendApi.url}`);
    console.log(`  ${c.cyan}Token${c.reset}: ${backendApi.token ? backendApi.token.substring(0, 20) + '...' : '(none)'}`);
    console.log(`\n${c.dim}Usage: backend <path> — e.g. backend /api/health${c.reset}`);
    return;
  }

  try {
    const result = backendApi.fetch!(path);
    console.log(`${c.green}${result.status}${c.reset}`);
    try {
      const parsed = JSON.parse(result.body);
      console.log(prettyJson(parsed));
    } catch {
      console.log(result.body);
    }
  } catch (e) {
    console.log(`${c.red}Backend error: ${e}${c.reset}`);
  }
}

function cmdSocket(G: G): void {
  const socketApi = G.socket as {
    connected?: () => boolean;
    id?: () => string | undefined;
  } | undefined;

  if (!socketApi) {
    console.log(`${c.yellow}Socket API not available${c.reset}`);
    return;
  }

  const connected = socketApi.connected?.() ?? false;
  const id = socketApi.id?.();
  console.log(`${c.bold}Socket.io:${c.reset}`);
  console.log(`  ${c.cyan}Status${c.reset}: ${connected ? `${c.green}connected${c.reset}` : `${c.red}disconnected${c.reset}`}`);
  if (id) console.log(`  ${c.cyan}ID${c.reset}: ${id}`);
}

function cmdEmit(G: G, rest: string): void {
  const socketApi = G.socket as {
    connected?: () => boolean;
    emit?: (event: string, ...args: unknown[]) => void;
  } | undefined;

  if (!socketApi?.emit) {
    console.log(`${c.yellow}Socket API not available${c.reset}`);
    return;
  }

  if (!socketApi.connected?.()) {
    console.log(`${c.red}Socket not connected${c.reset}`);
    return;
  }

  const spaceIdx = rest.indexOf(' ');
  const event = spaceIdx === -1 ? rest : rest.substring(0, spaceIdx);
  const jsonStr = spaceIdx === -1 ? '' : rest.substring(spaceIdx + 1).trim();

  if (!event) {
    console.log(`${c.red}Usage: emit <event> [json-data]${c.reset}`);
    return;
  }

  let data: unknown;
  if (jsonStr) {
    try {
      data = JSON.parse(jsonStr);
    } catch (e) {
      console.log(`${c.red}Invalid JSON: ${e}${c.reset}`);
      return;
    }
  }

  try {
    if (data !== undefined) {
      socketApi.emit(event, data);
    } else {
      socketApi.emit(event);
    }
    console.log(`${c.green}Emitted "${event}"${c.reset}`);
  } catch (e) {
    console.log(`${c.red}Emit error: ${e}${c.reset}`);
  }
}

// ─── Commands & Completion ──────────────────────────────────────────

const ALL_COMMANDS = [
  'help', 'tools', 'call', 'init', 'start', 'stop', 'sync', 'cron', 'session',
  'setup', 'oauth', 'options', 'option', 'state', 'db', 'env', 'backend',
  'socket', 'emit', 'disconnect', 'tdlib', 'reload', 'exit', 'quit',
];

// ─── Suggestion Sources (for ghost text) ────────────────────────────

function buildSuggestionSources(getCtx: () => { G: G }): SuggestionSource[] {
  // Helper: return the untyped suffix if `full` starts with `typed`, else null
  function suffix(typed: string, full: string): string | null {
    if (full.startsWith(typed) && full.length > typed.length) return full.slice(typed.length);
    return null;
  }

  // 1. Command name completion (first word)
  const commandSource: SuggestionSource = {
    suggest(line) {
      const trimmed = line.trimStart();
      if (trimmed.includes(' ')) return null;
      for (const cmd of ALL_COMMANDS) {
        const s = suffix(trimmed.toLowerCase(), cmd);
        if (s !== null) return s;
      }
      return null;
    },
  };

  // 2. Tool name after "call "
  const toolNameSource: SuggestionSource = {
    suggest(line) {
      const match = line.match(/^call\s+(\S*)$/i);
      if (!match) return null;
      const partial = match[1];
      const tools = getTools(getCtx().G);
      for (const t of tools) {
        const s = suffix(partial, t.name);
        if (s !== null) return s;
      }
      return null;
    },
  };

  // 3. Arg template after "call <tool> "
  const argTemplateSource: SuggestionSource = {
    suggest(line) {
      const match = line.match(/^call\s+(\S+)\s+$/i);
      if (!match) return null;
      const toolName = match[1];
      const tool = getTools(getCtx().G).find(t => t.name === toolName);
      if (!tool?.input_schema?.properties) return null;
      const props = tool.input_schema.properties;
      const keys = Object.keys(props);
      if (keys.length === 0) return null;
      // Build a JSON template with placeholders
      const template: Record<string, unknown> = {};
      for (const key of keys) {
        const prop = props[key];
        if (prop.enum && prop.enum.length > 0) template[key] = prop.enum[0];
        else if (prop.default !== undefined) template[key] = prop.default;
        else if (prop.type === 'number' || prop.type === 'integer') template[key] = 0;
        else if (prop.type === 'boolean') template[key] = false;
        else template[key] = '';
      }
      return JSON.stringify(template);
    },
  };

  // 4. Cron IDs after "cron "
  const cronSource: SuggestionSource = {
    suggest(line) {
      const match = line.match(/^cron\s+(\S*)$/i);
      if (!match) return null;
      const partial = match[1];
      const ids = Object.keys(getLiveState().cronSchedules);
      for (const id of ids) {
        const s = suffix(partial, id);
        if (s !== null) return s;
      }
      return null;
    },
  };

  // 5. Option names after "option "
  const optionSource: SuggestionSource = {
    suggest(line) {
      const match = line.match(/^option\s+(\S*)$/i);
      if (!match) return null;
      const partial = match[1];
      try {
        const fn = getCtx().G.onListOptions as (() => { options: Array<{ name: string }> }) | undefined;
        if (typeof fn !== 'function') return null;
        const result = fn();
        for (const opt of result.options) {
          const s = suffix(partial, opt.name);
          if (s !== null) return s;
        }
      } catch { /* ignore */ }
      return null;
    },
  };

  // 6. Session actions after "session "
  const sessionSource: SuggestionSource = {
    suggest(line) {
      const match = line.match(/^session\s+(\S*)$/i);
      if (!match) return null;
      const partial = match[1];
      for (const sub of ['start', 'end']) {
        const s = suffix(partial, sub);
        if (s !== null) return s;
      }
      return null;
    },
  };

  // 7. TDLib subcommands after "tdlib "
  const tdlibSource: SuggestionSource = {
    suggest(line) {
      const match = line.match(/^tdlib\s+(\S*)$/i);
      if (!match) return null;
      const partial = match[1];
      for (const sub of ['send', 'receive']) {
        const s = suffix(partial, sub);
        if (s !== null) return s;
      }
      return null;
    },
  };

  return [commandSource, toolNameSource, argTemplateSource, cronSource, optionSource, sessionSource, tdlibSource];
}

// ─── Main ──────────────────────────────────────────────────────────

async function main(): Promise<void> {
  console.log(`${c.cyan}${c.bold}═══════════════════════════════════════════════════════════════${c.reset}`);
  console.log(`${c.cyan}${c.bold}            Skill REPL (Interactive · Live Mode)                ${c.reset}`);
  console.log(`${c.cyan}${c.bold}═══════════════════════════════════════════════════════════════${c.reset}`);

  const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout,
  });

  // Parse CLI args
  const args = process.argv.slice(2);
  let skillId: string | undefined;
  let cleanFlag = false;

  for (const arg of args) {
    if (arg === '--clean') {
      cleanFlag = true;
    } else if (!arg.startsWith('-')) {
      skillId = arg;
    }
  }

  // Validate CLI skill id: must be a built skill (e.g. gmail, server-ping), not "{}" or invalid
  const skills = discoverSkills();
  if (skillId && skills.length > 0) {
    const valid = skills.some((s) => s.id === skillId);
    if (!valid) {
      console.log(
        `${c.yellow}Unknown skill "${skillId}". Use a built skill id (e.g. gmail, server-ping) or pick below.${c.reset}\n`
      );
      skillId = undefined;
    }
  }

  // If no skill specified, let user pick
  if (!skillId) {
    if (skills.length === 0) {
      console.log(`${c.red}No compiled skills found. Run 'yarn build' first.${c.reset}`);
      rl.close();
      process.exit(1);
    }

    console.log(`\n${c.bold}Available skills:${c.reset}`);
    for (let i = 0; i < skills.length; i++) {
      const s = skills[i];
      console.log(`  ${c.cyan}${i + 1}${c.reset}) ${c.bold}${s.manifest.name}${c.reset} ${c.dim}(${s.id})${c.reset}`);
      if (s.manifest.description) {
        console.log(`     ${c.dim}${s.manifest.description}${c.reset}`);
      }
    }

    while (!skillId) {
      const answer = await rl.question(`\n${c.cyan}Select skill (1-${skills.length}):${c.reset} `);
      const idx = parseInt(answer, 10);
      if (idx >= 1 && idx <= skills.length) {
        skillId = skills[idx - 1].id;
      } else {
        // Try by name
        const match = skills.find(s => s.id === answer.trim());
        if (match) {
          skillId = match.id;
        } else {
          console.log(`${c.red}Enter a number 1-${skills.length} or a skill id${c.reset}`);
        }
      }
    }
  }

  // ─── Backend Connection ─────────────────────────────────────────
  const defaultBackendUrl = process.env.BACKEND_URL || process.env.BACKEND_URL || 'https://api.alphahuman.xyz';
  const defaultJwtToken = process.env.JWT_TOKEN || process.env.DEV_JWT_TOKEN || '';

  console.log(`\n${c.bold}Backend Connection${c.reset}`);
  console.log(`${c.dim}${'─'.repeat(50)}${c.reset}`);

  const backendUrlInput = await rl.question(
    `  ${c.cyan}Backend URL${c.reset} ${c.dim}(${defaultBackendUrl})${c.reset}: `,
  );
  const backendUrl = backendUrlInput.trim() || defaultBackendUrl;

  const jwtInput = await rl.question(
    `  ${c.cyan}JWT Token${c.reset}${defaultJwtToken ? ` ${c.dim}(from env)${c.reset}` : ''}: `,
  );
  const jwtToken = jwtInput.trim() || defaultJwtToken;

  if (jwtToken) {
    console.log(`${c.green}JWT token set${c.reset} ${c.dim}(${jwtToken.substring(0, 20)}...)${c.reset}`);
  } else {
    console.log(`${c.yellow}No JWT token — backend/socket APIs will be unauthenticated${c.reset}`);
  }
  console.log(`${c.dim}Backend: ${backendUrl}${c.reset}`);

  // Load the skill
  console.log(`\n${c.dim}Loading ${skillId}...${c.reset}`);
  console.log(`${c.dim}Mode: live (real HTTP via curl, persistent storage, socket.io)${c.reset}`);
  let ctx: { G: G; manifest: Manifest; cleanup: () => void };
  try {
    ctx = await loadSkill(skillId, cleanFlag, { jwtToken, backendUrl });
  } catch (e) {
    console.log(`${c.red}${e}${c.reset}`);
    rl.close();
    process.exit(1);
  }

  const toolCount = getTools(ctx.G).length;
  console.log(`${c.green}Loaded${c.reset} ${c.bold}${ctx.manifest.name}${c.reset} v${ctx.manifest.version}`);
  if (toolCount > 0) console.log(`${c.dim}  ${toolCount} tools available${c.reset}`);

  // Restore OAuth credential on the bridge from persisted config (survives REPL restarts)
  if (ctx.manifest.setup?.oauth) {
    const stateApi = ctx.G.state as { get?: (key: string) => unknown } | undefined;
    const savedConfig = stateApi?.get?.('config') as { credentialId?: string } | null;
    const credId = savedConfig?.credentialId;
    if (credId && isValidIntegrationId(credId)) {
      const oauthApi = ctx.G.oauth as { __setCredential?: (cred: unknown) => void } | undefined;
      if (oauthApi?.__setCredential) {
        oauthApi.__setCredential({
          credentialId: credId,
          provider: ctx.manifest.setup.oauth.provider,
          scopes: ctx.manifest.setup.oauth.scopes,
          isValid: true,
          createdAt: Date.now(),
        });
        console.log(`${c.green}OAuth credential restored${c.reset} ${c.dim}(${credId.substring(0, 8)}...)${c.reset}`);
      }
    } else if (credId && !isValidIntegrationId(credId)) {
      console.log(`${c.yellow}Skipped invalid saved credential ID "${credId}" — run OAuth flow to set a valid integration ID.${c.reset}`);
    }
  }

  // Call init + start
  if (typeof ctx.G.init === 'function') {
    try {
      await (ctx.G.init as () => void | Promise<void>)();
      console.log(`${c.green}init()${c.reset} ok`);
    } catch (e) {
      console.log(`${c.red}init() error: ${e}${c.reset}`);
    }
  }
  if (typeof ctx.G.start === 'function') {
    try {
      await (ctx.G.start as () => void | Promise<void>)();
      console.log(`${c.green}start()${c.reset} ok`);
    } catch (e) {
      console.log(`${c.red}start() error: ${e}${c.reset}`);
    }
  }

  // Auto-detect setup needed
  if (ctx.manifest.setup?.required) {
    const stateApi = ctx.G.state as { get?: (key: string) => unknown } | undefined;
    const config = stateApi?.get?.('config');
    if (!config) {
      if (ctx.manifest.setup.oauth) {
        // OAuth-based setup
        console.log(`\n${c.yellow}OAuth setup required but no config found.${c.reset}`);
        const answer = await rl.question(`${c.cyan}Run OAuth flow? [Y/n]:${c.reset} `);
        if (answer === '' || answer.toLowerCase().startsWith('y')) {
          await runOAuthFlow(ctx.G, ctx.manifest, rl, backendUrl, jwtToken);
        }
      } else if (typeof ctx.G.onSetupStart === 'function') {
        // Traditional form-based setup wizard
        console.log(`\n${c.yellow}Setup required but no config found.${c.reset}`);
        const answer = await rl.question(`${c.cyan}Run setup wizard? [Y/n]:${c.reset} `);
        if (answer === '' || answer.toLowerCase().startsWith('y')) {
          await runSetupWizard(ctx.G, rl);
        }
      }
    }
  }

  // REPL loop
  console.log(`\n${c.dim}Type 'help' for commands. Tab/Right arrow accepts ghost suggestions.${c.reset}`);

  // Close the initial readline (used for skill selection & setup prompts)
  rl.close();

  const prompt = `${c.cyan}${skillId}${c.reset}${c.dim}>${c.reset} `;
  const sources = buildSuggestionSources(() => ctx);
  const ghostInput = createGhostInput(process.stdin, process.stdout, { prompt, sources });

  // Patch globalThis.console so async log messages (TDLib updates, socket events,
  // skill console.log, etc.) don't corrupt the prompt.
  const origConsole = {
    log: globalThis.console.log.bind(globalThis.console),
    info: globalThis.console.info.bind(globalThis.console),
    warn: globalThis.console.warn.bind(globalThis.console),
    error: globalThis.console.error.bind(globalThis.console),
    debug: globalThis.console.debug.bind(globalThis.console),
  };

  function replSafeWrite(orig: (...a: unknown[]) => void, ...args: unknown[]) {
    ghostInput.interruptForLog(() => orig(...args));
  }

  globalThis.console.log = (...a: unknown[]) => replSafeWrite(origConsole.log, ...a);
  globalThis.console.info = (...a: unknown[]) => replSafeWrite(origConsole.info, ...a);
  globalThis.console.warn = (...a: unknown[]) => replSafeWrite(origConsole.warn, ...a);
  globalThis.console.error = (...a: unknown[]) => replSafeWrite(origConsole.error, ...a);
  globalThis.console.debug = (...a: unknown[]) => replSafeWrite(origConsole.debug, ...a);

  // Helper: create a temporary readline for sub-prompts (setup wizard, tool args, etc.)
  // Ghost input releases raw mode before these run, so normal readline works fine.
  function createTempRl(): readline.Interface {
    return readline.createInterface({ input: process.stdin, output: process.stdout });
  }

  let running = true;

  while (running) {
    let line: string;
    try {
      line = await ghostInput.question();
    } catch {
      // EOF or error
      break;
    }

    const trimmed = line.trim();
    if (!trimmed) continue;

    const [cmd, ...restParts] = trimmed.split(/\s+/);
    const rest = restParts.join(' ');

    try {
      switch (cmd.toLowerCase()) {
        case 'help':
        case '?':
          cmdHelp();
          break;

        case 'tools':
          cmdTools(ctx.G);
          break;

        case 'call': {
          const tmpRl = createTempRl();
          try { await cmdCall(ctx.G, rest, tmpRl); } finally { tmpRl.close(); }
          break;
        }

        case 'load':
          cmdLoad(ctx.G, rest);
          break;

        case 'init':
          await cmdLifecycle(ctx.G, 'init');
          break;

        case 'start':
          await cmdLifecycle(ctx.G, 'start');
          break;

        case 'stop':
          await cmdLifecycle(ctx.G, 'stop');
          break;

        case 'sync':
          await cmdLifecycle(ctx.G, 'onSync');
          break;

        case 'cron':
          await cmdCron(ctx.G, rest);
          break;

        case 'session':
          await cmdSession(ctx.G, rest);
          break;

        case 'setup': {
          const tmpRl = createTempRl();
          try { await runSetupWizard(ctx.G, tmpRl); } finally { tmpRl.close(); }
          break;
        }

        case 'oauth': {
          const tmpRl = createTempRl();
          try { await runOAuthFlow(ctx.G, ctx.manifest, tmpRl, backendUrl, jwtToken); } finally { tmpRl.close(); }
          break;
        }

        case 'options':
          await cmdOptions(ctx.G);
          break;

        case 'option':
          await cmdSetOption(ctx.G, rest);
          break;

        case 'state':
          cmdState(ctx.G);
          break;

        case 'db':
          cmdDb(ctx.G, rest);
          break;

        case 'env':
          cmdEnv(rest);
          break;

        case 'backend':
          cmdBackend(ctx.G, rest);
          break;

        case 'socket':
          cmdSocket(ctx.G);
          break;

        case 'emit':
          cmdEmit(ctx.G, rest);
          break;

        case 'disconnect':
          await cmdLifecycle(ctx.G, 'onDisconnect');
          break;

        case 'tdlib': {
          const tdlibApi = ctx.G.tdlib as {
            isAvailable?: () => boolean;
            send?: (json: string) => Promise<string>;
            receive?: (ms: number) => Promise<unknown>;
          } | undefined;

          const tdlibAvailable = tdlibApi?.isAvailable?.() ?? false;

          if (!rest) {
            // Show TDLib status
            console.log(`${c.bold}TDLib:${c.reset}`);
            console.log(`  ${c.cyan}Available${c.reset}: ${tdlibAvailable ? `${c.green}yes${c.reset}` : `${c.red}no${c.reset}`}`);

            // Try to get auth state from skill state
            const stateApi = ctx.G.state as { get?: (key: string) => unknown } | undefined;
            const skillState = ctx.G.globalThis as Record<string, unknown> | undefined;
            const getState = skillState?.getTelegramSkillState as (() => Record<string, unknown>) | undefined;
            if (getState) {
              try {
                const s = getState();
                console.log(`  ${c.cyan}Auth State${c.reset}: ${s.authState ?? 'unknown'}`);
                console.log(`  ${c.cyan}Connected${c.reset}: ${s.clientConnecting ? 'connecting...' : s.client ? `${c.green}yes${c.reset}` : `${c.red}no${c.reset}`}`);
                if (s.clientError) console.log(`  ${c.cyan}Error${c.reset}: ${c.red}${s.clientError}${c.reset}`);
              } catch {
                // skill state not available
              }
            }
            const config = stateApi?.get?.('config') as Record<string, unknown> | null;
            if (config?.isAuthenticated) {
              console.log(`  ${c.cyan}Authenticated${c.reset}: ${c.green}yes${c.reset}`);
            }
          } else if (rest.startsWith('send ')) {
            // Send raw TDLib request
            const jsonStr = rest.substring(5).trim();
            if (!tdlibAvailable || !tdlibApi?.send) {
              console.log(`${c.red}TDLib not available${c.reset}`);
              break;
            }
            try {
              const parsed = JSON.parse(jsonStr);
              console.log(`${c.dim}Sending: ${JSON.stringify(parsed)}${c.reset}`);
              const response = await tdlibApi.send(JSON.stringify(parsed));
              const result = JSON.parse(response);
              console.log(`${c.green}Response:${c.reset}`);
              console.log(prettyJson(result));
            } catch (e) {
              console.log(`${c.red}TDLib send error: ${e}${c.reset}`);
            }
          } else if (rest === 'receive') {
            // Wait for next update
            if (!tdlibAvailable || !tdlibApi?.receive) {
              console.log(`${c.red}TDLib not available${c.reset}`);
              break;
            }
            console.log(`${c.dim}Waiting 3s for TDLib update...${c.reset}`);
            try {
              const update = await tdlibApi.receive(3000);
              if (update) {
                console.log(`${c.green}Update:${c.reset}`);
                console.log(prettyJson(update));
              } else {
                console.log(`${c.dim}(no update received within 3s)${c.reset}`);
              }
            } catch (e) {
              console.log(`${c.red}TDLib receive error: ${e}${c.reset}`);
            }
          } else {
            console.log(`${c.red}Usage: tdlib | tdlib send <json> | tdlib receive${c.reset}`);
          }
          break;
        }

        case 'reload': {
          console.log(`${c.dim}Reloading...${c.reset}`);
          // Stop current skill
          if (typeof ctx.G.stop === 'function') {
            try { await (ctx.G.stop as () => void | Promise<void>)(); } catch { /* ignore */ }
          }
          ctx.cleanup();

          // Re-load
          try {
            ctx = await loadSkill(skillId!, false, { jwtToken, backendUrl });
            const newToolCount = getTools(ctx.G).length;
            console.log(`${c.green}Reloaded${c.reset} ${c.bold}${ctx.manifest.name}${c.reset} v${ctx.manifest.version}`);
            if (newToolCount > 0) console.log(`${c.dim}  ${newToolCount} tools available${c.reset}`);

            // Restore OAuth credential on the bridge
            if (ctx.manifest.setup?.oauth) {
              const stateApi = ctx.G.state as { get?: (key: string) => unknown } | undefined;
              const savedConfig = stateApi?.get?.('config') as { credentialId?: string } | null;
              if (savedConfig?.credentialId) {
                const oauthApi = ctx.G.oauth as { __setCredential?: (cred: unknown) => void } | undefined;
                oauthApi?.__setCredential?.({
                  credentialId: savedConfig.credentialId,
                  provider: ctx.manifest.setup.oauth.provider,
                  scopes: ctx.manifest.setup.oauth.scopes,
                  isValid: true,
                  createdAt: Date.now(),
                });
                console.log(`${c.green}OAuth credential restored${c.reset}`);
              }
            }

            if (typeof ctx.G.init === 'function') {
              await (ctx.G.init as () => void | Promise<void>)();
              console.log(`${c.green}init()${c.reset} ok`);
            }
            if (typeof ctx.G.start === 'function') {
              await (ctx.G.start as () => void | Promise<void>)();
              console.log(`${c.green}start()${c.reset} ok`);
            }
          } catch (e) {
            console.log(`${c.red}Reload failed: ${e}${c.reset}`);
          }
          break;
        }

        case 'exit':
        case 'quit':
        case '.exit':
          running = false;
          break;

        default:
          console.log(`${c.red}Unknown command: ${cmd}${c.reset}. Type 'help' for available commands.`);
      }
    } catch (e) {
      console.log(`${c.red}Error: ${e}${c.reset}`);
    }

    // Visual separator between command output and next prompt
    if (running) {
      console.log(`\n${c.dim}${'─'.repeat(40)}${c.reset}`);
    }
  }

  // Restore original console and clean exit
  globalThis.console.log = origConsole.log;
  globalThis.console.info = origConsole.info;
  globalThis.console.warn = origConsole.warn;
  globalThis.console.error = origConsole.error;
  globalThis.console.debug = origConsole.debug;

  console.log(`\n${c.dim}Shutting down...${c.reset}`);
  if (typeof ctx.G.stop === 'function') {
    try {
      await (ctx.G.stop as () => void | Promise<void>)();
      console.log(`${c.green}stop()${c.reset} ok`);
    } catch (e) {
      console.log(`${c.red}stop() error: ${e}${c.reset}`);
    }
  }
  ctx.cleanup();
  ghostInput.destroy();
  console.log(`${c.dim}Bye!${c.reset}`);
}

main().catch(e => {
  console.error(`${c.red}Fatal: ${e}${c.reset}`);
  process.exit(1);
});
