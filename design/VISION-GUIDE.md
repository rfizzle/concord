# Vision Guide — a member mod's `design/VISION.md`

Every member mod carries a `design/VISION.md`: the mod's promise to the
player. Someone who plays Minecraft but has never opened a line of code
should finish it knowing exactly what the mod wants to do, every headline
feature, what the experience feels like over a world's life, and how they
will use each feature in-game. It is the first document a new reader opens,
and the yardstick incoming feature requests are measured against.

## Where it sits among the docs

| Document | Question it answers | Reader |
|---|---|---|
| `design/VISION.md` | What does playing with this feel like, and why would I want it? | a player |
| `design/SPEC.md` | What exactly happens — rules, numbers, edge cases? | the implementer |
| `design/DESIGN.md` | How does it look, sound, and read — brand, palette, motifs? | the designer |
| `design/ASSETS.md` | Where does every committed asset live? | the maintainer |
| `README.md` / `site/` | What is shipped today, and how do I install it? | a player, about the present |

Each `design/` doc has its own authoring guide beside this one
(`SPEC-GUIDE.md`, `DESIGN-GUIDE.md`, `ASSETS-GUIDE.md`).

**This document owns** the promise, the arc, each feature as an experience —
what it is, how you use it, what changes for you — and the player-facing
boundaries. **It defers** the authoritative rules and values to `SPEC.md`
(the vision quotes headline numbers; the spec is where they live), the brand
— motif, palette, logo — to `DESIGN.md`, every file's whereabouts to
`ASSETS.md`, and the description of what is currently shipped to the README
and site.

The vision sits upstream: SPEC turns its promises into exact behavior,
DESIGN gives them a face, and the site markets whatever part has shipped. A
feature that contradicts the vision is reshaped or declined — or the vision
is amended first, deliberately. It is never silently outgrown.

The suite-level counterpart is concord's [`VISION.md`](../VISION.md): one
domain per mod, standalone always, siblings optional (§1), with the hard
out-of-scope lines in §8. A member's vision lives inside the silo the suite
grants it; the "will never do" section of the template below is where the
member draws those edges in its own player-facing words.

## The one hard rule: written for a player

The vision contains **zero implementation vocabulary**. If understanding a
sentence requires knowing how mods are built, the sentence is not too
detailed — it is wrong.

**Never appears:** mixin, packet, payload, codec, registry, mapping, API,
callback, event, attachment, NBT, cache, thread, tick budget, class or
package names, config key names, source set, Gradle, datagen — any word
whose home is the codebase rather than the game.

**Free to use** — players see these in play: item, block, and mob names;
screens and menus; commands (`/prosperity where`); config options described
by what they change ("the badge can be turned off"); HUD, tooltip, keybind;
singleplayer, multiplayer, server; worlds, dimensions, biomes; drop chances,
distances, durations.

The acceptance test: hand the document to someone who plays Minecraft and
does not mod it. They should be able to retell every feature and how they
would use it. Any sentence that makes them ask "what's a ___?" fails.

## Voice

The suite voice (concord `VISION.md` §2), applied to a player-facing page:

- **Mechanically precise.** Real numbers over adjectives: "a 0.5% drop
  chance from scaled mobs", never "a rare drop". Every quantity a player
  would plan around is a number or a range — quoted from `SPEC.md`, which
  owns them; when the two disagree, the spec and code win and the vision
  updates.
- **Vanilla-deferential.** The mod completes vanilla; nothing reads as
  "vanilla is broken".
- **Second person, present tense.** What *you* do and what happens: "stand
  within four blocks and the orbs drift to the table instead."
- **Mythic accent, sparingly.** The mod's one motif register may color the
  tagline and a flavor line; body text stays concrete.
- **Quoted in-game text is vanilla-toned** — short, dry, no exclamation
  points.

## The shape

Fixed name `design/VISION.md`, target 60–120 lines — a five-minute read:

```markdown
# <Mod> — Vision

> *"<tagline>"* — <one supporting line: the domain, in plain words.>

## The promise
<3–5 sentences. Name the one vanilla system this mod takes over and what
your game becomes with it installed. A player should be able to decide
"this is for me / not for me" from this paragraph alone.>

## The arc of a world
<How a playthrough feels: what you notice in the first hours, what you are
working toward in the mid game, what mastery looks like in the late game.
Progression told as time and play, not as systems.>

## The features, as you'll play them
<One subsection per headline feature — usually 3–7. Each answers three
questions, in order. A feature that cannot fill all three is not ready to
be promised:>

### <Feature name, in game words>
- **What it is** — one or two sentences, game terms only.
- **How you use it** — the literal actions: what you place, right-click,
  type, hold, trade, or walk toward.
- **What changes for you** — the payoff, and the cost or tradeoff if
  there is one.

## Staying in control
<Every lever a player or server owner has, described by effect: what can
be toggled off (the HUD badge, whole features), what commands exist and
what they tell you, what the defaults assume. Promise what stays untouched
for a player who changes nothing.>

## Better together
<One line per sibling Concord mod this mod lights up with, phrased as an
in-game experience and ending with the standing promise: never required.
State plainly that with no siblings installed, nothing is missing.>

## What <Mod> will never do
<The mod's edges as promises: the systems it will not touch (naming the
sibling that owns them, where one does), no new dimensions, no required
companions, nothing that clutters your screen. A feature request that
collides with this section is declined or reshaped — or this document is
amended first, deliberately.>
```

## Worked example

The same feature, told two ways:

> ✗ "A `playerTouch` mixin intercepts experience orbs inside the table's
> bounding box and routes their value through `AttunementManager`,
> persisted as a player attachment."

> ✓ "Experience finds the table before it finds you: stand within four
> blocks of your enchanting table and orbs drift to it instead, banking
> their full value toward your next enchantment."

Both are true of the same code. Only the second belongs in a vision.

## Checklist before committing

- [ ] A non-modding player could retell every feature and how to trigger it.
- [ ] Zero implementation vocabulary anywhere in the file.
- [ ] Every feature answers all three: what it is, how you use it, what
      changes for you.
- [ ] Every quantity a player would plan around is a number or a range.
- [ ] "What <Mod> will never do" draws the silo edges from concord's
      `VISION.md`, in player words.
- [ ] Sibling mentions are experiences, each marked never required.
- [ ] Tagline present, in the suite register.
- [ ] 60–120 lines — a five-minute read.

## How the suite uses it

- The vendored `/implement` command reads it in its domain gate — an issue
  that collides with "What <Mod> will never do" stops the pipeline for a
  human decision — and its player-experience review judges the shipped diff
  against the promises made here.
- The vendored `/align` command sweeps it (`vision` target): factual claims
  are checked against the code, promises are adjudicated rather than
  rewritten, and a mod without a `VISION.md` gets one scaffolded from this
  guide in `--fix` mode.
- `site/` copy (hero, feature cards, store listings) paraphrases the
  promise; when the site and the vision drift, one of them is wrong.
- When behavior changes by design, the vision changes in the same PR — it
  states the current promise, never a history of promises.
