.PHONY: dev stop migrate sync-full sync-incremental test lint

dev:
	docker compose up -d

stop:
	docker compose down

migrate:
	cd backend && uv run alembic upgrade head

sync-full:
	cd backend && uv run python -m app.ingestion.sync --full

sync-incremental:
	cd backend && uv run python -m app.ingestion.sync --incremental

test:
	cd backend && uv run pytest
	cd frontend && pnpm test

lint:
	cd backend && uv run ruff check . && uv run ruff format --check .
	cd frontend && pnpm lint
