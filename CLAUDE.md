# Card Reader for Claude Code

Use the shared project instructions:

@AGENTS.md

## Documentation discovery

The maintained documentation index is imported below. Read the relevant guides
before changing their feature or workflow; the Campaign plan describes proposed
work rather than an implemented contract.

@docs/README.md

For setup and runtime commands, read [README.md](README.md). Package details live
in [API](services/api/README.md), [Core](services/core/README.md),
[Parser](services/parser/README.md), and
[Integration tests](services/integration/README.md). The documentation index also
links the database diagram and [TTS importer guide](tts/README.md).

## Skill discovery

Project skills are discoverable under `.claude/skills/`, including through
`/card-reader-api`, `/card-reader-frontend`, and the other `card-reader-*` commands.
Each entry is a small wrapper that directs you to the full, canonical skill in
`.codex/skills/<skill-name>/SKILL.md`. Read that file before doing the skill's work,
including any resources it references. Repository paths resolve from this root.

Choose skills by their descriptions and the task's scope. When a canonical skill
names another project skill, read its matching `.codex/skills/` entry as needed.
Codex's `$skill-name` invocation syntax corresponds to `/skill-name` in Claude Code.

Maintain workflow instructions in `.codex/skills/`; keep only the matching name,
description, and canonical-file link in each Claude wrapper. When adding, renaming,
or removing a project skill, update its wrapper too. Keep the wrapper description
aligned with the canonical frontmatter so automatic discovery has the same scope.
