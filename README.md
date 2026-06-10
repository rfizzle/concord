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

## How mod repos reference Concord

Each mod's `AGENTS.md` carries this section (and nothing more — content lives here):

```markdown
## Suite standards (Concord)

This mod is a member of Concord, the Vanilla+ collection. Suite-wide standards live in
the [concord repo](https://github.com/rfizzle/concord) — checked out at `../concord/`
in the local workspace. Normative for this repo:

- [API-STANDARD.md](https://github.com/rfizzle/concord/blob/main/API-STANDARD.md) — the `api` package conventions (conforms to v1)
- [HUD-STANDARD.md](https://github.com/rfizzle/concord/blob/main/HUD-STANDARD.md) — HUD slot, stacking, accessors (conforms to v1)
- [DESIGN-SYSTEM.md](https://github.com/rfizzle/concord/blob/main/design/DESIGN-SYSTEM.md) — palette, typography, logo rules
- [REPO-LAYOUT.md](https://github.com/rfizzle/concord/blob/main/REPO-LAYOUT.md) — where non-code files live
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
