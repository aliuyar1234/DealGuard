# DealGuard - Product & Technical Specification

## Für: Claude Code CLI (Opus 4.5)
## Von: au (Product Owner / QA)
## Status: Greenfield Project, Production Target

---

## 1. KONTEXT - WARUM BAUEN WIR DAS?

### Das Problem

KMU im DACH-Raum (3.5 Mio Unternehmen) haben ein massives, teures Problem:

**Sie unterschreiben Verträge blind.**
- Anwalt kostet 300-500€/h → zu teuer für jeden Vertrag
- Also wird übersprungen → versteckte Risiken werden akzeptiert
- Ergebnis: Haftungsfallen, Auto-Renewals, unfaire Zahlungsbedingungen

**Sie prüfen Geschäftspartner nicht.**
- Neuer Kunde bestellt für 50k€ → niemand prüft Bonität
- Neuer Lieferant → niemand checkt Insolvenzrisiko
- Ergebnis: 2-3% Umsatzverlust durch Zahlungsausfälle (Branchenschnitt)

**Warum jetzt lösbar?**
- LLMs können erstmals Verträge auf Jurist-Niveau analysieren
- Kosten: ~0.50€ pro Analyse statt 500€ Anwalt
- Noch kein Player im DACH-Markt der beides kombiniert (Vertrag + Partner)

### Wettbewerb & Lücke

| Was existiert | Was es macht | Was fehlt |
|---------------|--------------|-----------|
| ContractHero, fynk | Vertragsverwaltung (speichern, Fristen) | Prüft nicht VOR Unterschrift |
| Creditreform, Bürgel | Bonitätsauskunft | Teuer, nur Finanzdaten, keine AI |
| Anwalt | Vertragsprüfung | 500€/Vertrag, 2 Wochen Wartezeit |

**Unsere Lücke: AI-gestützte Risiko-Intelligence BEVOR unterschrieben wird.**

---

## 2. PRODUKTVISION

### One-Liner
"Der AI-Anwalt und Wirtschaftsdetektiv für KMU - in 60 Sekunden statt 2 Wochen."

### Core Value Proposition
1 vermiedener Zahlungsausfall (50k€) = 40+ Jahre Abo bezahlt. Kein Brainer.

### Die drei Säulen

