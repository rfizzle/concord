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
  or tooltip. This is the one deliberately absolute typographic rule — and it is about
  *fonts*, not textures. Custom textures are welcome and have their own pathway (§8); a
  custom font is not, because text legibility and cross-mod consistency depend on it.

## 4. Logos

The formula, the spec for every **new** member logo:

> **Pixel art. Dark stone brickwork frame. One central glowing motif object. Mod name
> in blocky pixel type below.**

| Mod | Motif object |
|---|---|
| Meridian | Stone arch + eight-pointed compass rose, crescent moon |
| Tribulation | Hourglass, heart above, skulls below |
| Prosperity | Overflowing chalice, ornate key crowning the frame |
| Mercantile | Market stall with hanging scales, in a circular emerald-rimmed medallion on green brickwork — shipped logo, **ratified as-is 2026-06-12** (predates the formula; the earlier bell-over-emeralds proposal is retired — see [`../VISION.md`](../VISION.md) §3.2) |

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
(see [`../REPO-LAYOUT.md`](../REPO-LAYOUT.md)). Each pipeline-generated master ships its
`.glyph` source beside it (§8) — `art/hud-icon-16.png` + `art/hud-icon-16.glyph`.

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

## 8. Textures

**The stance.** Custom, high-quality textures are encouraged across the suite — icons,
HUD glyphs, item and block sprites, and retextured vanilla mobs where they earn it. The
old "reach for the vanilla sprite first" reflex is retired: we have a clean pathway to
good art (below), so the bar is *quality and coherence*, not vanilla purity. The only
hard cosmetic rule is the vanilla **font** (§3); textures are open.

**What "good" means here.** A texture is conformant when it:

- is **pixel art** — hard pixels, no anti-aliasing or smooth gradients (dither instead),
  a limited palette (≈3–5 colors for a glyph);
- uses the **design-system colors** as named tokens (`mercantile.emerald`, `ink`, `gold`
  — run `python3 scripts/glyph.py --list-colors`), and a mod's accents never appear in
  another mod's art (§2 rule 1);
- **reads as Minecraft** — sits naturally beside vanilla sprites at the same size; an
  `ink` (`#0a0a0a`) 1px outline so it reads against any background, silhouette before
  detail;
- is **legible at its target size** — design the 16px glyph for 16px, don't shrink a
  large drawing into the slot.

**The pipeline.** Author textures as ASCII-grid `.glyph` specs and rasterize them
deterministically with `scripts/glyph.py` — you lay out the grid (reliable), the script
renders the exact cells (no drift). Three entry points:

| Tool | Use it for |
|---|---|
| `/glyph` | any pixel-art glyph — a single 16×16 HUD/UI sprite, a 16/32/64/128/256 size ladder (author small, integer-upscale large), or an animated multi-frame strip |
| `mc-textures` skill | the craft reference `/glyph` leans on — read before designing |

**Companion `.glyph` files (repeatability).** Every committed texture master carries its
`.glyph` source at the same path with the `.glyph` extension, committed beside the PNG in
the mod's `art/` — `art/hud-icon-16.png` ↔ `art/hud-icon-16.glyph`; a size ladder commits
one `.glyph` per natively-authored tier. The `.glyph` is the source of truth: minor edits
re-render in seconds instead of hand-patching pixels, and the master is reproducible from
the spec alone (the renderer lives in concord's `scripts/`; check it out as a sibling to
re-render a member's art). PNG masters that predate the pipeline are grandfathered, but
any *re-touch* recreates them through a `.glyph`.
