FROM ghcr.io/astral-sh/uv:0.8.13 AS uv

FROM python:3.12.11-slim-bookworm AS builder
COPY --from=uv /uv /uvx /bin/
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

FROM python:3.12.11-slim-bookworm AS runtime
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
RUN groupadd --system --gid 10001 stockstack \
    && useradd --system --uid 10001 --gid stockstack --home-dir /app stockstack
WORKDIR /app
COPY --from=builder --chown=stockstack:stockstack /app/.venv .venv
COPY --chown=stockstack:stockstack alembic.ini ./
COPY --chown=stockstack:stockstack alembic ./alembic
COPY --chown=stockstack:stockstack app ./app
RUN mkdir -p /app/uploads && chown stockstack:stockstack /app/uploads
USER stockstack
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
