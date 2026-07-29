# VeriLedger API

VeriLedger API is a backend portfolio project inspired by verifiable finance and blockchain infrastructure. It implements backend components related to blockchain infrastructure, such as transaction hashing, Merkle proofs, RPC-style endpoints, audit logs, and a simple DEX-like trading module.

## Stack
- Python 3.12+
- FastAPI
- SQLAlchemy 2.x (async)
- PostgreSQL
- Alembic
- Pydantic v2
- uv (Dependency Management)
- pytest, ruff, mypy

## Architecture
The project strictly follows Clean Architecture and Domain-Driven Design (DDD) principles:
- `core/`: Cross-cutting concerns like configuration and logging.
- `domain/`: Pure business logic, entities, and ports. Zero dependencies on external frameworks.
- `application/`: Use cases, DTOs, orchestrators.
- `infrastructure/`: Database models, repositories, and third-party integrations.
- `presentation/`: FastAPI routers and dependency injection.

## Commands

- `make up`: Start the development environment (backend + postgres) using Docker Compose.
- `make down`: Stop the development environment.
- `make test`: Run pytest suite.
- `make lint`: Run Ruff for linting.
- `make format`: Auto-format code using Ruff.
- `make typecheck`: Run Mypy for static type checking.

## Running Locally

1. Copy `.env.example` to `.env` and adjust variables if needed.
2. Run `make up` to build and start the containers.
3. Access the API at `http://localhost:8000`.
4. Access the health check at `http://localhost:8000/health`.
