.PHONY: up down logs migrate seed dev-api dev-web migrate-local seed-local test-backend test-frontend e2e validate-load-env load-cached load-missing load-hot load-degraded

BASE_URL ?= http://localhost:8080
PRODUCT_ID ?= 0198c8bc-1234-7abc-8def-0123456789ab
# Freeze command-line values as raw simple variables so GNU make never expands
# user-supplied $(shell ...), function, or variable syntax while exporting them.
override BASE_URL := $(value BASE_URL)
override PRODUCT_ID := $(value PRODUCT_ID)
export BASE_URL PRODUCT_ID

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
	@set -a; test ! -f .env || . ./.env; set +a; cd backend && PYTHONPATH=. uv run --frozen python ../scripts/seed.py

test-backend:
	cd backend && uv run --frozen pytest

test-frontend:
	cd frontend && npm test

e2e:
	cd frontend && npm run test:e2e

validate-load-env:
	@case "$$PRODUCT_ID" in *[!\ -~]*) printf '%s\n' 'PRODUCT_ID must contain printable ASCII only' >&2; exit 2;; esac
	@printf '%s\n' "$$PRODUCT_ID" | grep -Eq '^[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12}$$' || { printf '%s\n' 'PRODUCT_ID must be a UUID' >&2; exit 2; }
	@case "$$BASE_URL" in *[!\ -~]*) printf '%s\n' 'BASE_URL must contain printable ASCII only' >&2; exit 2;; esac
	@printf '%s\n' "$$BASE_URL" | grep -Eq '^https?://[]A-Za-z0-9._:[-]+(/[A-Za-z0-9._~:/?#@!$$&()*+,;=%-]*)?$$' || { printf '%s\n' 'BASE_URL must be an HTTP(S) URL without whitespace or shell syntax' >&2; exit 2; }

load-cached: validate-load-env
	k6 run -e SCENARIO=cached -e BASE_URL="$$BASE_URL" -e PRODUCT_ID="$$PRODUCT_ID" loadtest/product-detail.js

load-missing: validate-load-env
	k6 run -e SCENARIO=missing -e BASE_URL="$$BASE_URL" -e PRODUCT_ID="$$PRODUCT_ID" loadtest/product-detail.js

load-hot: validate-load-env
	@printf 'Operator step required: delete product:v1:%s immediately before this run (see docs/performance/report-template.md).\n' "$$PRODUCT_ID"
	k6 run -e SCENARIO=hot-expiry -e BASE_URL="$$BASE_URL" -e PRODUCT_ID="$$PRODUCT_ID" loadtest/product-detail.js

load-degraded: validate-load-env
	@printf '%s\n' 'Operator step required: stop/pause Redis before this run and guarantee recovery afterward; this target never changes Redis state.'
	@printf '%s\n' 'See docs/performance/report-template.md for Compose and local-service procedures.'
	k6 run -e BASE_URL="$$BASE_URL" -e PRODUCT_ID="$$PRODUCT_ID" loadtest/redis-degraded.js
