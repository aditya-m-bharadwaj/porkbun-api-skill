Generate a session log per the memory protocol in this project's CLAUDE.md.

1. Pick a short slug for what this session was about (e.g. `add-dns-named-commands`, `wire-idempotency-key`).
2. Write a new file at `docs/progress/YYYY-MM-DD-<slug>.md` using `docs/progress/TEMPLATE.md` as the structure. Today's date in `YYYY-MM-DD` form.

The progress note must include:
- **What was done** — bullets with file paths, function names, commit hashes if relevant.
- **What's in-flight (not finished)** — what was started but blocked or deferred.
- **What's next (recommended pickup)** — one or two concrete next steps.
- **Open questions** — decisions not yet made, things to ask the operator about.
- **Related files / links** — wikilinks to ADRs touched (`[[NNNN-slug]]`), commit hashes, external links (the Porkbun docs at <https://porkbun.com/api/json/v3/spec>, the project's GitHub, etc.).

If a material design decision was made in this session (an architectural choice with tradeoffs that aren't obvious from the diff), also create a new ADR:

- Read the highest-numbered file in `docs/decisions/` to find the next ADR number.
- Copy `docs/decisions/TEMPLATE.md` → `docs/decisions/<NNNN>-<slug>.md` and fill it in.
- Reference the new ADR from the progress note via `[[<NNNN>-<slug>]]`.

If a reusable concept came up that's not specific to this project (e.g. a general pattern for handling dual-key auth, or idempotency-key behavior under retry), create a concept note in the operator's centralized vault at `~/.claude/vault/zettel/concepts/<concept-slug>.md`. Don't put concept notes in this repo's `docs/`.

**Commit alongside the code, not after it.** When the just-finished session produced a code/fix commit, the progress note / ADR / SKILL.md / CHANGELOG updates belong **in the same commit (or commit batch)** as the code change they document — not as a trailing `docs(...)` commit. Default: stage the docs alongside the code, then commit; or if a multi-commit batch, fold per-commit docs into each commit. Only exception: operator explicitly says "draft the progress note and stop."

Do **not** modify or delete existing notes. Only create new ones, or append to the in-flight progress note if a session continues across multiple invocations of this command.

After writing, list what was created so the operator can verify.
