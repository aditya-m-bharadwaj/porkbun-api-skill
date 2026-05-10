# Project: Porkbun-API Skill (`porkbun-api-skill`)

A safe, cross-platform CLI (`porkbun-api-skill`) for the entire Porkbun v3 API, plus a matching Claude skill that drives it. The skill at [.claude/skills/porkbun-api-skill/SKILL.md](.claude/skills/porkbun-api-skill/SKILL.md) is authoritative for runtime behavior — read it before acting on any Porkbun-related request.

This project is the **sister** of [`linode-api-skill`](https://github.com/aditya-m-bharadwaj/linode-api-skill). Same vision (AI-safe single-file CLI for a cloud-platform API), same architecture (six-tier classifier, OS keystore, AI-safe credential entry via GUI dialog, audit log, monolithic file), adapted for Porkbun's dual-key auth and registrar-domain semantics. When a question is ambiguous, prefer the linode-api-skill answer unless it conflicts with a Porkbun-specific rule below.

## Hard rules (override anything else)

1. **Never read the user's Porkbun API credentials** or their storage (macOS Keychain, libsecret, file at `~/.porkbun-api-skill/credentials.json`, `PORKBUN_API_KEY` / `PORKBUN_SECRET_API_KEY` env vars). Do not run `security find-generic-password`, `secret-tool lookup`, `printenv PORKBUN_*`, `env | grep PORKBUN`, or `cat ~/.porkbun-api-skill/credentials.json`. **Porkbun uses two secrets** — the API key *and* the secret API key — both must never enter your context.
2. **Never call the Porkbun API directly** with `curl`/`wget`/`requests`. Always go through `./bin/porkbun-api-skill` (or `porkbun-api-skill` if installed). Direct API calls bypass classification, idempotency-key insertion, and the audit log.
3. **Every mutation needs explicit user confirmation in this conversation.** The CLI's `--yes` is the *machine* gate; the user's "yes" in chat is the *human* gate.
4. **Respect classifier output.** The CLI categorizes every endpoint as `read`, `mutating`, `destructive`, `billable`, or `privilege`, and refuses mutations without the matching flags. Porkbun does not have a distinct `financial` tier (no payment-method endpoints in the v3 API); billing/account credit interactions fall under `billable`. If you don't know an endpoint's classification, run `porkbun-api-skill classify <METHOD> <path>` before you plan the call.
5. **Domain-registration calls (`/domain/create`, `/domain/renew`, `/domain/transfer`) ALWAYS need a fresh `/domain/checkDomain` or `/pricing/get` price quote first**, echoed to the user in chat, with the user explicitly confirming the dollar amount. The Porkbun API takes a `cost` parameter in pennies; the CLI must pass `--cost-cents <N>` matching the just-quoted price, and the user's chat-side confirmation must restate it.
6. **Use `Idempotency-Key` on every write call.** Porkbun's v3 API caches responses for 24h keyed on the `Idempotency-Key` header. The CLI must generate and attach one for every POST (excluding partner routes), so that a network blip + retry can never double-register or double-charge.

## Auth model (different from linode-api-skill)

Porkbun authenticates with **a pair** of secrets:
- `apikey` (public-prefixed, looks like `pk1_...`)
- `secretapikey` (looks like `sk1_...`)

Storage: a single JSON blob `{"apikey": "...", "secretapikey": "..."}` in the OS keystore under service `porkbun-api-skill`, or as a file at `~/.porkbun-api-skill/credentials.json` (mode `0600`).

For AI-runnable token entry, `porkbun-api-skill gui-setup` should pop **one** native OS dialog that captures *both* values (a small form with two password fields), validates by calling `POST /ping` with the pair, and stores them as a unit. Neither key ever crosses Claude's context.

## "Set up the credentials"

Tell the user to run `./bin/porkbun-api-skill setup` (or `porkbun-api-skill setup`) themselves. You cannot — it reads from a TTY, which you don't have. AI-runnable alternative: `porkbun-api-skill gui-setup` (native OS dialog).

## DNS-record safety

Domain DNS records are user-visible infrastructure. Editing or deleting an `A`/`AAAA`/`MX` record can cause production outages.

- For `dns/edit` or `dns/delete`, the CLI requires `--confirm-id <record-id>` matching the path's `id` segment (the destructive tier flag matrix).
- For batch deletes via `dns/deleteByNameType` (which can delete *multiple* records matching a type+subdomain pattern), the CLI should *list the records that would be deleted* with `--dry-run` first, then require `--confirm-name <subdomain>` matching the exact subdomain.
- Never delete records on a domain you weren't asked to touch.

## Versioning

SemVer with `-alpha.N` / `-beta.N` / `-rc.N` pre-release identifiers — same as linode-api-skill (see [docs/decisions/0007-versioning-semver.md](docs/decisions/0007-versioning-semver.md)).

## Cross-platform notes

Credential storage by platform: macOS Keychain → Linux Secret Service (libsecret) → file fallback at `~/.porkbun-api-skill/credentials.json` (mode 600). The CLI picks the strongest available backend at run time. The JSON blob holds both `apikey` and `secretapikey`.

## Memory protocol (binding for /resume, /save, and any agent in this repo)

Identical to linode-api-skill's protocol. Project memory is split:

| Layer | Location | Tracked by git? | What lives there |
| --- | --- | --- | --- |
| **In-repo canonical** | `docs/` | yes | Decision records (ADRs), session-by-session progress notes |
| **Live code graph** | `graphify-out/` | no (auto-regenerated) | `GRAPH_REPORT.md`, `graph.json`, `graph.html`. Rebuilt by graphify post-commit hook |
| **Operator's centralized vault** | `~/.claude/vault/` | no (lives outside the repo) | Cross-project graphify snapshots at `graphify/porkbun-api-skill/`; cross-project concept notes at `zettel/concepts/` |

In-repo layout:

```
docs/
├── README.md                                ← memory layer index
├── api-spec.json                            ← Porkbun v3 OpenAPI spec (the build target)
├── progress/                                ← session-by-session progress notes
│   ├── TEMPLATE.md
│   └── YYYY-MM-DD-<slug>.md
└── decisions/                               ← ADRs (numbered)
    ├── TEMPLATE.md
    └── NNNN-<slug>.md
```

`graphify-out/` (gitignored, in repo root) contains the live code-structure graph. After cloning, run `graphify update .` once to populate it; the post-commit hook keeps it fresh thereafter.

### `/resume` reads, in order:

1. The most recent file in `docs/progress/` (sorted by filename = sorted by date).
2. `graphify-out/GRAPH_REPORT.md` for current code structure (run `graphify update .` first if absent on a fresh clone).
3. The 3 most recent files in `docs/decisions/`.
4. `docs/api-spec.json` if a CLI question is open.

Then summarizes: where we left off, what's in-flight, what's next, open questions.

### `/save` writes:

- A new progress note at `docs/progress/YYYY-MM-DD-<slug>.md` summarizing the just-finished session.
- If a material design decision was made, a new ADR at `docs/decisions/NNNN-<slug>.md`.

### Documentation goes with the code

When committing a code change, **include the progress note / ADR / SKILL update / CHANGELOG entry in the same commit (or commit batch) as the code change it documents**. Do not land code first and documentation as a trailing commit — this leaves `git log` lying about rationale and makes `/resume` stale. The only exception is if the operator explicitly says "draft the progress note and stop".

## Commit-message rules (binding for any AI agent in this repo)

Identical to linode-api-skill. Format:

```
type(scope): short subject

Brief description.

- Bullet per logical change.

Prompted-By: <operator name> <operator email>
Co-Authored-By: <model name and version> <noreply address>
```

- **`type`** ∈ {`feat`, `fix`, `docs`, `chore`, `refactor`, `test`, `perf`, `ci`, `build`}.
- **`Prompted-By:`** identifies the human who directed the commit. Use the current operator's name and email — read from `git config user.name` / `git config user.email` if not told otherwise.
- **`Co-Authored-By:`** identifies the model that wrote the code.
- Trailers only when the AI materially shaped the commit.
- One logical change per commit. Never bypass commit hooks without explicit per-commit instruction.

If the operator has not given explicit go-ahead to commit, draft the message and stop.

## graphify

This project has a graphify knowledge graph at `graphify-out/`.

- Before answering architecture or codebase questions, read `graphify-out/GRAPH_REPORT.md` for god nodes and community structure.
- If `graphify-out/wiki/index.md` exists, navigate it instead of reading raw files.
- For cross-module "how does X relate to Y" questions, prefer `graphify query "<question>"`, `graphify path "<A>" "<B>"`, or `graphify explain "<concept>"` over grep.
- After modifying code in this session, run `graphify update .` to keep the graph current (AST-only, no API cost).
