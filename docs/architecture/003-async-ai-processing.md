# ADR-003: Asynchrone AI-Verarbeitung via Queue

## Status
**Accepted** (2024-12-04)

## Kontext

Contract Analysis dauert 30-60 Sekunden:
- PDF-Extraktion: 1-5s
- AI-Analyse: 20-50s (Claude API)
- DB-Writes: <1s

Problem: HTTP-Requests sollten nicht 60s dauern wegen:
- Browser Timeouts
- Load Balancer Limits
- Schlechte UX

## Entscheidung

**Queue-basierte Verarbeitung mit Polling:**

```
┌─────────┐     ┌─────────┐     ┌─────────┐     ┌─────────┐
│ Frontend│────▶│   API   │────▶│  Redis  │────▶│ Worker  │
│         │     │         │     │  Queue  │     │         │
└─────────┘     └─────────┘     └─────────┘     └─────────┘
     │               │                               │
     │  POST /contracts (202 Accepted)               │
     │◀──────────────┤                               │
     │               │                               │
     │  GET /contracts/{id} (status: processing)     │
     │◀──────────────┤                               │
     │               │                               │
     │               │         analyze_contract_job  │
     │               │◀──────────────────────────────┤
     │               │                               │
     │  GET /contracts/{id} (status: completed)      │
     │◀──────────────┤                               │
```

**Stack:**
- **ARQ** (async Redis queue) für Jobs
- **Redis** als Broker
- **Polling** im Frontend (3s Intervall)

**Alternative verworfen:** WebSockets
- Komplexer (Connection Management)
- Nicht nötig für 1 Request/Minute Use Case

## Implementierung

**Upload queued Job:**
```python
# backend/src/dealguard/api/routes/contracts.py
@router.post("/")
async def upload_contract(...):
    contract = await service.upload_contract(...)
    await enqueue_contract_analysis(
        contract_id=contract.id,
        organization_id=user.organization_id,
        user_id=user.id,
    )
    return UploadResponse(status="pending")
```

**Worker verarbeitet:**
```python
# backend/src/dealguard/infrastructure/queue/worker.py
async def analyze_contract_job(ctx, contract_id, ...):
    service = ctx["contract_service"]
    await service.perform_analysis(UUID(contract_id))
```

**Frontend pollt:**
```typescript
// frontend/src/app/vertraege/[id]/page.tsx
useEffect(() => {
  if (contract?.status === 'processing') {
    const interval = setInterval(loadContract, 3000);
    return () => clearInterval(interval);
  }
}, [contract?.status]);
```

## Konsequenzen

### Positiv
- Zuverlässig (Jobs überleben API-Restarts)
- Skalierbar (mehr Worker = mehr Throughput)
- Retry-fähig (ARQ hat eingebaute Retries)
- UX: User sieht sofort "wird verarbeitet"

### Negativ
- Komplexer als sync (Redis + Worker Prozess)
- Polling ist nicht real-time (~3s Delay)
- Debugging über mehrere Prozesse

### Metriken
- Job Timeout: 5 Minuten
- Max Retries: 3
- Polling Interval: 3 Sekunden

## Referenzen

- `backend/src/dealguard/infrastructure/queue/client.py` - Enqueuing
- `backend/src/dealguard/infrastructure/queue/worker.py` - Worker
- `frontend/src/app/vertraege/[id]/page.tsx` - Polling
