# Concord — Collective Vision & Roadmap

*Modular overhauls for Minecraft's core systems.*

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

Concord is a collection of five independent Fabric mods for Minecraft 1.21.1 that
each take one vanilla system the game shipped shallow — enchanting, villagers, difficulty,
loot, vitality — and overhaul it. Meridian makes enchanting a system you
build toward instead of a slot machine. Mercantile makes villagers people you have a
history with instead of lever-operated vending machines. Tribulation makes the world push
back the longer and farther you survive. Prosperity makes every chest worth opening for
every player who finds it. Respite makes the night a lived part of survival instead of a
skip button. Each mod owns a single domain and goes as deep as that domain
needs — deepening, replacing, or running a system in parallel with vanilla's — but it stays
in its lane: one domain per mod, no new dimension, and nothing another member must load.
The discipline is structural, not cosmetic: a mod is free to ship its own high-quality
textures wherever they raise the bar (icons, HUD glyphs, items, blocks — even retextured
vanilla mobs), as long as the result stays visually coherent with Minecraft. The pathway for that art is the design
system's texture pipeline (see [`design/DESIGN-SYSTEM.md`](design/DESIGN-SYSTEM.md) §8).

The unified promise the members make *together* — that none makes alone — is a **complete
risk/reward loop layered over unmodified vanilla survival**. Tribulation supplies the
risk curve (time, distance, depth). Prosperity supplies the reward curve on the same
distance axis. Meridian supplies the power progression that lets you keep pace with the
risk. Mercantile supplies the economy that converts surplus into what you're missing.
Respite supplies the recovery beat — the night that restores you between runs.
Install all five and survival Minecraft has the escalation arc of a roguelike without a
single new block of HUD clutter beyond a small, opt-out icon strip. Install any one and
it stands entirely on its own.

À-la-carte plus optional integration is the right shape because it is the only shape that
keeps each mod honest. A modpack can paper over a weak member; a suite of independently
installable mods cannot — every mod must justify itself solo, which is exactly the
modular discipline. The integration layer (read-only public APIs, Fabric events,
`modCompileOnly` + `isModLoaded` guards, pioneered by Tribulation) means siblings *light
up* together without ever leaning on each other. A player who removes one mod loses that
mod's features and nothing else. A server admin can adopt the collection one mod at a
time. A third-party mod can integrate with any member using the identical pattern the
siblings use — the suite has no private handshakes.

The member taglines sit under the collection's one line:

| | Verb | Tagline |
|---|---|---|
| **Tribulation** | Survive | "Survive what comes next." |
| **Meridian** | Enchant | "Chart your enchantments." |
| **Mercantile** | Trade | "Every villager remembers." |
| **Prosperity** | Discover | "Every chest, yours to discover." |
| **Respite** | Rest | "Make the night count." |

---

## 2. Narrative & Naming

### The five narratives as one loop

