# Plan: PlanBar Backend Implementierung – Phase 1

## TL;DR
Implementierung eines Python/FastAPI-Backends als REST API mit JWT-Auth, SQLAlchemy ORM, und Proxy zu TiTO. Das Backend fungiert als zentrale Schnittstelle für das Frontend, persistent speichert alle Daten in einer separaten PostgreSQL-DB und verwaltet TiTO-Jobs asynchron über einen Callback-Mechanismus. Modulare Struktur mit FastAPI Routers, umfassende Tests, und Docker-ready Deployment.

### Aktueller Umsetzungsstand
- [x] Phase 1A: Projekt Setup & Foundation
  - [x] `src/app/` Ordnerstruktur erstellt
  - [x] `pyproject.toml` & `requirements.txt` angelegt
  - [x] `src/app/config.py` mit `pydantic-settings` eingerichtet
  - [x] `.env.example` angelegt
- [x] Phase 1B: Database & ORM Basis
  - [x] `src/app/db/base.py` erstellt
  - [x] `src/app/db/database.py` erstellt
  - [x] `src/app/db/models/user.py` implementiert
- [x] Phase 1C: Auth & Schemas
  - [x] `src/app/core/auth.py` implementiert
  - [x] `src/app/schemas/user.py` implementiert
- [x] Phase 1D: API Layer
  - [x] `src/app/api/v1/router.py` eingerichtet
  - [x] `src/app/api/v1/users.py`: Register/Login/Me implementiert
  - [x] `src/app/api/v1/health.py` implementiert
- [x] Phase 1E: Business Logic Services
  - [x] `src/app/services/user_service.py` implementiert
- [x] Phase 1F: Middleware & Error Handling
  - [x] `src/app/middleware/error_handler.py` erstellt
  - [x] `src/app/core/logging.py` erstellt
- [x] Phase 1G: Testing
  - [x] `tests/conftest.py` vorhanden
  - [x] `tests/integration/test_health.py` vorhanden und bestanden
- [x] Phase 1H: Deployment & Dokumentation
  - [x] `Dockerfile` vorhanden
  - [x] `.dockerignore` vorhanden

> Offen: PostgreSQL-Compose-Setup, Alembic-Migrationen, weitere Domain-Modelle, vollständige CRUD-APIs, TiTO-Proxy/Callback, Auth-Middleware, Metrics-Endpunkte, umfassende Tests, ausführliche Dokumentation.

---

## Projekt-Architektur-Überblick

