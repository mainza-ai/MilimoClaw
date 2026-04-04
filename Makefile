.PHONY: check lint format lint-ts lint-py format-ts format-py test test-ts test-py test-integration

check: lint-ts lint-py
	@echo "All checks passed."

lint: lint-ts lint-py

lint-ts:
	cd milimo && npm run check 2>/dev/null || npx tsc --noEmit

lint-py:
	cd milimo-blueprint && python3 -m pytest tests/ -v --tb=short

format: format-ts format-py

format-ts:
	cd milimo && npx prettier --write "src/**/*.ts" 2>/dev/null || true

format-py:
	cd milimo-blueprint && python3 -m ruff format . 2>/dev/null || true

# --- Testing ---

test: test-ts test-py test-integration

test-ts:
	cd milimo && npm test

test-py:
	cd milimo-blueprint && python3 -m pytest tests/ -v

test-integration:
	node --test test/integration/*.test.js
