# Proactive Monitoring

## Overview

The Proactive Monitoring system automatically tracks contract deadlines, generates alerts, and provides a unified Risk Radar view across all contracts and partners.

## Features

### 1. Deadline Extraction
AI automatically extracts deadlines from uploaded contracts:
- Termination deadlines (Kündigungsfristen)
- Automatic renewal dates
- Payment due dates
- Option exercise dates
- Contract start/end dates

### 2. Smart Alerts
Proactive alerts for:
- Upcoming deadlines (7, 14, 30 days before)
- Overdue deadlines
- Partner risk changes
- Compliance issues

### 3. Risk Radar
Combined risk scoring across four categories:
- **Contracts (30%)**: High-risk clauses, missing terms
- **Partners (25%)**: Credit, sanctions, insolvency
- **Compliance (25%)**: GDPR, ESG, regulatory
- **Deadlines (20%)**: Overdue, upcoming critical dates

## Architecture

```
Contract Upload
      │
      ▼
┌─────────────────┐
│ Deadline        │  ← AI extraction
│ Extraction Job  │  ← Background worker
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ ContractDeadline│  ← Database
│ Model           │
└────────┬────────┘
         │
    Daily Cron
         │
         ▼
┌─────────────────┐
│ Alert           │  ← Check deadlines
│ Generator       │  ← Create alerts
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Risk Radar      │  ← Aggregate scores
│ Service         │  ← Daily snapshot
└─────────────────┘
```

## Database Models

### ContractDeadline
```python
class ContractDeadline:
    id: UUID
    contract_id: UUID
    deadline_type: DeadlineType  # termination, renewal, payment, etc.
    deadline_date: date
    reminder_days_before: int = 14
    source_clause: str  # The contract text this was extracted from
    confidence: float  # AI confidence (0-1)
    is_verified: bool  # Human confirmed
    status: DeadlineStatus  # active, handled, dismissed
    notes: str
```

### ProactiveAlert
```python
class ProactiveAlert:
    id: UUID
    source_type: AlertSourceType  # contract, partner, compliance
    source_id: UUID
    alert_type: AlertType  # deadline, risk, compliance
    severity: AlertSeverity  # info, warning, critical
    title: str
    description: str
    ai_recommendation: str  # AI-generated action suggestion
    recommended_actions: list[dict]  # Actionable steps
    status: AlertStatus  # new, seen, in_progress, resolved, dismissed
    snoozed_until: datetime | None
    due_date: date | None
```

### RiskSnapshot
```python
class RiskSnapshot:
    id: UUID
    snapshot_date: date
    overall_risk_score: int  # 0-100
    contract_risk_score: int
    partner_risk_score: int
    compliance_score: int
    total_contracts: int
    high_risk_contracts: int
    pending_deadlines: int
    open_alerts: int
```

## API Endpoints

### Deadlines
```http
# List upcoming deadlines
GET /api/v1/proactive/deadlines?days_ahead=30&include_overdue=true

# Get deadline stats
GET /api/v1/proactive/deadlines/stats

# Mark deadline as handled
POST /api/v1/proactive/deadlines/{id}/handle
{
  "action": "renewed",
  "notes": "Contract renewed for 2 years"
}

# Verify AI-extracted deadline
POST /api/v1/proactive/deadlines/{id}/verify
{
  "correct_date": "2024-03-15"
}
```

### Alerts
```http
# List alerts with filters
GET /api/v1/proactive/alerts?status=new&severity=critical

# Get alert count (for badge)
GET /api/v1/proactive/alerts/count

# Resolve alert
POST /api/v1/proactive/alerts/{id}/resolve
{
  "action": "contract_terminated",
  "notes": "Sent termination letter"
}

# Snooze alert
POST /api/v1/proactive/alerts/{id}/snooze
{
  "days": 7
}
```

### Risk Radar
```http
# Get current risk overview
GET /api/v1/proactive/risk-radar

# Get historical data for charts
GET /api/v1/proactive/risk-radar/history?days=30
```

## Background Jobs

### Daily Jobs (arq worker)
```python
# Check deadlines and create alerts (6:00 AM)
async def check_deadlines_job(ctx):
    ...

# Create daily risk snapshot (6:30 AM)
async def create_risk_snapshot_job(ctx):
    ...

# Wake up snoozed alerts (hourly)
async def wake_snoozed_alerts_job(ctx):
    ...
```

### On Contract Upload
```python
# Extract deadlines after analysis completes
async def extract_deadlines_job(ctx, contract_id: str):
    ...
```

## Risk Scoring

### Overall Score Calculation
```python
def calculate_overall_score(
    contract_score: int,
    partner_score: int,
    compliance_score: int,
    deadline_score: int,
) -> int:
    return int(
        contract_score * 0.30 +
        partner_score * 0.25 +
        compliance_score * 0.25 +
        deadline_score * 0.20
    )
```

### Risk Levels
- **0-25**: Low (green)
- **26-50**: Medium (yellow)
- **51-75**: High (orange)
- **76-100**: Critical (red)

## Frontend Components

- `/proaktiv` - Main dashboard
- `RiskRadar` - Visual radar chart
- `AlertList` - Filterable alert list
- `DeadlineCalendar` - Calendar view of deadlines
- `RiskTrendChart` - Historical risk graph

## Configuration

```env
# Alert thresholds
DEADLINE_WARNING_DAYS=14
DEADLINE_CRITICAL_DAYS=3

# Risk weights (must sum to 1.0)
RISK_WEIGHT_CONTRACTS=0.30
RISK_WEIGHT_PARTNERS=0.25
RISK_WEIGHT_COMPLIANCE=0.25
RISK_WEIGHT_DEADLINES=0.20
```

## Related Files

- `backend/src/dealguard/domain/proactive/deadline_service.py`
- `backend/src/dealguard/domain/proactive/alert_service.py`
- `backend/src/dealguard/domain/proactive/risk_radar_service.py`
- `backend/src/dealguard/api/routes/proactive.py`
- `backend/src/dealguard/infrastructure/queue/worker.py`
- `frontend/src/app/proaktiv/page.tsx`
