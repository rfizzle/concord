# Concord Repo Layout Standard

> Where non-programmatic files live, so all Concord member repos (and every future
> member) mirror each other. Companion to [`VISION.md`](VISION.md).

The rule of thumb: **`src/` is for the compiler, `site/` is for the website,
everything else that's text or art has exactly one named home.** Every member
mirrors this layout; a new member is scaffolded from it before any code exists.

---

## 1. The canonical tree

```
<mod>/
├── README.md                  # feature summary + dev/API section; only prose doc at root
├── LICENSE                    # MIT
├── AGENTS.md                  # AI agent guidance: conventions, layout, lifecycle
├── CLAUDE.md                  # symlink → AGENTS.md (Tribulation pattern)
├── Makefile                   # task shortcuts wrapping gradle
├── build.gradle / settings.gradle / gradle.properties
├── versions-common.properties # suite toolchain pins — concord-owned, synced
├── gradlew / gradlew.bat / gradle/
│
├── .ai/                       # AI working area (committed)
│   ├── README.md              #   what lives here and why
│   ├── skills/                #   vendored from concord — refresh via `make sync`
│   ├── skills/.concord-rev    #   provenance: concord SHA of the last sync
│   ├── commands/              #   vendored from concord — slash commands (/glyph, /sfx)
│   ├── agents/                #   vendored from concord — /implement pipeline sub-agents
│   └── prompts/, review-criteria.yml  # OPTIONAL overrides of the concord defaults
│
├── .claude/                   # Claude Code local state (mostly gitignored)
│   ├── skills/                #   symlink → ../.ai/skills (vendored skills)
│   ├── commands/              #   symlink → ../.ai/commands (vendored slash commands)
│   ├── agents/                #   symlink → ../.ai/agents (vendored sub-agents)
│   └── settings.local.json    #   gitignored
│
├── .plan/                     # local planning scratchpad (gitignored, never committed)
│
├── design/                    # the "why & what" — pre-implementation truth
│   ├── VISION.md              #   the player-experience promise, written for players
│   ├── DESIGN.md              #   brand, palette, motif, HUD slot
│   ├── SPEC.md                #   full behavioral spec (the Prosperity model)
│   └── ASSETS.md              #   asset manifest: .glyph source → final path, MISSING where none
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
│   ├── listing-curseforge.md
│   ├── listing-summary.txt    #   ≤256 chars — synced to the Modrinth description
│   └── github-description.txt #   the GitHub "About" blurb (manual)
│
├── changelogs/                # OPTIONAL hand-authored release notes
│   └── <version>.md           #   e.g. 1.0.0.md — published verbatim if present
│
├── scripts/                   # OPTIONAL repo automation (generators, a tag-only release.sh)
│
├── src/                       # code only — Loom split source sets
│   ├── main/                  #   server + common
│   ├── client/                #   client-only
│   ├── gametest/              #   Fabric gametests + their manifest and
│   │                          #   fixtures (not in jar)
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
conventions (Mojang mappings, the `MOD_ID` / `LOGGER` / `<Mod>.id()` bootstrap trio
from the `mc-registration` skill, conventional commits) → **Where things live**
(the map from a subsystem to its package) → **Compat integrations** (the soft deps
this mod probes for, and the guard each sits behind — omit it when there are none)
→ development lifecycle.

Those sections sit **outside** the Concord-owned block and stay repo-owned: they
describe this mod's packages and this mod's integrations, so there is nothing for
concord to say. The sync never touches them.

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

### `Makefile`
Thin task shortcuts wrapping gradle, and a fixed contract: the canonical target
list, recipes, and `help` descriptions live in concord's
[`makefile-targets.json`](makefile-targets.json) and are checked by
`make makefile-check`. Thirteen targets are required in every member and are
byte-identical across the suite once the jar name is substituted — `build`, `jar`,
`test`, `run-client`, `run-server`, `gen-sources`, `refresh-deps`, `clean`,
`version`, `release`, `site`, `site-serve`, `sync`.

Two more are required **conditionally**, owed when the member's `build.gradle`
wires what they drive:

- `coverage` — when `jacocoMergedReport` is wired. Without the target, the
  documented way to get the mod's real coverage number is missing, and what a
  reader finds instead is the unit-only report.
- `run-datagen` — when a Loom `datagen` run config exists (the third of the four
  datagen anchors in the `mc-datagen` skill).

`help` is the one recipe that varies, because it lists only the targets that
member has. It is held to the contract as an *ordered projection* of those
descriptions rather than byte-for-byte — the wording of each line is fixed even
though the set of lines is not. Targets beyond the contract are a member's own
business: the list is a floor, not a ceiling.

### `.ai/` — AI working area
Committed. `skills/` and `commands/` are **vendored from the concord repo** —
edit them in concord; the `concord-sync` PR proposes refreshes automatically when
they change on concord's `master`, or run `make sync` locally to work ahead of it
(both directories are wholly owned by the sync — removals propagate; `.concord-rev`
records the source SHA). Claude Code
reaches them via `.claude/skills` → `.ai/skills`, `.claude/commands` →
`.ai/commands`, and `.claude/agents` → `.ai/agents` symlinks, so vendored skills,
slash commands (like `/glyph`), and sub-agents work here. All three symlinks are
committed.

`agents/` holds the sub-agents the `/implement` pipeline dispatches — `recon`,
`domain-reviewer`, `standards-reviewer`, `performance-reviewer` — each pinning its
own model in frontmatter. It is vendored from concord like the other two, but on a
**different channel**: `make sync` rsyncs it, while the automatic `concord-sync` PR
does not carry it. Editing an agent in concord therefore reaches members only when
someone runs `make sync`; a member whose agents look stale is not a sync failure.

The generated `skills/CATALOG.md`
(concord's `make catalog`) indexes the skills and rides the same sync, so
`AGENTS.md` points at it rather than repeating the list. CI prompts and review criteria
default to concord's `.ai/`; a repo-local `prompts/*.md` or
`review-criteria.yml` here is a whole-file override (see the resolution order
in concord's README). Reusable role prompts belong in concord.

### `.plan/` — planning (local only)
A local dev scratchpad, **never committed** — the whole directory is gitignored.
Durable work tracking lives in GitHub Issues (the `needs-spec` → `jules`
lifecycle); anything under `.plan/` is personal working state.

### `design/` — pre-implementation truth
The **why and what**, kept out of the published site. Fixed names: `VISION.md`
(the player-experience promise — written for players, zero implementation
vocabulary), `DESIGN.md` (brand, palette, motif, HUD slot decision), `SPEC.md`
(behavioral spec), `ASSETS.md` (asset manifest — each asset's `.glyph` source under
`art/`, its final resource/site path, and `MISSING` where no glyph source exists
yet). Each fixed name has an authoring guide in concord prescribing its shape,
requirements, and truth direction:
[`design/VISION-GUIDE.md`](design/VISION-GUIDE.md),
[`design/DESIGN-GUIDE.md`](design/DESIGN-GUIDE.md),
[`design/SPEC-GUIDE.md`](design/SPEC-GUIDE.md),
[`design/ASSETS-GUIDE.md`](design/ASSETS-GUIDE.md). Specs are written *before* implementation (the Prosperity model) and
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
Store listing copy lives here too, in four files split by how they reach their
destination. `listing-modrinth.md` and `listing-summary.txt` are **synced**: the
`listing-sync.yml` stub calls concord's `mod-listing-sync.yml`, which pushes the
body and — when the summary file is non-empty — the ≤256-character Modrinth
description, failing the run if it is longer. An absent summary file is skipped
silently, so a member that wants one has to have one. `listing-curseforge.md` and
`github-description.txt` are **manual** copy-paste sources — CurseForge has no
public write API, and the GitHub "About" blurb is set through the repo settings —
so nothing reads them and nothing will tell you when they go stale.
Generated `_site/` output is never committed.

### `scripts/`
Optional. Executable automation only — anything an agent or human runs by hand;
Makefile targets wrap these. `make release` (tag-and-push) is the standard
release entry point; a repo-local `release.sh` is optional sugar around it and
must stay tag-only per the version scheme in [`AGENTS-COMMON.md`](AGENTS-COMMON.md)
— it never writes a version into `gradle.properties`.

---

## 3. Naming conventions

- Directories: lowercase, singular (`design/`, `art/`, not `designs/`)
- Canonical docs: UPPERCASE fixed names (`DESIGN.md`, `SPEC.md`, `BACKLOG.md`) —
  greppable across all repos at the same path
- Everything else kebab-case (`listing-modrinth.md`, `listing-curseforge.md`)
- Suite-level documents (this file, `VISION.md`, `API-STANDARD.md`,
  `HUD-STANDARD.md`, `design/DESIGN-SYSTEM.md`) live in the **concord repo**
  (`../concord/` in the local workspace), never duplicated into mod repos; each
  mod's `AGENTS.md` carries a "Suite standards (Concord)" section linking to them
  (snippet in the concord README)

---

## 4. Standard `.gitignore`

The common ignores are a Concord-owned managed region, synced from concord's
[`gitignore-common`](gitignore-common) into each member's `.gitignore` (between
`# concord:gitignore:start` / `# concord:gitignore:end`) by `propagate.yml` — the
same mechanism as the `AGENTS.md` regions. Edit the shared list in
`gitignore-common`, never in a mod repo; put repo-specific ignores **outside** the
marker block, where the sync never touches them. A member opts in by carrying the
marker pair once (`make gitignore-sync` from concord seeds and refreshes siblings
checked out as `../<member>`).

**Defensive anchoring.** Every ignore whose name could collide with a source,
package, or resource directory — `build out bin classes net .gradle run mods logs
config _site .plan` — is anchored with a leading `/` so it matches only at repo
root, never a nested dir like `src/.../config/`. An unanchored `config/` silently
swallows a Java package of that name. Genuinely global junk (IDE/OS files,
`*.iml`, JVM crash dumps) stays unanchored so it is caught at any depth.

---

## 5. Definition of "mirrored"

A repo conforms when all of these are true at the same paths:

1. `README.md`, `LICENSE`, `AGENTS.md`, `CLAUDE.md` (symlink), `Makefile` at root —
   and nothing else prose or binary at root
2. `design/` carries the four fixed names — `VISION.md`, `DESIGN.md`, `SPEC.md`,
   `ASSETS.md` (§2)
3. `.ai/` with `skills/`, `commands/`, and `agents/` vendored from concord, and the
   matching `.claude/` symlinks committed (`prompts/` / `review-criteria.yml`
   only as deliberate whole-file overrides — concord defaults otherwise); no
   committed `.plan/`
4. `art/logo.png` + `art/icon-128.png` masters; README embeds `art/logo.png`
5. `site/` contains the structured website content (`site.json`, `pages/`,
   `assets/`, `listing-*.md`, `listing-summary.txt`, `github-description.txt`) +
   a `site.yml` workflow calling concord's reusable build; no committed `docs/` or
   `_site/` output
6. The standard `.gitignore`, with no committed runtime artifacts (`logs/`, `run/`,
   `replay_pid*`, compiled classes)
7. The `.github/workflows/` caller stubs match concord's canonical contract —
   each stub's `uses:` ref and `permissions:` block per
   [`workflow-stubs.json`](workflow-stubs.json) (checked by `make stubs-check`);
   per-repo triggers and `with:` inputs (e.g. `curseforge-id`) may vary
8. The `Makefile` carries the canonical targets per
   [`makefile-targets.json`](makefile-targets.json) — the thirteen universal ones,
   plus `coverage` and `run-datagen` where `build.gradle` wires them (checked by
   `make makefile-check`); extra targets are a member's own business
9. `build.gradle` carries the canonical skeleton blocks in order, per the
   `mc-gradle-builds` skill. Not machine-checked — the file is read and applied,
   never synced, because `propagate/` copies whole files and every member's
   build.gradle differs
10. Datagen is either **4-of-4** on the anchors in the `mc-datagen` skill —
    entrypoint, Loom run config, make target, `verifyDatagenIdempotent` — or
    deliberately none of the four, recorded in `AGENTS.md`. A partial set is drift:
    CI gates the idempotency step on the task existing, and the task itself passes
    vacuously without the entrypoint

Future members (Husbandry, Apothecary, …) are created from this layout before any
code exists — Prosperity is the template.
