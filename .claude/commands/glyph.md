---
description: Design a 16×16 Minecraft HUD glyph as an ASCII grid and render it to a PNG sprite.
argument-hint: <motif description> [mod: meridian|mercantile|tribulation|prosperity]
allowed-tools: Read, Write, Bash(python3 scripts/glyph.py:*), Bash(uv run scripts/glyph_pil.py:*)
---

You are designing a **16×16 pixel-art glyph** for a Concord Minecraft mod, then
rendering it to a PNG with `scripts/glyph.py`. The pattern: *you* lay out the
sprite as a character grid (which you do reliably); the script deterministically
rasterizes it (which you don't). The whole craft is in the grid.

## Request

$ARGUMENTS

If no mod is named, ask which mod the glyph is for (its palette decides the
accents) — or proceed palette-neutral if the user says it's not mod-specific.

## Step 1 — Pin the palette

Read `design/DESIGN-SYSTEM.md` §2 (per-mod accents) and §5 (glyph spec). The
renderer already knows the design-system colors as named tokens — run
`python3 scripts/glyph.py --list-colors` to see them. Use the **named tokens**
in your legend (e.g. `mercantile.emerald`, `ink`, `gold`), not raw hex, so the
glyph stays tied to the system. A mod's accents never appear in another mod's
glyph (§2 coexistence rule 1).

## Step 2 — Design the grid

Honor the design-system glyph conventions (§4 logo formula, scaled down to a
glyph; §5):

- **16×16, one motif object**, centered and readable at native size. A HUD glyph
  is tiny — silhouette first, detail second. If you can't tell what it is at
  16px, simplify.
- **Dark-stone outline.** Wrap the motif in an `ink` (`#0a0a0a`) 1px outline so
  it reads against any HUD background, the way vanilla item sprites do.
- **One glowing accent**, the mod's signature. Use the brighter accent (`*-bright`,
  `gold`, `ember`) sparingly for highlights; the base accent for the body.
- **Vanilla aesthetic.** Limited palette (≈3–5 colors), hard pixels, no
  anti-aliasing or gradients — the script renders exactly the cells you write.
- `.` is transparent. Keep at least a 1px transparent margin unless the motif
  intentionally bleeds to the edge.

Write the spec to `scripts/examples/<mod>-<motif>.glyph` (or a path the user
gives). Format — a `legend:` mapping single chars to colors, then a `frame:` (or
`grid:`) of exactly 16 rows × 16 chars. `#` begins a comment anywhere; don't use
it as a legend key. The full format (with a worked example) is documented in the
`SPEC FORMAT` header of `scripts/glyph.py`.

**Animated glyph?** Add more than one `frame:` block (all the same size) plus a
`frametime:` directive (ticks/frame). The renderer emits a vertical sprite
strip (16 × 16·N) and a `<name>.png.mcmeta` sidecar — exactly the vanilla
animated-texture packaging. Design the motion as a short loop (e.g. a pulse:
small → medium → large → medium).

## Step 3 — Render and review

```bash
python3 scripts/glyph.py scripts/examples/<name>.glyph
```

This writes `<name>.png` (the true master) and `<name>@16x.png` (a 256px
nearest-neighbor preview; a horizontal filmstrip if animated). **Read the @16x
preview image back** and judge it honestly against the motif. Then iterate the
grid until it's right — fixing pixel art is fast: edit the `.glyph` and re-run.

> Equivalent Pillow backend, if the user prefers it:
> `uv run scripts/glyph_pil.py scripts/examples/<name>.glyph` — identical sprite
> output, pulls Pillow via uv instead of running on bare stdlib. For **animated**
> specs it additionally writes `<name>@16x.gif`, a real animated preview (frames
> on a checkerboard) — the best way to judge the motion. Send it to the user.

## Step 4 — Place the master

The design system masters a HUD glyph at `art/hud-icon-16.png` in the *mod's*
repo (§5), with derived copies in `docs/`/`assets/`. This concord repo is the
design hub, not a mod, so generate here for review; when the user approves, the
final PNG belongs in the target mod's `art/`. Confirm the destination with the
user rather than assuming.

Keep going until the glyph reads clearly at 16px and matches the mod's identity.
Show the user the preview each iteration.
