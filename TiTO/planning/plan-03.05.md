## Plan: Completing TiTO Implementation Based on README Requirements

Implement missing critical and high-priority features to make TiTO a production-ready shift scheduling optimizer, focusing on authentication, full constraint enforcement, monitoring, and robustness as specified in README.md.

**Steps**
1. **Phase 1: Implement Authentication and Authorization** (Parallel with Phase 2)
   - Implement token-based authentication in auth.py (e.g., JWT or API keys)
   - Add middleware to Flask API for request authentication
   - Implement role-based access control for multi-tenancy isolation
   - Update API endpoints to require authentication

2. **Phase 2: Complete Hard Constraints in Solver** (Parallel with Phase 1)
   - Add maximum 10 hours/day work time constraint
   - Implement Sunday rest requirement (15 free Sundays/year)
   - Enforce break rules (30-45 min based on shift duration)
   - Add support for split shifts (Teilschichten) with rest time calculation
   - Implement maximal consecutive days limit
   - Add weekly working hours constraints based on contracts

3. **Phase 3: Enhance Soft Constraints and Optimization**
   - Implement OFF wishes (day off requests) as soft constraints
   - Add equal wish distribution fairness
   - Optimize for Stundenkonto (hour balance) minimization
   - Include additional wish types (e.g., avoid shift)

4. **Phase 4: Improve Job Queue Robustness**
   - Implement retry mechanism with exponential backoff
   - Add Dead Letter Queue for permanently failed jobs
   - Enforce job timeout handling
   - Add idempotency checks using jobId
   - Implement callback queue support

5. **Phase 5: Enhance Monitoring and Metrics**
   - Implement detailed metrics collection in monitoring.py (job duration, error rates, solver timeouts)
   - Add Prometheus-compatible endpoints
   - Track per-worker performance and constraint violations
   - Integrate metrics with Flask API

6. **Phase 6: Error Handling and Robustness**
   - Add structured error responses and logging
   - Implement job failure status and attempt counter management
   - Add graceful degradation on solver failures
   - Enhance worker error handling

7. **Phase 7: Multi-Tenancy and Security**
   - Enforce tenant data isolation in DB queries - different tenants should use different databases in the same dbms
   - Add tenant-specific configuration and monitoring
   - Implement data encryption (if required)
   - Add audit trails per tenant

8. **Phase 8: Replace Schema Validation with Pydantic**
   - Create Pydantic models for input/output schemas
   - Implement schema versioning with Pydantic
   - Update validation in schema.py and worker.py

9. **Phase 9: Advanced Solver Features**
   - Add constraint violation details in output
   - Implement rotation rules and role separation
   - Distinguish soft vs hard availability
   - Add monotony avoidance constraints

10. **Phase 10: Documentation and Testing**
    - Create API documentation (OpenAPI/Swagger)
    - Document JSON schemas and constraint logic
    - Add comprehensive tests for new features
    - Create deployment and performance tuning guides

**Relevant files**
- `src/tito/auth.py` — Implement authentication logic
- `src/tito/solver.py` — Add missing constraints and features
- `src/tito/monitoring.py` — Build metrics collection
- `src/tito/queue.py` — Enhance queue management
- `src/tito/db.py` — Add error handling and tenant isolation
- `src/tito/schema.py` — Migrate to Pydantic
- `src/tito/api.py` — Add auth middleware and advanced endpoints
- `src/tito/worker.py` — Improve error handling
- `tests/` — Expand test coverage for new features
- `docs/` — Add API and deployment docs

**Verification**
1. Run all existing tests and ensure new tests pass for each phase
2. Manually test API endpoints with authentication
3. Verify solver produces valid schedules with all constraints using sample inputs
4. Check metrics endpoints return real data
5. Test multi-tenant isolation with separate tenant jobs
6. Validate timeout and error handling with malformed inputs

**Decisions**
- Use JWT for authentication (simple, scalable)
- Prioritize hard constraints over soft ones in solver objective
- Keep SQLite for development, add PostgreSQL support for production
- Implement basic retry (3 attempts) before DLQ
- Exclude data encryption for MVP as per README

**Further Considerations**
1. What authentication method to use (JWT, API keys, OAuth)?
2. Should we switch to PostgreSQL now or keep SQLite for simplicity?
3. How to handle schema versioning for backward compatibility?
4. Any specific monitoring tools or formats (Prometheus, custom)?