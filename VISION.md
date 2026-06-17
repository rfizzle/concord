# Concord — Collective Vision & Roadmap

*A Vanilla+ collection — the depth vanilla deserved.*

> Synthesized 2026-06-10 from source-grounded profiles of all four mod repos
> (`../meridian`, `../mercantile`, `../tribulation`, `../prosperity`); originating
> handoff archived at `design/handoffs/suite-vision-handoff.md`.
>
> The normative standards are [`HUD-STANDARD.md`](HUD-STANDARD.md),
> [`API-STANDARD.md`](API-STANDARD.md), and
> [`design/DESIGN-SYSTEM.md`](design/DESIGN-SYSTEM.md) + [`docs/tokens.css`](docs/tokens.css);
> §3.3 and §5.1 below summarize them. Where this document and a standard disagree, the
> standard wins.

---

## 1. Collective Vision Statement

**Collection tagline: *"The depth vanilla deserved."***

Concord is a collection of four independent Fabric mods for Minecraft 1.21.1 that
each take one vanilla system the game shipped shallow — enchanting, villagers, difficulty,
loot — and finish it. Not replace it: finish it. Meridian makes enchanting a system you
build toward instead of a slot machine. Mercantile makes villagers people you have a
history with instead of lever-operated vending machines. Tribulation makes the world push
back the longer and farther you survive. Prosperity makes every chest worth opening for
every player who finds it. Each mod completes a vanilla *system* rather than bolting on a
new one — none adds a dimension, a skill tree, or a wiki dependency. The discipline is
mechanical, not cosmetic: a mod is free to ship its own high-quality textures wherever
they raise the bar (icons, HUD glyphs, items, blocks — even retextured vanilla mobs), as
long as the result still reads as Minecraft. The pathway for that art is the design
system's texture pipeline (see [`design/DESIGN-SYSTEM.md`](design/DESIGN-SYSTEM.md) §8).

The unified promise the four make *together* — that none makes alone — is a **complete
risk/reward loop layered over unmodified vanilla survival**. Tribulation supplies the
risk curve (time, distance, depth). Prosperity supplies the reward curve on the same
distance axis. Meridian supplies the power progression that lets you keep pace with the
risk. Mercantile supplies the economy that converts surplus into what you're missing.
Install all four and survival Minecraft has the escalation arc of a roguelike without a
single new block of HUD clutter beyond a small, opt-out icon strip. Install any one and
it stands entirely on its own.

À-la-carte plus optional integration is the right shape because it is the only shape that
keeps each mod honest. A modpack can paper over a weak member; a suite of independently
installable mods cannot — every mod must justify itself solo, which is exactly the
Vanilla+ discipline. The integration layer (read-only public APIs, Fabric events,
`modCompileOnly` + `isModLoaded` guards, pioneered by Tribulation) means siblings *light
up* together without ever leaning on each other. A player who removes one mod loses that
mod's features and nothing else. A server admin can adopt the collection one mod at a
time. A third-party mod can integrate with any member using the identical pattern the
siblings use — the suite has no private handshakes.

The four taglines sit under the collection's one line:

| | Verb | Tagline |
|---|---|---|
| **Tribulation** | Survive | "Survive what comes next." |
| **Meridian** | Enchant | "Chart your enchantments." |
| **Mercantile** | Trade | "Every villager remembers." |
| **Prosperity** | Discover | "Every chest, yours to discover." |

---

## 2. Narrative & Naming

### The four narratives as one loop

