# Datenschutzverletzungen — Verfahren nach Art. 33/34 DSGVO

> **Status:** Entwurf  
> **Erstellt:** 2026-07-06  
> **Letzte Prüfung:** 2026-07-06  
> **Verantwortlich:** [Datenschutzbeauftragter / Geschäftsführung]  
> **Geltungsbereich:** PlanBar — Schichtplanungsplattform

---

## 1. Zweck und Rechtsgrundlage

Dieses Dokument beschreibt das Verfahren zur Meldung und Benachrichtigung bei Datenschutzverletzungen gemäß:

- **Art. 33 DSGVO** — Meldung von Verletzungen personenbezogener Daten an die Aufsichtsbehörde
- **Art. 34 DSGVO** — Benachrichtigung der betroffenen Personen

---

## 2. Definition: Was ist eine Datenschutzverletzung?

Gemäß Art. 4 Nr. 12 DSGVO ist eine Verletzung des Schutzes personenbezogener Daten:

> „eine Verletzung der Sicherheit, die zur Vernichtung, zum Verlust oder zur Veränderung oder zur unbefugten Offengabe von beziehungsweise zum unbefugten Zugang zu personenbezogenen Daten führt, die übermittelt, gespeichert oder auf sonstige Weise verarbeitet wurden."

### Kategorien von Verletzungen

| Kategorie | Beispiele |
|-----------|-----------|
| **Vertraulichkeit** | Unbefugter Zugriff auf Mitarbeiterdaten, Datenbank-Leak |
| **Verfügbarkeit** | Ransomware, Systemausfall mit Datenverlust |
| **Integrität** | Manipulation von Schichtdaten, unautorisierte Änderungen |

---

## 3. Erkennung und Meldung interner Vorfälle

### 3.1 Meldewege

| Quelle | Meldung an |
|--------|------------|
| System-Alerts (Monitoring) | IT-Administration |
| Mitarbeiter-Hinweise | IT-Administration oder Datenschutzbeauftragter |
| Externe Hinweise (Nutzer, Partner) | Datenschutzbeauftragter |
| Audit-Logs | IT-Administration |

### 3.2 Ersteinschätzung

Nach Kenntnisnahme eines Vorfalls erfolgt **unverzüglich** (spätestens innerhalb von 4 Stunden):

1. **Sicherung** des Vorfalls (Logs, Screenshots, Status)
2. **Ersteinschätzung**: Art, Umfang, betroffene Personen
3. **Einstufung** der Schwere (siehe Risikomatrix unten)
4. **Dokumentation** im Vorfall-Log

---

## 4. Meldung an die Aufsichtsbehörde (Art. 33 DSGVO)

### 4.1 Frist

Die Meldung muss **innerhalb von 72 Stunden** nach Bekanntwerden der Verletzung an die zuständige Aufsichtsbehörde erfolgen, es sei denn, die Verletzung führt voraussichtlich nicht zu einem Risiko für die Rechte und Freiheiten betroffener Personen.

### 4.2 Zuständige Aufsichtsbehörde

Für PlanBar: [Landesbeauftragter für Datenschutz und Informationsfreiheit]
- Adresse: [Einzutragen]
- E-Mail: [Einzutragen]
- Telefon: [Einzutragen]
- Online-Meldeportal: [URL eintragen]

### 4.3 Pflichtangaben (Art. 33 Abs. 3 DSGVO)

Die Meldung muss enthalten:

| Pflichtangabe | Beschreibung |
|---------------|-------------|
| Art der Verletzung | Kategorien und Anzahl betroffener Personen/Daten |
| Kontaktdaten des DSB | Name, Telefon, E-Mail des Datenschutzbeauftragten |
| Wahrscheinliche Folgen | Mögliche negative Auswirkungen für Betroffene |
| Geplante Maßnahmen | Ergriffene oder geplante Abhilfemaßnahmen |

### 4.4 Meldeschema

