# Concord — suite-level maintenance tasks.
# Member mod repos have their own Makefile (build/test/release + sync);
# this one maintains the concord-owned artifacts that propagate to them.

PY ?= python3

.PHONY: catalog catalog-check agents-sync agents-check gitignore-sync gitignore-check stubs-check stubs-test help

help:
	@echo "catalog        regenerate .ai/skills/CATALOG.md from SKILL.md frontmatter"
	@echo "catalog-check  fail if CATALOG.md is stale (CI guard)"
	@echo "agents-sync      inject concord-owned AGENTS.md regions into sibling repos (../<member>)"
	@echo "agents-check     show which sibling AGENTS.md regions would change (no writes)"
	@echo "gitignore-sync   inject the concord-owned .gitignore region into sibling repos (../<member>)"
	@echo "gitignore-check  show which sibling .gitignore regions would change (no writes)"
	@echo "stubs-check    fail if any sibling member workflow stub drifts from workflow-stubs.json"
	@echo "stubs-test     run the workflow-stub checker's unit tests"

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

gitignore-sync:
	@for m in $(MEMBERS); do \
		test -f ../$$m/.gitignore && $(PY) scripts/inject-agents-regions.py gitignore-common ../$$m/.gitignore || echo "skip: ../$$m/.gitignore not found"; \
	done

gitignore-check:
	@for m in $(MEMBERS); do \
		test -f ../$$m/.gitignore && { cp ../$$m/.gitignore /tmp/$$m.gitignore.bak; $(PY) scripts/inject-agents-regions.py gitignore-common ../$$m/.gitignore >/dev/null; diff -u /tmp/$$m.gitignore.bak ../$$m/.gitignore && echo "up to date: $$m" || true; mv /tmp/$$m.gitignore.bak ../$$m/.gitignore; } || echo "skip: ../$$m/.gitignore not found"; \
	done

# Diff each sibling member's .github/workflows/*.yml caller stubs against the
# canonical permissions + uses ref in workflow-stubs.json. Exits non-zero on
# drift (CI runs the same check over freshly-fetched member stubs).
stubs-check:
	@$(PY) scripts/check-workflow-stubs.py --root ..

stubs-test:
	@$(PY) -m unittest scripts.test_check_workflow_stubs
