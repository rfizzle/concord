# Concord API Standard

> Normative for every Concord member mod. Generalized from Tribulation's
> `com.rfizzle.tribulation.api` package, the collection's shape and naming reference.
> **Tribulation does not yet meet §3.1** — its two provider slots catch `Exception`, and
> `TribulationLevelCallback` does not isolate in the invoker — which is tracked as a
> member work item. The working references for §3.1 are **Respite's** and **Instinct's**
> callbacks — the only shipped invokers that carry all three rules (`Throwable` catch,
> `VirtualMachineError` rethrow, once-gated log naming the guest). Distillation and
> Cultivation catch `Throwable` in the invoker but lack the rethrow, the gate, and the
> name; Meridian, Mercantile, Prosperity, and Tribulation catch `Exception` or nothing.
> Rationale and the cross-mod integration matrix live in
> [`VISION.md`](VISION.md) §5.

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

1. **Catch `Throwable`, never `Exception` — but rethrow `VirtualMachineError`.** A
   consumer compiled against an older signature surfaces the mismatch as an `Error` —
   `AbstractMethodError`, `NoClassDefFoundError`, `LinkageError` — which an `Exception`
   catch lets escape and kill the server tick. This is the same posture §4 already
   requires of calls *into* a sibling, and what the suite's reflection-backed accessors
   already do. The one carve-out is `VirtualMachineError`, rethrown unchanged before the
   catch body runs: an `OutOfMemoryError` or `StackOverflowError` means the JVM is
   unrecoverable, not that the guest misbehaved. Absorbing an OOME and then allocating a
   log message allocates on the heap that just failed, and rule 2's "continue" turns one
   `StackOverflowError` into one per remaining listener. None of the errors this rule
   exists for is a `VirtualMachineError`, so the carve-out costs the isolation nothing.
2. **Isolate per guest, and continue.** The `try`/`catch` wraps a single listener or
   provider invocation, so one misbehaving guest never denies the others their call.
   For events this means the `catch` lives **inside the `createArrayBacked` invoker's
   loop** (§6), not around the fire site — a fire-site wrap catches the throw but
   abandons every listener after the one that threw.

   Continuing means later guests observe whatever the thrower already applied. For a
   mutable context that is the intended trade: the host's own scalars are validated on
   every mutation, so any partial application is a valid state, and continuing recovers
   the later guests' contributions a fire-site wrap would have dropped. A context
   carrying a free-form bag for guest-to-guest exchange (Prosperity's
   `LootModifierContext#customData`) can hand a later listener a half-written record, so
   document per event which context fields survive a throw, and keep host-consumed
   fields independently validated rather than checked once at the end of the chain.
3. **Fall back to the host's default, and log once.** A provider that throws *or returns
   a non-finite value* yields the host's configured default. Log at `WARN` — a foreign
   guest throwing is the guest's defect, not a host failure — passing the `Throwable`
   itself so the stack trace survives, and naming the offending guest class so an
   unfamiliar third-party listener is tractable to diagnose.

   Gate that log behind an `AtomicBoolean.compareAndSet(false, true)`, or a windowed
   throttle where guests are identified per key. A guest that throws once throws every
   time, and an ungated log puts stack-trace formatting and appender I/O on the server
   thread at the fire site's full rate — Cultivation's harvest callback fires once per
   harvested crop block, so one explosion in a farm is a hundred traces in a single
   tick. The isolation must not cost more than the throw it absorbs.

A host that satisfies these three cannot be broken by a guest that throws, returns
garbage, or was compiled against a stale signature. It is not proof against one that
exhausts the heap, blocks forever, or calls `System.exit` — those are the JVM's problem,
and rule 1's rethrow hands them back rather than papering over them.

## 4. Consumption pattern

Soft dependency only, no exceptions:

