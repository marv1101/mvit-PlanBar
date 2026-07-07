# Datenminimierung und Zweckbindung — Prüfung gemäß Art. 5 Abs. 1 lit. b, c DSGVO

> **Status:** Entwurf  
> **Erstellt:** 2026-07-07  
> **Verantwortlich:** Datenschutzbeauftragter PlanBar

---

## 1. Rechtliche Grundlagen

### Art. 5 Abs. 1 lit. b DSGVO — Zweckbindung
Personenbezogene Daten müssen **für festgelegte, eindeutige Zwecke** erhoben werden und dürfen nicht in einer mit diesen Zwecken nicht zu vereinbarender Weise weiterverarbeitet werden.

### Art. 5 Abs. 1 lit. c DSGVO — Datenminimierung
Personenbezogene Daten müssen **dem Zweck angemessen und erheblich sowie auf das für die Zwecke der Verarbeitung notwendige Maß beschränkt** sein.

---

## 2. Prüfung der Datenmodelle

### 2.1 User-Tabelle (`users`)

| Feld | Zweck | Erforderlich | Bewertung |
|------|-------|--------------|-----------|
| `id` | Primärschlüssel | ✅ Ja | Technisch erforderlich |
| `username` | Authentifizierung | ✅ Ja | Login-Identifikator |
| `email` | Authentifizierung, Kommunikation | ✅ Ja | Eindeutige Identifikation, Password-Recovery |
| `password_hash` | Authentifizierung | ✅ Ja | Sicherheit |
| `role` | Autorisierung (RBAC) | ✅ Ja | Berechtigungskonzept |
| `must_change_password` | Security-Policy | ✅ Ja | Erstlogin-Sicherheit |
| `last_login` | Security-Monitoring | ✅ Ja | Erkennung anomaler Anmeldungen |
| `created_at` | Audit-Trail | ✅ Ja | Nachvollziehbarkeit |
| `updated_at` | Audit-Trail | ✅ Ja | Nachvollziehbarkeit |
| `processing_restricted` | DSGVO Art. 18 (Einschränkung) | ✅ Ja | Betroffenenrechte |
| `objection_filed` | DSGVO Art. 21 (Widerspruch) | ✅ Ja | Betroffenenrechte |
| `objection_date` | DSGVO Art. 21 (Widerspruch) | ✅ Ja | Fristenwachung |
| `employee_id` | Verknüpfung Employee ↔ User | ⚠️ Optional | Nur für Mitarbeiter mit Login-Zugang |

**Ergebnis User-Tabelle:** Alle Felder sind erforderlich und zweckgebunden. Keine redundante Datenspeicherung festgestellt.

---

### 2.2 Employee-Tabelle (`employees`)

| Feld | Zweck | Erforderlich | Bewertung |
|------|-------|--------------|-----------|
| `id` | Primärschlüssel | ✅ Ja | Technisch erforderlich |
| `user_id` | Verknüpfung Employee ↔ User | ⚠️ Optional | Nur für Mitarbeiter mit Login-Zugang |
| `first_name` | Schichtplanung, Kommunikation | ✅ Ja | Identifikation, Dienstpläne |
| `last_name` | Schichtplanung, Kommunikation | ✅ Ja | Identifikation, Dienstpläne |
| `email` | Kommunikation, Benachrichtigungen | ⚠️ **Prüfung nötig** | Siehe Abschnitt 3.1 |
| `color` | UI-Visualisierung (Schichtplan) | ✅ Ja | Benutzerfreundlichkeit |
| `working_hours_json` | Schichtplanung, ArbZG-Compliance | ✅ Ja | Kernfunktionalität |
| `break_start` | ArbZG-Compliance | ✅ Ja | Gesetzliche Anforderungen |
| `break_end` | ArbZG-Compliance | ✅ Ja | Gesetzliche Anforderungen |
| `max_work_hours` | ArbZG-Compliance | ✅ Ja | §3 ArbZG (Höchstgrenze) |
| `created_at` | Audit-Trail | ✅ Ja | Nachvollziehbarkeit |
| `updated_at` | Audit-Trail | ✅ Ja | Nachvollziehbarkeit |
| `processing_restricted` | DSGVO Art. 18 (Einschränkung) | ✅ Ja | Betroffenenrechte |

**Ergebnis Employee-Tabelle:** Überwiegend erforderlich. Ein Feld benötigt Klärung (siehe unten).

---

## 3. Offene Fragen und Prüfbedarf

### 3.1 Employee-Email: Redundanz zur User-Email?

