# Concord Repo Layout Standard

> Where non-programmatic files live, so all Concord member repos (and every future
> member) mirror each other. Grounded in the current state of `meridian`, `mercantile`,
> `tribulation`, and `prosperity` as of 2026-06-10. Companion to [`VISION.md`](VISION.md).

The rule of thumb: **`src/` is for the compiler, `docs/` is for the website,
everything else that's text or art has exactly one named home.** Tribulation and
Mercantile are closest to this standard already; most of the migration work is in
Meridian and Prosperity.

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
│   ├── prompts/               #   reusable role prompts + one-shot handoffs
│   ├── skills/                #   repo-specific skills
│   └── review-criteria.yml    #   automated review rubric
│
├── .claude/                   # Claude Code local state (mostly gitignored)
│   ├── skills/                #   committed if repo-specific
│   └── settings.local.json    #   gitignored
│
├── .plan/                     # lightweight planning (committed, logs gitignored)
│   ├── BACKLOG.md
│   ├── SPRINT.md
│   └── DONE.md
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
│   └── exploration/           #   style explorations, rejected variants, gen prompts
│
├── docs/                      # the published website ONLY (GitHub Pages root)
│   ├── CNAME                  #   <mod>.rfizzle.com
│   ├── index.html             #   + features/config/commands/faq/guide/changelog/
│   │                          #     developers.html and domain pages per VISION.md §4
│   ├── css/
│   ├── logo.png, icon.png     #   web-optimized copies of art/ masters
│   ├── og-image.png, favicon.ico, favicon-32.png, apple-touch-icon.png
│   ├── robots.txt, sitemap.xml
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
`build/`, `out/`, `classes/`, `run/`, `mods/`, `logs/`, `config/`, `.idea/`, `.vscode/`.

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

### `.ai/` — AI working area
Committed. Reusable prompts (`prompts/code-reviewer.md`, `prompts/spec-writer.md`),
repo skills, and `review-criteria.yml`. One-shot handoff briefs (like
`suite-vision-handoff.md`) belong in `design/handoffs/` once they're about *this
mod's* design, or in `.ai/prompts/` if they're reusable roles — the test is
"would a second run produce a different artifact?" Reusable → `.ai/prompts/`,
one-shot → `design/handoffs/`.

### `.plan/` — planning
Three files, fixed names: `BACKLOG.md` (prioritized, feeds from `VISION.md`
§6), `SPRINT.md` (current slice), `DONE.md` (append-only log). Runner/review logs
under `.plan/` are gitignored. Repos that track everything in GitHub Issues keep
the directory with `BACKLOG.md` pointing at the issue tracker — presence is what
makes the repos mirror.

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

### `docs/` — the website, nothing else
`docs/` *is* the GitHub Pages artifact. If a file isn't meant to be served at
`<mod>.rfizzle.com`, it doesn't go here. Store listing copy (`listing-modrinth.md`,
`listing-curseforge.md`) is the sanctioned exception — it's distribution-facing and
harmless to serve. Standard page set per `VISION.md` §4.

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
.plan/logs/
.plan/*.log

# OS junk
.DS_Store
Thumbs.db

# stray runtime artifacts
replay_pid*.log
hs_err_pid*.log
```

---

## 5. Per-repo migration checklist

### Meridian (largest gap — no AI/plan scaffolding)
- [ ] `mkdir design/` ; `git mv DESIGN.md design/DESIGN.md`
- [ ] Write `AGENTS.md` (adapt Tribulation's skeleton); `ln -s AGENTS.md CLAUDE.md`
- [ ] Create `.ai/` (README, `prompts/` seeded from Tribulation's code-reviewer /
      spec-writer, `review-criteria.yml`) and `.plan/` (BACKLOG/SPRINT/DONE)
- [ ] `mkdir art/` ; `git mv logo.png art/logo.png` ; update README `<img src>` →
      `art/logo.png`; add `icon-128.png` master (copy of the in-jar icon)
- [ ] **Delete stray `net/` directory** (compiled `.class` files at repo root) and
      gitignore the pattern
- [ ] Adopt the standard `.gitignore`; add `codecov.yml` when tests report coverage
- [ ] Rename `docs/curseforge.md` → `docs/listing-curseforge.md`; add
      `listing-modrinth.md`

### Mercantile (closest to standard — mostly renames)
- [ ] `git mv spec design` ; write `design/DESIGN.md` (it's the only mod without
      one — brand section can seed from `VISION.md` §2–3)
- [ ] `mkdir art/` ; `git mv logo.png art/logo.png` ; update README img src; copy
      icon master in
- [ ] **Delete `replay_pid391.log`**; gitignore `replay_pid*.log` and `config/`
- [ ] Move `.plan/logs`, `*.log` files under `.plan/` into gitignore (keep the
      three MD files committed)
- [ ] `CLAUDE.md` → verify it's a symlink to `AGENTS.md` (convert if a copy)

### Tribulation (reference repo — one move)
- [ ] `mkdir design/` ; `git mv docs/design/DESIGN.md design/DESIGN.md` ;
      `git mv docs/design/feature-review-handoff.md design/handoffs/` ; remove the
      now-empty `docs/design/` (design docs no longer published with the site)
- [ ] `mkdir art/` ; `git mv logo.png art/logo.png` ; update README img src; copy
      icon master in
- [ ] Rename `docs/curseforge.md` → `docs/listing-curseforge.md`; add
      `listing-modrinth.md`
- [ ] Add `.plan/` (BACKLOG.md may simply point at GitHub Issues)
- [ ] Gitignore `.claude/scheduled_tasks.lock`

### Prosperity (greenfield — scaffold the standard from day one)
- [ ] `mkdir design/` ; `git mv DESIGN.md SPEC.md design/`
- [ ] `git mv art/hud-exploration art/exploration` ;
      `git mv art/hud_icon_prosperity.png art/hud-icon-16.png`
- [ ] Initialize as a git repo with the standard `.gitignore` (currently not one)
- [ ] Write `AGENTS.md` + `CLAUDE.md` symlink, `.ai/` (seed from Tribulation),
      `.plan/` (BACKLOG.md = the build plan from `VISION.md` §6)
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
3. `.ai/` with `prompts/` + `review-criteria.yml`; `.plan/` with the three MD files
4. `art/logo.png` + `art/icon-128.png` masters; README embeds `art/logo.png`
5. `docs/` contains only the published site + `listing-*.md`
6. The standard `.gitignore`, with no committed runtime artifacts (`logs/`, `run/`,
   `replay_pid*`, compiled classes)

Future members (Husbandry, Apothecary, …) are created from this layout before any
code exists — Prosperity post-migration is the template.
