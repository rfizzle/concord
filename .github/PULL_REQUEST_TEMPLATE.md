<!--
Title: Conventional Commits with a topical scope, matching the issue's
normalized title — e.g. feat(render): add glyph atlas cache
Imperative mood, lower-case, no trailing period.
-->

## Summary

<!-- A short plain-language description of what changed and why. -->

Closes #<!-- issue number -->
<!-- Use "Refs #<n>" instead if this PR deliberately leaves part of the issue for later. -->

## Docs impact

<!--
Player-facing change (new feature, config option, command, or gameplay rule)?
Name the site/ page(s) updated here. Delete this section for internal-only work.
-->

## Checklist

- [ ] Title and commits follow Conventional Commits with the issue's scope vocabulary
- [ ] Build is green (`./gradlew build`)
- [ ] Unit tests and gametests pass
- [ ] Player-facing changes update the matching `site/` page(s)
