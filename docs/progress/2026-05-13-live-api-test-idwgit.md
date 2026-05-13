---
date: 2026-05-13
session: live-api-test-idwgit
operator: Aditya Bharadwaj <aditya@bharadwaj.co>
ai-assist: Claude Opus 4.7 (1M context)
---

# Live API test on idwgit.cc (v0.1.0-alpha.1 validation)

First live exercise of the CLI against `api.porkbun.com`. The operator
installed a credential pair scoped to a test domain (`idwgit.cc`) via
`gui-setup`, then green-lit a non-billable test plan covering all five
classification tiers. The CLI passed every operation; idwgit.cc is back at
its starting configuration with zero test residue.

This validates the implementation that landed in commit `af876f9`
(`feat: implement v0.1.0-alpha.1 single-file CLI`) against a real
account. Live API expectations from that build's "what's next" list are
now confirmed — DNS list response wrapper is `{"records": [...]}`,
domains-listAll wrapper is `{"domains": [...]}`, errors arrive as `{...
"message": "..."}` with a separate code embedded in the URL path's status.

## What was done

### Credential entry — AI-safe path

Operator chose `gui-setup`. Two `osascript display dialog` calls appeared
on macOS desktop (apikey → secretapikey). The CLI validated against
`POST /ping`, stored the pair in the macOS Keychain (service
`porkbun-api-skill`), and printed only the caller IP — no key bytes ever
crossed the AI's context. Workflow validated end-to-end on macOS as
designed in ADR-0004.

### Batch 1 — reads (8 endpoints)

All returned `status: SUCCESS`:

- `whoami` (`POST /ping`): credentialsValid + caller IP
- `balance` (`GET /account/balance`): $0.00
- `domains` (paginated `POST /domain/listAll`): 32 domains on this account
- `domain idwgit.cc` (`GET /domain/get/{domain}`)
- `price idwgit.cc` (`POST /domain/checkDomain/{domain}`): registration
  $3.40 (first-year promo), renewal/transfer $8.55. Pretty-printed price
  table + `--cost-cents 340` hint matched expectations.
- `dns list idwgit.cc` (`GET /dns/retrieve/{domain}`): 9 records (6 NS,
  3 TXT)
- `nameservers idwgit.cc --get` (`GET /domain/getNs/{domain}`): 4
  Porkbun nameservers (registrar-level, distinct from in-zone NS records)
- `audit-log`: empty pre-test as expected

### Bug surfaced (and fixed live)

Initial `dns list` and `nameservers --get` failed with
`API_ACCESS_DISABLED` / `DOMAIN_IS_NOT_OPTED_IN_TO_API_ACCESS`. **idwgit.cc
had `apiAccess: 0` in the domain record** — Porkbun gates DNS/NS reads
*and* writes on a per-domain (or account-wide) opt-in toggled at
<https://porkbun.com/account/api>. The CLI surfaced Porkbun's raw error
verbatim (a long `_`-separated uppercase code + message). Operator
enabled API access; reads resumed.

This is a recurring class of error that deserves a friendlier CLI path
— see the "polish items queued" section below.

### Batch 2a — reversible DNS on throwaway subdomain

On `claude-smoke.idwgit.cc`:

1. `dns add` TXT (content "porkbun-api-skill smoke 1", ttl 600)
2. `dns list` confirmed record id 546712348
3. `dns edit` (content "porkbun-api-skill smoke 2 edited", `--confirm-id`
   matching `--id`)
4. `dns delete` (with `--confirm-id`)
5. `dns list` confirmed clean

All four mutations recorded in the audit log with unique UUIDv4
idempotency keys.

### Batch 2b — auto-renew toggle and restore

Pre-state: `autoRenew: "1"` (string). Toggled `--off` → `--on`. Porkbun
returns `autoRenew: 0` (integer) when off and `"1"` (string) when on —
type-inconsistent on Porkbun's side, not the CLI's. Restore verified.

### Batch 2c — DNS edit on production NS, add+delete A/MX

idwgit.cc had no existing A or MX records — only NS and TXT — so the
"edit existing A/MX/NS" surface was exercised by:

