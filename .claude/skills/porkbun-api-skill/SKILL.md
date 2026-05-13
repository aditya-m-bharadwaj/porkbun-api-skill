---
name: porkbun-api-skill
description: Drive the entire Porkbun v3 API safely through the local porkbun-api-skill CLI. Trigger when the user asks to register, renew, transfer, or inspect a domain; manage DNS records (A/AAAA/CNAME/MX/TXT/NS/CAA/etc.); retrieve SSL certificate bundles; check domain pricing/availability; manage glue records, URL forwarding, DNSSEC, nameservers, or auto-renew settings; or anything under api.porkbun.com/api/json/v3. The CLI mediates every call, classifies it, attaches an Idempotency-Key on writes, refuses unsafe operations without explicit operator-supplied flags, and never lets the AI see the credential pair.
---

# Porkbun-API Skill — full API coverage with mandatory AI safeguards

You drive the user's Porkbun account exclusively through one local executable:

```
porkbun-api-skill <subcommand> [flags]
```

(or `./bin/porkbun-api-skill ...` if not yet on `$PATH`). The credentials (`apikey` + `secretapikey`) live in the OS keystore — **you never see them**. Every mutation is gated by an explicit flag matrix, attaches an `Idempotency-Key` header, and is recorded in `~/.porkbun-api-skill/audit.log`.

> This skill is the sister of `linode-api-skill`. Same vision, same architecture (six-tier-style classifier, OS keystore, AI-safe GUI credential entry, audit log, monolithic CLI), adapted for Porkbun's registrar-domain semantics and dual-key authentication.

## Hard rules (non-negotiable)

1. **Never read the credentials, the keystore, or `~/.porkbun-api-skill/`.** Do not run `security`, `secret-tool`, `cmdkey`, `printenv PORKBUN_*`, or `cat ~/.porkbun-api-skill/credentials.json`. Porkbun uses **two** secrets — both must remain out of your context.
2. **Never call `api.porkbun.com` directly.** Always go through `porkbun-api-skill`.
3. **Every mutation needs explicit user confirmation in this conversation.** The CLI's `--yes` flag is the *machine* gate; the user's "yes" in chat is the *human* gate.
4. **Always preview with `--dry-run` first** when the user hasn't seen the exact request body or you have any uncertainty.
5. **Always quote price in dollars** for billable operations (register / renew / transfer) using a fresh `/domain/checkDomain` or `/pricing/get` call, and require the user to restate the dollar amount before you proceed.
6. **Idempotency.** Every write call must carry an `Idempotency-Key`. The CLI generates one automatically (UUIDv4); your job is to never bypass this by reaching for the raw API yourself.
7. **Refuse and explain** if the user asks you to bypass any of the above.

## How the safety classifier works

Before any mutation, run:

```
porkbun-api-skill classify <METHOD> <path>
```

It returns one of five classifications and the flags you must supply.

| Classification | When | Required flags | What you tell the user |
| --- | --- | --- | --- |
| `read` | Any GET; certain idempotent POSTs (e.g. `/ping`, `/pricing/get` if you POST them) | (none) | "I'm going to fetch X. Safe, read-only." |
| `mutating` | In-place change (DNS create/edit, nameserver update, auto-renew toggle, URL-forward add, glue create/update, DNSSEC add) | `--yes` | "I'll change X. This is reversible." |
| `destructive` | DNS record / DNSSEC record / glue / URL-forward deletions | `--yes --confirm-id <id>` (or `--confirm-name <subdomain>` for `deleteByNameType`) | "I will permanently delete `<resource>`. This cannot be undone. Confirm the id." |
| `billable` | Domain registration, renewal, transfer (anything that charges the account credit) | `--yes --i-understand-billing --cost-cents <N>` where `N` matches the just-quoted `/domain/checkDomain` price | "This will charge $X.YZ against your Porkbun credit (balance: $B.CC from `/account/balance`). Confirm I should proceed at $X.YZ?" |
| `privilege` | Generating an API key (`/apikey/request`, `/apikey/retrieve`), inviting another user to the account (`/account/invite`), changing an email-hosting password (`/email/setPassword`), retrieving an SSL bundle (`/ssl/retrieve` — contains private key material) | `--yes --allow-privilege` | "This issues credentials, changes who can access the account, or returns private key material. This is the highest-blast-radius change." |

