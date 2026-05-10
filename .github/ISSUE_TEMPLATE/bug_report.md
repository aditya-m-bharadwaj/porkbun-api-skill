---
name: Bug report
about: Report a defect in porkbun-api-skill (CLI, classifier, installer, or skill)
title: "bug: <short summary>"
labels: ["bug"]
assignees: []
---

> **Security note:** if this is a vulnerability (credential leak, classifier bypass,
> missing idempotency-key on a write path, sandbox escape via the generic `api`
> command, etc.), please **do not** file it here. File a private advisory at
> <https://github.com/aditya-m-bharadwaj/porkbun-api-skill/security/advisories/new>
> instead. See [SECURITY.md](../../SECURITY.md).

## Summary

A one-sentence description of what is broken.

## Environment

- `porkbun-api-skill --version` output:
- OS and version (e.g. macOS 14.4, Ubuntu 22.04, Windows 11):
- Python version (`python3 --version`):
- Credential storage backend (macOS Keychain / Linux Secret Service / file fallback):
- Installed via: clone / `install.sh` / `install.ps1` / `curl ... | sh`

## Reproduction steps

Minimum commands to trigger the bug. Use `--dry-run` where possible so we can
reproduce without hitting the real API.

```sh
porkbun-api-skill ...
```

## Expected behavior

What you thought would happen.

## Observed behavior

What actually happened. Paste exit code, stderr, and the relevant lines of
`~/.porkbun-api-skill/audit.log` if a mutation was attempted. **Redact any
domain names, record contents, or IPs you'd rather not share publicly.**

## Additional context

Screenshots, related issues, anything else useful.
