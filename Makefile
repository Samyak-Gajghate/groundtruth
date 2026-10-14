.PHONY: help up down logs build migrate seed test lint format psql clean

help:
	@echo "Targets:"
	@echo "  up         postgres + backend + frontend"
	@echo "  migrate    alembic upgrade head"
	@echo "  seed       create two demo tenants with docs (Acme + Globex)"
	@echo "  test       pytest"
	@echo "  lint       ruff + mypy"
	@echo "  format     ruff format + autofix"
	@echo "  psql       open psql shell"
	@echo "  logs       tail logs"
	@echo "  down       stop containers"
	@echo "  clean      drop volumes"

up:
	docker compose up -d
	@echo "Backend:   http://localhost:8000/docs"
	@echo "Dashboard: http://localhost:3002"

down:
	docker compose down

logs:
	docker compose logs -f --tail=200

build:
	docker compose build

migrate:
	docker compose exec backend alembic upgrade head

seed:
	docker compose exec backend python -m scripts.seed_demo

test:
	docker compose exec backend pytest -v

lint:
	docker compose exec backend ruff check src tests scripts
	docker compose exec backend mypy src

format:
	docker compose exec backend ruff format src tests scripts
	docker compose exec backend ruff check --fix src tests scripts

psql:
	docker compose exec postgres psql -U saas

clean:
	docker compose down -v
