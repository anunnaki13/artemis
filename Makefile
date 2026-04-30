.PHONY: install test lint typecheck dev migrate

PYTHON := .venv/bin/python
PIP := .venv/bin/pip
PYTEST := .venv/bin/pytest
RUFF := .venv/bin/ruff
MYPY := .venv/bin/mypy

install:
	cd frontend && npm install
	python3.11 -m venv .venv
	$(PIP) install --upgrade pip setuptools wheel
	$(PIP) install -e "backend[dev]"

test:
	cd backend && ../$(PYTEST)

lint:
	cd backend && ../$(RUFF) check .
	cd frontend && npm run lint

typecheck:
	cd backend && ../$(MYPY) app
	cd frontend && npm run typecheck

dev:
	docker compose up --build

migrate:
	cd backend && ../.venv/bin/alembic upgrade head
