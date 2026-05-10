Per the memory protocol in this project's CLAUDE.md:

1. Read the most recent file in `docs/progress/` (sorted by filename = sorted by date).
2. Read `graphify-out/GRAPH_REPORT.md` for current code structure. If it doesn't exist yet (e.g. fresh clone), run `graphify update .` first.
3. Read the 3 most recent files in `docs/decisions/`.
4. If the latest progress note flags an open API question or the CLI is being designed/built, also skim `docs/api-spec.json` (Porkbun v3 OpenAPI spec) for the relevant endpoint shape.

Then summarize for the operator:
- Where we left off (1-2 sentences).
- What's in-flight (started but not finished).
- What's next (recommended pickup, concrete next steps).
- Open questions (decisions not yet made).

Reference the actual files/commits by clickable path so the operator can verify. Do not modify any notes — `/resume` is read-only.
