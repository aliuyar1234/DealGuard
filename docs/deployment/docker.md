# Docker Deployment

## Overview
DealGuard uses Docker Compose for local development and production deployments.

- `docker-compose.yml` is optimized for local development.
- `docker-compose.prod.yml` is production-ready and uses Caddy for TLS termination.

## Services
| Service | Image | Port | Description |
|---------|-------|------|-------------|
| `postgres` | postgres:16.4-alpine | 5432 (dev only) | PostgreSQL database |
| `redis` | redis:7.2-alpine | 6379 (dev only) | Cache and job queue |
| `minio` | minio/minio:RELEASE.2024-06-13T22-53-53Z | 9000, 9001 (dev or prod profile) | S3-compatible storage |
| `backend` | dealguard-backend | 8000 (internal) | FastAPI application |
| `worker` | dealguard-backend | - | Background job worker |
| `frontend` | dealguard-frontend | 3000 (internal) | Next.js application |
| `edge` | caddy:2.8.4-alpine | 80, 443 | TLS reverse proxy (production) |

## Development Setup

### Start All Services
```bash
docker-compose up -d
```

### Start Specific Services
```bash
# Just infrastructure
docker-compose up -d postgres redis minio

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

### 1. Configure Environment
```bash
cp .env.example .env
# Edit .env with your settings
```

### 2. Start Services
```bash
docker-compose -f docker-compose.prod.yml up -d
```

### 3. (Optional) Use MinIO in Production
```bash
docker-compose -f docker-compose.prod.yml --profile minio up -d
```

### 4. Run Migrations
```bash
docker-compose -f docker-compose.prod.yml exec backend alembic upgrade head
```

## Networking

Production uses an internal Docker network for all services. Only the `edge`
(Caddy) container is exposed to the host on ports 80 and 443.

The Caddy configuration lives at `deploy/Caddyfile`.

Set these variables in `.env` for TLS:

```env
APP_DOMAIN=example.com
TLS_EMAIL=admin@example.com
```

## Health Checks

- Liveness: `GET /health`
- Readiness: `GET /ready`

## Volumes

```yaml
volumes:
  postgres_data:
  redis_data:
  minio_data:
  caddy_data:
  caddy_config:
```

## Common Commands

```bash
# Build images
docker-compose -f docker-compose.prod.yml build

# View running containers
docker-compose -f docker-compose.prod.yml ps

# Execute command in container
docker-compose -f docker-compose.prod.yml exec backend python -c "print('hello')"

# Scale workers
docker-compose -f docker-compose.prod.yml up -d --scale worker=3
```