```
PlanBar - Backend/
├── src/
│   ├── app/
│   │   ├── __init__.py              # FastAPI app factory
│   │   ├── main.py                  # Entry point
│   │   ├── config.py                # Config (env, database, secrets)
│   │   ├── dependencies.py          # Dependency injection (DB session, current_user)
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   ├── auth.py              # JWT token generation/validation, password hashing
│   │   │   ├── exceptions.py        # Custom exceptions (validation, auth, not found)
│   │   │   ├── logging.py           # Logger configuration
│   │   │   └── enums.py             # Status, Role enums
│   │   ├── db/
│   │   │   ├── __init__.py
│   │   │   ├── database.py          # SQLAlchemy session factory
│   │   │   ├── base.py              # Base declarative model
│   │   │   └── models/
│   │   │       ├── __init__.py
│   │   │       ├── user.py          # User model
│   │   │       ├── employee.py      # Employee, Contract, Timecard
│   │   │       ├── shift_wish.py    # ShiftWish
│   │   │       ├── schedule.py      # Schedule, Shiftplan
│   │   │       └── role.py          # Role
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   ├── user.py              # Pydantic schemas (UserCreate, UserUpdate, UserResponse)
│   │   │   ├── employee.py          # Employee schemas
│   │   │   ├── schedule.py          # Schedule schemas
│   │   │   ├── common.py            # PaginationResponse, ErrorResponse
│   │   │   └── tito.py              # TiTO request/response schemas
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── v1/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── router.py        # Main router combining all endpoints
│   │   │   │   ├── users.py         # User CRUD endpoints
│   │   │   │   ├── employees.py     # Employee CRUD endpoints
│   │   │   │   ├── roles.py         # Role CRUD endpoints
│   │   │   │   ├── contracts.py     # Contract CRUD endpoints
│   │   │   │   ├── timecards.py     # Timecard CRUD endpoints
│   │   │   │   ├── requests.py      # ShiftWish CRUD endpoints
│   │   │   │   ├── schedules.py     # Schedule CRUD & TiTO proxy endpoints
│   │   │   │   ├── health.py        # Health check endpoints
│   │   │   │   └── metrics.py       # Metrics endpoints
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── user_service.py      # User business logic (create, update, delete)
│   │   │   ├── employee_service.py  # Employee business logic
│   │   │   ├── schedule_service.py  # Schedule & TiTO job management
│   │   │   ├── tito_proxy.py        # TiTO API client (POST /jobs, GET /jobs/{id}, etc.)
│   │   │   ├── tito_callback.py     # Webhook handler for TiTO callbacks
│   │   │   └── metrics_service.py   # Metrics aggregation & reporting
│   │   ├── middleware/
│   │   │   ├── __init__.py
│   │   │   ├── auth.py              # JWT verification middleware
│   │   │   ├── error_handler.py     # Global exception handler
│   │   │   └── request_logging.py   # Request/response logging
│   │   └── utils/
│   │       ├── __init__.py
│   │       ├── pagination.py        # Pagination helper
│   │       ├── validators.py        # Custom validators (email, etc.)
│   │       └── helpers.py           # Utility functions
│   └── migrations/                  # Alembic migrations
│       ├── env.py
│       ├── script.py.mako
│       └── versions/
├── tests/
│   ├── __init__.py
│   ├── conftest.py                  # Pytest fixtures (test DB, test client, auth)
│   ├── test_config.py               # Config
│   ├── unit/
│   │   ├── __init__.py
│   │   ├── test_auth.py             # Test JWT generation/validation
│   │   ├── test_validators.py       # Test custom validators
│   │   └── test_services/
│   │       ├── __init__.py
│   │       ├── test_user_service.py
│   │       ├── test_employee_service.py
│   │       └── test_schedule_service.py
│   ├── integration/
│   │   ├── __init__.py
│   │   ├── test_user_endpoints.py   # Test /api/v1/users/* endpoints
│   │   ├── test_employee_endpoints.py
│   │   ├── test_schedule_endpoints.py
│   │   ├── test_tito_proxy.py       # Test TiTO proxy behavior
│   │   └── test_auth_flow.py        # Test login, token refresh, auth middleware
│   └── e2e/
│       ├── __init__.py
│       └── test_schedule_creation.py # E2E: Create schedule -> TiTO job -> callback
├── requirements.txt                 # Dependencies
├── pyproject.toml                   # Project metadata
├── Dockerfile                       # Multi-stage Docker build
├── docker-compose.override.yaml     # Local dev overrides
├── .env.example                     # Environment template
├── .dockerignore
├── .gitignore
├── alembic.ini                      # Alembic config
├── pytest.ini                       # Pytest config
└── README.md                        # Project documentation
```

---

## Phase 1: Implementierungs-Steps (mit Abhängigkeiten & Parallelisierung)

### Phase 1A: Projekt Setup & Foundation (*parallel möglich*)

1. **Projekt-Struktur & Dependencies**
   - FastAPI, SQLAlchemy 2.x, Alembic, pydantic, python-dotenv, httpx (für TiTO API)
   - pytest, pytest-asyncio, pytest-cov, factory-boy, faker (testing)
   - Install: `pip install fastapi sqlalchemy alembic pydantic python-dotenv httpx pytest ...`
   - Erstelle `src/app/` Ordnerstruktur & `__init__.py` files
   - Setup `pyproject.toml` & `requirements.txt`
   - Dependency: *None* → **kann parallel starten**

2. **Datenbank-Setup (PostgreSQL)**
   - Separate DB-Instanz: `planbar_backend` (nicht `tito`)
   - User: `planbar` (separate von TiTO-User)
   - Add to `Infrastructure/compose.yaml`: neuer `db_backend` Service
   - Konfiguriere Environment-Variablen (DATABASE_URL, etc.)
   - Dependency: *None* → **kann parallel mit Step 1 starten**

3. **Konfiguration & Environment**
   - `src/app/config.py`: Settings Klasse (FastAPI Best Practice)
   - Environment vars: `DATABASE_URL`, `SECRET_KEY`, `JWT_ALGORITHM`, `TITO_API_URL`, `TITO_API_KEY`, etc.
   - `.env.example` & `.gitignore` Setup
   - Dependency: *None* → **parallel möglich**

### Phase 1B: Database & ORM Setup

