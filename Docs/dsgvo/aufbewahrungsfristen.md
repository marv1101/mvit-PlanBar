# Aufbewahrungsfristen — PlanBar

> Zentrale Wahrheitsquelle für alle Datenkategorien, deren Aufbewahrungsfristen
> und die jeweiligen Rechtsgrundlagen.
> Verarbeitungszweck → Löschfrist Mapping gemäß Art. 5 Abs. 1 lit. e DSGVO
> (Speicherbegrenzung / „data minimisation" / „purpose limitation").

Letzte Aktualisierung: 2026-07-12 · Issue [#48](https://github.com/marv1101/mvit-PlanBar/issues/48)

---

## 1. Übersicht

| # | Datenkategorie | Frist | Rechtsgrundlage | Aktion |
|---|---|---|---|---|
| 1 | User-Account (inaktiv) | 6 Monate nach Kündigung | Beweissicherung | Pseudonymisierung → dann Löschung |
| 2 | Employee-Stammdaten (ausgeschieden) | 10 Jahre | § 147 AO (Abgabenordnung) | Pseudonymisierung → dann Löschung |
| 3 | Zeitkonto-Daten (Timecards) | 10 Jahre | Lohnunterlagen, § 147 AO | Löschung |
| 4 | Request-Logs | 90 Tage | Art. 5 Abs. 1 lit. e DSGVO | Löschung |
| 5 | Auth-Logs (Login/Logout) | 1 Jahr | Sicherheits-Compliance | Löschung |
| 6 | Audit-Logs | 3 Jahre | Art. 30 DSGVO (Nachweispflicht) | Löschung |
| 7 | Session-Tokens | bereits durch `max_age` abgedeckt | — | ✅ Kein zusätzlicher Aufwand |
| 8 | Schichtpläne (abgeschlossen) | 2 Jahre | Betrieblich | Löschung |
| 9 | Schichtwünsche (verarbeitet) | 1 Jahr | Betrieblich | Löschung |
| 10 | Urlaubsanträge (abgeschlossen) | 5 Jahre | Urlaubsrecht | Löschung |
| 11 | Pinboard-Einträge | 1 Jahr nach Löschung | Betrieblich | Löschung |
| 12 | Webhook-Logs | 90 Tage | Art. 5 Abs. 1 lit. e DSGVO | Löschung |

---

## 2. Rechtsgrundlagen im Detail

### § 147 AO — Abgabenordnung
Aufbewahrungspflicht für Buchungsbelege, Lohn- und Gehaltsunterlagen.
Frist: **10 Jahre** ab Ende des Kalenderjahrs der letzten Betätigung.
Betrifft: Employee-Stammdaten, Zeitkonto-Daten, Verträge.

### § 257 HGB — Handelsgesetzbuch
Aufbewahrung von Unterlagen der Handels- und Steuerbuchführung.
Frist: **6 Jahre** (Handelsbriefe) bzw. **10 Jahre** (Bücher, Aufzeichnungen).
Betrifft: Zeitkonto-Daten, Verträge (im Overlap mit § 147 AO).

### Art. 5 Abs. 1 lit. e DSGVO — Speicherbegrenzung
Personenbezogene Daten dürfen nicht in einer Form gespeichert werden, die
die Identifizierung der betroffenen Personen länger ermöglicht, als es für
die Zwecke der Verarbeitung erforderlich ist.
Betrifft: Request-Logs, Webhook-Logs (kein betriebliches Interesse an
längerer Aufbewahrung).

### Art. 30 DSGVO — Verzeichnis der Verarbeitungstätigkeiten
Nachweispflicht für Verarbeitungsvorgänge. Aufbewahrung der Audit-Logs
ermöglicht die Erfüllung der Dokumentationspflicht.
Betrifft: Audit-Logs.

---

## 3. Verarbeitungszweck → Löschfrist Mapping

| Verarbeitungszweck | Kategorie(n) | Löschfrist |
|---|---|---|
| Personalverwaltung | Employee-Stammdaten, Verträge | 10 Jahre (§ 147 AO) |
| Lohnabrechnung / Zeitkonto | Timecards | 10 Jahre (§ 147 AO) |
| Zugriffskontrolle / Authentifizierung | Auth-Logs | 1 Jahr |
| Betriebliche Kommunikation | Pinboard-Einträge | 1 Jahr nach Löschung |
| Dienstplanung | Schichtpläne, Schichtwünsche | 2 Jahre / 1 Jahr |
| Urlaubsverwaltung | Urlaubsanträge | 5 Jahre |
| Sicherheits-Compliance | Request-Logs, Webhook-Logs | 90 Tage |
| Nachweispflicht (Art. 30) | Audit-Logs | 3 Jahre |
| Betriebliche Nutzung | User-Accounts (inaktiv) | 6 Monate (Pseudonymisierung) |

---

## 4. Begründung je Frist

### User-Account (inaktiv) — 6 Monate
Nach Kündigung oder Deaktivierung wird das Konto pseudonymisiert.
Die Pseudonymisierung behält die referenzielle Integrität für laufende
Dienstpläne. Nach 6 Monaten erfolgt die vollständige Löschung.
Rechtsgrundlage: Beweissicherung (Übergangsfrist für mögliche arbeitsrechtliche
Auseinandersetzungen, §§ 195, 199 BGB).

### Employee-Stammdaten (ausgeschieden) — 10 Jahre
Personalunterlagen unterliegen der Aufbewahrungspflicht nach § 147 AO.
Erst nach Ablauf der steuerrechtlichen Frist darf eine Löschung erfolgen.
Zuvor wird pseudonymisiert.

### Zeitkonto-Daten — 10 Jahre
Lohnunterlagen (§ 147 AO). Zeitkonten sind Teil der Lohnabrechnung und
müssen 10 Jahre aufbewahrt werden.

### Request-Logs — 90 Tage
Nur für Debugging und Fehleranalyse relevant. Kein betriebliches oder
rechtliches Interesse an längerer Aufbewahrung. Art. 5 Abs. 1 lit. e DSGVO.

### Auth-Logs — 1 Jahr
Sicherheitsrelevante Aufzeichnungen. Ein Jahr ermöglicht die Nachvollziehbarkeit
von Sicherheitsvorkommnissen. Danach Löschung.

### Audit-Logs — 3 Jahre
Erfüllung der Nachweispflicht nach Art. 30 DSGVO. Drei Jahre decken
typische Verjährungsfristen für Datenschutzverstöße ab (§ 83 DSGVO i.V.m.
§§ 195, 199 BGB).

### Schichtpläne (abgeschlossen) — 2 Jahre
Betriebliches Interesse an der Nachvollziehbarkeit vergangener Dienstpläne
(z.B. bei Streitigkeiten über Arbeitszeiten). Danach Löschung.

### Schichtwünsche (verarbeitet) — 1 Jahr
Nach Umsetzung oder Ablehnung kein betriebliches Interesse mehr.
Ein Jahr Puffer für Rückfragen.

### Urlaubsanträge (abgeschlossen) — 5 Jahre
Urlaubsabrechnung unterliegt der Lohnunterlagen-Pflicht. Fünf Jahre
als Konservativ-Schätzung (Überlappung mit § 147 AO).

### Pinboard-Einträge — 1 Jahr nach Löschung
Betriebliche Kommunikation. Ein Jahr nach Ende der Relevanz
(Löschung durch Autor/Admin) zur Nachvollziehbarkeit.

### Webhook-Logs — 90 Tage
Nur für Debugging der Webhook-Integration relevant. Kein rechtliches
Interesse an längerer Aufbewahrung.

---

## 5. Implementierung

Die Aufbewahrungsfristen werden in `src/app/services/retention_service.py`
als `RETENTION_RULES`-Dictionary implementiert (Code-Konstante).
Ein automatischer Cleanup-Scheduler (optional APScheduler oder externes Cron)
führt täglich um 03:00 Uhr die Bereinigung durch.

Admin-Endpoints:
- `POST /api/v1/retention/cleanup` — Manueller Trigger
- `GET /api/v1/retention/policies` — Auflistung aller Regeln
- `GET /api/v1/retention/preview` — Dry-Run ohne Seiteneffekte

Audit-Trail: Jede Löschung/Pseudonymisierung wird in der
`retention_audit_logs`-Tabelle protokolliert (keine PII im Log).