Survive / Enchant / Trade / Discover / Rest are the five verbs of a single survival
session, in the order a player actually lives them: the world threatens you
(**Tribulation**), you grow stronger to meet it (**Meridian**), you convert surplus into
what you lack (**Mercantile**), you push outward for more (**Prosperity**) — which raises
the threat, closing the loop — and you rest to run it again (**Respite**), the night that
turns one day's loop into the next. Marketing copy for any one mod should gesture at this loop in
exactly one sentence ("Part of **Concord** — a modular collection of system overhauls.
Install any, combine all.") and no more; each mod's page sells that mod.

### Collection name & positioning

The collection is named **Concord** — *agreement and harmony between independent
parties* — which is the architecture thesis itself: independent gates, optional
integration, no hard dependencies. It keeps the established register (a single weighty
Latinate abstract noun, alongside Tribulation, Meridian, Mercantile, Prosperity,
Respite) while
naming what the members share rather than competing with what each owns. Positioning
always pairs the name with the descriptor for searchability: "**Concord** — a modular
collection of system overhauls." The name is deliberately not username-derived; the maintainer's identity
spans more than these mods. Future members must keep the naming register: one weighty
abstract noun, no compounds, no "Craft"/"Plus" suffixes (see §9 candidates: Husbandry,
Apothecary, Tempest, Stratum).

### Tagline pattern

The taglines follow a codified pattern: **a short declarative or imperative
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

All member mods converge on identical neutral/surface tokens — this is the design
system's foundation, canonicalized in this repo as
[`design/DESIGN-SYSTEM.md`](design/DESIGN-SYSTEM.md) + [`docs/tokens.css`](docs/tokens.css)
(hot-linked by the mod sites, never copied):

**Shared tokens (identical across all member sites):**

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
| Respite | `#141a3d` / `#232e66` (midnight indigo) | `#7C8EE8` Moonlight Indigo | `#F2C14E` Candleglow |

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
| — | Respite | **No slot, by design.** Weariness rides the vanilla status-effect icons; time is read from the sky, the Chronometer block, and `/respite status`. |

This opt-out is a feature of the standard, not an omission: a mod takes a HUD slot only
if it has *persistent ambient state* the player needs while walking around. Future mods
(§9) default to no slot.

**Visibility:** hidden during F1, open screens, spectator mode, and the death screen —
all four rules already implemented in Tribulation; normative for everyone.

**Coordination mechanism — fix the current gap.** Today Mercantile hardcodes
`TRIBULATION_RESERVED_HEIGHT = 22` and offsets if `isModLoaded("tribulation")` — which is
wrong whenever the Tribulation user disables its HUD or moves its anchor. The standard's
coordination rule: each HUD-bearing mod exposes two **client-safe API accessors** in
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

**Cross-mod footer (all member sites):** a "Part of **Concord** — a modular
collection of system overhauls" strip — member 16×16 glyphs + names + one-line taglines, current mod
highlighted, linking to the sibling sites and the Concord landing page. This is the entire cross-promotion surface;
no banners, no popups.

**SEO/social conventions:** `<title>` = `Mod — Tagline`; meta description = tagline + one
mechanical sentence; OG image = full logo on Obsidian at 1200×630; canonical domain the
`<mod>.rfizzle.com` form.

### Collection landing page — yes, build it

Recommendation: **one lightweight page served from this repo's `docs/`** at
**`concord.rfizzle.com`** (matching the `<mod>.rfizzle.com` pattern) — hero with the
collection tagline, member logo cards, a visual of the integration loop
(Survive → Enchant → Trade → Discover → Rest), an "install any, combine all" explainer, and the
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
| 3 | Meridian → Prosperity | Static form: loot injections add Meridian enchanted books at Outlands/Depths. Dynamic form: distance tier maps to enchant power and rolls Meridian-consistent enchants on found loot | **High** | `EnchantmentInfo` lookup *(exists)*; a stable loot-roll function + actual `maxLootLevel` enforcement on loot *(new — the field is readable today but Meridian does not clamp loot to it)*; item IDs | Conditional `loot_injections` datapack (static, ships today) + a distance→power enchant listener (dynamic) |
| 4 | Meridian → Mercantile | Reputation-gated librarian exclusive trades sell Meridian salvage tomes & shelf materials — an economic road into the enchanting endgame | **High** | Item IDs only | Conditional exclusive-trades datapack entries (needs resource-condition support, §5.3) |
| 5 | Tribulation → Mercantile | Cleric exclusive trades sell Shatter Shards / Heart Fragments at high reputation — emeralds buy relief from the difficulty curve | **Med-High** | Item IDs only | Conditional exclusive-trades datapack entries |
| 6 | Meridian → Tribulation | Keep-on-death convergence: `meridian:tether` and `tribulation:soulbound` are the same mechanic, so when both load they collapse to one acquirable enchant (Tether) via the shared `#c:soulbound` tag, with Tribulation's soul-inventory as the single behavior owner | **Med** | `meridian:tether` + the `#c:soulbound` convention tag | Soul-inventory reads the tag, suppresses its own enchant when Meridian is present, shared exclusive-set; Meridian's handler stands down |
| 7 | Meridian → Tribulation | Tier 4–5 scaled-mob equipment enchant pool includes Meridian combat enchants (Sharpness-class swaps) via a `meridian:mob_equipment` tag | **Med** | The `meridian:mob_equipment` tag *(new — no such tag exists yet)* | A tag-aware enchanter hook in the equipment scaling engine *(new engine work — gear enchanting is config-driven today, not tag/loot-driven)* |
| 8 | Tribulation → Mercantile | Sentry Pylon scales golem count / detection with local effective level — defense keeps pace with raids Tribulation already hardens (Pillager/Vindicator/Witch/Ravager are scaled mobs) | **Med** | `getEffectiveLevel(Entity)` *(exists)* | Pylon spawn logic reads tier when present |
| 9 | Prosperity → Mercantile | Cartographer exploration maps biased toward structures in the player's next-higher loot tier | **Low** | `getDistanceTier` | Map-offer tweak — nice flavor, low payoff |
| 10 | Mercantile → Prosperity | Reputation adds loot luck | **Rejected** → §8 (silo bleed: village standing should not change wilderness chests) |
| 11 | Mercantile → Meridian | Reputation discounts enchanting costs | **Rejected** → §8 (wrong currency — enchanting spends XP, not standing) |
| 12 | Prosperity → Meridian | Distance tier biases table enchant quality | **Rejected** → §8 (enchanting is location-built via shelves, not location-found; would undercut Meridian's own progression) |
| 13 | Tribulation → Respite | Tribulation's mob scaling reaches Respite's altitude/new-moon phantoms automatically — they are plain vanilla phantoms, so a hardened world's peaks are real fights | **Med** | `getEffectiveLevel` scaling *(exists — applies to the vanilla phantom type unchanged)* | Nothing — zero-code integration |
| 14 | Respite → Mercantile | Reputation-gated farmer/wandering-trader exclusive trades sell cocoa and Caffeinated Brews — emeralds buy safe all-nighters | **Med** | Item IDs only (`respite:caffeinated_brew`, `respite:unsteeped_brew`) | Conditional exclusive-trades datapack entries |
| 15 | Respite → Prosperity | Chronometers and Caffeinated Brews turn up in far-tier chests — the deep wilderness keeps its own time | **Low-Med** | Item IDs only | Conditional `loot_injections` datapack entries |

Items 1+2 form the flagship pairing — both Tribulation and Prosperity scale with
remoteness, though they anchor it differently: Tribulation measures distance from **world
spawn** (one axis among playtime and depth), Prosperity from **world origin (0,0)**.
Keeping the risk and reward curves aligned despite the two anchors is a deliberate balance
point; both halves are anticipated in Prosperity's spec. Items 4+5 make Mercantile the
suite's economic connective tissue, which is exactly its silo.

**Duplicate-mechanic convergence (the pattern behind #6).** When two members ship
near-identical mechanics — as Meridian's Tether and Tribulation's Soulbound both keep an
item through death — they must not delete or hard-reference each other. The resolution is
convention, not dependency: each mod contributes *its own* enchant to a shared `c:` tag
(`#c:soulbound`), each triggers its behavior off the **tag** rather than a specific id, and
when both are installed one mod stands down so a single owner runs (here Tribulation's richer
soul-inventory wins and Tether is the lone acquirable enchant). Remove either mod and the
other still works off its own copy. This is the canonical way to resolve any overlap between
members, present or future.

### 5.3 API surface per mod — shipped and remaining

Marked *(exists)* / *(new)* against the current code. Three of the five `api` packages are
built (Respite's is specced, pre-implementation); what remains is a small set of targeted
additions the integrations need.

**Tribulation** (reference implementation — full surface shipped):
- `getLevel`, `getTier`, `getEffectiveLevel(Entity)`, `getScaledTier`,
  `wasScaledByTribulation`, `isBossScaled`, `getTierThresholds`, `getMobScalingSummary`,
  the `setArmorDropChanceProvider` / `setWeaponDropChanceProvider` hooks, the
  `TribulationLevelCallback` event, and HUD accessors `isHudVisible()` / `getHudHeight()`
  — all *(exist)*
- Remaining: `getEffectiveLevel` takes an `Entity`; there is no position-only level
  accessor, so the Sentry Pylon compat (matrix #8) derives level from the nearest player
  *(new, only if a `getEffectiveLevel(ServerLevel, BlockPos)` is later wanted)*

**Meridian** (`api` package shipped):
- `com.rfizzle.meridian.api`: `MeridianAPI` (`gatherStats`, `getEnchantmentInfo`,
  `getAllEnchantmentInfo`, `getStoredPoints`), `StatCollection`, `EnchantmentInfo`, the four
  provider interfaces (`IEnchantingStatProvider`, `BlacklistSource`, `TreasureFlagSource`,
  `EnchantableItem`), and `MeridianReloadCallback` — all *(exist)*. `EnchantmentInfo` carries
  level/loot caps and power functions but **not** a treasure flag or weight (those come from
  the enchant's own data/tags)
- Remaining *(new)*: `maxLootLevel` is exposed but **not enforced** during loot generation
  (Meridian only post-filters disabled enchants), and there is no public "roll an
  appropriate enchant at power N" function. Matrix #3's dynamic form needs both — enforce the
  loot cap, and promote `RealEnchantmentHelper.selectEnchantment` into a stable call

**Mercantile** (`api` package shipped):
- `com.rfizzle.mercantile.api`: `getReputation(ServerPlayer)`,
  `getReputationTier(ServerPlayer)`, `isSentryGolem(Entity)`, `isProfessionLocked(Villager)`,
  `isTradeLocked(Villager, MerchantOffer)` (per-offer — there is no single-arg form), the
  `ReputationChangedCallback` / `TradeExecutedCallback` events, and HUD accessors — all
  *(exist)*
- Remaining *(new)*: **resource-condition support for exclusive-trades datapacks** — load
  entries only when a given mod is present; the single feature that lets matrix #4/#5 ship
  in-jar instead of leaning on the unknown-item skip

**Prosperity** (`api` package partially shipped):
- `com.rfizzle.prosperity.api` ships `LootModifierCallback` + `LootModifierContext` and the
  HUD accessors *(exist)*. The key remaining gap is public tier access:
  `getDistanceTier(ServerLevel, BlockPos)` and `getTierForPlayer(ServerPlayer)` *(new)* —
  the reward-axis counterpart to `TribulationAPI.getTier`. Tier resolution currently lives
  in internal `LootScaling`/`ProsperityConfig`, so siblings cannot read it; this is the
  highest-leverage addition in the integration set (unblocks the dynamic form of matrix #3).
- A `ContainerLootedCallback(player, pos, lootTable)` event *(new)* would round out the
  surface — today only a client-sync packet exists, not a public event.
- The full §5.1 conventions applied from the first commit (a local `@Stable` marker, not
  a shared `@ApiStatus.Stable`, per the no-shared-jar rule)

**Respite** (specced, pre-implementation — its `design/SPEC.md` §Public API):
- `com.rfizzle.respite.api`: `getTimeLapseRate(ServerLevel)`, `isTimeLapseActive(ServerLevel)`,
  `getTicksSinceRest(ServerPlayer)`, `isWeary(ServerPlayer)`, `getChronometerSignal(Level)`,
  plus the `RespiteTimeLapseCallback` and `RespiteRestCallback` events — all *(new, land
  with implementation)*. No HUD accessors, by design (no slot). Respite is a provider in
  every current integration (matrix #13–#15), so it ships no compat code of its own.

### 5.4 Third-party integration story

An outside mod integrates with any member identically: add the Modrinth maven
`modCompileOnly` dep, guard with `isModLoaded`, read the api package, optionally register
a provider/callback. Document the pattern **once** on the collection landing page's API
section with one worked example (the Tribulation README's developer section is the seed),
and link it from every per-mod API page. The suite's pitch to third parties: *five mods,
one integration pattern* — learn it once, integrate with all, and any future member (§9)
works the same way. Prosperity's `LootModifierContext.customData()` CompoundTag is the
designated escape hatch for inter-mod context the APIs don't model.

---

## 6. Per-Mod Roadmap

Format per item: **pitch** — why it fits — silo note — sketch.

### Meridian

**High**

1. **Loot-cap enforcement + stable enchant-roll API** — the `api` package is in place; the
   remaining gap is enforcing `maxLootLevel` during loot generation and exposing a stable
   "roll an appropriate enchant at power N" call (the keystone for matrix #3's dynamic form).
   Fit: invisible to players. Silo: enchanting math is Meridian's. Sketch: a loot mixin that
   clamps to `getMaxLootLevel()` + `enabled()`, plus promoting
   `RealEnchantmentHelper.selectEnchantment` into `MeridianAPI`.
2. **Library ↔ Fabric Transfer API** — hoppers work today; make libraries first-class
   storage participants so automation mods and pipes interact predictably. Fit:
   hopper-era expectations, no new blocks. Silo: enchantment storage is Meridian's.
   Sketch: expose a `Storage<ItemVariant>` view over `LibraryStorageAdapter` honoring the
   existing `ioRateLimitTicks` throttle.

**Med**

3. **Conditional sibling recipes** — enchanting-table transmutations involving Shatter
   Shards/Heart Fragments load only when Tribulation is present (matrix #6 supporting
   work). Sketch: Fabric resource conditions on `recipe/enchanting/*.json`.
4. **`meridian:mob_equipment` tag** — curated subset of the 75 enchants safe to appear on
   Tribulation-scaled mob gear (matrix #7). Sketch: data tag + doc note; Tribulation does
   the consuming.
5. **Shelf registration helper for mods** — block registration can't be datapack-driven;
   give sibling/third-party mods a one-call `registerShelf(block, statsId)` so the
   stat JSON + `IEnchantingStatProvider` wiring is trivial.

**Low**

6. **Power-function variety** (polynomial/exponential curves in `enchantmentOverrides`) —
   server-tuner quality of life.
7. **Library access events** for audit/claims mods on multiplayer.

### Mercantile

**High**

1. **Resource-conditioned exclusive trades** — the `api` package and its
   `ReputationChangedCallback` / `TradeExecutedCallback` events are in place; the remaining
   keystone is datapack entries that load per `isModLoaded`. Unlocks matrix #4/#5 and is
   useful to every third-party pack. Sketch: extend `ExclusiveTradesManager` JSON schema with
   a `conditions` block (Fabric resource conditions), plus hot-reload on `/mercantile reload`.
2. **Sibling trade packs** — ship the matrix #4 (librarian ↔ Meridian tomes/shelf mats)
   and #5 (cleric ↔ Shatter Shards/Heart Fragments) datapacks in-jar, condition-gated.
   Fit: uses the vanilla professions' existing identities. Silo: trade content is
   exactly Mercantile's.

**Med**

3. **Wandering trader overhaul** — the one villager explicitly excluded from v0.1; make
   his inventory worth a look (rotating rep-blind exclusive stock, rarer goods at higher
   prices). Fit: he exists to be interesting and isn't. Silo: squarely trade.
   Sketch: trade-pool datapack + spawn-announce toggle; no new entity.
4. **Villager happiness** (deferred from v0.1) — workstation proximity, bed quality, and
   recent-hit memory nudge prices ±5%. Fit: extends gossip's existing spirit.
   Sketch: villager attachment + price modifier in the existing demand-pricing pipeline;
   surfaces in the info panel, no new HUD.
5. **HUD accessor adoption** (§3.3) — the `isHudVisible()` / `getHudHeight()` accessors
   exist; adopt the accessor pattern for cross-mod stacking in place of any hardcoded
   sibling offset.

**Low**

6. **Community localization scaffolding** (crowdin or PR templates) — listing reach.
7. **Troubleshooting/migration docs** ("my villager lost its profession", vanilla-village
   adoption guide).

### Tribulation

**High**

1. **Shared vs. per-player progression mode** — the suite's biggest MP-fairness gap.
   A config enum `progression: PER_PLAYER | SHARED_MAX | SHARED_AVERAGE`. Fit:
   mirrors how `keepInventory`-style gamerules let servers pick their social contract.
   Sketch: `PlayerDifficultyState` grows a server-level aggregate; `getEffectiveLevel`
   resolves through the mode; HUD unchanged.

**Med**

2. **Meridian equipment-enchant consumption** (matrix #7) — at tiers 4–5, roll mob gear
   enchants from `meridian:mob_equipment` when present. Sketch: guarded pool extension in
   the equipment scaling engine.
3. **Finish the website punch list** — changelog page, per-mob reference page (rates,
   caps, abilities per tier), apple-touch icon. The reference site should be complete
   before the template propagates (§7).
4. **Jade/WTHIT tier detail** — show "Scaled: Tier 4 (boss formula)" using the API so
   players can read the danger they're looking at.

**Low**

5. **Datapack-driven scaling profiles** — per-mob JSON overlays for pack makers.
6. **Shatter Shard consumption cap** (per-day config) — closes the grinder-stockpile
   exploit noted in the profile.

### Prosperity

The instanced-loot core (the zero-trust per-player proxy), distance tiers + structure
overrides, the loot-injection system, the `api` package (`LootModifierCallback` +
`LootModifierContext` + HUD accessors), the tier HUD badge + visual indicators, the
Jade/WTHIT + EMI/REI/JEI loot index, and the config-gated loot-refresh /
container-protection / mob-loot-scaling systems are in place. Remaining work:

**High — integration surface**

1. **Public tier accessors** (§5.3) — `getDistanceTier(ServerLevel, BlockPos)` /
   `getTierForPlayer(ServerPlayer)` and a `ContainerLootedCallback` event, the reward-axis
   counterpart to `TribulationAPI.getTier`.
2. **Flagship compats** in `compat/tribulation/` — the luck listener (matrix #1) and the
   equipment-drop provider registration (matrix #2).
3. **Conditional Meridian book injections** (matrix #3) — a mod-presence gate on injections
   plus the authored book pack; the dynamic, distance-rolled form follows once Meridian
   ships loot-cap enforcement + a roll API.

**Med — polish**

4. **Indicator render budget** — distance culling / occlusion for the 200-indicator target,
   if profiling demands.
5. **Loot-refresh + protection defaults** — revisit the config-gated defaults with real
   server feedback (ties into the §7 MP-fairness pass).

**Low**

6. **Spec future list** (loot preview, party mode, trapped-chest per-player triggering) —
   explicitly post-parity.

---

## 7. Cross-Cutting Roadmap & Sequencing

Ordered; each step's dependency noted.

1. **API Standard.** The conventions doc is [`API-STANDARD.md`](API-STANDARD.md).
   The Tribulation, Meridian, and Mercantile `api` packages are in place; the remaining
   additions are Prosperity's public tier accessors, Meridian's loot-cap enforcement +
   enchant-roll call, and Mercantile's exclusive-trades resource conditions.
   *Dependency: nothing — the stable surfaces already exist for Prosperity to target.*
2. **HUD Convention (with step 1).** The convention is [`HUD-STANDARD.md`](HUD-STANDARD.md).
   The HUD accessors live in each `api` package; Mercantile adopts the accessor pattern for
   cross-mod stacking in place of any hardcoded offset.
   *Dependency: the HUD accessors (present in each api package).*
3. **Prosperity to parity (the long pole — start immediately after 1).** Phases 1–3 of
   its roadmap. *Dependency: Tribulation tier API stable (it is; the additions in step 1
   are additive). Its HUD badge (phase 4) depends on step 2.*
4. **Integration wave 1 (as the pieces land).** Matrix #1/#2 ship inside Prosperity
   phase 3; #4/#5 ship today via the unknown-item skip and harden when Mercantile's
   conditional trades land; #3's static book-injection ships now (Meridian's
   `EnchantmentInfo` is already exposed), its dynamic form lands with Meridian's loot-cap
   enforcement + roll API and Prosperity's tier accessors. Each integration gets one
   gametest in the *consumer's* repo with the provider on the gametest classpath.
5. **Design system & website rollout (parallel track, low risk).** The design tokens are
   [`design/DESIGN-SYSTEM.md`](design/DESIGN-SYSTEM.md) + [`docs/tokens.css`](docs/tokens.css).
   Finish the Tribulation site punch list; propagate the template; add the cross-mod
   footer to every member site; build the collection landing page; create the Modrinth
   Collection; Mercantile surface tint.
   *Dependency: none on code — start anytime; footer links want the member sites
   template-consistent first.*
6. **MP-fairness pass (after parity).** Tribulation shared-progression mode, Mercantile
   happiness, Prosperity refresh-mechanic review with real server feedback.
7. **Next-member evaluation (last).** Only after integration wave 1 proves the pattern
   end-to-end — see §9 shortlist.

The critical path is **1 → 3 → 4**: API standard, Prosperity build, integrations.
Everything else is parallelizable.

---

## 8. Explicitly Out of Scope

Rejected with reasons — protecting the modular thesis. These are **structural** lines —
they keep mods à-la-carte, single-domain, and multiplayer-fair — not purity lines: a mod
may deepen, replace, or run a system parallel to vanilla's *within its own domain*. A few
former purity bans are now conventions, marked *(convention)*. What stays out:

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
4. **New villager professions (Enchanter, Lootmonger…).** *(Convention.)* Mercantile keeps
   the vanilla profession roster so sibling trade integration keys off a stable,
   recognizable cast — sibling content uses the *existing* professions' trade pools
   (librarian, cleric, cartographer). Not forbidden; just unnecessary.
5. **A new currency/coin economy.** *(Convention.)* The suite standardizes on emeralds so
   cross-mod value stays coherent. Not forbidden; just unnecessary.
6. **A heavy, always-on progression UI (skill trees, XP-spend screens).** *(Convention.)*
   Not banned as a mechanic, but it collides with the HUD-minimal design — a small,
   opt-out icon strip (see `design/DESIGN-SYSTEM.md`). Tribulation's level stays ambient
   world state by choice.
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
    near-zero integration surface with the existing members. Likewise **building/decoration**
    (pure content, no system, no API story) and a **Nether/End progression overhaul**
    (a dimension is a *place*, not a *system* — it would cut across every existing silo).
11. **Exploration/structures as a fifth silo.** Its natural features are already owned:
    loot-at-distance is Prosperity, maps/cartographer are Mercantile trade content,
    danger-at-distance is Tribulation. A fifth mod here would be born in three silo
    conflicts. (Transportation, the adjacent candidate, survives — barely — see §9.)

---

## 9. Additional Areas for Overhaul Evaluation

Survey of remaining vanilla systems, filtered against the four tests (domain fit,
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
  farming is AFK-able and flavorless, animal breeding is click-spam. The thesis:
  make *what you eat and raise* matter the way Mercantile made *who you trade with*
  matter — crop quality tiers from soil/care, meals worth cooking from existing
  ingredients, animals with lineage worth breeding — all with vanilla blocks, items, and
  the composter/smoker/campfire cast that vanilla shipped and forgot.
- **Narrative & motif:** working name **Husbandry** — it is literally a vanilla
  advancement tab, the strongest possible domain-fit naming claim, and fits the abstract-
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
- **Verdict: High.** Big untouched silo, four natural integrations, zero overlap, a clean
  single-domain overhaul. The strongest "what comes after Prosperity" candidate.

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

- **Silo & boundary:** owns weather event variety and weather gameplay consequences.
  Does NOT touch: seasons (changes vanilla's core rhythm — cross-cuts every silo;
  explicitly out), mob spawn *scaling* (Tribulation), crop growth rules (would collide
  with Husbandry — if both exist, Tempest exposes weather state and Husbandry consumes
  it), and not sleep, rest, or how the night passes — Respite owns those. The
  day/night/moon axis itself is shared vanilla state: Tempest may *read* it (as Respite
  does, and already exposes as a Chronometer signal accessor), never own or reshape it.
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

Vitality — sleep, rest, and the passage of night — entered through this gate as
**Respite**, the fifth member, without appearing on the original survey; the gate, not
the list, is what admits a member. Remaining candidates:

**Husbandry → Apothecary → Tempest**, with Stratum held until
its three-way boundary contract is drafted and Expedition on the Mojang-watchlist. Each
follows the same admission path: DESIGN.md + SPEC.md first (the Prosperity model proved
this works), API designed from day one, no HUD slot unless it carries persistent ambient
state, palette cleared against the §3.1 pairing rule, name in the register.