```gradle
dependencies {
    // Sibling jars resolve from GitHub Releases through the artifact-only `rfizzle:` ivy
    // repo — the Modrinth projects are not publicly resolvable. Recipe: `mc-public-api`.
    modCompileOnly "rfizzle:tribulation:<version>"
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

### 4.1 `fabric.mod.json` dependency shape

The gradle side of a soft dependency is only half of it — the manifest has to agree, or
the loader hard-fails on a mod the code was written to live without. Every member's
`fabric.mod.json` must declare:

| Key | Value | Why |
|---|---|---|
| `depends.minecraft` | `"~1.21.1"` | Tolerates a patch bump without a manifest edit in eight repos |
| `depends.fabricloader` | `">=0.16.10"` | Floor, not a pin — loader is backward compatible |
| `depends.fabric-api` | `"*"` | The real floor is the gradle pin (see below) |
| `depends.java` | `">=21"` | Matches the toolchain |

All eight members carry this shape. Meridian was the last deviation — exact
`"1.21.1"`, a bounded `fabric-api`, and `tribulation` under `recommends` with a
version floor — and adopted the standard shape in rfizzle/meridian#287.

`fabric-api` is unbounded on purpose. The version that actually matters is
`fabric_version` in [`propagate/versions-common.properties`](propagate/versions-common.properties),
which is what the mod compiles against and what the suite bumps in one place. Restating
that floor in eight manifests gives it eight chances to drift from the pin it is
supposed to mirror, and the manifest copy is the one nobody updates.

**A sibling is never a hard dependency, and never a recommendation.** It goes under
`suggests` with `*`:

```json
"suggests": {
  "tribulation": "*"
}
```

- Not `depends` — that is the load-bearing coupling §1 forbids.
- Not `recommends` — the loader surfaces a recommendation as something the player ought
  to install, which is a claim the integration cannot support. Every Concord feature
  works fully with the sibling absent; a sibling adds, it does not complete.
- Not a version floor. A floor says the integration breaks below it, but §4's guards and
  §3.1's isolation mean an older sibling degrades to un-integrated behavior instead of
  breaking. The manifest should not assert a hard edge the code does not have.

Third-party viewers and config UIs (Jade, WTHIT, EMI, REI, JEI, Mod Menu, Cloth Config)
follow the same rule for the same reason — see the `mc-compat` skill.

## 5. Client-safe accessors

Anything callable from common code that reads client state is **reflection-backed**
and returns a documented sentinel when unavailable (reference:
`TribulationAPI.getClientLevel()` → `-1`). It must be safe to call unconditionally
from common code on either side. The HUD coordination accessors required by
[`HUD-STANDARD.md`](HUD-STANDARD.md) (`isHudVisible()`, `getHudHeight()`) follow this
pattern.

## 6. Events

- Fabric `Event` objects, array-backed via the **two-argument**
  `EventFactory.createArrayBacked(Class, Function)`. **Never the three-argument
  overload** (`Class, emptyInvoker, Function`): with exactly one listener registered it
  uses that listener *as* the invoker and never calls the factory, so the isolation
  below silently disappears in the single-listener case — the common one. Fabric's own
  Javadoc recommends that overload for performance-critical events; the suite trades the
  micro-optimization for isolation that always holds.
- Named `<Mod><Thing>Callback` (naming reference: `TribulationLevelCallback`).
- Fired **server-side** at state changes; the firing mod documents every trigger
  (e.g. Tribulation's level event fires on playtime progression, death relief, Shatter
  Shard use, and `/tribulation set`). Fire on the server thread. A fire site on a
  reload worker or a `CompletableFuture` stage needs its own analysis, since a caught
  `Throwable` there leaves state half-initialized with no tick to retry on.
- Listeners receive old and new values where the change is scalar.
- **The invoker isolates each listener** per §3.1 — the `try`/`catch (Throwable)` lives
  inside the `createArrayBacked` loop, so one listener throwing does not deny the rest
  their call. Fire sites then stay clean: when isolation moves into the invoker, delete
  the fire-site wrap rather than leaving it as belt-and-braces, since it can only
  re-introduce the abandon-the-rest semantics the invoker exists to prevent. Isolation
  is a property of the event, declared once where the event is, rather than a discipline
  every fire site has to remember.

The block below is the standard's **model shape**, not a transcript of a shipped class.
Cultivation's real `CultivationHarvestCallback` catches `Throwable` but has no
`VirtualMachineError` rethrow, no once-gate, and does not name the guest (it logs at
ERROR, once per harvested block) — that gap is member work, tracked in its repo.
Respite's `RespiteRestCallback` and Instinct's callbacks ship this shape verbatim.

```java
/**
 * Fired server-side from the harvest choke point on every path that reaps a supported
 * crop — player, piston, water, explosion, scythe, villager — and on a sweet-berry pick,
 * which leaves the bush standing. The {@code drops} list is mutable and is the
 * sanctioned mutation point.
 *
 * <p>A listener that throws is caught, logged, and skipped; it can never break the
 * harvest or the listeners registered after it.
 */
@Stable
public interface CultivationHarvestCallback {

    AtomicBoolean LISTENER_FAILURE_LOGGED = new AtomicBoolean(false);

