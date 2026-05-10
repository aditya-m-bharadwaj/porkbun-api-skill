---
name: Feature request
about: Suggest a new capability, classifier entry, or workflow
title: "feat: <short summary>"
labels: ["enhancement"]
assignees: []
---

## Problem

What are you trying to do that the current CLI doesn't support, or that it
makes unnecessarily hard? Describe the *workflow*, not the *solution*.

## Proposed solution

Your idea for how to address it. If it's a new endpoint or classifier change,
include:

- HTTP method and path (e.g. `POST /v3/dns/createBulk/{domain}`)
- Proposed safety tier: `read` / `mutating` / `destructive` / `billable` / `privilege`
- Justification for the tier (link to the [Porkbun API docs](https://porkbun.com/api/json/v3/spec) if possible)

## Alternatives considered

Other approaches you ruled out and why.

## Additional context

Links, prior art, or examples from other tools.
