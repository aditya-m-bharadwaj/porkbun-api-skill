---
number: 0007
title: SemVer 2.0.0 with `-alpha.N` / `-beta.N` / `-rc.N`
date: 2026-05-11
status: accepted
---

# 0007 — SemVer 2.0.0 with `-alpha.N` / `-beta.N` / `-rc.N`

## Context

We need a single, well-understood version scheme that signals:

- pre-1.0 means "API surface and behavior may break between releases";
- alpha → beta → rc → 1.0.0 progression conveys readiness;
- machine-comparable so install scripts and CI can reason about it.

The sister project `linode-api-skill` chose SemVer 2.0.0 with `-alpha.N` for the same reasons. We carry that over.

## Decision

Versions are strict [SemVer 2.0.0](https://semver.org/spec/v2.0.0.html). Pre-1.0 pre-release identifiers are `alpha.N`, `beta.N`, `rc.N` in that order, e.g.:

- `0.1.0-alpha.1` — first cut, alpha period
- `0.1.0-alpha.2` — bugfix during alpha
- `0.1.0-beta.1` — feature-complete enough for beta testers
- `0.1.0-rc.1` — release candidate
- `0.1.0` — first stable release; only after this does the API become a contract

Stored as the `VERSION` constant in `bin/porkbun-api-skill`. Reported by `porkbun-api-skill --version`. Tagged in git as `v<version>`.

If/when we publish to PyPI, the string is translated to PEP 440 form at build time (`0.1.0-alpha.1` → `0.1.0a1`); the canonical version in source remains SemVer.

## Consequences

- Pre-1.0 releases can break the CLI surface or storage format without bumping major. Documented in CHANGELOG and SECURITY.md.
- Tooling (install scripts, `gh release create --prerelease`) understands the convention.
- A future PyPI publish needs a small translation step at build time.

## Alternatives considered

- **CalVer.** Doesn't signal API stability.
- **0.0.X for everything pre-1.0.** Loses the alpha → beta → rc readiness signal.
- **Skip pre-release identifiers and use 0.X.Y.** Acceptable but less expressive.

## Related

- Sister project: [`linode-api-skill` ADR-0007](https://github.com/aditya-m-bharadwaj/linode-api-skill/blob/main/docs/decisions/0007-versioning-semver.md).
