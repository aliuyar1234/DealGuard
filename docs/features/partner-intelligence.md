# Feature: Partner-Intelligence (Phase 2)

## Status
**Planned**

## Übersicht

Vor Vertragsabschluss: Wer ist mein Geschäftspartner wirklich? Automatische Recherche zu Firmen inkl. Risiko-Bewertung.

## User Stories

1. **Als Einkäufer** möchte ich einen Lieferanten prüfen, bevor ich einen Vertrag unterschreibe.

2. **Als Geschäftsführer** möchte ich gewarnt werden, wenn ein Partner finanzielle Probleme hat.

3. **Als Compliance-Officer** möchte ich wissen, ob ein Partner auf Sanktionslisten steht.

## Datenquellen

| Quelle | Daten | API |
|--------|-------|-----|
| Handelsregister | Geschäftsführer, Kapital, Sitz | North Data, CompanyHub |
| Creditreform/SCHUFA | Bonität, Zahlungsverhalten | Kostenpflichtig |
| Bundesanzeiger | Jahresabschlüsse | Scraping? |
| Sanktionslisten | EU, UN, OFAC | OpenSanctions |
| News | Pressemitteilungen, Skandale | News APIs |
| ESG-Datenbanken | Nachhaltigkeit, Lieferketten | TBD |

## Partner Risiko-Score

Komponenten:
- **Finanzielle Stabilität** (30%) - Bonität, Eigenkapital
- **Rechtliche Compliance** (25%) - Keine Sanktionen, Insolvenzverfahren
- **Reputation** (20%) - News-Sentiment, Bewertungen
- **Operative Stabilität** (15%) - Alter der Firma, Management-Wechsel
- **ESG** (10%) - Nachhaltigkeit, Arbeitsbedingungen

## Technische Anforderungen

### Backend
- Neues Domain: `domain/partners/`
- Neue Models: `partners`, `partner_checks`, `partner_alerts`
- API für externe Datenquellen
- Caching (Firmendaten ändern sich selten)

### Frontend
- Partner-Suche (Firmenname → Vorschläge)
- Partner-Profil (alle Daten auf einen Blick)
- Verknüpfung Partner ↔ Verträge
- Alerts Dashboard

### AI
- News-Zusammenfassung
- Sentiment-Analyse
- Risiko-Interpretation

## MVP Scope (Phase 2.1)

1. Partner manuell anlegen (Name, Adresse)
2. Handelsregister-Abfrage (North Data API)
3. Basis-Score aus verfügbaren Daten
4. Verknüpfung mit Verträgen

## Erweiterungen (Phase 2.2+)

- Automatische Partner-Erkennung aus Verträgen
- Watchlist mit E-Mail Alerts
- Sanktionslisten-Prüfung
- News-Monitoring

## Offene Fragen

- [ ] Welche API für Handelsregister? (North Data vs CompanyHub vs eigenes Scraping)
- [ ] Bonität: Creditreform direkt oder Aggregator?
- [ ] News: Eigenes Crawling oder API (NewsAPI, GDELT)?
- [ ] Rechtlich: Dürfen wir Firmendaten speichern/cachen?
