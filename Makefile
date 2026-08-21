.PHONY: up down logs migrate seed dev-api dev-web migrate-local seed-local test-backend test-frontend e2e

up:
	docker compose up --build -d --wait

down:
	docker compose down

logs:
	docker compose logs -f

migrate:
	docker compose run --rm migrate

seed:
	docker compose run --rm seed

dev-api:
	@set -a; test ! -f .env || . ./.env; set +a; echo "Starting API at http://127.0.0.1:$${API_PORT:-8000}"; cd backend && uv run --frozen uvicorn app.main:app --host 127.0.0.1 --port $${API_PORT:-8000}

dev-web:
	@set -a; test ! -f .env || . ./.env; set +a; echo "Starting web at http://127.0.0.1:$${WEB_PORT:-8080}; proxy target: $${VITE_DEV_PROXY_TARGET:-http://127.0.0.1:8000}"; cd frontend && VITE_DEV_PROXY_TARGET=$${VITE_DEV_PROXY_TARGET:-http://127.0.0.1:8000} npm run dev -- --host 127.0.0.1 --port $${WEB_PORT:-8080}

migrate-local:
	@set -a; test ! -f .env || . ./.env; set +a; cd backend && uv run --frozen alembic upgrade head

seed-local:
	@set -a; test ! -f .env || . ./.env; set +a; cd backend && uv run --frozen python ../scripts/seed.py

test-backend:
	cd backend && uv run --frozen pytest

test-frontend:
	cd frontend && npm test

e2e:
	cd frontend && npm run test:e2e