**Frage:** Ist die `email` in der Employee-Tabelle redundant zur `email` in der User-Tabelle?

**Analyse:**
- **Szenario A:** Mitarbeiter hat Login-Zugang → `user_id` ist gesetzt → User-Email vorhanden
- **Szenario B:** Mitarbeiter hat keinen Login-Zugang → `user_id` ist NULL → nur Employee-Email vorhanden
- **Szenario C:** Mitarbeiter hat Login, aber private Email für Benachrichtigungen → unterschiedliche Emails sinnvoll

**Empfehlung:**
- Employee-Email beibehalten, da sie in Szenario B und C erforderlich ist
- Dokumentation: Employee-Email dient ausschließlich der betrieblichen Kommunikation (Schichtänderungen, Benachrichtigungen)
- User-Email dient ausschließlich der Authentifizierung und Account-Wiederherstellung

**Maßnahme:** ✅ Keine Änderung erforderlich. Feld ist zweckgebunden und nicht redundant.

---

### 3.2 Last_Login: Zweckbindung für Security-Monitoring

**Frage:** Wird `last_login` für mehr als Security-Monitoring verwendet?

**Analyse:**
- Aktuelle Verwendung: Nur in `user_service.py` zur Aktualisierung nach erfolgreichem Login
- Keine Auswertung in Reports, Analytics oder Business-Logik
- Kein Export in Drittsysteme

**Empfehlung:**
- Zweckbindung ist gewährleistet: Ausschließlich Security-Monitoring
- Regelmäßige Prüfung (jährlich), ob neue Verwendungszwecke hinzukommen
- Bei neuer Verwendung: Prüfung auf Vereinbarkeit mit ursprünglichem Zweck (Art. 6 Abs. 4 DSGVO)

**Maßnahme:** ✅ Keine Änderung erforderlich. Zweckbindung ist dokumentiert und eingehalten.

---

### 3.3 Request-Logging: IP-Adressen und personenbezogene Daten

**Frage:** Werden im Request-Logging personenbezogene Daten (insbesondere IP-Adressen) gespeichert?

**Analyse der aktuellen Implementierung:**

```python
# PlanBar - Backend/src/app/middleware/request_logging.py
logger.info(
    "%s %s -> %s (%.3fs)",
    request.method,
    request.url.path,
    response.status_code,
    duration,
)
```

**Ergebnis:**
- ❌ **Keine IP-Adressen** werden geloggt
- ❌ **Keine User-IDs** werden geloggt
- ❌ **Keine Query-Parameter** werden geloggt (könnten personenbezogene Daten enthalten)
- ✅ Nur Methode, Pfad, Statuscode, Dauer

**Bewertung:**
- aktuelle Implementierung ist **bereits datenschutzfreundlich**
- keine personenbezogenen Daten im Request-Log
- keine Pseudonymisierung erforderlich, da keine personenbezogenen Daten erhoben werden

**Rechtsgrundlage:**
- Falls in Zukunft IP-Adressen geloggt werden sollen: Art. 6 Abs. 1 lit. f DSGVO (berechtigtes Interesse)
- Zweck: IT-Sicherheit, Erkennung von Missbrauch, Fehleranalyse
- Speicherdauer: Maximal 7 Tage (siehe Abschnitt 4)

**Maßnahme:** ✅ Keine Änderung erforderlich. Aktuelle Implementierung ist DSGVO-konform.

---

## 4. Aufbewahrungsfristen und Löschung

### 4.1 Request-Logs

**Aktueller Status:** Keine automatisierte Löschung implementiert

**Empfehlung:**
- Aufbewahrungsfrist: **7 Tage** (IT-Sicherheit, Fehleranalyse)
- Automatische Löschung nach Ablauf der Frist
- Rechtsgrundlage: Art. 6 Abs. 1 lit. f DSGVO (berechtigtes Interesse)

**Implementierung:**
```python
# Log-Rotation konfigurieren (Beispiel für Python logging)
from logging.handlers import TimedRotatingFileHandler

handler = TimedRotatingFileHandler(
    filename="request.log",
    when="midnight",
    interval=1,
    backupCount=7,  # 7 Tage aufbewahren
)
```

**Maßnahme:** ⚠️ **Umsetzung erforderlich** — Automatische Log-Rotation konfigurieren

---

### 4.2 Audit-Logs

