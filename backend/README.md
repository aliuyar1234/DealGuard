# DealGuard Backend

FastAPI backend for DealGuard - AI-powered contract analysis and partner intelligence.

## Setup

```bash
# Install dependencies
pip install -e ".[dev]"

# Run migrations
alembic upgrade head

# Start server
uvicorn dealguard.main:app --reload
```

## API Documentation

When running locally, visit http://localhost:8000/docs for the interactive API documentation.
