# Contributing to DealGuard

Vielen Dank für dein Interesse an DealGuard! Wir freuen uns über jeden Beitrag.

## Entwicklungsumgebung einrichten

### Voraussetzungen

- Docker & Docker Compose
- Python 3.12+
- Node.js 18+
- Make (optional, aber empfohlen)

### Schnellstart

```bash
# Repository klonen
git clone https://github.com/aliuyar1234/DealGuard.git
cd DealGuard

# Umgebungsvariablen kopieren
cp .env.example .env

# Docker-Container starten (PostgreSQL, Redis, MinIO)
docker-compose up -d

# Backend einrichten
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
alembic upgrade head

# Frontend einrichten
cd ../frontend
npm install

# Entwicklungsserver starten
# Terminal 1: Backend
cd backend && uvicorn dealguard.main:app --reload

# Terminal 2: Worker
cd backend && arq dealguard.infrastructure.queue.worker.WorkerSettings

# Terminal 3: Frontend
cd frontend && npm run dev
```

### Mit Makefile (empfohlen)

```bash
make setup      # Alles einrichten
make dev        # Alle Services starten
make test       # Tests ausführen
make lint       # Code-Qualität prüfen
```

## Code-Style

### Python (Backend)

- **Formatter**: Black (Zeilenlänge 100)
- **Linter**: Ruff
- **Type Hints**: Überall erforderlich
- **Docstrings**: Google Style

```python
async def analyze_contract(
    self,
    contract_id: UUID,
    options: AnalysisOptions | None = None,
) -> ContractAnalysis:
    """Analysiert einen Vertrag mit KI.

    Args:
        contract_id: Die ID des Vertrags
        options: Optionale Analyse-Einstellungen

    Returns:
        Das Analyse-Ergebnis

    Raises:
        NotFoundError: Wenn der Vertrag nicht existiert
    """
    ...
```

### TypeScript (Frontend)

- **Formatter**: Prettier
- **Linter**: ESLint
- **Komponenten**: Funktionale Komponenten mit TypeScript

```typescript
interface ContractCardProps {
  contract: Contract;
  onAnalyze?: (id: string) => void;
}

export function ContractCard({ contract, onAnalyze }: ContractCardProps) {
  // ...
}
```

## Architektur

### Backend (Clean Architecture)

```
backend/src/dealguard/
├── api/           # HTTP Layer (FastAPI Routes)
├── domain/        # Business Logic (Services)
├── infrastructure/# External Services (DB, AI, Storage)
├── mcp/           # MCP Tools für Claude
└── shared/        # Utilities (Logging, Exceptions)
```

**Wichtige Regeln:**
- API Layer darf nur Domain Layer importieren
- Domain Layer darf nur Infrastructure Layer importieren
- Infrastructure Layer importiert nichts aus höheren Schichten
- Alle DB-Queries müssen `organization_id` filtern (Multi-Tenant)

### Frontend (Next.js App Router)

```
frontend/src/
├── app/           # Pages (App Router)
├── components/    # React Components
├── hooks/         # Custom Hooks
└── lib/           # Utilities (API Client, Auth)
```

## Pull Requests

### Vor dem PR

1. **Tests schreiben/aktualisieren**
   ```bash
   # Backend
   cd backend && pytest tests/ -v

   # Frontend
   cd frontend && npm test
   ```

2. **Code formatieren**
   ```bash
   # Backend
   black backend/src
   ruff check backend/src --fix

   # Frontend
   npm run lint
   ```

3. **Type-Checking**
   ```bash
   # Backend
   mypy backend/src

   # Frontend
   npm run type-check
   ```

### PR-Beschreibung

Bitte folgendes Format verwenden:

```markdown
## Beschreibung
Kurze Beschreibung der Änderungen.

## Änderungen
- Feature X hinzugefügt
- Bug Y behoben
- Refactoring von Z

## Test-Plan
- [ ] Unit Tests hinzugefügt
- [ ] Integration Tests aktualisiert
- [ ] Manuell getestet

## Screenshots (falls UI-Änderungen)
```

## Commit-Messages

Wir verwenden [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: Neue Funktion hinzugefügt
fix: Bug behoben
docs: Dokumentation aktualisiert
refactor: Code umstrukturiert
test: Tests hinzugefügt/geändert
chore: Build/CI/Config Änderungen
```

Beispiele:
```
feat(contracts): Vertragsvergleich hinzugefügt
fix(auth): Token-Refresh bei Ablauf
docs: README aktualisiert
refactor(api): Response-Helper extrahiert
```

## Branches

- `main` - Stabiler Branch, nur über PR
- `feature/*` - Neue Features
- `fix/*` - Bugfixes
- `docs/*` - Dokumentation

## Issues

### Bug Report

```markdown
**Beschreibung**
Was ist passiert?

**Erwartetes Verhalten**
Was sollte passieren?

**Schritte zur Reproduktion**
1. Gehe zu ...
2. Klicke auf ...
3. Fehler erscheint

**Umgebung**
- OS: Windows/Mac/Linux
- Browser: Chrome/Firefox/Safari
- Version: x.x.x
```

### Feature Request

```markdown
**Problem**
Welches Problem soll gelöst werden?

**Lösungsvorschlag**
Wie könnte die Lösung aussehen?

**Alternativen**
Welche Alternativen wurden erwogen?
```

## Fragen?

- GitHub Issues für Bugs und Features
- Discussions für allgemeine Fragen

Danke fürs Mitmachen! 🙏
