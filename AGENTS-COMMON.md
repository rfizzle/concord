# AGENTS.md — shared region (Concord-owned)

> Canonical source for the **Concord-owned region** of every member mod's
> `AGENTS.md`. Everything between the single `<!-- concord:managed:start -->` /
> `<!-- concord:managed:end -->` pair below is synced verbatim into the matching
> block of each member's `AGENTS.md` by [`propagate.yml`](.github/workflows/propagate.yml)
> (job `sync-agents-regions`, via [`scripts/inject-agents-regions.py`](scripts/inject-agents-regions.py)).
>
> **Edit the shared guidance HERE, never in a mod repo.** Everything *outside*
> the managed block in a member `AGENTS.md` (project overview, mod id,
> entrypoints, assets, compat, commit-scope examples) is repo-owned and never
> touched by the sync. A member opts in once by carrying the marker pair; new
> sections added inside the block then propagate automatically, no per-section
> markers needed (see [`REPO-LAYOUT.md`](REPO-LAYOUT.md) §AGENTS.md).

<!-- concord:managed:start -->
## Working with domain skills

The suite's `mc-*` domain skills live under `.ai/skills/`, vendored from concord
and refreshed with `make sync`. The full list — each skill's one-line
summary and the situation that should make you pull it in — is the generated
catalog at [`.ai/skills/CATALOG.md`](.ai/skills/CATALOG.md). It is always in step
with the skills actually vendored here, so consult it rather than a hand-kept
table.

Claude Code auto-loads these via the `.claude/skills` symlink; Google Jules,
OpenCode, and any other agent should read the relevant `SKILL.md` directly
**before** working in its subject area.

## Custom art & audio

Custom, high-quality assets are encouraged across the suite — there are clean,
consistent pipelines for both (the `mc-textures` skill → `/glyph`, the `mc-audio`
skill → `/sfx`), so the bar is *fitness and coherence*, not vanilla purity. The
one hard cosmetic rule is the vanilla **font** (never a custom font in any
GUI/HUD/tooltip).

Decide *whether* to make a custom asset here, before reaching for a skill:

- **Default to custom where it serves a valid purpose** — identity, clarity, or a
  slot vanilla can't fill. This is not license for a blanket retexture or a
  wholesale soundscape overhaul; add assets where they earn their place, not for
  their own sake.
- **Use a vanilla asset when it is genuinely already right** — a trade UI literally
  showing an emerald, a literal bell on a bell block.
- **Audio also stays vanilla when the sound is organic** — a real horn, a physical
  bell, footsteps, foley — which pure synthesis renders obviously fake. Synthesis
  is for synthetic cues (alarms, UI blips, tech alerts, charge-ups, chiptune).

Once the decision is made, the `mc-textures` / `mc-audio` skills are the craft
reference for producing a good one. The normative spec is concord's
`design/DESIGN-SYSTEM.md` §8 (textures) and §9 (audio).

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
   the spec has no open questions, **`open-questions`** when it does. A
   player-facing change (new feature, config option, command, or gameplay rule)
   carries a **Docs impact** section naming the `site/` page(s) to update;
   internal-only work omits it.
4. **Human review** — spec edited or approved. For `open-questions`, answer the
   questions inline in the issue (no spec re-run needed for the simple cases).
5. **`jules` label** added → Jules picks up the issue and opens a draft PR.
   Apply it from either `ready` or `open-questions` once you're satisfied.
6. **PR opened** → `claude-code-review.yml` posts a structured ✓/⚠/✗ review
   (categories from concord's default `review-criteria.yml`, unless a
   repo-local `.ai/review-criteria.yml` override exists). For player-facing
   work it scores a **Site docs** category — a feature, config, command, or
   gameplay change that ships without the matching `site/` page update is
   flagged. `ci.yml` runs the full build, unit tests + gametests, and uploads
   coverage + results to Codecov.
7. **Human review + merge.**

`@claude <message>` in any issue or PR comment also invokes Claude for ad-hoc
help via `.github/workflows/claude.yml`.

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

## No tooling or session metadata

Commits, PR titles and bodies, issue and review comments, and code comments are
durable records for the humans reading this repo later — write them as if a
human did. Never add agent or tooling provenance:

- No agent/cloud **session or run links**, and no session/task/run IDs. They
  point at ephemeral, often private surfaces and mean nothing to a reader.
- No "generated by" / "co-authored-by" lines naming a tool or agent, and no
  tool banners, badges, or sign-offs.
- No narrating which agent did the work; the change stands on its content, and
  git already records authorship.

If your tooling appends such a footer by default, strip it before committing or
posting.

## Version scheme

The pushed `v*` tag is the single source of version truth. Releasing is just
`git tag vX.Y.Z && git push origin vX.Y.Z` — the release workflow injects the tag
as the build version. `mod_version=0.0.0` in `gradle.properties` is only the
local/dev base; local builds surface as `0.0.0+g<sha>`. Never hand-edit a real
version into `gradle.properties` or open a "set version" PR.
<!-- concord:managed:end -->
