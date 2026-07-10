# Concord Design System

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
| Respite | `#141a3d` / `#232e66` | `#7C8EE8` Moonlight Indigo | `#F2C14E` Candleglow |
| Distillation | `#1a0a18` / `#2e102c` | `#C44DCC` Potion Magenta | `#E77C56` Copper |
| Cultivation | `#101a0a` / `#1c2e10` | `#D9A441` Wheat Amber | `#7CB342` Leaf Green |
| Instinct | `#1a120a` / `#2e2210` | `#E5709B` Heart Rose | `#B8622B` Hide Russet |

Reserved by shortlisted future members (`VISION.md` §9): Tempest — Storm Blue
`#4A7FB5` / Lightning White `#E8F4FF`; Stratum — Deepslate Grey `#5B6470` / Copper
Orange `#E07A3F`.

### Coexistence rules

1. **Accents never leave their mod's surfaces.** A mod's accents appear only in its own
   UI, site, and HUD contexts.
2. **The pairing rule:** no two mods may share *both* accents; sharing one is fine if
   the pair is distinct. Gold-with-violet reads Meridian; gold-with-cyan reads
   Prosperity; candle-with-indigo reads Respite; magenta-with-copper reads
   Distillation (the nearest hue, Meridian's purple, is disambiguated by both
   partners); amber-with-leaf reads Cultivation (the gold-family amber is
   disambiguated by its green partner); rose-with-russet reads Instinct (the suite's
   only pink — its russet sits near Distillation's lighter copper but the rose
   partner disambiguates at a glance). Every new palette is checked against the
   full table above.
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
- **Notification glyph:** chat lines and action-bar toasts a mod pushes to the player
  are prefixed with **✦** (U+2726, four-pointed star) — the shared marker that reads as
  "a Concord mod is telling you something" across every member. Reserve **⚠** (U+26A0)
  for a genuine warning (a blocked or destructive action); everything else takes ✦. Keep
  the following text vanilla-toned and terse. Prosperity's loot toast, structure-cleared
  line, and peek hint are the reference.

## 4. Logos

The formula, the spec for every **new** member logo:

> **Pixel art. Dark stone brickwork frame. One central glowing motif object. Mod name
> in blocky pixel type below.**

| Mod | Motif object |
|---|---|
| Meridian | Stone arch + eight-pointed compass rose, crescent moon |
| Tribulation | Hourglass, heart above, skulls below |
| Prosperity | Overflowing treasure chest, ornate key crowning the frame |
| Mercantile | Market stall with hanging scales, in a circular emerald-rimmed medallion on green brickwork |
| Respite | Hanging lantern in a circular indigo stone medallion over midnight brickwork |
| Distillation | Alchemist's still in a rune-carved magenta medallion — copper alembic and coiled piping feeding glowing flasks, on plum brickwork |
| Cultivation | Bound wheat sheaf with a scythe and hoe crossed behind it, on mossy-green brickwork breaking into tilled furrows |
| Instinct | Glowing rose paw print pressed into a weathered stone slab, in a circular russet-leather-rimmed medallion over umber brickwork |

One motif object per mod; the motif may recur in headers and flavor art but never in
another mod's assets.

## 5. Icons

Two sizes per mod, both pixel art:

- **128×128 mod icon** — `fabric.mod.json`, store listings. Master at
  `art/icon-128.png` in the mod repo.
- **16×16 glyph** — HUD element (if the mod has a slot), Jade/recipe-viewer contexts.
  Master at `art/hud-icon-16.png`. Existing: Tribulation skull, Prosperity chest,
  Respite lantern, Distillation bottle, Cultivation sheaf, and Instinct paw (those
  four Jade/recipe-viewer contexts only — no HUD slot).
  Needed: Mercantile (bell or emerald), Meridian (open book — Jade/EMI contexts only).

Masters live in each repo's `art/`; `docs/` and `assets/` hold derived copies
(see [`../REPO-LAYOUT.md`](../REPO-LAYOUT.md)). Each pipeline-generated master ships its
`.glyph` source beside it (§8) — `art/hud-icon-16.png` + `art/hud-icon-16.glyph`.

