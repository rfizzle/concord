# Handoff: Collective Vision & Roadmap for the Vanilla+ Overhaul Collection

> Prompt for Fable 5. Takes a high-level look at the four-mod rfizzle collection and
> produces a unified vision statement, a cross-mod roadmap, and the shared standards
> (design system, narrative, integration architecture) that bind the mods into a suite
> while keeping each one independently installable.
>
> Fable: you are encouraged to use **sub-agents** for the research phase — spin up one
> per mod to deep-read its repo in parallel, then synthesize their structured profiles
> into the collective vision yourself. Do not write the synthesis until all four profiles
> are in hand.

---

## What this is

The **rfizzle Vanilla+ Overhaul Collection** is four independent Minecraft 1.21.1 Fabric
mods, each overhauling one vanilla system. They are designed to be installed à la carte —
any one alone, any combination, or all four — and to *light up extra integration* when
their siblings are present, without ever hard-depending on each other.

| Mod | Domain | Color signature | Maturity |
|-----|--------|-----------------|----------|
| **Meridian** | Enchanting | Violet / Gold | Implemented (mod + docs) |
| **Mercantile** | Villagers & Trade | Green / Emerald | Implemented (mod + docs) |
| **Tribulation** | Difficulty & Scaling | Crimson / Red | Implemented (mod + docs); furthest along on the public-API pattern |
| **Prosperity** | Loot & Containers | Gold / Diamond-Cyan | **Greenfield** — `DESIGN.md` + `SPEC.md` + art only, not yet coded |

The four mod repos are sibling directories of the current working directory:
`./meridian`, `./mercantile`, `./tribulation`, `./prosperity`.

## The architectural thesis (the spine of the whole collection)

Every recommendation must reinforce these principles. They are the reason the collection
is a *suite* and not a *modpack*:

1. **Independent gates.** Each mod is fully functional standalone. No mod requires another
   to load, and no feature silently breaks when a sibling is absent. Every cross-mod
   behavior is guarded by `FabricLoader.getInstance().isModLoaded(...)`.
2. **Siloed functionality.** Each mod owns exactly one vanilla system. No scope bleed —
   enchanting logic lives only in Meridian, loot instancing only in Prosperity, etc.
   Overlapping ideas get assigned to the correct silo, not duplicated.
3. **Exposed public APIs for integration.** Following the route Tribulation has taken
   (read-only `TribulationAPI` + a level-change event, consumed via `modCompileOnly`),
   each mod publishes a stable, documented, read-only-by-default API and event surface so
   siblings — and third-party mods — can integrate. Integration is *additive and optional*,
   never load-bearing.
4. **Vanilla+ throughout.** Everything feels like it could have shipped in vanilla
   Minecraft. Reuses vanilla mobs, items, blocks, and visual language. No new dimensions,
   no RPG skill trees, no HUD clutter, no wiki required to play. Server-friendly and
   multiplayer-fair.

## Required reading

