# Concord HUD Standard — v1

> Normative for every Concord member mod that renders a persistent HUD element.
> Elevated from Tribulation's DESIGN.md "Shared HUD Element Standard"; Tribulation's
> `TribulationHudOverlay` is the reference implementation.

## 1. Whether a mod gets a slot at all

A mod takes a HUD slot **only if it has persistent ambient state the player needs while
walking around** (a level, a standing, a tier that changes as you play). Everything else
belongs in screens, tooltips (Jade/WTHIT), or recipe viewers. Opting out is conformant —
Meridian has no slot by design. Future members default to **no slot**.

## 2. Slot registry

Fixed priority order, top to bottom. Elements shift up to fill gaps when a
higher-priority mod is absent or its HUD is disabled.

| Slot | Mod | Content |
|---|---|---|
| 1 | Tribulation | 16×16 skull glyph tinted by tier, 2px level-progress bar |
| 2 | Mercantile | Reputation tier label, emerald/bell glyph |
| 3 | Prosperity | Current loot distance tier, chest glyph, tier-color tint |
| — | Meridian | No slot, by design |

New slots are assigned here, in this file, by appending — never by renumbering.

## 3. Visual spec

- Container: semi-transparent black box, `#000000` at 50–60% opacity, 2px rounded
  corners.
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
- The glyph is a **purpose-built 16×16 texture**, not a downscaled vanilla item render
  (those go muddy at 16px). Author it through the texture pipeline and commit its `.glyph`
  source beside the master — see [`design/DESIGN-SYSTEM.md`](design/DESIGN-SYSTEM.md) §8.

## 4. Positioning

- Default anchor: **top-left**. Configurable per mod to any corner via an `Anchor` enum
  (`TOP_LEFT`, `TOP_RIGHT`, `BOTTOM_LEFT`, `BOTTOM_RIGHT`) plus pixel `offsetX`/`offsetY`
  (default 4px from each edge).
- Stacking applies within an anchor: a lower-priority element placed at the same anchor
  as a visible higher-priority sibling offsets past it.

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
int     getHudHeight();   // contribution in px (element + gap); 0 if not visible
```

Each mod's offset = sum of `getHudHeight()` over all *higher-priority* mods that are
loaded, queried per render pass (cheap reads of synced client state). Hardcoded sibling
heights and bare `isModLoaded` displacement (Mercantile's current
`TRIBULATION_RESERVED_HEIGHT = 22`) are non-conformant: they go stale the moment the
user disables or moves the sibling's HUD.

The ~80 lines of offset logic are deliberately duplicated per mod — convention over
dependency (`VISION.md` §8.1).

## 7. Reference implementation

`tribulation/src/client/java/com/rfizzle/tribulation/client/TribulationHudOverlay.java`
— anchor enum + offsets in `TribulationConfig.Hud`, glyph at
`assets/tribulation/textures/gui/hud_icon.png`, tier tints, progress bar, level-up lerp,
and all four visibility rules.

## 8. Conformance checklist

- [ ] Slot registered in §2 of this file (or explicit no-slot decision recorded in the
      mod's `design/DESIGN.md`)
- [ ] 20px element + 2px gap; visual spec per §3; vanilla font only
- [ ] Glyph is a purpose-built texture with its `.glyph` source committed beside the
      master (DESIGN-SYSTEM §8) — not a downscaled vanilla item
- [ ] Anchor + pixel-offset config; default top-left, 4px
- [ ] All four visibility rules implemented
- [ ] `isHudVisible()` / `getHudHeight()` exposed in the `api` package,
      reflection-safe from common code
- [ ] Offset computed from sibling accessors — no hardcoded sibling heights
- [ ] `AGENTS.md` declares "conforms to Concord HUD Standard v1"
