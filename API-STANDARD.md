# Concord API Standard

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
- `api` classes carry a stability marker. **Erratum 2026-06-12:** this standard
  originally prescribed `@ApiStatus.Stable`, which does not exist —
  `org.jetbrains.annotations.ApiStatus` has no `Stable` member in any published
  version. The convention is instead: each mod declares a local marker annotation
  **`com.rfizzle.<mod>.api.Stable`** (an empty `@Documented` annotation in the api
  package — convention over dependency, per the suite's no-shared-jar rule) and
  applies it to every api class. Internal classes that tooling might surface still
  carry the real `org.jetbrains` `@ApiStatus.Internal`.
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
- **Error isolation is the host's job** — see §3.1. A misbehaving integration must never
  crash or corrupt the host.
- Provider slots use last-writer-wins `volatile` semantics unless the host documents
  otherwise.

### 3.1 Error isolation

Every point where the host invokes guest code — an event listener, a provider slot, a
provider chain — is a trust boundary, and the host isolates it. Three rules, all
normative:

1. **Catch `Throwable`, never `Exception`.** A consumer compiled against an older
   signature surfaces the mismatch as an `Error` — `AbstractMethodError`,
   `NoClassDefFoundError`, `LinkageError` — which an `Exception` catch lets escape and
   kill the server tick. This is the same posture §4 already requires of calls *into* a
   sibling, and it is what the suite's reflection-backed accessors already do.
2. **Isolate per guest, and continue.** The `try`/`catch` wraps a single listener or
   provider invocation, so one misbehaving guest never denies the others their call.
   For events this means the `catch` lives **inside the `createArrayBacked` invoker's
   loop** (§6), not around the fire site — a fire-site wrap catches the throw but
   abandons every listener after the one that threw.
3. **Fall back to the host's default, and log.** A provider that throws *or returns a
   non-finite value* yields the host's configured default. Log the `Throwable` itself so
   the stack trace survives; naming the offending guest class in the message makes an
   unfamiliar third-party listener tractable to diagnose.

A host that satisfies these three cannot be broken by any guest, however badly written.

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
- Named `<Mod><Thing>Callback` (naming reference: `TribulationLevelCallback`).
- Fired **server-side** at state changes; the firing mod documents every trigger
  (e.g. Tribulation's level event fires on playtime progression, death relief, Shatter
  Shard use, and `/tribulation set`).
- Listeners receive old and new values where the change is scalar.
- **The invoker isolates each listener** per §3.1 — the `try`/`catch (Throwable)` lives
  inside the `createArrayBacked` loop, so one listener throwing does not deny the rest
  their call. Fire sites then stay clean; they neither need nor should carry their own
  wrap. Isolation is a property of the event, declared once where the event is, rather
  than a discipline every fire site has to remember.

```java
@Stable
public interface CultivationHarvestCallback {

    Event<CultivationHarvestCallback> EVENT = EventFactory.createArrayBacked(
            CultivationHarvestCallback.class,
            listeners -> (level, pos, crop, drops, harvester) -> {
                for (CultivationHarvestCallback listener : listeners) {
                    try {
                        listener.onHarvest(level, pos, crop, drops, harvester);
                    } catch (Throwable t) {
                        // Throwable, not Exception: a listener compiled against an older
                        // signature throws Error (AbstractMethodError, NoClassDefFoundError),
                        // which an Exception catch would let escape and kill the server tick.
                        Cultivation.LOGGER.error("CultivationHarvestCallback listener {} threw; skipping it",
                                listener.getClass().getName(), t);
                    }
                }
            });

    void onHarvest(ServerLevel level, BlockPos pos, BlockState crop, List<ItemStack> drops,
            @Nullable ServerPlayer harvester);
}
```

The event's Javadoc states the isolation posture so a consumer knows what a throw costs
them ("A listener that throws is caught, logged, and skipped"). A callback whose Javadoc
disclaims isolation is a defect in one or the other — fix the code, not the promise.

### 6.1 Grandfathered names

Three events shipped before the `<Mod><Thing>Callback` rule was enforced. They are
`@Stable` and present in every tagged release of their mod, so §8 binds them: renaming
is a breaking change and waits for the next major. They are **conformant by exception**
— a conformance sweep records them here and does not re-flag them.

| Mod | Shipped name | Replacement at next major |
|---|---|---|
| mercantile | `TradeExecutedCallback` | `MercantileTradeExecutedCallback` |
| mercantile | `ReputationChangedCallback` | `MercantileReputationChangedCallback` |
| prosperity | `LootModifierCallback` | `ProsperityLootModifierCallback` |

This register is **closed and exhaustive** — it is not a queue. Every other event in the
suite conforms, and a new event that does not is a defect, not an entry. The exception
exists because these three were already public when the rule landed; nothing else
qualifies.

The register is scoped to **events**. §6's naming rule has never governed the other
types an `api` package holds — records, enums, extension interfaces, context objects —
so those are not violations and do not belong here.

Each mod's next-major checklist carries the rename per §8:

- Add the prefixed type; the old name either delegates to it or is replaced outright.
- Mark the old name deprecated for the release that still carries it.
- The changelog entry names the broken signature.

When a rename ships, delete its row. An empty register means the exception is spent.

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
are tracked in [`VISION.md`](VISION.md) §5.3 and each mod's GitHub Issues (the
`needs-spec` → `jules` lifecycle; `.plan/` is local-only scratch per
[`REPO-LAYOUT.md`](REPO-LAYOUT.md) and is never the durable tracker). In
summary: Tribulation adds boss/threshold/HUD accessors; Meridian and Mercantile promote
their de-facto surfaces into formal `api` packages with events; Prosperity builds to
this standard from its first commit.

## 10. Conformance checklist

A mod conforms to the API Standard when:

- [ ] All externally consumable surface lives in `com.rfizzle.<mod>.api`, annotated
      with the mod's local `@Stable` marker (see §2 erratum)
- [ ] No `api` method mutates mod state outside the provider/callback pattern
- [ ] Every provider/callback invocation is isolated per §3.1 — `catch (Throwable)`, per
      guest, falling back to the host's default; event isolation lives in the
      `createArrayBacked` invoker, not at the fire site
- [ ] The mod's own sibling integrations use `modCompileOnly` + `isModLoaded` guards in
      `compat/<modid>/` packages
- [ ] Client-reading accessors callable from common code are reflection-backed with
      documented sentinels
- [ ] Events are Fabric `Event`s named `<Mod><Thing>Callback` with documented triggers,
      or hold a row in the §6.1 grandfather register
- [ ] README has a developer/API section with the gradle + guard example (model:
      Tribulation's README)
- [ ] `AGENTS.md` declares "conforms to Concord API Standard"
