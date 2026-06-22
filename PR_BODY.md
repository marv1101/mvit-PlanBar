## Beschreibung

Implementiert Issue #38: DSGVO Datenschutzerklärung (Art. 13/14 DSGVO) für MVIT PlanBar.

### Frontend
- Neue Seite `/privacy` mit vollständiger DSGVO-konformer Datenschutzerklärung
- Route ist öffentlich zugänglich (kein ProtectedRoute)
- Footer-Link "Datenschutzerklärung" im Layout
- Verwendet bestehende UI-Komponenten (Card, Separator) und Lucide Icons
- Testabdeckung mit 8 Tests (vitest)

### Backend
- Neuer Endpoint `GET /api/v1/privacy` gibt DSGVO-Inhalt als JSON zurück
- Keine Authentifizierung erforderlich
- Rückgabe von: Verantwortlicher, Datenkategorien, Zwecke, Rechtsgrundlagen, Speicherdauer, Betroffenenrechte, Beschwerderecht, Drittlandhinweis, Kontakt

### Enthaltene DSGVO-Pflichtangaben
1. Verantwortlicher (Art. 4 Nr. 7 DSGVO)
2. Zweck der Datenverarbeitung pro Kategorie
3. Rechtsgrundlage (Art. 6 Abs. 1 lit. a-f DSGVO)
4. Speicherdauer
5. Betroffenenrechte (Art. 15-22 DSGVO)
6. Beschwerderecht bei Aufsichtsbehörde (Art. 77 DSGVO)
7. Datenübermittlung in Drittländer (Art. 44-49 DSGVO)
8. Kontakt für Datenschutzfragen

### Tests
- Frontend: 8 Tests in PrivacyPolicy.test.tsx
- Backend: 7 Tests in test_privacy.py

Closes #38
