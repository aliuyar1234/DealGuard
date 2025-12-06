# Production Deployment Guide

## Overview

DealGuard is designed for self-hosted single-tenant deployment. Each installation serves one organization with users managing their own AI API keys.

## Prerequisites

- Docker & Docker Compose
- PostgreSQL 16+ (or use Docker)
- Redis 7+ (or use Docker)
- MinIO or S3-compatible storage
- Domain with SSL certificate
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

### 4. Run Migrations
```bash
docker-compose exec backend alembic upgrade head
```

### 5. Access Application
- Frontend: https://your-domain.com
- API: https://your-domain.com/api/v1
- Docs: https://your-domain.com/docs

## Environment Configuration

### Required Variables

```env
# Database
DATABASE_URL=postgresql+asyncpg://user:pass@db:5432/dealguard
DATABASE_SYNC_URL=postgresql://user:pass@db:5432/dealguard

# Redis
REDIS_URL=redis://redis:6379/0

# Storage
S3_ENDPOINT=https://s3.eu-central-1.amazonaws.com
S3_BUCKET=dealguard-documents
S3_ACCESS_KEY=your-access-key
S3_SECRET_KEY=your-secret-key
S3_REGION=eu-central-1

# Security
APP_SECRET_KEY=your-32-char-secret-key-here-xxx

# Auth (Production)
AUTH_PROVIDER=supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_JWT_SECRET=your-jwt-secret
```

### Optional Variables

```env
# AI (users can also configure in Settings)
AI_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-xxx
DEEPSEEK_API_KEY=sk-xxx

# Rate Limiting
RATE_LIMIT_AI=10/minute

# Logging
LOG_LEVEL=INFO
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Reverse Proxy                         │
│                      (nginx/Traefik)                        │
│                          :443                               │
└─────────────────┬───────────────────────────┬───────────────┘
                  │                           │
                  ▼                           ▼
         ┌───────────────┐           ┌───────────────┐
         │   Frontend    │           │    Backend    │
         │   (Next.js)   │           │   (FastAPI)   │
         │    :3000      │           │    :8000      │
         └───────────────┘           └───────┬───────┘
                                             │
                  ┌──────────────────────────┼──────────────────────────┐
                  │                          │                          │
                  ▼                          ▼                          ▼
         ┌───────────────┐           ┌───────────────┐           ┌───────────────┐
         │  PostgreSQL   │           │     Redis     │           │    MinIO/S3   │
         │    :5432      │           │    :6379      │           │    :9000      │
         └───────────────┘           └───────────────┘           └───────────────┘
```

## Security Checklist

### Before Going Live

- [ ] `AUTH_PROVIDER=supabase` (NOT `dev`)
- [ ] Strong `APP_SECRET_KEY` (32+ chars)
- [ ] SSL/TLS enabled
- [ ] Database credentials rotated
- [ ] S3 bucket private
- [ ] Rate limiting configured
- [ ] CORS origins restricted

### Production Validators

DealGuard automatically enforces security in production:

```python
# config.py
@model_validator(mode="after")
def validate_production_settings(self) -> "Settings":
    if self.is_production:
        if self.auth_provider == "dev":
            raise ValueError("AUTH_PROVIDER=dev not allowed in production!")
        if not self.supabase_jwt_secret:
            raise ValueError("SUPABASE_JWT_SECRET required in production!")
    return self
```

## Health Checks

### Backend Health
```bash
curl https://your-domain.com/api/v1/health
```

Expected response:
```json
{
  "status": "healthy",
  "database": "connected",
  "redis": "connected",
  "storage": "connected"
}
```

### AI Health (requires auth)
```bash
curl -H "Authorization: Bearer $TOKEN" \
  https://your-domain.com/api/v1/chat/v2/health
```

## Scaling

### Horizontal Scaling

```yaml
# docker-compose.prod.yml
services:
  backend:
    deploy:
      replicas: 3

  worker:
    deploy:
      replicas: 2
```

### Database Connection Pool

```env
# Adjust based on replicas
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=10
```

## Monitoring

### Logs
```bash
docker-compose logs -f backend worker
```

### Metrics
DealGuard exposes Prometheus metrics at `/metrics` (requires auth).

### Cost Tracking
AI costs are logged to the database. Query with:
```sql
SELECT date(created_at), sum(cost_usd)
FROM ai_usage_logs
GROUP BY 1
ORDER BY 1 DESC;
```

## Backup & Recovery

### Database Backup
```bash
# Using pg_dump
docker-compose exec db pg_dump -U dealguard dealguard > backup.sql

# Restore
docker-compose exec -T db psql -U dealguard dealguard < backup.sql
```

### Document Storage
```bash
# Using MinIO client
mc mirror myminio/dealguard-documents ./backup/documents
```

## Troubleshooting

### Common Issues

**Auth errors in production:**
- Check `AUTH_PROVIDER=supabase`
- Verify `SUPABASE_JWT_SECRET` matches Supabase project

**AI not responding:**
- Check API key in Settings → API Keys
- Test connection with "Verbindung testen" button
- Check rate limits

**Missing documents:**
- Verify S3 credentials
- Check bucket permissions
- Ensure bucket exists and is accessible

### Debug Mode

```env
# Enable detailed logs (NOT for production traffic)
LOG_LEVEL=DEBUG
```

## Updates

### Applying Updates
```bash
git pull origin main
docker-compose -f docker-compose.prod.yml build
docker-compose -f docker-compose.prod.yml up -d
docker-compose exec backend alembic upgrade head
```

### Rollback
```bash
git checkout v1.0.0  # Previous version
docker-compose -f docker-compose.prod.yml build
docker-compose -f docker-compose.prod.yml up -d
docker-compose exec backend alembic downgrade -1
```