## 6. Web asset conventions

- OG image: full logo on Ink, 1200×630
- `<title>`: `Mod — Tagline`; meta description: tagline + one mechanical sentence
- Favicon set: `favicon.ico`, `favicon-32.png`, `apple-touch-icon.png` (180×180)
- Cross-mod footer on every mod site: "Part of **Concord** — a modular collection of system overhauls",
  four 16×16 glyphs + names + taglines, current mod highlighted

## 7. Admitting a new palette

A future member's palette is conformant when: surfaces are a dark tint of its primary
hue in the `#1a..`/`#2e..` value range; both accents pass the pairing rule against every
row of §2 (including reserved rows); text/surface roles use the shared neutrals
unchanged; and the logo follows the §4 formula with a single new motif object.

## 8. Textures

**The stance.** Custom, high-quality textures are encouraged across the suite — icons,
HUD glyphs, item and block sprites, and retextured vanilla mobs where they earn it. There
is a clean pathway to good art (below), so the bar is *quality and coherence*, not vanilla
purity. The only hard cosmetic rule is the vanilla **font** (§3); textures are open.

**What "good" means here.** A texture is conformant when it:

- is **pixel art** — hard pixels, no anti-aliasing or smooth gradients (dither instead),
  a limited palette (≈3–5 colors for a glyph);
- uses the **design-system colors** as named tokens (`mercantile.emerald`, `ink`, `gold`
  — run `python3 .ai/skills/mc-textures/scripts/glyph.py --list-colors`), and a mod's accents never appear in
  another mod's art (§2 rule 1);
- **reads as Minecraft** — sits naturally beside vanilla sprites at the same size; an
  `ink` (`#0a0a0a`) 1px outline so it reads against any background, silhouette before
  detail;
- is **legible at its target size** — design the 16px glyph for 16px, don't shrink a
  large drawing into the slot.

**The pipeline.** Author textures as ASCII-grid `.glyph` specs and rasterize them
deterministically with `.ai/skills/mc-textures/scripts/glyph.py` — you lay out the grid (reliable), the script
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
the spec alone (the renderer ships with the `mc-textures` skill at
`.ai/skills/mc-textures/scripts/glyph.py`, vendored into every repo, so re-rendering needs
no sibling checkout). Re-touching a texture recreates it through its `.glyph`.

## 9. Audio

**The stance.** Custom sound is encouraged across the suite — the `.sfx` pipeline gives a
clean, consistent way to make it, so the bar is *fitness and coherence*, not vanilla purity.
Custom audio comes from **procedural synthesis** (no recorded audio, samples, or licensing),
through the `.sfx` pipeline below. This is the audio analogue of §8.

**Custom vs. vanilla.** Default to **custom** where a cue benefits from its own identity.
Use a vanilla `SoundEvent` when it is genuinely already the right sound (worth knowing:
`event.raid.horn`, `block.bell.resonate`, `block.note_block.*`, `block.beacon.*`), or when
the sound is **organic** — a real horn, a physical bell, footsteps, foley — which pure
synthesis renders obviously fake. This is not license for a wholesale soundscape overhaul:
add custom cues where they earn their place, not everywhere for its own sake.

**What "good" means here.** A sound is conformant when it:

- is **Ogg Vorbis, mono** (mono is required for 3D distance attenuation; stereo is only for
  music/ambient/UI), 44.1 or 48 kHz;
- is **short and trimmed** — an SFX cue, not a track; no dead air, most cues well under ~2 s;
- sits at **vanilla loudness** — normalized with headroom (peak ≈ −1 dBFS, no clipping);
- reads as **one gesture** — a single recognizable cue (rise, fall, two-tone, pulse),
  silhouette first, like a glyph;
- **belongs to its mod** — matches the feature's character;
- ships its **companions** — a registered `SoundEvent`, a `sounds.json` entry, and a
  **subtitle** (accessibility, non-negotiable).

