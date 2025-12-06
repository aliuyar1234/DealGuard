# DealGuard Backend

FastAPI backend for DealGuard - Austrian Legal Infrastructure as a Service.

## Features

- **Vertragsanalyse**: AI-powered contract analysis with risk scoring
- **Partner-Intelligence**: Company verification, sanctions screening, insolvency checks
- **AI Legal Chat**: RAG-based chat with real Austrian legal data
- **Proactive Monitoring**: Deadline tracking, risk radar, smart alerts
- **MCP Server**: 13 tools for LLMs with access to Austrian legal databases

## Austrian Legal Data APIs

| Datenquelle | Was drin ist | Kosten |
|-------------|--------------|--------|
| **RIS OGD** | Alle Bundesgesetze, OGH-Urteile | GRATIS |
| **Ediktsdatei** | Insolvenzen, Versteigerungen | GRATIS |
| **OpenFirmenbuch** | Firmendaten, Geschäftsführer | GRATIS |
| **OpenSanctions** | EU/UN/US Sanktionslisten, PEP | GRATIS |

## Tech Stack

- Python 3.12
- FastAPI (async)
- SQLAlchemy 2.0 + Alembic
- PostgreSQL 16
- Redis + ARQ (background jobs)
- Anthropic Claude / DeepSeek (AI)
- Fernet encryption (API keys, contract text)
- slowapi (rate limiting)

## Setup

### Prerequisites

- Python 3.12+
- PostgreSQL 16
- Redis

### Installation

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate     # Windows

# Install dependencies
pip install -e ".[dev]"

# Generate APP_SECRET_KEY (REQUIRED!)
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Copy and configure environment
cp ../.env.example ../.env
# Edit .env with your APP_SECRET_KEY and other settings

# Run migrations
alembic upgrade head

# Start server
uvicorn dealguard.main:app --reload
```

### Development Mode

For local development without Supabase:

```bash
# In .env
AUTH_PROVIDER=dev
AI_PROVIDER=deepseek  # ~20x cheaper than Anthropic
```

## Project Structure

```
backend/
├── src/dealguard/
│   ├── api/                  # HTTP Routes + Rate Limiting
│   │   ├── routes/
│   │   │   ├── contracts.py
│   │   │   ├── partners.py
│   │   │   ├── chat_v2.py
│   │   │   ├── proactive.py
│   │   │   └── settings.py
│   │   └── ratelimit.py
│   ├── domain/               # Business Logic
│   │   ├── chat/             # AI Chat Service
│   │   ├── contracts/        # Contract Analysis
│   │   ├── legal/            # Legal Chat (RAG)
│   │   ├── partners/         # Partner Intelligence
│   │   └── proactive/        # Alerts & Deadlines
│   ├── infrastructure/       # External Services
│   │   ├── ai/               # Anthropic/DeepSeek Clients
│   │   ├── auth/             # Supabase/Dev Auth
│   │   ├── database/         # SQLAlchemy Models
│   │   ├── document/         # PDF/DOCX Extraction
│   │   ├── external/         # OpenFirmenbuch, OpenSanctions
│   │   ├── queue/            # ARQ Worker
│   │   └── storage/          # S3/MinIO
│   ├── mcp/                  # MCP Server + 13 Tools
│   │   ├── server_v2.py
│   │   ├── models.py
│   │   ├── ris_client.py
│   │   └── ediktsdatei_client.py
│   ├── shared/               # Crypto, Logging
│   ├── config.py             # Pydantic Settings
│   └── main.py               # FastAPI App
├── alembic/                  # DB Migrations
│   └── versions/
│       ├── 001_initial.py
│       ├── 002_add_partners.py
│       ├── 003_add_legal_chat.py
│       └── 004_add_proactive_system.py
└── tests/                    # 147 Tests
    ├── unit/                 # 76 Unit Tests
    └── integration/          # 71 Integration Tests
```

## API Endpoints

### Contracts
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/contracts/` | Upload contract |
| GET | `/api/v1/contracts/` | List contracts |
| GET | `/api/v1/contracts/{id}` | Get contract with analysis |
| POST | `/api/v1/contracts/{id}/analyze` | Start analysis |
| DELETE | `/api/v1/contracts/{id}` | Delete contract |

### Partners
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/partners/` | List partners |
| POST | `/api/v1/partners/` | Create partner |
| GET | `/api/v1/partners/{id}` | Get partner details |
| POST | `/api/v1/partners/{id}/checks` | Run checks |
| GET | `/api/v1/partners/{id}/alerts` | Get alerts |

### Chat (AI Legal Assistant)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/chat/v2` | Chat with real legal data |
| GET | `/api/v1/chat/v2/tools` | Available tools |
| GET | `/api/v1/chat/v2/health` | Health check |

### Proactive
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/proactive/deadlines` | Get deadlines |
| GET | `/api/v1/proactive/alerts` | Get alerts |
| GET | `/api/v1/proactive/risk-radar` | Risk radar |

### Settings
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/settings` | Load settings |
| PUT | `/api/v1/settings/api-keys` | Save API keys |
| GET | `/api/v1/settings/check-ai` | Test AI connection |

## Rate Limits

| Endpoint Type | Limit |
|---------------|-------|
| General API | 100/minute |
| Auth (Login) | 5/minute |
| File Upload | 10/minute |
| AI Endpoints | 20/minute |
| Search | 30/minute |
| Health | 60/minute |

## Security

- **Encryption at Rest**: Contract text and API keys encrypted with Fernet
- **APP_SECRET_KEY Required**: No insecure defaults
- **Rate Limiting**: slowapi with configurable limits
- **Soft Deletes**: `deleted_at IS NULL` automatically filtered
- **CORS Configuration**: Only allowed origins
- **Input Validation**: Pydantic v2 with constraints

## Testing

```bash
# All tests
python -m pytest tests/ -v

# Unit tests only (no DB needed)
python -m pytest tests/unit/ -v

# Integration tests (needs Docker)
python -m pytest tests/integration/ -v

# With coverage
python -m pytest tests/ -v --cov=dealguard --cov-report=html
```

## API Documentation

When running locally, visit http://localhost:8000/docs for the interactive Swagger UI.

## License

MIT License
