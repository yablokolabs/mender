# Mender: Kubernetes Incident-to-Fix Agent — developer commands.

.PHONY: setup test lint demo serve diagram image

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

diagram: ## render assets/arch-diagram.png from its SVG source (needs librsvg2-bin, fonts-liberation)
	rsvg-convert --width 1920 assets/arch-diagram.svg --output assets/arch-diagram.png

image: ## build the service image and check that it starts
	docker build -t mender .
	bash .github/workflows/image-smoke.sh mender