Default fallbacks if an endpoint isn't in the classifier table: GET → read, POST → mutating. **DELETE is not used by Porkbun's v3 API** — Porkbun expresses deletion as POST to a `/delete*` route, which the classifier table must explicitly mark `destructive`. You may not work around an unrecognized classification.

## Use the named commands when they exist; fall back to `api` for the rest

### Named commands (ergonomic + extra safety)

| Command | Purpose | Notes |
| --- | --- | --- |
| `porkbun-api-skill whoami` | Verify auth | Calls `/ping` with credentials; prints `credentialsValid: true/false` + caller IP. Never prints the keys. |
| `porkbun-api-skill balance` | Show account credit (`/account/balance`) | Read |
| `porkbun-api-skill domains` | List all domains (`/domain/listAll`, paginated) | Read |
| `porkbun-api-skill domain <name>` | Show one domain (`/domain/get/{domain}`) | Read |
| `porkbun-api-skill price <name>` | Check availability + price (`/domain/checkDomain/{domain}`) | Read; the canonical pre-billable check |
| `porkbun-api-skill register <name> --cost-cents <N> --yes --i-understand-billing` | Register a new domain | Billable. Re-fetches `/domain/checkDomain` and refuses if quoted price ≠ `--cost-cents`. |
| `porkbun-api-skill renew <name> --cost-cents <N> --yes --i-understand-billing` | Renew a domain | Billable. Same price-confirm-check. |
| `porkbun-api-skill transfer <name> --cost-cents <N> --auth-code <code> --yes --i-understand-billing` | Inbound transfer | Billable. |
| `porkbun-api-skill auto-renew <name> --on\|--off --yes` | Toggle auto-renew (`/domain/updateAutoRenew`) | Mutating |
| `porkbun-api-skill nameservers <name> --set ns1,ns2,... --yes` | Update NS (`/domain/updateNs`) | Mutating |
| `porkbun-api-skill dns list <name>` | List DNS records (`/dns/retrieve/{domain}`) | Read |
| `porkbun-api-skill dns add <name> --type A --content 1.2.3.4 [--subdomain s] [--ttl 600] --yes` | Create record (`/dns/create/{domain}`) | Mutating |
| `porkbun-api-skill dns edit <name> --id <id> --content ... --yes --confirm-id <id>` | Edit record (`/dns/edit/{domain}/{id}`) | Destructive-ish; treats edits as destructive when overwriting `A`/`AAAA`/`MX`/`NS`. |
| `porkbun-api-skill dns delete <name> --id <id> --yes --confirm-id <id>` | Delete record (`/dns/delete/{domain}/{id}`) | Destructive |
| `porkbun-api-skill dns delete-by-nametype <name> --type T --subdomain s --confirm-name s --yes` | Bulk-delete all records matching `(type, subdomain)` (`/dns/deleteByNameType/...`) | **Destructive** — deletes multiple. Preview with `dns list` first. |
| `porkbun-api-skill dnssec list <name>` | List DNSSEC records (`/dns/getDnssecRecords/{domain}`) | Read |
| `porkbun-api-skill dnssec add <name> --keytag N --alg N --digest-type N --digest HEX --yes` | Add a DS record. CLI validates digest hex + length (SHA-1=40, SHA-256=64, SHA-384=96). | Mutating |
| `porkbun-api-skill dnssec delete <name> --keytag N --confirm-id N --yes` | Delete DS record (`/dns/deleteDnssecRecord/{domain}/{keytag}`) | Destructive |
| `porkbun-api-skill glue list <name>` | List glue records (`/domain/getGlue/{domain}`) | Read |
| `porkbun-api-skill glue set <name> --subdomain ns1 --ip 1.2.3.4[,2001:db8::1] --yes` | Create-or-update a glue host. Uses `updateGlue` (which has create-or-update semantics) and so avoids the `createGlue` IPv4+IPv6 `UPDATE_FAILED` quirk. | Mutating |
| `porkbun-api-skill glue delete <name> --subdomain ns1 --confirm-name ns1 --yes` | Delete glue (`/domain/deleteGlue/{domain}/{subdomain}`) | Destructive |
| `porkbun-api-skill forward list <name>` | List URL forwards (`/domain/getUrlForwarding/{domain}`) | Read |
| `porkbun-api-skill forward add <name> --location https://x/ --subdomain fwd --permanent --yes` | Create a URL forward. Exactly one of `--permanent` (HTTP 301) / `--temporary` is required. | Mutating |
| `porkbun-api-skill forward delete <name> --id N --confirm-id N --yes` | Delete URL forward (`/domain/deleteUrlForward/{domain}/{id}`) | Destructive |
| `porkbun-api-skill ssl <name>` | Retrieve SSL bundle (`/ssl/retrieve/{domain}`) | **Privilege** — response contains private key material; write to a file with mode 0600 and tell the user the path. Do **not** echo to chat. |
| `porkbun-api-skill audit-log [--last N]` | Local mutation log | |
| `porkbun-api-skill classify <METHOD> <path>` | Plan-time helper | |

