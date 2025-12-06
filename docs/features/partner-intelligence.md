# Feature: Partner-Intelligence (Phase 2)

## Status
**Done** - Production Ready

## Übersicht

Vor Vertragsabschluss: Wer ist mein Geschäftspartner wirklich? Automatische Recherche zu Firmen mit Risiko-Bewertung und Echtzeit-Daten aus österreichischen Quellen.

## User Stories

1. **Als Einkäufer** möchte ich einen Lieferanten prüfen, bevor ich einen Vertrag unterschreibe.

2. **Als Geschäftsführer** möchte ich gewarnt werden, wenn ein Partner finanzielle Probleme hat.

3. **Als Compliance-Officer** möchte ich wissen, ob ein Partner auf Sanktionslisten steht.

## Datenquellen (Alle GRATIS!)

| Quelle | Daten | API | Status |
|--------|-------|-----|--------|
| **OpenFirmenbuch** | Firmenwortlaut, FN, GF, Kapital | REST | ✅ Live |
| **OpenSanctions** | EU/UN/US Sanktionslisten, PEP | REST | ✅ Live |
| **Ediktsdatei** | Insolvenzen, Versteigerungen | IWG | ✅ Live |
| **RIS OGD** | Rechtliche Verfahren | SOAP | ✅ Live |

## Partner Risiko-Score

Komponenten:
- **Finanzielle Stabilität** (30%) - Bonität, Eigenkapital
- **Rechtliche Compliance** (25%) - Keine Sanktionen, Insolvenzverfahren
- **Reputation** (20%) - News-Sentiment, Bewertungen
- **Operative Stabilität** (15%) - Alter der Firma, Management-Wechsel
- **Compliance** (10%) - ESG, Nachhaltigkeit

## Technische Implementierung

### Backend
- **Domain**: `domain/partners/`
- **Models**: `Partner`, `PartnerCheck`, `PartnerAlert`, `ContractPartner`
- **Services**: `PartnerService`, `PartnerCheckService`, `RiskCalculator`
- **External**: `OpenFirmenbuchClient`, `OpenSanctionsClient`

### Frontend
- Partner-Suche (Firmenname → Vorschläge)
- Partner-Profil (alle Daten auf einen Blick)
- Verknüpfung Partner ↔ Verträge
- Alerts Dashboard

### Check Types

| Check | Datenquelle | Was wird geprüft |
|-------|-------------|------------------|
| `firmenbuch` | OpenFirmenbuch | Firmendaten, GF, Kapital |
| `sanctions` | OpenSanctions | EU/UN/US Sanktionslisten |
| `pep` | OpenSanctions | Politically Exposed Persons |
| `insolvency` | Ediktsdatei | Aktive Insolvenzverfahren |

## Dateien

| Datei | Funktion |
|-------|----------|
| `backend/src/dealguard/domain/partners/services.py` | Business Logic |
| `backend/src/dealguard/domain/partners/risk_calculator.py` | Risiko-Scoring |
| `backend/src/dealguard/domain/partners/check_service.py` | Check Orchestrierung |
| `backend/src/dealguard/infrastructure/external/openfirmenbuch.py` | OpenFirmenbuch Client |
| `backend/src/dealguard/infrastructure/external/opensanctions.py` | OpenSanctions Client |
| `backend/src/dealguard/infrastructure/database/models/partner.py` | DB Models |
| `backend/src/dealguard/api/routes/partners.py` | API Endpoints |
| `frontend/src/app/partner/page.tsx` | Partner-Liste |
| `frontend/src/app/partner/[id]/page.tsx` | Partner-Detail |

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/partners/` | List partners |
| POST | `/api/v1/partners/` | Create partner |
| GET | `/api/v1/partners/{id}` | Get partner details |
| POST | `/api/v1/partners/{id}/checks` | Run checks |
| GET | `/api/v1/partners/{id}/alerts` | Get alerts |
| POST | `/api/v1/partners/search` | Search companies |

## MCP Tools für LLMs

| Tool | Beschreibung |
|------|-------------|
| `dealguard_search_companies` | Suche nach österr. Unternehmen |
| `dealguard_get_company_details` | Firmenbuch-Auszug |
| `dealguard_check_company_austria` | Schnelle Firmenprüfung |
| `dealguard_check_sanctions` | Sanktionslisten-Check |
| `dealguard_check_pep` | PEP-Prüfung |
| `dealguard_comprehensive_compliance` | Compliance-Gesamtprüfung |
| `dealguard_search_insolvency` | Insolvenz-Suche |

## Tests

- 24+ Unit Tests für Partner Models und Risk Calculator
- 20+ Integration Tests für API Endpoints

## Verbesserungen (Optional)

- [ ] Automatische Partner-Erkennung aus Verträgen
- [ ] Watchlist mit E-Mail Alerts
- [ ] News-Monitoring Integration
- [ ] DE/CH Handelsregister-Anbindung
