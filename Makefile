.PHONY: help dev stop logs test lint migrate shell clean

# Default target
help:
	@echo "DealGuard - Available Commands"
	@echo "=============================="
	@echo ""
	@echo "Development:"
	@echo "  make dev        Start all services (PostgreSQL, Redis, MinIO, Backend, Frontend)"
	@echo "  make dev-infra  Start only infrastructure (DB, Redis, MinIO)"
	@echo "  make stop       Stop all services"
	@echo "  make logs       Tail logs from all services"
	@echo "  make clean      Stop and remove all containers, volumes"
	@echo ""
	@echo "Backend:"
	@echo "  make backend    Start backend only (requires infra running)"
	@echo "  make worker     Start background worker only"
	@echo "  make shell      Open Python shell in backend container"
	@echo "  make migrate    Run database migrations"
	@echo "  make migrate-new NAME=xyz  Create new migration"
	@echo ""
	@echo "Frontend:"
	@echo "  make frontend   Start frontend only"
	@echo ""
	@echo "Quality:"
	@echo "  make test       Run all tests"
	@echo "  make lint       Run linters (ruff, mypy, eslint)"
	@echo "  make format     Auto-format code"
	@echo ""
	@echo "Setup:"
	@echo "  make install    Install all dependencies locally"
	@echo "  make setup      First-time setup (install + migrate + seed)"

# ============================================
# Development
# ============================================

dev:
	docker-compose up -d
	@echo ""
	@echo "Services starting..."
	@echo "  Backend:   http://localhost:8000"
	@echo "  Frontend:  http://localhost:3000"
	@echo "  API Docs:  http://localhost:8000/docs"
	@echo "  MinIO:     http://localhost:9001 (minio/minio123)"
	@echo ""
	@echo "Run 'make logs' to see output"

dev-infra:
	docker-compose up -d postgres redis minio minio-setup
	@echo ""
	@echo "Infrastructure running:"
	@echo "  PostgreSQL: localhost:5432"
	@echo "  Redis:      localhost:6379"
	@echo "  MinIO:      localhost:9000 (API) / localhost:9001 (Console)"

stop:
	docker-compose down

logs:
	docker-compose logs -f

clean:
	docker-compose down -v --remove-orphans
	@echo "All containers and volumes removed"

# ============================================
# Backend
# ============================================

backend:
	docker-compose up -d backend

worker:
	docker-compose up -d worker

shell:
	docker-compose exec backend python

migrate:
	docker-compose exec backend alembic upgrade head

migrate-new:
ifndef NAME
	$(error NAME is required. Usage: make migrate-new NAME=add_users_table)
endif
	docker-compose exec backend alembic revision --autogenerate -m "$(NAME)"

# ============================================
# Frontend
# ============================================

frontend:
	docker-compose up -d frontend

# ============================================
# Quality
# ============================================

test:
	docker-compose exec backend pytest -v
	docker-compose exec frontend npm test

test-backend:
	docker-compose exec backend pytest -v

test-frontend:
	docker-compose exec frontend npm test

lint:
	docker-compose exec backend ruff check src
	docker-compose exec backend mypy src
	docker-compose exec frontend npm run lint

lint-backend:
	docker-compose exec backend ruff check src
	docker-compose exec backend mypy src

lint-frontend:
	docker-compose exec frontend npm run lint

format:
	docker-compose exec backend ruff format src
	docker-compose exec frontend npm run format

# ============================================
# Setup
# ============================================

install:
	cd backend && pip install -e ".[dev]"
	cd frontend && npm install

setup: dev-infra
	@echo "Waiting for services to be ready..."
	@sleep 5
	$(MAKE) migrate
	@echo ""
	@echo "Setup complete! Run 'make dev' to start all services."

# ============================================
# Utilities
# ============================================

# Generate TypeScript types from OpenAPI
generate-types:
	docker-compose exec backend python -c "from dealguard.main import app; import json; print(json.dumps(app.openapi()))" > docs/api/openapi.json
	cd frontend && npx openapi-typescript ../docs/api/openapi.json -o src/lib/api/types.ts

# Database shell
db-shell:
	docker-compose exec postgres psql -U dealguard -d dealguard

# Redis CLI
redis-cli:
	docker-compose exec redis redis-cli
