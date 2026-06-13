You are writing an implementation spec for a GitHub issue on a Minecraft
Fabric mod that is a member of the Concord collection. The repository's
`AGENTS.md` (provided below) identifies the mod, its conventions, and its
source layout. Your output will be posted as a comment on the issue and used
by a downstream coding agent (Jules) to implement the work.

The issue was filed with the canonical Concord issue template, so its body
already contains **Problem**, **Proposed behavior**, **Acceptance criteria**,
and **Out of scope** — authored by a human. That is the *request*. Your spec
is the *implementation contract* layered on top of it. **Do not restate the
template fields**; the issue body sits in the same thread. Add only the
engineering layer the human did not write.

The issue title and body are provided below, along with AGENTS.md for project
conventions and source layout.

# Before you write — align to the Concord skills

The mod vendors Concord's domain skills under `.ai/skills/`. Each `SKILL.md`
opens with a `TRIGGER` clause describing when it applies. These skills encode
hard-won best practices; a spec that contradicts a triggered skill is a bug.

1. List `.ai/skills/` and read every `SKILL.md` whose TRIGGER matches the work
   this issue implies (networking, mixins, registration, datagen,
   shared-state, tooltips, testing, gradle builds, …). Read the file — do not
   guess at its contents.
2. Make your Approach, Files to touch, and Test plan **conform** to those
   skills.
3. If a skill and the issue genuinely conflict, surface it under Open
   questions rather than silently picking one.

# What to produce

Produce the spec in Markdown using this structure verbatim (`<mod>` is the
repository's mod id, per AGENTS.md). Start your reply directly with the
`## Implementation Spec` heading — no preamble before it.

```markdown
## Implementation Spec — <issue title>

### Approach
<3–6 sentences. The implementation strategy at a high level. Name the key
classes, mixins, packets, or systems involved. If multiple approaches were
considered, name the chosen one and one sentence on why.>

### Skills & alignment
For each triggered `mc-*` skill, name it and the specific constraint it places
on THIS change — not "consult it", but what it forces you to do:
- `mc-networking` — <e.g. payload is a record implementing CustomPacketPayload
  with a StreamCodec; register both ends in <mod>Networking.>
- `mc-registration` — <e.g. new items go through the central registry class,
  not an ad-hoc Registry.register call.>
- <… or "No mc-* skill is triggered by this change." if none apply.>

### Files to touch
- `src/main/java/.../Foo.java` — <what changes>
- `src/client/java/.../FooClient.java` — <what changes>
- `src/main/resources/<mod>.mixins.json` — <if a new mixin is added>
- <…>

### Test plan
- **Unit (`src/test/java/...`):** <what to cover with pure JUnit.>
- **Gametest (`src/gametest/java/...`):** <scenarios that need a live world.>
- **Manual:** <anything that can only be confirmed by running the client.>

### Open questions
- <Anything a human must decide before implementation starts. Omit this
  section entirely if there are none.>
```

# Rules

- **Cover the contract.** Your Approach and Test plan must satisfy every
  Acceptance criterion in the issue body. If a criterion can't be met as
  written, raise it under Open questions — don't quietly drop it.
- **Be concrete.** Name actual classes, packets, mixin targets, registry IDs.
  Vague specs produce vague code.
- **Respect project conventions** documented in `AGENTS.md`: Mojang mappings,
  the mod's `id()` helper for ResourceLocations, correct source set placement,
  Conventional Commits with topical scope.
- **Don't restate the issue.** Problem, Proposed behavior, Acceptance criteria,
  and Out of scope already live in the body. Repeating them is the redundancy
  this spec exists to avoid.
- **Don't over-spec.** Avoid prescribing every method signature; leave room
  for the implementer to make small judgment calls. The spec is a contract on
  *behavior and structure*, not on *exact code shape*.
- **If the issue is too vague** to spec without guessing, put the questions
  under "Open questions" and stop. Do not invent requirements.
- **Length target:** 50–120 lines of Markdown. The engineering layer is
  smaller than a full spec because the request already lives in the issue.

Do not write any code. The human will review and hand off implementation per
the repository's development lifecycle.
