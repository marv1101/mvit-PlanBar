# Zeitkonto und Arbeitszeiten

Das Zeitkonto zeigt Ihre persönlichen Arbeitszeiten und ermöglicht die Verwaltung Ihrer Arbeitsstunden.

## Zeitkonto öffnen

1. Navigieren Sie zu **„Zeitkonto"** in der Seitenleiste
2. Sie sehen Ihre Arbeitszeit-Übersicht

## Zeitkonto-Übersicht

### Gesamtübersicht

```
┌─────────────────────────────────────────────┐
│  ⏱️ Mein Zeitkonto – Dezember 2026          │
│                                             │
│  Soll-Stunden:     160,00 h                 │
│  Ist-Stunden:      148,50 h                 │
│  Differenz:        -11,50 h                 │
│  Plusstunden:      11,50 h                  │
│  Minusstunden:      0,00 h                  │
└─────────────────────────────────────────────┘
```

### Monatsübersicht

| Monat | Soll | Ist | Differenz |
|-------|------|-----|-----------|
| Oktober 2026 | 160,00 h | 165,50 h | +5,50 h |
| November 2026 | 160,00 h | 152,00 h | -8,00 h |
| Dezember 2026 | 160,00 h | 148,50 h | -11,50 h |

### Detailansicht

Für jeden Tag sehen Sie:

| Spalte | Beschreibung |
|--------|-------------|
| Datum | Tag |
| Schicht | Zugewiesene Schichtrolle |
| Soll | Soll-Stunden für diesen Tag |
| Ist | Tatsächlich geleistete Stunden |
| Status | ✅ Erfasst / ⏳ Ausstehend |

## Arbeitszeiten erfassen

### Automatisch (aus Dienstplan)

Wenn Sie einem Dienstplan zugewiesen sind, werden Ihre Arbeitszeiten automatisch erfasst:

1. Ihre Schicht wird aus dem Dienstplan übernommen
2. Die Soll-Stunden werden automatisch berechnet
3. Die Ist-Stunden werden aus der Schichtdauer abgeleitet

### Manuell erfassen

1. Öffnen Sie das Zeitkonto
2. Klicken Sie auf **„Zeit erfassen"**
3. Füllen Sie die Felder aus:

| Feld | Beschreibung |
|------|-------------|
| Datum | Tag der Arbeitszeit |
| Startzeit | Beginn der Arbeit |
| Endezeit | Ende der Arbeit |
| Pause | Pausendauer (in Minuten) |
| Beschreibung | Optional: Tätigkeit |

4. Klicken Sie auf **„Speichern"**

## Zeitkonto-Berechnung

### Formel

```
Ist-Stunden = (Endezeit - Startzeit) - Pause
Differenz = Ist-Stunden - Soll-Stunden
```

### Beispiel

```
Start:      08:00
Ende:       17:00
Pause:       1:00 h
─────────────────────
Ist:         8:00 h
Soll:        8:00 h
Differenz:   0:00 h
```

## Plus- und Minusstunden

| Situation | Bedeutung |
|-----------|-----------|
| **Plusstunden** | Sie haben mehr gearbeitet als vorgesehen |
| **Minusstunden** | Sie haben weniger gearbeitet als vorgesehen |

### Ausgleich

Plusstunden können durch Freizeitausgleich kompensiert werden:

1. Tragen Sie einen **Schichtwunsch** für Freizeitausgleich ein
2. Der Schichtleiter genehmigt den Wunsch
3. Die Stunden werden automatisch angepasst

> **Hinweis:** Plusstunden verfallen nicht automatisch. Klären Sie mit Ihrem Arbeitgeber, wie Plusstunden ausgeglichen werden.

## Export

Sie können Ihr Zeitkonto exportieren:

1. Klicken Sie auf **„Exportieren"**
2. Wählen Sie den **Zeitraum**
3. Wählen Sie das **Format** (CSV, PDF)
4. Die Datei wird automatisch heruntergeladen

> **Tipp:** Der Export eignet sich gut für die Lohnabrechnung oder persönliche Unterlagen.
