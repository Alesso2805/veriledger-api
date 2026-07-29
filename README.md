# VeriLedger API

VeriLedger API is a backend portfolio project inspired by verifiable finance and blockchain infrastructure. It implements a complete decentralized ledger including cryptographic transaction hashing, digital signatures (Ed25519), a Mempool, Proof of Work (mining), a P2P network consensus mechanism, and Data Notarization (Proof of Existence).

## Stack
- Python 3.14+
- FastAPI
- SQLAlchemy 2.x (async)
- SQLite (aiosqlite)
- Alembic
- Pydantic v2
- `uv` (Fast Python package installer and resolver)
- pytest, ruff, mypy

## Architecture & Application Flow
The project strictly follows Clean Architecture and Domain-Driven Design (DDD) principles:
- `core/`: Cross-cutting concerns like configuration and logging.
- `domain/`: Pure business logic, entities, and ports. Zero dependencies on external frameworks.
- `application/`: Use cases, DTOs, orchestrators.
- `infrastructure/`: Database models, repositories, and third-party integrations (like Hashing and Cryptography).
- `presentation/`: FastAPI routers and dependency injection.

### How it works:
1. **Transactions & Mempool:** Users submit cryptographically signed transactions via the API. The API verifies the Ed25519 signature mathematically. If valid, it is stored in the Mempool (status: `PENDING`).
2. **Proof of Existence:** Users can submit transactions with `amount: 0.0` and a `payload` (a document hash). This acts as a decentralized notary.
3. **Mining (Proof of Work):** A miner hits the `/blocks/mine` endpoint. The system gathers pending transactions, verifies them again, and solves a computationally difficult cryptographic puzzle (finding a nonce). Once solved, the block is saved to the SQLite database and transactions become `CONFIRMED`.
4. **P2P Consensus:** Nodes can register other peer URLs. When `/nodes/resolve` is called, the node fetches the blockchain from all peers. If it finds a mathematically valid chain longer than its own, it drops its local chain and synchronizes with the network, achieving decentralized consensus.

## Setup & Running Locally

### 1. Install Dependencies
We use `uv` for lightning-fast dependency management.
```bash
# Sync dependencies and create virtual environment
uv sync
```

### 2. Configure Environment
```bash
# Copy the example file and adjust if necessary
cp .env.example .env
```
*Note: The project is currently configured to use SQLite, so no external database engine is required.*

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

## Useful Commands (Testing, Linting & DB)

Here are the most important commands to manage the backend repository. 
**Note:** Always use `uv run` to ensure you execute within the virtual environment.

### Testing
Run the comprehensive unit testing suite using an in-memory database:
```bash
# Run all tests
$env:PYTHONPATH="C:\Users\USER\Documents\GitHub\veriledger-api"; $env:DATABASE_URL="sqlite+aiosqlite:///:memory:"; uv run pytest tests/unit/application/use_cases

# Run specific tests with verbose output
$env:PYTHONPATH="C:\Users\USER\Documents\GitHub\veriledger-api"; $env:DATABASE_URL="sqlite+aiosqlite:///:memory:"; uv run pytest tests/unit/application/use_cases -v
```

### Linting & Formatting
```bash
# Auto-format all code
uv run ruff format backend

# Run linter to check for code quality issues
uv run ruff check backend

# Run static type checking
uv run mypy backend/app backend/tests
```

### Database Management (Alembic)
```bash
# Create a new migration after changing SQLAlchemy models
uv run alembic -c backend/alembic.ini revision --autogenerate -m "description of changes"

# Apply migrations to the database
uv run alembic -c backend/alembic.ini upgrade head

# Rollback the last migration
uv run alembic -c backend/alembic.ini downgrade -1
```
