# AGENTS.md — shared regions (Concord-owned)

> Canonical source for the **invariant regions** of every member mod's
> `AGENTS.md`. The text between each `<!-- concord:NAME:start -->` /
> `<!-- concord:NAME:end -->` pair below is synced verbatim into the matching
> region of each member's `AGENTS.md` by [`propagate.yml`](.github/workflows/propagate.yml)
> (job `sync-agents-regions`, via [`scripts/inject-agents-regions.py`](scripts/inject-agents-regions.py)).
>
> **Edit the shared lifecycle / version / skills guidance HERE, never in a mod
> repo.** Everything *outside* these regions in a member `AGENTS.md` (project
> overview, mod id, entrypoints, assets, compat, commit-scope examples) is
> repo-owned and never touched by the sync. A member only receives a region if
> it already carries the matching marker pair — seeding the markers once is the
> per-repo opt-in (see [`REPO-LAYOUT.md`](REPO-LAYOUT.md) §AGENTS.md).

<!-- concord:skills:start -->
## Working with domain skills

The suite's `mc-*` domain skills live under `.ai/skills/`, vendored from concord
and refreshed with `make sync-skills`. The full list — each skill's one-line
summary and the situation that should make you pull it in — is the generated
catalog at [`.ai/skills/CATALOG.md`](.ai/skills/CATALOG.md). It is always in step
with the skills actually vendored here, so consult it rather than a hand-kept
table.

Claude Code auto-loads these via the `.claude/skills` symlink; Google Jules,
OpenCode, and any other agent should read the relevant `SKILL.md` directly
**before** working in its subject area.
<!-- concord:skills:end -->

<!-- concord:lifecycle:start -->
## Development lifecycle

1. **Issue opened** using the feature or bug template under `.github/ISSUE_TEMPLATE/`.
2. **Triage** — human discussion in the issue.
3. **`needs-spec` label** added → `.github/workflows/claude-spec.yml` fires.
   Claude normalizes the issue title to a Conventional Commits form and writes
   a plain-language summary plus a structured implementation spec into the
   issue body, preserving the reporter's original text in between (prompt:
   concord's default `spec-writer.md`, unless a repo-local
   `.ai/prompts/spec-writer.md` override exists). Once the spec lands the
   `needs-spec` label is removed and a status label is added: **`ready`** when
   the spec has no open questions, **`open-questions`** when it does.
4. **Human review** — spec edited or approved. For `open-questions`, answer the
   questions inline in the issue (no spec re-run needed for the simple cases).
5. **`jules` label** added → Jules picks up the issue and opens a draft PR.
   Apply it from either `ready` or `open-questions` once you're satisfied.
6. **PR opened** → `claude-code-review.yml` posts a structured ✓/⚠/✗ review
   (categories from concord's default `review-criteria.yml`, unless a
   repo-local `.ai/review-criteria.yml` override exists). `ci.yml` runs the
   full build, unit tests + gametests, and uploads coverage + results to
   Codecov.
7. **Human review + merge.**

`@claude <message>` in any issue or PR comment also invokes Claude for ad-hoc
help via `.github/workflows/claude.yml`.
<!-- concord:lifecycle:end -->

<!-- concord:pr-conventions:start -->
## Pull requests & commits

When you open a pull request for an issue:

- **Title** — Conventional Commits with a topical scope, matching the issue's
  normalized title (e.g. `feat(render): add glyph atlas cache`). Imperative
  mood, lower-case, no trailing period.
- **Body** — open with a short plain-language summary of what changed and why,
  then link the source issue with `Closes #<n>` so it auto-closes on merge and
  the code review can pull the issue's spec for context. Use `Refs #<n>` only
  when the PR deliberately leaves part of the issue for later.
- **Commits** — Conventional Commits using the same scope vocabulary. Group the
  edits for one logical change together rather than scattering fixup commits.
- Run the project's build and tests before opening the PR, and open it only
  once the build is green.
<!-- concord:pr-conventions:end -->

<!-- concord:version-scheme:start -->
## Version scheme

Version is computed from git tags at build time (`build.gradle`,
`computeModVersion()`). Base version is in `gradle.properties` as
`mod_version`. Tagged commits produce clean versions; post-tag commits append
`+<commits>.g<sha>`.
<!-- concord:version-scheme:end -->
