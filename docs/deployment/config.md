# Configuration Reference

## Overview
DealGuard uses environment variables for configuration. All variables can be set
in a `.env` file or via system environment variables.

## Environment Variables

### Core Settings
| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `APP_ENV` | No | `development` | `development`, `staging`, or `production` |
| `APP_DEBUG` | No | `false` | Enable debug mode |
| `LOG_LEVEL` | No | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `APP_SECRET_KEY` | Yes | - | 32+ char secret for encryption |

### Database
| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DB_USER` | Yes | - | Database user |
| `DB_PASSWORD` | Yes | - | Database password |
| `DB_NAME` | Yes | - | Database name |
| `DATABASE_URL` | Yes | - | PostgreSQL async URL |
| `DATABASE_SYNC_URL` | Yes | - | PostgreSQL sync URL (migrations) |
| `DATABASE_POOL_SIZE` | No | `5` | Connection pool size |
| `DATABASE_MAX_OVERFLOW` | No | `10` | Max overflow connections |

**Example:**
```env
DB_USER=dealguard
DB_PASSWORD=strong-password
DB_NAME=dealguard
DATABASE_URL=postgresql+asyncpg://dealguard:strong-password@postgres:5432/dealguard
DATABASE_SYNC_URL=postgresql://dealguard:strong-password@postgres:5432/dealguard
```

### Redis
| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `REDIS_PASSWORD` | Yes | - | Redis password |
| `REDIS_URL` | Yes | - | Redis connection URL |

**Example:**
```env
REDIS_PASSWORD=strong-redis-password
REDIS_URL=redis://:strong-redis-password@redis:6379/0
```

### Storage (S3/MinIO)
| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `MINIO_ROOT_USER` | Dev | - | MinIO root username (only for bundled MinIO) |
| `MINIO_ROOT_PASSWORD` | Dev | - | MinIO root password (only for bundled MinIO) |
| `S3_ENDPOINT` | Yes | - | S3 endpoint URL |
| `S3_ACCESS_KEY` | Yes | - | Access key ID |
| `S3_SECRET_KEY` | Yes | - | Secret access key |
| `S3_BUCKET` | Yes | - | Bucket name |
| `S3_REGION` | No | `eu-central-1` | AWS region |

**Example (MinIO):**
```env
S3_ENDPOINT=http://minio:9000
S3_ACCESS_KEY=minioadmin
S3_SECRET_KEY=change-me
S3_BUCKET=dealguard-documents
S3_REGION=eu-central-1
```

### Authentication
| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `AUTH_PROVIDER` | No | `dev` | `dev` or `supabase` |
| `SUPABASE_URL` | Prod | - | Supabase project URL |
| `SUPABASE_JWT_SECRET` | Prod | - | Supabase JWT secret |
| `SUPABASE_ANON_KEY` | No | - | Supabase anon key |
| `SUPABASE_SERVICE_ROLE_KEY` | No | - | Supabase service role key |

### AI Providers
| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `AI_PROVIDER` | No | `anthropic` | `anthropic` or `deepseek` |
| `ANTHROPIC_API_KEY` | No | - | Anthropic API key |
| `ANTHROPIC_MODEL` | No | `claude-sonnet-4-20250514` | Model name |
| `ANTHROPIC_MAX_TOKENS` | No | `4096` | Max response tokens |
| `DEEPSEEK_API_KEY` | No | - | DeepSeek API key |
| `DEEPSEEK_MODEL` | No | `deepseek-chat` | Model name |
| `DEEPSEEK_BASE_URL` | No | `https://api.deepseek.com` | API base URL |

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
| `CORS_ORIGINS` | No | `http://localhost:3000` | Allowed origins (comma-separated) |

### Edge / TLS
| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `APP_DOMAIN` | Prod | - | Public domain for TLS |
| `TLS_EMAIL` | Prod | - | ACME registration email |

## Validation

### Production Requirements
DealGuard validates settings on startup:

- `AUTH_PROVIDER` must be `supabase`
- `SUPABASE_JWT_SECRET` must be set
- `APP_SECRET_KEY` must be 32+ chars and not a placeholder
- `APP_DEBUG` must be `false`
- `DATABASE_URL`/`DATABASE_SYNC_URL` must not use defaults
- `REDIS_URL` must include credentials
- `S3_ACCESS_KEY`/`S3_SECRET_KEY` must not be defaults
- `CORS_ORIGINS` must be restricted

### Checking Configuration
```bash
python -c "from dealguard.config import get_settings; print(get_settings())"
```

## Security Notes

1. Never commit `.env` to git (use `.env.example`)
2. Rotate secrets regularly
3. Use strong passwords for DB and Redis
4. Restrict CORS to your domains
5. Use TLS for all traffic
