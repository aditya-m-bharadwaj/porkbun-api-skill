---
number: 0004
title: AI-safe credential entry via native GUI dialog (dual-field)
date: 2026-05-11
status: accepted
---

# 0004 — AI-safe credential entry via native GUI dialog (dual-field)

## Context

An AI agent that drives the CLI cannot run `porkbun-api-skill setup` interactively (no TTY for `getpass`) and **must not** be allowed to read the credential pair from any pipe it can observe. But operators using the Claude skill want the AI to be able to direct *every* credential-management workflow, including the initial add and later rotations — that's the whole point of the project.

The sister project `linode-api-skill` solves this by popping a native OS password dialog (osascript / zenity / kdialog / `Get-Credential`) for a single token. Porkbun needs the same pattern, adapted to capture **two** secrets in one user-visible interaction.

## Decision

`porkbun-api-skill gui-setup` pops a native OS dialog that captures `apikey` and `secretapikey` together, validates the pair against `POST /ping`, and stores them atomically in the OS keystore (or file fallback). The AI never sees any byte of either secret.

Per platform:

- **macOS**: `osascript` shows a two-field dialog (the first prompt with `default answer ""`, the second with `with hidden answer`) — or a single dialog body parsed via a delimiter (e.g. two `display dialog` calls, captured in subprocess.run). The CLI assembles the JSON blob from the two captures, calls `/ping`, and stores on success.
- **Linux**: `zenity --forms --add-password apikey --add-password secretapikey` (or `kdialog --getpassword` invoked twice as fallback).
- **Windows**: PowerShell `Get-Credential` returns a `PSCredential` whose `UserName` we treat as `apikey` and `Password` as `secretapikey` (with an in-script prompt noting the convention) — or two `Read-Host -AsSecureString` prompts in sequence.

The CLI uses `subprocess.run(..., capture_output=True, text=True)` to receive the dialog's stdout into Python memory. That memory is used to construct the auth payload and is discarded after the keystore write. **No echo to stdout, no log line, no error message ever includes the captured value.**

If `_has_display()` returns false (SSH session, headless server, no `$DISPLAY` / Quartz), `gui-setup` errors with a clear message and points the user at `porkbun-api-skill setup` (manual TTY path).

## Consequences

- AI-runnable add + rotate flows: the AI commits no security violation because it cannot inspect the dialog process's bytes.
- One dialog interaction for two secrets — slightly more UX friction than linode-api-skill's single-secret flow, but the user is going to copy both keys from the same Porkbun page anyway.
- The CLI must shell-escape the dialog prompt strings carefully. AppleScript and zenity each have their own escaping rules; we'll mirror linode-api-skill's escape-backslash-and-double-quote-and-strip-control-chars approach.
- Live dialog flow has only been validated on macOS for the sister project; Linux/Windows paths compile-pass but real-user validation is an alpha-period task.

## Alternatives considered

- **Two separate `gui-setup-apikey` and `gui-setup-secretapikey` commands.** Doubles the UX steps and creates a "what if I only entered one?" failure mode. Rejected.
- **`zenity --password` invoked twice without delimiting which is which.** Confusing UX; people will paste the wrong one into the wrong field. Rejected.
- **Out-of-band paste via a clipboard helper.** The CLI reads the clipboard, asks the user to copy each key in turn. Surprising and gives the AI a side channel (if it can read clipboard via other tools). Rejected.
- **A managed-account browser-OAuth flow.** Porkbun's API doesn't offer OAuth; this is hypothetical.

## Related

- Sister project: [`linode-api-skill` ADR-0004](https://github.com/aditya-m-bharadwaj/linode-api-skill/blob/main/docs/decisions/0004-ai-safe-token-entry-gui-dialog.md).
- ADRs: [[0003-cross-platform-credential-pair-storage]].
