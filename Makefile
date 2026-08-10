.PHONY: help install dev-install run demo lint format test check clean

help:
	@echo "Comandos disponíveis:"
	@echo "  make install      - instala dependências de produção"
	@echo "  make dev-install  - instala dependências de desenvolvimento (dev + viz)"
	@echo "  make run          - sobe a API com reload (uvicorn)"
	@echo "  make demo         - roda o cronista direto (sem API); args: SEED e YEARS"
	@echo "  make lint         - roda ruff check"
	@echo "  make format       - roda ruff format"
	@echo "  make test         - roda a suíte de testes (pytest)"
	@echo "  make check        - roda lint + testes"
	@echo "  make clean        - remove caches e artefatos temporários"

install:
	uv sync

dev-install:
	uv sync --extra dev --extra viz

run:
	uv run uvicorn api.main:create_app --factory --reload

demo:
	uv run python demo.py $(SEED) $(YEARS)

lint:
	uv run ruff check .

format:
	uv run ruff format .

test:
	uv run pytest

check: lint test

clean:
	rm -rf .ruff_cache .pytest_cache
	find . -type d -name "__pycache__" -exec rm -rf {} +
