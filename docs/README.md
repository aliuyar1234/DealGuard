# DealGuard Dokumentation

> Technische Dokumentation für Entwickler und zukünftige Claude Sessions.

## Struktur

```
docs/
├── README.md                 # Diese Übersicht
├── architecture/             # Architektur-Entscheidungen (ADRs)
│   ├── 001-auth-abstraction.md
│   ├── 002-multi-tenant.md
│   └── ...
├── api/                      # API-Dokumentation
│   └── contracts.md
└── features/                 # Feature-Spezifikationen
    ├── contract-analysis.md  # Phase 1 (MVP)
    ├── partner-intelligence.md # Phase 2
    └── ...
```

## Quick Links

| Dokument | Beschreibung |
|----------|--------------|
| [CLAUDE.md](../CLAUDE.md) | Session-Kontext, aktueller Stand |
| [DEALGUARD_SPEC.md](../DEALGUARD_SPEC.md) | Produkt-Vision, alle Features |
| [Architecture Decisions](./architecture/) | Warum wir X statt Y gewählt haben |
| [API Reference](./api/) | Endpoint-Dokumentation |
| [Feature Specs](./features/) | Detaillierte Feature-Beschreibungen |

## Wann welches Dokument?

| Frage | Dokument |
|-------|----------|
| "Wo sind wir gerade?" | `CLAUDE.md` |
| "Was wollen wir langfristig?" | `DEALGUARD_SPEC.md` |
| "Warum ist Auth so gebaut?" | `docs/architecture/001-auth-abstraction.md` |
| "Wie funktioniert der Upload-Endpoint?" | `docs/api/contracts.md` |
| "Was genau soll Feature X können?" | `docs/features/[feature].md` |

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
