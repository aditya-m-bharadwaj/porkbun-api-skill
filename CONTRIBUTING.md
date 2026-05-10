# Contributing to `porkbun-api-skill`

Welcome. This document captures the rules that make `porkbun-api-skill` what it is.

## Hard rules

1. **Stdlib only.** No third-party Python dependencies, ever. The CLI must remain installable as a single file with nothing more than CPython 3.8+. See [docs/decisions/0001-stdlib-only-python.md](docs/decisions/0001-stdlib-only-python.md).
2. **One file.** `bin/porkbun-api-skill` is a single executable Python file with section banners. See [docs/decisions/0006-monolithic-cli-file.md](docs/decisions/0006-monolithic-cli-file.md).
3. **Every write call carries an `Idempotency-Key`.** Don't add a write path that bypasses `_request`'s auto-attach. See [docs/decisions/0008-idempotency-key-on-write-ops.md](docs/decisions/0008-idempotency-key-on-write-ops.md).
4. **Credentials never enter argv, env, logs, or stdout.** They flow into a `subprocess.run(..., capture_output=True)` buffer in Python memory and from there into the OS keystore. Nowhere else.
5. **Every mutation goes through the classifier.** If you add a new endpoint to a named command or to `api`, add it to the classifier table at the same time. The CLI refuses unrecognized POSTs only at the default mutating level — destructive must be explicit, and billable / privilege must be in the table.

## Tests

Tests are offline-only `unittest`s in `tests/test_*.py`. They load `bin/porkbun-api-skill` via `importlib.machinery.SourceFileLoader` and exercise the classifier, path validation, and helpers without touching the network or the keystore. Add tests when you add classifier entries or change normalization logic.

```sh
python3 -m unittest discover tests
```

## Commit-message format

Every commit follows this format:

```
type(scope): short subject

Brief description.

- Bullet per logical change.

Prompted-By: <operator name> <operator email>
Co-Authored-By: <model name and version> <noreply address>
```

- **`type`** ∈ {`feat`, `fix`, `docs`, `chore`, `refactor`, `test`, `perf`, `ci`, `build`}.
- **`scope`** is the section of the code touched, e.g. `classify`, `auth`, `dns`, `domain`, `gui-setup`, `api`, `memory`, `github`.
- **`Prompted-By:`** — the human who directed the commit. Read from `git config user.name` / `git config user.email` if not told otherwise.
- **`Co-Authored-By:`** — the AI model that wrote the code. Use the actual model identifier you're running as (e.g. `Claude Opus 4.7 (1M context) <noreply@anthropic.com>`).
- Add trailers only when the AI materially shaped the commit; omit on hand-typed changes.
- One logical change per commit. Split unrelated work.
- Never bypass commit hooks (`--no-verify`, `--no-gpg-sign`) without an explicit per-commit instruction from the operator.

**Docs go in the same commit as the code they describe** — not as a trailing `docs(...)` commit. The progress note for a session, the ADR if the session made a material decision, the SKILL.md / CHANGELOG / README updates: stage them alongside the code in the same commit (or same commit batch). See [docs/decisions/0005-prompted-by-trailer-convention.md](docs/decisions/0005-prompted-by-trailer-convention.md) for the rationale on the trailers, and the memory protocol in [CLAUDE.md](CLAUDE.md#memory-protocol-binding-for-resume-save-and-any-agent-in-this-repo) for the docs-in-the-same-commit rule.

## Extending the classifier

If Porkbun adds a new endpoint:

1. Add the path + method to the appropriate table:
   - `_DESTRUCTIVE_EXACT` for any POST that deletes a user-created resource.
   - `_BILLABLE_EXACT` for any POST that charges account credit.
   - `_PRIVILEGE_PREFIXES` (or `_PRIVILEGE_EXACT`) for any POST that issues credentials, grants access, or returns private key material.
   - `_MUTATING_EXACT` for explicit-classification mutating ops (e.g. when the path could otherwise be misread).
2. Add a test in `tests/test_classify.py` covering the new path under both `/v3/...` and `/...`.
3. Update `.claude/skills/porkbun-api-skill/SKILL.md`'s resource-category table.

## Reporting issues

Public issues for bugs and feature requests; **private security advisory** for vulnerabilities (see [SECURITY.md](SECURITY.md)).