```
MELDUNG AN AUFSICHTSBEHÖRDE — Art. 33 DSGVO
===============================================

Verantwortlicher:        [Name Unternehmen]
                         [Adresse]
                         [Kontaktdaten]

Datenschutzbeauftragter: [Name]
                         [E-Mail]
                         [Telefon]

Datum der Verletzung:    [YYYY-MM-DD HH:MM]
Datum der Entdeckung:    [YYYY-MM-DD HH:MM]

Art der Verletzung:      [ ] Vertraulichkeit
                         [ ] Verfügbarkeit
                         [ ] Integrität
                         [ ] Sonstiges: ___

Betroffene Datenkategorien:
                         [ ] Name, Adresse
                         [ ] E-Mail, Telefon
                         [ ] Gesundheitsdaten (indirekt)
                         [ ] Arbeitszeiten, Schichtdaten
                         [ ] Kontodaten
                         [ ] Zugangsdaten (Passwörter)
                         [ ] Sonstiges: ___

Anzahl betroffener Personen: ca. [N]

Kurzbeschreibung:        [Was ist geschehen?]

Wahrscheinliche Folgen:  [Risikoabschätzung]

Ergriffene Maßnahmen:    [Technische und organisatorische Maßnahmen]

Nachmeldung:             [ ] Ja, wenn weitere Informationen vorliegen
```

---

## 5. Benachrichtigung der Betroffenen (Art. 34 DSGVO)

### 5.1 Wann ist eine Benachrichtigung erforderlich?

Eine Benachrichtigung ist erforderlich, wenn die Verletzung ein **hohes Risiko** für die Rechte und Freiheiten betroffener Personen zur Folge hat.

### 5.2 Risikobewertung

| Risikostufe | Kriterien | Benachrichtigung |
|-------------|-----------|-----------------|
| **Kein Risiko** | Daten waren verschlüsselt, keine personenbezogenen Daten | Keine Meldung |
| **Normales Risiko** | Zugriff auf Namen/E-Mails, keine sensiblen Daten | Meldung nur wenn notwendig |
| **Hohes Risiko** | Gesundheitsdaten, Passwörter, Kontodaten betroffen | **Benachrichtigung erforderlich** |
| **Sehr hohes Risiko** | Massenleck, Identitätsdiebstahl möglich, Gesundheitsdaten | **Sofortige Benachrichtigung** |

### 5.3 Ausnahmen von der Benachrichtigungspflicht (Art. 34 Abs. 3)

Eine Benachrichtigung kann unterbleiben, wenn:

1. **Technische Schutzmaßnahmen**: Die Daten waren verschlüsselt oder anderweitig geschützt
2. **Sofortmaßnahmen**: Es wurde sichergestellt, dass das hohe Risiko nicht mehr besteht
3. **Unverhältnismäßiger Aufwand**: Öffentliche Bekanntmachung ist effektiver (z.B. bei sehr vielen Betroffenen)

### 5.4 Benachrichtigungsschreiben

```
BENACHRICHTIGUNG ÜBER DATENSCHUTZVERLETZUNG
============================================

Sehr geehrte/r [Name],

wir müssen Sie darüber informieren, dass es bei unserem System PlanBar 
am [Datum] zu einer Datenschutzverletzung gekommen ist.

WAS IST GESCHEHEN?
[Beschreibung des Vorfalls in verständlicher Sprache]

WELCHE DATEN SIND BETROFFEN?
[Liste der betroffenen Datenkategorien]

WELCHE FOLGEN KÖNNEN SICH ERGEBEN?
[Mögliche Risiken für die betroffene Person]

WAS HABEN WIR UNTERNOMMEN?
[Ergriffene Maßnahmen zur Eindämmung und Abhilfe]

WAS KÖNNEN SIE TUN?
[Empfehlungen zum Selbstschutz, z.B. Passwort ändern]

KONTAKT
Bei Fragen wenden Sie sich an:
[Name Datenschutzbeauftragter]
[E-Mail]
[Telefon]

Wir entschuldigen uns für die Unannehmlichkeiten.

Mit freundlichen Grüßen,
[Name Verantwortlicher]
```

---

## 6. Dokumentation (Art. 33 Abs. 5 DSGVO)

Jede Datenschutzverletzung ist zu dokumentieren — unabhängig davon, ob sie gemeldet wird.

### 6.1 Vorfall-Log Template

| Feld | Wert |
|------|------|
| **Vorfall-ID** | [eindeutige ID] |
| **Datum der Verletzung** | [YYYY-MM-DD] |
| **Datum der Entdeckung** | [YYYY-MM-DD] |
| **Entdeckt durch** | [Name/System] |
| **Art der Verletzung** | Vertraulichkeit / Verfügbarkeit / Integrität |
| **Betroffene Systeme** | [Liste] |
| **Betroffene Datenkategorien** | [Liste] |
| **Anzahl betroffener Personen** | [N] |
| **Schweregrad** | Gering / Mittel / Hoch |
| **Meldung an Behörde** | Ja/Nein, wenn Nein: Begründung |
| **Datum der Meldung** | [YYYY-MM-DD HH:MM] |
| **Benachrichtigung Betroffene** | Ja/Nein, wenn Nein: Begründung |
| **Ergriffene Maßnahmen** | [Beschreibung] |
| **Nachbereitung** | [Lessons Learned] |

