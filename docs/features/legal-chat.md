# Legal Chat (AI-Jurist)

## Overview

The Legal Chat feature provides an interactive AI assistant that answers legal questions based on the user's actual contracts, with citations and confidence scoring.

## Architecture

```
User Question
     │
     ▼
┌─────────────────┐
│ Knowledge       │  ← PostgreSQL FTS
│ Retriever       │  ← Contract snippets
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Legal Chat      │  ← RAG context
│ Service         │  ← System prompt
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ AI Provider     │  ← Claude/DeepSeek
│ (Anthropic)     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Citation        │  ← Validate citations
│ Validator       │  ← Match to contracts
└────────┬────────┘
         │
         ▼
   Response with
   [File, Page] citations
```

## Anti-Hallucination Mechanisms

### 1. RAG (Retrieval-Augmented Generation)
- AI only sees relevant contract snippets, not the entire internet
- PostgreSQL full-text search with German language support
- Snippets include page numbers for citation

### 2. Citation Requirement
Every factual statement must include a citation:
```
"Die Kündigungsfrist beträgt 3 Monate [Mietvertrag.pdf, S. 5]"
```

### 3. Citation Validation
Backend validates that cited files and pages actually exist in the user's contracts.

### 4. Confidence Scoring
Each response includes a confidence score (0-1):
- **0.8-1.0**: High confidence, direct quote from contract
- **0.5-0.8**: Medium confidence, inference from contract
- **< 0.5**: Low confidence, may need lawyer review

### 5. "Anwalt empfohlen" Badge
Displayed when:
- Question involves complex legal interpretation
- AI confidence is below threshold
- Question involves multiple jurisdictions

## API Endpoints

### Start Conversation
```http
POST /api/v1/legal/conversations
Content-Type: application/json

{
  "title": "Fragen zum Mietvertrag"
}
```

### Ask Question
```http
POST /api/v1/legal/conversations/{id}/ask
Content-Type: application/json

{
  "question": "Wie ist die Kündigungsfrist in meinem Mietvertrag?"
}
```

Response:
```json
{
  "answer": "Laut Ihrem Mietvertrag beträgt die Kündigungsfrist 3 Monate zum Quartalsende [Mietvertrag_Wien.pdf, S. 5].",
  "citations": [
    {
      "file": "Mietvertrag_Wien.pdf",
      "page": 5,
      "snippet": "...Kündigungsfrist beträgt 3 Monate zum Quartalsende..."
    }
  ],
  "confidence": 0.92,
  "requires_lawyer": false
}
```

## System Prompt

The system prompt enforces:
1. German (Austrian) language
2. Professional but accessible tone
3. Mandatory citations for all facts
4. Explicit uncertainty when unsure
5. Recommendation to consult lawyer for complex issues

## Database Schema

```sql
-- Conversations
CREATE TABLE legal_conversations (
  id UUID PRIMARY KEY,
  organization_id UUID NOT NULL,
  user_id UUID NOT NULL,
  title TEXT,
  created_at TIMESTAMP,
  updated_at TIMESTAMP
);

-- Messages
CREATE TABLE legal_messages (
  id UUID PRIMARY KEY,
  conversation_id UUID NOT NULL,
  role TEXT NOT NULL,  -- 'user' or 'assistant'
  content TEXT NOT NULL,
  citations JSONB,
  confidence FLOAT,
  created_at TIMESTAMP
);

-- Full-text search index
CREATE INDEX idx_contracts_fts ON contracts
USING gin(to_tsvector('german', raw_text));
```

## Cost Estimation

- Average query: 2,000 input tokens + 500 output tokens
- DeepSeek: ~$0.001/query
- Claude: ~$0.02/query

## Configuration

```env
# AI Provider
AI_PROVIDER=deepseek  # or 'anthropic'

# For user-managed keys (single-tenant mode)
# Users configure in Settings → API Keys
```

## Related Files

- `backend/src/dealguard/domain/legal/chat_service.py` - Main service
- `backend/src/dealguard/domain/legal/knowledge_retriever.py` - RAG component
- `backend/src/dealguard/infrastructure/ai/prompts/legal_advisor_v1.py` - System prompt
- `backend/src/dealguard/api/routes/legal_chat.py` - API endpoints
- `frontend/src/app/jurist/page.tsx` - Chat UI
- `frontend/src/hooks/useLegalChat.ts` - React hook
