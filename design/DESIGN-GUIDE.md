# Design Guide — a member mod's `design/DESIGN.md`

Every member mod carries a `design/DESIGN.md`: the mod's brand record — its
narrative, motif, signature palette, logo, and the art direction behind every
custom asset. It answers *why the mod looks and sounds the way it does*, in
enough detail that any asset could be regenerated true to brand.

The split with the suite standard: [`DESIGN-SYSTEM.md`](DESIGN-SYSTEM.md) is
**the rules** — shared tokens, the palette pairing rule, typography, the logo
formula, icon sizes, the texture (§8) and audio (§9) pipelines. `DESIGN.md`
is **the mod's application of them** — which four signature colors, which
motif, what the logo depicts. The document never restates a suite rule; it
records the mod-owned decisions the rules leave open, and links the standard
for everything else.

**This document owns** the brand: narrative, tagline, motif, palette, logo,
art direction, generation prompts, the HUD slot decision, and how the brand
lands on web surfaces. **It defers** what features do — including when a HUD
element shows or a sound plays — to `SPEC.md`; the player pitch to
`VISION.md`; every asset's whereabouts to `ASSETS.md`; page and listing copy
to `site/`; and the shared rules to `DESIGN-SYSTEM.md`.

**Truth direction** (the `/align` model): bidirectional brand intent. Only
objective drift (a hex that doesn't match the shipped CSS, a described asset
that doesn't exist) is corrected toward reality; intent statements are
adjudicated, not rewritten.

## The shape

Fixed name `design/DESIGN.md`, title `# <Mod> — Design Specification`, with
a one-line blockquote subtitle (domain + Minecraft version). Sections:

**1. Brand Identity**

- **Narrative** — 2–4 sentences: what the mod is, and the visual language it
  draws from ("treasure hoards, overflowing chests, precious gems, ancient
  keys"). This names the mod's one mythic register (suite `VISION.md` §2).
- **Tagline** — the line, verbatim as it appears in `members.json`, README,
  and the site hero.
- **Motif** — the single motif object (DESIGN-SYSTEM §4): what it is, where
  it may appear (logo, headers, flavor art), and that it never appears in
  another mod's assets.
- **Logo description** — prose detailed enough to regenerate each branding
  master true to brand: the full logo (per the stone-frame formula), the
  128×128 icon, and the 16×16 glyph if the mod has one.
- **Color palette** — a table (Role · Color · Hex · Usage) of the mod's four
  signature colors (tinted surface pair + two accents, DESIGN-SYSTEM §2) and
  any working shades, on top of the shared neutrals listed by their token
  names. The signature pair must pass the pairing rule against the full §2
  table, including reserved rows.
- **Typography** — only the mod-owned parts: the heading gradient endpoints.
  Everything else is the standard; in-game is the vanilla font, always.

**2. HUD decision** — slot or no slot, and why, against the standard's test:
a slot only for *persistent ambient state* the player needs while walking
around (`HUD-STANDARD.md`). "No slot, by design" is a first-class answer and
gets recorded with its reasoning, plus where the mod's info lives instead
(Jade/WTHIT, its own screens, recipe viewers).

**3. Assets** — a pointer, not a manifest: the inventory of every asset,
its source, and its ship path lives in the mod's `design/ASSETS.md` (see
[`ASSETS-GUIDE.md`](ASSETS-GUIDE.md)). This document owns the *why and the
look* of each asset family; the manifest owns the *where*.

**4. Generation prompts** — the committed prompts that produced the
non-glyph masters (Gemini/PixelLab: logo, OG image, hero art), kept beside
the palette hexes they embed so the art is regenerable. Pixel-art sources
are `.glyph` files under `art/` — referenced, never duplicated here.

**5. Image references** — the reference shots and exploration images the
brand leans on, and where they live (`art/exploration/`).

**6. Website & listing brand notes** — how the brand lands on the mod's
surfaces: accent usage, hero art direction, OG image spec. Content itself
lives elsewhere — page copy in `site/` (rendered by the shared template),
store listing copy in `site/listing-*.md` (per the `mc-listing` skill) —
this section carries only what is *brand*, not what is *content*.

**7. Concord context** — one short section placing the mod in the suite:
its silo in one line, its signature pair against its siblings' (why it reads
distinct), and links to the suite `VISION.md` and standards.

**Open decisions** — optional final section for genuinely unresolved brand
questions. Resolved decisions get folded into the sections above and removed
from here — the document states the current brand, not its history.

## Requirements

- The palette passes DESIGN-SYSTEM §7 admission: dark-tint surfaces in the
  `#1a..`/`#2e..` range, both accents clear of every existing and reserved
  pair, neutrals untouched.
- One motif object, in the register; the logo follows the §4 formula.
- No custom fonts anywhere, in any mockup or asset (§3).
- Custom-asset decisions follow the suite stance (custom where it earns its
  place, vanilla where vanilla is genuinely right — `AGENTS.md`, DESIGN-SYSTEM
  §8–9); the *judgment* for each asset family is recorded here.
- Descriptions match the shipped files — when an asset is redesigned, its
  description and prompt update in the same PR.

## Checklist before committing

- [ ] Narrative, tagline, and motif present; tagline matches `members.json`.
- [ ] Palette table passes the pairing rule against the full DESIGN-SYSTEM
      §2 table, reserved rows included.
- [ ] Logo description detailed enough to regenerate the master.
- [ ] HUD decision recorded with its reasoning — including "no slot".
- [ ] No suite rules restated; the standard is linked, not copied.
- [ ] Generation prompts committed for every non-glyph master.
- [ ] Nothing narrates history; the document reads as the current brand.
