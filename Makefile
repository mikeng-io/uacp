.PHONY: lint format fmt types quality test acceptance ci-pr ci-push help
.DEFAULT_GOAL := help

ENGINES := skills/uacp-core/scripts/engines/
E2E     := tests/e2e/
PYRIGHT_PATHS := \
	skills/uacp-core/scripts/engines/guardian \
	skills/uacp-core/scripts/engines/domain/paths.py \
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

help:
	@echo "Targets:"
	@echo "  lint       ruff check (scoped to engines + e2e)"
	@echo "  format     ruff format --check (scoped)"
	@echo "  fmt        ruff format --fix (scoped)"
	@echo "  types      pyright (strict-scoped engines)"
	@echo "  quality    lint + format + types"
	@echo "  test       pytest -n auto (all suites)"
	@echo "  acceptance E2E plugin-conformance smoke in a container (needs docker)"
	@echo "  ci-pr      act pull_request — simulate PR gate locally"
	@echo "  ci-push    act push — simulate post-merge jobs locally"