4. **SQLAlchemy Models & Database Layer** (*depends on Step 2*)
   - `src/app/db/base.py`: Declarative base
   - `src/app/db/database.py`: Session factory, engine, async support
   - Models in `src/app/db/models/`:
     - `user.py`: User (userid, username, email, password_hash, role, created_at, last_login)
     - `employee.py`: Employee (employee_id, user_id, contract_id), Contract, Timecard
     - `shift_wish.py`: ShiftWish (wish_id, employee_id, date, type, note)
     - `schedule.py`: Schedule, Shiftplan (planid, schedule_id, employee_id, shift_id, date, times, TiTO metadata/metrics/diagnostics)
     - `role.py`: Role (role_id, name, permissions)
   - Include: relationships, indexes, constraints
   - Dependency: *Step 2* → **Phase 1A must complete**

5. **Alembic Migrations Setup** (*depends on Step 4*)
   - Init Alembic: `alembic init migrations`
   - Configure `alembic.ini` für DATABASE_URL
   - Create initial migration from models: `alembic revision --autogenerate -m "initial"`
   - Verify migration applies cleanly on fresh DB
   - Dependency: *Step 4* → **serial**

### Phase 1C: Authentication & Security

6. **Core Auth Module** (*depends on Step 4, can parallel with 7*)
   - `src/app/core/auth.py`:
     - JWT token generation (access_token, refresh_token)
     - JWT token validation & claims extraction
     - Password hashing (bcrypt via passlib)
     - User role/permission checks
   - JWT Config: algorithm (HS256), expiration times (15min access, 7d refresh)
   - Dependency: *Step 4* (User model) → **serial**

7. **Schemas: Pydantic Models** (*depends on Step 4, can parallel with 6*)
   - `src/app/schemas/`:
     - `user.py`: UserCreate, UserLogin, UserResponse, UserUpdate
     - `employee.py`: EmployeeCreate, EmployeeResponse
     - `schedule.py`: ScheduleCreate, ScheduleResponse
     - `common.py`: PaginationResponse, ErrorResponse
     - `tito.py`: TiTOJobRequest, TiTOJobResponse schemas
   - All with validation (Field(min_length=1), EmailStr, etc.)
   - Dependency: *Step 4* (models) → **parallel with Step 6**

### Phase 1D: API Layer – Endpoints & Routing

8. **Router Setup & Dependency Injection** (*depends on Step 6, 7*)
   - `src/app/dependencies.py`: get_db(), get_current_user() fastapi.Depends
   - `src/app/core/exceptions.py`: HTTPException subclasses (ValidationError, NotFoundError, etc.)
   - `src/app/middleware/error_handler.py`: Global exception handler middleware
   - `src/app/api/v1/router.py`: Combine all routers, include in FastAPI app
   - Dependency: *Step 6, 7* → **serial**

9. **CRUD Endpoints (Users, Employees, Roles, Contracts, Timecards)** (*depends on Step 8*)
   - `src/app/api/v1/users.py`:
     - POST /api/v1/users (register)
     - GET /api/v1/users (list, requires auth)
     - GET /api/v1/users/{id}
     - PUT /api/v1/users/{id}
     - DELETE /api/v1/users/{id}
     - POST /api/v1/users/login
     - POST /api/v1/users/refresh-token
   - `src/app/api/v1/employees.py`: POST, GET, PUT, DELETE (similar pattern)
   - `src/app/api/v1/roles.py`, `contracts.py`, `timecards.py` (same pattern)
   - Include request body validation, auth middleware, error handling
   - Dependency: *Step 8* → **all can parallel, no cross-dependency**

10. **ShiftWish (Requests) & Schedule Endpoints** (*depends on Step 9*)
    - `src/app/api/v1/requests.py`: POST, GET, PUT, DELETE ShiftWishes
    - `src/app/api/v1/schedules.py`: (detailed below)
    - Dependency: *Step 9* → **serial**

11. **Schedule & TiTO Proxy Endpoints** (*depends on Step 10*)
    - `src/app/api/v1/schedules.py`:
      - POST /api/v1/schedules (create schedule + submit TiTO job)
      - GET /api/v1/schedules (list all)
      - GET /api/v1/schedules/{id} (get with TiTO result)
      - PUT /api/v1/schedules/{id} (update)
      - DELETE /api/v1/schedules/{id}
      - POST /api/v1/schedules/{id}/retry (resubmit to TiTO)
      - GET /api/v1/schedules/{id}/weeks
      - PUT /api/v1/schedules/{id}/weeks
      - GET /api/v1/schedules/{id}/shifts
      - GET /api/v1/schedules/{id}/summary
    - Includes TiTO API calls (see Step 13)
    - Dependency: *Step 10* → **serial**

