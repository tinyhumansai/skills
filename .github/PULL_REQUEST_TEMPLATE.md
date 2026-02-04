## Skill Submission

**Skill name**: `skill-name-here`
**Type**: [ ] Prompt-only | [ ] Coded (skill.ts)

### Description

Brief description of what this skill does and why it's useful.

### Checklist

- [ ] `SKILL.md` has valid YAML frontmatter (`name`, `description`)
- [ ] Skill name matches directory name (lowercase-hyphens)
- [ ] Instructions are clear enough for an AI agent to follow
- [ ] Examples demonstrate expected usage
- [ ] No hardcoded API keys, tokens, or secrets
- [ ] No `eval()`, `Function()`, or dynamic code execution
- [ ] No direct filesystem or network access (use `ctx.readData`/`ctx.writeData`)
- [ ] If coded: `skill.ts` has name, description, version
- [ ] If coded: all hooks complete within 10 seconds
- [ ] If coded: tools have JSON Schema parameters and return `{ content: string }`
- [ ] Tested locally with `npx tsx harness/runner.ts ../skills/my-skill`
- [ ] `npm run validate` passes in `dev/`

### Testing

Describe how you tested this skill:

1.
2.
3.

### Category

- [ ] DeFi
- [ ] Trading
- [ ] Research
- [ ] Community
- [ ] NFT
- [ ] Security
- [ ] Other: \_\_\_
