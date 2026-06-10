# Concord API Standard — v1

> Normative for every Concord member mod. Generalized from Tribulation's
> `com.rfizzle.tribulation.api` package, the collection's reference implementation.
> Rationale and the cross-mod integration matrix live in [`VISION.md`](VISION.md) §5.

## 1. Scope

This standard governs how a Concord mod exposes functionality to sibling mods and
third parties, and how it consumes a sibling's. It exists so that integration is
**additive and optional, never load-bearing**: no member may ever require another to
load, and no feature may silently break when a sibling is absent.

## 2. The package rule

Each mod publishes exactly one stable surface: **`com.rfizzle.<mod>.api`**.

- Everything inside `api` is stable and documented; everything outside it is internal
  and may change without notice in any release.
- `api` classes are annotated `@ApiStatus.Stable`. Internal classes that tooling might
  surface should carry `@ApiStatus.Internal`.
- Entity/player data attachments, mixin interfaces, and manager classes are **not** API
  even when technically public — if a sibling needs the data, the owning mod adds an
  accessor to its `api` package.

## 3. Read-only by default

Static accessors return values; nothing in an `api` package mutates the owning mod's
state. The single sanctioned mutation pattern is **provider/callback registration**:

- The host mod defines a functional interface and a registration point
  (e.g. `TribulationAPI.setArmorDropChanceProvider(...)`), or fires an event carrying a
  mutable context object (e.g. Prosperity's `LootModifierContext` with
  `addLuck`/`multiplyStacks`).
- The host calls *out* at a defined moment; the guest adjusts the context. The guest
  never reaches into the host.
- **Error isolation is the host's job**: a provider that throws or returns a non-finite
  value is caught and the host falls back to its configured default. A misbehaving
  integration must never crash or corrupt the host.
- Provider slots use last-writer-wins `volatile` semantics unless the host documents
  otherwise.

## 4. Consumption pattern

Soft dependency only, no exceptions:

```gradle
dependencies {
    modCompileOnly "maven.modrinth:tribulation:<version>"
}
```

```java
if (FabricLoader.getInstance().isModLoaded("tribulation")) {
    // Only here may com.rfizzle.tribulation.api.* be referenced
    int level = TribulationAPI.getLevel(serverPlayer);
}
```

- Every call site is guarded by `FabricLoader.getInstance().isModLoaded("<modid>")`,
  or lives in a class that is only classloaded behind such a guard.
- Integration code lives in `compat/<modid>/` packages that fail gracefully when the
  target is absent.
- Conditional *data* (recipes, trade entries, loot injections that reference a
  sibling's items) uses Fabric resource conditions keyed on the sibling's mod id.

## 5. Client-safe accessors

Anything callable from common code that reads client state is **reflection-backed**
and returns a documented sentinel when unavailable (reference:
`TribulationAPI.getClientLevel()` → `-1`). It must be safe to call unconditionally
from common code on either side. The HUD coordination accessors required by
[`HUD-STANDARD.md`](HUD-STANDARD.md) (`isHudVisible()`, `getHudHeight()`) follow this
pattern.

## 6. Events

- Fabric `Event` objects, array-backed via `EventFactory.createArrayBacked`.
- Named `<Mod><Thing>Callback` (reference: `TribulationLevelCallback`).
- Fired **server-side** at state changes; the firing mod documents every trigger
  (e.g. Tribulation's level event fires on playtime progression, death relief, Shatter
  Shard use, and `/tribulation set`).
- Listeners receive old and new values where the change is scalar.

## 7. Server authority

All gameplay-affecting reads happen server-side; client accessors exist for rendering
only. Nothing in an `api` package may let a client influence server state.

## 8. Stability & versioning

- The `api` package is stable across patch and minor versions of the owning mod.
- A breaking API change requires a **major version bump** and a changelog entry naming
  the broken signature.
- Additive growth (new accessors, new events) is always allowed and is the expected
  path — design minimal, extend later.

## 9. Required surface per member

The per-mod API work items (what each mod must add to enable the integration matrix)
are tracked in [`VISION.md`](VISION.md) §5.3 and each mod's `.plan/BACKLOG.md`. In
summary: Tribulation adds boss/threshold/HUD accessors; Meridian and Mercantile promote
their de-facto surfaces into formal `api` packages with events; Prosperity builds to
this standard from its first commit.

## 10. Conformance checklist

A mod conforms to API Standard v1 when:

- [ ] All externally consumable surface lives in `com.rfizzle.<mod>.api`, annotated
      `@ApiStatus.Stable`
- [ ] No `api` method mutates mod state outside the provider/callback pattern
- [ ] All provider/callback invocations are wrapped in host-side error isolation
- [ ] The mod's own sibling integrations use `modCompileOnly` + `isModLoaded` guards in
      `compat/<modid>/` packages
- [ ] Client-reading accessors callable from common code are reflection-backed with
      documented sentinels
- [ ] Events are Fabric `Event`s named `<Mod><Thing>Callback` with documented triggers
- [ ] README has a developer/API section with the gradle + guard example (model:
      Tribulation's README)
- [ ] `AGENTS.md` declares "conforms to Concord API Standard v1"
