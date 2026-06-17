# Concord Repo Layout Standard

> Where non-programmatic files live, so all Concord member repos (and every future
> member) mirror each other. Grounded in the current state of `meridian`, `mercantile`,
> `tribulation`, and `prosperity` as of 2026-06-11. Companion to [`VISION.md`](VISION.md).

The rule of thumb: **`src/` is for the compiler, `site/` is for the website,
everything else that's text or art has exactly one named home.** Meridian
(2026-06-11) and Mercantile (2026-06-12) completed their migrations and join
Tribulation as references; the remaining work is Tribulation's last root moves
and Prosperity.

---

## 1. The canonical tree

```
<mod>/
├── README.md                  # feature summary + dev/API section; only prose doc at root
├── LICENSE                    # MIT
├── AGENTS.md                  # AI agent guidance: conventions, layout, lifecycle
├── CLAUDE.md                  # symlink → AGENTS.md (Tribulation pattern)
├── Makefile                   # task shortcuts wrapping gradle
├── codecov.yml
├── build.gradle / settings.gradle / gradle.properties
├── gradlew / gradlew.bat / gradle/
│
├── .ai/                       # AI working area (committed)
│   ├── README.md              #   what lives here and why
│   ├── skills/                #   vendored from concord — refresh via `make sync-skills`
│   ├── skills/.concord-rev    #   provenance: concord SHA of the last sync
│   ├── commands/              #   vendored from concord — slash commands (/glyph, /sfx)
│   └── prompts/, review-criteria.yml  # OPTIONAL overrides of the concord defaults
│
├── .claude/                   # Claude Code local state (mostly gitignored)
│   ├── skills/                #   symlink → ../.ai/skills (vendored skills)
│   ├── commands/              #   symlink → ../.ai/commands (vendored slash commands)
│   └── settings.local.json    #   gitignored
│
├── .plan/                     # local planning scratchpad (gitignored, never committed)
│
├── design/                    # the "why & what" — pre-implementation truth
│   ├── DESIGN.md              #   vision, brand, palette, motifs, HUD slot
│   ├── SPEC.md                #   full behavioral spec (the Prosperity model)
│   ├── REVIEW.md              #   spec review findings, when one exists
│   └── handoffs/              #   one-shot agent handoff briefs (archived after use)
│
├── art/                       # art masters & working files (web copies live in docs/)
│   ├── logo.png               #   full logo master (stone-frame formula)
│   ├── icon-128.png           #   mod icon master (fabric.mod.json / store listings)
│   ├── hud-icon-16.png        #   HUD/UI glyph master (omit if mod has no HUD slot)
│   ├── hud-icon-16.glyph      #   .glyph source beside each pipeline master (re-renderable)
│   └── exploration/           #   style explorations, rejected variants, gen prompts
│
├── site/                      # website CONTENT (built by the shared Concord template)
│   ├── site.json              #   identity, nav, theme colors, links
│   ├── pages/<slug>.json      #   one structured-content file per page
│   ├── assets/                #   logo.png, icon.png, og-image.png, favicons
│   ├── listing-modrinth.md    #   store listing copy (Mercantile pattern)
│   └── listing-curseforge.md
│
├── scripts/                   # repo automation
│   └── release.sh
│
├── src/                       # code only — Loom split source sets
│   ├── main/                  #   server + common
│   ├── client/                #   client-only
│   ├── gametest/              #   Fabric gametests (not in jar)
│   └── test/                  #   JUnit
│
└── .github/                   # CI, issue/PR templates
```

**Gitignored runtime/IDE dirs** (never committed, standard list in §4): `.gradle/`,
`build/`, `out/`, `classes/`, `run/`, `mods/`, `logs/`, `config/`, `.idea/`, `.vscode/`,
`_site/` (the generated website), `.plan/` (local planning).

**`docs/` is retired.** The website is no longer committed: `site/` holds the
structured content, the shared template in the concord repo renders it, and CI
deploys the result straight to GitHub Pages (source: "GitHub Actions"). During
migration a repo may still carry its legacy `docs/` until its `site/` build is
verified live.

---

## 2. Directory-by-directory rules

### Root
Text only, and only the files listed above. No binaries (logo moves to `art/` —
README embeds `art/logo.png` instead), no design docs, no stray logs or compiled
classes. `README.md` is the single prose document at root; everything deeper has a
directory.

`CLAUDE.md` is a **symlink to `AGENTS.md`** (already true in Tribulation) so every
agent finds what it expects without content drift. `AGENTS.md` follows the
Tribulation skeleton: project overview → build commands → source layout →
conventions (Mojang mappings, `<Mod>.id()` helper, conventional commits) →
development lifecycle.