### Generic `api` command (everything else)

```
porkbun-api-skill api <METHOD> <path> [flags]
```

Flags:
- `--data '<inline json>'` OR `--body @file.json` (mutually exclusive)
- `--paginate` (for `listAll` / `getUrlForwarding` etc. — fetches all pages)
- `--yes`, `--confirm-id`, `--confirm-name`, `--i-understand-billing`, `--cost-cents <N>`, `--allow-privilege`
- `--dry-run`, `--json`
- `--idempotency-key <key>` (optional; CLI generates one if omitted on writes)

The CLI auto-attaches:
- `X-API-Key` / `X-Secret-API-Key` headers from the keystore (never visible to argv or env).
- `Idempotency-Key: <uuid4>` on every POST that isn't a read-style endpoint (`/ping`, `/pricing/get`, etc.).
- The path is normalized so `/v3/...` and `/...` both resolve.

Examples (preview only — pause and confirm with the user before running for real):

```
# Read
porkbun-api-skill api GET /domain/listAll --paginate
porkbun-api-skill api GET /dns/retrieve/example.com
porkbun-api-skill api GET /domain/get/example.com
porkbun-api-skill api GET /pricing/get

# Mutating
porkbun-api-skill api POST /dns/create/example.com --data '{"type":"A","content":"1.2.3.4","ttl":"600"}' --yes
porkbun-api-skill api POST /domain/updateAutoRenew/example.com --data '{"autoRenew":"on"}' --yes

# Destructive
porkbun-api-skill api POST /dns/delete/example.com/12345 --yes --confirm-id 12345

# Billable — always quote price first via `price <domain>` or `/pricing/get`
porkbun-api-skill price example.com         # quote → user confirms $ amount in chat
porkbun-api-skill api POST /domain/create/example.com --data '{"cost":973,"agreeToTerms":"yes"}' --yes --i-understand-billing --cost-cents 973

# Privilege
porkbun-api-skill api POST /apikey/request --yes --allow-privilege   # returns a NEW API key
porkbun-api-skill ssl example.com                                    # SSL bundle: private key written to disk, not stdout
```

## Resource categories — what to know before touching them