12. **Health & Metrics Endpoints** (*can parallel with Step 11*)
    - `src/app/api/v1/health.py`:
      - GET /api/v1/health (backend status)
      - GET /api/v1/health/tito (TiTO connectivity)
      - GET /api/v1/health/db (DB connectivity)
    - `src/app/api/v1/metrics.py`:
      - GET /api/v1/metrics (TiTO metrics proxy)
      - GET /api/v1/metrics/robustness
      - GET /api/v1/metrics/prometheus
    - Dependency: *Step 11* → **parallel**

### Phase 1E: Business Logic & TiTO Integration

13. **TiTO Proxy Service** (*depends on Step 4*)
    - `src/app/services/tito_proxy.py`:
      - HTTP client to TiTO API (POST /jobs, GET /jobs/{id}, POST /retry, etc.)
      - Transform PlanBar Schedule data → TiTO JobPayload
      - Handle TiTO responses, store in DB
      - Error handling (timeout, invalid response, TiTO down)
      - Implement exponential backoff for retries
    - Use `httpx` for async HTTP calls
    - Dependency: *Step 4* (models) → **can start in parallel with Phase 1D, but endpoint needs it**

14. **TiTO Callback Webhook Handler** (*depends on Step 13*)
    - `src/app/services/tito_callback.py`:
      - Endpoint for TiTO to POST results: POST /api/v1/callbacks/tito
      - Validates callback (signature, idempotency)
      - Updates Schedule/Shiftplan with TiTO result (assignments, metrics, diagnostics)
      - Triggers any post-processing (notifications, DLQ checks)
    - Alternative: Polling endpoint if TiTO doesn't support callbacks (see metrics.py)
    - Dependency: *Step 13* → **serial**

15. **Business Logic Services** (*depends on Steps 4, 6*)
    - `src/app/services/user_service.py`:
      - create_user, update_user, delete_user, get_user_by_email
      - Password hashing via auth module
    - `src/app/services/employee_service.py`:
      - CRUD + business rules (e.g., validate employee_id unique per tenant)
    - `src/app/services/schedule_service.py`:
      - create_schedule (calls tito_proxy.submit_job)
      - get_schedule_with_result (fetches TiTO result if ready)
      - retry_schedule (resubmit to TiTO)
    - `src/app/services/metrics_service.py`:
      - Aggregate TiTO metrics, compute additional stats
    - Dependency: *Step 4, 6* → **parallel with Step 13**

### Phase 1F: Middleware & Error Handling

16. **Authentication Middleware** (*depends on Step 6*)
    - `src/app/middleware/auth.py`:
      - JWT token extraction from Authorization header
      - Token validation (signature, expiration)
      - Attach user to request context
      - Return 401/403 for missing/invalid tokens
    - Exclude endpoints: /health, /login, /register, /openapi.json
    - Dependency: *Step 6* → **serial**

17. **Error Handling & Logging** (*depends on Step 8*)
    - `src/app/middleware/error_handler.py`:
      - Catch ValidationError, ValueError, custom exceptions
      - Return standardized error responses (status, message, detail)
    - `src/app/core/logging.py`:
      - Configure logging (structured logs, JSON format)
      - Log all requests/responses (except sensitive data)
    - Dependency: *Step 8* → **parallel**

### Phase 1G: Testing

18. **Test Infrastructure & Fixtures** (*depends on Step 4, 5*)
    - `tests/conftest.py`:
      - Pytest fixtures: test_db, test_client, test_user, auth_headers
      - In-memory SQLite or separate test PostgreSQL
      - Mock TiTO API calls
    - `tests/test_config.py`: Test configuration loading
    - Dependency: *Step 4, 5* → **serial**

19. **Unit Tests** (*depends on Step 18*)
    - `tests/unit/test_auth.py`: Test JWT generation, validation, password hashing
    - `tests/unit/test_validators.py`: Test email, date validators
    - `tests/unit/test_services/`: Test user_service, employee_service, schedule_service
    - Target: >80% code coverage for services
    - Dependency: *Step 18* → **parallel**

20. **Integration Tests** (*depends on Step 19, Steps 9-12*)
    - `tests/integration/test_user_endpoints.py`: Test POST /users, GET /users, etc.
    - `tests/integration/test_auth_flow.py`: Test login → token → refresh → unauthorized
    - `tests/integration/test_schedule_endpoints.py`: Test schedule CRUD + TiTO proxy calls
    - `tests/integration/test_tito_proxy.py`: Mock TiTO, verify request format
    - Include: invalid inputs, auth failures, DB errors
    - Dependency: *Step 19, Steps 9-12* → **parallel**

