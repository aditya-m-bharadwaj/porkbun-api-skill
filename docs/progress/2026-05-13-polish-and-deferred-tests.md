---
date: 2026-05-13
session: polish-and-deferred-tests
operator: Aditya Bharadwaj <aditya@bharadwaj.co>
ai-assist: Claude Opus 4.7 (1M context)
---

# Polish pass + deferred live tests on devbed.sbs

Two-part session sitting on top of the same day's earlier live-API
validation (`docs/progress/2026-05-13-live-api-test-idwgit.md`):

1. **Polish pass** — addressed the 5 papercuts captured during the
   idwgit.cc live test. Landed as commit `aa1e2f3`.
2. **Deferred live coverage** — purchased a $1.28 throwaway testbed
   (`devbed.sbs`) with auto-renew off + WHOIS privacy on, and exercised
   the remaining endpoint families that had only classifier-level
   coverage (`dns/deleteByNameType`, `dnssec*`, `glue*`, `urlforward*`).

## Part 1 — polish pass (committed)

Five fixes + one helper function, +16 tests (68 total, all passing).

### Fixes in `bin/porkbun-api-skill`

- **`--json` now propagates to every subparser.** Previously declared
  only on the top-level parser, so `dns list <domain> --json` silently
  emitted human-readable output. Refactored to a `_global_parent()`
  parent parser passed via `parents=[common]` to every `sub.add_parser()`
  call. Both `--json <subcmd>` and `<subcmd> --json` now work.
- **`--prio` refused for non-MX/SRV record types.** `dns add` and
  `dns edit` raise `CtlError` if `--prio` is passed with type A / AAAA /
  CNAME / NS / TXT / CAA. Porkbun-side prio=0 default still happens for
  those types — that's the registry's quirk we can't fix — but the CLI
  no longer accepts a value that gets silently dropped.
- **`prio=N` column hidden in `dns list` output for non-MX/SRV records.**
  `_format_summary` checks the record type against `_PRIO_RECORD_TYPES =
  ("MX", "SRV")` and only shows the priority column for those types.
- **`nameservers --set` surfaces Porkbun's "No change" response.** When
  the API reports no change (because `/domain/updateNs` is set-based and
  ignores order), the CLI now prints an explicit `NOTE:` warning. The
  `--set` flag's `--help` documents this set-based behavior so an
  operator doesn't waste retries.
- **`API_ACCESS_DISABLED` errors get a friendlier path.** `_request`
  detects `API_ACCESS_DISABLED` / `NOT_OPTED_IN_TO_API_ACCESS` in either
  the `code` or `message` field of Porkbun's error response and replaces
  the 100-character UPPERCASE_UNDERSCORED Porkbun message with a
  one-liner pointing the operator at <https://porkbun.com/account/api>.
- **`autoRenew` typing normalized.** Porkbun returns `0` (int) when off,
  `"1"` (string) when on. New `_normalize_auto_renew(v)` helper coerces
  both forms to a stable string `"0"` / `"1"`. Wired into `cmd_domain`
  and `_format_summary`. Doesn't lie when Porkbun returns an unexpected
  value — falls through as-is.

### Test additions

`tests/test_classify.py` grew by 16 cases across 3 new classes and 2
new methods on the existing `TestCliEntrypoint`:

- `TestCliEntrypoint`: `test_json_flag_accepted_before_subcommand`,
  `test_json_flag_accepted_after_subcommand` (regression for the polish
  fix).
- `TestNormalizeAutoRenew` (7 cases): int/str/bool inputs in both
  forms; unknown-value fall-through.
- `TestFormatSummaryPrio` (5 cases): MX/SRV show prio, NS/A/TXT hide.
- `TestPrioRejection` (2 cases): `--prio` on A is refused (exit 2);
  `--prio` on MX is accepted at the validation gate.

Total: 52 → 68 tests, all passing in ~1.7s (mostly the new tests
exercising `pb.main` which has to construct the full parser).

## Part 2 — deferred live tests on devbed.sbs

### Pricing exploration

- Pulled `/pricing/get` (906 TLDs). Filtered for `registration < $2`
  AND `renewal < $2`: only `.fly` qualified (at $0/$0/$0 — restricted),
  plus all Handshake TLDs (don't resolve via standard DNS — bad for
  HTTP/SSL test workflows).
- Realistic option: **register on a first-year-promo TLD, disable
  auto-renew immediately so the expensive renewal never triggers,
  let the domain expire naturally after 1 year.** That maps cleanly
  to "discarded without any worry."
- Cheapest viable first-year-promo TLDs at $1.28 first year:
  `.sbs`, `.cfd`, `.cyou`. All have $15.96 renewals (which we won't
  pay).
- Generated a CSV snapshot of all 906 TLDs at
  `/tmp/porkbun-pricing-20260513T111535Z.csv` (sorted by registration
  price ASC). Not committed — pricing snapshots go stale quickly.

### Picking a name

After rejecting four short single-word candidates (`tinker.sbs`,
`sandbox.sbs`, `devlab.sbs`, `proto.sbs` — three were premium-tier at
$63-328, one was taken), settled on **`devbed.sbs`** ($1.28
registration, available, not premium). Each `/domain/checkDomain`
costs ~11s wallclock against Porkbun's 1/10s rate limit, so the search
was deliberately conservative.

### Purchase

Operator confirmed "$1.28" in chat (SKILL.md hard rule). Sequence:

1. `register devbed.sbs --cost-cents 128 --yes --i-understand-billing --dry-run`
   — preview body: `{"cost": 128, "agreeToTerms": "yes"}`.
