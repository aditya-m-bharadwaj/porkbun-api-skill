# Changelog

All notable changes are documented here. Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this project adheres to [Semantic Versioning 2.0.0](https://semver.org/spec/v2.0.0.html). Pre-1.0 releases (alpha / beta / rc) may include breaking changes between iterations; the public API is considered stable starting at `1.0.0`.

## [Unreleased]

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
