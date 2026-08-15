# Rollen definieren

Rollen definieren die verschiedenen Schichttypen in Ihrem Unternehmen. Typische Rollen sind Frühschicht, Spätschicht und Nachtschicht.

## Rollenübersicht

Die Rollenliste zeigt alle definierten Schichtrollen:

| Spalte | Beschreibung |
|--------|-------------|
| Name | Bezeichnung der Rolle |
| Farbe | Farbliche Zuordnung im Kalender |
| Startzeit | Beginn der Schicht |
| Endezeit | Ende der Schicht |
| Dauer | Automatisch berechnet |
| Min. Mitarbeiter | Mindestbesetzung |

## Neue Rolle hinzufügen

1. Klicken Sie auf **„Rolle hinzufügen"**
2. Füllen Sie die Felder aus:

### Pflichtfelder

| Feld | Beschreibung | Beispiel |
|------|-------------|----------|
| Name | Bezeichnung | Frühschicht |
| Startzeit | Beginn der Schicht | 06:00 |
| Endezeit | Ende der Schicht | 14:00 |

### Optionale Felder

| Feld | Beschreibung |
|------|-------------|
| Farbe | Farbe im Kalender (Standard: Grau) |
| Min. Mitarbeiter | Mindestanzahl pro Schicht |
| Beschreibung | Zusätzliche Informationen |

3. Klicken Sie auf **„Speichern"**

## Beispiel-Rollen

### Standard Konfiguration

```
Frühschicht:   06:00 – 14:00 (8h)
Spätschicht:   14:00 – 22:00 (8h)
Nachtschicht:  22:00 – 06:00 (8h)
```

### Erweiterte Konfiguration

```
Frühschicht:      06:00 – 14:00 (8h)  – Min. 3 Mitarbeiter
Spätschicht:      14:00 – 22:00 (8h)  – Min. 3 Mitarbeiter
Nachtschicht:     22:00 – 06:00 (8h)  – Min. 2 Mitarbeiter
Wochenendfrüh:    08:00 – 16:00 (8h)  – Min. 2 Mitarbeiter
Wochenendspät:    16:00 – 00:00 (8h)  – Min. 2 Mitarbeiter
```

## Rolle bearbeiten

1. Klicken Sie auf die Rolle in der Liste
2. Ändern Sie die gewünschten Einstellungen
3. Klicken Sie auf **„Speichern"**

> **Hinweis:** Änderungen an Rollen wirken sich nicht auf bereits erstellte Dienstpläne aus.

## Rolle löschen

1. Klicken Sie auf das **Lösch-Symbol** (🗑️) neben der Rolle
2. Bestätigen Sie die Löschung

> **Warnung:** Rollen können nur gelöscht werden, wenn keine Mitarbeiter diese Rolle haben und keine Schichtwünsche dafür vorliegen.

## Mindestbesetzung

Die Mindestbesetzung ist die Anzahl der Mitarbeiter, die mindestens in jeder Schicht dieser Rolle arbeiten müssen. Dies wird vom TiTO-Optimierer bei der Automatischen Schichtplanung berücksichtigt.

### Einstellen

1. Öffnen Sie die Rollendetails
2. Setzen Sie **„Min. Mitarbeiter"** auf die gewünschte Zahl
3. Speichern Sie die Änderung

> **Tipp:** Für eine 24/7-Besetzung mit 3-Schicht-Modell setzen Sie die Mindestbesetzung auf mindestens 2-3 Mitarbeiter pro Schicht.
