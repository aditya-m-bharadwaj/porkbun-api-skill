---
number: 0005
title: "`Prompted-By:` + `Co-Authored-By:` trailers on AI-shaped commits"
date: 2026-05-11
status: accepted
---

# 0005 — `Prompted-By:` + `Co-Authored-By:` trailers on AI-shaped commits

## Context

Most of this project's commits are landed by a Claude agent on the operator's behalf. We want the commit history to be honest about that: the human who directed the work and the model that wrote the code should both be discoverable from `git log`. We also want a single convention that any AI agent working in this repo will follow without re-asking.

The sister project `linode-api-skill` established this exact convention. The reasoning carries over unchanged.

## Decision

Every commit shaped materially by an AI carries two trailers in this order:

```
Prompted-By: <operator name> <operator email>
Co-Authored-By: <model name and version> <noreply address>
```

- `Prompted-By:` identifies the human who directed the commit. Read from `git config user.name` / `git config user.email` if not told otherwise — this project is open source and any contributor may direct an AI.
- `Co-Authored-By:` identifies the model that wrote the code. Use the actual model identifier (e.g. `Claude Opus 4.7 (1M context) <noreply@anthropic.com>`).
- Omit the trailers on hand-typed commits that the AI did not shape.

This is codified in [CLAUDE.md](../../CLAUDE.md) and [CONTRIBUTING.md](../../CONTRIBUTING.md). Any AI agent operating in this repo must read CLAUDE.md before its first commit.

## Consequences

- Honest history of who/what wrote each commit.
- GitHub renders `Co-Authored-By:` as a co-author chip; cleanly surfaces AI involvement.
- Slightly longer commit messages.
- Trivial drift risk: agents may guess a wrong model version. Mitigated by CLAUDE.md telling them to use the actual model id they're running as.

## Alternatives considered

- **Don't credit AI involvement.** Misleads collaborators about who/what wrote each commit.
- **A single `Authored-By:` trailer combining both.** Loses the human-directed-by signal that `Prompted-By:` carries.
- **Co-author the human via `Co-Authored-By:` only.** Doesn't distinguish "directed" from "wrote".

## Related

- Sister project: [`linode-api-skill` ADR-0005](https://github.com/aditya-m-bharadwaj/linode-api-skill/blob/main/docs/decisions/0005-prompted-by-trailer-convention.md).
