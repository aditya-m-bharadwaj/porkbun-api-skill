---
number: 0003
title: Cross-platform credential-pair storage (dual-key)
date: 2026-05-11
status: accepted
---

# 0003 — Cross-platform credential-pair storage (dual-key)

## Context

Porkbun authenticates with **two** secrets — `apikey` (e.g. `pk1_...`) and `secretapikey` (e.g. `sk1_...`) — both of which must be sent with every authenticated request, either in the JSON body (primary) or as `X-API-Key` / `X-Secret-API-Key` headers.

The sister project `linode-api-skill` stores a single bearer token. We need a storage shape that:

- holds *both* values as a single unit (rotating one without the other is a programming error we want to make impossible),
- works across macOS / Linux / Windows with the same code shape,
- can be wiped in one operation,
- refuses to be read by AI agents (mode 0600 on the file fallback; native keystore lookup elsewhere).

## Decision

Store the pair as a single JSON object: `{"apikey": "<key>", "secretapikey": "<secret>"}`, then persist that JSON string atomically.

| Platform | Backend | Notes |
| --- | --- | --- |
| macOS | Keychain via `security` CLI | Service: `porkbun-api-skill`, Account: `credentials`. Value: the JSON blob. |
| Linux | Secret Service via `secret-tool` (libsecret) | Schema: `org.porkbun.api-skill`, label `credentials`. Value: the JSON blob. |
| Windows / fallback | File at `~/.porkbun-api-skill/credentials.json`, mode `0600` (Unix) or `icacls`-locked ACL (Windows). | Contains the JSON blob verbatim. |

Read path (highest-strength backend wins):
1. macOS → Keychain.
2. Linux → libsecret if `secret-tool` is on PATH.
3. Fallback → file (refuses to read if POSIX mode is broader than `0600`).

`gui-setup` captures *both* values in a single native dialog (a small form with two password fields). It validates by `POST /ping` with the pair and stores them atomically. Partial-write of one key without the other is not possible.

## Consequences

- Both keys live and die together — no risk of mixing an old `apikey` with a new `secretapikey` because we serialize atomically.
- The file fallback (`~/.porkbun-api-skill/credentials.json`) is JSON; `cat` would show both keys at once. Mitigated by mode 0600 and by the harness deny rule that blocks the AI from reading the path.
- Slight extra complexity in the file fallback over linode-api-skill's plain-text token file.
- Single-source-of-truth for "is the user authenticated?" — either both keys are stored and valid, or the file/keystore entry doesn't exist.

## Alternatives considered

- **Two separate keystore entries** (e.g. service `porkbun-api-skill` with accounts `apikey` and `secretapikey`). Lets one be rotated independently of the other — but that's not actually a feature we want; Porkbun rotates them together. Rejected for false-flexibility.
- **Two separate files**. Same issue.
- **Environment variables `PORKBUN_API_KEY` / `PORKBUN_SECRET_API_KEY`** as primary storage. Visible to `printenv` and to every child process; explicitly *not* the AI-safe path. We support reading them as a fallback for CI use, but never write them.

## Related

- Sister project: [`linode-api-skill` ADR-0003](https://github.com/aditya-m-bharadwaj/linode-api-skill/blob/main/docs/decisions/0003-cross-platform-token-storage.md).
- ADRs: [[0004-ai-safe-credential-entry-gui-dialog]].
