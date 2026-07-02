# Verarbeitungsverzeichnis gemäß Art. 30 DSGVO

**Erstellt:** 2026-07-02
**Letzte Aktualisierung:** 2026-07-02
**Verantwortlicher:** [Firmenname], [Adresse], [Kontakt]
**Datenschutzbeauftragter:** [Name, Kontaktdaten falls benannt]

---

## 1. Überblick

Dieses Verzeichnis dokumentiert alle Verarbeitungstätigkeiten personenbezogener Daten im System **PlanBar** gemäß Art. 30 Abs. 1 DSGVO. Es dient als Nachweis für die Rechenschaftspflicht (Art. 5 Abs. 2 DSGVO).

---

## 2. Verarbeitungstätigkeiten

### 2.1 User-Management

| Feld | Beschreibung |
|------|-------------|
| **Zweck** | Registrierung, Authentifizierung, Autorisierung von Benutzern |
| **Rechtsgrundlage** | Art. 6 Abs. 1 lit. b DSGVO (Vertragserfüllung) / lit. f (berechtigtes Interesse) |
| **Kategorien betroffener Personen** | Mitarbeiter, Administratoren |
| **Kategorien personenbezogener Daten** | E-Mail-Adresse, Passwort (gehastet), Benutzername, Rollen, Erstellungsdatum |
| **Empfänger** | Interne Systemkomponenten (Backend-API) |
| **Drittländer-Übermittlung** | Keine |
| **Löschfrist** | Nach 30 Tagen nach Kontolöschung (Art. 17 DSGVO) |
| **Technische Maßnahmen (Art. 32)** | Passwort-Hashing (bcrypt), JWT-Tokens, HTTPS, CORS-Policy |

### 2.2 Mitarbeiterverwaltung

| Feld | Beschreibung |
|------|-------------|
| **Zweck** | Verwaltung von Stammdaten, Verträgen und Arbeitszeiten |
| **Rechtsgrundlage** | Art. 6 Abs. 1 lit. b DSGVO (Vertragserfüllung) |
| **Kategorien betroffener Personen** | Mitarbeiter |
| **Kategorien personenbezogener Daten** | Name, E-Mail, Telefon, Abteilung, Position, Eintritts-/Austrittsdatum, Vertragsdaten |
| **Empfänger** | Interne Systemkomponenten, Admin-Benutzer |
| **Drittländer-Übermittlung** | Keine |
| **Löschfrist** | 10 Jahre nach Austritt (§257 HGB, §147 AO) |
| **Technische Maßnahmen (Art. 32)** | Rollenbasierte Zugriffskontrolle, Protokollierung von Änderungen |

### 2.3 Schichtplanung

| Feld | Beschreibung |
|------|-------------|
| **Zweck** | Erstellung, Optimierung (TiTO) und Zuweisung von Dienstplänen |
| **Rechtsgrundlage** | Art. 6 Abs. 1 lit. b DSGVO (Vertragserfüllung) |
| **Kategorien betroffener Personen** | Mitarbeiter |
| **Kategorien personenbezogener Daten** | Name, Arbeitszeiten, Schichtzuweisungen, Verfügbarkeit |
| **Empfänger** | TiTO-System (extern), Mitarbeiter über Benachrichtigungen |
| **Drittländer-Übermittlung** | Keine |
| **Löschfrist** | 3 Jahre nach Ende der Planungsperiode |
| **Technische Maßnahmen (Art. 32)** | HTTPS, rollenbasierte Zugriffskontrolle |

### 2.4 Zeiterfassung

| Feld | Beschreibung |
|------|-------------|
| **Zweck** | Erfassung und Berechnung von Arbeitszeiten (Soll/Ist-Vergleich) |
| **Rechtsgrundlage** | Art. 6 Abs. 1 lit. b DSGVO (Vertragserfüllung) / lit. c (rechtliche Verpflichtung §611a BGB) |
| **Kategorien betroffener Personen** | Mitarbeiter |
| **Kategorien personenbezogener Daten** | Arbeitszeiten, Pausen, Überstunden, Zeitkonto |
| **Empfänger** | Interne Systemkomponenten, Admin-Benutzer |
| **Drittländer-Übermittlung** | Keine |
| **Löschfrist** | 10 Jahre (§257 HGB, §147 AO) |
| **Technische Maßnahmen (Art. 32)** | HTTPS, Protokollierung, rollenbasierte Zugriffskontrolle |

### 2.5 Request-Logging