| Category | Paths | Typical class | Confirm with user |
| --- | --- | --- | --- |
| Utility / connectivity | `/ping`, `/ip` | read | safe |
| Pricing | `/pricing/get` | read | TLD pricing snapshot; safe |
| Domains: list & inspect | `/domain/listAll`, `/domain/get/{d}` | read | safe |
| Domains: registration | `/domain/create/{d}` | **billable** | TLD price (re-quote!), `agreeToTerms`, account balance |
| Domains: renewal | `/domain/renew/{d}` | **billable** | renewal price, current expiry |
| Domains: transfer in | `/domain/transfer/{d}` | **billable** | auth-code, transfer-in price |
| Domains: transfer status | `/domain/getTransfer`, `/listTransfers` | read | safe |
| Domains: nameservers | `/domain/getNs`, `/domain/updateNs` | mutating on update | full NS list (mistakes break the domain) |
| Domains: auto-renew | `/domain/updateAutoRenew` | mutating | on/off; reversible |
| Domains: glue records | `/createGlue`, `/updateGlue`, `/deleteGlue`, `/getGlue` | mutating / destructive | only matters for vanity nameservers |
| Domains: URL forwarding | `/addUrlForward`, `/deleteUrlForward`, `/getUrlForwarding` | mutating / destructive | destination URL, include-path flag |
| DNS: read | `/dns/retrieve*`, `/dns/getDnssecRecords` | read | safe |
| DNS: write | `/dns/create`, `/dns/edit`, `/dns/editByNameType`, `/dns/createDnssecRecord` | mutating | the FQDN and record type — edits to `A`/`MX`/`NS` can take down production |
| DNS: delete | `/dns/delete`, `/dns/deleteByNameType`, `/dns/deleteDnssecRecord` | destructive | record id (or subdomain for `deleteByNameType` — dry-run first!) |
| SSL | `/ssl/retrieve/{d}` | **privilege** | response includes the private key; write to a mode-0600 file and tell the user the path |
| Account: balance & settings | `/account/balance`, `/account/apiSettings` | read | safe |
| Account: invite | `/account/invite`, `/account/inviteStatus` | privilege on invite (grants account access) | who is being invited and with what role |
| API keys | `/apikey/request`, `/apikey/retrieve` | privilege | the response *contains a new key* — tell the user to copy it from terminal, do not echo |
| Email hosting | `/email/setPassword` | privilege | password change (no plaintext in chat) |
| Marketplace | `/marketplace/getAll` | read | safe |

When a user asks something open-ended ("what's in my Porkbun account?"), do this in order:

1. `porkbun-api-skill whoami`
2. `porkbun-api-skill balance`
3. `porkbun-api-skill domains`
4. `porkbun-api-skill dns list <domain>` only if a specific domain comes up
5. Summarize. Do not propose mutations unless asked.

## Credential management

The user may ask you to **add, rotate, change, or remove** the credential pair. You can drive every one of these workflows yourself — including launching the entry dialog — without ever seeing, typing, or storing the credentials.

- **You** run the commands and report results.
- **The user** types in a native OS desktop dialog that the CLI pops up. The dialog is rendered by the desktop's WindowServer/compositor; it is not part of any pipe or stdout you can observe.
- **No credential bytes ever cross your context.** The CLI captures the dialog's output into Python memory, validates the pair against `/ping`, stores it in the OS keystore, and prints only metadata to stdout.

### Quick reference

| Operation | AI-runnable command (preferred) | When the AI can't (no GUI / SSH session) |
| --- | --- | --- |
| Add (first time) | `porkbun-api-skill gui-setup` | User runs `porkbun-api-skill setup` in terminal |
| Rotate / change | `porkbun-api-skill gui-setup` | User runs `porkbun-api-skill setup` in terminal |
| Remove | `porkbun-api-skill uninstall-credentials --yes` | (same — no secret involved) |
| Verify (no key printed) | `porkbun-api-skill whoami` | (same) |

### Add or rotate credentials

Always confirm in chat first, because a desktop dialog will pop on the user's screen:

> "I'm going to run `porkbun-api-skill gui-setup`. A native dialog will appear on your desktop with two password fields — one for `apikey` and one for `secretapikey`. Generate a new key pair at <https://porkbun.com/account/api>, paste each value into the matching field, and click OK. I won't see what you type. Confirm I should run this?"

On rotation, remind the user to revoke the old key pair at <https://porkbun.com/account/api>. Local replacement does not invalidate the old keys server-side.

### What NOT to do during credential management

- Do not ask the user to email, paste, or message either key to you.
- Do not put either key in any file, env file, shell rc, gist, or chat message.
- Do not run `setup` yourself with `expect` or here-docs.
- Do not "verify" by curling the API with the keys in argv or a body. Use `porkbun-api-skill whoami`.

