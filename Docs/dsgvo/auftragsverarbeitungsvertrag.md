# Auftragsverarbeitungsvertrag (AVV) gemäß Art. 28 DSGVO

> **PlanBar** — Stand: 04. Juli 2026  
> **Verantwortlicher:** mvit-PlanBar (Marvin Vitus)  
> **Datenschutzbeauftragter:** [Platzhalter — Name und Kontaktdaten eintragen]

---

## 1. Zweck und Geltungsbereich

Dieses Dokument dient der Nachweisführung gemäß **Art. 28 Abs. 1 DSGVO**, dass mit allen externen Auftragsverarbeitern, die personenbezogene Daten im Auftrag von PlanBar verarbeiten, wirksame Auftragsverarbeitungsverträge (AVV) geschlossen wurden.

---

## 2. Liste der Auftragsverarbeiter

| Nr. | Auftragsverarbeiter | Zweck der Verarbeitung | Kontakt | AVV-Status | Letzte Prüfung |
|-----|---------------------|------------------------|---------|------------|----------------|
| 1 | **Hosting-Provider** (noch zu definieren) | Hosting der Anwendung, Speicherung aller Daten | [Platzhalter] | ⬜ Ausstehend | — |
| 2 | **PostgreSQL-Datenbank** (als Managed Service, falls zutreffend) | Persistente Datenspeicherung | [Platzhalter] | ⬜ Ausstehend | — |
| 3 | **E-Mail-Service** (falls für Benachrichtigungen genutzt) | Versand von Benachrichtigungen | [Platzhalter] | ⬜ Ausstehend | — |
| 4 | **DNS-Provider** | DNS-Auflösung, ggf. Logging | [Platzhalter] | ⬜ Ausstehend | — |
| 5 | **CDN** (falls für Frontend-Assets genutzt) | Caching und Auslieferung statischer Assets | [Platzhalter] | ⬜ Ausstehend | — |

> **Hinweis:** Die konkreten Dienstleister müssen bei Bedarf eingetragen werden. Die obige Liste dient als Vorlage.

---

## 3. Pflichtangaben eines AVV (Art. 28 Abs. 3 DSGVO)

Jeder AVV muss mindestens folgende Regelungen enthalten:

### 3.1 Gegenstand und Dauer der Verarbeitung
- **Gegenstand:** Verarbeitung personenbezogener Daten gemäß den in Abschnitt 4 definierten Kategorien.
- **Dauer:** Für die Dauer des Vertragsverhältnisses.

### 3.2 Art und Zweck der Verarbeitung
- **Art:** Speicherung, Abruf, Übermittlung, Löschung.
- **Zweck:** Betrieb der PlanBar-Anwendung gemäß Vertrag.

### 3.3 Kategorien betroffener Personen und Daten
- **Betroffene Personen:** Mitarbeiter, Administratoren, Benutzer.
- **Datenkategorien:** Stammdaten (Name, E-Mail), Arbeitszeiten, Schichtpläne, Gesundheitsdaten (indirekt über Schichtwünsche), Authentifizierungsdaten.

### 3.4 Pflichten des Auftragsverarbeiters
- Verarbeitung nur nach Weisung des Verantwortlichen (Art. 28 Abs. 3 lit. a).
- Vertraulichkeitsverpflichtung der Mitarbeiter (Art. 28 Abs. 3 lit. b).
- Implementierung technischer und organisatorischer Maßnahmen (Art. 32) (Art. 28 Abs. 3 lit. c).
- Zustimmung zu Unterauftragsverarbeitern (Art. 28 Abs. 2, 4).
- Unterstützung bei Betroffenenrechten (Art. 28 Abs. 3 lit. e).
- Löschung oder Rückgabe aller Daten nach Vertragsende (Art. 28 Abs. 3 lit. g).
- Bereitstellung aller Informationen zur Überprüfung (Art. 28 Abs. 3 lit. h).

### 3.5 Weisungsbindung
Der Auftragsverarbeiter darf nur auf dokumentierte Weisung des Verantwortlichen verarbeiten (Art. 28 Abs. 3 lit. a). Weisungen müssen schriftlich erfolgen.

### 3.6 Unterauftragsverarbeiter
- **Zustimmungspflicht:** Der Auftragsverarbeiter darf nur mit vorheriger schriftlicher Zustimmung des Verantwortlichen Unterauftragsverarbeiter einsetzen (Art. 28 Abs. 2).
- **Informationspflicht:** Der Auftragsverarbeiter muss den Verantwortlichen über geplante Änderungen informieren (Art. 28 Abs. 2).
- **Haftung:** Der ursprüngliche Auftragsverarbeiter bleibt gegenüber dem Verantwortlichen verantwortlich (Art. 28 Abs. 4).

### 3.7 Technische und organisatorische Maßnahmen (Art. 32)
Der Auftragsverarbeiter muss angemessene technische und organisatorische Maßnahmen ergreifen, um ein dem Risiko angemessenes Schutzniveau zu gewährleisten, insbesondere:
- Pseudonymisierung und Verschlüsselung personenbezogener Daten.
- Vertraulichkeit, Integrität, Verfügbarkeit und Belastbarkeit der Systeme.
- Fähigkeit zur Wiederherstellung der Verfügbarkeit und des Zugangs zu Daten bei einem technischen Ausfall.
- Regelmäßige Überprüfung, Bewertung und Evaluierung der Wirksamkeit der Maßnahmen.

