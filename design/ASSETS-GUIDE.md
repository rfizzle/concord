# Assets Guide — a member mod's `design/ASSETS.md`

Every member mod carries a `design/ASSETS.md`: the asset manifest. One row
per committed asset: its source under `art/` and the final file it ships as.
`DESIGN.md` covers *why* each asset exists and how it looks; this file covers
*where it lives* — nothing else. It is a lookup table, not a design document:
no rationale, no narratives.

**This document owns** exactly one fact per asset: source → shipped path.
**It defers** why the asset exists and how it looks to `DESIGN.md`, and when
it renders or plays to `SPEC.md`.

**Truth direction** (the `/align` model): filesystem → doc. The manifest
describes what is on disk; correcting it toward reality is safe and largely
mechanical. It updates in the same PR that adds, moves, or removes an asset.

## The shape

Fixed name `design/ASSETS.md`, title `# <Mod> — Asset Manifest`, opening
with a short blockquote stating the conventions the tables rely on:

> Where every committed asset lives: its source under `art/` (a re-renderable
> `.glyph` for pixel art, a `.sfx` for audio, or a `.png` master for
> generated hi-res art) and the final file it ships as. **`MISSING`** in the
> source column flags a pixel asset with no `.glyph` source yet — a candidate
> for the glyph pipeline (concord `design/DESIGN-SYSTEM.md` §8). Final paths
> are under `src/main/resources/` unless noted.

Then the sections, each a three-column table:

**`## Branding masters`** — Asset · Source · Final / derived copies. The
full logo is typically a generated `.png` master (not glyph-based — its
committed generation prompt in `DESIGN.md` is its source); the mod icon and
any size ladder come from a `.glyph` where possible. The derived-copies
column names every place a master lands (`assets/<mod>/icon.png`,
`site/assets/…`), with sizes and roles in parentheses.

**`## In-game pixel art`** — Asset · `.glyph` source · Final asset. One row
per texture; families produced by one generator may share a grouped row
(sources as a glob plus the script, finals as a brace-list). Animated
textures note the frame count and their `.png.mcmeta`. Rendered previews
under `art/` are gitignored review artifacts, not entries.

**`## Audio (.sfx — procedural synthesis)`** — present when the mod ships
custom sound: Asset · `.sfx` source · Final asset
(`art/audio/<name>.sfx` ↔ `.ogg` → `assets/<mod>/sounds/<name>.ogg`).

**`## Not yet created`** — planned assets: Asset · intended source
(`/glyph`, `/sfx`, Gemini) · destination, marked `— (planned, …)`. This is
the manifest's only forward-looking section; an entry graduates into the
table above when the asset lands.

## Requirements

- **Complete both ways.** Every committed asset has a row; every row has a
  file. No orphan entries, no unlisted assets — the `/align` assets sweep
  holds the manifest to the filesystem.
- **Every pixel master has its `.glyph`; every sound its `.sfx`** — same
  path, same basename (DESIGN-SYSTEM §8–9). `MISSING` is the tracked
  exception, not a shrug: it marks pipeline debt.
- **Real paths, exactly.** Source and final columns are literal repo paths a
  reader can open; no hand-waving ("various textures").
- **Same-PR updates.** An asset change without its manifest row (or a
  removal without deleting the row) is incomplete work.

## Checklist before committing

- [ ] Every file under `art/` (excluding gitignored previews and
      `exploration/`) appears in exactly one row.
- [ ] Every custom file under `assets/<mod>/textures/` and
      `assets/<mod>/sounds/` traces back to a source row.
- [ ] Every `MISSING` is genuinely missing — no stale flags on assets that
      now have a `.glyph`.
- [ ] "Not yet created" holds only assets still planned.
- [ ] No prose beyond the intro blockquote — rationale lives in `DESIGN.md`.
