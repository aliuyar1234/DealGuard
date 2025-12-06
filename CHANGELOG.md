# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0] - 2024-12-06

### Added

#### MCP Server v2 (Model Context Protocol)
- 13 Claude tools for Austrian legal data access
- RIS integration (Austrian federal laws, court decisions)
- Ediktsdatei integration (insolvency, auctions)
- Pydantic v2 input validation for all tools
- Tool annotations (readOnlyHint, destructiveHint, idempotentHint)
- Response pagination with has_more, next_offset, total_count
- Character limits (25000) with truncation hints

#### Proactive Monitoring (AI-Jurist)
- Automatic deadline extraction from contracts
- Smart alerts for upcoming and overdue deadlines
- Risk Radar with weighted scoring across 4 categories
- Daily risk snapshots for trend analysis
- Alert lifecycle management (view, resolve, snooze, dismiss)

#### Austrian Data Sources
- OpenFirmenbuch integration (company registry)
- OpenSanctions integration (sanctions/PEP screening)
- Full RIS OGD API integration (laws, court decisions)
- Ediktsdatei IWG API integration (insolvency data)

#### Self-Hosted Single-Tenant Mode
- User-managed API keys (Anthropic/DeepSeek)
- Fernet encryption for API keys at rest
- No multi-tenant complexity for self-hosted deployments

#### AI Chat v2
- Claude tool-calling with MCP integration
- DeepSeek support (OpenAI-compatible API)
- Cost tracking for all API calls
- Retry logic with exponential backoff
- Anti-hallucination system prompt

### Changed
- CORS now restricted in production (was permissive)
- Dev auth provider blocked in production environment
- Contract analysis prompt updated for Austrian law (ABGB/UGB/KSchG)
- Service architecture refactored to modular handlers

### Security
- Production validator prevents dev auth in production
- API key encryption with Fernet
- Rate limiting on AI endpoints
- JWT validation for all protected routes

## [1.0.0] - 2024-11-XX

### Added

#### Contract Analysis
- PDF and DOCX document processing
- AI-powered contract analysis with risk scoring
- Finding categorization (critical, high, medium, low)
- Clause extraction and annotation
- Full-text search with PostgreSQL

#### Partner Intelligence
- Partner database with CRUD operations
- External check integration (mock providers)
- Risk scoring with weighted categories
- Watchlist management
- Alert system for partner changes

#### Legal Chat (AI-Jurist)
- RAG-based contract search
- Citation validation
- Confidence scoring
- Anti-hallucination safeguards
- Conversation history

#### Infrastructure
- FastAPI backend with async support
- Next.js 14 frontend with App Router
- PostgreSQL with SQLAlchemy 2.0
- Redis + ARQ for background jobs
- MinIO/S3 for document storage
- Supabase Auth integration
- Dev auth provider for local development

### Security
- Multi-tenant isolation via organization_id
- JWT-based authentication
- Soft delete for all records
- Audit logging
