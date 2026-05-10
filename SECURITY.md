# Security policy

`porkbun-api-skill` is a privileged tool: with a valid Porkbun API key pair it can register, transfer, delete, and modify domains; edit DNS records (production-breaking); retrieve SSL bundles containing private key material; and issue new API key pairs.

## Reporting a vulnerability

If you find a security issue — credential leakage, classifier bypass, sandbox-escape via the generic `api` command, missing `Idempotency-Key` on a write path, etc. — please open a **private security advisory** on the project's GitHub repository rather than a public issue. Include:

- a description of the issue,
- minimum repro (commands and expected vs. observed behavior),
- the version reported by `porkbun-api-skill --version`,
- and your platform.

We aim to acknowledge within 5 business days.

## Threat model

### Defended

- **Credentials at rest.** Both `apikey` and `secretapikey` are stored as a single atomic JSON blob in an OS-native secret store when available (macOS Keychain, Linux Secret Service / libsecret). On platforms without one, fallback is `~/.porkbun-api-skill/credentials.json` with mode `0600`. The CLI refuses to read the file if its permissions allow group or world read.
- **Credentials in transit (within the host).** Neither secret appears in argv, environment exported to children, log files, or stdout. They are held in process memory only for the lifetime of one CLI call.
- **Accidental destructive operations.** The CLI's five-tier classifier (read / mutating / destructive / billable / privilege) requires per-class flags before any mutation. `register`/`renew`/`transfer` additionally re-fetch the price quote and abort if it has changed since the user confirmed it.
- **Double-charging on retry.** Every write call carries an `Idempotency-Key` header; Porkbun replays the cached response for 24h on a retry of the same request. See [docs/decisions/0008-idempotency-key-on-write-ops.md](docs/decisions/0008-idempotency-key-on-write-ops.md).
- **AI agents driving the tool.** When run from inside a Claude (or other AI) session, the accompanying skill instructs the agent to never read credentials, never call the API directly, obtain explicit human confirmation in chat before any mutation, and prefer `--dry-run` first. Operators can additionally enforce these constraints at the harness level via `.claude/settings.local.json` (template at [docs/settings.local.json.template](docs/settings.local.json.template) — created during the CLI build session).
- **Audit trail.** Every mutation appends one JSON line to `~/.porkbun-api-skill/audit.log` with timestamp, user, action, target, classification, idempotency key, and parameter metadata (record types, ttls, body keys for generic `api` calls — never credentials, never private keys, never DNS record content unless it's the bare type/ttl shape).
- **SSL private key material.** `porkbun-api-skill ssl <domain>` writes the cert bundle to a mode-0600 file under `~/.porkbun-api-skill/ssl/`. The private key is **never** written to stdout, echoed back, or surfaced to the AI agent.

### Not defended

- **Compromise of the local user account.** If the operator's user session is compromised, an attacker can read the keystore, the file fallback, the audit log, and the SSL bundle files just as the user can. Use disk encryption and standard endpoint security.
- **Porkbun-side IAM / key scope.** Porkbun keys don't have per-resource scopes; a valid pair can do anything the account owner can do. Use a short-lived key for automation; rotate regularly (`porkbun-api-skill uninstall-credentials --yes` then `porkbun-api-skill setup`).
- **Network adversaries.** TLS to `api.porkbun.com` is provided by the OS / Python stdlib trust store. The tool does not pin certificates.
- **Side channels.** Domain list, DNS record names, expiry dates are visible via the audit log and by listing resources; do not assume secrecy of resource metadata.
- **Tool freshness.** Endpoints added to Porkbun's API after `docs/api-spec.json` was captured fall through to method-based defaults (POST → mutating, GET → read). Destructive endpoints introduced in future API versions will not be auto-classified destructive unless the table is updated.

## Hardening recommendations

- Rotate the API key pair periodically and immediately on suspicion.
- On Linux, install `libsecret-tools` (`apt install libsecret-tools` / `dnf install libsecret`) so the credentials live in the Secret Service rather than a file.
- When running under an AI agent, enable the harness deny rules from `docs/settings.local.json.template` (added in the CLI build session). These mechanically prevent the agent from reading the credentials or calling the API directly.
- Review `~/.porkbun-api-skill/audit.log` periodically. Forward it to your SIEM if you have one.
- For domain registrations, set up Porkbun's account-level 2FA in addition.

## Cryptographic notes

- Idempotency keys use `uuid.uuid4()` (UUIDv4 from Python's `uuid` module, which uses `os.urandom`).
- No secrets are written to stdout, stderr, or the audit log.
