from fastapi import APIRouter

router = APIRouter()


PRIVACY_POLICY = {
    "title": "Datenschutzerklärung",
    "regulatory_reference": "Art. 13 und 14 DSGVO",
    "last_updated": "2026-06",
    "controller": {
        "name": "MVIT PlanBar",
        "address": "Musterstraße 123, 12345 Musterstadt",
        "email": "datenschutz@planbar.example.com",
    },
    "data_categories": [
        {
            "category": "User-Accounts",
            "data": ["Username", "E-Mail", "Passwort-Hash", "Rolle", "Letzter Login", "Erstellungsdatum"],
            "purpose": "Authentifizierung, Autorisierung, Systemsicherheit",
            "legal_basis": "Art. 6 Abs. 1 lit. f DSGVO (Berechtigtes Interesse)",
            "retention": "Bis zur Löschung des Kontos; bei Inaktivität > 12 Monate Löschung vorbehalten",
        },
        {
            "category": "Mitarbeiterdaten",
            "data": [
                "Vor- und Nachname",
                "E-Mail",
                "Arbeitszeiten",
                "Vertragsdaten",
                "Zeitkonto",
            ],
            "purpose": "Dienstplanerstellung, Schichtwünsche, Arbeitszeiterfassung, Zeitkonto-Berechnung",
            "legal_basis": "Art. 6 Abs. 1 lit. b DSGVO (Vertragserfüllung), Art. 6 Abs. 1 lit. c DSGVO (Rechtliche Verpflichtung)",
            "retention": "Dauer des Beschäftigungsverhältnisses zzgl. gesetzlicher Aufbewahrungsfristen (3-10 Jahre)",
        },
        {
            "category": "Session-Cookies",
            "data": ["access_token (httponly)", "refresh_token (httponly)"],
            "purpose": "Sitzungsaufrechterhaltung, sichere Authentifizierung",
            "legal_basis": "Art. 6 Abs. 1 lit. f DSGVO (Berechtigtes Interesse)",
            "retention": "access_token: 15 Minuten, refresh_token: 7 Tage",
        },
    ],
    "data_subject_rights": {
        "access": "Art. 15 DSGVO - Auskunftsrecht",
        "rectification": "Art. 16 DSGVO - Recht auf Berichtigung",
        "erasure": "Art. 17 DSGVO - Recht auf Löschung",
        "restriction": "Art. 18 DSGVO - Recht auf Einschränkung der Verarbeitung",
        "data_portability": "Art. 20 DSGVO - Recht auf Datenübertragbarkeit",
        "objection": "Art. 21 DSGVO - Widerspruchsrecht",
    },
    "complaint_right": {
        "description": "Beschwerderecht bei der Aufsichtsbehörde gemäß Art. 77 DSGVO",
        "authority": "Der Landesdatenschutzbeauftragte, Postfach 12 34 56, 12345 Musterstadt",
        "email": "poststelle@datenschutz.example.com",
    },
    "third_country_transfer": "Eine Übermittlung in Drittländer findet nicht statt. Verarbeitung ausschließlich auf Servern innerhalb der EU.",
    "contact": {
        "role": "Datenschutzbeauftragter",
        "name": "MVIT PlanBar",
        "address": "Musterstraße 123, 12345 Musterstadt",
        "email": "datenschutz@planbar.example.com",
    },
}


@router.get("/privacy", tags=["privacy"])
def get_privacy_policy():
    return PRIVACY_POLICY
