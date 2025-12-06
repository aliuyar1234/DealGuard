# DealGuard - Product & Technical Specification

## Status: Production Ready (v2.0)
## Letzte Aktualisierung: 2025-12-06

---

## 1. WAS IST DEALGUARD?

### Austrian Legal Infrastructure as a Service

DealGuard ist mehr als ein Vertragsanalyse-Tool - es ist eine **vollständige Legal-Tech-Plattform** mit Zugang zu echten österreichischen Rechtsdaten.

### One-Liner
**"Der AI-Anwalt und Wirtschaftsdetektiv für KMU - mit echten Rechtsdaten, nicht Halluzinationen."**

### Core Value Proposition
- 1 vermiedener Zahlungsausfall (50k€) = 40+ Jahre Abo bezahlt
- Echte Rechtsdaten statt AI-Halluzinationen
- GRATIS Zugang zu österreichischen Open-Data APIs

---

## 2. AKTUELLER STATUS

### ✅ Implementiert (100%)

| Phase | Feature | Status |
|-------|---------|--------|
| **Phase 1** | Vertragsanalyse MVP | ✅ Fertig |
| **Phase 2** | Partner-Intelligence | ✅ Fertig |
| **Phase 2.5** | AI-Jurist / Legal Chat | ✅ Fertig |
| **Phase 3** | Proaktives Monitoring | ✅ Fertig |
| **Phase 4** | Austrian Open Data APIs | ✅ Fertig |
| **Phase 5** | Self-Hosted / Single-Tenant | ✅ Fertig |

### 📊 Test Coverage
- **147 Tests** bestanden
- Unit Tests: 76
- Integration Tests: 71

---

## 3. FEATURES IM DETAIL

### 🏛️ Austrian Legal Data APIs (Game-Changer)

| Datenquelle | Was drin ist | Kosten | Status |
|-------------|--------------|--------|--------|
| **RIS OGD** | Alle Bundesgesetze, OGH-Urteile, tagesaktuell | **GRATIS** | ✅ Live |
| **Ediktsdatei** | Insolvenzen, Versteigerungen, Pfändungen | **GRATIS** | ✅ Live |
| **OpenFirmenbuch** | Firmenwortlaut, FN, GF, Kapital | **GRATIS** | ✅ Live |
| **OpenSanctions** | EU/UN/US Sanktionslisten, PEP-Daten | **GRATIS** | ✅ Live |

**Warum das Game-Changing ist:**
- ABGB-Zitate sind **ECHT** (aus RIS API)
- Insolvenz-Info ist **ECHT** (aus Ediktsdatei)
- Firmendaten sind **ECHT** (aus OpenFirmenbuch)
- Sanktionsprüfung ist **ECHT** (aus OpenSanctions)
- ChatGPT kann das **NICHT** (kein Zugang zu diesen Datenquellen)

### 📋 Vertragsanalyse

- PDF/DOCX Upload mit OCR-Support
- KI-Analyse in <120 Sekunden
- Risiko-Score 0-100 mit Ampel
- Kategorien: Haftung, Zahlung, Kündigung, Gerichtsstand, IP, DSGVO, Gewährleistung
- Konkrete Handlungsempfehlungen

**Vertragstypen:**
1. Lieferantenverträge
2. Kundenverträge / AGB
3. Dienstleistungsverträge
4. NDAs
5. Mietverträge (Gewerbe)
6. Arbeitsverträge
7. Lizenzverträge

### 🔍 Partner-Intelligence

- Firmensuche mit Fuzzy Matching
- Aggregierte Risiko-Bewertung
- Handelsregister-Daten
- Insolvenz-Prüfung
- Sanktions-Screening
- PEP-Check (Politically Exposed Persons)

**Risiko-Score Berechnung:**
- Finanzen: 30%
- Recht: 25%
- Reputation: 20%
- Betrieb: 15%
- Compliance: 10%

### 💬 AI Legal Chat

- ChatGPT-ähnliches Interface
- Zugriff auf eigene Verträge via RAG
- **Echte Gesetzeszitate** aus RIS API
- Citation-Validierung (Anti-Halluzination)
- Confidence Score für Antworten

### ⚡ Proaktives Monitoring

- **Fristen-Wächter**: Kündigungsfristen, Auto-Verlängerungen, Zahlungsziele
- **Risk Radar**: Kombiniertes Scoring über alle Bereiche
- **Smart Alerts**: Kontextuelle Empfehlungen mit Aktionen
- **Daily Snapshots**: Risiko-Trending über Zeit

### 🔧 MCP Server (13 Tools für LLMs)