Survive / Enchant / Trade / Discover are the four verbs of a single survival session,
in the order a player actually lives them: the world threatens you (**Tribulation**),
you grow stronger to meet it (**Meridian**), you convert surplus into what you lack
(**Mercantile**), and you push outward for more (**Prosperity**) — which raises the
threat, closing the loop. Marketing copy for any one mod should gesture at this loop in
exactly one sentence ("Part of **Concord** — a Vanilla+ collection. Install any,
combine all.") and no more; each mod's page sells that mod.

### Collection name & positioning

The collection is named **Concord** — *agreement and harmony between independent
parties* — which is the architecture thesis itself: independent gates, optional
integration, no hard dependencies. It keeps the established register (a single weighty
Latinate abstract noun, alongside Tribulation, Meridian, Mercantile, Prosperity) while
naming what the members share rather than competing with what each owns. Positioning
always pairs the name with the descriptor for searchability: "**Concord** — a Vanilla+
collection." The name is deliberately not username-derived; the maintainer's identity
spans more than these mods. Future members must keep the naming register: one weighty
abstract noun, no compounds, no "Craft"/"Plus" suffixes (see §9 candidates: Husbandry,
Apothecary, Tempest, Stratum).

### Tagline pattern

The four taglines follow a codified pattern: **a short declarative or imperative
sentence about the player's relationship to the system** — "Survive what comes
next," "Chart your enchantments," "Every chest, yours to discover," "Every
villager remembers." Mercantile's line states the reputation thesis in three
words and mirrors Prosperity's "Every chest…" construction, giving the Trade and
Discover mods a deliberate echo. A feature-description line ("villager and trade
overhaul…") serves as the supporting copy under the tagline (README masthead,
site hero) and in SEO metadata.

### Voice & tone

Shared across all marketing, docs, and in-game text:

- **Mechanically precise.** Numbers, ranges, and exact item names over adjectives. The
  existing READMEs and websites already do this — keep it. "0.5% drop chance from scaled
  mobs," not "rare drop."
- **Vanilla-deferential.** Always framed as completing vanilla, never fixing it. No
  "vanilla is broken" copy.
- **Per-mod mythic accent, used sparingly.** Each mod gets one motif register —
  Tribulation's mortality (hourglass, skulls), Meridian's astral cartography (compass
  rose, constellations), Mercantile's craft-commerce (emeralds, the bell), Prosperity's
  treasure-hoard (chalice, keys) — confined to logos, headers, and flavor lines. Body
  text stays technical.
- **In-game text is vanilla-toned.** Action bar messages and tooltips read like Mojang
  wrote them ("Villager will remember that" energy): short, dry, no exclamation points.

---

## 3. Shared Design System

### 3.1 Color: shared tokens + per-mod signature pairs

All four mods already converge on identical neutral/surface tokens — this is the design
system's foundation, canonicalized in this repo as
[`design/DESIGN-SYSTEM.md`](design/DESIGN-SYSTEM.md) + [`docs/tokens.css`](docs/tokens.css)
(hot-linked by the mod sites, never copied):

**Shared tokens (identical across all four sites today):**

| Token | Hex | Role |
|---|---|---|
| Obsidian / Ink | `#0a0a0a` | Page background |
| Dark Stone / Card | `#1a1a1a` | Cards, panels |
| Stone / Elevated | `#222222` | Hover, elevated surfaces |
| Bone | `#e8e0d4` | Primary text |
| Ash | `#a89f93` | Secondary text |
| Smoke | `#6b6359` | Tertiary / disabled text |

**Per-mod signature: a tinted dark-surface pair + two accents.** Every mod's identity is
exactly four colors layered on the shared neutrals:

| Mod | Tinted surfaces | Accent 1 | Accent 2 |
|---|---|---|---|
| Meridian | `#1a0a3e` / `#2a1a6e` (violet/cosmic) | `#7B2FBE` Arcane Purple | `#DAA520`→`#FFD700` Gold |
| Mercantile | *(neutral — none today)* | `#50C878` Emerald | `#6DDB94` Emerald Bright |
| Tribulation | `#1a0a0a` / `#2e1010` (crimson) | `#DC143C` Crimson | `#FF6B35` Ember |
| Prosperity | `#1a1408` / `#2e2510` (bronze) | `#DAA520`→`#FFD700` Gold | `#4EEAED` Diamond Cyan |

Rules for coexistence when multiple mods are installed:

1. **Accents never leave their mod's surfaces.** Meridian gold appears only in Meridian
   UI/site/HUD contexts; the shared neutrals are the only colors that cross mod
   boundaries. This is already true in practice — make it law.
2. **Gold collision (Meridian vs. Prosperity) is resolved by pairing, not by changing
   either.** Gold-with-violet reads Meridian; gold-with-cyan reads Prosperity. The
   precedent (Prosperity's logo was already regenerated away from emerald to avoid
   Mercantile) establishes the rule: *no two mods may share both accents; sharing one is
   fine if the pair is distinct.* Future mods are checked against this (§9).
3. **Mercantile should adopt a tinted surface pair** (e.g. `#0a140d` / `#10241a` deep
   emerald-blacks) to match its siblings' depth — it is currently the only mod sitting
   on pure neutrals.

### 3.2 Typography, logos, iconography

- **Type:** monospace stack everywhere on web — `"SF Mono", "Cascadia Code", "Fira Code",
  Consolas` — body in Bone on Obsidian. Headings: blocky/pixel display treatment with the
  mod's accent gradient and the existing 4s ease-in-out brightness pulse (1.0→1.15),
  already implemented identically on the Meridian and Tribulation sites. In-game: vanilla
  Minecraft font only, ever.
- **Logos:** the formula is the spec for new logos — **pixel-art, dark stone brickwork
  frame, one central glowing motif object, mod name in blocky pixel type below**.
  Meridian: arch + compass rose. Tribulation: hourglass + heart/skulls. Prosperity:
  treasure chest + key. Mercantile: a pixel-art market stall with hanging scales inside a
  circular emerald-rimmed medallion on green brickwork (`mercantile/art/logo.png`,
  described in its `design/DESIGN.md`).
- **Icons:** two sizes per mod, both pixel art — a 128×128 mod icon (`fabric.mod.json` /
  store listings) and a 16×16 HUD/UI glyph. Existing 16×16 glyphs: Tribulation skull,
  Prosperity chest; Mercantile needs one (bell or emerald), Meridian has none and needs
  none (no HUD slot, §3.3) but should keep a 16×16 for Jade/recipe-viewer contexts
  (open book).
- **Textures more broadly:** custom item/block/UI textures are first-class. The house
  style is pixel art in the design-system palette, produced through the texture pipeline
  (the `/glyph` command over `.ai/skills/mc-textures/scripts/glyph.py`, plus the `mc-textures` skill), and every
  committed texture ships its `.glyph` source beside it so it stays re-renderable. Full
  spec in [`design/DESIGN-SYSTEM.md`](design/DESIGN-SYSTEM.md) §8.

### 3.3 Shared HUD Standard (collection-wide spec)

The normative collection-level document is [`HUD-STANDARD.md`](HUD-STANDARD.md) in this
repo (mod repos link to it, never copy it); Tribulation's `TribulationHudOverlay` is the
reference implementation. The one place reality diverges from it is Mercantile's hardcoded
offset — see below.

**Visual:** semi-transparent black box (50–60% opacity, 2px rounded corners) containing a
16×16 mod glyph, optional text label in vanilla font (white, drop shadow), optional 2px
progress bar under the icon. No custom fonts, no frames, no animation beyond color tint
and Tribulation's 2s level-up lerp. **Standard element height: 20px + 2px inter-element
gap** (Tribulation's 19px icon+bar rounds into this).

**Position & stacking:** top-left anchor by default (configurable to any corner),
elements stack vertically in fixed priority order and shift up to fill gaps when a
higher-priority sibling is absent or has its HUD disabled:

| Slot | Mod | Content |
|---|---|---|
| 1 | Tribulation | Skull glyph tinted by tier + level progress bar (`Lv. 127 · T3`) |
| 2 | Mercantile | Reputation tier (`Trusted`), emerald glyph |
| 3 | Prosperity | Current distance tier (`Frontier`), chest glyph, tier-color tint |
| — | Meridian | **No slot, by design.** Meridian's info lives in the enchanting screen, Jade/WTHIT, and recipe viewers. |

This opt-out is a feature of the standard, not an omission: a mod takes a HUD slot only
if it has *persistent ambient state* the player needs while walking around. Future mods
(§9) default to no slot.

**Visibility:** hidden during F1, open screens, spectator mode, and the death screen —
all four rules already implemented in Tribulation; normative for everyone.

**Coordination mechanism — fix the current gap.** Today Mercantile hardcodes
`TRIBULATION_RESERVED_HEIGHT = 22` and offsets if `isModLoaded("tribulation")` — which is
wrong whenever the Tribulation user disables its HUD or moves its anchor. The standard's
v1 coordination rule: each HUD-bearing mod exposes two **client-safe API accessors** in
its `api` package — `isHudVisible()` and `getHudHeight()` (reflection-backed, safe
defaults when absent, same pattern as `TribulationAPI.getClientLevel()`). Each mod
computes its offset by summing the heights of *visible* higher-priority siblings.
No shared library, no shared renderer — convention over dependency (a shared HUD
*library mod* is explicitly rejected in §8).

---

## 4. Website & Distribution

### Per-mod sites (standardize the existing pattern)

All sites follow the proven shape: GitHub Pages from `docs/`, Tailwind, shared dark
tokens, `<mod>.rfizzle.com`. Standard page set:

1. **Home** — hero (full logo, tagline, version/MC badges) → feature cards → install →
   sibling-integration teaser
2. **Features** (or domain-specific deep pages: Meridian's Enchantments/Shelves,
   Mercantile's Trade Index, Tribulation's Mobs, Prosperity's Tiers)
3. **Config** — full annotated schema, generated from the real config class when possible
4. **Commands** — table with permission levels
5. **API** — the integration page (§5); every mod gets one, even where thin today
6. **Changelog + FAQ**

Tribulation's missing specced pages (changelog, mob reference, apple-touch icon) are the
template's punch list — finish them there first since it's the reference site.

**Cross-mod footer (new, all four sites):** a "Part of **Concord** — a Vanilla+
collection" strip — four 16×16 glyphs + names + one-line taglines, current mod
highlighted, linking to the sibling sites and the Concord landing page. This is the entire cross-promotion surface;
no banners, no popups.

**SEO/social conventions:** `<title>` = `Mod — Tagline`; meta description = tagline + one
mechanical sentence; OG image = full logo on Obsidian at 1200×630; canonical domain the
`<mod>.rfizzle.com` form.

### Collection landing page — yes, build it

Recommendation: **one lightweight page served from this repo's `docs/`** at
**`concord.rfizzle.com`** (matching the `<mod>.rfizzle.com` pattern) — hero with the
collection tagline, four logo cards, a visual of the integration loop
(Survive → Enchant → Trade → Discover), an "install any, combine all" explainer, and the
integration matrix in friendly form. One page, same design tokens, near-zero maintenance.
It is warranted because the suite's core differentiator — *mods that light up together* —
currently has nowhere to be explained. Pair it with a **Modrinth Collection** and
matching CurseForge listing cross-links.

### Store listing standard (CurseForge/Modrinth)

- Icon: the 128×128 pixel mod icon; gallery: full logo + 3–5 in-game screenshots
  (at least one showing a sibling integration when relevant, captioned "with
  Tribulation installed")
- Description: tagline → 5–8 feature bullets with real numbers → config/commands link →
  **"Enhanced by"** section listing siblings explicitly as *optional* ("Detects
  Tribulation and scales loot by its difficulty tier — never required")
- Required deps: Fabric API (+ CCA for Prosperity) only. Everything else under optional.
- Badges: MC 1.21.1 · Fabric · MIT, consistent README header across repos.
- **Slugs:** the bare mod names are taken by unrelated projects on both stores, so
  the suite convention is `<mod>-<domain>-overhaul` — live on CurseForge as
  `meridian-enchanting-overhaul` (1546092) and `tribulation-difficulty-overhaul`
  (1546072); CurseForge registrations for Mercantile/Prosperity pending.
  Modrinth projects exist as drafts under the same slug convention —
  `mercantile-villager-overhaul` (`Bnp3Drhe`), `meridian-enchanting-overhaul`
  (`qywREjYt`), `tribulation-difficulty-overhaul` (`8KuQhMGI`) — awaiting
  submission and review (the Meridian draft still needs its 128×128 icon
  uploaded, `meridian/art/icon-128.png`). Once public, link as
  `modrinth.com/mod/<slug>` and badge with `img.shields.io/modrinth/dt/<id>`.
  READMEs and sites link a store only once its listing is publicly live
  (GitHub Releases is always listed and is the canonical source).

---

## 5. Integration Architecture

### 5.1 The suite API standard (generalizing Tribulation)

Every mod publishes a stable integration surface under
**`com.rfizzle.<mod>.api`** — the *only* stable package; everything outside it is
internal and may change without notice. The conventions, all proven in
`TribulationAPI` / `TribulationLevelCallback`:

1. **Read-only by default.** Static accessors return values; nothing in the API mutates
   mod state. The single sanctioned mutation pattern is **provider/callback
   registration** (Tribulation's `setArmorDropChanceProvider`, Prosperity's
   `LootModifierCallback` context): the host mod calls *out* at a defined moment and the
   guest adjusts a context object. Providers that throw or return non-finite values are
   caught and fall back to defaults — error isolation is the host's job.
2. **Consumption is `modCompileOnly` + runtime guard.** Published to Modrinth maven;
   every call site wrapped in `FabricLoader.getInstance().isModLoaded("<mod>")`.
   Integration code lives in `compat/<modid>/` packages that fail gracefully.
3. **Client-safe accessors.** Anything callable from common code that needs client state
   is reflection-backed and returns a sentinel when unavailable
   (`getClientLevel() → -1`). Required for the HUD accessors in §3.3.
4. **Events are Fabric `Event` objects** (array-backed), fired server-side at state
   changes, named `<Mod><Thing>Callback`.
5. **Stability contract:** `@ApiStatus.Stable` on api classes; stable across patch
   versions; breaking changes require a major version bump and a changelog entry.
   Internal classes may be `@ApiStatus.Internal`-annotated for tooling enforcement.
6. **Server-authoritative.** All gameplay-affecting reads happen server-side; client
   accessors are for rendering only.

### 5.2 Cross-mod integration matrix

Direction notation: **Provider → Consumer** (the consumer ships the compat code; the
provider only exposes API). Value = player-facing payoff vs. cost.

| # | Provider → Consumer | Integration | Value | Provider exposes | Consumer ships |
|---|---|---|---|---|---|
| 1 | Tribulation → Prosperity | Difficulty tier adds loot luck/stack bonus on top of distance tier — harder world, richer chests | **High** | `getEffectiveLevel` / `getTier` *(exists)* | A `LootModifierCallback` listener mapping tier → `addLuck` |
| 2 | Prosperity → Tribulation | Scaled mobs' tier equipment drops more often in high distance tiers | **High** | `getDistanceTier(pos)` *(new, §5.3)* | A provider registered via `TribulationAPI.setArmor/WeaponDropChanceProvider` *(exists)* |
| 3 | Meridian → Prosperity | Loot injections add Meridian enchanted books at Outlands/Depths; loot enchanting respects Meridian's `maxLootLevel` overrides | **High** | `EnchantmentInfo` lookup in api package *(new)*; item IDs | Conditional `loot_injections` datapack + an `EnchantmentInfo`-aware enchant function |
| 4 | Meridian → Mercantile | Reputation-gated librarian exclusive trades sell Meridian salvage tomes & shelf materials — an economic road into the enchanting endgame | **High** | Item IDs only | Conditional exclusive-trades datapack entries (needs resource-condition support, §5.3) |
| 5 | Tribulation → Mercantile | Cleric exclusive trades sell Shatter Shards / Heart Fragments at high reputation — emeralds buy relief from the difficulty curve | **Med-High** | Item IDs only | Conditional exclusive-trades datapack entries |
| 6 | Tribulation → Meridian | `tribulation:soulbound` becomes rollable on Meridian's table at high Eterna and storable in libraries when both installed | **Med** | Enchantment ID + an `enchantable` tag | Tag entry + treasure-pool inclusion guard |
| 7 | Meridian → Tribulation | Tier 4–5 scaled-mob equipment enchant pool includes Meridian combat enchants (Sharpness-class swaps) via a `meridian:mob_equipment` tag | **Med** | The tag | Tag-aware equipment enchanter in the equipment scaling engine |
| 8 | Tribulation → Mercantile | Sentry Pylon scales golem count / detection with local effective level — defense keeps pace with raids Tribulation already hardens (Pillager/Vindicator/Witch/Ravager are scaled mobs) | **Med** | `getEffectiveLevel(Entity)` *(exists)* | Pylon spawn logic reads tier when present |
| 9 | Prosperity → Mercantile | Cartographer exploration maps biased toward structures in the player's next-higher loot tier | **Low** | `getDistanceTier` | Map-offer tweak — nice flavor, low payoff |
| 10 | Mercantile → Prosperity | Reputation adds loot luck | **Rejected** → §8 (silo bleed: village standing should not change wilderness chests) |
| 11 | Mercantile → Meridian | Reputation discounts enchanting costs | **Rejected** → §8 (wrong currency — enchanting spends XP, not standing) |
| 12 | Prosperity → Meridian | Distance tier biases table enchant quality | **Rejected** → §8 (enchanting is location-built via shelves, not location-found; would undercut Meridian's own progression) |

Items 1+2 form the flagship pairing — Tribulation and Prosperity already share the
distance-from-origin axis by design, and both halves are anticipated in Prosperity's
spec. Items 4+5 make Mercantile the suite's economic connective tissue, which is exactly
its silo.

### 5.3 API surface each mod must add

**Tribulation** (reference implementation — smallest gap):
- `isBossScaled(Entity)` — siblings can't currently distinguish boss-formula scaling
- `getTierThresholds()` — consumers shouldn't hardcode 50/100/150/200/250
- `getMobScalingSummary(Entity)` — what scaling a (possibly modded) mob actually received
- Client HUD accessors `isHudVisible()` / `getHudHeight()` (§3.3)

**Meridian** (most implemented surface, least formalized — promote, don't invent):
- Create `com.rfizzle.meridian.api`: read-only wrappers over `EnchantingStatRegistry`
  (`gatherStats`, `StatCollection`), `EnchantmentInfo` lookup, and promoted interfaces
  `IEnchantingStatProvider`, `BlacklistSource`, `TreasureFlagSource`, `EnchantableItem`
  (these already exist as de-facto API — moving them in is the work)
- `MeridianReloadCallback` — fired on `/meridian reload` so consumers can re-read
  `EnchantmentInfo` instead of polling
- Library query API (`getStoredPoints`, read-only) for tooltip/automation consumers

**Mercantile** (data exists in attachments; needs an API door):
- Create `com.rfizzle.mercantile.api`: `getReputation(ServerPlayer)` /
  `getReputationTier(ServerPlayer)`; `isSentryGolem(Entity)`; `isTradeLocked(Villager)`
  (wrapping the attachments so they stop being the de-facto API)
- `ReputationChangedCallback(player, oldScore, newScore)` and
  `TradeExecutedCallback(player, villager, offer)` events
- **Resource-condition support for exclusive-trades datapacks** (load entries only when
  a given mod is present) — this single feature unlocks matrix items 4 and 5
- Client HUD accessors (§3.3)

**Prosperity** (greenfield — design it right the first time):
- `com.rfizzle.prosperity.api` from day one: `LootModifierCallback` + context (specced),
  plus `getDistanceTier(ServerLevel, BlockPos)` and `getTierForPlayer(ServerPlayer)`
  static accessors, `ContainerLootedCallback(player, pos, lootTable)` event
- Client accessors: `getClientTier()`, HUD accessors (§3.3)
- `@ApiStatus.Stable` and the full §5.1 conventions applied from the first commit

### 5.4 Third-party integration story

An outside mod integrates with any member identically: add the Modrinth maven
`modCompileOnly` dep, guard with `isModLoaded`, read the api package, optionally register
a provider/callback. Document the pattern **once** on the collection landing page's API
section with one worked example (the Tribulation README's developer section is the seed),
and link it from every per-mod API page. The suite's pitch to third parties: *four mods,
one integration pattern* — learn it once, integrate with all, and any future member (§9)
works the same way. Prosperity's `LootModifierContext.customData()` CompoundTag is the
designated escape hatch for inter-mod context the APIs don't model.

---

## 6. Per-Mod Roadmap

Format per item: **pitch** — why Vanilla+ — silo note — sketch.

### Meridian

**High**

1. **Formal `api` package** — promote the existing de-facto surface (§5.3). Vanilla+:
   invisible to players. Silo: pure packaging. Sketch: move/wrap
   `EnchantingStatRegistry`, `StatCollection`, `EnchantmentInfo`, the four provider
   interfaces; add `MeridianReloadCallback`; `@ApiStatus` annotations; README dev section
   modeled on Tribulation's.
2. **Library ↔ Fabric Transfer API** — hoppers work today; make libraries first-class
   storage participants so automation mods and pipes interact predictably. Vanilla+:
   hopper-era expectations, no new blocks. Silo: enchantment storage is Meridian's.
   Sketch: expose a `Storage<ItemVariant>` view over `LibraryStorageAdapter` honoring the
   existing `ioRateLimitTicks` throttle.
3. **Repo hygiene to suite standard** — Meridian is the only repo without
   CLAUDE.md/AGENTS.md, conventional-commit policy, or split client source set
   documentation. Sketch: copy Tribulation's AGENTS.md skeleton, adapt.

**Med**

4. **Conditional sibling recipes** — enchanting-table transmutations involving Shatter
   Shards/Heart Fragments load only when Tribulation is present (matrix #6 supporting
   work). Sketch: Fabric resource conditions on `recipe/enchanting/*.json`.
5. **`meridian:mob_equipment` tag** — curated subset of the 75 enchants safe to appear on
   Tribulation-scaled mob gear (matrix #7). Sketch: data tag + doc note; Tribulation does
   the consuming.
6. **Shelf registration helper for mods** — block registration can't be datapack-driven;
   give sibling/third-party mods a one-call `registerShelf(block, statsId)` so the
   stat JSON + `IEnchantingStatProvider` wiring is trivial.

**Low**

7. **Power-function variety** (polynomial/exponential curves in `enchantmentOverrides`) —
   server-tuner quality of life.
8. **Library access events** for audit/claims mods on multiplayer.

### Mercantile

**High**

1. **Formal `api` package + events** (§5.3) — reputation/tier accessors,
   `ReputationChangedCallback`, `TradeExecutedCallback`, `isSentryGolem`. Vanilla+:
   invisible. Silo: packaging. Sketch: wrap the attachments; never expose mutation.
2. **Resource-conditioned exclusive trades** — datapack entries that load per
   `isModLoaded`. This is the keystone for matrix #4/#5 and useful to every third-party
   pack. Sketch: extend `ExclusiveTradesManager` JSON schema with a `conditions` block
   (Fabric resource conditions), plus hot-reload on `/mercantile reload`.
3. **Sibling trade packs** — ship the matrix #4 (librarian ↔ Meridian tomes/shelf mats)
   and #5 (cleric ↔ Shatter Shards/Heart Fragments) datapacks in-jar, condition-gated.
   Vanilla+: uses the vanilla professions' existing identities. Silo: trade content is
   exactly Mercantile's.

**Med**

4. **Wandering trader overhaul** — the one villager explicitly excluded from v0.1; make
   his inventory worth a look (rotating rep-blind exclusive stock, rarer goods at higher
   prices). Vanilla+: he exists to be interesting and isn't. Silo: squarely trade.
   Sketch: trade-pool datapack + spawn-announce toggle; no new entity.
5. **Villager happiness** (deferred from v0.1) — workstation proximity, bed quality, and
   recent-hit memory nudge prices ±5%. Vanilla+: extends gossip's existing spirit.
   Sketch: villager attachment + price modifier in the existing demand-pricing pipeline;
   surfaces in the info panel, no new HUD.
6. **HUD accessor compliance** (§3.3) — replace `TRIBULATION_RESERVED_HEIGHT = 22` with
   the accessor pattern; expose Mercantile's own.

**Low**

7. **Community localization scaffolding** (crowdin or PR templates) — listing reach.
8. **Troubleshooting/migration docs** ("my villager lost its profession", vanilla-village
   adoption guide).

### Tribulation

**High**

1. **API completions** (§5.3): `isBossScaled`, `getTierThresholds`,
   `getMobScalingSummary`, HUD accessors. Silo: packaging. Sketch: thin reads over
   existing state; gametest each in `APIGameTest`.
2. **Shared vs. per-player progression mode** — the suite's biggest MP-fairness gap.
   A config enum `progression: PER_PLAYER | SHARED_MAX | SHARED_AVERAGE`. Vanilla+:
   mirrors how `keepInventory`-style gamerules let servers pick their social contract.
   Sketch: `PlayerDifficultyState` grows a server-level aggregate; `getEffectiveLevel`
   resolves through the mode; HUD unchanged.

**Med**

3. **Meridian equipment-enchant consumption** (matrix #7) — at tiers 4–5, roll mob gear
   enchants from `meridian:mob_equipment` when present. Sketch: guarded pool extension in
   the equipment scaling engine.
4. **Finish the website punch list** — changelog page, per-mob reference page (rates,
   caps, abilities per tier), apple-touch icon. The reference site should be complete
   before the template propagates (§7).
5. **Jade/WTHIT tier detail** — show "Scaled: Tier 4 (boss formula)" using the new API so
   players can read the danger they're looking at.

**Low**

6. **Datapack-driven scaling profiles** — per-mob JSON overlays for pack makers.
7. **Shatter Shard consumption cap** (per-day config) — closes the grinder-stockpile
   exploit noted in the profile.

### Prosperity (build plan — greenfield to parity)

Priorities are build phases; each phase is shippable.

**High — core (Phase 1–2)**

1. **Scaffold to suite standard** — repo layout cloned from Tribulation (split source
   sets, gametest entrypoints, AGENTS.md, conventional commits), CCA dependency, config
   system with hot `/prosperity reload`.
2. **Instanced loot core** — `InstancedLootComponent` (per-player inventories, original
   loot table/seed capture, generated flags), `UseBlockCallback` interception, loot-table
   nullification, the `unpackLootTable` safety-net mixin, double-chest canonicalization,
   blacklist. This is the zero-trust proxy and the mod's entire reason to exist; gametest
   two-player instancing before anything visual.
3. **Distance tiers + structure overrides + notifications** — the five tiers, Nether
   coordinate rule, End=Depths rule, `StructureManager` override resolution, action-bar
   notification.

**High — API & integration (Phase 3)**

4. **`api` package from first principles** (§5.3) — `LootModifierCallback` + context,
   tier accessors, `ContainerLootedCallback`, `@ApiStatus.Stable`. Then the two flagship
   compats: the Tribulation luck listener (matrix #1) and the equipment-drop provider
   registration (matrix #2), both in `compat/tribulation/`.
5. **Loot injection system** — datapack-driven, wildcard expansion, conditional Meridian
   book injections (matrix #3).

**Med — client & polish (Phase 4–5)**

6. **Visual indicators + tier HUD badge** — per spec, built against the §3.3 accessor
   convention from day one (no hardcoded sibling heights). Budget rendering for the
   200-indicator target (distance culling first; occlusion later if profiling demands).
7. **Jade/WTHIT tooltips + EMI/REI/JEI loot index** — with sync throttling for the
   per-look tooltip data (profile flagged packet-spam risk).

**Low — optional systems (Phase 6)**

8. **Loot refresh, container protection, mob loot scaling** — all config-gated, all
   default states per spec (refresh off, protection off, mob scaling on).
9. **Spec future list** (loot preview, party mode, trapped-chest per-player triggering) —
   explicitly post-parity.

---

## 7. Cross-Cutting Roadmap & Sequencing

Ordered; each step's dependency noted.

1. **API Standard v1.** The conventions doc is [`API-STANDARD.md`](API-STANDARD.md).
   Complete Tribulation's API additions (it's the reference and is nearly done); then
   Meridian and Mercantile `api` packages in parallel.
   *Dependency: nothing — Tribulation's existing API is already stable enough for
   Prosperity to target.*
2. **HUD Convention v1 (with step 1).** The convention is [`HUD-STANDARD.md`](HUD-STANDARD.md).
   Tribulation + Mercantile implement the accessor pattern; Mercantile deletes its
   hardcoded offset.
   *Dependency: the api packages from step 1 (accessors live there).*
3. **Prosperity to parity (the long pole — start immediately after 1).** Phases 1–3 of
   its roadmap. *Dependency: Tribulation tier API stable (it is; the additions in step 1
   are additive). Its HUD badge (phase 4) depends on step 2.*
4. **Integration wave 1 (as the pieces land).** Matrix #1/#2 ship inside Prosperity
   phase 3; #4/#5 ship when Mercantile's conditional trades land; #3 when Meridian's
   `EnchantmentInfo` is in its api package. Each integration gets one gametest in the
   *consumer's* repo with the provider on the gametest classpath.
5. **Design system & website rollout (parallel track, low risk).** The design tokens are
   [`design/DESIGN-SYSTEM.md`](design/DESIGN-SYSTEM.md) + [`docs/tokens.css`](docs/tokens.css).
   Finish the Tribulation site punch list; propagate the template; add the cross-mod
   footer to all four; build the collection landing page; create the Modrinth Collection;
   Mercantile surface tint.
   *Dependency: none on code — start anytime; footer links want all four sites
   template-consistent first.*
6. **MP-fairness pass (after parity).** Tribulation shared-progression mode, Mercantile
   happiness, Prosperity refresh-mechanic review with real server feedback.
7. **Member 5 evaluation (last).** Only after Prosperity ships and integration wave 1
   proves the pattern end-to-end — see §9 shortlist.

The critical path is **1 → 3 → 4**: API standard, Prosperity build, integrations.
Everything else is parallelizable.

---

## 8. Explicitly Out of Scope

Rejected with reasons — protecting the thesis:

1. **A shared required library mod (`rfizzle-core`).** The single most tempting and most
   dangerous idea. The moment two mods share a runtime dependency, à-la-carte dies and
   every mod inherits every other's release cadence. Convention over code: shared
   *documents* (API standard, HUD standard, design tokens), duplicated *tiny* patterns
   (the ~80-line HUD offset logic), zero shared jars.
2. **Mercantile reputation → loot luck or enchanting discounts (matrix #10/#11).**
   Cross-silo currency bleed. Reputation is village standing; letting it buy wilderness
   loot or cheaper enchants makes one mod's grind the meta for the others' rewards and
   muddies all three progression curves. The sanctioned coupling is *trade content*
   (selling sibling items), not *stat leakage*.
3. **Prosperity distance tier → Meridian table quality (matrix #12).** Meridian's whole
   design is that enchanting power is *built* (shelves) not *found*; a location bonus
   undercuts its own progression. Wrong silo, self-defeating.
4. **New villager professions (Enchanter, Lootmonger…).** Not Vanilla+ — vanilla's
   profession roster is a fixed, recognizable cast. Sibling integration uses the
   *existing* professions' trade pools (librarian, cleric, cartographer).
5. **A currency/coin economy.** Emeralds are the vanilla currency; coins are modpack
   flavor, not Vanilla+.
6. **Skill trees / XP-spend progression UI.** Tribulation's level is ambient world state,
   not a build system. Any "spend points" mechanic is RPG creep and was the explicit
   anti-goal of the HUD-minimal design.
7. **New dimensions or custom structures for loot.** Prosperity's discipline is *vanilla
   containers in vanilla structures*. New destinations are a different (non-member) kind
   of mod.
8. **Difficulty-scaled raid mechanics inside Mercantile.** Raid/raider scaling is
   Tribulation's silo (Pillager, Vindicator, Witch, Ravager are already its scaled mobs);
   Mercantile owns the *defense* economy (Sentry Pylon). The pairing is matrix #8, with
   each side staying home.
9. **Server-wide loot refresh events.** Per-player refresh is fair by construction;
   server-wide resets create login-timing races and FOMO — the exact unfairness
   Prosperity exists to remove.
10. **A redstone/automation overhaul as a future member.** Wrong audience register for
    the suite, brutal vanilla-parity maintenance (Mojang actively iterates redstone), and
    near-zero integration surface with the existing four. Likewise **building/decoration**
    (pure content, no system, no API story) and a **Nether/End progression overhaul**
    (a dimension is a *place*, not a *system* — it would cut across every existing silo).
11. **Exploration/structures as a fifth silo.** Its natural features are already owned:
    loot-at-distance is Prosperity, maps/cartographer are Mercantile trade content,
    danger-at-distance is Tribulation. A fifth mod here would be born in three silo
    conflicts. (Transportation, the adjacent candidate, survives — barely — see §9.)

---

## 9. Additional Areas for Overhaul Evaluation

Survey of remaining vanilla systems, filtered against the four tests (Vanilla+,
independence, MP-fairness, silo cleanliness). Rejected outright: redstone, building/
decoration, Nether/End, exploration/structures, fishing-as-standalone (Prosperity's spec
already lists fishing loot as its own future consideration) — reasons in §8. Survivors,
ranked:

### 1. Husbandry — farming, food & animals. **Priority: High.**

- **Silo & boundary:** owns crops, food values, cooking, animal breeding and animal products.
  Does NOT touch: villager farmers' trades (Mercantile), crop-trampling mobs
  (Tribulation's spider ability), loot-table food (Prosperity), and no Tinkers-style
  cuisine sprawl.
- **Vanilla pain point:** food is solved at iron-farm tier (golden carrots forever),
  farming is AFK-able and flavorless, animal breeding is click-spam. The Vanilla+ thesis:
  make *what you eat and raise* matter the way Mercantile made *who you trade with*
  matter — crop quality tiers from soil/care, meals worth cooking from existing
  ingredients, animals with lineage worth breeding — all with vanilla blocks, items, and
  the composter/smoker/campfire cast that vanilla shipped and forgot.
- **Narrative & motif:** working name **Husbandry** — it is literally a vanilla
  advancement tab, the strongest possible Vanilla+ naming claim, and fits the abstract-
  noun register. Tagline candidate: *"Worth growing."* Color signature: **Wheat Amber
  (`#D9A441`) / Leaf Green (`#7CB342`)** — amber-with-leaf is distinct from
  Prosperity's gold-with-cyan and Mercantile's emerald-with-emerald under the §3.1
  pairing rule. Motif: the hoe and the sheaf in the stone-frame logo formula. No HUD slot.
- **Integration potential:** Mercantile farmer/butcher exclusive trades for quality
  produce (provider: item IDs; consumer: Mercantile's conditional trade packs — the
  exact #4/#5 pattern); Tribulation's Husk Hunger ability bites harder when food matters
  (consumer reads food-quality API); Prosperity injects rare seeds/breeds at high tiers;
  Meridian's Furrow/Bounty enchants get first-class targets. Exposes:
  `getCropQuality(pos)`, `getAnimalLineage(entity)`, a `FoodValueCallback`.
- **Verdict: High.** Big untouched silo, four natural integrations, zero overlap, deeply
  Vanilla+. The strongest "what comes after Prosperity" candidate.

### 2. Apothecary — brewing & status effects. **Priority: High (close second).**

- **Silo & boundary:** owns the brewing stand, potion recipes/durations, status-effect
  behavior, and effect application UX. Does NOT touch: enchantment effects (Meridian),
  Tribulation's shard debuffs (it *consumes* effect definitions, never redefines
  Tribulation's), witch loot (Prosperity/Tribulation).
- **Vanilla pain point:** brewing is the least-used major system — recipe-wiki dependence,
  awkward batch sizes, and most potions lose to a golden apple. Thesis: in-game recipe
  discoverability (the Meridian "clues" philosophy applied to the brewing stand),
  worthwhile niche potions from existing ingredients, and durations that respect how
  people actually play.
- **Narrative & motif:** working name **Apothecary** (alternatives: Tincture, Panacea).
  Tagline candidate: *"Every drop counts."* Color signature: **Potion Magenta
  (`#C44DCC`) / Copper (`#E77C56`)** — magenta-with-copper clears Meridian's
  purple-with-gold under the pairing rule. Motif: brewing stand silhouette in the stone
  frame. No HUD slot (effects already have vanilla HUD icons — respect them).
- **Integration potential:** Tribulation witches throw Apothecary potions at high tiers
  and shard debuffs become curable via specific brews (consumer-side, guarded);
  Mercantile cleric trades brewing ingredients by reputation; Prosperity injects rare
  reagents at distance; Meridian boundary is the one to police (potion effects vs.
  enchant effects must never share definitions).
- **Verdict: High**, second only because its silo is smaller than Husbandry's and the
  Meridian-adjacent "magic" territory needs more careful fencing.

### 3. Tempest — weather & sky. **Priority: Med.**

- **Silo & boundary:** owns weather event variety, weather gameplay consequences, and the
  day/night/moon axis. Does NOT touch: seasons (changes vanilla's core rhythm — fails
  Vanilla+; explicitly out), mob spawn *scaling* (Tribulation), crop growth rules (would
  collide with Husbandry — if both exist, Tempest exposes weather state and Husbandry
  consumes it).
- **Vanilla pain point:** weather is a screen filter. Rain means nothing, thunder means
  one mob conversion. Thesis: weather as *event* — meaningful storms, fog mornings, moon
  phases that matter — all atmospheric-consequence, no new blocks.
- **Narrative & motif:** working name **Tempest**; tagline candidate: *"Watch the sky."*
  Color signature: **Storm Blue (`#4A7FB5`) / Lightning White (`#E8F4FF`)** — blue is
  the one primary hue the suite hasn't claimed. Possible HUD slot 4 (incoming-weather
  glyph) — the first new mod that would genuinely qualify for one.
- **Integration potential:** rich as a *provider*: `getWeatherIntensity()` consumed by
  Tribulation (storm-tier mob aggression), Husbandry (crops), Prosperity (storm-only
  loot injections). Weak as a consumer.
- **Verdict: Med.** Great provider surface and clean silo, but highest un-vanilla risk in
  the shortlist — every feature needs the "could Mojang have shipped this?" test applied
  twice. Sequence after Husbandry/Apothecary.

### 4. Stratum — mining & geology. **Priority: Med-Low.**

- **Silo & boundary:** owns ore distribution texture (veins/indicators), stone variety
  behavior, and prospecting. Does NOT touch: cave *mobs* (Tribulation, which also already
  owns the depth/height axis), mineshaft/dungeon *containers* (Prosperity), mining
  *enchants* (Meridian's Prospect/Excavate stay Meridian's).
- **Vanilla pain point:** mining is strip-mine monotony; 1.18 worldgen made caves
  beautiful and prospecting still doesn't exist. Thesis: readable geology — surface
  indicators, vein structure — rewarding attention over tunnel-spam.
- **Narrative & motif:** working name **Stratum**; tagline candidate: *"Read the stone."*
  Color signature: **Deepslate Grey (`#5B6470`) / Copper Orange (`#E07A3F`)**. No HUD.
- **Integration potential:** moderate — Meridian's Prospect enchant reads Stratum veins;
  Prosperity geode-adjacent injections; Tribulation depth tiers align with strata names.
- **Verdict: Med-Low.** Real silo, but it sits wedged between three existing boundaries
  (Tribulation's height axis, Prosperity's cave loot, Meridian's mining enchants) — the
  highest scope-bleed risk of the survivors. Only attempt with the boundary contract
  written first.

### 5. Expedition — transportation. **Priority: Low (watchlist).**

- Minecarts/horses/elytra travel is a genuine dead zone, but Mojang has active minecart
  experiments in flight — building here risks vanilla collision within a version or two.
  Park it; revisit when Mojang's direction settles. (Boundary if revived: travel
  *mechanics* only; Meridian keeps mount/elytra enchants, Mercantile keeps anything
  villager-drawn.)

### The shortlist

**After Prosperity ships: Husbandry → Apothecary → Tempest**, with Stratum held until
its three-way boundary contract is drafted and Expedition on the Mojang-watchlist. Each
follows the same admission path: DESIGN.md + SPEC.md first (the Prosperity model proved
this works), API designed from day one, no HUD slot unless it carries persistent ambient
state, palette cleared against the §3.1 pairing rule, name in the register.
