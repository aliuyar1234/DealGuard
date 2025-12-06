# Feature: Vertragsanalyse (MVP)

## Status
**Done** (Phase 1)

## Übersicht

Upload eines Vertrags (PDF/DOCX) → KI-Analyse nach deutschem Recht → Risiko-Score + Empfehlungen.

## User Stories

1. **Als KMU-Geschäftsführer** möchte ich einen Vertrag hochladen, damit ich verstehe welche Risiken darin stecken.

2. **Als Einkäufer** möchte ich kritische Klauseln markiert bekommen, damit ich weiß was ich verhandeln sollte.

3. **Als Buchhaltung** möchte ich Zahlungsbedingungen extrahiert sehen, damit ich sie ins ERP übernehmen kann.

## Analyse-Kategorien

| Kategorie | Was wird geprüft? |
|-----------|-------------------|
| `liability` | Haftung, Gewährleistung, Schadensersatz |
| `payment` | Zahlungsfristen, Skonto, Verzugszinsen |
| `termination` | Kündigungsfristen, Auto-Renewal |
| `jurisdiction` | Gerichtsstand, anwendbares Recht |
| `gdpr` | DSGVO-Konformität, AVV vorhanden? |
| `ip` | Geistiges Eigentum, Lizenzrechte |
| `confidentiality` | Geheimhaltung, NDA-Klauseln |

## Risiko-Bewertung

| Score | Level | Bedeutung |
|-------|-------|-----------|
| 0-25 | `low` | Vertrag ist fair, wenige Anpassungen nötig |
| 26-50 | `medium` | Einige Klauseln sollten überprüft werden |
| 51-75 | `high` | Mehrere kritische Klauseln, Verhandlung empfohlen |
| 76-100 | `critical` | Nicht unterschreiben ohne Rechtsberatung! |

## Technische Implementierung

### Backend
- **Upload**: `POST /api/v1/contracts/` (multipart/form-data)
- **Status**: `GET /api/v1/contracts/{id}` (polling)
- **Analyse**: Background Worker via ARQ
- **Prompt**: `contract_analysis_v1.py`

### Frontend
- **Upload UI**: Drag & Drop + Vertragstyp-Auswahl
- **Status**: Polling mit Spinner
- **Ergebnis**: Risk Score + Findings expandable

### AI
- **Model**: Claude Sonnet
- **Max Tokens**: 4096 Output
- **Response**: Strukturiertes JSON

## Dateien

| Datei | Funktion |
|-------|----------|
| `backend/src/dealguard/domain/contracts/services.py` | Business Logic |
| `backend/src/dealguard/infrastructure/ai/prompts/contract_analysis_v1.py` | Der Prompt |
| `backend/src/dealguard/api/routes/contracts.py` | API Endpoints |
| `frontend/src/app/vertraege/neu/page.tsx` | Upload UI |
| `frontend/src/app/vertraege/[id]/page.tsx` | Ergebnis-Ansicht |

## Offene Verbesserungen

- [ ] OCR für gescannte PDFs testen
- [ ] Mehr Vertragstypen im Prompt abdecken
- [ ] Confidence Score pro Finding
- [ ] Export als PDF-Report