| Tool | Beschreibung | Datenquelle |
|------|-------------|-------------|
| `dealguard_search_ris` | Suche nach Gesetzen | RIS OGD API |
| `dealguard_get_law_text` | Hole vollständigen Gesetzestext | RIS OGD API |
| `dealguard_search_insolvency` | Suche nach Insolvenzen | Ediktsdatei IWG |
| `dealguard_search_companies` | Suche nach österr. Unternehmen | OpenFirmenbuch |
| `dealguard_get_company_details` | Firmendetails aus Firmenbuch | OpenFirmenbuch |
| `dealguard_check_company_austria` | Schnelle Firmenprüfung AT | OpenFirmenbuch |
| `dealguard_check_sanctions` | Sanktionslisten-Check | OpenSanctions |
| `dealguard_check_pep` | PEP-Prüfung | OpenSanctions |
| `dealguard_comprehensive_compliance` | Kombination: Sanktionen + PEP | OpenSanctions |
| `dealguard_search_contracts` | Durchsuche Verträge | DealGuard DB |
| `dealguard_get_contract` | Hole Vertragsdetails | DealGuard DB |
| `dealguard_get_partners` | Liste Partner | DealGuard DB |
| `dealguard_get_deadlines` | Hole Fristen | DealGuard DB |

---

## 4. TECH STACK

| Bereich | Technologie | Notizen |
|---------|-------------|---------|
| Backend | Python 3.12, FastAPI | Async, SQLAlchemy 2.0, Pydantic v2 |
| Frontend | Next.js 14, TypeScript | App Router, Tailwind CSS |
| Database | PostgreSQL 16 | Multi-Tenant via organization_id |
| Queue | Redis + ARQ | Background Jobs |
| AI | Anthropic Claude / DeepSeek | Wählbar pro User |
| Auth | Supabase Auth | Dev-Mode ohne Supabase möglich |
| Storage | S3/MinIO | EU-only für DSGVO |
| Rate Limiting | slowapi + Redis | Schutz vor Abuse |
| Encryption | Fernet (cryptography) | API Keys + Vertragstext |

---

## 5. SECURITY

### Implementiert

- ✅ **Encryption at Rest**: Vertragstext und API Keys mit Fernet verschlüsselt
- ✅ **APP_SECRET_KEY Required**: Kein unsicherer Default möglich
- ✅ **Rate Limiting**: slowapi mit konfigurierbaren Limits
- ✅ **Tenant Isolation**: Alle Queries per `organization_id` gefiltert
- ✅ **Soft Deletes**: `deleted_at IS NULL` automatisch gefiltert
- ✅ **CORS Konfiguration**: Nur erlaubte Origins
- ✅ **Input Validation**: Pydantic v2 mit Constraints

### Rate Limits

| Endpoint-Typ | Limit |
|-------------|-------|
| General API | 100/minute |
| Auth (Login) | 5/minute |
| File Upload | 10/minute |
| AI Endpoints | 20/minute |
| Search | 30/minute |
| Health | 60/minute |

---

## 6. KOSTEN

### AI-Kosten pro Operation

| Operation | DeepSeek | Anthropic |
|-----------|----------|-----------|
| Vertragsanalyse | ~€0.05 | ~€1.00 |
| Chat-Nachricht | ~€0.001 | ~€0.02 |
| Deadline Extraktion | ~€0.002 | ~€0.04 |

### Datenquellen

**Alle österreichischen APIs sind GRATIS:**
- RIS OGD: Kostenlos
- Ediktsdatei: Kostenlos
- OpenFirmenbuch: Kostenlos
- OpenSanctions: Kostenlos

### Externe APIs (Optional, für später)

| API | Zweck | Kosten |
|-----|-------|--------|
| North Data | Handelsregister DE | €99-299/mo |
| Creditreform | Bonitätsprüfung | €200-500/mo |
| NewsAPI | Nachrichten-Monitoring | €449/mo |

---

## 7. DEPLOYMENT

### Self-Hosted (Empfohlen)

```bash
# 1. Repository klonen
git clone https://github.com/aliuyar1234/DealGuard.git
cd DealGuard

# 2. Konfiguration
cp .env.example .env
# APP_SECRET_KEY generieren (REQUIRED!)
python -c "import secrets; print(secrets.token_urlsafe(32))"

# 3. Services starten
docker-compose up -d

# 4. Datenbank migrieren
make migrate
```

### Umgebungsvariablen

