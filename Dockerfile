FROM python:3.12-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
# Never install the dev group, also when compose starts the app with `uv run`
ENV UV_NO_DEV=1

WORKDIR /app

# Install dependencies
COPY pyproject.toml .
RUN uv sync --no-dev

# Copy application code
COPY backend/ ./backend/

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