- Editing in-zone NS record #521144450 (`curitiba.porkbun.com`): TTL
  86400 → 3600 → 86400. **Side effect**: Porkbun set `prio: None → 0` on
  the record during the edit; not restorable without further intervention.
  Functionally irrelevant (NS records don't use priority) but it IS a
  visible state change introduced by the CLI sending `prio` in the body.
- Adding then deleting an A record (`claude-a-test.idwgit.cc` →
  `192.0.2.1`, TEST-NET-1 documentation prefix per RFC 5737, never routes).
- Adding, editing prio (10 → 20), then deleting an MX record
  (`claude-mx-test.idwgit.cc` → `mx.invalid` per RFC 6761).

### Batch 2d — nameservers --set roundtrip

Reordered the existing 4 Porkbun nameservers (curitiba/fortaleza/salvador/maceio
→ reversed → restored). **Both calls returned `"message": "No change."`**
because Porkbun's `/domain/updateNs` is set-based, not list-based — the
order in the request body is ignored by the registry. The CLI's
`--set ns1,ns2,...` argument order is therefore not preserved on the
server side. Test exercised the write code path (multi-NS regex
validation, request marshalling, response parsing) without actually
mutating the registry.

### Batch 3 — SSL retrieve (privilege)

`ssl idwgit.cc --yes --allow-privilege` wrote three files to
`~/.porkbun-api-skill/ssl/idwgit.cc.20260513T104658Z.{certificatechain,privatekey,publickey}.pem`
(mode 0600, dir 0700). Operator confirmed:

- certificatechain.pem opens with `-----BEGIN CERTIFICATE-----`
- publickey.pem opens with `-----BEGIN PUBLIC KEY-----`
- privatekey.pem: 52 lines / 3272 bytes / mode 0600 — **content
  deliberately not inspected** so it never enters AI context

After verification, operator instructed `rm ~/.porkbun-api-skill/ssl/*.pem`;
directory is empty.

### Final state — verified clean

- 9 DNS records on idwgit.cc (matches starting state)
- Zero `claude-smoke` / `claude-a-test` / `claude-mx-test` residue
- `autoRenew: "1"` (restored)
- Registrar NS list back to original order
- NS #521144450 TTL back to 86400 (prio went 0 → 0; was None pre-test)
- 15 mutations in `~/.porkbun-api-skill/audit.log`, each carrying a
  unique UUIDv4 idempotency key, classification, and body-key list
  (never values, never credentials)

## Bugs and polish items captured

Five items captured in the session todo list for the next polish pass:

1. **`--json` is top-level only.** `dns list --json | python3 ...`
   silently produced empty stdin. `argparse` didn't error because the
   subparser ignored the trailing `--json`. Fix: propagate `--json` to
   every subparser via a parent-parser pattern, or surface a clear error
   on trailing unrecognized `--json`.
2. **NS edit sets `prio: None → 0`.** The CLI always sends `prio` in the
   body when the operator passes `--prio` (and defaults to omit
   otherwise). On an NS edit, the body shape forced a `prio` write
   somewhere. Fix: omit `prio` from the request body when the record
   type isn't MX or SRV.
3. **`nameservers --set` is set-based per Porkbun.** CLI silently passes
   the operator's order, but the registry ignores it. Fix: surface
   Porkbun's `"No change"` response prominently in the human-readable
   output, and document set-based behavior in `nameservers --help`.
4. **`API_ACCESS_DISABLED` deserves a friendlier path.** Detect the code
   in `_request` and redirect: `"This domain isn't opted in to API access.
   Enable it at https://porkbun.com/account/api (account-wide) or in the
   domain's settings page (per-domain)."`
5. **`autoRenew` typing inconsistency** (0 int vs "1" string from
   Porkbun). Normalize on the CLI output side so `domain <name>` reports
   a stable type.

Plus two test-coverage gaps:

6. `dns/deleteByNameType` (pattern-delete) + `--confirm-name` is only
   classifier-tested, not live-tested. Worth a named `dns delete-by-nametype`
   command exercised on a throwaway subdomain.
7. `dnssec*`, `glue*`, `urlforward*` endpoints are classifier-tested
   only. Worth named commands or documented `api` usage exercised on a
   test domain.

## New ADRs or concept notes

**None.** No material design decisions were made; the bugs and quirks
captured are operational polish, not architectural. They flow into the
session todo list, not new ADRs.

If any of the polish items grow into a real design decision (e.g.
"should the CLI always validate apiAccess pre-flight before write
operations?"), that warrants an ADR in the follow-up session.

## What's in-flight (not finished)

- All 7 polish/test-gap items in the session todo list, queued for the
  next session.
- The live test exercised only domains the operator owns. Not yet tested:
  `register` / `renew` / `transfer` (deliberately — billable, explicitly
  off-limits this session).

## What's next (recommended pickup)

1. **Address the 5 polish items + 2 test gaps** queued in the todo list.
   Lowest blast radius first: `autoRenew` typing normalization and the
   NS `prio` omit. Then `--json` propagation and the `API_ACCESS_DISABLED`
   redirect. Then live exercise of `dnssec` / `glue` / `urlforward`.
2. **One-shot live billable test on a cheap throwaway TLD.** With
   explicit operator confirmation: `price <cheap-tld>` →
   `register <cheap-tld> --cost-cents N --yes --i-understand-billing
   --dry-run` → actual register → immediate `auto-renew --off` →
   delete after expiry. Confirms the price-confirm guard and the
   idempotency-key replay path (which prevents double-charge on a
   network blip + retry).
3. **GitHub repo creation** per the checklist in
   `docs/progress/2026-05-11-cli-build.md` step 4 (description, topics,
   homepage, Discussions, Sponsors, security advisories, branch
   protection, default labels).
4. **Tag `v0.1.0-alpha.1`** and cut a GitHub release once live
   validation completes — this session was much of that validation.

## Related files / links

- Implementation: `bin/porkbun-api-skill` (commit `af876f9`).
- Prior session: `docs/progress/2026-05-11-cli-build.md` — the build that
  shipped what this session validated.
- ADRs informing the live behaviour: 0002 (classifier), 0003 (dual-key
  storage), 0004 (GUI dialog), 0008 (idempotency-key).
- Porkbun docs for the `API_ACCESS_DISABLED` gate:
  <https://porkbun.com/account/api>.
- RFC 5737 (TEST-NET-1 `192.0.2.0/24` used for the A record test),
  RFC 6761 (`*.invalid` used for the MX record test).