| Variable | Required | Beschreibung |
|----------|----------|--------------|
| `APP_SECRET_KEY` | ✅ | Encryption Key (min 32 chars) |
| `AI_PROVIDER` | ❌ | `anthropic` oder `deepseek` |
| `ANTHROPIC_API_KEY` | ❌ | Für Claude |
| `DEEPSEEK_API_KEY` | ❌ | Für DeepSeek (günstiger) |
| `AUTH_PROVIDER` | ❌ | `supabase` oder `dev` |
| `DATABASE_URL` | ❌ | PostgreSQL Connection |

---

## 8. API ÜBERSICHT

### Contracts
| Methode | Pfad | Beschreibung |
|---------|------|--------------|
| POST | `/api/v1/contracts/` | Vertrag hochladen |
| GET | `/api/v1/contracts/` | Alle Verträge listen |
| GET | `/api/v1/contracts/{id}` | Vertrag mit Analyse |
| POST | `/api/v1/contracts/{id}/analyze` | Analyse starten |
| DELETE | `/api/v1/contracts/{id}` | Vertrag löschen |

### Partners
| Methode | Pfad | Beschreibung |
|---------|------|--------------|
| GET | `/api/v1/partners/` | Partner listen |
| POST | `/api/v1/partners/` | Partner anlegen |
| GET | `/api/v1/partners/{id}` | Partner-Details |
| POST | `/api/v1/partners/{id}/checks` | Prüfungen starten |
| GET | `/api/v1/partners/{id}/alerts` | Alerts abrufen |

### Chat (AI Legal Assistant)
| Methode | Pfad | Beschreibung |
|---------|------|--------------|
| POST | `/api/v1/chat/v2` | Chat mit Tools |
| GET | `/api/v1/chat/v2/tools` | Verfügbare Tools |
| GET | `/api/v1/chat/v2/health` | Chat Health Check |

### Proactive
| Methode | Pfad | Beschreibung |
|---------|------|--------------|
| GET | `/api/v1/proactive/deadlines` | Fristen abrufen |
| GET | `/api/v1/proactive/alerts` | Alerts abrufen |
| GET | `/api/v1/proactive/risk-radar` | Risk Radar |

### Settings
| Methode | Pfad | Beschreibung |
|---------|------|--------------|
| GET | `/api/v1/settings` | Einstellungen laden |
| PUT | `/api/v1/settings/api-keys` | API Keys speichern |
| GET | `/api/v1/settings/check-ai` | AI-Verbindung testen |

---

## 9. ROADMAP

### ✅ Erledigt

- [x] Phase 1: Vertragsanalyse MVP
- [x] Phase 2: Partner-Intelligence
- [x] Phase 2.5: AI-Jurist / Legal Chat
- [x] Phase 3: Proaktives Monitoring
- [x] Phase 4: Austrian Open Data Integration
- [x] Phase 5: Self-Hosted / Single-Tenant Mode
- [x] Production Security (Encryption, Rate Limiting)
- [x] 147 Tests

### 🔜 Nächste Schritte (Optional)

| Feature | Aufwand | Priorität |
|---------|---------|-----------|
| Stripe Integration | ⭐⭐⭐ | Hoch |
| Multi-User / Teams | ⭐⭐⭐ | Hoch |
| Vertragsvergleich (Diff) | ⭐⭐⭐ | Mittel |
| Verhandlungs-Assistent | ⭐⭐⭐⭐ | Mittel |
| E-Signature Integration | ⭐⭐⭐⭐ | Niedrig |
| DE/CH Recht Erweiterung | ⭐⭐⭐ | Niedrig |

---

## 10. ARCHITEKTUR

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           DEALGUARD ARCHITECTURE                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────────────────┐ │
│  │   Frontend   │────▶│   FastAPI    │────▶│   Austrian APIs          │ │
│  │   Next.js    │     │   Backend    │     │   (RIS, Edikt, FB, OS)   │ │
│  └──────────────┘     └──────────────┘     └──────────────────────────┘ │
│                              │                                           │
│                              ▼                                           │
│         ┌────────────────────┼────────────────────┐                     │
│         │                    │                    │                      │
│         ▼                    ▼                    ▼                      │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐            │
│  │  PostgreSQL  │     │    Redis     │     │   MinIO/S3   │            │
│  │  (Data)      │     │   (Queue)    │     │  (Files)     │            │
│  └──────────────┘     └──────────────┘     └──────────────┘            │
│                              │                                           │
│                              ▼                                           │
│                       ┌──────────────┐                                  │
│                       │  AI Clients  │                                  │
│                       │  Claude/DS   │                                  │
│                       └──────────────┘                                  │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 11. LIZENZ

**MIT License** - Open Source

---

## 12. LINKS

- **Repository**: https://github.com/aliuyar1234/DealGuard
- **API Docs**: http://localhost:8000/docs (nach Start)
- **Frontend**: http://localhost:3000 (nach Start)
