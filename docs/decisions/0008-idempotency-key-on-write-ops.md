---
number: 0008
title: Auto-attach `Idempotency-Key` on every write call
date: 2026-05-11
status: accepted
---

# 0008 — Auto-attach `Idempotency-Key` on every write call

## Context

Porkbun's v3 API supports an `Idempotency-Key: <unique-string>` request header on every POST endpoint (excluding partner-only routes). When the header is present, the API stores the response for 24h and replays it on a retry of the same request — so an agent that retries after a network blip will **not** double-charge or double-register.

Without it, a flaky network or a re-tried agent loop could end up registering the same domain twice (and being billed for both, or losing the second one to `DOMAIN_NOT_AVAILABLE`), creating duplicate DNS records, or otherwise mutating state in unintended ways.

This is the single highest-value safety feature Porkbun's API offers that has no analog in Linode's API. It is **the** defining Porkbun-specific decision.

## Decision

The CLI **always** attaches an `Idempotency-Key` header on every POST request, unless the operator explicitly opts out via `--no-idempotency-key`.

- Key generation: `uuid.uuid4().hex` per call. Stable per-call (no retry inside the CLI reuses a different key by accident); not stable across CLI invocations (a deliberate operator re-invoke is a new operation).
- Header is added in `_request` (the single HTTP entry point), so the named commands and the generic `api` command get it for free.
- Read-style endpoints (`/ping`, `/pricing/get`, `/dns/retrieve*`, `/domain/get*`, `/domain/listAll`, etc.) get the header too — harmless; Porkbun's docs say these are not cached, and the header is ignored for read-style routes.
- The operator may pass `--idempotency-key <key>` to supply their own (e.g. when wrapping the CLI in a higher-level workflow that wants its own retry semantics). The supplied key is honored verbatim.
- `--no-idempotency-key` exists for debugging; CHANGELOG must call out that it is unsafe for production scripts.

## Consequences

- A retried `porkbun-api-skill register example.com` will never double-charge — Porkbun's server will replay the original response.
- The audit log records the idempotency key alongside the action, so an operator can investigate retries forensically.
- Slight noise on read responses (the key is sent but unused). Acceptable.
- An accidental same-key + different-body sequence will fail with `IDEMPOTENCY_KEY_MISMATCH` 409 — a deliberate Porkbun safety feature we let surface unchanged.

## Alternatives considered

- **Only attach to billable endpoints (`/domain/create`, `/renew`, `/transfer`).** Misses the case of double-creating DNS records or double-issuing API keys.
- **Let the operator opt in per command.** Foot-gun; defeats the safety property.
- **Use a deterministic key derived from `(action, target, body)`.** Lets an operator's intentional second call collide with a stored response. Rejected: intentional second calls (e.g. "renew this domain *again* next year") should not be deduplicated.
- **Reuse the same key across CLI invocations within a TTL.** Way too clever; surprises operators. Rejected.

## Related

- Porkbun docs on idempotency: <https://porkbun.com/api/json/v3/spec> (search for `Idempotency-Key`).
- ADRs: [[0002-safety-classifier-five-tiers]] (defense-in-depth for billable).