21. **E2E Tests** (*depends on Steps 20, 14*)
    - `tests/e2e/test_schedule_creation.py`:
      - Create employee + shift wishes
      - Submit schedule (triggers TiTO job)
      - Mock TiTO callback
      - Verify schedule updated with results
    - Dependency: *Step 20, 14* → **serial (last test phase)**

### Phase 1H: Deployment & Documentation

22. **Docker Setup** (*depends on Step 5*)
    - `Dockerfile`:
      - Multi-stage: build (pip install) + runtime (lean image)
      - Use python:3.11-slim base image
      - Health check: curl http://localhost:8000/health
    - `.dockerignore`: exclude tests, .env, __pycache__
    - Update `Infrastructure/compose.yaml`:
      - Add `planbar_backend` service (port 8000)
      - Add `db_backend` service (PostgreSQL)
      - Ensure TiTO has callback_url pointing to backend
    - Dependency: *Step 5* → **can start early**

23. **Documentation & README**
    - `README.md`: Quick start, API overview, env vars
    - `API.md` or OpenAPI schema: Auto-generated from FastAPI docstrings
    - `ARCHITECTURE.md`: High-level design, data flow, TiTO integration
    - `CONTRIBUTING.md`: Setup, running tests, PR process
    - Dependency: *all steps* → **final**

---

## Kritische Dateien & Best Practices

### Must-Have Patterns:

**1. Database Models** (`src/app/db/models/*.py`)
- Use SQLAlchemy 2.x style (mapped_column, declarative)
- Include: __tablename__, primary keys, foreign keys, indexes
- Timestamps: created_at, updated_at (auto-managed via default/onupdate)
- Example (User model):
  ```python
  from sqlalchemy import Column, Integer, String, DateTime
  from sqlalchemy.sql import func
  from src.app.db.base import Base


  class User(Base):
      __tablename__ = "users"
      id = Column(Integer, primary_key=True)
      username = Column(String(64), unique=True, nullable=False)
      email = Column(String(120), unique=True, nullable=False)
      password_hash = Column(String(255), nullable=False)
      role = Column(String(20), default="user", nullable=False)
      created_at = Column(DateTime, default=func.now(), nullable=False)
      updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
      last_login = Column(DateTime, nullable=True)
  ```

**2. Pydantic Schemas** (`src/app/schemas/*.py`)
- Separate for Create (subset fields), Update (optional fields), Response (all fields + id, timestamps)
- Use Field for validation & documentation
- Example:
  ```python
  from pydantic import BaseModel, EmailStr, Field


  class UserCreate(BaseModel):
      username: str = Field(..., min_length=3, max_length=64)
      email: EmailStr
      password: str = Field(..., min_length=8)


  class UserResponse(BaseModel):
      id: int
      username: str
      email: str
      role: str
      created_at: datetime

      model_config = ConfigDict(from_attributes=True)
  ```

**3. Dependency Injection** (`src/app/dependencies.py`)
```python
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from src.app.db.database import SessionLocal
from src.app.core.auth import verify_token


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    claims = verify_token(token)
    user = db.query(User).filter(User.id == claims["sub"]).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    return user
```

**4. Error Handling** (`src/app/core/exceptions.py`)
```python
class BaseException(Exception):
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail


class NotFoundError(BaseException):
    def __init__(self, resource: str):
        super().__init__(404, f"{resource} not found")


class ValidationError(BaseException):
    def __init__(self, message: str):
        super().__init__(400, message)
```

**5. API Endpoints** (`src/app/api/v1/*.py`)
- Use fastapi.APIRouter()
- Include request validation (request body), response model, status codes
- Example:
  ```python
  from fastapi import APIRouter, Depends, HTTPException, status

  router = APIRouter(prefix="/users", tags=["users"])


  @router.post("/", response_model=UserResponse, status_code=201)
  def create_user(user: UserCreate, db: Session = Depends(get_db)):
      # Check existing
      if db.query(User).filter(User.email == user.email).first():
          raise HTTPException(status_code=409, detail="Email already registered")
      # Create & return
      new_user = User(**user.model_dump(exclude={"password"}), password_hash=hash_password(user.password))
      db.add(new_user)
      db.commit()
      db.refresh(new_user)
      return new_user
  ```