### 6.2 Aufbewahrung

Vorfall-Dokumentationen werden **mindestens 3 Jahre** aufbewahrt (Nachweispflicht).

---

## 7. Prozesse und Verantwortlichkeiten

### 7.1 Rollen

| Rolle | Verantwortlichkeit |
|-------|-------------------|
| **Verantwortlicher** (Geschäftsführung) | Gesamtverantwortung, Entscheidung über Meldung |
| **Datenschutzbeauftragter** | Koordination, Meldung an Behörde, Benachrichtigung Betroffener |
| **IT-Administration** | Technische Analyse, Eindämmung, Wiederherstellung |
| **Alle Mitarbeiter** | Meldung von Verdachtsfällen |

### 7.2 Prozessablauf

```
┌─────────────────────────────────────────────────────────────────┐
│                    VORFALL ERKANNT                               │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  SCHRITT 1: Ersteinschätzung (innerhalb 4 Stunden)              │
│  - Art, Umfang, betroffene Daten/Personen                       │
│  - Erste Sicherung von Beweisen                                 │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  SCHRITT 2: Eindämmung (sofort)                                 │
│  - Technische Maßnahmen (Sperren, Patches)                      │
│  - Organisatorische Maßnahmen (Information, Sperren)            │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  SCHRITT 3: Risikobewertung (innerhalb 24 Stunden)              │
│  - Risikomatrix anwenden                                        │
│  - Entscheidung: Meldung an Behörde? Benachrichtigung?          │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                              ▼
                    ┌─────────┴─────────┐
                    │                   │
           ┌────────▼────────┐  ┌──────▼──────┐
           │ Meldung an      │  │ Keine       │
           │ Behörde         │  │ Meldung     │
           │ (innerhalb 72h) │  │ (Begründung │
           │                 │  │  dokument.) │
           └────────┬────────┘  └─────────────┘
                    │
                    ▼
           ┌────────────────┐
           │ Benachrichtigung│
           │ Betroffene      │
           │ (unverzüglich)  │
           └────────┬────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────────┐
│  SCHRITT 4: Dokumentation & Nachbereitung                       │
│  - Vorfall-Log vervollständigen                                 │
│  - Lessons Learned                                              │
│  - Maßnahmen zur Vermeidung ähnlicher Vorfälle                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 8. PlanBar-spezifische Szenarien

### 8.1 Szenario: Datenbank-Leak

| Aspekt | Details |
|--------|---------|
| **Auslöser** | Unbefugter Zugriff auf PostgreSQL-Datenbank |
| **Betroffene Daten** | Mitarbeiterstammdaten, Schichtdaten, evtl. Gesundheitsdaten (indirekt) |
| **Schweregrad** | Hoch (Gesundheitsdaten) |
| **Maßnahmen** | 1. Datenbank-Zugang sperren 2. Passwort-Reset erzwingen 3. Meldung an Behörde 4. Benachrichtigung Betroffener |

### 8.2 Szenario: Ransomware

| Aspekt | Details |
|--------|---------|
| **Auslöser** | Verschlüsselung der Server durch Malware |
| **Betroffene Daten** | Alle Daten (Verfügbarkeit) |
| **Schweregrad** | Hoch (Betriebsunterbrechung) |
| **Maßnahmen** | 1. Isolation der Systeme 2. Backup-Wiederherstellung 3. Forensische Analyse 4. Meldung an Behörde |

### 8.3 Szenario: Phishing / Credential-Leak

| Aspekt | Details |
|--------|---------|
| **Auslöser** | Admin-Credentials durch Phishing kompromittiert |
| **Betroffene Daten** | Alle Daten (voller Admin-Zugang) |
| **Schweregrad** | Hoch |
| **Maßnahmen** | 1. Sofortige Passwort-Änderung 2. 2FA erzwingen 3. Audit-Log-Analyse 4. Meldung |

### 8.4 Szenario: TiTO-Fehlentscheidung

| Aspekt | Details |
|--------|---------|
| **Auslöser** | TiTO-Algorithmus weist Schicht falsch zu (z.B. Schwangere nachts) |
| **Betroffene Daten** | Gesundheitsdaten (indirekt), Arbeitszeitdaten |
| **Schweregrad** | Mittel (abhängig von Folgen) |
| **Maßnahmen** | 1. Schicht korrigieren 2. Algorithmus-Parameter prüfen 3. Dokumentation |

---

## 9. Notfallkontakte

| Kontakt | Name | Telefon | E-Mail |
|---------|------|---------|--------|
| **Datenschutzbeauftragter** | [Einzutragen] | [Einzutragen] | [Einzutragen] |
| **IT-Administration** | [Einzutragen] | [Einzutragen] | [Einzutragen] |
| **Geschäftsführung** | [Einzutragen] | [Einzutragen] | [Einzutragen] |
| **Aufsichtsbehörde** | [Einzutragen] | [Einzutragen] | [Einzutragen] |
| **Rechtsberatung** | [Einzutragen] | [Einzutragen] | [Einzutragen] |

---

## 10. Checkliste für den Ernstfall

### Sofortmaßnahmen (erste 4 Stunden)

- [ ] Vorfall dokumentieren (Datum, Zeit, Entdecker)
- [ ] Beweise sichern (Logs, Screenshots)
- [ ] Betroffene Systeme isolieren/sperren
- [ ] IT-Administration und Datenschutzbeauftragten informieren
- [ ] Ersteinschätzung: Art, Umfang, betroffene Daten

### Kurzfristig (innerhalb 24 Stunden)

- [ ] Vollständige technische Analyse
- [ ] Risikobewertung durchführen
- [ ] Entscheidung: Meldung an Behörde? (72h-Frist!)
- [ ] Entscheidung: Benachrichtigung Betroffener?
- [ ] containment-Maßnahmen implementieren

### Mittelfristig (innerhalb 72 Stunden)

- [ ] Meldung an Aufsichtsbehörde (wenn erforderlich)
- [ ] Benachrichtigung der Betroffenen (wenn erforderlich)
- [ ] Vorfall-Log vervollständigen

### Nachbereitung

- [ ] Lessons Learned dokumentieren
- [ ] Maßnahmen zur Vermeidung planen
- [ ] Verfahren/Prozesse anpassen
- [ ] Schulung der Mitarbeiter (falls relevant)
- [ ] Vorfall-Log archivieren

---

## 11. Rechtsgrundlagen

| Artikel | Inhalt |
|---------|--------|
| **Art. 33 DSGVO** | Meldepflicht bei Verletzungen an die Aufsichtsbehörde |
| **Art. 34 DSGVO** | Benachrichtigungspflicht gegenüber Betroffenen |
| **Art. 4 Nr. 12 DSGVO** | Definition: Verletzung des Schutzes personenbezogener Daten |
| **Art. 82 DSGVO** | Schadensersatzansprüche bei Verstößen |
| **Art. 83 DSGVO** | Bußgelder (bis zu 10 Mio. € oder 2% des Jahresumsatzes) |
| **§ 42 BDSG** | Strafvorschriften (zusätzlich zu DSGVO) |

---

## 12. Anhänge und Vorlagen

- [ ] Vorlage: Meldung an Aufsichtsbehörde
- [ ] Vorlage: Benachrichtigung Betroffene
- [ ] Vorlage: Vorfall-Log
- [ ] Kontaktliste Notfall
- [ ] Risikomatrix (detailliert)

---

## 13. Revisionshistorie

| Datum | Version | Änderung | Autor |
|-------|---------|----------|-------|
| 2026-07-06 | 1.0 | Erstfassung | Orion (Hermes Agent) |

---

## 14. Nächste Schritte

1. **Konkrete Kontaktdaten eintragen** (DSB, Aufsichtsbehörde, IT-Admin)
2. **Vorlagen erstellen** (Meldung, Benachrichtigung, Vorfall-Log)
3. **Schulung der Mitarbeiter** (Meldewege, Erkennung)
4. **Test-Alarm** durchführen (mindestens jährlich)
5. **Verfahren regelmäßig prüfen** (mindestens jährlich oder bei wesentlichen Änderungen)

---

*Dieses Dokument ist Teil des DSGVO-Compliance-Pakets für PlanBar.*
