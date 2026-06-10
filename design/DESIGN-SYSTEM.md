# Concord Design System — v1

> Normative visual language for every Concord member: shared tokens, per-mod palettes,
> typography, and the logo/icon formula. The consumable form of the shared tokens is
> [`../docs/tokens.css`](../docs/tokens.css), hot-linked by mod sites once the Concord
> site is on Pages. Narrative voice & tone live in [`../VISION.md`](../VISION.md) §2.

## 1. Shared neutral tokens

Identical across every Concord property — websites, listings, OG images. These are the
only colors that cross mod boundaries.

| Token | CSS variable | Hex | Role |
|---|---|---|---|
| Ink / Obsidian | `--color-ink` | `#0a0a0a` | Page background |
| Card / Dark Stone | `--color-card` | `#1a1a1a` | Cards, panels |
| Elevated / Stone | `--color-elevated` | `#222222` | Hover, elevated surfaces |
| Bone | `--color-bone` | `#e8e0d4` | Primary text |
| Ash | `--color-ash` | `#a89f93` | Secondary text |
| Smoke | `--color-smoke` | `#6b6359` | Tertiary / disabled text |

Variable names match the conventions already in the Tribulation/Mercantile site CSS so
adoption is drop-in.

## 2. Per-mod signature palettes

Every mod's identity is exactly four colors on top of the shared neutrals: a tinted
dark-surface pair + two accents.

| Mod | Tinted surfaces | Accent 1 | Accent 2 |
|---|---|---|---|
| Meridian | `#1a0a3e` / `#2a1a6e` | `#7B2FBE` Arcane Purple | `#DAA520`→`#FFD700` Gold |
| Mercantile | `#0a140d` / `#10241a` *(proposed — currently neutral)* | `#50C878` Emerald | `#6DDB94` Emerald Bright |
| Tribulation | `#1a0a0a` / `#2e1010` | `#DC143C` Crimson | `#FF6B35` Ember |
| Prosperity | `#1a1408` / `#2e2510` | `#DAA520`→`#FFD700` Gold | `#4EEAED` Diamond Cyan |

Reserved by shortlisted future members (`VISION.md` §9): Husbandry — Wheat Amber
`#D9A441` / Leaf Green `#7CB342`; Apothecary — Potion Magenta `#C44DCC` / Copper
`#E77C56`; Tempest — Storm Blue `#4A7FB5` / Lightning White `#E8F4FF`; Stratum —
Deepslate Grey `#5B6470` / Copper Orange `#E07A3F`.

### Coexistence rules

1. **Accents never leave their mod's surfaces.** A mod's accents appear only in its own
   UI, site, and HUD contexts.
2. **The pairing rule:** no two mods may share *both* accents; sharing one is fine if
   the pair is distinct. Gold-with-violet reads Meridian; gold-with-cyan reads
   Prosperity. Every new palette is checked against the full table above.
3. **HUD tints** use the mod's accent/state colors inside the standard element only
   (see [`../HUD-STANDARD.md`](../HUD-STANDARD.md) §3).

## 3. Typography

- **Web body:** monospace stack — `"SF Mono", "Cascadia Code", "Fira Code", Consolas` —
  Bone on Ink.
- **Web headings:** blocky/pixel display treatment in the mod's accent gradient, with
  the shared 4s ease-in-out brightness pulse (1.0 → 1.15).
- **In-game:** the vanilla Minecraft font only, ever. No custom fonts in any GUI, HUD,
  or tooltip.

## 4. Logos

The formula, applied by every member:

> **Pixel art. Dark stone brickwork frame. One central glowing motif object. Mod name
> in blocky pixel type below.**

| Mod | Motif object |
|---|---|
| Meridian | Stone arch + eight-pointed compass rose, crescent moon |
| Tribulation | Hourglass, heart above, skulls below |
| Prosperity | Overflowing chalice, ornate key crowning the frame |
| Mercantile | *(needed)* — proposed: market arch framing a bell above stacked emeralds |

One motif object per mod; the motif may recur in headers and flavor art but never in
another mod's assets.

## 5. Icons

Two sizes per mod, both pixel art:

- **128×128 mod icon** — `fabric.mod.json`, store listings. Master at
  `art/icon-128.png` in the mod repo.
- **16×16 glyph** — HUD element (if the mod has a slot), Jade/recipe-viewer contexts.
  Master at `art/hud-icon-16.png`. Existing: Tribulation skull, Prosperity chest.
  Needed: Mercantile (bell or emerald), Meridian (open book — Jade/EMI contexts only).

Masters live in each repo's `art/`; `docs/` and `assets/` hold derived copies
(see [`../REPO-LAYOUT.md`](../REPO-LAYOUT.md)).

## 6. Web asset conventions

- OG image: full logo on Ink, 1200×630
- `<title>`: `Mod — Tagline`; meta description: tagline + one mechanical sentence
- Favicon set: `favicon.ico`, `favicon-32.png`, `apple-touch-icon.png` (180×180)
- Cross-mod footer on every mod site: "Part of **Concord** — a Vanilla+ collection",
  four 16×16 glyphs + names + taglines, current mod highlighted

## 7. Admitting a new palette

A future member's palette is conformant when: surfaces are a dark tint of its primary
hue in the `#1a..`/`#2e..` value range; both accents pass the pairing rule against every
row of §2 (including reserved rows); text/surface roles use the shared neutrals
unchanged; and the logo follows the §4 formula with a single new motif object.