The invariant tail sections — **Working with domain skills**, **Custom art &
audio**, **Development lifecycle**, **Pull requests & commits**, and **Version
scheme** — are Concord-owned: they sit together inside one
`<!-- concord:managed:start -->` / `<!-- concord:managed:end -->` block and are
kept in sync from concord's [`AGENTS-COMMON.md`](AGENTS-COMMON.md) by
`propagate.yml`, which proposes the update as a `concord-sync` PR (the default
branch is protected). Don't hand-edit between those markers; edit the canonical
copy in concord. The skills section is just a pointer to the generated
`.ai/skills/CATALOG.md` — the old per-repo "when you're touching X, read Y" table
is retired (it drifted: it hard-coded a skill count). A new repo opts in once by
pasting the single marker pair; sections added inside the block thereafter
propagate automatically, no new markers needed.

### `.ai/` — AI working area
Committed. `skills/` and `commands/` are **vendored from the concord repo** —
edit them in concord, refresh with `make sync-skills` (both directories are
wholly owned by the sync; `.concord-rev` records the source SHA). Claude Code
reaches them via `.claude/skills` → `.ai/skills` and `.claude/commands` →
`.ai/commands` symlinks, so vendored skills and slash commands (like `/glyph`)
work here. The generated `skills/CATALOG.md`
(concord's `make catalog`) indexes the skills and rides the same sync, so
`AGENTS.md` points at it rather than repeating the list. CI prompts and review criteria
default to concord's `.ai/`; a repo-local `prompts/*.md` or
`review-criteria.yml` here is a whole-file override (see the resolution order
in concord's README). One-shot handoff briefs belong in `design/handoffs/`;
reusable role prompts belong in concord.

### `.plan/` — planning (local only)
A local dev scratchpad, **never committed** — the whole directory is gitignored
(decided 2026-06-11 during the Meridian migration). Durable work tracking lives
in GitHub Issues (the `needs-spec` → `jules` lifecycle); anything under `.plan/`
is personal working state. Repos that still commit `.plan/` files (Mercantile)
untrack them as part of their migration.

### `design/` — pre-implementation truth
The **why and what**, kept out of the published site (Tribulation currently
publishes its DESIGN.md inside `docs/` — that moves out). Fixed names: `DESIGN.md`
(brand, palette, motif, HUD slot decision), `SPEC.md` (behavioral spec), `REVIEW.md`
(spec review). Specs are written *before* implementation (the Prosperity model) and
updated when behavior changes — `README.md`/`docs/` describe what *is*; `design/`
records what was *intended* and why.

### `art/` — masters
Source-of-truth images and working files. `docs/` and `src/main/resources/assets/`
hold *derived, optimized copies*; when art changes, the master changes first.
Generation prompts (Gemini/PixelLab) live next to their outputs in `exploration/`.
Every pipeline-generated master ships its **`.glyph` source beside it**, same basename
(`hud-icon-16.png` ↔ `hud-icon-16.glyph`), so the texture is re-renderable for minor edits
— the spec is the source of truth (concord `design/DESIGN-SYSTEM.md` §8, the `mc-textures`
skill). Custom, high-quality textures are encouraged.

### `site/` — website content, not website output
The mod repo holds only structured content: `site.json` (identity, nav order, the
four theme colors), `pages/<slug>.json` (one per page, block-based — schema in the
concord repo's `template/README.md`), and `assets/` (image masters' web copies).
The shared Concord template renders it; `.github/workflows/site.yml` (≈15 lines,
calls concord's reusable workflow) deploys it to Pages. Local preview: `make site`.
Store listing copy (`listing-modrinth.md`, `listing-curseforge.md`) lives here too.
Generated `_site/` output is never committed.

### `scripts/`
Executable automation only (`release.sh` is the current standard member). Anything
an agent or human runs by hand. Makefile targets wrap these.

---

## 3. Naming conventions

- Directories: lowercase, singular (`design/`, `art/`, not `designs/`)
- Canonical docs: UPPERCASE fixed names (`DESIGN.md`, `SPEC.md`, `BACKLOG.md`) —
  greppable across all repos at the same path
- Everything else kebab-case (`feature-review-handoff.md`, `listing-modrinth.md`)
- Suite-level documents (this file, `VISION.md`, `API-STANDARD.md`,
  `HUD-STANDARD.md`, `design/DESIGN-SYSTEM.md`) live in the **concord repo**
  (`../concord/` in the local workspace), never duplicated into mod repos; each
  mod's `AGENTS.md` carries a "Suite standards (Concord)" section linking to them
  (snippet in the concord README)

---

## 4. Standard `.gitignore`

Tribulation's is the baseline; add the planning/AI local-state entries:

```gitignore
# gradle
.gradle/
build/
out/
classes/

# loom dev runtime
run/
mods/
logs/
config/

# IDE
.idea/
*.iml
*.ipr
*.iws
.settings/
.vscode/
.classpath
.project
*.launch

# local AI / planning state
.claude/settings.local.json
.claude/projects/
.claude/scheduled_tasks.lock
.plan/

# OS junk
.DS_Store
Thumbs.db

# stray runtime artifacts
replay_pid*.log
hs_err_pid*.log
```

---

## 5. Per-repo migration checklist

### Meridian (migrated 2026-06-11 — PRs #22–#26)
- [x] `mkdir design/` ; `git mv DESIGN.md design/DESIGN.md`
- [x] Write `AGENTS.md` (adapt Tribulation's skeleton); `ln -s AGENTS.md CLAUDE.md`
- [x] Create `.ai/` (README + `skills/` vendored from concord; no prompt/criteria
      overrides — concord defaults apply). `.plan/` is local-only per the updated
      standard, so nothing to commit
- [x] `mkdir art/` ; `git mv logo.png art/logo.png` ; update README `<img src>` →
      `art/logo.png`; add `icon-128.png` master (copy of the in-jar icon)
- [x] **Delete stray `net/` directory** (compiled `.class` files at repo root) and
      gitignore the pattern
- [x] Adopt the standard `.gitignore`; add `codecov.yml` (JaCoCo wired in CI;
      `CODECOV_TOKEN` secret still unset — upload is optional until added)
- [x] Migrate `docs/` to `site/` content + `site.yml`; `docs/curseforge.md` →
      `site/listing-curseforge.md`; `listing-modrinth.md` added; legacy `docs/`
      deleted after verifying meridian.rfizzle.com live (Pages source: Actions)

### Mercantile (migrated 2026-06-12)
- [x] `spec/` → `design/` ; `design/DESIGN.md` written (brand seeded from
      `VISION.md` §2–3 + the live site palette). Bonus: `SPEC.md`/`REVIEW.md`
      were gitignored before — they are now actually tracked
- [x] `mkdir art/` ; `git mv logo.png art/logo.png` ; README img src updated;
      `icon-128.png` master added (derived from the 1024px docs icon)
- [x] **Delete `replay_pid391.log`**; standard `.gitignore` adopted; the log
      blob was also expunged from history (master rewritten + force-pushed
      2026-06-12)
- [x] `.plan/` was already untracked; now gitignored as a whole directory
- [x] `CLAUDE.md` verified as a symlink to `AGENTS.md`; `.ai/` prompt/criteria
      overrides dropped (they were the ancestors of the concord defaults)
- [x] CI workflows replaced with thin stubs calling the concord reusables;
      `test.yml` dropped (covered by `mod-ci.yml`)
- [x] Migrate `docs/` to `site/` content + `site.yml`; listings moved to
      `site/listing-*.md`; mercantile.rfizzle.com verified live on the
      Actions Pages source and legacy `docs/` removed (PR #2)

### Tribulation (reference repo — one move)
- [ ] `mkdir design/` ; `git mv docs/design/DESIGN.md design/DESIGN.md` ;
      `git mv docs/design/feature-review-handoff.md design/handoffs/` ; remove the
      now-empty `docs/design/` (design docs no longer published with the site)
- [ ] `mkdir art/` ; `git mv logo.png art/logo.png` ; update README img src; copy
      icon master in
- [x] Migrate `docs/` to `site/` content + `site.yml` workflow (done — the pilot);
      delete legacy `docs/` once the Pages build is verified live; move
      `docs/curseforge.md` → `site/listing-curseforge.md`; add `listing-modrinth.md`
- [ ] Gitignore `.claude/scheduled_tasks.lock` and `.plan/`

### Prosperity (greenfield — scaffold the standard from day one)
- [ ] `mkdir design/` ; `git mv DESIGN.md SPEC.md design/`
- [ ] `git mv art/hud-exploration art/exploration` ;
      `git mv art/hud_icon_prosperity.png art/hud-icon-16.png`
- [ ] Initialize as a git repo with the standard `.gitignore` (currently not one)
- [ ] Write `AGENTS.md` + `CLAUDE.md` symlink, `.ai/` (skills vendored from
      concord); track the build plan from `VISION.md` §6 in GitHub Issues
- [ ] **Delete `.claude/blah.txt`**
- [ ] `docs/` stays empty until the site is built; add `CNAME`
      (`prosperity.rfizzle.com`) when Pages is enabled
- [ ] Gradle scaffold, `Makefile`, `scripts/release.sh`, `src/` split source sets,
      `README.md`, `LICENSE`, `codecov.yml` arrive with Phase 1 of the build plan

---

## 6. Definition of "mirrored"

A repo conforms when all of these are true at the same paths:

1. `README.md`, `LICENSE`, `AGENTS.md`, `CLAUDE.md` (symlink), `Makefile` at root —
   and nothing else prose or binary at root
2. `design/DESIGN.md` exists (and `design/SPEC.md` for any mod specced before/while
   being built)
3. `.ai/` with `skills/` vendored from concord (`prompts/` / `review-criteria.yml`
   only as deliberate whole-file overrides — concord defaults otherwise); no
   committed `.plan/`
4. `art/logo.png` + `art/icon-128.png` masters; README embeds `art/logo.png`
5. `site/` contains the structured website content (`site.json`, `pages/`,
   `assets/`, `listing-*.md`) + a `site.yml` workflow calling concord's reusable
   build; no committed `docs/` or `_site/` output
6. The standard `.gitignore`, with no committed runtime artifacts (`logs/`, `run/`,
   `replay_pid*`, compiled classes)

Future members (Husbandry, Apothecary, …) are created from this layout before any
code exists — Prosperity post-migration is the template.
