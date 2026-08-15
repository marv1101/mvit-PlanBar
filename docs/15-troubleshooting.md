# Fehlerbehebung

Lösungen für häufige Probleme bei der Nutzung von PlanBar.

## Anmeldung

### „Ungültige Zugangsdaten"

| Ursache | Lösung |
|---------|--------|
| Falsche E-Mail-Adresse | Prüfen Sie die E-Mail-Adresse |
| Falsches Passwort | Groß-/Kleinbuchstaben beachten, Caps Lock prüfen |
| Account deaktiviert | Kontaktieren Sie Ihren Administrator |

### „Session abgelaufen"

| Ursache | Lösung |
|---------|--------|
| Zu lange inaktiv | Melden Sie sich erneut an |
| Token abgelaufen | Browser-Cache löschen und neu anmelden |

### Seite lädt nicht

1. **Browser-Cache leeren:**
   - Chrome: Strg+Shift+Entf → „Zwischengespeicherte Bilder und Dateien löschen"
   - Firefox: Strg+Shift+Entf → „Cache leeren"
   - Edge: Strg+Shift+Entf → „Zwischengespeicherte Bilder und Dateien löschen"

2. **Browser neu starten**

3. **Andere Website testen:**
   - Funktioniert andere Websites? → Internetverbindung prüfen
   - Nur PlanBar betroffen? → Server-Status prüfen

## Mitarbeiter

### Mitarbeiter erscheint nicht in der Liste

| Ursache | Lösung |
|---------|--------|
| Status „Inaktiv" | Status auf „Aktiv" setzen |
| Filter aktiv | Filter zurücksetzen |
| Falsche Rolle | Rolle prüfen und ändern |

### Mitarbeiter kann sich nicht anmelden

1. Prüfen Sie, ob der Account **aktiv** ist
2. Prüfen Sie die **E-Mail-Adresse**
3. **Passwort zurücksetzen** über Admin-Bereich

## Dienstplan

### TiTO-Optimierung fehlgeschlagen

**Fehler: „Keine Lösung gefunden"**

| Ursache | Lösung |
|---------|--------|
| Zu viele Einschränkungen | Mindestbesetzung reduzieren |
| Zu wenige Mitarbeiter | Mehr Mitarbeiter hinzufügen |
| ArbZG-Verstoß | Mitarbeiterwünsche prüfen |

**Fehler: „Mindestbesetzung nicht erfüllbar"**

1. Prüfen Sie die **Mindestbesetzung** pro Rolle
2. Prüfen Sie die **Anzahl verfügbarer Mitarbeiter**
3. Passen Sie die **Rollen** an

**Fehler: „ArbZG-Verstoß"**

1. Prüfen Sie die **Ruhezeiten** (11h nachts)
2. Prüfen Sie die **Schichtfolge** der Mitarbeiter
3. Passen Sie die **Wünsche** an

### Plan wird nicht angezeigt

1. **Status prüfen:** Ist der Plan „Abgeschlossen"?
2. **Zeitraum prüfen:** Liegt der Plan im richtigen Zeitraum?
3. **Browser-Cache leeren**
4. **Seite neu laden** (F5)

## Pinboard

### Eintrag wird nicht angezeigt

1. **Berechtigungen prüfen:** Sind Sie in der richtigen Zielgruppe?
2. **Kategorie prüfen:** Ist die Kategorie aktiv?
3. **Priorität prüfen:** Ist die Priorität „Niedrig"?

## Zeitkonto

### Arbeitszeiten werden nicht angezeigt

| Ursache | Lösung |
|---------|--------|
| Kein Dienstplan | Schicht muss im Dienstplan zugewiesen sein |
| Zeiträum falsch | Zeitraum im Zeitkonto anpassen |
| Status nicht „Erfasst" | Arbeitszeit manuell erfassen |

### Falsche Stunden angezeigt

1. **Schicht prüfen:** Ist die richtige Schicht zugewiesen?
2. **Pausen prüfen:** Wurden Pausen korrekt erfasst?
3. **Manuelle Erfassung:** Zeit manuell korrigieren

## Allgemeine Fehler

### 500 Internal Server Error

| Ursache | Lösung |
|---------|--------|
| Server-Problem | Administrator kontaktieren |
| Datenbankfehler | Server-Logs prüfen |
| API-Problem | Backend-Status prüfen |

### 403 Forbidden

| Ursache | Lösung |
|---------|--------|
| Keine Berechtigung | Administrator kontaktieren |
| Account deaktiviert | Administrator kontaktieren |
| Session abgelaufen | Neu anmelden |

### 404 Not Found

| Ursache | Lösung |
|---------|--------|
| Falsche URL | URL in Adresszeile prüfen |
| Seite entfernt | Administrator kontaktieren |

## Kontakt

Bei technischen Problemen, die Sie nicht selbst lösen können:

1. **Administrator:** Prüfen Sie den Systemstatus
2. **Support:** Kontaktieren Sie Ihren IT-Support
3. **Dokumentation:** Durchsuchen Sie diese Anleitung

> **Tipp:** Für eine schnellere Fehlerbehebung notieren Sie bitte:
> - Datum und Uhrzeit des Fehlers
> - Genaueren Fehlermeldungen (Screenshot)
> - Welche Schritte Sie ausgeführt haben
> - Welchen Browser Sie verwenden