    Event<CultivationHarvestCallback> EVENT = EventFactory.createArrayBacked(
            CultivationHarvestCallback.class,
            listeners -> (level, pos, crop, drops, harvester) -> {
                for (CultivationHarvestCallback listener : listeners) {
                    try {
                        listener.onHarvest(level, pos, crop, drops, harvester);
                    } catch (VirtualMachineError e) {
                        throw e;                  // OOME/SOE: the JVM is gone, not the guest
                    } catch (Throwable t) {
                        // Throwable, not Exception: a listener compiled against an older
                        // signature throws Error (AbstractMethodError, NoClassDefFoundError),
                        // which an Exception catch would let escape and kill the server tick.
                        // Once-only: this fires once per harvested block, so an ungated log
                        // would put stack-trace formatting on the server thread at that rate.
                        if (LISTENER_FAILURE_LOGGED.compareAndSet(false, true)) {
                            Cultivation.LOGGER.warn("CultivationHarvestCallback listener {} threw; skipping it",
                                    listener.getClass().getName(), t);
                        }
                    }
                }
            });

    void onHarvest(ServerLevel level, BlockPos pos, BlockState crop, List<ItemStack> drops,
            @Nullable Entity harvester);
}
```

The event's Javadoc states the isolation posture so a consumer knows what a throw costs
them: *"A listener that throws is caught, logged, and skipped — it can never break `<the
host operation>` or the listeners registered after it."* Any Javadoc that promises less
is a defect in one or the other: fix the code, then fix the promise. That covers both a
Javadoc that **disclaims** isolation (Respite's formerly read "a listener that throws is
not isolated by Respite"; it now states full isolation) and one that promises the old
**fire-site** posture (Mercantile's `TradeExecutedCallback` still reads "it may prevent
listeners registered after it from seeing that trade") — both describe behavior this section no
longer permits.

### 6.1 Grandfathered names

Three events shipped before the `<Mod><Thing>Callback` rule was enforced. They are
`@Stable` and present in every tagged release of their mod, so §8 binds them: renaming
is a breaking change and waits for the next major. They are **waived, not conformant** —
a conformance sweep records the waiver here and does not re-flag it, and the waiver dies
with the rename.

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

Each row is carried by an open issue in the owning mod's repo — the durable tracker §9
already names — labelled `breaking` and titled "rename `<OldName>` to `<NewName>`
(API-STANDARD §6.1)". A waiver with no owner and no trigger never expires, so the row
and the issue are filed together. The issue carries the rename per §8:

- Add the prefixed type; the old name either delegates to it or is replaced outright.
- Mark the old name deprecated for the release that still carries it.
- The changelog entry names the broken signature.

When a rename ships, delete its row. An empty register means the waiver is spent.

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
summary: every member's `api` package has shipped and is in a tagged release (the last
four landed with the 2026-08 betas). Prosperity's `LootModifierCallback` predates the
invoker-isolation rule and its name is grandfathered (§6.1), so "built to this standard
from its first commit" is not a claim the suite can make; the open work is §3.1
retrofits in Tribulation, Meridian, Mercantile, and Prosperity, tracked in each repo's
conformance sweep.

## 10. Conformance checklist

A mod conforms to the API Standard when:

- [ ] All externally consumable surface lives in `com.rfizzle.<mod>.api`, annotated
      with the mod's local `@Stable` marker (see §2 erratum)
- [ ] No `api` method mutates mod state outside the provider/callback pattern
- [ ] Every provider/callback invocation is isolated per §3.1 — `catch (Throwable)` with
      `VirtualMachineError` rethrown, per guest, falling back to the host's default,
      logging once at `WARN`; event isolation lives in the two-argument
      `createArrayBacked` invoker, not at the fire site
- [ ] The mod's own sibling integrations use `modCompileOnly` + `isModLoaded` guards in
      `compat/<modid>/` packages, with foreign references classload-isolated (adapter
      class or nested `Api` holder) and whole integration bodies catching `Throwable`
- [ ] `fabric.mod.json` carries the §4.1 dependency shape, with any sibling under
      `suggests`
- [ ] Compat mapping/scaling cores are pure (zero sibling imports) and unit-tested
      without the sibling jar on the classpath
- [ ] Client-reading accessors callable from common code are reflection-backed with
      documented sentinels
- [ ] Events are Fabric `Event`s named `<Mod><Thing>Callback` with documented triggers,
      or hold a row in the §6.1 grandfather register
- [ ] README has a developer/API section with the gradle + guard example (model:
      Tribulation's README)
- [ ] `AGENTS.md` declares "conforms to Concord API Standard"
