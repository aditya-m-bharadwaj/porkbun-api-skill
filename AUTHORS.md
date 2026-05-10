# Authors

## Disclaimer

`porkbun-api-skill` is being authored by an AI agent (Claude Opus 4.7, 1M-context) on behalf of a human operator who prompts and reviews each commit. This is **AI-assisted, single-session code** — the same caveats that apply to any AI-generated codebase apply here:

- Audit `bin/porkbun-api-skill` before granting it real credentials.
- Use `--dry-run` before any mutation you have not seen the body of.
- Treat pre-1.0 releases as alpha-quality; do not rely on the API surface remaining stable across releases.
- File bugs and security concerns per [SECURITY.md](SECURITY.md).

## Attribution

- **Prompted by:** Aditya Bharadwaj — `aditya.m.bharadwaj@gmail.com`
- **Written by:** Claude (Anthropic) — Claude Opus 4.7

The commit history uses the `Prompted-By:` and `Co-Authored-By:` trailer convention codified in [docs/decisions/0005-prompted-by-trailer-convention.md](docs/decisions/0005-prompted-by-trailer-convention.md) and [CONTRIBUTING.md](CONTRIBUTING.md). Any contributor whose changes are materially shaped by an AI agent is expected to use the same trailers.

## Sister project

This project mirrors [`linode-api-skill`](https://github.com/aditya-m-bharadwaj/linode-api-skill) for the Porkbun API. The vision, architecture, and AI-safety contract come from that project; substantial design carries over directly (see ADRs `0001`, `0005`, `0006`, `0007`). Porkbun-specific decisions live in ADRs `0002` (five-tier classifier), `0003` (dual-key credential storage), `0004` (dual-field GUI dialog), and `0008` (idempotency-key auto-attach).
