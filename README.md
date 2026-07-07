# Concord

*Modular overhauls for Minecraft's core systems.*

Concord is a collection of independent Minecraft 1.21.1 Fabric mods, each overhauling
exactly one vanilla system. Every mod is fully functional standalone; when siblings are
installed together they detect each other and light up extra integration — never a hard
dependency, never a shared jar.

| Mod | Domain | Tagline | Status |
|---|---|---|---|
| **[Tribulation](https://tribulation.rfizzle.com)** | Difficulty & scaling | "Survive what comes next." | Released |
| **[Meridian](https://meridian.rfizzle.com)** | Enchanting | "Chart your enchantments." | Released |
| **[Mercantile](https://mercantile.rfizzle.com)** | Villagers & trade | "Every villager remembers." | Released |
| **[Prosperity](https://prosperity.rfizzle.com)** | Loot & containers | "Every chest, yours to discover." | Released |

Install any. Combine all.

## What this repo is

Concord's single source of truth: the collection's vision, the suite-wide standards
every member mod conforms to, and (eventually) the collection landing site served from
`docs/`. Mod repos **link to these documents — they never copy them.**

| Document | What it governs |
|---|---|
| [`VISION.md`](VISION.md) | The collective vision, narrative, integration matrix, per-mod and cross-cutting roadmaps |
| [`API-STANDARD.md`](API-STANDARD.md) | The public-API + event pattern every mod's `api` package follows |
| [`HUD-STANDARD.md`](HUD-STANDARD.md) | The shared HUD element spec: slots, stacking, visibility, coordination |
| [`REPO-LAYOUT.md`](REPO-LAYOUT.md) | The common repository layout all mod repos mirror |
| [`AGENTS-COMMON.md`](AGENTS-COMMON.md) | The Concord-owned regions shared by every member's `AGENTS.md` (skills pointer, dev lifecycle, version scheme) — proposed to each member via the `concord-sync` PR by `propagate.yml`; edit shared agent guidance HERE |
| [`design/DESIGN-SYSTEM.md`](design/DESIGN-SYSTEM.md) | Color tokens, per-mod palettes, typography, logo formula |
| [`design/VISION-GUIDE.md`](design/VISION-GUIDE.md) · [`DESIGN-GUIDE.md`](design/DESIGN-GUIDE.md) · [`SPEC-GUIDE.md`](design/SPEC-GUIDE.md) · [`ASSETS-GUIDE.md`](design/ASSETS-GUIDE.md) | Authoring guides for the four fixed member docs under `design/` — each prescribes its document's shape, requirements, and truth direction: the player-facing vision, the brand record, the behavioral contract, and the asset manifest |
| [`docs/tokens.css`](docs/tokens.css) | The shared design tokens as consumable CSS — mod sites hot-link this |
| [`template/`](template/README.md) | The shared website template — mod repos hold only `site/` content; CI builds and deploys via [`build-site.yml`](.github/workflows/build-site.yml) |
| [`members.json`](members.json) | The member registry — per-member `status`, `conformance` (standard versions, layout migration), name/tagline/url, and `store` (Modrinth/CurseForge project id + slug); drives every site's cross-mod footer and the propagate workflow. The `store` ids are the canonical source for the publish (`modrinth-id`/`curseforge-id`) and listing-sync workflow inputs |
| [`propagate/`](propagate) | Canonical concord-owned files (currently the `.github/ISSUE_TEMPLATE/` forms) proposed verbatim to every member repo via a `concord-sync` PR by `propagate.yml` (member default branches are protected) — edit HERE, never in a mod repo |
| [`.github/workflows/`](.github/workflows) | Reusable CI for all members: `mod-ci`, `mod-release`, `mod-build-artifact`, `mod-listing-sync`, `claude-review`, `claude-spec`, `claude-mention`, `build-site` — mod repos carry only thin trigger stubs |
| [`.ai/`](.ai) | Suite-default Claude prompts (`code-reviewer`, `spec-writer`) and `review-criteria.yml` — generic, mod identity comes from each repo's AGENTS.md. Resolution: explicit `prompt-file`/`criteria-file` workflow input → repo-local `.ai/` file (whole-file override) → these defaults |
| [`.ai/skills/`](.ai/skills) | Canonical `mc-*` domain skills for all member repos. Mod repos keep vendored copies (so Claude Code, Jules, and bare clones all work) and refresh them with `make sync` — edit skills HERE, never in a mod repo. The generated [`CATALOG.md`](.ai/skills/CATALOG.md) (`make catalog`) indexes them — one row per skill, summary + when to read it — and rides the same sync, so each `AGENTS.md` points at it instead of carrying its own table |
| [`.ai/commands/`](.ai/commands) | Canonical slash commands (`/glyph`, `/sfx`, `/assess`, `/align`, `/implement`) for all member repos — vendored by the same `make sync` target, surfaced to Claude Code via a `.claude/commands` → `.ai/commands` symlink. Edit HERE, never in a mod repo |

### The CI contract

The reusable workflows assume every member repo provides: repo name == mod id ==
jar prefix (`build/libs/<mod>-<version>.jar`), and gradle tasks `build` (compile +
unit tests + jar), `jacocoTestReport` (XML at
`build/reports/jacoco/test/jacocoTestReport.xml`), `runGametest` (JUnit XML at
`build/junit-gametest.xml`), and `printVersion`. Secrets per repo:
`CLAUDE_CODE_OAUTH_TOKEN` (for the Claude workflows).
Each mod repo's stubs declare only triggers, concurrency, and permissions — the
stub bodies are documented at the top of each reusable workflow.

### Syncing skills & commands

Skills and slash commands are edited in this repo and vendored into each mod
repo. The standard Makefile target (copy into new member repos):

```make
CONCORD_DIR ?= ../concord

sync:
	@test -d $(CONCORD_DIR)/.ai/skills || { echo "concord checkout not found at $(CONCORD_DIR) (set CONCORD_DIR=...)"; exit 1; }
	rsync -a --delete $(CONCORD_DIR)/.ai/skills/ .ai/skills/
	rsync -a --delete $(CONCORD_DIR)/.ai/commands/ .ai/commands/
	@git -C $(CONCORD_DIR) rev-parse HEAD > .ai/skills/.concord-rev
	@echo "synced .ai/skills + .ai/commands from concord @ $$(git -C $(CONCORD_DIR) rev-parse --short HEAD)"
```

`.ai/skills/` and `.ai/commands/` in a mod repo are wholly owned by the sync
(`--delete` propagates removals); `.concord-rev` records provenance. Claude Code
loads them through `.claude/skills` → `.ai/skills` and `.claude/commands` →
`.ai/commands` symlinks, so the vendored skills and slash commands (like
`/glyph`) work in every member repo. A repo needing a repo-local skill or
command puts it outside the synced directory and wires the symlink accordingly.

## How mod repos reference Concord

Each mod's `AGENTS.md` carries this section (and nothing more — content lives here):

```markdown
## Suite standards (Concord)

This mod is a member of Concord, a modular collection of system overhauls. Suite-wide standards live in
the [concord repo](https://github.com/rfizzle/concord) — checked out at `../concord/`
in the local workspace. Normative for this repo:

- [API-STANDARD.md](https://github.com/rfizzle/concord/blob/master/API-STANDARD.md) — the `api` package conventions
- [HUD-STANDARD.md](https://github.com/rfizzle/concord/blob/master/HUD-STANDARD.md) — HUD slot, stacking, accessors
- [DESIGN-SYSTEM.md](https://github.com/rfizzle/concord/blob/master/design/DESIGN-SYSTEM.md) — palette, typography, logo rules
- [REPO-LAYOUT.md](https://github.com/rfizzle/concord/blob/master/REPO-LAYOUT.md) — where non-code files live
```

Conformance is **declared, not copied**: a mod states the standard version it conforms
to in one line and bumps it deliberately. The only mechanically *consumed* artifact is
`docs/tokens.css`, which the mod websites hot-link once the Concord site is on Pages.

### Shared AGENTS.md regions

Most of a member's `AGENTS.md` is mod-specific (overview, mod id, entrypoints, assets,
compat, commit-scope examples) and stays repo-owned. But a few sections are byte-identical
across every mod — the domain-skills pointer, the development lifecycle, and the version
scheme. Those live once in [`AGENTS-COMMON.md`](AGENTS-COMMON.md), delimited by
`<!-- concord:NAME:start -->` / `<!-- concord:NAME:end -->` markers, and `propagate.yml`
opens a `concord-sync` PR rewriting the matching marked region in each member's `AGENTS.md`
whenever the canonical copy changes (direct commits — issue templates and these regions
alike — go through a PR because member default branches are protected). Only the marked
regions move; prose outside them is never touched, and a repo that hasn't seeded the markers
is skipped. To opt a repo in, paste the marker pairs around the corresponding sections once
(or run `make agents-sync` locally against a sibling checkout). Edit shared agent guidance in
`AGENTS-COMMON.md`, never in a mod repo.

What stays deliberately duplicated in each mod: the ~80 lines of HUD offset logic and
the `api` package code itself. Concord rejects a shared runtime library on principle
(see `VISION.md` §8.1) — convention over dependency, in standards as in code.

## The principles (the reason this is a collection and not a modpack)

1. **Independent gates** — every mod works alone; cross-mod behavior is guarded by
   `FabricLoader.getInstance().isModLoaded(...)`.
2. **Siloed functionality** — each mod owns exactly one vanilla system; no scope bleed.
3. **Exposed public APIs** — each mod publishes a stable, read-only-by-default
   `com.rfizzle.<mod>.api` package and event surface (see `API-STANDARD.md`).
4. **Bounded by structure, not by purity** — a mod overhauls its domain as deeply as
   that domain needs, free to deepen, replace, or run a system parallel to vanilla's;
   what it must not do is add a new dimension, require another mod to load, or break
   multiplayer fairness.
