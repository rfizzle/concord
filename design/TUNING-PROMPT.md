# Tuning Prompt — the feature interview for a member's VISION and SPEC

The paste-in prompt for a working session on a member mod's feature set: you
and the agent throw ideas around, every idea is gated against the mod's
domain, and what survives lands in `design/VISION.md` and `design/SPEC.md` to
their guides' standards. Companion to
[`BOOTSTRAP-PROMPT.md`](BOOTSTRAP-PROMPT.md) — that one creates the vision;
this one tunes it, for any member at any stage.

To use it: start a fresh agent session in the member repo (standard sibling
layout, concord at `../concord`), optionally fill the field at the top, and
paste everything below the rule.

---

Run a feature interview for the mod in this directory: a spoken-style working
session where we explore, sharpen, and prune the mod's feature set together,
then land the agreed changes in `design/VISION.md` and `design/SPEC.md`.

**Focus (optional):** \<a feature area, a nagging doubt, or seed ideas to
explore — leave blank for a whole-vision pass\>

## Ground rules

You are two things at once in this session, and the second is the reason it
exists:

1. **A design partner.** Bring your own ideas, sharpen mine, and hunt for the
   version of each idea that is most fun in play. Think in player experience
   first, numbers second, implementation last.
2. **The domain warden.** Every idea — mine included, especially mine — is
   checked against the mod's silo before it is entertained on the merits. The
   interview's value is the boundary: an enthusiastic yes to an out-of-domain
   feature is a failure of this session, however good the feature.

This is a conversation, not a batch job. One topic at a time, real back and
forth, and **no file edits until the landing phase** — keep a running ledger
instead. Push back when I'm wrong, with reasons; ask the question that
exposes a weak feature ("what changes for the player?", "what does it cost?")
rather than silently patching it.

## Step 1 — Orient

Read, in this order:

- This repo's `design/VISION.md` and `design/SPEC.md` (if present) — the
  current promise and contract.
- `../concord/VISION.md` — the suite: §1 (one domain per mod, standalone
  always), §2 (voice), §8 (explicitly out of scope), §9 (admission tests and
  domain profiles), and the integration matrix.
- `../concord/design/VISION-GUIDE.md` and `SPEC-GUIDE.md` — the standards the
  landing phase must meet.
- `../concord/HUD-STANDARD.md` — the HUD test, in case an idea wants a slot.

Then open the session with a short brief, not a document dump: the mod's
promise in one line, its headline features as they stand, where its silo
edges sit (its own "will never do" plus the neighboring siblings), how much
of the vision the spec currently covers, and — your opening move — the two or
three places you think the feature set is weakest, thinnest, or most fun to
push on. If a **Focus** was given above, orient the brief around it.

## Step 2 — The interview loop

For each idea on the table, from either of us:

1. **Restate it as play.** One or two sentences of what the player does and
   what happens — the vision guide's register. If it can't be said without
   implementation vocabulary, it isn't a feature yet.
2. **Gate it.** Against the suite §8 rejections, the sibling silos, this
   mod's "What \<Mod\> will never do", the standalone rule (works with no
   siblings, degrades to nothing missing), MP-fairness, and the HUD test if
   it touches the screen. Verdict, stated plainly:
   - **In domain** — proceed to sharpening.
   - **Reshape** — the kernel is in domain but the current form crosses a
     line; propose the in-domain version.
   - **Belongs to \<sibling\>** — name the owner; if it's a real integration,
     recast it as an optional Better-together line instead.
   - **Out (§8 / suite line)** — say which line, and drop it.
   - **Needs a suite ruling** — it collides with the suite or member vision
     but might deserve a deliberate amendment; park it for the report, never
     steamroll it.
3. **Sharpen what survives.** Drive it to the three vision answers (what it
   is / how you use it / what changes for you), a real cost or tradeoff, and
   concrete numbers — propose defensible defaults and ranges yourself rather
   than leaving adjectives. Note the spec-shaped consequences as they come
   up: edge cases against vanilla systems, multiplayer behavior, config
   surface.
4. **Ledger it.** Accepted / reshaped / declined / parked, with the one-line
   reason. Existing features are on the table too — the interview can weaken,
   sharpen, or remove a promise, not just add them.

Between my ideas, contribute your own: gaps the arc-of-a-world leaves open,
features the domain profile in suite §9 hints at, places where an existing
feature stops one step short of fun. Same gates apply.

## Step 3 — Land it

When I say to land it (or the conversation wraps), apply the ledger:

- **`design/VISION.md`** absorbs every accepted change — new features in the
  three-part shape, sharpened numbers, amended edges in "will never do",
  Better-together lines for recast integrations. Rewrite to the current
  promise only (no change narration), then run the vision guide's "Checklist
  before committing" and fix what fails.
- **`design/SPEC.md`** — where a feature lands depends on where the mod is in
  its life:
  - **Pre-first-release** (spec-before-code): write the full per-feature
    anatomy into `SPEC.md` — Problem, Behavior with exact numbers, named edge
    cases, Config, Implementation Notes — plus the cross-cutting sections it
    touches, per the spec guide.
  - **Released**: `SPEC.md` states shipped behavior, so new features flow
    through the issue lifecycle instead — open one GitHub issue per accepted
    feature carrying the sharpened sketch (the play-language pitch, numbers,
    known edge cases), labeled `needs-spec` so the pipeline in
    `AGENTS-COMMON.md` picks it up. Changes to *already-shipped* numbers or
    rules get an issue too; the spec absorbs them when the change ships.
- **Parked items** are not landed anywhere — they go in the report.

One conventional commit per repo touched (e.g. `docs: sharpen the vision
after feature interview — <headline>`). Do not touch `../concord`.

## Step 4 — Report

Close with the ledger in full: accepted (and where each landed — vision
section, spec section, or issue number), reshaped (original → landed form),
declined (which gate), and parked suite-ruling items with the exact tension a
human needs to rule on. If the session exposed something wrong in the suite
vision itself — a §9 profile that misjudged this domain, an §8 line that cuts
a good feature — say so explicitly; amending that is my move, in concord,
deliberately.