| Feld | Beschreibung |
|------|-------------|
| **Zweck** | HTTP-Request-Logging zur Sicherheitsüberwachung und Fehleranalyse |
| **Rechtsgrundlage** | Art. 6 Abs. 1 lit. f DSGVO (berechtigtes Interesse an IT-Sicherheit) |
| **Kategorien betroffener Personen** | Alle Benutzer |
| **Kategorien personenbezogener Daten** | IP-Adresse, User-Agent, Request-Pfad, Zeitstempel |
| **Empfänger** | Interne Logs |
| **Drittländer-Übermittlung** | Keine |
| **Löschfrist** | 90 Tage (automatische Rotation) |
| **Technische Maßnahmen (Art. 32)** | Log-Rotation, eingeschränkter Zugriff |

### 2.6 Session-Management

| Feld | Beschreibung |
|------|-------------|
| **Zweck** | Verwaltung von Benutzersitzungen via JWT-Tokens |
| **Rechtsgrundlage** | Art. 6 Abs. 1 lit. f DSGVO (berechtigtes Interesse an sicherer Authentifizierung) |
| **Kategorien betroffener Personen** | Alle Benutzer |
| **Kategorien personenbezogener Daten** | User-ID, Token-Ablaufzeit, Rollen |
| **Empfänger** | Interne Systemkomponenten |
| **Drittländer-Übermittlung** | Keine |
| **Löschfrist** | Ablauf des JWT-Tokens (konfigurierbar, Standard: 24 Stunden) |
| **Technische Maßnahmen (Art. 32)** | HTTPS-only Cookies, HttpOnly-Flag, Secure-Flag |

### 2.7 Webhook-System

| Feld | Beschreibung |
|------|-------------|
| **Zweck** | Benachrichtigung externer Systeme bei relevanten Events |
| **Rechtsgrundlage** | Art. 6 Abs. 1 lit. f DSGVO (berechtigtes Interesse an Integration) |
| **Kategorien betroffener Personen** | Admin-Benutzer (die Webhooks konfigurieren) |
| **Kategorien personenbezogener Daten** | Webhook-URLs, Event-Typen (keine personenbezogenen Daten im Payload) |
| **Empfänger** | Konfigurierte externe URLs |
| **Drittländer-Übermittlung** | Abhängig von Webhook-Konfiguration |
| **Löschfrist** | Webhook-Logs: 100 Einträge (automatisches Trimmen) |
| **Technische Maßnahmen (Art. 32)** | HMAC-SHA256-Signatur, Retry-Logik |

### 2.8 LDAP/AD-Integration

| Feld | Beschreibung |
|------|-------------|
| **Zweck** | Single Sign-On und automatische Benutzersynchronisation |
| **Rechtsgrundlage** | Art. 6 Abs. 1 lit. b DSGVO (Vertragserfüllung) |
| **Kategorien betroffener Personen** | Mitarbeiter |
| **Kategorien personenbezogener Daten** | E-Mail, Name, LDAP-Gruppen, LDAP-DN |
| **Empfänger** | Interne Systemkomponenten, LDAP-Server |
| **Drittländer-Übermittlung** | Keine (LDAP-Server ist intern) |
| **Löschfrist** | Wie User-Management (30 Tage nach Kontolöschung) |
| **Technische Maßnahmen (Art. 32)** | TLS-Unterstützung, Audit-Logging |

---

## 3. Auftragsverarbeiter (Art. 28 DSGVO)

| Auftragsverarbeiter | Zweck | Standort |
|---------------------|-------|----------|
| [Hosting-Provider] | Server-Hosting | [Land] |
| [E-Mail-Service] | E-Mail-Versand | [Land] |

---

## 4. Technische und organisatorische Maßnahmen (Art. 32 DSGVO)

1. **Verschlüsselung**: HTTPS/TLS für alle Kommunikation
2. **Zugriffskontrolle**: Rollenbasierte Berechtigungen (Admin, User)
3. **Passwortschutz**: bcrypt-Hashing für Passwörter
4. **Protokollierung**: Audit-Logging für sicherheitsrelevante Aktionen
5. **Datensicherung**: Regelmäßige Datenbank-Backups
6. **Pseudonymisierung**: Soft-Delete mit Pseudonymisierung bei Kontolöschung
7. **Recht auf Löschung**: Art. 17 DSGVO implementiert (Self-Service)
8. **Cookie-Consent**: DSGVO-konformer Cookie-Banner

---

## 5. Verantwortlicher

| Feld | Wert |
|------|------|
| **Name** | [Firmenname] |
| **Adresse** | [Straße, PLZ, Ort] |
| **Kontakt** | [E-Mail, Telefon] |
| **Datenschutzbeauftragter** | [Name, Kontaktdaten falls benannt] |

---

## 6. Historie

| Datum | Änderung | Autor |
|-------|----------|-------|
| 2026-07-02 | Erstversion erstellt | PlanBar-Team |

---

*Dieses Verzeichnis ist regelmäßig zu aktualisieren (mindestens jährlich oder bei Änderungen der Verarbeitungstätigkeiten).*