**Aktueller Status:** Audit-Logs werden in `audit_logs`-Tabelle gespeichert (siehe Issue #48)

**Empfehlung:**
- Aufbewahrungsfrist: **3 Jahre** (gesetzliche Aufbewahrungspflichten, Nachweisbarkeit)
- Automatische Archivierung/Löschung nach Ablauf
- Rechtsgrundlage: Art. 6 Abs. 1 lit. c DSGVO (rechtliche Verpflichtung)

**Maßnahme:** ⚠️ **Umsetzung erforderlich** — Siehe Issue #48 (Aufbewahrungsfristen)

---

### 4.3 User- und Employee-Daten

**Aktueller Status:** Keine automatische Löschung implementiert

**Empfehlung:**
- Bei Löschung des User-Accounts: Pseudonymisierung der Employee-Daten (siehe Issue #40, bereits implementiert)
- Bei Kündigung: Daten für 6 Monate aufbewahren (Reklamationen, Rückfragen), dann pseudonymisieren
- Gesetzliche Aufbewahrungspflichten (z.B. Arbeitsrecht): 3 Jahre

**Maßnahme:** ✅ Bereits implementiert (Issue #40 — Recht auf Löschung)

---

## 5. Zusammenfassung der Maßnahmen

| Nr. | Maßnahme | Priorität | Status | Verantwortlich |
|-----|----------|-----------|--------|----------------|
| 1 | Employee-Email als nicht-redundant dokumentieren | 🟡 Mittel | ✅ Abgeschlossen | Datenschutzbeauftragter |
| 2 | Zweckbindung `last_login` dokumentieren | 🟡 Mittel | ✅ Abgeschlossen | Datenschutzbeauftragter |
| 3 | Request-Logging: Keine IP-Adressen (bereits konform) | 🟢 Hoch | ✅ Abgeschlossen | Entwicklung |
| 4 | Log-Rotation: 7-Tage-Aufbewahrung implementieren | 🟡 Mittel | ⚠️ Offen | Entwicklung |
| 5 | Audit-Log-Aufbewahrung: 3 Jahre (Issue #48) | 🟡 Mittel | ⚠️ Offen | Entwicklung |
| 6 | Jährliche Prüfung der Zweckbindung | 🟡 Mittel | ⚠️ Offen | Datenschutzbeauftragter |

---

## 6. Fazit

Die aktuelle Datenmodell-Implementierung von PlanBar ist **überwiegend DSGVO-konform** im Hinblick auf Datenminimierung und Zweckbindung:

✅ **Positiv:**
- Alle erhobenen Felder sind für den Zweck erforderlich
- Keine redundante Datenspeicherung
- Request-Logging enthält keine personenbezogenen Daten (keine IPs)
- Betroffenenrechte sind implementiert (Löschung, Einschränkung, Widerspruch)

⚠️ **Verbesserungsbedarf:**
- Log-Rotation für Request-Logs (7-Tage-Aufbewahrung)
- Audit-Log-Aufbewahrung (3 Jahre) — abhängig von Issue #48
- Jährliche Prüfung der Zweckbindung dokumentieren

---

## 7. Nächste Schritte

1. **Log-Rotation implementieren** (siehe Abschnitt 4.1)
   - Konfiguration des Python-Loggings mit `TimedRotatingFileHandler`
   - Backup-Count: 7 Tage
   - Testing: Verifizieren, dass alte Logs automatisch gelöscht werden

2. **Issue #48 abwarten** (Aufbewahrungsfristen und automatische Löschung)
   - Koordinierung mit Audit-Log-Implementierung
   - Einheitliche Löschstrategie für alle Log-Typen

3. **Dokumentation aktualisieren**
   - Diese Prüfung in das Verarbeitungsverzeichnis (Issue #43) einpflegen
   - Datenschutz-Folgenabschätzung (Issue #44) aktualisieren

4. **Jährliche Prüfung**
   - Termin im Kalender setzen
   - Verantwortlichen benennen
   - Prüfungsvorlage erstellen

---

## Anhang: DSGVO-Referenzen

- **Art. 5 Abs. 1 lit. b DSGVO** — Zweckbindung
- **Art. 5 Abs. 1 lit. c DSGVO** — Datenminimierung
- **Art. 6 Abs. 1 lit. f DSGVO** — Berechtigtes Interesse (IT-Sicherheit)
- **Art. 6 Abs. 4 DSGVO** — Vereinbarkeit bei neuer Zweckbestimmung
- **Art. 13 Abs. 2 DSGVO** — Informationspflicht bei Aufbewahrungsdauer

---

**Hinweis:** Dieses Dokument ersetzt keine Rechtsberatung. Für verbindliche Auskünfte sollte der Datenschutzbeauftragte konsultiert werden.
