# Bootstrap Prompt — new Concord member repo

The paste-in prompt that turns an empty directory into a new member mod repo
with its `design/VISION.md` written to standard. To use it: create the repo
directory beside this one (`mkdir ~/Projects/<modname>`), start a fresh agent
session in that directory, fill in the three fields at the top of the prompt,
and paste everything below the rule.

The prompt assumes this repo is checked out at `../concord` relative to the new
repo — the standard sibling layout ([`REPO-LAYOUT.md`](../REPO-LAYOUT.md) §3).

---

Bootstrap a new Concord member mod repo in this directory.

**Mod name:** \<NAME\>
**Domain it overhauls:** \<DOMAIN — one vanilla system, e.g. "farming, food & animals"\>
**Features:** \<optional seed list — headline features the vision must promise. Expand each into the guide's three-part shape, and add more of your own if the domain needs them; leave blank to derive the feature set from the domain yourself.\>

This empty directory will become the mod's repo, living beside the suite repo at
`../concord`. The Concord documents are the authority for everything below — read
these before writing a single file:

- `../concord/VISION.md` — the collective vision. Especially §1 (one domain per
  mod, standalone always, no new dimensions, nothing another member must load),
  §2 (naming register and shared voice), §3.1 (the accent-pairing rule), §8
  (explicitly out of scope), and §9 (the four admission tests, plus any existing
  profile of this domain).
- `../concord/design/VISION-GUIDE.md` — the authoring guide for the deliverable.
  Its shape, voice rules, and checklist are binding.
- `../concord/REPO-LAYOUT.md` — the canonical member tree and the definition of
  "mirrored".

## Step 1 — Admission gate (do this before scaffolding anything)

Run the domain through the four §9 tests: domain fit, independence, MP-fairness,
silo cleanliness. Check it — and every seed feature provided above — against
each §8 rejection and against the four existing members' silos (enchanting =
Meridian, villagers/trade = Mercantile, difficulty = Tribulation, loot =
Prosperity). Check the name against the register: one weighty Latinate abstract
noun, no compounds, no "Craft"/"Plus" suffixes.

- If `../concord/VISION.md` §9 already profiles this domain (Husbandry,
  Apothecary, Tempest, Stratum), treat that profile — silo boundary, tagline
  candidate, motif, color signature — as the seed and stay consistent with it.
- If the domain or a seed feature collides with §8, an existing member's silo,
  or fails an admission test, **stop and report the conflict instead of
  proceeding.** The suite vision is amended deliberately, never steamrolled by
  a new member.

## Step 2 — Scaffold the repo

`git init` (default branch `master`), then create the minimal skeleton from
`../concord/REPO-LAYOUT.md` §1:

- `README.md` — masthead stub only: mod name, tagline, the one-line supporting
  description (`<name> — <domain> overhaul`), MC 1.21.1 · Fabric · MIT badges,
  and a "Part of Concord" line per suite convention. No feature list yet —
  README describes what is shipped, and nothing is shipped.
- `LICENSE` — MIT, copyright rfizzle (match a sibling member's file).
- `.gitignore` — copy `../concord/gitignore-common` between the
  `# concord:gitignore:start` / `# concord:gitignore:end` marker pair so future
  `make gitignore-sync` runs own that region.
- `design/` — the deliverable goes here.

Do NOT: copy any suite-level document into this repo (they are linked, never
duplicated), add this mod to `../concord/members.json`, touch `../concord` at
all, write any Java/Gradle code, or create `AGENTS.md`/`site/`/`art/` yet —
those come with the DESIGN.md/SPEC.md phase.

## Step 3 — Author `design/VISION.md` (the deliverable)

Write it to the exact shape in `../concord/design/VISION-GUIDE.md`: tagline →
The promise → The arc of a world → The features, as you'll play them (3–7, each
answering what it is / how you use it / what changes for you) → Staying in
control → Better together → What \<NAME\> will never do. 60–120 lines.

Every seed feature from the **Features** field above must appear as a headline
feature (reshaped into player language where needed); fill the remaining slots
with features the domain demands.

Hard requirements, verbatim from the guide:

- **Zero implementation vocabulary.** No mixin, packet, API, registry, event,
  config key, datagen — no word whose home is the codebase rather than the game.
- **Second person, present tense; mechanically precise.** Every quantity a
  player would plan around is a real number or range. No SPEC.md exists yet, so
  the numbers you choose here are the seed the future spec will canonicalize —
  pick concrete, defensible defaults rather than hedging with adjectives.
- **Vanilla-deferential.** The mod completes vanilla; nothing reads as "vanilla
  is broken".
- **Tagline in the suite register** — a short declarative or imperative sentence
  about the player's relationship to the system ("Survive what comes next.",
  "Every villager remembers.").
- **Better together** — one line per existing member (Meridian, Mercantile,
  Tribulation, Prosperity) where a real integration is plausible, phrased as an
  in-game experience, each marked never required, and state plainly that with no
  siblings installed nothing is missing.
- **What \<NAME\> will never do** — draw this mod's silo edges in player words:
  name the sibling that owns each neighboring system, no new dimensions, no
  required companions, and honor the suite-wide lines (no HUD slot unless the
  mod carries persistent ambient state the player needs while walking around —
  default is none).

Then run the guide's "Checklist before committing" against the file and fix
anything that fails before moving on.

## Step 4 — Commit and report

One conventional commit, e.g. `docs: add design/VISION.md and repo skeleton for
<name>`. Then report back: the admission-gate verdict (how the domain passed the
four tests and where its silo edges sit), the tagline, the headline feature
list, and any tension with the suite vision you noticed that a human should
rule on — including anything §9 got wrong or didn't anticipate about this
domain. Next steps after this bootstrap (not yours to do now): DESIGN.md and
SPEC.md per their guides, palette cleared against §3.1, then admission into
`../concord/members.json` and the sync machinery.
