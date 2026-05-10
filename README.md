# `porkbun-api-skill`

> **Status:** `v0.0.0-scaffold` — scaffolding only. The CLI is not yet implemented. See [`docs/progress/2026-05-11-scaffold.md`](docs/progress/2026-05-11-scaffold.md) for what's done and what's next.

A safe, cross-platform CLI (`porkbun-api-skill`) for the entire [Porkbun v3 API](https://porkbun.com/api/json/v3/spec), plus a matching [Claude](https://claude.com/claude-code) skill that drives it under explicit AI-safety constraints. The credential pair (`apikey` + `secretapikey`) never enters AI context; every mutation passes through a five-tier safety classifier; every write call carries an `Idempotency-Key` so a retry can't double-register or double-charge.

This is the **sister project** of [`linode-api-skill`](https://github.com/aditya-m-bharadwaj/linode-api-skill) — same vision, same architecture, adapted for Porkbun's registrar-domain semantics and dual-key authentication.

## What it will do (when built)

- **Domain operations** — register, renew, transfer in, list, inspect, update nameservers, toggle auto-renew, manage glue records and URL forwarding. Every billable call (`register`/`renew`/`transfer`) requires a fresh price quote echoed to the user and a `--cost-cents <N>` flag matching the quote.
- **DNS management** — list, create, edit, delete records. Edits/deletes to `A`/`AAAA`/`MX`/`NS` require explicit confirmation; batch deletes via `deleteByNameType` require a dry-run preview first.
- **SSL bundle retrieval** — write certificate + private key to a mode-0600 file path; never echo private key material to chat.
- **Account info** — balance, API settings, invitations.
- **Generic `api` gateway** — `porkbun-api-skill api <METHOD> <path>` for anything not covered by a named command, gated by the same classifier.

## Why it doesn't exist yet

This repository is the scaffold. The actual CLI in `bin/porkbun-api-skill` is a placeholder stub that prints "not yet implemented." The next session is the build, following the contract in [.claude/skills/porkbun-api-skill/SKILL.md](.claude/skills/porkbun-api-skill/SKILL.md) and the ADRs in [docs/decisions/](docs/decisions/).

## Repository layout

```
porkbun-api-skill/
├── bin/porkbun-api-skill                ← single-file CLI (stub today)
├── tests/                               ← offline unittest suite
├── install.sh / install.ps1             ← one-line bootstrap installers (skeletons)
├── .claude/
│   ├── skills/porkbun-api-skill/SKILL.md  ← skill contract for any AI driving the CLI
│   ├── commands/{resume,save}.md        ← project-level slash commands
│   └── settings.json                    ← graphify PreToolUse hook
├── docs/
│   ├── api-spec.json                    ← Porkbun v3 OpenAPI spec (build target)
│   ├── README.md                        ← memory layer index
│   ├── progress/                        ← session-by-session progress notes
│   └── decisions/                       ← ADRs (0001–0008 seeded)
├── .github/                             ← workflows, issue/discussion templates, FUNDING
├── CLAUDE.md                            ← project hard rules + memory protocol for AI agents
├── README.md                            ← you are here
├── AUTHORS.md / SECURITY.md / CONTRIBUTING.md / CHANGELOG.md / LICENSE
└── graphify-out/                        ← live code graph (gitignored, auto-rebuilt)
```

## Project memory

Three layers, split by purpose:

- **`docs/`** (canonical, tracked) — ADRs, progress notes, the API spec.
- **`graphify-out/`** (live, gitignored, auto-rebuilt by post-commit hook) — code-structure graph used by AI agents to navigate before grepping.
- **`~/.claude/vault/`** (operator-side, lives outside the repo) — cross-project graphify snapshots and cross-project concept notes for the operator's Obsidian + MCP workflow.

See [`docs/README.md`](docs/README.md) for the protocol that `/resume` and `/save` follow.

## For AI agents

- Read [`CLAUDE.md`](CLAUDE.md) before doing anything. It carries the hard rules (never read credentials, never call the API directly, every mutation needs explicit chat confirmation, etc.).
- Read [`.claude/skills/porkbun-api-skill/SKILL.md`](.claude/skills/porkbun-api-skill/SKILL.md) for the per-resource confirmation playbooks and the classifier matrix.
- The CLI is the *only* interface to Porkbun. Direct `curl` / `requests` calls are explicitly forbidden.

## License

MIT. See [LICENSE](LICENSE).