For **each** mod repo (delegate one sub-agent per mod):
- `README.md` — feature summary and any developer/API section
- `DESIGN.md` (Tribulation's is at `tribulation/docs/design/DESIGN.md`; Meridian/Prosperity
  keep it at their repo root; Mercantile may not have one — discover what's present)
- `SPEC.md` where present (Prosperity has the fullest spec since it's pre-implementation)
- `docs/*.html` — published feature/config/command surface
- `src/main/java/...` — skim the real implementation; for the three coded mods, confirm
  the docs match reality and locate the existing public API / event classes (e.g.
  `com.rfizzle.tribulation.api.*`). For Prosperity, read the spec's architecture section
  (CCA-based, zero-trust proxy over vanilla containers).
- `CLAUDE.md` / `AGENTS.md` — conventions, source layout, lifecycle (shared across the suite)

Ground every claim in source, not marketing copy.

## Research phase (sub-agents)

Spawn one research sub-agent per mod. Each returns a **structured Mod Profile**:
- **Domain & silo boundary** — what it owns; what it deliberately does *not* touch
- **Current feature surface** — implemented vs. specced vs. aspirational
- **Public API & events** — what's already exposed; what a sibling could consume today;
  what's missing to make it integratable
- **Narrative & brand** — tagline, motif, color palette, voice
- **Integration hooks** — concrete points where a sibling mod could meaningfully plug in
  (e.g. Tribulation's scaling tier as an input to Prosperity's loot quality)
- **Gaps & risks** — un-vanilla edges, balance concerns, MP-fairness issues, maturity gaps

Then **you** (not a sub-agent) synthesize the four profiles into the deliverable below.

## Deliverable

A single structured markdown document with these sections. Treat each `##` as a required,
clearly-labeled section.

### 1. Collective Vision Statement
2–4 paragraphs. What is the rfizzle Vanilla+ Overhaul Collection *as a whole*? What unified
player promise do the four mods make together that none makes alone? Why à-la-carte +
optional-integration is the right shape. Give the collection a one-line tagline that sits
above the four individual taglines.

### 2. Narrative & Naming
How the four narratives (Survive / Enchant / Trade / Discover) relate. The collection's
name and positioning. The voice and tone shared across all marketing and in-game text.

### 3. Shared Design System
The cross-mod visual language. Consolidate what already exists (each mod's palette, the
dark website theme, the bone/ash/smoke text palette, the monospace stack, the pixel-art
logo style) into one design system:
- **Color palettes** — each mod's signature + the shared neutral/surface tokens; how they
  coexist when multiple mods are installed
- **Typography, logos, iconography** — the shared rules and the per-mod variations
- **Shared HUD standard** — elevate Tribulation's existing "Shared HUD Element Standard"
  (priority-ordered, stackable, togglable top-left strip) into a collection-wide spec, and
  assign each mod its HUD slot and content

### 4. Website & Distribution
The shared website structure (hero → features → config → commands), cross-mod navigation
footer, domain pattern (`<mod>.rfizzle.com`), SEO/social conventions, and CurseForge/Modrinth
listing standards. Recommend whether a collection-level landing site/page is warranted.

### 5. Integration Architecture
The heart of the document. Define the **public-API + event pattern** as a suite standard,
generalizing Tribulation's approach:
- API conventions: read-only by default, `modCompileOnly` consumption, `isModLoaded` guards,
  client-safe accessors, versioning/stability expectations
- A **cross-mod integration matrix**: for each ordered pair of mods, the concrete, Vanilla+
  integration points worth building (e.g. Tribulation tier → Prosperity loot quality;
  Mercantile reputation → Meridian enchant access; etc.). Mark each as
  High/Med/Low value and note which side exposes what.
- What API surface each mod must *add* to enable the matrix (Prosperity's can be designed
  from scratch; the other three may need additions)
- Third-party integration story: how an outside mod consumes the suite

### 6. Per-Mod Roadmap
For each of the four mods, a prioritized (High/Med/Low) roadmap of features and API work.
Keep each mod strictly in its silo. For Prosperity, this is effectively a build plan from
its spec. For the other three, this is incremental evolution + the API additions from §5.
Every item carries: one-line pitch, why it's Vanilla+, suite-fit / silo note, and rough
implementation sketch (vanilla systems / mixins / events touched).

### 7. Cross-Cutting Roadmap & Sequencing
The work that spans mods: the shared design system rollout, the shared HUD library, the
API/event standard, the website system, Prosperity reaching parity. Recommend a sequence
and call out dependencies (e.g. "Tribulation's tier API must stabilize before Prosperity
consumes it").

### 8. Explicitly Out of Scope
Tempting ideas you rejected, with reasons: wrong silo, not Vanilla+, hard-dependency risk,
MP-unfair, or too costly. Protecting the thesis is as valuable as extending it.

### 9. Additional Areas for Overhaul Evaluation
Look beyond the current four silos and identify *other vanilla Minecraft systems* that would
benefit from a dedicated overhaul in the same manner — a coherent, Vanilla+, independently-
installable, API-exposing mod that could become a fifth, sixth, etc. member of the collection.
Survey the vanilla feature surface (e.g. exploration/structures, farming & food, mining &
caves, redstone/automation, mobs & breeding, world generation, status effects, the weather/
time/seasons axis, transportation, building blocks & decoration, the nether/end progression)
and for each *candidate worth pursuing* give:
- **Proposed silo & domain boundary** — the one vanilla system it owns; what it must *not*
  touch to avoid overlapping the existing four
- **The vanilla pain point** it overhauls and the Vanilla+ thesis for fixing it
- **Candidate narrative & motif** — a working name, tagline, color signature, and how it
  would slot into the shared design system
- **Integration potential** — concrete hooks into the existing four mods via the public-API
  pattern (e.g. how it would consume Tribulation's tier or feed Prosperity's loot)
- **Fit/priority verdict** — High/Med/Low, with the reasoning, and an explicit note if it
  risks scope-bleed into an existing silo or fails the Vanilla+ / independence / MP-fairness
  tests. Rejected candidates belong in §8; only carry forward the ones genuinely worth a slot.

Rank the surviving candidates so the maintainer has a clear "what comes after Prosperity" shortlist.

## Style
Concrete over aspirational. Name vanilla mobs, items, blocks, and mechanics specifically.
Prefer a tight set of strong, coherent recommendations over an exhaustive brainstorm.
Assume the reader knows Minecraft deeply, owns all four repos, and is allergic to bloat and
to hard inter-mod dependencies.
