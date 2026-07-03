# Datenschutz-Folgenabschätzung (DSFA) gemäß Art. 35 DSGVO

**System:** PlanBar — Schichtplanungs- und Zeiterfassungssystem  
**Erstellt:** 2026-07-03  
**Letzte Aktualisierung:** 2026-07-03  
**Verantwortlicher:** [Firmenname], [Adresse], [Kontakt]  
**Datenschutzbeauftragter:** [Name, Kontaktdaten falls benannt]  
**Version:** 1.0

---

## 1. Einleitung und Rechtsgrundlage

### 1.1 Zweck der DSFA

Diese Datenschutz-Folgenabschätzung (DSFA) gemäß Art. 35 Abs. 1 DSGVO bewertet die Risiken der Verarbeitung personenbezogener Daten im System **PlanBar** für die Rechte und Freiheiten der betroffenen Personen.

### 1.2 Prüfung: Ist eine DSFA erforderlich?

| Kriterium | Bewertung | Ergebnis |
|-----------|-----------|----------|
| **Art. 35 Abs. 1 DSGVO** — Systematische Bewertung persönlicher Aspekte | TiTO optimiert Schichtpläne basierend auf Mitarbeiterverfügbarkeit, Präferenzen und gesetzlichen Rahmenbedingungen. Dies stellt eine **automatisierte Bewertung** dar, die Einfluss auf Arbeitszeiten und -bedingungen hat. | ⚠️ **Ja** |
| **Art. 35 Abs. 3 lit. a** — Umfangreiche Verarbeitung | PlanBar wird für die Mitarbeiterverwaltung eingesetzt. Bei >250 Mitarbeitern ist eine DSFA empfohlen. | ⚠️ **Abhängig von Unternehmensgröße** |
| **Art. 35 Abs. 3 lit. b** — Besondere Kategorien (Art. 9) | Gesundheitsdaten (Krankheiten, Arbeitsunfähigkeiten) werden indirekt verarbeitet (Abwesenheiten, Krankheitsvertretungen). | ⚠️ **Ja** |
| **Art. 35 Abs. 3 lit. c** — Systematisches Monitoring | Zugriffskontrolle, Protokollierung von Änderungen, Audit-Trail. | ⚠️ **Ja** |

### 1.3 Ergebnis der Prüfung

**Eine DSFA ist erforderlich**, da:
1. TiTO eine automatisierte Entscheidung trifft, die erhebliche Wirkung auf die Arbeitsbedingungen der Mitarbeiter hat (Art. 35 Abs. 1)
2. Gesundheitsdaten (indirekt) verarbeitet werden (Art. 35 Abs. 3 lit. b)
3. Ein systematisches Monitoring der Mitarbeiterzugriffe stattfindet (Art. 35 Abs. 3 lit. c)

---

## 2. Beschreibung der geplanten Verarbeitungstätigkeiten

### 2.1 Systemübersicht

PlanBar besteht aus folgenden Hauptkomponenten:

| Komponente | Funktion |
|------------|----------|
| **Backend (FastAPI)** | API-Server für alle Geschäftslogiken |
| **Frontend (React)** | Benutzeroberfläche für Admins und Mitarbeiter |
| **TiTO** | Optimierungsalgorithmus für Schichtpläne |
| **PostgreSQL** | Primäre Datenbank |
| **LDAP/AD** | Single Sign-On Integration (optional) |
| **Webhook-System** | Event-Benachrichtigungen an externe Systeme |

### 2.2 Verarbeitete Datenkategorien

| Datenkategorie | Enthaltene Daten | Betroffene Personen |
|----------------|------------------|---------------------|
| **Stammdaten** | Name, E-Mail, Telefon, Abteilung, Position | Mitarbeiter |
| **Vertragsdaten** | Eintritts-/Austrittsdatum, Arbeitsvertrag, Stundenumfang | Mitarbeiter |
| **Arbeitszeitdaten** | Schichtpläne, Soll/Ist-Zeiten, Überstunden, Zeitkonto | Mitarbeiter |
| **Abwesenheitsdaten** | Urlaub, Krankheit, Sonderurlaub, Sabbatical | Mitarbeiter |
| **Authentifizierungsdaten** | E-Mail, Passwort (gehastet), LDAP-Attribut | Benutzer |
| **Zugriffsprotokolle** | API-Aufrufe, Änderungs-Historie, Audit-Logs | Benutzer |
| **Webhook-Daten** | URL, Events, Secret, Logs | Admins |

### 2.3 Automatisierte Entscheidungen (Art. 22 DSGVO)

