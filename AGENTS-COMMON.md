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
3. **`needs-spec` label** added → `.github/workflows/claude-spec.yml` fires,
   Claude posts a structured implementation spec as an issue comment
   (prompt: concord's default `spec-writer.md`, unless a repo-local
   `.ai/prompts/spec-writer.md` override exists).
4. **Human review** — spec edited or approved.
5. **`jules` label** added (remove `needs-spec`) → Jules picks up the issue
   and opens a draft PR.
6. **PR opened** → `claude-code-review.yml` posts a structured ✓/⚠/✗ review
   (categories from concord's default `review-criteria.yml`, unless a
   repo-local `.ai/review-criteria.yml` override exists). `ci.yml` runs the
   full build, unit tests + gametests, and uploads coverage + results to
   Codecov.
7. **Human review + merge.**

`@claude <message>` in any issue or PR comment also invokes Claude for ad-hoc
help via `.github/workflows/claude.yml`.
<!-- concord:lifecycle:end -->

<!-- concord:version-scheme:start -->
## Version scheme

Version is computed from git tags at build time (`build.gradle`,
`computeModVersion()`). Base version is in `gradle.properties` as
`mod_version`. Tagged commits produce clean versions; post-tag commits append
`+<commits>.g<sha>`.
<!-- concord:version-scheme:end -->