## Workflow recipes

### Register a domain (billable)

```
porkbun-api-skill whoami
porkbun-api-skill balance                            # confirm the account has credit
porkbun-api-skill price example.com                  # quote — note `price` in USD, `firstYearPromo`, `coupon`, etc.
# Tell the user: "Porkbun will charge $X.YZ for example.com (first-year price). Account balance is $B.CC. Confirm?"
porkbun-api-skill register example.com --cost-cents 973 --yes --i-understand-billing --dry-run
# (confirm with user once more)
porkbun-api-skill register example.com --cost-cents 973 --yes --i-understand-billing
```

The CLI re-fetches the price and aborts if it changed since the user confirmed.

### Manage DNS for a domain

```
porkbun-api-skill dns list example.com               # capture record ids
porkbun-api-skill dns add  example.com --type A --content 192.0.2.10 --ttl 600 --yes
porkbun-api-skill dns edit example.com --id 87654321 --content 192.0.2.11 --yes --confirm-id 87654321
porkbun-api-skill dns delete example.com --id 87654321 --yes --confirm-id 87654321
```

### Update nameservers (carefully — can break the domain)

```
porkbun-api-skill nameservers example.com --get
# Tell the user the current NS list, the new NS list, and the propagation expectations (24-48h).
porkbun-api-skill nameservers example.com --set ns1.example.com,ns2.example.com --yes --dry-run
porkbun-api-skill nameservers example.com --set ns1.example.com,ns2.example.com --yes
```

### Retrieve an SSL bundle (privilege — contains private key)

```
porkbun-api-skill ssl example.com --yes --allow-privilege
# CLI writes the bundle to ~/.porkbun-api-skill/ssl/example.com.<timestamp>.{certificatechain,privatekey,publickey}.pem (mode 0600).
# Tell the user the directory path. Never copy the privatekey.pem contents into chat.
```

### Issue a scoped API key (privilege)

```
porkbun-api-skill api POST /apikey/request --yes --allow-privilege
```

The new key pair is in the response body. **Tell the user the response is sensitive — they should copy it out of their terminal and store it somewhere safe. Do not log, store, or repeat the keys in chat.** If you absolutely must echo back, redact: `{"apikey":"pk1_<hidden>","secretapikey":"sk1_<hidden>"}`.

## Things you should NOT do

- Do not write either key to any file, env file, shell rc, CI variable, gist, pastebin, or chat message.
- Do not run `porkbun-api-skill setup` yourself — it requires a TTY for hidden input.
- Do not invent record ids, glue subdomains, or URL-forward ids — list them with `dns list` / `getGlue` / `getUrlForwarding` first.
- Do not delete records on a domain you weren't asked to touch.
- Do not skip the price-confirm step on `register` / `renew` / `transfer`.
- Do not bypass the idempotency-key insertion.
- Do not bypass an "unrecognized mutation" classification by reframing the request. If the CLI refuses, stop and ask the user.

## When something goes wrong

| Symptom | What to do |
| --- | --- |
| `error: No Porkbun credentials found` | Tell user to run `porkbun-api-skill setup` (or `gui-setup`). |
| API code `INVALID_API_KEYS_001` | Credentials revoked or wrong. Same fix. |
| API code `INSUFFICIENT_FUNDS` | Account credit too low. Ask the user to top up at <https://porkbun.com/account/billing>. |
| API code `DOMAIN_NOT_AVAILABLE` | Someone else owns it. Re-quote with a variant. |
| API code `RATE_LIMIT_EXCEEDED` | Honor `X-RateLimit-Reset`. Don't tightly retry. |
| API code `IDEMPOTENCY_KEY_MISMATCH` | The CLI sent a key it had previously used for a *different* body. Bug — surface it. |
| `--confirm-id mismatch` | You constructed the id wrong. Re-fetch the resource. |
| Quoted price changed between quote and `register` | The CLI's safety check fired correctly. Re-quote, ask the user, retry. |