**TiTO-Optimierung:**
- **Eingabe:** Mitarbeiterverfügbarkeit, Qualifikationen, gesetzliche Grenzen (ArbZG), Präferenzen
- **Verfahren:** Mathematische Optimierung (kein maschinelles Lernen)
- **Ausgabe:** Optimaler Schichtplan mit Zuweisungen
- **Eingriff in Rechte:** Die Zuweisung von Schichten kann die Lebensgestaltung der Mitarbeiter beeinflussen (Arbeitszeiten, Freizeitplanung)
- **Menschliches Eingreifen:** Admins können manuell eingreifen und Zuweisungen ändern

---

## 3. Bewertung der Notwendigkeit und Verhältnismäßigkeit

### 3.1 Rechtsgrundlagen

| Verarbeitung | Rechtsgrundlage | Bewertung |
|--------------|-----------------|-----------|
| Mitarbeiterstammdaten | Art. 6 Abs. 1 lit. b DSGVO (Vertragserfüllung) | ✅ Erforderlich |
| Schichtplanung | Art. 6 Abs. 1 lit. b DSGVO (Vertragserfüllung) | ✅ Erforderlich |
| Zeiterfassung | Art. 6 Abs. 1 lit. b DSGVO (Vertragserfüllung) + §611 BGB | ✅ Erforderlich |
| Gesundheitsdaten (Abwesenheiten) | Art. 9 Abs. 2 lit. b DSGVO (Arbeitsrechtliche Verpflichtung) | ✅ Erforderlich |
| Audit-Protokollierung | Art. 6 Abs. 1 lit. f DSGVO (berechtigtes Interesse) | ✅ Verhältnismäßig |
| LDAP/AD-Integration | Art. 6 Abs. 1 lit. f DSGVO (berechtigtes Interesse) | ✅ Verhältnismäßig |

### 3.2 Datenminimierung (Art. 5 Abs. 1 lit. c)

| Prüfpunkt | Status |
|-----------|--------|
| Werden nur Daten erhoben, die für den Zweck erforderlich sind? | ✅ Ja |
| Werden Gesundheitsdaten nur im Rahmen der Abwesenheitsverwaltung verarbeitet? | ✅ Ja |
| Werden keine überflüssigen Daten gespeichert? | ✅ Ja |
| Ist die Speicherungsdauer begrenzt? | ✅ Ja (Löschfristen definiert) |

### 3.3 Speicherbegrenzung (Art. 5 Abs. 1 lit. e)

| Datenkategorie | Aufbewahrungsfrist | Rechtsgrundlage |
|----------------|-------------------|-----------------|
| Mitarbeiterstammdaten | 10 Jahre nach Austritt | §257 HGB, §147 AO |
| Schichtpläne | 3 Jahre | §257 HGB |
| Zeiterfassung | 3 Jahre | §257 HGB |
| Audit-Logs | 1 Jahr | Art. 5 Abs. 1 lit. e DSGVO |
| Webhook-Logs | 30 Tage | Eigene Festlegung |
| Session-Tokens | 24 Stunden | Technische Notwendigkeit |

---

## 4. Bewertung der Risiken für die Rechte der Betroffenen

### 4.1 Risikobewertungsmatrix

| Risiko | Eintrittswahrscheinlichkeit | Schwere | Risikostufe |
|--------|----------------------------|---------|-------------|
| Unbefugter Zugriff auf Mitarbeiterdaten | Mittel | Hoch | **Hoch** |
| Manipulation von Schichtplänen | Niedrig | Hoch | **Mittel** |
| Ausfall des Systems (Datenverlust) | Niedrig | Hoch | **Mittel** |
| Verlust der Vertraulichkeit von Gesundheitsdaten | Niedrig | Sehr hoch | **Hoch** |
| Automatisierte Fehlentscheidungen durch TiTO | Mittel | Mittel | **Mittel** |
| Übermittlung an Dritte ohne Rechtsgrundlage | Niedrig | Hoch | **Mittel** |

### 4.2 Detaillierte Risikoanalyse

#### R1: Unbefugter Zugriff auf Mitarbeiterdaten

- **Beschreibung:** Ein Angreifer oder unbefugter Benutzer erhält Zugriff auf sensitive Mitarbeiterdaten (Stammdaten, Gesundheitsdaten, Arbeitszeiten).
- **Betroffene Rechte:** Recht auf informationelle Selbstbestimmung, Recht auf Privatsphäre
- **Potenzieller Schaden:** Identitätsdiebstahl, Diskriminierung, soziale Schädigung

#### R2: Manipulation von Schichtplänen

