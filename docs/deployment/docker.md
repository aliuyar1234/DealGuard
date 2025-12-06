# Docker Deployment

## Overview

DealGuard uses Docker Compose for both development and production deployments.

## Services

| Service | Image | Port | Description |
|---------|-------|------|-------------|
| `db` | postgres:16 | 5432 | PostgreSQL database |
| `redis` | redis:7 | 6379 | Cache & job queue |
| `minio` | minio/minio | 9000, 9001 | S3-compatible storage |
| `backend` | dealguard-backend | 8000 | FastAPI application |
| `worker` | dealguard-backend | - | Background job worker |
| `frontend` | dealguard-frontend | 3000 | Next.js application |

## Development Setup

### Start All Services
```bash
docker-compose up -d
```

### Start Specific Services
```bash
# Just infrastructure
docker-compose up -d db redis minio

# Add backend
docker-compose up -d backend worker

# Add frontend
docker-compose up -d frontend
```

### View Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
```

### Stop Services
```bash
docker-compose down

# With volume cleanup
docker-compose down -v
```

## Production Setup

### docker-compose.prod.yml

```yaml
version: "3.8"

services:
  db:
    image: postgres:16
    restart: always
    environment:
      POSTGRES_USER: ${DB_USER}
      POSTGRES_PASSWORD: ${DB_PASSWORD}
      POSTGRES_DB: dealguard
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DB_USER}"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    restart: always
    command: redis-server --appendonly yes
    volumes:
      - redisdata:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    restart: always
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    environment:
      - DATABASE_URL=postgresql+asyncpg://${DB_USER}:${DB_PASSWORD}@db:5432/dealguard
      - REDIS_URL=redis://redis:6379/0
      - ENVIRONMENT=production
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  worker:
    build:
      context: ./backend
      dockerfile: Dockerfile
    restart: always
    command: arq dealguard.infrastructure.queue.worker.WorkerSettings
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    environment:
      - DATABASE_URL=postgresql+asyncpg://${DB_USER}:${DB_PASSWORD}@db:5432/dealguard
      - REDIS_URL=redis://redis:6379/0
      - ENVIRONMENT=production

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
      args:
        - NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}
    restart: always
    depends_on:
      - backend

volumes:
  pgdata:
  redisdata:
```

## Dockerfiles

### Backend Dockerfile

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY pyproject.toml .
RUN pip install -e ".[prod]"

# Copy application
COPY src/ src/
COPY alembic/ alembic/
COPY alembic.ini .

# Create non-root user
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["uvicorn", "dealguard.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Frontend Dockerfile

```dockerfile
FROM node:18-alpine AS builder

WORKDIR /app

# Install dependencies
COPY package*.json ./
RUN npm ci

# Build application
COPY . .
ARG NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
RUN npm run build

# Production image
FROM node:18-alpine AS runner

WORKDIR /app

ENV NODE_ENV=production

# Copy built application
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public

EXPOSE 3000

CMD ["node", "server.js"]
```

## Resource Limits

### Development
```yaml
services:
  backend:
    deploy:
      resources:
        limits:
          cpus: '1'
          memory: 512M
```

### Production
```yaml
services:
  backend:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '0.5'
          memory: 512M
```

## Networking

### Internal Network
All services communicate on an internal Docker network:
```yaml
networks:
  default:
    driver: bridge
```

### External Access
Only expose necessary ports:
```yaml
services:
  frontend:
    ports:
      - "3000:3000"  # Or use reverse proxy

  backend:
    # No external port - accessed via reverse proxy
    expose:
      - "8000"
```

## Volumes

### Named Volumes (Persistent)
```yaml
volumes:
  pgdata:
    driver: local
  redisdata:
    driver: local
  documents:
    driver: local
```

### Bind Mounts (Development)
```yaml
services:
  backend:
    volumes:
      - ./backend/src:/app/src:ro  # Hot reload
```

## Health Checks

All services include health checks for orchestration:

```yaml
services:
  backend:
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
```

## Common Commands

```bash
# Build images
docker-compose build

# Build specific service
docker-compose build backend

# Rebuild without cache
docker-compose build --no-cache

# Pull latest images
docker-compose pull

# View running containers
docker-compose ps

# Execute command in container
docker-compose exec backend python -c "print('hello')"

# Run one-off command
docker-compose run --rm backend alembic upgrade head

# Scale service
docker-compose up -d --scale worker=3
```

## Troubleshooting

### Container won't start
```bash
# Check logs
docker-compose logs backend

# Check container status
docker-compose ps

# Inspect container
docker inspect dealguard_backend_1
```

### Database connection issues
```bash
# Test from backend container
docker-compose exec backend python -c "
from dealguard.infrastructure.database.connection import engine
import asyncio
async def test():
    async with engine.begin() as conn:
        result = await conn.execute('SELECT 1')
        print('Connected!')
asyncio.run(test())
"
```

### Disk space issues
```bash
# Cleanup unused resources
docker system prune -a

# Remove unused volumes
docker volume prune
```