### 3.8 Betroffenenrechte
Der Auftragsverarbeiter muss dem Verantwortlichen bei der Erfüllung der Pflichten gemäß Art. 15–22 DSGVO assistieren (Art. 28 Abs. 3 lit. e). Dies umfasst:
- Auskunftserteilung.
- Berichtigung.
- Löschung.
- Einschränkung der Verarbeitung.
- Datenübertragbarkeit.
- Widerspruch.

### 3.9 Löschung und Rückgabe nach Vertragsende
Nach Ende des Vertragsverhältnisses muss der Auftragsverarbeiter:
- Alle personenbezogenen Daten löschen oder an den Verantwortlichen zurückgeben (Art. 28 Abs. 3 lit. g).
- Die Löschung nachweisen können.

### 3.10 Überprüfungsberechtigung
Der Verantwortliche hat das Recht, den Auftragsverarbeiter zu überprüfen oder Prüfungen durch Dritte durchführen zu lassen (Art. 28 Abs. 3 lit. h). Der Auftragsverarbeiter muss alle Informationen bereitstellen, die für die Überprüfung erforderlich sind.

---

## 4. Technische und organisatorische Maßnahmen des Auftragsverarbeiters

Der Auftragsverarbeiter muss folgende Mindestmaßnahmen nachweisen:

| Maßnahme | Beschreibung |
|----------|--------------|
| **Zugangskontrolle** | physische und logische Zugangskontrolle zu den Verarbeitungsanlagen |
| **Benutzerkontrolle** | Berechtigungskonzept mit Rollen und Berechtigungen |
| **Datenträgerkontrolle** | Schutz vor unbefugtem Zugriff auf Datenträger |
| **Speicherplatzkontrolle** | Trennung不同er Verarbeitungszwecke |
| **Pseudonymisierung** | Verfremdung personenbezogener Daten, soweit möglich |
| **Verschlüsselung** | Transport- und Speicherverschlüsselung |
| **Vertraulichkeit** | Verpflichtung der Mitarbeiter auf Datengeheimnis |
| **Integrität** | Schutz vor unbefugter Datenänderung |
| **Verfügbarkeit** | Redundanz, Backup, Disaster Recovery |
| **Regelmäßige Überprüfung** | Evaluierung der Wirksamkeit der Maßnahmen |

---

## 5. Datenschutz-Folgenabschätzung (Art. 35 DSGVO)

Sofern der Auftragsverarbeiter Verarbeitungen durchführt, die eine Datenschutz-Folgenabschätzung erfordern, muss er den Verantwortlichen unterstützen (Art. 28 Abs. 3 lit. f).

---

## 6. Benachrichtigung bei Datenschutzverletzungen (Art. 33/34 DSGVO)

Der Auftragsverarbeiter muss den Verantwortlichen unverzüglich über Datenschutzverletzungen informieren (Art. 33 Abs. 2). Die Benachrichtigung muss mindestens enthalten:
- Art der Verletzung.
- Kategorien und ungefähre Zahl der betroffenen Personen.
- Name und Kontaktdaten des Datenschutzbeauftragten.
- Beschreibung der wahrscheinlichen Folgen.
- Beschreibung der ergriffenen oder vorgeschlagenen Maßnahmen.

---

## 7. Datenübermittlung in Drittländer (Art. 44–49 DSGVO)

Falls der Auftragsverarbeiter personenbezogene Daten in ein Drittland übermittelt, muss er sicherstellen, dass:
- Ein angemessenes Schutzniveau gewährleistet ist (Art. 45–46).
- Eine der Ausnahmeregelungen des Art. 49 DSGVO vorliegt.
- Der Verantwortliche über die Übermittlung informiert wird.

---

## 8. Verantwortlichkeiten

| Verantwortlichkeit | Verantwortlicher | Auftragsverarbeiter |
|---------------------|------------------|----------------------|
| Auswahl des Auftragsverarbeiters | ✅ | |
| AVV abschließen | ✅ | |
| Weisungen erteilen | ✅ | |
| Verarbeitung gemäß Weisung | | ✅ |
| Technische Maßnahmen implementieren | | ✅ |
| Überprüfung des Auftragsverarbeiters | ✅ | |
| Unterstützung bei Betroffenenrechten | | ✅ |
| Benachrichtigung bei Verletzungen | | ✅ |
| Löschung nach Vertragsende | | ✅ |

---

## 9. Dokumentation und Nachweise

Für jeden Auftragsverarbeiter sind folgende Dokumente zu führen:
- Geschlossener AVV (als Anlage).
- Nachweis der technischen und organisatorischen Maßnahmen.
- Protokolle der Überprüfungen.
- Nachweis der Schulung der Mitarbeiter.

---

## 10. Aktualisierung

Dieses Dokument muss mindestens jährlich und bei Änderungen der Verarbeitungstätigkeiten aktualisiert werden.

---

## Anlagen

- [ ] AVV mit Hosting-Provider
- [ ] AVV mit PostgreSQL-Dienstleister (falls Managed)
- [ ] AVV mit E-Mail-Service (falls genutzt)
- [ ] AVV mit DNS-Provider
- [ ] AVV mit CDN (falls genutzt)

---

*Erstellt von Orion im Rahmen der PlanBar-DSGVO-Umsetzung.*
