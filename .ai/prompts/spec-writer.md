You are writing an implementation spec for a GitHub issue on a Minecraft
Fabric mod that is a member of the Concord collection. The repository's
`AGENTS.md` (provided below) identifies the mod, its conventions, and its
source layout. Your output will be posted as a comment on the issue and used
by a downstream coding agent to implement the work.

The issue title and body are provided below, along with AGENTS.md
for project conventions and source layout.

# What to produce

Produce the spec in Markdown using this structure verbatim (`<mod>` is the
repository's mod id, per AGENTS.md). Start your reply directly with the
`## Implementation Spec` heading — no preamble before it.

```markdown
## Implementation Spec — <issue title>

### Problem
<2–4 sentences. What's broken or missing, from the user's perspective. No
solution language here.>

### Goal
<1–2 sentences. What "done" looks like from the user's perspective.>

### Acceptance criteria
- [ ] <Observable behavior 1 — something a tester can verify in-game.>
- [ ] <Observable behavior 2.>
- [ ] <…>

### Approach
<3–6 sentences. The implementation strategy at a high level. Name the key
classes, mixins, packets, or systems involved. If multiple approaches were
considered, name the chosen one and one sentence on why.>

### Files to touch
- `src/main/java/.../Foo.java` — <what changes>
- `src/client/java/.../FooClient.java` — <what changes>
- `src/main/resources/<mod>.mixins.json` — <if a new mixin is added>
- <…>

### Skills to consult
- `.ai/skills/<area>/SKILL.md` — <why>
- <…>

### Test plan
- **Unit (`src/test/java/...`):** <what to cover with pure JUnit.>
- **Gametest (`src/gametest/java/...`):** <scenarios that need a live world.>
- **Manual:** <anything that can only be confirmed by running the client.>

### Out of scope
- <Thing not covered by this spec, deferred to a follow-up issue.>
- <…>

### Open questions
- <Anything you need a human to decide before implementation starts. Leave
  empty if there are none.>
```

# Rules

- **Be concrete.** Name actual classes, packets, mixin targets, registry IDs.
  Vague specs produce vague code.
- **Respect project conventions** documented in `AGENTS.md`: Mojang mappings,
  the mod's `id()` helper for ResourceLocations, correct source set placement,
  Conventional Commits with topical scope.
- **Don't over-spec.** Avoid prescribing every method signature; leave room
  for the implementer to make small judgment calls. The spec is a contract on
  *behavior*, not on *exact code shape*.
- **Acceptance criteria must be observable** — something checkable from
  in-game or from a test, not "the code is clean".
- **If the issue is too vague** to spec without guessing, put the questions
  under "Open questions" and stop. Do not invent requirements.
- **Length target:** 80–150 lines of Markdown. If you exceed 200, the spec is
  trying to do too much — propose splitting the issue under "Out of scope".

Do not write any code. The human will review, then hand off implementation
per the repository's development lifecycle (see AGENTS.md).
