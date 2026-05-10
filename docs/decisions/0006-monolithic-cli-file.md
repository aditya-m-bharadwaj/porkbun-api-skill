---
number: 0006
title: Monolithic single-file CLI
date: 2026-05-11
status: accepted
---

# 0006 — Monolithic single-file CLI

## Context

Should `bin/porkbun-api-skill` be one file, or should the code be split into a Python package (`src/porkbun_api_skill/{auth,classifier,commands,...}.py`)?

The sister project `linode-api-skill` is monolithic (~1500 LOC in `bin/linode-api-skill`). The argument for monolithic carries over almost unchanged:

- A single file is auditable in one pass — no jumping between modules to find the request path.
- AI agents working in the repo can `Read` the whole file once and reason about it.
- The CLI is installed as a symlink, not a package; no `__main__.py` / `pyproject.toml` overhead.
- The surface is small enough to fit (~1000-1500 LOC for a stdlib-only Porkbun client).

## Decision

`bin/porkbun-api-skill` is a single executable Python file. Sections are demarcated by comment banners (`# ---------- Section name ----------`), in roughly this order:

1. Module docstring + version constant
2. Constants & regex
3. Errors
4. Path validation
5. Credential storage (Keychain / libsecret / file)
6. HTTP layer (`_request`, idempotency-key insertion, error parsing)
7. Pagination
8. Safety classifier (`_normalize_path`, `classify`, tables)
9. Audit log
10. Named-command handlers (`cmd_whoami`, `cmd_balance`, `cmd_domains`, `cmd_register`, `cmd_dns_list`, ...)
11. Generic `api` command
12. Argparse / `build_parser()`
13. `main()`

Tests live in `tests/test_classify.py` (etc.) and load the script via `importlib.machinery.SourceFileLoader`, mirroring linode-api-skill.

## Consequences

- One `Read` call covers the whole CLI.
- Refactoring is per-section; section banners make grep-by-section trivial.
- If/when the file grows past ~2.5k LOC, this decision should be revisited. (Linode-api-skill at ~1.5k LOC is still comfortable.)

## Alternatives considered

- **Python package** (`src/porkbun_api_skill/`). Standard for larger projects; over-engineered for the surface.
- **`click`-based CLI in a package.** Pulls in a dependency, contradicts ADR-0001.
- **Generated CLI from the OpenAPI spec.** Tempting (we *have* the spec). But a generator either pulls a dependency (`openapi-generator`) or we hand-roll one — and the classifier table is the most important piece, which a generator can't infer.

## Related

- Sister project: [`linode-api-skill` ADR-0006](https://github.com/aditya-m-bharadwaj/linode-api-skill/blob/main/docs/decisions/0006-monolithic-cli-file.md).
- ADRs: [[0001-stdlib-only-python]].
