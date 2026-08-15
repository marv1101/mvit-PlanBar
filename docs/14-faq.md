# FAQ – Häufig gestellte Fragen

## Allgemeines

### Was ist PlanBar?
PlanBar ist eine webbasierte Schichtplanungsanwendung für KMU in Deutschland. Sie ermöglicht die Erstellung, Verwaltung und automatische Optimierung von Dienstplänen unter Berücksichtigung des deutschen Arbeitszeitgesetzes (ArbZG).

### Für wen ist PlanBar geeignet?
PlanBar ist für Unternehmen geeignet, die Schichtbetrieb haben, z.B.:
- Pflegedienste
- Sicherheitsdienste
- Gastronomie
- Produktion
- Logistik

### Welche Browser werden unterstützt?
PlanBar funktioniert mit allen modernenrowsern:
- Google Chrome (ab Version 90)
- Mozilla Firefox (ab Version 88)
- Microsoft Edge (ab Version 90)
- Apple Safari (ab Version 14)

### Funktioniert PlanBar auf Mobilgeräten?
Ja, PlanBar ist responsiv und funktioniert auf Smartphones und Tablets.

## Anmeldung

### Ich habe mein Passwort vergessen
1. Klicken Sie auf **„Passwort vergessen?"** auf der Login-Seite
2. Geben Sie Ihre E-Mail-Adresse ein
3. Folgen Sie dem Link in der E-Mail

### Ich kann mich nicht anmelden
Prüfen Sie:
- Korrekte E-Mail-Adresse
- Korrektes Passwort ( Groß-/Kleinbuchstaben!)
- Caps Lock ist deaktiviert
- Internetverbindung besteht

### Wie lange bleibt meine Sitzung aktiv?
- **Access-Token:** 15 Minuten (verlängert sich automatisch bei Aktivität)
- **Refresh-Token:** 7 Tage

## Mitarbeiter

### Wie füge ich einen Mitarbeiter hinzu?
1. Navigieren Sie zu **„Mitarbeiter"**
2. Klicken Sie auf **„Mitarbeiter hinzufügen"**
3. Füllen Sie die Pflichtfelder aus
4. Speichern Sie die Änderung

### Kann ich einen Mitarbeiter deaktivieren statt löschen?
Ja! Setzen Sie den Status auf **„Inaktiv"** statt zu löschen. So bleiben die Daten erhalten.

### Wie ändere ich die Farbe eines Mitarbeiters?
1. Öffnen Sie die Mitarbeiterdetails
2. Klicken Sie auf das Farbfeld
3. Wählen Sie eine neue Farbe
4. Speichern Sie die Änderung

## Rollen

### Was ist eine Rolle?
Eine Rolle definiert einen Schichttyp (z.B. Frühschicht, Spätschicht, Nachtschicht). Jede Rolle hat eine Startzeit, Endzeit und Farbe.

### Wie viele Rollen kann ich erstellen?
Es gibt keine Begrenzung. Erstellen Sie so viele Rollen wie nötig.

## Dienstpläne

### Was ist der Unterschied zwischen manuell und TiTO?
- **Manuell:** Sie weisen Schichten per Drag-and-Drop zu
- **TiTO:** Der Optimierer erstellt automatisch einen optimalen Plan

### Was passiert, wenn TiTO fehlschlägt?
1. Prüfen Sie die Fehlermeldung
2. Stellen Sie sicher, dass genügend Mitarbeiter vorhanden sind
3. Prüfen Sie die Mindestbesetzung
4. Passen Sie die Einstellungen an
5. Übermitteln Sie den Plan erneut

### Kann ich einen optimierten Plan manuell bearbeiten?
Ja! Nach der TiTO-Optimierung können Sie Schichten manuell anpassen.

## Schichtwünsche

### Welche Arten von Wünschen gibt es?
- **Urlaub:** Zeitraum komplett nicht verfügbar
- **Bevorzugt:** Bevorzugte Schichten oder Zeiten
- **Nicht verfügbar:** Bestimmte Tage/Zeiten nicht möglich

### Wer genehmigt meine Wünsche?
Der Schichtleiter oder Administrator genehmigt oder lehnt Wünsche ab.

### Wann werden genehmigte Wünsche berücksichtigt?
Genehmigte Wwünsche werden vom TiTO-Optimierer bei der nächsten Schichtplanung automatisch berücksichtigt.

## Pinboard

### Was ist das Pinboard?
Das Pinboard ist eine interne Kommunikationsplattform für Ankündigungen und Notizen.

### Wer kann Einträge erstellen?
Alle Benutzer können Einträge erstellen (sofern keine Einschränkungen definiert sind).

## Zeitkonto

### Wie werden meine Arbeitszeiten erfasst?
Arbeitszeiten werden automatisch aus dem Dienstplan übernommen. Sie können zusätzlich manuell Zeiten erfassen.

### Was sind Plus- und Minusstunden?
- **Plusstunden:** Sie haben mehr gearbeitet als vorgesehen
- **Minusstunden:** Sie haben weniger gearbeitet als vorgesehen

### Verfallen Plusstunden?
Plusstunden verfallen nicht automatisch. Klären Sie mit Ihrem Arbeitgeber, wie sie ausgeglichen werden.

## Technisches

### PlanBar funktioniert nicht – was soll ich tun?
1. Aktualisieren Sie die Seite (F5 oder Strg+R)
2. Löschen Sie den Browser-Cache
3. Prüfen Sie die Internetverbindung
4. Kontaktieren Sie Ihren Administrator

### Welche Daten werden gespeichert?
PlanBar speichert nur betriebsrelevante Daten:
- Benutzer- und Mitarbeiterdaten
- Dienstpläne und Schichtwünsche
- Pinboard-Einträge

Es werden keine persönlichen Daten ohne Betriebszweck gespeichert.

### Ist mein Passwort sicher?
PlanBar speichert Passwörter verschlüsselt (bcrypt). Ihr Passwort ist für niemanden im Klartext lesbar, auch nicht für Administratoren.
