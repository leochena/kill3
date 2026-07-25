# Agent-agnostic skill package

This directory is a **portable skill**: any general agent that can load markdown instructions can use it.

## Layout

```
skills/free-match/
  SKILL.md                 # primary instructions (Claude Code frontmatter + body)
  references/              # protocol, matching, roles, discovery
```

## Claude Code

```bash
ln -sfn "$(pwd)/skills/free-match" ~/.claude/skills/free-match
# or project-local:
mkdir -p .claude/skills
ln -sfn "$(pwd)/skills/free-match" .claude/skills/free-match
```

Then invoke `/free-match` or let the model auto-trigger on trade intents.

## Other agents (Cursor, OpenAI custom GPT, open agents, etc.)

1. Load `SKILL.md` into the system / tool instruction context.
2. Attach `references/*.md` and optionally repo `protocol/SPEC.md`.
3. Point file tools at `runtime/board/messages/` or your own transport.
4. Require the agent to emit Free-Match v1 JSON envelopes for durable state.

## Non-goals for integrators

Do not wrap this skill with:

- mandatory KYC gates
- category ban lists as protocol
- take-rate middleware on messages

Optional user-local filters are fine; they are not free-match core.
