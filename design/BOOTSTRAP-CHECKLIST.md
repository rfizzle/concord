# Bootstrap Checklist — from empty directory to feature development

The runway every new member mod walks before its first feature is built.
Companion to [`BOOTSTRAP-PROMPT.md`](BOOTSTRAP-PROMPT.md) (which automates
Phase 0) and the authoring guides beside this file. Work through the phases in
order — each one's items are the exit gate for starting the next; Phases 4 and
5 may run in parallel with each other. Track progress in a GitHub issue in the
new repo, not by copying this file into it (suite docs are linked, never
duplicated).

## Phase 0 — Admission & vision

- [ ] The domain passes the four admission tests (suite
      [`VISION.md`](../VISION.md) §9): domain fit, independence, MP-fairness,
      silo cleanliness — checked against every §8 rejection and the existing
      members' silos.
- [ ] The name fits the register (one weighty Latinate abstract noun, no
      compounds, no "Craft"/"Plus" suffixes) and the
      `<mod>-<domain>-overhaul` slug is unclaimed on CurseForge and Modrinth.
- [ ] The repo is scaffolded via [`BOOTSTRAP-PROMPT.md`](BOOTSTRAP-PROMPT.md):
      `git init`, README masthead stub, MIT `LICENSE`, `.gitignore` carrying
      the `# concord:gitignore:start/end` marker region.
- [ ] `design/VISION.md` is written per [`VISION-GUIDE.md`](VISION-GUIDE.md)
      and its "Checklist before committing" is green.
- [ ] Any tension with the suite vision surfaced during bootstrap has a human
      ruling — the suite vision is amended deliberately or the member reshaped.

## Phase 1 — Design truth (the Prosperity model: spec before code)

- [ ] `design/DESIGN.md` per [`DESIGN-GUIDE.md`](DESIGN-GUIDE.md): narrative,
      tagline, motif, logo description detailed enough to regenerate the
      masters, and the four signature colors passing the pairing rule against
      the full [`DESIGN-SYSTEM.md`](DESIGN-SYSTEM.md) §2 table, reserved rows
      included.
- [ ] The HUD decision is recorded with its reasoning against
      [`HUD-STANDARD.md`](../HUD-STANDARD.md)'s test (persistent ambient
      state only) — "no slot, by design" is the default answer.
- [ ] `design/SPEC.md` per [`SPEC-GUIDE.md`](SPEC-GUIDE.md): every feature
      with Problem, Behavior, edge cases, and config; every quantity a
      number, range, or formula (the vision's headline numbers move into the
      spec's ownership here); multiplayer behavior stated for every feature
      it could touch.
- [ ] The `com.rfizzle.<mod>.api` surface is specced from day one per
      [`API-STANDARD.md`](../API-STANDARD.md) — accessors, events, provider
      hooks — and every sibling integration is listed with its direction
      (provider → consumer) and marked optional.
- [ ] `design/ASSETS.md` per [`ASSETS-GUIDE.md`](ASSETS-GUIDE.md): the full
      planned-asset manifest, `MISSING` rows honest.

## Phase 2 — Brand masters

- [ ] `art/logo.png` follows the stone-frame logo formula; `art/icon-128.png`
      exists; a 16×16 glyph only if the mod has a HUD slot or a
      recipe-viewer/Jade presence that wants one.
- [ ] Every pipeline-generated master has its `.glyph` source beside it, same
      basename; generation prompts for non-glyph masters live in
      `art/exploration/`.
- [ ] The README masthead embeds `art/logo.png`.

## Phase 3 — Working repo skeleton

- [ ] Gradle/Loom project with the split source sets (`main`, `client`,
      `gametest`, `test`), `fabric.mod.json` (mod id, icon, empty
      entrypoints), and Mojang mappings — `make build` is green and the
      client launches.
- [ ] One trivial gametest and one trivial JUnit test exist and pass, so the
      CI wiring is exercised before real features depend on it.
- [ ] Coverage is wired the suite way from day one: the JaCoCo agent attached
      to `runGametest` and a `jacocoMergedReport` task merging unit + gametest
      execution data (snippets in the `mc-gradle-builds` skill), so the
      coverage number is honest before the first real feature lands.
- [ ] `AGENTS.md` per the Tribulation skeleton with the "Suite standards
      (Concord)" section (snippet in concord's README) and the
      `<!-- concord:managed:start/end -->` marker pair seeded; `CLAUDE.md` is
      a symlink to it.
- [ ] `Makefile` carries the standard `sync` target (concord README); `make
      sync` has run — `.ai/skills/` + `.ai/commands/` vendored,
      `.ai/skills/.concord-rev` present, `.claude/skills` and
      `.claude/commands` symlinks in place so `/glyph`, `/align`, and
      `/implement` work.
- [ ] All eight `.github/workflows/` caller stubs exist with the `uses:` refs
      and `permissions:` blocks pinned in
      [`workflow-stubs.json`](../workflow-stubs.json).
- [ ] The repo's GitHub settings match
      [`REPO-SETTINGS.md`](REPO-SETTINGS.md) — merge policy, `master`
      protection, Actions permissions, the `CLAUDE_CODE_OAUTH_TOKEN` secret,
      and the five suite labels (release-time items like store tokens and the
      §7 security features wait for Phase 5 and the release).
- [ ] CI is green on the empty skeleton.

## Phase 4 — Suite admission

- [ ] [`members.json`](../members.json) gains the member entry (id, name,
      tagline, url, store block as slugs are registered) — this is what puts
      the repo on the sync and propagation trains.
- [ ] The suite [`VISION.md`](../VISION.md) is amended: the mod moves from §9
      candidate to member (§1 table and tagline list, §3.1 palette table,
      §3.3 HUD table if it takes a slot).
- [ ] [`DESIGN-SYSTEM.md`](DESIGN-SYSTEM.md) §2 records the signature pair,
      reserving it under the pairing rule.
- [ ] From concord: `make agents-sync`, `make gitignore-sync`, and `make
      stubs-check` all pass clean against the new repo.

## Phase 5 — Site & listings (parallel with Phase 4)

- [ ] `site/site.json` (id matching `members.json`, theme colors from
      `DESIGN.md`) plus the starter `pages/` set (index, features, config,
      commands, developers, faq) and `assets/` web copies, per the schema in
      [`template/README.md`](../template/README.md).
- [ ] `listing-modrinth.md` / `listing-curseforge.md` drafts in `site/`;
      store projects registered as drafts under the slug convention.
- [ ] The `site.yml` stub deploys to Pages (source: GitHub Actions) and the
      site is live at `<mod>.rfizzle.com` — land this close to the
      `members.json` entry so the cross-mod footer never links a dead site.

## Ready for feature development when

1. Every `design/` doc is green against its guide's checklist.
2. `make build`, CI, and `make stubs-check` are green.
3. The vendored skills and commands are in place (`.concord-rev` present), so
   the `/implement` pipeline can read the vision's domain gate and the spec.
4. The `members.json` entry is live and the sync machinery owns its regions.

The site may still be thin at this point — it markets what has shipped, and
nothing has — but it must be live before the first release. From here,
features flow through the normal lifecycle: issue → spec → `/implement` →
review, with `SPEC.md` updated in the same PR whenever behavior changes by
design. The feature set itself is revisited in working sessions via
[`TUNING-PROMPT.md`](TUNING-PROMPT.md).
