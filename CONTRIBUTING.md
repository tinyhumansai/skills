# Contributing to AlphaHuman Skills

Thank you for contributing to the AlphaHuman skills ecosystem. This guide covers everything you need to submit a skill.

## Ways to Contribute

1. **Create a new skill** — Add capabilities to the AlphaHuman agent
2. **Improve an existing skill** — Better tools, bug fixes, more handlers
3. **Improve tooling** — Enhance dev tools, CI, documentation
4. **Add examples** — Show patterns others can follow

## Creating a New Skill

### 1. Setup

```bash
# Fork and clone
git clone https://github.com/YOUR-USERNAME/alphahuman-skills.git
cd alphahuman-skills

# Install dev tools
pip install -e dev/

# Create a branch
git checkout -b skill/my-skill-name
```

### 2. Scaffold

```bash
python -m dev.scaffold.new_skill my-skill
```

Or manually copy `examples/tool-skill/` to `skills/your-skill-name/`.

### 3. Write skill.py

Every skill needs a `skill.py` that exports a `SkillDefinition`:

- `name` must be lowercase-hyphens matching the directory name
- `description` — one sentence explaining what the skill does
- `version` must be semver (X.Y.Z)
- `hooks` — lifecycle handlers (on_load, on_tick, etc.)
- `tools` — list of AI-callable tools with JSON Schema parameters

### 4. Write setup.py (Optional)

If your skill needs interactive configuration (API keys, auth flows):

- Export `on_setup_start(ctx)` → returns the first `SetupStep`
- Export `on_setup_submit(ctx, step_id, values)` → returns `SetupResult` (next/error/complete)
- Export `on_setup_cancel(ctx)` → cleanup on user abort
- Set `has_setup=True` in the `SkillDefinition`

### 5. Validate

```bash
# Structure and type checks
python -m dev.validate.validator

# Security scan
python -m dev.security.scan_secrets

# Test harness (runs hooks + tools with mock context)
python -m dev.harness.runner skills/my-skill --verbose

# Test setup flow interactively
python test-setup.py skills/my-skill

# Interactive server REPL — browse tools, call them live
python test-server.py
```

### 6. Submit

```bash
git add skills/my-skill/
git commit -m "Add my-skill"
git push -u origin skill/my-skill
```

Open a pull request. Fill out the PR template completely.

## Naming Conventions

- **Lowercase only**: `price-tracker`, not `Price-Tracker`
- **Hyphens for spaces**: `on-chain-lookup`, not `on_chain_lookup`
- **Descriptive**: `whale-watcher`, not `ww`
- **No prefixes**: `price-tracker`, not `skill-price-tracker`
- **Directory match**: `name` in skill.py must match the directory name

## Code Standards

### skill.py

- No pip dependencies beyond the skill's declared `dependencies` in manifest.json
- No `eval()`, `Function()`, or dynamic code execution
- No direct filesystem access outside `data_dir` — use `ctx.read_data()` / `ctx.write_data()`
- All hooks must complete within 10 seconds
- Use `try/except` for operations that might fail
- Tools must return `ToolResult(content=...)` with a string

### setup.py

- Setup state should be module-level (transient, not persisted)
- Each step validates by actually testing the configuration (e.g., connecting to an API)
- On completion, persist config via `ctx.write_data("config.json", ...)`
- Handle cancel gracefully — clean up connections and transient state

## What Gets Rejected

1. **Missing skill.py** — every skill needs a `skill.py` with a `skill` export
2. **Hardcoded secrets** — API keys, tokens, private keys in code
3. **Dangerous code** — eval(), exec(), dynamic imports from user input
4. **Name mismatches** — directory name must match skill.py name
5. **Failing validation** — `python -m dev.validate.validator` must pass
6. **Security issues** — `python -m dev.security.scan_secrets` must not report errors
7. **Broken setup flow** — if `has_setup=True`, setup hooks must work correctly

## PR Review Process

1. **Automated CI** runs validation, security scanning, and test harness
2. **Maintainer review** checks quality, clarity, and safety
3. **Feedback round** — you may be asked to make changes
4. **Merge** — skill becomes available to AlphaHuman users

## Getting Help

- Check [docs/](docs/) for detailed guides
- Open an issue for questions or feature requests
