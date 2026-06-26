.PHONY: lint format types quality test ci-pr ci-push help

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

test:
	pytest tests/ -n auto -q

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
	@echo "  ci-pr      act pull_request — simulate PR gate locally"
	@echo "  ci-push    act push — simulate post-merge jobs locally"
