# ADR 0001: Produktname PlanBar beibehalten

> **Status:** Akzeptiert (Vorschlag) · **Datum:** 2026-07-19 · **Bezieht sich auf:** Issue #66 "Umbenennung prüfen"

## Kontext

Issue #66 schlug eine Umbenennung der Anwendung vor. Diskutierte Alternativen:

- DienstDingo
- PlanPanda
- Planix
- Planaro
- Plani

Zur Diskussion standen Marketing-Attraktivität, Markenidentität, Domain-Verfügbarkeit und SEO-Relevanz.

## Entscheidungstreiber

- **Bestandskunden-Bekanntheit:** Der Name "PlanBar" ist in der gesamten Codebase, allen Konfigurationen, der DSGVO-Dokumentation, dem Cookie-Banner, der Impressum-Seite und der Außenkommunikation verankert.
- **Technische Reichweite:** Eine Umbenennung berührt > 200 Dateien (Backend-Routen, Frontend-Titel, Docker-Container, DB-Namen, Nginx-Config, .env-Templates, Compose-Services, Audit-Logs, Test-Fixtures, GitHub-Actions, TiTO-Worker).
- **Domain & SEO:** `planbar.app` und `planbar.de` sind die zentralen Identifikatoren; ein Namenswechsel würde Redirect-Ketten, Suchmaschinen-Re-Indexierung und Verlust bestehender Backlinks bedeuten.
- **DSGVO-Folgen:** Impressum, Datenschutzerklärung, Verarbeitungsverzeichnis, Auftragsverarbeitungsvertrag, AVV-Anlagen — alle nennen "PlanBar" als Produktnamen. Eine Umbenennung erzwingt eine vollständige Dokumentenrevision mit erneuter Rechtsprüfung.
- **Team-Kapazität:** Sprint-Kapazität ist durch offene Features gebunden (Reporting, Webhooks, SSO, Lohnabrechnungs-Export). Eine Umbenennung würde mehrere Sprints binden ohne direkten Produktnutzen.

## In Betracht gezogene Alternativen

| Name | Pro | Contra | Bewertung |
|------|-----|--------|-----------|
| **PlanBar** (Status quo) | Etabliert, semantisch klar (Plan + Bar = Planungstool), Domain verfügbar | Klingt nach Gastronomie | ✅ Beibehalten |
| DienstDingo | Niedlich, einprägsam | "Dienst" mehrdeutig, kein Domain-Bezug zur Schichtplanung | ❌ |
| PlanPanda | Sympathisch, "Plan" bleibt | Tier-Metapher ohne Mehrwert, Markenrecherche nötig | ⚠️ |
| Planix | Modern, kurz | Erinnert stark an "Planfix" (existierende SaaS), Kollisionsrisiko | ❌ |
| Planaro | Klingt nach Produkt | Schwer auszusprechen, keine Wiedererkennung | ❌ |
| Plani | Sehr kurz | Zu generisch, keine Markenpersönlichkeit | ❌ |

## Entscheidung

**PlanBar wird beibehalten.** Der Name beschreibt präzise das Produkt (Schichtplanung als zentrale Funktion) und hat in der Zielgruppe (KMU im DACH-Raum) bereits Wiedererkennungswert aufgebaut.

## Konsequenzen

### Positiv
- Kein Refactoring-Aufwand in Codebase
- DSGVO-Dokumentation bleibt konsistent
- Bestehende Kunden und Marketing-Materialien bleiben gültig
- Sprint-Kapazität bleibt für Feature-Entwicklung verfügbar

### Negativ
- Sollte das Produkt später repositioniert werden (z.B. Internationalisierung), müsste diese Entscheidung erneut geprüft werden
- Der "Bar"-Suffix bleibt eine kleine Markenrisiko-Komponente (Assoziation Gastronomie)

## Wenn dennoch umbenannt werden soll

Falls zu einem späteren Zeitpunkt eine Umbenennung notwendig wird, empfiehlt sich folgendes Vorgehen:

1. **Phase 0 (1 Sprint):** Markenrecherche, Domain-Check, Trademark-Recherche (DPMA), Konkurrenz-Analyse
2. **Phase 1 (1 Sprint):** Stakeholder-Interviews (5 Kunden), finale Namenswahl
3. **Phase 2 (2 Sprints):** Codebase-Migration mit automatisierter Codemod (Backend-Routen, Frontend-Labels, DB-Schemas, Nginx-Config, Docker-Container, GitHub-Org-Umbenennung)
4. **Phase 3 (1 Sprint):** Dokumenten-Refresh (DSGVO-Suite: Impressum, Datenschutz, Verarbeitungsverzeichnis, AVV, DSFA, Retention-Richtlinie) + Rechtsprüfung
5. **Phase 4 (laufend):** 301-Redirects, SEO-Re-Indexierung, Marketing-Update, Kundenkommunikation

Geschätzter Gesamtaufwand: **4-5 Sprints + laufende SEO-Begleitung**.

## Verweise

- Issue #66: Umbenennung prüfen
- DSGVO-Dokumentation: `Docs/dsgvo/impressum.md`, `Docs/dsgvo/datenschutzerklaerung.md`
- README: `/README.md` (zentrale Erwähnung)

---

**Hinweis:** Diese ADR ersetzt keine Markenrechts-Beratung. Bei einer tatsächlichen Umbenennung sollten DPMA-Recherche und Rechtsberatung eingeholt werden.