- **Beschreibung:** Unbefugte Änderung von Schichtplänen, die zu Fehlbesetzungen oder ungerechten Arbeitsbedingungen führt.
- **Betroffene Rechte:** Recht auf faire Arbeitsbedingungen
- **Potenzieller Schaden:** Wirtschaftliche Einbußen, Arbeitsbelastung

#### R3: Ausfall des Systems

- **Beschreibung:** Technischer Ausfall oder Datenverlust durch Hardware-/Softwarefehler.
- **Betroffene Rechte:** Recht auf Schutz personenbezogener Daten
- **Potenzieller Schaden:** Verlust von Arbeitszeitnachweisen, Verwaltungsaufwand

#### R4: Verlust der Vertraulichkeit von Gesundheitsdaten

- **Beschreibung:** Gesundheitsdaten (Krankheitsstatus, Arbeitsunfähigkeiten) werden unbefugt offengelegt.
- **Betroffene Rechte:** Recht auf Schutz besonderer Kategorien personenbezogener Daten (Art. 9)
- **Potenzieller Schaden:** Diskriminierung am Arbeitsplatz, soziale Stigmatisierung

#### R5: Automatisierte Fehlentscheidungen durch TiTO

- **Beschreibung:** Der Optimierungsalgorithmus trifft Entscheidungen, die zu ungerechten Schichtzuweisungen führen.
- **Betroffene Rechte:** Recht auf menschliches Eingreifen bei automatisierten Entscheidungen (Art. 22)
- **Potenzieller Schaden:** Ungerechte Arbeitsverteilung, Einschränkung der Lebensgestaltung

---

## 5. Technische und organisatorische Maßnahmen zur Risikominderung

### 5.1 Technische Maßnahmen (Art. 32 DSGVO)

| Maßnahme | Beschreibung | Risiko adressiert |
|----------|-------------|-------------------|
| **Verschlüsselung at rest** | PostgreSQL-TDE, verschlüsselte Datenbank-Backups | R1, R4 |
| **Verschlüsselung in transit** | TLS 1.3 für alle API-Kommunikation | R1, R4 |
| **Passwort-Hashing** | bcrypt mit Salt für lokale Passwörter | R1 |
| **JWT-Tokens** | Kurze Ablaufzeiten (24h), sichere Cookies | R1 |
| **Rollenbasierte Zugriffskontrolle (RBAC)** | Admin-, Manager-, User-Rollen mit unterschiedlichen Berechtigungen | R1, R2, R4 |
| **API-Authentifizierung** | Bearer-Token für alle API-Endpunkte | R1 |
| **Health-Endpoint-Schutz** | Admin-Auth für /health/db, /metrics | R1 |
| **CORS-Policy** | Nur erlaubte Origins | R1 |
| **HMAC-SHA256 Webhook-Signatur** | Signierung aller Webhook-Requests | R1 |
| **LDAP/TLS** | Verschlüsselte LDAP-Kommunikation | R1 |
| **VAPID Keys** | Serverseitig generierte Push-Notification-Keys | R1 |
| **Datenbank-Backups** | Automatische, verschlüsselte Backups | R3 |
| **Non-Root Container** | Alle Docker-Container laufen als appuser (UID 1001) | R1 |
| **DB-Port-Bindung** | PostgreSQL nur auf localhost (127.0.0.1) erreichbar | R1 |

### 5.2 Organisatorische Maßnahmen

| Maßnahme | Beschreibung | Risiko adressiert |
|----------|-------------|-------------------|
| **Verarbeitungsverzeichnis** | Art. 30 DSGVO — Dokumentation aller Verarbeitungstätigkeiten | Alle |
| **Datenschutzerklärung** | Art. 13/14 DSGVO — Information der Betroffenen | Alle |
| **Betroffenenrechte API** | Art. 15-22 DSGVO — Auskunft, Berichtigung, Löschung, Datenübertragbarkeit | Alle |
| **Cookie-Consent** | Art. 6 DSGVO / ePrivacy — Opt-in für nicht-essentielle Cookies | Alle |
| **Soft-Delete mit Pseudonymisierung** | Art. 17 DSGVO — Recht auf Löschung mit Aufbewahrungspflichten | Alle |
| **Audit-Trail** | Protokollierung aller Änderungen ohne sensible Daten | R1, R2 |
| **Regelmäßige Updates** | Dependabot-Alerts, Sicherheits-Patches | Alle |

### 5.3 Organisatorische Maßnahmen (人文组织)

