---
number: 0002
title: Five-tier safety classifier for Porkbun endpoints
date: 2026-05-11
status: accepted
---

# 0002 — Five-tier safety classifier for Porkbun endpoints

## Context

Porkbun's API surface is small (41 endpoints in v3) but high-impact: it can register / transfer / delete domains (real money, real downtime), edit DNS records (production-breaking), retrieve SSL bundles (private key material), and issue new API keys (credential blast radius). An AI driver needs a deterministic, fail-closed mechanism that maps each endpoint to a category and refuses to mutate without an operator-supplied flag matching that category.

The sister project `linode-api-skill` uses six tiers (read / mutating / destructive / billable / financial / privilege) because Linode has a distinct cluster of `/account/payments`-style endpoints. Porkbun's API has *no separate financial endpoints* — billing happens automatically via account credit as a side effect of `/domain/create` etc.

## Decision

Five tiers:

| Tier | When | Required flags |
| --- | --- | --- |
| `read` | GET endpoints; idempotent POSTs that are documented as read-style (`/ping`, `/pricing/get`, `/dns/retrieve*`) | (none) |
| `mutating` | POST endpoints that change state but don't allocate paid resources or grant privileges (DNS create/edit, nameserver update, auto-renew toggle, URL-forward add, glue create/update, DNSSEC add) | `--yes` |
| `destructive` | POST endpoints whose name starts with `delete*` or that overwrite an `A`/`AAAA`/`MX`/`NS` record | `--yes --confirm-id <id>` (or `--confirm-name <subdomain>` for `deleteByNameType`) |
| `billable` | POST endpoints that charge account credit (`/domain/create`, `/domain/renew`, `/domain/transfer`) | `--yes --i-understand-billing --cost-cents <N>` (must match the freshly-quoted price) |
| `privilege` | POST endpoints that grant access, issue credentials, or return private key material (`/apikey/request`, `/apikey/retrieve`, `/account/invite`, `/email/setPassword`, **`/ssl/retrieve`**) | `--yes --allow-privilege` |

Unknown endpoints fall through to method-based defaults: GET → `read`, POST → `mutating`. Porkbun's API uses POST for deletes (no HTTP DELETE), so the destructive tier *must be populated explicitly* — there is no method-based default that catches it.

`/ssl/retrieve` is `privilege`, not `read`, because the response body contains the private key for the user's SSL certificate. Treating it as `read` would let an AI agent casually echo private key material to chat.

## Consequences

- One fewer tier than linode-api-skill makes the matrix marginally simpler.
- The `destructive` tier requires an explicit lookup table (no method-based default catches POST-to-delete-route). This is acceptable; the table is small.
- `--cost-cents <N>` on billable operations is a Porkbun-specific gate that has no analog in the Linode CLI. It locks a quoted price to the actual call: the CLI re-fetches `/domain/checkDomain` and aborts if the price has changed since the quote.
- Over-classification (e.g. treating `/ssl/retrieve` as `privilege` not `read`) costs an extra confirmation but cannot harm the user.

## Alternatives considered

- **Mirror linode-api-skill's six tiers exactly.** Adds an unused `financial` tier. Confusing if a future Porkbun endpoint appears under `financial` without a clear definition.
- **Three tiers (read / write / dangerous).** Simpler, but conflates DNS mutation with credential issuance — and we want the AI to be visibly extra-careful with the latter.
- **No classifier; rely on per-command implementations.** Loses the `api`-generic-gateway pattern, which we want for completeness.

## Related

- Sister project: [`linode-api-skill` ADR-0002](https://github.com/aditya-m-bharadwaj/linode-api-skill/blob/main/docs/decisions/0002-safety-classifier-six-tiers.md).
- ADRs: [[0008-idempotency-key-on-write-ops]] (defense-in-depth for billable ops).
