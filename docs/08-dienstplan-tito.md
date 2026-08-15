# Dienstplan erstellen (TiTO-Automatik)

TiTO (Timetable Optimizer) ist der automatische Schichtplan-Optimierer. Er erstellt einen optimalen Dienstplan unter Berücksichtigung aller Rahmenbedingungen.

## So funktioniert TiTO

```
┌─────────────────────────────────────────────────────────┐
│                    TiTO-Optimierungsprozess              │
│                                                         │
│  1. Dienstplan erstellen (Name + Zeitraum)               │
│  2. Rollen definieren (Mindestbesetzung)                 │
│  3. Mitarbeiter und Wünsche erfassen                    │
│  4. Plan an TiTO übermitteln                             │
│  5. TiTO analysiert:                                    │
│     ├── ArbZG-Regeln (11h Ruhezeit, max. 10h Arbeit)    │
│     ├── Mitarbeiterwünsche (Urlaub, Bevorzugt)          │
│     ├── Mindestbesetzung pro Schicht                     │
│     └── Gleichmäßige Verteilung                          │
│  6. TiTO erstellt optimalen Plan                         │
│  7. Ergebnis wird im Frontend angezeigt                  │
└─────────────────────────────────────────────────────────┘
```

## Schritt-für-Schritt Anleitung

### 1. Dienstplan erstellen

1. Navigieren Sie zu **„Dienstplan"**
2. Klicken Sie auf **„Neuen Dienstplan erstellen"**
3. Füllen Sie die Grunddaten aus:
   - **Name:** z.B. „Dezember 2026"
   - **Zeitraum:** 01.12.2026 – 31.12.2026
   - **Beschreibung:** Optional

### 2. Rollen und Mindestbesetzung prüfen

Stellen Sie sicher, dass für jede Schichtrolle eine Mindestbesetzung definiert ist:

1. Navigieren Sie zu **„Rollen"**
2. Prüfen Sie die **Min. Mitarbeiter** für jede Rolle

### 3. Mitarbeiterwünsche erfassen

1. Navigieren Sie zu **„Schichtwünsche"**
2. Stellen Sie sicher, dass alle relevanten Wünsche eingetragen sind:
   - 🏖️ Urlaube
   - ⭐ Bevorzugte Schichten
   - 🚫 Nicht-verfügbare Zeiten

### 4. Plan an TiTO übermitteln

1. Öffnen Sie den Dienstplan
2. Klicken Sie auf **„An TiTO übermitteln"**
3. Bestätigen Sie die Übermittlung
4. Der Plan wechselt in den Status **„Eingereicht"**

### 5. Auf Ergebnis warten

- Der TiTO-Optimierer verarbeitet den Plan
- Dauer: Je nach Komplexität 1-30 Minuten
- Das Frontend aktualisiert sich automatisch (Polling)

### 6. Ergebnis prüfen

Nach Abschluss der Optimierung:

| Status | Was tun? |
|--------|----------|
| ✅ **Abgeschlossen** | Plan ist fertig – Schichten können eingesehen werden |
| ❌ **Fehlgeschlagen** | Optimierung fehlgeschlagen – siehe Fehlerbehebung |

## ArbZG-Regeln

TiTO beachtet automatisch die folgenden Regeln des deutschen Arbeitszeitgesetzes:

| Regel | Beschreibung |
|-------|-------------|
| **11h Ruhezeit** | Nachtschicht → Frühschicht: mind. 11 Stunden pause |
| **Max. 10h Arbeitstag** | Einzelne Schicht darf max. 10 Stunden dauern |
| **Sonntagsruhe** | Sonntag ist grundsätzlich arbeitsfrei (Ausnahmen möglich) |
| **Nachtruhe** | 22:00 – 06:00 Ruhezeit (Ausnahmen für Nachtschicht) |
| **Max. 48h/Woche** | Durchschnittlich max. 48 Stunden pro Woche |

> **Hinweis:** Bei Verstößen gegen das ArbZG meldet TiTO einen Fehler und der Plan kann nicht optimiert werden.

## TiTO-Fehlermeldungen

### Häufige Fehler

| Fehler | Ursache | Lösung |
|--------|---------|--------|
| „Keine Lösung gefunden" | Zu viele Einschränkungen | Mindestbesetzung reduzieren oder mehr Mitarbeiter hinzufügen |
| „ArbZG-Verstoß" | Ruhezeiten nicht eingehalten | Mitarbeiterwünsche prüfen |
| „Mindestbesetzung nicht erfüllbar" | Zu wenige Mitarbeiter | Mitarbeiter hinzufügen oder Rollen anpassen |

### Plan wiederholen

Wenn die Optimierung fehlgeschlagen ist:

1. Klicken Sie auf **„Plan wiederholen"**
2. Nehmen Sie Änderungen vor (z.B. Mitarbeiter hinzufügen)
3. Übermitteln Sie den Plan erneut

## Optimierung anpassen

### Prioritäten setzen

TiTO kann Prioritäten berücksichtigen:

1. **Bevorzugte Schichten** werden vorrangig berücksichtigt
2. **Urlaub** wird immer berücksichtigt
3. **Gleichmäßige Verteilung** über alle Mitarbeiter

### Manuelle Nachbearbeitung

Nach der automatischen Optimierung können Sie Schichten manuell anpassen:

1. Öffnen Sie den optimierten Plan
2. Ziehen Sie Mitarbeiter per Drag-and-Drop auf andere Schichten
3. Speichern Sie die Änderungen

> **Hinweis:** Manuelle Änderungen können zu ArbZG-Verstößen führen. Prüfen Sie die Konformität manuell.
