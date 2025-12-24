# Production Deployment Guide

## Overview
DealGuard is designed for self-hosted single-tenant deployments. The production
stack uses `docker-compose.prod.yml` and Caddy as the TLS-terminating reverse
proxy.

## Prerequisites
- Docker and Docker Compose
- PostgreSQL 16+ (or use the bundled container)
- Redis 7+ (or use the bundled container)
- S3-compatible storage (MinIO via profile or managed S3)
- Domain name with DNS pointing to the host
- AI API key (Anthropic or DeepSeek)

## Quick Start with Docker

### 1. Clone Repository
```bash
git clone https://github.com/yourorg/dealguard.git
cd dealguard
```

### 2. Configure Environment
```bash
cp .env.example .env
# Edit .env with your settings
```

### 3. Start Services
```bash
docker-compose -f docker-compose.prod.yml up -d
```

### 4. (Optional) Use MinIO in Production
```bash
docker-compose -f docker-compose.prod.yml --profile minio up -d
```

### 5. Run Migrations
```bash
docker-compose -f docker-compose.prod.yml exec backend alembic upgrade head
```

### 6. Access Application
- Frontend: https://your-domain.com
- API: https://your-domain.com/api/v1
- Docs: https://your-domain.com/docs

## Environment Configuration

### Required Variables
```env
# Application
APP_SECRET_KEY=your-32-char-secret-key-here
APP_ENV=production
APP_DEBUG=false
CORS_ORIGINS=https://your-domain.com

# Database
DB_USER=dealguard
DB_PASSWORD=strong-password
DB_NAME=dealguard
DATABASE_URL=postgresql+asyncpg://dealguard:strong-password@postgres:5432/dealguard
DATABASE_SYNC_URL=postgresql://dealguard:strong-password@postgres:5432/dealguard

# Redis
REDIS_PASSWORD=strong-redis-password
REDIS_URL=redis://:strong-redis-password@redis:6379/0

# Storage
S3_ENDPOINT=https://s3.eu-central-1.amazonaws.com
S3_BUCKET=dealguard-documents
S3_ACCESS_KEY=your-access-key
S3_SECRET_KEY=your-secret-key
S3_REGION=eu-central-1

# Auth
AUTH_PROVIDER=supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_JWT_SECRET=your-jwt-secret

# Edge / TLS
APP_DOMAIN=your-domain.com
TLS_EMAIL=admin@your-domain.com
```

### Optional Variables
```env
# AI
AI_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-xxx
DEEPSEEK_API_KEY=sk-xxx

# Rate Limiting
RATE_LIMIT_AI=10/minute

# Logging
LOG_LEVEL=INFO
```

## Security Checklist

- [ ] `AUTH_PROVIDER=supabase` (NOT `dev`)
- [ ] Strong `APP_SECRET_KEY` (32+ chars)
- [ ] `APP_ENV=production` and `APP_DEBUG=false`
- [ ] TLS enabled (Caddy with valid DNS)
- [ ] Database and Redis credentials rotated
- [ ] S3 bucket private
- [ ] CORS origins restricted to production domains

## Health Checks

### Backend
```bash
curl https://your-domain.com/health
```

### Readiness
```bash
curl https://your-domain.com/ready
```

## Scaling

```bash
# Scale workers
docker-compose -f docker-compose.prod.yml up -d --scale worker=3

# Scale backend (Caddy will load-balance)
docker-compose -f docker-compose.prod.yml up -d --scale backend=2
```

## Monitoring

### Logs
```bash
docker-compose -f docker-compose.prod.yml logs -f backend worker
```

### Metrics
DealGuard exposes Prometheus metrics at `/metrics` (requires auth).

## Backup & Recovery

### Database Backup
```bash
# Using pg_dump
docker-compose -f docker-compose.prod.yml exec postgres pg_dump -U dealguard dealguard > backup.sql

# Restore
docker-compose -f docker-compose.prod.yml exec -T postgres psql -U dealguard dealguard < backup.sql
```

### Document Storage
```bash
# Using MinIO client
mc mirror myminio/dealguard-documents ./backup/documents
```

## Updates

### Applying Updates
```bash
git pull origin main
docker-compose -f docker-compose.prod.yml build
docker-compose -f docker-compose.prod.yml up -d
docker-compose -f docker-compose.prod.yml exec backend alembic upgrade head
```

### Rollback
```bash
git checkout v1.0.0  # Previous version
docker-compose -f docker-compose.prod.yml build
docker-compose -f docker-compose.prod.yml up -d
docker-compose -f docker-compose.prod.yml exec backend alembic downgrade -1
```
