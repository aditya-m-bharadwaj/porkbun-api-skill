# Changelog

All notable changes are documented here. Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this project adheres to [Semantic Versioning 2.0.0](https://semver.org/spec/v2.0.0.html). Pre-1.0 releases (alpha / beta / rc) may include breaking changes between iterations; the public API is considered stable starting at `1.0.0`.

## [Unreleased]

### Fixed / Polished — post-alpha.1 papercuts (from 2026-05-13 live test on idwgit.cc)

- **`--json` works after a subcommand.** Previously `--json` was only defined on the top-level parser, so `porkbun-api-skill dns list <domain> --json` silently emitted human-readable output (and broke a downstream `python3 -c` pipe during the live test). The flag is now declared on a parent parser (`_global_parent()`) and inherited by every subparser via `parents=[common]`. Both positions work: `--json <subcmd>` and `<subcmd> ... --json`.
- **`--prio` is refused on non-MX/SRV record types.** `dns add` / `dns edit` now error with a clear message if `--prio` is passed for `A`, `AAAA`, `CNAME`, `NS`, `TXT`, `CAA`, etc. (priority is only meaningful for MX and SRV). Porkbun will still default `prio=0` server-side for those types — there's nothing the CLI can do about that — but the CLI no longer passes through a user-supplied value that the server quietly ignores.
- **`prio` hidden from `dns list` output for non-MX/SRV records.** Porkbun returns `prio=0` on every record regardless of type. `_format_summary` now suppresses the `prio=...` column for record types where it's meaningless.
- **`nameservers --set` surfaces Porkbun's `"No change"` response prominently.** When the API reports no change (because the registry's `/domain/updateNs` is set-based and ignores order), the CLI prints an explicit `NOTE:` warning instead of leaving the operator to spot it in the raw JSON. The `--set` help text now documents the set-based behavior.
- **`API_ACCESS_DISABLED` / `DOMAIN_IS_NOT_OPTED_IN_TO_API_ACCESS` errors get a friendlier redirect.** `_request` detects these codes and replaces Porkbun's auto-generated 100-character UPPERCASE_UNDERSCORED error with a one-liner pointing the operator at <https://porkbun.com/account/api> (account-wide toggle) or the domain's per-domain settings page.
- **`autoRenew` typing normalized on `domain <name>` output.** Porkbun returns `0` (int) when auto-renew is off and `"1"` (string) when on. The CLI's new `_normalize_auto_renew` helper coerces both forms to a stable string `"0"` / `"1"` so consumers don't have to special-case the typing inconsistency.
- **Tests**: +16 cases (68 total, all passing). Covers `--json` propagation in both positions, `_normalize_auto_renew` across int/string/bool/unknown inputs, `_format_summary` hiding `prio` for non-MX/SRV, and `dns add` refusing `--prio` for non-priority record types.

### Added — 0.1.0-alpha.1 — first functional CLI