| Maßnahme | Beschreibung |
|----------|-------------|
| **Zugriffskonzept** | Definition von Rollen und Berechtigungen |
| **Schulung** | Regelmäßige Datenschutz-Schulung für Administratoren |
| **Incident-Response-Plan** | Verfahren bei Datenschutzverletzungen (Art. 33/34 DSGVO) |
| **Auftragsverarbeitungsvertrag** | Art. 28 DSGVO — Verträge mit Hosting-Providern |
| **Testimonials** | [Platzhalter] |

---

## 6. Stellungnahme des Datenschutzbeauftragten

> **[Platzhalter]** — Name des Datenschutzbeauftragten  
> **Datum:** [Datum]  
> **Stellungnahme:**  
> [Hier folgt die Stellungnahme des Datenschutzbeauftragten zur DSFA.  
> Der DSB bestätigt, dass die identifizierten Risiken angemessen bewertet  
> und geeignete Maßnahmen zur Risikominderung implementiert wurden.]

---

## 7. Ergebnis und Empfehlungen

### 7.1 Gesamtbewertung

| Aspekt | Bewertung |
|--------|-----------|
| **Risikostufe vor Maßnahmen** | Hoch |
| **Risikostufe nach Maßnahmen** | Niedrig bis Mittel |
| **Verbleibende Risiken** | Akzeptabel mit Monitoring |

### 7.2 Empfehlungen

1. **TiTO-Transparenz:** Sicherstellen, dass die Optimierungslogik nachvollziehbar und dokumentiert ist.
2. **Regelmäßige Überprüfung:** DSFA jährlich oder bei wesentlichen Änderungen aktualisieren.
3. **Incident-Response:** Verfahren bei Datenschutzverletzungen testen und dokumentieren.
4. **Monitoring:** Zugriffsprotokolle regelmäßig überprüfen.
5. **DSB-Einbindung:** Stellungnahme des Datenschutzbeauftragten einholen und dokumentieren.

### 7.3 Fristen

| Aufgabe | Verantwortlich | Frist |
|---------|---------------|-------|
| DSFA aktualisieren | Datenschutzbeauftragter | Jährlich |
| Incident-Response-Plan testen | IT-Admin | Halbjährlich |
| Zugriffsprotokolle prüfen | IT-Admin | Monatlich |
| TiTO-Logik dokumentieren | Entwicklung | Bei Änderungen |

---

## 8. Änderungshistorie

| Datum | Version | Änderung | Autor |
|-------|---------|----------|-------|
| 2026-07-03 | 1.0 | Erstfassung | Orion (Automatisiert) |

---

## Anhang A: Betroffene Rechte (Art. 15-22 DSGVO)

| Recht | Beschreibung | Umsetzung in PlanBar |
|-------|-------------|---------------------|
| **Auskunftsrecht (Art. 15)** | Recht auf Auskunft über verarbeitete Daten | `GET /api/v1/gdpr/export` |
| **Berichtigungsrecht (Art. 16)** | Recht auf Korrektur unrichtiger Daten | `PUT /api/v1/users/me` |
| **Recht auf Löschung (Art. 17)** | Recht auf Löschung personenbezogener Daten | `DELETE /api/v1/users/me` (Soft-Delete) |
| **Recht auf Einschränkung (Art. 18)** | Recht auf Einschränkung der Verarbeitung | [Implementierung] |
| **Datenübertragbarkeit (Art. 20)** | Recht auf maschinenlesbares Format | `GET /api/v1/gdpr/export?format=csv` |
| **Widerspruchsrecht (Art. 21)** | Recht auf Widerspruch gegen Verarbeitung | [Implementierung] |
| **Recht auf Information (Art. 13/14)** | Informationspflichten | Datenschutzerklärung |

---

## Anhang B: Technische Architektur

```
┌─────────────────────────────────────────────────────────┐
│                    PlanBar System                        │
├─────────────────────────────────────────────────────────┤
│  Frontend (React)  ←→  Backend (FastAPI)  ←→  TiTO     │
│       │                      │                    │      │
│       │                      │                    │      │
│       ▼                      ▼                    ▼      │
│  [PWA/Offline]        [PostgreSQL]           [Worker]    │
│                           │                              │
│                           ▼                              │
│                    [LDAP/AD (optional)]                   │
└─────────────────────────────────────────────────────────┘
```

**Datenfluss:**
1. Mitarbeiter → Frontend → Backend → TiTO (Schichtoptimierung)
2. Admin → Frontend → Backend → PostgreSQL (Datenverwaltung)
3. Backend → Webhook-Externe Systeme (Event-Benachrichtigungen)

---

*Dieses Dokument ist ein Lebendiges Dokument und wird bei wesentlichen Änderungen am System aktualisiert.*
