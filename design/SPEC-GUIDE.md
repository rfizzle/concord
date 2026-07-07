# Spec Guide — a member mod's `design/SPEC.md`

Every member mod carries a `design/SPEC.md`: the behavioral contract. It
states **exactly** what the mod does — every rule, number, range, and edge
case — precisely enough that an implementer could build the mod from it and
a reviewer can call any divergence a bug. It is written *before*
implementation (the Prosperity model) and updated in the same PR whenever
behavior deliberately changes.

Where `design/VISION.md` promises the experience in player language, SPEC
defines it in engineering language — technical vocabulary belongs here.
The reader is the implementer; players read the README and site, which
paraphrase this document and must never contradict it.

**This document owns** behavior: every rule, number, edge case, config
option, command, API surface, compat guard, and test obligation — including
*when* a HUD element shows what and *when* a sound cue fires (and its
subtitle). **It defers** the experience pitch to `VISION.md`; look, sound
character, and brand to `DESIGN.md`; and asset file locations to
`ASSETS.md`.

**Truth direction** (the `/align` model): bidirectional intent. When code
and SPEC disagree, one of them is wrong — either the code has a bug or the
behavior changed deliberately and the spec must absorb it. Divergence is
adjudicated, never silently rewritten toward code.

## The shape

Fixed name `design/SPEC.md`, title `# <Mod> — Feature Spec`. Length is
whatever the mod needs — member specs run 500–1600 lines. Structure:

**Intro block** — one line of identity (domain, Minecraft version, loader),
then the standing philosophies that govern every feature below:

- **Architectural philosophy** — the structural stance a feature may never
  violate (e.g. Prosperity's zero-trust proxy: intercept vanilla containers,
  never register or replace blocks).
- **Asset philosophy** — where this mod draws its custom-vs-vanilla line for
  textures and audio, within the suite stance (concord
  `design/DESIGN-SYSTEM.md` §8–9).

**Numbered feature sections** — `## N. <Feature name>`, one per feature.
The per-feature anatomy:

- **Problem** — the vanilla gap this feature closes, 1–3 sentences. Every
  feature should trace back to a promise in `VISION.md`.
- **Behavior** — the exact player-observable rules. Multi-step mechanics as
  a numbered flow (intercept → decide → present → persist). Every quantity
  is a number, range, or formula — these are the values README, site, and
  tooltips quote, so this is where they live first.
- **Named edge-case subsections** — interactions with vanilla systems
  (hoppers, comparators, redstone, creative mode, breaking the block),
  multiplayer behavior and fairness, and failure paths (malformed data,
  missing dependency). An edge case the spec is silent on is an edge case
  the implementer decides by accident.
- **Config** — the options this feature adds: name, type, default,
  valid range.
- **Implementation Notes** — always last, clearly bounded: the key classes,
  mixins, events, attachments, and persistence seams. This is the only
  per-feature home for code shapes, and it constrains *structure*, not
  every method signature — leave room for implementer judgment.

**Cross-cutting sections** — after the features, one section each for the
surfaces that span them:

- **Configuration** — the consolidated inventory: every option with key,
  type, default, and range/validation. The config class must match this
  table exactly; `/align` and `/assess` cross-check it.
- **Commands** — syntax, arguments, permission level, output.
- **Public API** — the `com.rfizzle.<mod>.api` surface, per concord's
  `API-STANDARD.md`.
- **Compatibility** — each optional integration (siblings, Mod Menu,
  Jade/WTHIT, EMI/REI/JEI) and its guard.
- **Sound Design / Localization / HUD / Advancements** — as the mod needs
  them. Sound Design here is *triggers and subtitles* — which events cue
  sound (each cue's character and file live with `DESIGN.md`/`ASSETS.md`);
  HUD here is the element's *behavior and content*, per concord's
  `HUD-STANDARD.md` (the slot decision and visual identity live in
  `DESIGN.md`).
- **Testing Strategy** — which behaviors land in which tier (pure JUnit /
  fabric-loader-junit / gametest), per the `mc-mod-testing` skill.

## Requirements

- **Numbers are the contract.** Every tunable ships with a default and a
  range; every chance, distance, duration, and cap is stated. "Configurable"
  without a default is not specced.
- **Server-authoritative, multiplayer-honest.** Each feature states where
  its decisions run and how it behaves for multiple players; MP-fairness
  concerns are addressed in the spec, not discovered in review.
- **Respect the suite line.** Nothing in the spec may cross the mod's silo
  (concord `VISION.md` §1/§8) or require a sibling at runtime — sibling
  integration is specced under Compatibility with its `isModLoaded` guard.
- **Spec deltas flow through issues.** The issue lifecycle's per-issue
  Implementation Spec is a *delta* against this document; when the delta
  ships, this document absorbs the new behavior in the same PR.
- **State the current behavior only.** No "previously", no dated decision
  notes, no migration narratives — git is the history.

## Checklist before committing

- [ ] Intro block states the architectural and asset philosophies.
- [ ] Every feature has Problem, Behavior, edge cases, config, and
      Implementation Notes — in that order.
- [ ] Every quantity is a number, range, or formula; the Configuration
      section matches the config class field-for-field.
- [ ] Multiplayer behavior stated for every feature it could affect.
- [ ] Nothing crosses the silo or hard-requires a sibling.
- [ ] An implementer could build each feature from its section alone;
      a reviewer could fail a PR from it alone.
