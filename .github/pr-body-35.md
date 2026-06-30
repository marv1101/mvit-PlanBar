## Beschreibung

Issue #35 — Phase 1 der Single Sign-On Integration: LDAP/AD-Bindung für PlanBar.

### Implementierte Features

1. **LDAP-Bindung für Login**
   - Authentifizierung via LDAP-Bind (OpenLDAP, Samba AD, Active Directory)
   - Automatischer Fallback auf lokales Passwort bei LDAP-Ausfall
   - User wird bei erstmaligem LDAP-Login automatisch in der lokalen DB angelegt

2. **Automatische Synchronisation (OU-Import)**
   - `POST /api/v1/ldap/sync` — Importiert/updatet alle User aus der konfigurierten LDAP-OU
   - Überspringt Einträge ohne Mail-Attribut
   - Audit-Logging für jede Synchronisation

3. **Gruppenbasierte Rollenzuordnung**
   - `LDAP_ROLE_MAPPING`-Config (JSON) bildet LDAP-Gruppen auf PlanBar-Rollen ab
   - Beispiel: `{"admins": "admin", "employees": "user"}`
   - Rollen-Update bei Login und Sync, wenn sich die LDAP-Gruppe geändert hat

4. **Admin-Endpoints**
   - `POST /api/v1/ldap/test` — LDAP-Verbindung testen (admin only)
   - `POST /api/v1/ldap/sync` — Manuelle Synchronisation (admin only)
   - `GET /api/v1/ldap/status` — Konfiguration und letzte Sync-Zeit (admin only)

5. **Sicherheit**
   - TLS-Unterstützung via `LDAP_USE_TLS`
   - Keine hardcodierten Credentials (alle Werte via .env/Config)
   - Audit-Logging: LDAP_CREATED, LDAP_ROLE_UPDATED, LOGIN_LDAP, LDAP_SYNC

### Neue Konfiguration (.env)

```env
LDAP_ENABLED=false
LDAP_SERVER=ldap://localhost:389
LDAP_BIND_DN=cn=admin,dc=example,dc=com
LDAP_BIND_PASSWORD=your-secret
LDAP_USER_SEARCH_BASE=ou=users,dc=example,dc=com
LDAP_USER_SEARCH_FILTER=(objectClass=person)
LDAP_GROUP_SEARCH_BASE=ou=groups,dc=example,dc=com
LDAP_GROUP_SEARCH_FILTER=(objectClass=groupOfNames)
LDAP_GROUP_MEMBER_ATTR=member
LDAP_ROLE_MAPPING={"admins": "admin"}
LDAP_USE_TLS=false
```

### Neue Dateien

- `src/app/api/v1/ldap.py` — Admin-Endpoints für LDAP
- `src/app/services/ldap_service.py` — LDAP-Provider (Authenticate, Sync, Test)
- `src/app/schemas/ldap.py` — Pydantic-Schemata für LDAP-Endpoints
- `tests/unit/test_ldap_service.py` — 14 Unit-Tests (mock ldap3)
- `tests/integration/test_ldap_endpoints.py` — 15 Integration-Tests

### Geänderte Dateien

- `src/app/config.py` — LDAP-Konfigurationsfelder
- `src/app/services/user_service.py` — authenticate_user prüft LDAP zuerst
- `src/app/api/v1/router.py` — LDAP-Router registriert
- `requirements.txt` / `pyproject.toml` — ldap3-Abhängigkeit

### Testing

```bash
# Unit-Tests
pytest tests/unit/test_ldap_service.py -v

# Integration-Tests
pytest tests/integration/test_ldap_endpoints.py -v

# Alle Tests
pytest
```

### Nächste Schritte (zukünftige Phasen)

- Phase 2: SAML/OIDC (Single Sign-On via Identity Provider)
- Phase 3: Just-In-Time Provisioning & SCIM
