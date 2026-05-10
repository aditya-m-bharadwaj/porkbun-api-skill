---
number: 0001
title: Stdlib-only Python for the CLI
date: 2026-05-11
status: accepted
---

# 0001 — Stdlib-only Python for the CLI

## Context

`porkbun-api-skill` is meant to be installable in seconds on any developer's machine, runnable by AI agents that don't want to manage a virtualenv, and copy-pasteable as a single file for audit. Adding dependencies (`requests`, `click`, `pydantic`, `keyring`, ...) would force users to manage a virtualenv, increase the audit surface, and create platform-specific install headaches.

The sister project [`linode-api-skill`](https://github.com/aditya-m-bharadwaj/linode-api-skill) made the same choice for the same reasons (see its ADR-0001). The audit surface and install-friction arguments transfer 1:1.

## Decision

`bin/porkbun-api-skill` is **stdlib-only Python**. Target: Python 3.8+. Uses only `argparse`, `urllib.request`, `urllib.parse`, `json`, `subprocess`, `secrets`, `getpass`, `pathlib`, `uuid` (for idempotency keys), and similar standard-library modules. No third-party packages, ever.

Tests use only `unittest`, run via `python -m unittest discover tests`.

## Consequences

- One-line install. No virtualenv, no `pip install`.
- Easy to audit — every line is in `bin/porkbun-api-skill`, no transitive dependencies to vet.
- Slower to write some things (HTTP retry/backoff, multipart, SSL cert parsing) than with `requests`, but Porkbun's API is JSON-only and the surface is small.
- We accept some boilerplate (manual `urllib` request construction, hand-rolled retry) in exchange for the audit story.

## Alternatives considered

- **`requests` + `click` + `keyring`** — ergonomic, but a 4-package dependency tree and an opinionated CLI framework. Rejected: install friction and audit surface.
- **A Rust or Go binary** — fast, statically linked, but a much higher bar for contributor-side modifications and harder for AI agents to read/extend.
- **The official `@porkbunllc/mcp-server`** — exists and is high-quality, but is an *AI integration*, not a CLI. We want both surfaces (CLI for humans/scripts + Claude skill for AI), and we want the AI to drive a tool that other tooling can also use.

## Related

- Sister project: [`linode-api-skill` ADR-0001](https://github.com/aditya-m-bharadwaj/linode-api-skill/blob/main/docs/decisions/0001-stdlib-only-python.md).
- ADRs: [[0006-monolithic-cli-file]].
