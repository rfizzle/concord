# Concord — suite-level maintenance tasks.
# Member mod repos have their own Makefile (build/test/release + sync);
# this one maintains the concord-owned artifacts that propagate to them.

PY ?= python3

.PHONY: catalog catalog-check agents-sync agents-check help

help:
	@echo "catalog        regenerate .ai/skills/CATALOG.md from SKILL.md frontmatter"
	@echo "catalog-check  fail if CATALOG.md is stale (CI guard)"
	@echo "agents-sync    inject concord-owned AGENTS.md regions into sibling repos (../<member>)"
	@echo "agents-check   show which sibling AGENTS.md regions would change (no writes)"

catalog:
	@$(PY) scripts/gen-skills-catalog.py

catalog-check:
	@$(PY) scripts/gen-skills-catalog.py --check

# Local convenience: apply AGENTS-COMMON.md regions to each member checked out
# as a sibling directory. CI does the same for all members via propagate.yml.
MEMBERS := $(shell jq -r '.members[].id' members.json)

agents-sync:
	@for m in $(MEMBERS); do \
		test -f ../$$m/AGENTS.md && $(PY) scripts/inject-agents-regions.py AGENTS-COMMON.md ../$$m/AGENTS.md || echo "skip: ../$$m/AGENTS.md not found"; \
	done

agents-check:
	@for m in $(MEMBERS); do \
		test -f ../$$m/AGENTS.md && { cp ../$$m/AGENTS.md /tmp/$$m.agents.bak; $(PY) scripts/inject-agents-regions.py AGENTS-COMMON.md ../$$m/AGENTS.md >/dev/null; diff -u /tmp/$$m.agents.bak ../$$m/AGENTS.md && echo "up to date: $$m" || true; mv /tmp/$$m.agents.bak ../$$m/AGENTS.md; } || echo "skip: ../$$m/AGENTS.md not found"; \
	done
