# Feature: Vertragsanalyse (Phase 1)

## Status
**Done** - Production Ready

## Übersicht

Upload eines Vertrags (PDF/DOCX) → KI-Analyse nach österreichischem Recht → Risiko-Score + Empfehlungen.

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
| `warranty` | Gewährleistung nach ABGB/UGB |

## Vertragstypen

1. Lieferantenverträge
2. Kundenverträge / AGB
3. Dienstleistungsverträge
4. NDAs
5. Mietverträge (Gewerbe)
6. Arbeitsverträge
7. Lizenzverträge

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
- **Prompt**: `contract_analysis_v1.py` (österreichisches Recht: ABGB, UGB, KSchG)
- **Encryption**: Vertragstext wird mit Fernet verschlüsselt gespeichert

### Frontend
- **Upload UI**: Drag & Drop + Vertragstyp-Auswahl
- **Status**: Polling mit Spinner
- **Ergebnis**: Risk Score + Findings expandable

### AI
- **Model**: Claude Sonnet / DeepSeek (konfigurierbar)
- **Max Tokens**: 4096 Output
- **Response**: Strukturiertes JSON
- **Kosten**: ~€1.00/Analyse (Claude) oder ~€0.05/Analyse (DeepSeek)

## Dateien

| Datei | Funktion |
|-------|----------|
| `backend/src/dealguard/domain/contracts/services.py` | Business Logic |
| `backend/src/dealguard/infrastructure/ai/prompts/contract_analysis_v1.py` | Der Prompt (AT Recht) |
| `backend/src/dealguard/infrastructure/database/models/contract.py` | DB Model mit Encryption |
| `backend/src/dealguard/api/routes/contracts.py` | API Endpoints |
| `frontend/src/app/vertraege/neu/page.tsx` | Upload UI |
| `frontend/src/app/vertraege/[id]/page.tsx` | Ergebnis-Ansicht |

## Security

- **Encryption at Rest**: Vertragstext wird mit Fernet verschlüsselt
- **Soft Deletes**: Gelöschte Verträge werden nicht wirklich gelöscht
- **Rate Limiting**: 10 Uploads/Minute

## Tests

- 15+ Unit Tests für Contract Models
- 12+ Integration Tests für API Endpoints
- Encoding/Decoding Tests für Encryption

## Verbesserungen (Optional)

- [ ] OCR für gescannte PDFs verbessern
- [ ] Mehr Vertragstypen im Prompt abdecken
- [ ] Export als PDF-Report
- [ ] Vertragsvergleich (Diff)
