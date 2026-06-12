# Concord

*A Vanilla+ collection — the depth vanilla deserved.*

Concord is a collection of independent Minecraft 1.21.1 Fabric mods, each overhauling
exactly one vanilla system. Every mod is fully functional standalone; when siblings are
installed together they detect each other and light up extra integration — never a hard
dependency, never a shared jar.

| Mod | Domain | Tagline | Status |
|---|---|---|---|
| **[Tribulation](https://tribulation.rfizzle.com)** | Difficulty & scaling | "Survive what comes next." | Released |
| **[Meridian](https://meridian.rfizzle.com)** | Enchanting | "Chart your enchantments." | Released |
| **[Mercantile](https://mercantile.rfizzle.com)** | Villagers & trade | "Every villager remembers." | Released |
| **Prosperity** | Loot & containers | "Every chest, yours to discover." | In design (spec complete) |

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
| [`design/DESIGN-SYSTEM.md`](design/DESIGN-SYSTEM.md) | Color tokens, per-mod palettes, typography, logo formula |
| [`docs/tokens.css`](docs/tokens.css) | The shared design tokens as consumable CSS — mod sites hot-link this |
| [`template/`](template/README.md) | The shared website template — mod repos hold only `site/` content; CI builds and deploys via [`build-site.yml`](.github/workflows/build-site.yml) |
| [`members.json`](members.json) | The member registry — per-member `status` and `conformance` (standard versions, layout migration) plus name/tagline/url; drives every site's cross-mod footer and the propagate workflow |
| [`propagate/`](propagate) | Canonical concord-owned files (currently the `.github/ISSUE_TEMPLATE/` forms) synced verbatim into every member repo by `propagate.yml` — edit HERE, never in a mod repo |
| [`.github/workflows/`](.github/workflows) | Reusable CI for all members: `mod-ci`, `mod-release`, `mod-build-artifact`, `claude-review`, `claude-spec`, `claude-mention`, `build-site` — mod repos carry only thin trigger stubs |
| [`.ai/`](.ai) | Suite-default Claude prompts (`code-reviewer`, `spec-writer`) and `review-criteria.yml` — generic, mod identity comes from each repo's AGENTS.md. Resolution: explicit `prompt-file`/`criteria-file` workflow input → repo-local `.ai/` file (whole-file override) → these defaults |
| [`.ai/skills/`](.ai/skills) | Canonical `mc-*` domain skills for all member repos. Mod repos keep vendored copies (so Claude Code, Jules, and bare clones all work) and refresh them with `make sync-skills` — edit skills HERE, never in a mod repo |

### The CI contract

The reusable workflows assume every member repo provides: repo name == mod id ==
jar prefix (`build/libs/<mod>-<version>.jar`), and gradle tasks `build` (compile +
unit tests + jar), `jacocoTestReport` (XML at
`build/reports/jacoco/test/jacocoTestReport.xml`), `runGametest` (JUnit XML at
`build/junit-gametest.xml`), and `printVersion`. Secrets per repo:
`CODECOV_TOKEN` (optional), `CLAUDE_CODE_OAUTH_TOKEN` (for the Claude workflows).
Each mod repo's stubs declare only triggers, concurrency, and permissions — the
stub bodies are documented at the top of each reusable workflow.

### Syncing skills

Skills are edited in this repo and vendored into each mod repo. The standard
Makefile target (copy into new member repos):

```make
CONCORD_DIR ?= ../concord

sync-skills:
	@test -d $(CONCORD_DIR)/.ai/skills || { echo "concord checkout not found at $(CONCORD_DIR) (set CONCORD_DIR=...)"; exit 1; }
	rsync -a --delete $(CONCORD_DIR)/.ai/skills/ .ai/skills/
	@git -C $(CONCORD_DIR) rev-parse HEAD > .ai/skills/.concord-rev
	@echo "synced .ai/skills from concord @ $$(git -C $(CONCORD_DIR) rev-parse --short HEAD)"
```

`.ai/skills/` in a mod repo is wholly owned by the sync (`--delete` propagates
removals); `.concord-rev` records provenance. A repo needing a repo-local
skill puts it outside the synced directory and wires `.claude/skills`
accordingly.

## How mod repos reference Concord

Each mod's `AGENTS.md` carries this section (and nothing more — content lives here):

```markdown
## Suite standards (Concord)

This mod is a member of Concord, the Vanilla+ collection. Suite-wide standards live in
the [concord repo](https://github.com/rfizzle/concord) — checked out at `../concord/`
in the local workspace. Normative for this repo:

- [API-STANDARD.md](https://github.com/rfizzle/concord/blob/master/API-STANDARD.md) — the `api` package conventions (conforms to v1)
- [HUD-STANDARD.md](https://github.com/rfizzle/concord/blob/master/HUD-STANDARD.md) — HUD slot, stacking, accessors (conforms to v1)
- [DESIGN-SYSTEM.md](https://github.com/rfizzle/concord/blob/master/design/DESIGN-SYSTEM.md) — palette, typography, logo rules
- [REPO-LAYOUT.md](https://github.com/rfizzle/concord/blob/master/REPO-LAYOUT.md) — where non-code files live
```

Conformance is **declared, not copied**: a mod states the standard version it conforms
to in one line and bumps it deliberately. The only mechanically *consumed* artifact is
`docs/tokens.css`, which the mod websites hot-link once the Concord site is on Pages.

What stays deliberately duplicated in each mod: the ~80 lines of HUD offset logic and
the `api` package code itself. Concord rejects a shared runtime library on principle
(see `VISION.md` §8.1) — convention over dependency, in standards as in code.

## The principles (the reason this is a collection and not a modpack)

1. **Independent gates** — every mod works alone; cross-mod behavior is guarded by
   `FabricLoader.getInstance().isModLoaded(...)`.
2. **Siloed functionality** — each mod owns exactly one vanilla system; no scope bleed.
3. **Exposed public APIs** — each mod publishes a stable, read-only-by-default
   `com.rfizzle.<mod>.api` package and event surface (see `API-STANDARD.md`).
4. **Vanilla+ throughout** — everything could plausibly have shipped in vanilla;
   server-friendly and multiplayer-fair.