```
┌─────────────────────────────────────────────────────────────────┐
│                        DEALGUARD                                 │
├─────────────────┬─────────────────┬─────────────────────────────┤
│  VERTRAGSPRÜFUNG │ PARTNER-CHECK   │ FRÜHWARNSYSTEM             │
│                 │                 │                             │
│  Upload PDF/DOCX│ Firmenname      │ Watchlist für Top-Kunden/   │
│  → 60 Sek       │ eingeben        │ Lieferanten                 │
│  → Risiko-Score │ → 30 Sek        │ → Daily Monitoring          │
│  → Warnungen    │ → Risiko-Report │ → Push bei Gefahr           │
│  → Empfehlungen │ → Daten-Quellen │                             │
├─────────────────┴─────────────────┴─────────────────────────────┤
│  STARTER €49/mo │ BUSINESS €99/mo │ ENTERPRISE €299/mo          │
│  10 Analysen    │ 50 Analysen     │ Unlimited + API + SSO       │
│  5 Partner      │ 25 Partner      │ Unlimited + Webhooks        │
│  Kein Monitoring│ 10 Watchlist    │ Unlimited + Custom          │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. USER STORIES - WAS SOLL ES KÖNNEN?

### Epic 1: Vertragsprüfung

**Story 1.1: Schnelle Risikoanalyse**
> Als Geschäftsführer eines 20-Mann-Betriebs
> will ich einen Lieferantenvertrag (PDF, 15 Seiten) hochladen
> und in unter 2 Minuten wissen: Ist das gefährlich oder kann ich unterschreiben?

Akzeptanzkriterien:
- Upload von PDF, DOCX, Bildern (OCR für Scans)
- Risiko-Score 0-100 mit Ampel (grün/gelb/rot)
- Top 5 Risiken mit Erklärung in Deutsch
- Konkrete Empfehlung: "Nicht unterschreiben weil..." oder "OK mit Vorbehalt..."
- Max 120 Sekunden für 20-Seiten-Dokument

**Story 1.2: Detailanalyse**
> Als Prokurist will ich verstehen, WELCHE Klauseln problematisch sind
> um gezielt mit dem Vertragspartner nachzuverhandeln.

Akzeptanzkriterien:
- Jede problematische Klausel wird zitiert (Originaltext)
- Erklärung warum problematisch (verständliches Deutsch, kein Juristendeutsch)
- Vergleich mit "marktüblich" / "Best Practice"
- Optional: Formulierungsvorschlag für bessere Klausel

**Story 1.3: Vertragstyp-spezifische Analyse**
> Als Nutzer erwarte ich, dass ein Mietvertrag anders geprüft wird als ein Kaufvertrag.

Zu unterstützende Vertragstypen (Priorität):
1. Lieferantenverträge / Einkauf
2. Kundenverträge / AGB
3. Dienstleistungsverträge
4. NDAs
5. Mietverträge (Gewerbe)
6. Arbeitsverträge
7. Lizenzverträge

### Epic 2: Partner-Intelligence

**Story 2.1: Schneller Firmencheck**
> Als Vertriebsleiter will ich vor einem 100k€-Angebot in 30 Sekunden wissen:
> Ist dieser potenzielle Kunde solvent? Gibt es Red Flags?

Akzeptanzkriterien:
- Eingabe: Firmenname oder URL
- Automatische Identifikation (Fuzzy Match bei Tippfehlern)
- Output: Risiko-Score + strukturierter Report

**Story 2.2: Datenquellen-Aggregation**
> Ich will ALLE relevanten Infos an einem Ort, nicht 10 Tabs offen haben.

Zu aggregierende Quellen:
- Handelsregister (Gesellschafter, Kapital, Gründungsdatum, Rechtsform)
- Bundesanzeiger (Jahresabschlüsse falls veröffentlicht)
- News (Google News, Pressemitteilungen) - Sentiment-Analyse
- Bewertungen (Google, Kununu, branchenspezifisch)
- Website-Analyse (Impressum vollständig? SSL? Aktiv?)
- Optional Premium: Creditreform/Bürgel-Integration

**Story 2.3: Beziehungshistorie**
> Als langjähriger Nutzer will ich sehen, welche Verträge ich mit diesem Partner habe
> und wie sich sein Risiko-Score über Zeit entwickelt hat.

### Epic 3: Monitoring & Alerts

**Story 3.1: Watchlist**
> Als CFO will ich meine 20 wichtigsten Kunden und 10 kritischen Lieferanten überwachen.

Akzeptanzkriterien:
- Partner zur Watchlist hinzufügen (1-Click aus Partner-Check)
- Täglicher automatischer Scan aller Watchlist-Einträge
- Konfigurierbare Alert-Schwellen

**Story 3.2: Proaktive Alerts**
> Ich will SOFORT wissen, wenn ein wichtiger Partner in Schwierigkeiten gerät.

Alert-Typen:
- Insolvenzantrag / Insolvenzverfahren eröffnet
- Stark negative Presse (Skandal, Betrug, Klage)
- Führungswechsel (Geschäftsführer ausgeschieden)
- Signifikante Änderung im Handelsregister
- Vertragsablauf in X Tagen (eigene Verträge)

Delivery:
- In-App Notification
- E-Mail (konfigurierbar)
- Webhook für Enterprise (Slack, Teams, eigene Systeme)

### Epic 4: Enterprise Features

**Story 4.1: Multi-User & Rollen**
> Als IT-Leiter will ich mein Team einladen mit unterschiedlichen Rechten.

Rollen:
- Owner: Alles, inkl. Billing
- Admin: Alles außer Billing
- Member: Analysen durchführen, eigene sehen
- Viewer: Nur lesen

**Story 4.2: API-Zugang**
> Als Entwickler will ich DealGuard in unser CRM/ERP integrieren.

Requirements:
- RESTful API, OpenAPI 3.0 Spec
- API Keys mit Rate Limiting
- Webhooks für Events (neue Analyse fertig, Alert ausgelöst)

**Story 4.3: SSO**
> Als Enterprise-Kunde erwarte ich Login über unser Azure AD / Okta.

OIDC/SAML Support für Business/Enterprise Tier.

---

## 4. RISIKO-ANALYSE LOGIK

### Was soll die AI erkennen?

**Vertragsrisiken (Kernkompetenz):**

| Kategorie | Beispiele | Warum kritisch |
|-----------|-----------|----------------|
| Haftung | Unbeschränkte Haftung, einseitige Freistellung | Existenzbedrohend |
| Zahlungsbedingungen | >60 Tage Zahlungsziel, >50% Vorauszahlung | Cash Flow Killer |
| Kündigung | Versteckte Auto-Renewal, >6 Monate Frist, Strafzahlungen | Lock-in Falle |
| Gerichtsstand | Ausländisches Recht, Schiedsgerichtsklausel | Rechtsunsicherheit |
| IP/Nutzungsrechte | Vollständige Übertragung, kein Rückfall | Wertverlust |
| Geheimhaltung | Unbefristete NDA, einseitige Verpflichtung | Langfristiges Risiko |
| DSGVO | Fehlende AVV, keine Löschpflichten | Bußgelder |
| Gewährleistung | Ausschluss, verkürzte Fristen | Qualitätsrisiko |

**Partner-Risiken:**

| Signal | Quelle | Bedeutung |
|--------|--------|-----------|
| Negatives Eigenkapital | Bundesanzeiger | Überschuldung |
| Häufiger GF-Wechsel | Handelsregister | Instabilität |
| Insolvenzverfahren | Insolvenzbekanntmachungen | Akute Gefahr |
| Negative Presse | News APIs | Reputationsrisiko |
| Schlechte Bewertungen | Google/Kununu | Qualitätsprobleme |
| Junge Firma + hohe Bestellung | Kombiniert | Betrugsrisiko |

### Risiko-Score Berechnung

Kein starres Punktesystem - die AI soll kontextabhängig gewichten.

Aber grobe Orientierung:
- 0-30: Grün (geringes Risiko)
- 31-60: Gelb (moderate Risiken, prüfen)
- 61-80: Orange (signifikante Risiken, Vorsicht)
- 81-100: Rot (kritisch, nicht empfohlen)

---

## 5. QUALITÄTSANFORDERUNGEN

### Performance
- Vertragsanalyse: <120 Sekunden für 95th percentile
- Partner-Check: <30 Sekunden für initiale Ergebnisse
- API Response: <500ms für nicht-AI-Calls
- Uptime: 99.5% (Business), 99.9% (Enterprise SLA)

### Security & Compliance
- **DSGVO**: Volle Compliance. Wir verarbeiten hochsensitive Geschäftsdaten.
- **Datenhaltung**: EU-only. Kein US-Cloud ohne Standardvertragsklauseln.
- **Encryption**: At rest + in transit
- **Retention**: Nutzer muss Daten löschen können (Right to be forgotten)
- **AI-Daten**: Verträge werden NICHT zum Training verwendet
- **Audit Log**: Wer hat wann was analysiert (Enterprise Compliance)
- **Multi-Tenant**: Strikte Datentrennung zwischen Organisationen

### Skalierbarkeit
- MVP: 100 concurrent users
- Jahr 1: 1.000 concurrent users
- Architektur muss horizontal skalieren können

### Lokalisierung
- UI: Deutsch first, Englisch second
- Vertragsanalyse: Deutsches Recht (BGB, HGB) als Default
- Später: AT (ABGB), CH (OR) als Erweiterungen

---

## 6. TECHNISCHE RICHTLINIEN

### Stack-Präferenzen (keine Vorschriften)

Ich vertraue deinem Judgment. Hier meine Präferenzen:

| Bereich | Präferenz | Warum |
|---------|-----------|-------|
| Backend | Python (FastAPI) | AI/ML Ecosystem, async, schnell |
| Frontend | Next.js oder SvelteKit | Deine Wahl |
| Database | PostgreSQL | Bewährt, kann alles |
| AI | Anthropic Claude API | Beste Reasoning für Legal |
| Hosting | EU-based zwingend | DSGVO |

### Architektur-Prinzipien

1. **API-First**: Frontend austauschbar, API ist das Produkt
2. **Async für AI**: Lange Analysen → Queue → Webhook/Polling
3. **Multi-Tenant von Tag 1**: Keine Shortcuts bei Datentrennung
4. **Infrastructure as Code**: Reproduzierbar, kein Klicken in UIs
5. **Observability**: Logging, Metrics, Tracing von Anfang an

### AI/LLM Strategie

**Wichtig:**

1. **Prompts sind IP** - Versioniert, nicht hardcoded
2. **Structured Output** - Risiko-Scores müssen konsistent sein
3. **RAG für Präzision** - Wissensbasis für deutsches Recht anreichern
4. **Cost Tracking** - Token-Verbrauch pro Analyse loggen
5. **Fallback** - Graceful degradation wenn API down

### Externe Datenquellen

Müssen recherchiert werden:

| Quelle | Optionen | Status |
|--------|----------|--------|
| Handelsregister | North Data, CompanyHub, offene-register.de | Kosten prüfen |
| Bundesanzeiger | Kein offizielles API | Scraping rechtlich grau |
| News | NewsAPI, MediaStack, Google News | Rate Limits |
| Bonität | Creditreform, Bürgel, CRIF | Teuer, für Premium |

---

## 7. MVP SCOPE

### Phase 1: "Vertrags-Röntgen" (4-6 Wochen)

Fokus: Vertragsprüfung end-to-end, sonst nichts.

- [ ] Upload PDF/DOCX
- [ ] AI-Analyse mit Risiko-Score
- [ ] Ergebnis-Darstellung (Risiken + Empfehlungen)
- [ ] Basic Auth (Email/Password)
- [ ] 1 Plan (kostenlose Beta mit Limit)
- [ ] Simpelstes UI das funktioniert

**Ziel**: Echte Nutzer, echtes Feedback, Validierung.

### Phase 2: Partner-Intelligence (+ 4 Wochen)

- [ ] Firmensuche + Identifikation
- [ ] Handelsregister-Integration
- [ ] News-Aggregation
- [ ] Risiko-Score für Partner
- [ ] Verknüpfung Partner ↔ Verträge

### Phase 3: Monetarisierung (+ 4 Wochen)

- [ ] Watchlist + Alerts
- [ ] Pricing Tiers
- [ ] Stripe Integration
- [ ] Multi-User / Teams

### Phase 4: Enterprise (ongoing)

- [ ] API
- [ ] SSO
- [ ] Advanced Reporting
- [ ] Custom Integrations

---

## 8. OFFENE FRAGEN FÜR DICH

1. **Frontend**: Next.js vs. SvelteKit - Empfehlung für diesen Use Case?

2. **Repo-Struktur**: Monorepo oder getrennt?

3. **Auth**: Selbst bauen vs. Supabase/Clerk vs. Keycloak?

4. **Datenquellen**: Kaufen wir einen Provider oder bauen wir Scraper?

5. **AI Cost**: Wie strukturieren wir Pricing dass Heavy User uns nicht ruinieren?

---

## 9. SUCCESS METRICS

| Metrik | MVP | Jahr 1 |
|--------|-----|--------|
| Analysen/Tag | 50 | 1.000 |
| Ø Analyse-Zeit | <90s | <60s |
| User Retention M1 | 40% | 60% |
| NPS | >30 | >50 |
| Zahlende Kunden | 10 | 500 |
| MRR | €1k | €30k |

---

## 10. LOS GEHT'S

Mein Vorschlag:
1. Du setzt Projekt auf (Repo, Structure, Dev Environment)
2. Wir bauen Contract Analysis Flow end-to-end zuerst
3. Ich teste mit echten Verträgen
4. Iterate.

Bei Fragen: Frag. Ich bin der Tester, du bist der Builder.

Let's ship this.