2. Real `register`. SUCCESS, idempotency key `8e5cd99a43e44ffe8b86e51cffcb6c69`.
3. `auto-renew devbed.sbs --off --yes`. SUCCESS.
4. Verify via `domain devbed.sbs`:
   - `whoisPrivacy: "1"` (default for new Porkbun registrations) ✓
   - `autoRenew: "0"` ✓ (normalized output from the polish-pass fix)
   - `apiAccess: "1"` ✓ (already enabled, no manual toggle)
   - `securityLock: 0` (Porkbun doesn't lock new registrations
     immediately — fine for a testbed)
   - Expires 2027-05-13 → will auto-discard.
5. Balance went $0.00 → $10.00 (operator topped up) → $8.72 after
   the $1.28 charge. The $10 top-up coincides with the user raising
   the monthly cap from $0.02 to $2.00.

### Deferred test results

All four endpoint families exercised live:

| Family | Result |
| --- | --- |
| `dns/deleteByNameType` + `--confirm-name` | ✓ Refused without `--confirm-name`, refused with mismatched name, accepted with match. Two `purge-test` TXT records bulk-deleted in one call. |
| `dnssec*` (create/get/delete) | ✓ Cycle clean. **Quirk**: Porkbun accepted a bogus DS record (`digest="A"*64` with `digestType=2`/SHA-256) without validating the digest's hex content. An operator could lock themselves out of DNSSEC validation with bad inputs. |
| `glue*` (create/get/update/delete) | ⚠ `createGlue` failed `UPDATE_FAILED: Unable to update domain` when passing both IPv4 and IPv6. `updateGlue` succeeded *as a create*, exposing create-or-update semantics. `deleteGlue` with `--confirm-id ns1` validated that non-numeric `--confirm-id` works. |
| `urlforward*` (add/get/delete) | ✓ Cycle clean. The `--json api GET ... \| python3 -c ...` pipe worked, validating the polish-pass fix to `--json` propagation in a real flow. |

Final `devbed.sbs` state after all tests: 4 default Porkbun NS records
+ 2 `_acme-challenge` TXT records (auto-created for SSL provisioning,
same as idwgit.cc). DNSSEC / glue / urlforward all empty. Audit log
holds 28 entries across both live-test sessions.

## New polish items uncovered

Four new items beyond the original 5-item polish list:

1. **`createGlue` IPv6 quirk**. Document the IPv4+IPv6 rejection, or
   auto-retry with IPv4-only when `createGlue` returns
   `UPDATE_FAILED`. (Or call `updateGlue` directly — see #2.)
2. **`updateGlue` is create-or-update.** Document the overlap with
   `createGlue`. Possible CLI shape: a single `glue set` command that
   tries `createGlue` first, falls back to `updateGlue` on failure.
3. **Client-side DNSSEC digest hex-length validation.** SHA-256 ⇒ 64
   hex chars, SHA-384 ⇒ 96. Refuse bad inputs at the CLI boundary so
   operators don't ship broken DS records to the registry.
4. **Named commands for `dnssec*`, `glue*`, `urlforward*`, and `dns
   delete-by-nametype`.** The generic `api` command works but lacks
   per-endpoint validation (e.g. `--confirm-name` matching, valid
   record-type whitelists, hex digest validation from #3). Suggested
   shape: `dnssec {add,list,delete}`, `glue {create,get,update,delete}`,
   `forward {add,list,delete}`, `dns delete-by-nametype`.

## New ADRs or concept notes

**None.** All findings are operational polish or feature gaps captured
in the todo list. No architectural decisions; the existing 5-tier
classifier + idempotency-key + dual-key storage design held up
end-to-end across both live-test sessions.

If named-command coverage for `dnssec*`/`glue*`/`urlforward*` grows
non-trivially during the next session, an ADR for "named command vs
generic api gateway: when to add a named wrapper" might be worth
writing. Not needed yet.

## What's in-flight

- Polish queue now has 4 items (3 from this session + 1 carried; the
  earlier 5 from idwgit.cc are landed in `aa1e2f3`).
- devbed.sbs is in a clean state for future test sessions. The two
  `_acme-challenge` TXT records auto-created by Porkbun for SSL are
  left in place (cost-free, identical pattern to idwgit.cc).

## What's next (recommended pickup)

1. **Land the new polish items** (named wrappers + DNSSEC validation +
   glue documentation). The first cluster is mostly mechanical (named
   commands wrap `api` calls with thin validation); the second cluster
   is short doc/regex additions. Easy session.
2. **Push the local-only commits to origin.** Local is at `aa1e2f3`,
   origin (since the earlier `/save` work today) is at `a69c707`.
3. **GitHub repo creation checklist** still pending from the build
   session — description, topics, homepage, Discussions, Sponsors,
   private security advisories, branch protection, default labels.
4. **Tag `v0.1.0-alpha.1`** once polish is settled and pushed.

## Related files / links

- Same-day predecessor: `docs/progress/2026-05-13-live-api-test-idwgit.md`
  (the initial live validation that surfaced the 5 polish items this
  session fixed).
- Commit landing the polish pass: `aa1e2f3` (`fix: polish papercuts
  found during live API test on idwgit.cc`).
- Vault mirror of this note:
  `~/.claude/vault/zettel/progress/2026-05-13-porkbun-api-skill-polish-and-deferred-tests.md`.
- Pricing snapshot CSV (transient, /tmp): not committed.
- ADRs reaffirmed by both live-test sessions: 0002 (classifier),
  0003 (dual-key storage), 0004 (GUI dialog), 0008 (idempotency-key).
