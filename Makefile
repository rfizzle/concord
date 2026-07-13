# Concord — suite-level maintenance tasks.
# Member mod repos have their own Makefile (build/test/release + sync);
# this one maintains the concord-owned artifacts that propagate to them.

PY ?= python3

.PHONY: catalog catalog-check agents-sync agents-check gitignore-sync gitignore-check stubs-check stubs-test toolchain-check toolchain-test art-test status status-test sync-test help

help:
	@echo "catalog        regenerate .ai/skills/CATALOG.md from SKILL.md frontmatter"
	@echo "catalog-check  fail if CATALOG.md is stale (CI guard)"
	@echo "agents-sync      inject concord-owned AGENTS.md regions into sibling repos (../<member>)"
	@echo "agents-check     show which sibling AGENTS.md regions would change (no writes)"
	@echo "gitignore-sync   inject the concord-owned .gitignore region into sibling repos (../<member>)"
	@echo "gitignore-check  show which sibling .gitignore regions would change (no writes)"
	@echo "stubs-check    fail if any sibling member workflow stub drifts from workflow-stubs.json"
	@echo "stubs-test     run the workflow-stub checker's unit tests"
	@echo "toolchain-check  fail if any sibling member is behind propagate/versions-common.properties"
	@echo "toolchain-test   run the toolchain-drift checker's unit tests"
	@echo "art-test       run the glyph + sfx renderer unit tests"
	@echo "status         regenerate site/status.json + the status page from the public APIs"
	@echo "status-test    run the status generator's unit tests"
	@echo "sync-test      run the concord-sync PR script's integration tests"

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

# Diff each sibling member's effective toolchain pins (versions-common.properties
# precedence over gradle.properties) against the canonical suite pins in
# propagate/versions-common.properties. Exits non-zero when a member pins a
# governed key to a stale value (CI runs the same check over freshly-fetched
# member properties).
toolchain-check:
	@$(PY) scripts/check-toolchain-drift.py --root ..

toolchain-test:
	@$(PY) -m unittest scripts.test_check_toolchain_drift

# Regenerate the suite status dashboard (site/status.json, site/pages/status.json,
# and the landing "suite-status" section) from the public GitHub and Modrinth
# APIs. The nightly status.yml workflow runs the same script and commits the
# result when the data changed.
status:
	@$(PY) scripts/gen-status.py

status-test:
	@$(PY) -m unittest scripts.test_gen_status

# Guard the vendored art renderers (.ai/skills/mc-textures/scripts/glyph.py and
# .ai/skills/mc-audio/scripts/sfx.py) — every member repo receives these via the
# concord-sync propagate PR (or `make sync` locally), so a regression here breaks
# the whole suite's art pipeline.
art-test:
	@$(PY) -m unittest scripts.test_glyph scripts.test_sfx

# Exercise scripts/open-sync-pr.py — which stages concord-owned files onto each
# member's concord-sync PR — against a mock gh: add/update/delete of the vendored
# .ai/skills + .ai/commands trees and the .concord-rev provenance stamp.
sync-test:
	@$(PY) -m unittest scripts.test_open_sync_pr