- `bin/porkbun-api-skill` is no longer a stub — the full single-file CLI is implemented per the contract in [`.claude/skills/porkbun-api-skill/SKILL.md`](.claude/skills/porkbun-api-skill/SKILL.md) and ADRs 0001–0008.
- **Credential layer** (dual-key): JSON-blob storage in macOS Keychain / Linux Secret Service / file fallback (`~/.porkbun-api-skill/credentials.json`, mode 0600). `creds_get`/`creds_set`/`creds_delete` operate on the pair atomically. Env-var fallback reads `PORKBUN_API_KEY` + `PORKBUN_SECRET_API_KEY`.
- **HTTP layer** (`_request`): single entry point for every API call. Auto-attaches `X-API-Key` / `X-Secret-API-Key` headers from the keystore, and `Idempotency-Key: <uuid4>` on every POST unless the operator passes `--no-idempotency-key`. Strips any echo of the keys from error bodies before raising.
- **Five-tier safety classifier** (`classify`, `_normalize_path`): templates with `{domain}`/`{subdomain}`/`{id}`/`{type}`/`{keytag}` placeholders, sorted longest-first so specific matches win. Read-style POSTs (`/ping`, `/pricing/get`, `/dns/retrieve*`, `/domain/checkDomain`, ...) are explicitly marked `read` so they do not fall through to `mutating`. POST-to-`/delete*` routes are explicit-only on the `destructive` tier — no method-based default catches them. `/v3` and `/api/json/v3` prefixes are stripped.
- **Named commands**: `setup`, `gui-setup`, `uninstall-credentials`, `whoami`, `balance`, `domains` (paginated via `/domain/listAll` `start` offset), `domain`, `price`, `register` / `renew` / `transfer` (billable — each re-fetches `/domain/checkDomain` and refuses if quoted price ≠ `--cost-cents`), `auto-renew`, `nameservers --get/--set`, `dns list/add/edit/delete` (delete + edit require `--confirm-id` matching the path's id), `ssl` (privilege — writes timestamped bundle to `~/.porkbun-api-skill/ssl/<domain>.<ts>.{certificatechain,privatekey,publickey}.pem` mode 0600, never echoes to chat), `audit-log`, `classify`.
- **Generic `api` gateway**: `porkbun-api-skill api <METHOD> <path>` honors the same flag matrix; rejects unrecognized methods other than GET/POST (Porkbun's API has no DELETE/PUT).
- **AI-safe credential entry** (`gui-setup`): native OS dialog (osascript on macOS — two sequential `display dialog` calls; `zenity --forms --add-password` on Linux with kdialog fallback; `Get-Credential` on Windows with `UserName=apikey` / `Password=secretapikey` convention). Validates against `POST /ping` before storing. Captured bytes are never echoed.
- **Audit log**: `~/.porkbun-api-skill/audit.log` (mode 0600). One JSON line per mutation with timestamp, user, action, target, idempotency key, classification, and body-key list (never values, never credentials).
- **Test suite**: `tests/test_classify.py` expanded to 52 offline tests covering normalize-path, classification across all five tiers, path validation, domain validation, price-to-cents parsing, platform helpers, pack/unpack of the dual-key JSON blob, and CLI entrypoint smoke.

### Added — initial scaffold

- Sister-project scaffold for the Porkbun v3 API, modeled after [`linode-api-skill`](https://github.com/aditya-m-bharadwaj/linode-api-skill). No CLI yet — the next session is the build.
- `CLAUDE.md` — project-level hard rules + memory protocol + commit-message rules, adapted for Porkbun's dual-key auth and idempotency-key requirement.
- `.claude/skills/porkbun-api-skill/SKILL.md` — full skill contract with the five-tier classifier (read / mutating / destructive / billable / privilege; no `financial` tier because Porkbun has no payment-method endpoints), per-resource confirmation playbooks for domains / DNS / SSL / account / API keys / email, and credential-management workflow (dual-field GUI dialog).
- `.claude/commands/{resume,save}.md` — project-level slash commands matching the memory protocol; `/save` codifies "commit docs alongside code".
- `docs/api-spec.json` — Porkbun v3 OpenAPI spec captured from `/Users/aditya/Downloads/api-1.json`. The build target.
- Eight seed ADRs:
  - `0001-stdlib-only-python` (carry-over)
  - `0002-safety-classifier-five-tiers` (porkbun-specific — five tiers instead of six)
  - `0003-cross-platform-credential-pair-storage` (porkbun-specific — dual-key JSON blob, atomic)
  - `0004-ai-safe-credential-entry-gui-dialog` (porkbun-specific — dual-field native dialog)
  - `0005-prompted-by-trailer-convention` (carry-over)
  - `0006-monolithic-cli-file` (carry-over)
  - `0007-versioning-semver` (carry-over)
  - `0008-idempotency-key-on-write-ops` (porkbun-specific, defining decision)
- Initial progress note: `docs/progress/2026-05-11-scaffold.md` capturing what was scaffolded and the recommended pickup for the build session.
- Templates: `docs/progress/TEMPLATE.md`, `docs/decisions/TEMPLATE.md`.
- Public-face docs skeletons: `README.md`, `AUTHORS.md`, `SECURITY.md`, `CONTRIBUTING.md`, this file, `LICENSE`.
- `.github/` metadata: CI workflow (`workflows/ci.yml`), bug/feature issue templates + config (`ISSUE_TEMPLATE/`), discussion templates (`DISCUSSION_TEMPLATE/`), `FUNDING.yml`.
- `bin/porkbun-api-skill` — placeholder stub returning `not yet implemented`. **The CLI is not yet built.**
- `tests/test_classify.py` — single passing placeholder.
- `install.sh` / `install.ps1` — skeleton installers (paths and shape; not smoke-tested).
- `.gitignore` covering `.porkbun-api-skill/`, `graphify-out/`, `.claude/settings.local.json`, etc.

### Added — graphify integration

- Live code graph at `graphify-out/` (gitignored). Built with `graphify update .`.
- Post-commit hook auto-rebuilds the graph (installed via `graphify hook install`).
- PreToolUse Claude hook at `.claude/settings.json` (installed via `graphify claude install`) reminds the AI to consult `graphify-out/GRAPH_REPORT.md` before reaching for `grep`/`find`.

## [0.0.0-scaffold] — 2026-05-11 — initial scaffold (no CLI)

Initial commit. Repository layout, AI-facing prompts, memory layer, ADRs, and CI scaffolding only. `bin/porkbun-api-skill` is a stub.

This is **not** a usable release — there is no functional CLI. The next development session will implement the credential layer, HTTP layer with `Idempotency-Key` auto-attach, classifier, named commands, generic `api` gateway, GUI credential entry, and audit log per the contract in [`.claude/skills/porkbun-api-skill/SKILL.md`](.claude/skills/porkbun-api-skill/SKILL.md).
