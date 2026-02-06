# Contributing to AlphaHuman Skills

Thank you for contributing to the AlphaHuman skills ecosystem. This guide covers everything you need to submit a skill.

## Ways to Contribute

1. **Create a new skill** — Add capabilities to the AlphaHuman agent
2. **Improve an existing skill** — Better tools, bug fixes, more handlers
3. **Improve tooling** — Enhance dev tools, CI, documentation
4. **Add examples** — Show patterns others can follow

## Creating a New Skill

Start by looking at [`src/example-skill/`](src/example-skill/) — it demonstrates every bridge API, lifecycle hook, setup wizard, options system, and tool pattern.

### 1. Setup

```bash
# Fork and clone
git clone https://github.com/YOUR-USERNAME/alphahuman-skills.git
cd alphahuman-skills

# Install dependencies
yarn install

# Create a branch
git checkout -b skill/my-skill-name
```

### 2. Create Skill Directory

```bash
mkdir src/my-skill
```

### 3. Create manifest.json

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

### 4. Write index.ts

Every skill needs an `index.ts` with lifecycle hooks and tools:

```typescript
// Configuration
interface SkillConfig {
  apiKey: string;
}

const CONFIG: SkillConfig = { apiKey: '' };

// Lifecycle hooks
function init(): void {
  const saved = store.get('config') as Partial<SkillConfig> | null;
  if (saved) {
    CONFIG.apiKey = saved.apiKey ?? CONFIG.apiKey;
  }
}

function start(): void {
  console.log('[my-skill] Starting');
}

function stop(): void {
  store.set('config', CONFIG);
}

// Setup flow (if required)
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

function onSetupCancel(): void {}

// Tools
tools = [
  {
    name: 'get-status',
    description: 'Get current status',
    input_schema: { type: 'object', properties: {} },
    execute(args): string {
      return JSON.stringify({ status: 'ok' });
    },
  },
];
```

### 5. Add Per-Skill Dependencies (Optional)

If your skill needs npm packages, create a `package.json` in your skill directory:

```json
{
  "name": "@alphahuman/skill-my-skill",
  "private": true,
  "dependencies": { "some-library": "^1.0.0" }
}
```

Only `dependencies` are bundled — esbuild inlines them into the single output file.

### 6. Build, Validate, and Test

```bash
# Build
yarn build

# Type checking
yarn typecheck

# Validate (manifest, secrets, code quality)
yarn validate

# Run tests (if you have __tests__/test-my-skill.ts)
yarn test src/my-skill/__tests__/test-my-skill.ts
```

### 7. Submit

```bash
git add src/my-skill/
git commit -m "Add my-skill"
git push -u origin skill/my-skill
```

Open a pull request. Fill out the PR template completely.

## Naming Conventions

- **Lowercase only**: `price-tracker`, not `Price-Tracker`
- **Hyphens for spaces**: `on-chain-lookup`, not `on_chain_lookup`
- **Descriptive**: `whale-watcher`, not `ww`
- **No prefixes**: `price-tracker`, not `skill-price-tracker`
- **Directory match**: `id` in manifest.json must match the directory name

## Code Standards

### index.ts

- **Synchronous execution** — No async/await; use `net.fetch()` with timeout
- **JSON string results** — Tool execute functions must return JSON strings
- **SQL parameters** — Always use `?` placeholders, never string interpolation
- **Error handling** — Use `try/catch` for operations that might fail
- **No hardcoded secrets** — Use `platform.env()` or setup flow for credentials

### Setup Flow

- Each step should validate by actually testing the configuration (e.g., calling an API)
- On completion, persist config via `store.set("config", ...)`
- Handle cancel gracefully — clean up any transient state

### Testing

- Create `__tests__/test-my-skill.ts` for unit tests
- Use `setupSkillTest()` to configure mock state
- Use `callTool()` to test tools
- Use `getMockState()` to inspect mock internals

## What Gets Rejected

1. **Missing manifest.json** — every skill needs a manifest with id, runtime, entry
2. **Hardcoded secrets** — API keys, tokens, private keys in code
3. **Async code** — QuickJS doesn't support async/await in skills
4. **Name mismatches** — directory name must match manifest.json id
5. **Failing type checks** — `yarn typecheck` must pass
6. **Security issues** — no eval(), no dynamic code execution
7. **Broken setup flow** — if setup is required, it must work correctly
8. **Validation failures** — `yarn validate` must pass

## PR Review Process

1. **Automated CI** runs build, type checking, linting, validation, and tests
2. **Maintainer review** checks quality, clarity, and safety
3. **Feedback round** — you may be asked to make changes
4. **Merge** — skill becomes available to AlphaHuman users

## Getting Help

- Check [README.md](README.md) for detailed guides
- Check [`src/example-skill/`](src/example-skill/) for a complete working example
- Check existing skills in `src/` for patterns
- Open an issue for questions or feature requests
