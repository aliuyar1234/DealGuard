# Configuration Reference

## Overview

DealGuard uses environment variables for configuration. All variables can be set in a `.env` file or as system environment variables.

## Environment Variables

### Core Settings

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ENVIRONMENT` | No | `development` | `development`, `staging`, or `production` |
| `DEBUG` | No | `false` | Enable debug mode |
| `LOG_LEVEL` | No | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `APP_SECRET_KEY` | **Yes** | - | 32+ char secret for encryption |

### Database

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | **Yes** | - | PostgreSQL async URL |
| `DATABASE_SYNC_URL` | **Yes** | - | PostgreSQL sync URL (for migrations) |
| `DATABASE_POOL_SIZE` | No | `10` | Connection pool size |
| `DATABASE_MAX_OVERFLOW` | No | `20` | Max overflow connections |

**Example:**
```env
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/dealguard
DATABASE_SYNC_URL=postgresql://user:pass@localhost:5432/dealguard
```

### Redis

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `REDIS_URL` | **Yes** | - | Redis connection URL |

**Example:**
```env
REDIS_URL=redis://localhost:6379/0
```

### Storage (S3/MinIO)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `S3_ENDPOINT` | **Yes** | - | S3 endpoint URL |
| `S3_ACCESS_KEY` | **Yes** | - | Access key ID |
| `S3_SECRET_KEY` | **Yes** | - | Secret access key |
| `S3_BUCKET` | **Yes** | - | Bucket name |
| `S3_REGION` | No | `eu-central-1` | AWS region |

**Example (MinIO):**
```env
S3_ENDPOINT=http://localhost:9000
S3_ACCESS_KEY=minioadmin
S3_SECRET_KEY=minioadmin
S3_BUCKET=dealguard-documents
```

**Example (AWS S3):**
```env
S3_ENDPOINT=https://s3.eu-central-1.amazonaws.com
S3_ACCESS_KEY=AKIAIOSFODNN7EXAMPLE
S3_SECRET_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
S3_BUCKET=dealguard-documents
S3_REGION=eu-central-1
```

### Authentication

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `AUTH_PROVIDER` | No | `dev` | `dev` or `supabase` |
| `SUPABASE_URL` | Prod | - | Supabase project URL |
| `SUPABASE_JWT_SECRET` | Prod | - | Supabase JWT secret |

**Development (no Supabase needed):**
```env
AUTH_PROVIDER=dev
```

**Production:**
```env
AUTH_PROVIDER=supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_JWT_SECRET=your-jwt-secret
```

### AI Providers

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `AI_PROVIDER` | No | `anthropic` | `anthropic` or `deepseek` |
| `ANTHROPIC_API_KEY` | No | - | Anthropic API key |
| `ANTHROPIC_MODEL` | No | `claude-3-opus-20240229` | Model name |
| `ANTHROPIC_MAX_TOKENS` | No | `4096` | Max response tokens |
| `DEEPSEEK_API_KEY` | No | - | DeepSeek API key |
| `DEEPSEEK_MODEL` | No | `deepseek-chat` | Model name |
| `DEEPSEEK_BASE_URL` | No | `https://api.deepseek.com/v1` | API base URL |

**Note:** Users can also configure AI keys in Settings → API Keys. User settings override environment variables.

### Single-Tenant Mode

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SINGLE_TENANT_MODE` | No | `true` | Enable single-tenant mode |
| `DEFAULT_ORGANIZATION_ID` | No | (generated) | Default org UUID |
| `DEFAULT_USER_ID` | No | (generated) | Default user UUID |

### Rate Limiting

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `RATE_LIMIT_DEFAULT` | No | `100/minute` | Default rate limit |
| `RATE_LIMIT_AI` | No | `10/minute` | AI endpoint rate limit |

### CORS

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `CORS_ORIGINS` | No | `*` (dev) | Allowed origins (comma-separated) |

**Example:**
```env
CORS_ORIGINS=https://app.dealguard.at,https://dealguard.at
```

## Configuration Files

### .env.example
```env
# DealGuard Configuration
# Copy to .env and fill in values

# ===================
# Core Settings
# ===================
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=INFO
APP_SECRET_KEY=change-me-to-a-32-char-secret-key

# ===================
# Database
# ===================
DATABASE_URL=postgresql+asyncpg://dealguard:dealguard@localhost:5432/dealguard
DATABASE_SYNC_URL=postgresql://dealguard:dealguard@localhost:5432/dealguard

# ===================
# Redis
# ===================
REDIS_URL=redis://localhost:6379/0

# ===================
# Storage
# ===================
S3_ENDPOINT=http://localhost:9000
S3_ACCESS_KEY=minioadmin
S3_SECRET_KEY=minioadmin
S3_BUCKET=dealguard-documents

# ===================
# Authentication
# ===================
AUTH_PROVIDER=dev
# SUPABASE_URL=https://your-project.supabase.co
# SUPABASE_JWT_SECRET=your-jwt-secret

# ===================
# AI Providers
# ===================
AI_PROVIDER=deepseek
# ANTHROPIC_API_KEY=sk-ant-xxx
DEEPSEEK_API_KEY=sk-xxx
```

## Validation

### Production Requirements

DealGuard validates settings on startup:

```python
# In production:
# - AUTH_PROVIDER must be 'supabase'
# - SUPABASE_JWT_SECRET must be set
# - APP_SECRET_KEY must be at least 32 characters
```

### Checking Configuration

```bash
# Start backend and check for errors
docker-compose up backend

# Or run validation directly
python -c "from dealguard.config import get_settings; print(get_settings())"
```

## Security Notes

1. **Never commit `.env` to git** - Only `.env.example`
2. **Rotate secrets regularly** - Especially `APP_SECRET_KEY`
3. **Use strong passwords** - Database, Redis, MinIO
4. **Restrict CORS** - Only your domain in production
5. **Use SSL** - All traffic should be encrypted

## Environment-Specific Configs

### Development
```env
ENVIRONMENT=development
AUTH_PROVIDER=dev
DEBUG=true
LOG_LEVEL=DEBUG
```

### Staging
```env
ENVIRONMENT=staging
AUTH_PROVIDER=supabase
DEBUG=false
LOG_LEVEL=INFO
```

### Production
```env
ENVIRONMENT=production
AUTH_PROVIDER=supabase
DEBUG=false
LOG_LEVEL=WARNING
CORS_ORIGINS=https://your-domain.com
```
