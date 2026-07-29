# VeriLedger API

VeriLedger API is a backend portfolio project inspired by verifiable finance and blockchain infrastructure. It implements backend components related to blockchain infrastructure, such as transaction hashing, Merkle proofs, RPC-style endpoints, audit logs, Proof of Work (mining), and a P2P network consensus mechanism.

## Stack
- Python 3.12+
- FastAPI
- SQLAlchemy 2.x (async)
- PostgreSQL
- Alembic
- Pydantic v2
- `uv` (Fast Python package installer and resolver)
- pytest, ruff, mypy

## Architecture
The project strictly follows Clean Architecture and Domain-Driven Design (DDD) principles:
- `core/`: Cross-cutting concerns like configuration and logging.
- `domain/`: Pure business logic, entities, and ports. Zero dependencies on external frameworks.
- `application/`: Use cases, DTOs, orchestrators.
- `infrastructure/`: Database models, repositories, and third-party integrations.
- `presentation/`: FastAPI routers and dependency injection.

## Setup & Running Locally (Without Docker)

### 1. Install Dependencies
We use `uv` for lightning-fast dependency management.
```bash
# Sync dependencies and create virtual environment
uv sync
```

### 2. Configure Environment
```bash
# Copy the example file and adjust the database credentials if necessary
cp .env.example .env
```
Ensure you have a local PostgreSQL instance running. Alternatively, you can spin up just the database with Docker:
```bash
docker-compose up -d db
```

### 3. Database Migrations & Seeding
Apply the latest Alembic migrations to create the database schema:
```bash
uv run alembic -c backend/alembic.ini upgrade head
```
Seed the initial database (e.g., admin user):
```bash
uv run python -m backend.app.infrastructure.seed
```

### 4. Run the Application
Start the Uvicorn development server:
```bash
uv run uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```
- API Docs (Swagger): `http://127.0.0.1:8000/docs`
- Health check: `http://127.0.0.1:8000/health`

## Running via Docker
If you prefer running everything in containers:

- `make up`: Start the development environment (backend + postgres).
- `make down`: Stop the environment.

## Other Commands (Testing & Linting)
- `make test` or `uv run pytest backend/tests`: Run pytest suite.
- `make lint` or `uv run ruff check backend`: Run Ruff for linting.
- `make format` or `uv run ruff format backend`: Auto-format code.
- `make typecheck` or `uv run mypy backend/app backend/tests`: Run Mypy static type checking.
