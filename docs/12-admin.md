# Admin-Bereich

Der Admin-Bereich steht nur Administratoren zur Verfügung und ermöglicht die Verwaltung des gesamten Systems.

## Zugang zum Admin-Bereich

1. Melden Sie sich als **Administrator** an
2. In der Seitenleiste erscheint der Bereich **„Admin"**

> **Hinweis:** Nur Benutzer mit der Rolle „Administrator" haben Zugang zum Admin-Bereich.

## Admin-Bereiche

### 1. Benutzerverwaltung

Verwalten Sie alle Benutzer des Systems.

→ Siehe [Benutzerverwaltung](13-benutzerverwaltung.md)

### 2. Rollenverwaltung

Definieren und verwalten Sie Schichtrollen.

→ Siehe [Rollen definieren](05-rollen.md)

### 3. Mitarbeiterverwaltung

Verwalten Sie alle Mitarbeiter.

→ Siehe [Mitarbeiter verwalten](04-mitarbeiter.md)

### 4. Dienstplanverwaltung

Erstellen und optimieren Sie Dienstpläne.

→ Siehe [Dienstplan erstellen](07-dienstplan-manuell.md) und [TiTO-Automatik](08-dienstplan-tito.md)

### 5. Schichtwünsche verwalten

Genehmigen oder lehnen Sie Schichtwünsche ab.

→ Siehe [Schichtwünsche einreichen](06-schichtwuensche.md)

## Systemeinstellungen

### Allgemeine Einstellungen

| Einstellung | Beschreibung |
|-------------|-------------|
| Firmenname | Name Ihres Unternehmens |
| Logo | Logo für die Anwendung |
| Standard-Sprache | Standardsprache für alle Benutzer |
| Kontakt-E-Mail | Kontakt-E-Mail für Support |

### Sicherheitseinstellungen

| Einstellung | Beschreibung |
|-------------|-------------|
| Passwort-Politik | Mindestlänge, Komplexität |
| Session-Timeout | Zeit bis automatischer Logout |
| Max. Login-Versuche | Anzahl erlaubter Fehlversuche |

## Audit-Log

Das Audit-Log zeichnet alle wichtigen Aktionen im System auf:

| Aktion | Beschreibung |
|--------|-------------|
| Login | An- und Abmeldungen |
| Erstellen | Neue Einträge (Mitarbeiter, Pläne) |
| Ändern | Änderungen an Einträgen |
| Löschen | Löschung von Einträgen |
| Genehmigen | Genehmigung von Wünschen |

### Audit-Log einsehen

1. Navigieren Sie zu **„Admin"** → **„Audit-Log"**
2. Filtern Sie nach:
   - **Zeitraum**
   - **Benutzer**
   - **Aktionstyp**
3. Sie sehen alle protokollierten Aktionen

## Backup & Recovery

### Backup erstellen

1. Navigieren Sie zu **„Admin"** → **„Backup"**
2. Klicken Sie auf **„Backup erstellen"**
3. Die Sicherung wird automatisch gestartet

### Backup wiederherstellen

1. Navigieren Sie zu **„Admin"** → **„Backup"**
2. Wählen Sie ein Backup aus
3. Klicken Sie auf **„Wiederherstellen"**
4. Bestätigen Sie die Wiederherstellung

> **Warnung:** Die Wiederherstellung überschreibt alle aktuellen Daten!

## Monitoring

### Systemstatus

1. Navigieren Sie zu **„Admin"** → **„Systemstatus"**
2. Sie sehen den aktuellen Status aller Komponenten:

| Komponente | Status |
|------------|--------|
| Backend | 🟢 Online |
| Frontend | 🟢 Online |
| TiTO | 🟢 Online |
| Datenbank | 🟢 Online |

### Logs einsehen

1. Navigieren Sie zu **„Admin"** → **„Logs"**
2. Wählen Sie die **Log-Quelle** aus:
   - Backend
   - TiTO
   - Datenbank
3. Filtern Sie nach **Schweregrad** (Info, Warnung, Fehler)
