# Concord HUD Standard

> Normative for every Concord member mod that renders an on-screen HUD surface — the
> persistent slot badge (§2–§7) and the optional hold-to-peek detail panel (§8).
> Tribulation's `TribulationHudOverlay` and `TierDetailPanelRenderer` are the reference
> implementations.

## 1. Two HUD surfaces

The standard governs two on-screen surfaces a mod may render, independently of each other:

- **The slot badge** (§2–§7) — a persistent, always-on element in the shared top-left
  stack. A mod takes a slot **only if it has persistent ambient state the player needs
  while walking around** (a level, a standing, a tier that changes as you play).
- **The hold-to-peek detail panel** (§8) — an on-demand overlay shown only while a keybind
  is held, expanding the badge's headline into the full picture. Optional and independent
  of the badge: a mod may ship a badge, a panel, both, or neither.

A **transient cosmetic** drawn from `HudRenderCallback` (Respite's weariness blink) is
neither: it takes no slot and no accessors, and only the §3 draw-batch rule applies.
Everything else that is neither persistent-ambient nor on-demand-detail belongs in screens,
tooltips (Jade/WTHIT), or recipe viewers. Opting out of both is conformant — Meridian has
no HUD surface by design. Future members default to **no slot**.

## 2. Slot registry

Fixed priority order, top to bottom. Elements shift up to fill gaps when a
higher-priority mod is absent or its HUD is disabled.

| Slot | Mod | Content |
|---|---|---|
| 1 | Tribulation | 16×16 skull glyph tinted by tier, 2px level-progress bar |
| 2 | Mercantile | 16×16 balance-scale glyph (`reputation_badge`), 2px tier-tinted bar, no text |
| 3 | Prosperity | Untinted chest glyph, current loot distance tier as a tier-colored label |
| — | Meridian | No slot, by design — enchanting screen, Jade/WTHIT, recipe viewers |
| — | Respite | No slot, by design — weariness rides vanilla status-effect icons; a transient full-screen blink is drawn from `HudRenderCallback` (§1 cosmetic, not a badge) |
| — | Distillation | No slot, by design — brewing screen and vanilla effect icons |
| — | Cultivation | No slot, by design — soil overlays, Jade/WTHIT, tooltips |
| — | Instinct | No slot, by design — crouch-inspect, Jade/WTHIT, `/instinct info` |

New slots are assigned here, in this file, by appending — never by renumbering.

## 3. Visual spec

- Container: **optional** — a semi-transparent black box, `#000000` at 50–60% opacity,
  2px rounded corners. Prosperity draws one; Tribulation and Mercantile draw the glyph
  and bar directly on the screen. Either is conformant.
- Contents: 16×16 mod glyph (left); optional short text label (right) in the **vanilla
  Minecraft font**, white `#FFFFFF`, standard drop shadow; optional 2px progress bar
  directly under the glyph.
- **Standard element height: 20px**, with a **2px gap** between stacked elements.
  (Tribulation's 16px icon + 1px gap + 2px bar = 19px rounds into the 20px box.)
- No custom fonts, no ornate frames, no animation beyond simple color tint and brief
  transition lerps (reference: Tribulation's 2s gold-to-tier-color level-up lerp;
  Prosperity's specced 1.5s tier-crossing lerp).
- Glyph tinting by state is encouraged (Tribulation: white → yellow → orange → red →
  dark crimson across tiers); it is the element's only decoration.
- The glyph is a **purpose-built texture drawn at 16×16**, not a downscaled vanilla item
  render (those go muddy at 16px). Authoring at 32×32 and blitting down to 16 is fine
  (Tribulation and Prosperity do). Author it through the texture pipeline and commit its `.glyph`
  source under `art/glyphs/`, joined to the shipped sprite by `design/ASSETS.md` —
  see [`design/DESIGN-SYSTEM.md`](design/DESIGN-SYSTEM.md) §8.
- **Draw batch integrity.** Both surfaces draw through `GuiGraphics`
  (`blit`/`fill`/`drawString`) and **end every render pass with `graphics.flush()`**.
  The flush commits the batch immediately, so a batching optimizer (ImmediatelyFast) or a
  framebuffer-reading effect (Blur+, post shaders) can't fold in, drop, or capture
  unflushed GUI geometry. Never draw with raw `RenderSystem.setShaderTexture` +
  `Tessellator`/`BufferBuilder` quads (the manual path batching mods drop), and don't
  stash GL state across the render expecting it to reach a deferred draw.

## 4. Positioning

- Default anchor: **top-left**. Configurable per mod to any corner via an `Anchor` enum
  (`TOP_LEFT`, `TOP_RIGHT`, `BOTTOM_LEFT`, `BOTTOM_RIGHT`) plus pixel `offsetX`/`offsetY`
  (default 4px from each edge).
- Stacking applies within an anchor: a lower-priority element placed at the same anchor
  as a visible higher-priority sibling offsets past it.
- **Canonical config surface.** The three positioning controls carry the same option names
  and labels in every mod, so the config screen reads identically: `hudAnchor` → **"HUD
  Anchor"** (the `Anchor` enum, values labelled "Top Left" / "Top Right" / "Bottom Left" /
  "Bottom Right"), `hudOffsetX` → **"HUD Offset X"**, `hudOffsetY` → **"HUD Offset Y"**. The
  badge's own on/off toggle is domain-named on the pattern **"Show `<Domain>` HUD"** (e.g.
  "Show Tier HUD", "Show Reputation HUD").

## 5. Visibility rules

Hidden during all of:
- F1 (HUD toggle)
- any open screen/GUI
- spectator mode
- the death screen

All four are implemented in the reference overlay; all four are required.

## 6. Coordination mechanism (the part that keeps mods independent)

There is **no shared HUD manager and no shared library** — each mod renders its own
element and computes its own offset. Coordination happens through two **client-safe API
accessors** that every HUD-bearing mod exposes in its `api` package, per
[`API-STANDARD.md`](API-STANDARD.md) §5:

```java
// reflection-backed, safe to call when the mod is absent
boolean isHudVisible();   // false if mod absent, HUD config-disabled, or hidden
int     getHudHeight();   // element height PLUS the 2px stack gap (22 for a standard element); 0 if not visible
```

Each mod's offset = sum of `getHudHeight()` over all *higher-priority* mods that are
loaded, queried per render pass (cheap reads of synced client state). Hardcoded sibling
heights and bare `isModLoaded` displacement are non-conformant as a *primary* mechanism:
they go stale the moment the user disables or moves the sibling's HUD.

**The legacy fallback is conformant.** A sibling released before it exposed the
accessors has no `getHudHeight()` to read, and a consumer must still lay out against
it. Resolve the accessors reflectively once, and when the class or methods are absent,
fall back to a named fixed reservation so behavior against those older releases is
unchanged:

```java
if (!FabricLoader.getInstance().isModLoaded(SIBLING_ID)) return 0;
resolveOnce();
if (isHudVisibleHandle == null || getHudHeightHandle == null) {
    return LEGACY_FIXED_OFFSET;   // pre-accessor sibling; documented, not guessed
}
```

Two conditions make it conformant rather than a hardcode: the accessors are tried
*first* on every resolve, and the constant is documented as pre-accessor behavior for
a specific sibling — not a general assumption about its layout. Mercantile
(`ReputationHudOverlay.TribulationOffset`) and Prosperity are the reference
implementations. The fallback retires once every release in the wild exposes the
accessors.

The ~80 lines of offset logic are deliberately duplicated per mod — convention over
dependency (`VISION.md` §8.1).

## 7. Reference implementation

`tribulation/src/client/java/com/rfizzle/tribulation/client/TribulationHudOverlay.java`
— anchor enum + offsets as the flat `hudAnchor` / `hudOffsetX` / `hudOffsetY` fields on
`TribulationConfig` (a nested `Hud` section was flattened by its migrator), glyph at
`assets/tribulation/textures/gui/hud_icon.png`, tier tints, progress bar, level-up lerp,
and all four visibility rules.

## 8. Hold-to-peek detail panel

An optional on-demand companion to the slot badge: the badge says *roughly* where the
player stands, the panel says *everything*. It is a HUD surface, not a `Screen`.

- **Trigger.** A `KeyMapping` under Controls → `<Mod>`, named "Peek `<Domain>` Detail" (e.g.
  "Peek Tier Detail", "Peek Reputation Detail"). Shown only while the key is held; released,
  it dismisses. **Default: Left Alt** (`GLFW_KEY_LEFT_ALT`) — unused by vanilla and ergonomic
  to hold. Never bind it to Tab: Tab holds the vanilla player list, the exact interaction this
  panel imitates, so the two would conflict. New keybinds use the key `key.<mod>.peek_detail`;
  a shipped mod may keep an existing key id to avoid resetting players' rebindings.
- **Title.** The panel header is the keybind label minus "Peek " — **"`<Domain>` Detail"**
  (e.g. "Tier Detail", "Reputation Detail", "Loot Detail"), lang key `hud.<mod>.detail.title`.
  Never the mod's own name: the header names the panel's *content*, so it reads as the same
  feature as the keybind that opens it.
- **Non-capturing.** It behaves like vanilla's hold-Tab player list — it never captures the
  mouse, pauses the game, or blocks movement. It is drawn from a `HudRenderCallback`, never
  by opening a `Screen`.
- **Visibility.** Governed by the **same four rules as the badge** (§5); reuse the badge's
  visibility predicate rather than re-deriving it.
- **No slot, no coordination.** The panel is transient, so it takes **no slot-registry row
  (§2) and no `isHudVisible()`/`getHudHeight()` accessors (§6)** — it is never stacked.
  Anchor it adjacent to the mod's badge.
- **Framing.** A framed panel (9-slice) in the mod's theme; **vanilla font only** (§3):
  a header expanding the badge's headline stat, the relevant progress, and the mod's domain
  detail.
- **Proximity element.** Any "what's around me right now" listing is built from a **cached,
  throttled scan** (refreshed on a tick interval, not per frame) so the render path stays a
  lookup, not an entity sweep.
- **Overflow pages, never scrolls.** A non-focused HUD layer cannot scroll without capturing
  input, so overflow is **paged with a cross-fade and page dots**, not a scrollbar.
- **It cannot lie.** Every figure is derived from the same config/registry the server acts
  on (the same source the badge and `/`-commands read), never a parallel copy.
- **It does not duplicate the catalog.** Possible-loot / possible-reward listings live in
  the recipe viewers (EMI/REI/JEI) and tooltips (Jade/WTHIT); the panel is the *live,
  contextual* view — current state and what is physically around the player — not a static
  index of what *could* appear.
- **Class convention.** `*DetailPanelRenderer` (a `HudRenderCallback`).

Reference implementations: Tribulation's `TierDetailPanelRenderer`, Mercantile's
`ReputationDetailPanelRenderer`.

## 9. Conformance checklist

- [ ] Slot registered in §2 of this file (or explicit no-slot decision recorded in the
      mod's `design/DESIGN.md`)
- [ ] 20px element + 2px gap; visual spec per §3; vanilla font only
- [ ] Every HUD render pass ends with `graphics.flush()` and draws only through
      `GuiGraphics` (ImmediatelyFast / Blur+ compatibility, §3)
- [ ] Glyph is a purpose-built texture with its `.glyph` source committed beside the
      master (DESIGN-SYSTEM §8) — not a downscaled vanilla item
- [ ] Anchor + pixel-offset config; default top-left, 4px
- [ ] All four visibility rules implemented
- [ ] `isHudVisible()` / `getHudHeight()` exposed in the `api` package,
      reflection-safe from common code
- [ ] Offset computed from sibling accessors — no hardcoded sibling heights
- [ ] A hold-to-peek detail panel (if any) follows §8: "Peek `<Domain>` Detail" keybind
      defaulting to Left Alt (never Tab), "`<Domain>` Detail" header, non-capturing (not a
      `Screen`), the badge's four visibility rules reused, no slot/accessors, paged (not
      scrolled) overflow, and no duplication of recipe-viewer/tooltip catalogs
- [ ] `AGENTS.md` declares "conforms to Concord HUD Standard"
