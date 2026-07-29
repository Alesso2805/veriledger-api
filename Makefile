.PHONY: up down test lint typecheck format

up:
	docker-compose up -d --build

down:
	docker-compose down

test:
	uv run pytest backend/tests

lint:
	uv run ruff check backend

format:
	uv run ruff check --fix backend
	uv run ruff format backend

typecheck:
	uv run mypy backend/app backend/tests