**6. TiTO Integration** (`src/app/services/tito_proxy.py`)
```python
import httpx
from typing import Dict, Any


class TiTOProxy:
    def __init__(self, api_url: str, api_key: str):
        self.api_url = api_url
        self.client = httpx.AsyncClient(headers={"Authorization": f"Bearer {api_key}"})

    async def submit_job(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        try:
            response = await self.client.post(f"{self.api_url}/jobs", json=payload)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            # Retry logic or raise
            raise

    async def get_job_status(self, job_id: int) -> Dict[str, Any]:
        response = await self.client.get(f"{self.api_url}/jobs/{job_id}")
        response.raise_for_status()
        return response.json()
```

**7. Testing** (`tests/conftest.py`, `tests/integration/test_*.py`)
- Use TestClient from fastapi.testclient
- Mock TiTO API with unittest.mock
- Example:
  ```python
  @pytest.fixture
  def test_client(test_db):
      app.dependency_overrides[get_db] = lambda: test_db
      return TestClient(app)


  def test_create_user(test_client):
      response = test_client.post(
          "/api/v1/users", json={"username": "john", "email": "john@example.com", "password": "secure123"}
      )
      assert response.status_code == 201
      assert response.json()["username"] == "john"
  ```

---

## Verifikation & Milestones

### MVP Delivery (Week 1-2):
- ✓ Database schema created & migrations working
- ✓ User CRUD + JWT auth (login, refresh) endpoints
- ✓ Employee CRUD endpoints
- ✓ ShiftWish CRUD endpoints
- ✓ Schedule CRUD + TiTO job submission endpoint
- ✓ TiTO callback handler
- ✓ Basic error handling & logging
- ✓ Docker setup + docker-compose override

### Phase 1 Complete (Week 3-4):
- ✓ All CRUD endpoints (Roles, Contracts, Timecards)
- ✓ Schedule weeks/shifts/summary endpoints
- ✓ Health & metrics endpoints
- ✓ DLQ & callback management
- ✓ Comprehensive unit + integration + E2E tests (>80% coverage)
- ✓ Middleware (auth, error handling, logging)
- ✓ Documentation (README, API schema, architecture)
- ✓ Production-ready Dockerfile & docker-compose

### Post-Phase 1 (Future):
- Webhook signature validation (HMAC)
- Request rate limiting
- caching (Redis)
- Tenant isolation (if multi-tenant)
- Audit logging
- Database connection pooling optimization
- Observability (Prometheus, Grafana)

---

## Entscheidungen & Scoping

- **Framework**: FastAPI (async, performance, auto-docs)
- **Database**: PostgreSQL (separate instance from TiTO)
- **Auth**: JWT (stateless, SPA-friendly, no session management)
- **API**: RESTful (simple, well-understood, aligns with TiTO API)
- **Testing**: Pragmatic integration-focused (E2E for critical flows)
- **Deployment**: Docker Compose (local dev) + Dockerfile (production-ready)
- **Language**: Python (consistency with TiTO, data-heavy operations)
- **ORM**: SQLAlchemy 2.x (mature, type-hinting support, migration tooling)

### Nicht im Scope Phase 1:
- GraphQL (complexity not justified yet)
- Multi-tenancy (single tenant MVP)
- OAuth2 social login (JWT only)
- WebSocket (polling sufficient for MVP)
- Database replication/failover
- Load balancing (single backend instance)
- CDN/caching layer

---

## Relevant Files Reference

**Existing PlanBar Docs**:
- [PlanBar - Backend Architecture](architecture.md) – Requirements & DB schema
- [PlanBar - Frontend](../../PlanBar%20-%20Frontend/src) – Frontend types & API expectations

**TiTO Integration**:
- [TiTO Architecture](../../TiTO/docs/architecture.md) – Job lifecycle, schema validation
- [TiTO API](../../TiTO/docs/api-documentation.md) – Endpoints & request/response format
- [TiTO src](../../TiTO/src/tito) – Reference for job payloads, result structures

**Infrastructure**:
- [compose.yaml](../../Infrastructure/compose.yaml) – Database & service orchestration
- [init-db.sql](../../Infrastructure/init-db.sql) – DB initialization (extend for backend DB)

---

## Next Steps (Nach Plan-Approval)

1. Create repository memory (`/memories/repo/backend-setup.md`) with exact command sequence
2. Initialize FastAPI project with dependencies
3. Set up test infrastructure & first migration
4. Implement Phase 1A (foundations) & Phase 1B (models)
5. Iterate through phases, tracking progress in session memory
