.PHONY: lint format fmt types quality test acceptance ci-pr ci-push act-pr-policy act-pr-policy-fail-assignee act-pr-policy-fail-title act-pr-policy-fail-branch release-dry release-prep act-release help
.DEFAULT_GOAL := help

ENGINES := skills/uacp-core/scripts/engines/
E2E     := tests/e2e/
PYRIGHT_PATHS := \
	skills/uacp-core/scripts/engines/guardian \
	skills/uacp-core/scripts/engines/domain/paths.py \
	skills/uacp-core/scripts/engines/domain/design_lint.py \
	skills/uacp-core/scripts/engines/heartgate/models.py \
	skills/uacp-core/scripts/engines/heartgate/validators/helpers.py

lint:
	ruff check $(ENGINES) $(E2E)

format:
	ruff format --check $(ENGINES) $(E2E)

fmt:
	ruff format $(ENGINES) $(E2E)

types:
	pyright $(PYRIGHT_PATHS)

quality: lint format types

# Note: full CI parity requires `pip install -e '.[dev,mcp]'` + uv installed
# so the MCP boot test (TestMcpServerBoots) runs instead of skipping silently.
test:
	pytest tests/ -n auto -q

# E2E acceptance harness — plugin conformance (Increment 0) in a clean container: launch the MCP
# server as plugin.json configures it, assert the surface == tool_specs() + hooks/skills are loadable.
# The deterministic prober also runs in `make test` (tests/acceptance/); this target is the
# containerized plugin-source conformance smoke (not a `claude plugin install` round-trip). Needs docker.
acceptance:
	docker compose -f acceptance/compose.yml run --rm conformance

# Simulate the PR gate (quality + test) via act — mirrors what runs on pull_request.
ci-pr:
	act pull_request -W .github/workflows/ci.yml

# Simulate a merge to main (all jobs including test-compat) via act.
ci-push:
	act push -W .github/workflows/ci.yml

# Run PR Policy locally with a passing event (all 4 checks green).
act-pr-policy:
	act pull_request -W .github/workflows/pr-policy.yml \
	    --eventpath .act/pr-policy-pass.json

# Run PR Policy with a missing-assignee event — expect a failing exit.
act-pr-policy-fail-assignee:
	@act pull_request -W .github/workflows/pr-policy.yml \
	    --eventpath .act/pr-policy-fail-no-assignee.json; \
	  code=$$?; \
	  [ $$code -ne 0 ] \
	    && echo "PASS: workflow correctly rejected PR with no assignee (exit $$code)." \
	    || echo "FAIL: expected non-zero exit, got 0."

# Run PR Policy with a bad PR title — expect a failing exit.
act-pr-policy-fail-title:
	@act pull_request -W .github/workflows/pr-policy.yml \
	    --eventpath .act/pr-policy-fail-bad-title.json; \
	  code=$$?; \
	  [ $$code -ne 0 ] \
	    && echo "PASS: workflow correctly rejected bad PR title (exit $$code)." \
	    || echo "FAIL: expected non-zero exit, got 0."

# Run PR Policy with a bad branch name — expect a failing exit.
act-pr-policy-fail-branch:
	@act pull_request -W .github/workflows/pr-policy.yml \
	    --eventpath .act/pr-policy-fail-bad-branch.json; \
	  code=$$?; \
	  [ $$code -ne 0 ] \
	    && echo "PASS: workflow correctly rejected bad branch name (exit $$code)." \
	    || echo "FAIL: expected non-zero exit, got 0."

# Preview what a version bump would change — no files written.
# Usage: make release-dry TYPE=minor
TYPE ?= patch
release-dry:
	python3 scripts/bump_version.py $(TYPE) --dry-run

# Apply the version bump across all manifests. Prints git commands to run next.
# Usage: make release-prep TYPE=minor
release-prep:
	python3 scripts/bump_version.py $(TYPE)

# Test release.yml verification steps locally (needs act + Docker).
# The verification steps (main-ancestry, version match, manifest agreement) run in full.
# The final 'gh release create' step will fail with the fake token — this is expected.
# Proof-of-correctness: all earlier steps exit 0.
act-release:
	act push -W .github/workflows/release.yml \
	    --eventpath .act/release-tag-event.json \
	    -s GH_TOKEN=fake

help:
	@echo "Targets:"
	@echo "  lint       ruff check (scoped to engines + e2e)"
	@echo "  format     ruff format --check (scoped)"
	@echo "  fmt        ruff format --fix (scoped)"
	@echo "  types      pyright (strict-scoped engines)"
	@echo "  quality    lint + format + types"
	@echo "  test       pytest -n auto (all suites)"
	@echo "  acceptance E2E plugin-conformance smoke in a container (needs docker)"
	@echo "  ci-pr                  act pull_request — simulate PR gate locally"
	@echo "  ci-push                act push — simulate post-merge jobs locally"
	@echo "  act-pr-policy          run PR Policy with a passing event"
	@echo "  act-pr-policy-fail-*   run PR Policy with a failing event (assignee/title/branch)"
	@echo "  release-dry  TYPE=minor  preview version bump (no files written)"
	@echo "  release-prep TYPE=minor  bump version across all manifests"
