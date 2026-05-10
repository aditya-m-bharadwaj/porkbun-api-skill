# Project memory layer

This directory is the project's **canonical, tracked** memory: decision records, session-by-session progress notes, and the reference API spec. It is the same layout used by the sister project [`linode-api-skill`](https://github.com/aditya-m-bharadwaj/linode-api-skill).

## Layout

```
docs/
├── README.md                                ← you are here
├── api-spec.json                            ← Porkbun v3 OpenAPI spec (the build target)
├── progress/                                ← session-by-session progress notes
│   ├── TEMPLATE.md
│   └── YYYY-MM-DD-<slug>.md
└── decisions/                               ← ADRs (numbered monotonically)
    ├── TEMPLATE.md
    └── NNNN-<slug>.md
```

## What lives where

| Layer | Path | Tracked by git? | What lives there |
| --- | --- | --- | --- |
| **In-repo canonical** | `docs/` | yes | ADRs, progress notes, API spec |
| **Live code graph** | `graphify-out/` | no (auto-regenerated) | `GRAPH_REPORT.md`, `graph.json`, `graph.html`. Rebuilt by the graphify post-commit hook |
| **Operator's centralized vault** | `~/.claude/vault/` | no (lives outside the repo) | Cross-project graphify snapshots at `graphify/porkbun-api-skill/`; cross-project concept notes at `zettel/concepts/` |

The split rule: anything that should ship with the repo or guide a contributor goes in `docs/`. Anything that's a working surface for the operator's personal Obsidian / graphify workflow goes in `~/.claude/vault/`.

## How `/resume` and `/save` use it

`/resume` (project-level slash command at `.claude/commands/resume.md`) reads, in order:

1. The most recent file in `progress/`.
2. `../graphify-out/GRAPH_REPORT.md` (run `graphify update .` first if absent on a fresh clone).
3. The 3 most recent files in `decisions/`.
4. `api-spec.json` if a CLI question is open.

`/save` (project-level slash command at `.claude/commands/save.md`) writes:

- A new progress note at `progress/YYYY-MM-DD-<slug>.md` summarizing the just-finished session.
- A new ADR at `decisions/NNNN-<slug>.md` if the session made a material design decision.
- Optionally, a cross-project concept note at `~/.claude/vault/zettel/concepts/<concept>.md` if a reusable pattern came up.

**Commit alongside code, not after.** Docs that describe a code change belong in the same commit (or commit batch) as the change. Don't land code first and docs as a trailing commit — this leaves `git log` lying about rationale and stales `/resume`.

## How to add an entry yourself

- **New progress note**: copy `progress/TEMPLATE.md` → `progress/YYYY-MM-DD-<short-slug>.md` and fill it in.
- **New ADR**: read the highest-numbered file in `decisions/`, use the next number, copy `decisions/TEMPLATE.md` → `decisions/NNNN-<short-slug>.md`. Wikilink to related ADRs (`[[NNNN-other-decision]]`).
- **New concept note (cross-project)**: create at `~/.claude/vault/zettel/concepts/<concept-slug>.md`. Don't put concept notes in this repo's `docs/`.

## Obsidian + MCP (optional, operator-side)

Open `~/.claude/vault/` (the operator's centralized vault) as your single working vault across projects. Configure the Obsidian MCP server (e.g. [`iansinnott/obsidian-claude-code-mcp`](https://github.com/iansinnott/obsidian-claude-code-mcp), default port `localhost:22360`) to point at the same vault. Then `/resume` and `/save` interact via MCP rather than raw filesystem.

For contributors who don't use Obsidian, this `docs/` directory is sufficient — open it as a vault directly, or read it as plain markdown.

## API spec

`api-spec.json` is the Porkbun v3 OpenAPI spec, captured at project scaffold time. It is the build target: the CLI's classifier table, named commands, and `api` gateway all derive from it. When the upstream Porkbun spec changes, regenerate this file (currently a manual fetch from <https://porkbun.com/api/json/v3/spec>) and write an ADR describing what diff matters.