**The pipeline.** Author sounds as declarative `.sfx` specs (JSON) and synthesize them
deterministically with `.ai/skills/mc-audio/scripts/sfx.py` — you describe the layers
(oscillators, envelopes, pitch sweeps), the script renders exactly that (seeded noise, no
drift). Stdlib-only synthesis; its one external tool is **ffmpeg** (the WAV→Ogg encode).

| Tool | Use it for |
|---|---|
| `/sfx` | any synthesized cue — a UI blip, an alarm klaxon, a tech alert, a charge-up, a chiptune sting |
| `mc-audio` skill | the craft reference `/sfx` leans on — read before designing |

Because the renderer can't be heard, every run emits objective feedback — a waveform +
spectrogram PNG and stats (duration, peak dBFS, RMS, spectral centroid) — to iterate
against; the final ear-check is a human's.

**Companion `.sfx` files (repeatability).** Every committed sound master carries its `.sfx`
source at the same path with the `.sfx` extension, committed beside the `.ogg` in the mod's
`art/audio/` — `art/audio/pylon-alarm.ogg` ↔ `art/audio/pylon-alarm.sfx`. The `.sfx` is the
source of truth: edits re-render in seconds and the master is reproducible from the spec
alone. The derived `.ogg` is copied into `assets/<mod>/sounds/`. Re-touching a sound
recreates it through its `.sfx`.

## 10. Localization keys

**The rule.** Every user-visible string is translatable — command feedback, HUD text,
Jade/WTHIT tooltip lines, advancement titles, config labels. No literal user-facing
strings in code. The one sanctioned exception: op-gated dense diagnostic/telemetry
command output may be `Component.literal`.

**The prefix vocabulary.** Keys in `en_us.json` are namespaced by the *surface* the
string appears on, one prefix per surface:

| Prefix | Surface | Example |
|---|---|---|
| `config.<mod>.*` | Config labels — every label pairs with a `.tooltip` key | `config.tribulation.enableTierHud` |
| `command.<mod>.*` | Command feedback | `command.prosperity.no_container` |
| `hud.<mod>.*` | HUD element and detail-panel text | `hud.tribulation.detail.title` |
| `gui.<mod>.*` | Screens and widgets | `gui.mercantile.reroll_trades` |
| `tooltip.<mod>.*` | Hover tooltips and Jade/WTHIT lines | `tooltip.mercantile.pylon.fuel` |
| `message.<mod>.*` | Chat lines pushed by the mod | `message.tribulation.level_up` |
| `notification.<mod>.*` | ✦-prefixed toasts and action-bar lines | `notification.prosperity.loot_generated` |
| `advancements.<mod>.*` | Advancement `.title` / `.description` pairs | `advancements.meridian.root.title` |
| `info.<mod>.*` | Block/item purpose lines | `info.meridian.enchant.clues` |
| `key.<mod>.*` | Keybind names, plus one `key.categories.<mod>` per mod | `key.prosperity.peek_detail` |
| `stat.<mod>.*` | Custom statistics | `stat.tribulation.highest_level_reached` |
| `block.<mod>.<id>` | Block names (vanilla-mandated) | `block.meridian.stoneshelf` |
| `item.<mod>.<id>` | Item names (vanilla-mandated) | `item.mercantile.delivery_contract` |
| `enchantment.<mod>.<id>` | Enchantment names (vanilla-mandated) | `enchantment.tribulation.soulbound` |

**Conventions that ride along.**

- Internal enums (tiers, moods, states) expose a `translationKey()` rather than display
  strings — code never formats an enum name for the player.
- Notification strings carry the **✦** suite marker (§3) inside the localized value, not
  bolted on in code.
- Hints that name a key use `Component.keybind` so the client resolves the player's
  actual binding, never a hardcoded key name.

**Enforcement.** These conventions are pinned by each mod's Tier-1 resource-contract
tests; the recipe lives in the `mc-mod-testing` skill.
