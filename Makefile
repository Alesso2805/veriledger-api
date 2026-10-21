.PHONY: up down test lint typecheck format check-imports

up:
	docker-compose up -d --build

down:
	docker-compose down

test:
	uv run pytest backend/tests

lint:
	uv run ruff check backend
	uv run lint-imports

format:
	uv run ruff check --fix backend
	uv run ruff format backend

typecheck:
	uv run mypy backend/app backend/tests

# Fails if the app needs a package that is only a dev dependency
check-imports:
	uv run --isolated --no-dev python -c "import backend.app.main"

migrate:
	uv run alembic -c backend/alembic.ini upgrade head

seed:
	uv run python -m backend.app.cli.seed

# docs/openapi.json, the contract the webapp generates its types from (VLA-37)
openapi:
	DATABASE_URL=$${DATABASE_URL:-sqlite+aiosqlite:///:memory:} uv run python -m backend.app.openapi_document

# After changing ADMIN_PASSWORD (docs/runbooks/rotate-secrets.md)
set-admin-password:
	uv run python -m backend.app.cli.set_admin_password

# Run on a schedule in demo deployments (ADR-0006)
purge-demo-accounts:
	uv run python -m backend.app.cli.purge_demo_accounts
