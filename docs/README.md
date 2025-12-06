# DealGuard Dokumentation

> Austrian Legal Infrastructure as a Service - Technische Dokumentation für Entwickler.

## Status: Production Ready (v2.0)

**147 Tests** | **13 MCP Tools** | **4 Austrian APIs** | **MIT License**

## Struktur

```
docs/
├── README.md                     # Diese Übersicht
├── architecture/                 # Architektur-Entscheidungen (ADRs)
│   ├── 001-auth-abstraction.md
│   ├── 002-multi-tenant.md
│   └── 003-async-ai-processing.md
├── api/                          # API-Dokumentation
│   ├── contracts.md
│   └── EXTERNAL_APIS.md          # Externe API-Konfiguration
└── features/                     # Feature-Spezifikationen
    ├── contract-analysis.md      # Phase 1 (Done)
    ├── partner-intelligence.md   # Phase 2 (Done)
    ├── legal-chat.md             # Phase 2.5 (Done)
    └── proactive-monitoring.md   # Phase 3 (Done)
```

## Quick Links

| Dokument | Beschreibung |
|----------|--------------|
| [README.md](../README.md) | Projekt-Übersicht, Schnellstart |
| [DEALGUARD_SPEC.md](../DEALGUARD_SPEC.md) | Produkt-Vision, technische Specs |
| [Architecture Decisions](./architecture/) | Warum wir X statt Y gewählt haben |
| [API Reference](./api/) | Endpoint-Dokumentation |
| [Feature Specs](./features/) | Detaillierte Feature-Beschreibungen |

## Austrian Legal Data APIs

DealGuard ist die einzige Legal-Tech-Plattform mit direktem Zugang zu echten österreichischen Datenquellen:

| Datenquelle | Was drin ist | Kosten | Status |
|-------------|--------------|--------|--------|
| **RIS OGD** | Alle Bundesgesetze, OGH-Urteile, tagesaktuell | **GRATIS** | ✅ Live |
| **Ediktsdatei** | Insolvenzen, Versteigerungen, Pfändungen | **GRATIS** | ✅ Live |
| **OpenFirmenbuch** | Firmenwortlaut, FN, GF, Kapital | **GRATIS** | ✅ Live |
| **OpenSanctions** | EU/UN/US Sanktionslisten, PEP-Daten | **GRATIS** | ✅ Live |

## MCP Server - 13 Tools für LLMs

| Tool | Beschreibung | Datenquelle |
|------|-------------|-------------|
| `dealguard_search_ris` | Suche nach Gesetzen | RIS OGD API |
| `dealguard_get_law_text` | Hole vollständigen Gesetzestext | RIS OGD API |
| `dealguard_search_insolvency` | Suche nach Insolvenzen | Ediktsdatei |
| `dealguard_search_companies` | Suche nach österr. Unternehmen | OpenFirmenbuch |
| `dealguard_get_company_details` | Firmenbuch-Auszug | OpenFirmenbuch |
| `dealguard_check_company_austria` | Schnelle Firmenprüfung AT | OpenFirmenbuch |
| `dealguard_check_sanctions` | Sanktionslisten-Check | OpenSanctions |
| `dealguard_check_pep` | PEP-Prüfung | OpenSanctions |
| `dealguard_comprehensive_compliance` | Compliance-Gesamtprüfung | OpenSanctions |
| `dealguard_search_contracts` | Vertragssuche | DealGuard DB |
| `dealguard_get_contract` | Vertragsdetails | DealGuard DB |
| `dealguard_get_partners` | Partnerliste | DealGuard DB |
| `dealguard_get_deadlines` | Fristen-Übersicht | DealGuard DB |

## Feature-Status

| Phase | Feature | Status |
|-------|---------|--------|
| **Phase 1** | Vertragsanalyse MVP | ✅ Fertig |
| **Phase 2** | Partner-Intelligence | ✅ Fertig |
| **Phase 2.5** | AI-Jurist / Legal Chat | ✅ Fertig |
| **Phase 3** | Proaktives Monitoring | ✅ Fertig |
| **Phase 4** | Austrian Open Data APIs | ✅ Fertig |
| **Phase 5** | Self-Hosted / Single-Tenant | ✅ Fertig |

## Wann welches Dokument?

| Frage | Dokument |
|-------|----------|
| "Wie starte ich das Projekt?" | `README.md` |
| "Was ist der aktuelle Stand?" | `DEALGUARD_SPEC.md` |
| "Warum ist Auth so gebaut?" | `docs/architecture/001-auth-abstraction.md` |
| "Wie funktioniert der Upload-Endpoint?" | `docs/api/contracts.md` |
| "Was genau soll Feature X können?" | `docs/features/[feature].md` |
| "Welche externen APIs brauchen wir?" | `docs/api/EXTERNAL_APIS.md` |

## Konventionen

### Architecture Decision Records (ADRs)
Format: `NNN-kurzer-titel.md`
```markdown
# ADR-NNN: Titel

## Status
Accepted | Proposed | Deprecated

## Kontext
Warum mussten wir entscheiden?

## Entscheidung
Was haben wir gewählt?

## Konsequenzen
Was folgt daraus?
```

### Feature Specs
Format: `feature-name.md`
```markdown
# Feature: Name

## Status
Planned | In Progress | Done

## Übersicht
Was macht das Feature?

## User Stories
Als [Rolle] möchte ich [Aktion], damit [Nutzen].

## Technische Anforderungen
- Backend: ...
- Frontend: ...
- AI: ...

## Offene Fragen
- ...
```

## Tests

```bash
# Backend Tests (147 total)
cd backend && python -m pytest tests/ -v

# Frontend Tests
cd frontend && npm test
```
