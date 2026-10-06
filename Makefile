# Mender: Kubernetes Incident-to-Fix Agent — developer commands.

.PHONY: setup test lint demo serve

setup: ## one-command setup: python deps + demo cluster + images
	uv sync --group dev
	bash demo/cluster.sh

test: ## lint, type check, unit tests
	uv run ruff check src tests
	uv run ruff format --check src tests
	uv run mypy
	uv run pytest

demo: ## one-command demo: one fault, failure to diagnosis to patch to sandbox to PR
	bash demo/demo.sh

serve: ## run the HTTP service
	uv run mender serve
