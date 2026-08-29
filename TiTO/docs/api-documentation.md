# API Documentation

## Endpoints

### GET /health
- **Description**: Health check endpoint to verify the service is running.
- **Authentication**: None
- **Response**:
  - 200 OK: `{"status": "ok"}`

### GET /metrics
- **Description**: Retrieve metrics about the job queue and system, scoped to the authenticated tenant.
- **Authentication**: Required (Bearer token or X-API-Key)
- **Tenant Scoping**: Metrics are filtered by the authenticated tenant ID. Admin tokens without tenant mapping see all tenants.
- **Response**:
  - 200 OK: JSON object containing metrics data (see monitoring.get_metrics for details)

### GET /jobs
- **Description**: List all jobs in the queue, ordered by creation date (newest first). Results are scoped to the authenticated tenant.
- **Authentication**: Required
- **Tenant Scoping**: Mandanten-scoped tokens see only their own jobs. Admin tokens without tenant mapping see all jobs.
- **Response**:
  - 200 OK: Array of job objects, each containing: job_id, status, priority, created_at, updated_at

### POST /jobs
- **Description**: Enqueue a new job. The payload is validated against the Pydantic schema before being stored.
- **Authentication**: Required
- **Request Body**:
  - JSON object matching the `JobPayload` schema. Required metadata fields: `tenantId` (int ≥1). Optional metadata: `idempotency_key`, `callback_url`, `max_retries`.
- **Tenant Enforcement**:
  - Mandanten-scoped tokens may only submit jobs for their own `tenantId` (the payload `tenantId` must match the token's tenant).
  - Admin tokens without tenant mapping may submit for any `tenantId` (the value must be present and valid).
- **Response**:
  - 201 Created: `{"status": "queued", "jobId": <job_id>}`
  - 400 Bad Request: Invalid JSON payload or schema validation failure (missing `tenantId`, invalid dates, unknown references)
  - 403 Forbidden: `tenantId` does not match the authenticated tenant
  - 409 Conflict: Duplicate job (if idempotency_key provided and already exists for this tenant)

### POST /workers/register
- **Description**: Register a new worker.
- **Authentication**: Required
- **Request Body**:
  - `worker_id` (string): Unique identifier for the worker.
  - Optional: `cpu_usage` (float, default 0.0), `ram_usage` (float, default 0.0)
- **Response**:
  - 200 OK: `{"status": "registered"}`

### POST /workers/heartbeat
- **Description**: Update the heartbeat of a worker.
- **Authentication**: Required
- **Request Body**:
  - `worker_id` (string): The worker's ID.
  - Optional: `cpu_usage` (float, default 0.0), `ram_usage` (float, default 0.0), `active_jobs` (int, default 0)
- **Response**:
  - 200 OK: `{"status": "updated"}`

### POST /workers/deregister
- **Description**: Deregister a worker.
- **Authentication**: Required
- **Request Body**:
  - `worker_id` (string): The worker's ID.
- **Response**:
  - 200 OK: `{"status": "deregistered"}`

### POST /workers/cleanup
- **Description**: Manually trigger cleanup of inactive workers.
- **Authentication**: Required
- **Query Parameters**:
  - `timeout` (int, default 300): Timeout in seconds after which a worker is considered inactive.
- **Response**:
  - 200 OK: `{"status": "cleanup completed", "deleted_workers": <count>}`

### GET /dlq
- **Description**: Retrieve jobs in the Dead Letter Queue (DLQ), scoped to the authenticated tenant.
- **Authentication**: Required
- **Tenant Scoping**: Only DLQ entries for the authenticated tenant are returned. Admin tokens without tenant mapping see all.
- **Response**:
  - 200 OK: JSON object with `count` (number of DLQ jobs) and `jobs` (array of job objects)

### GET /callbacks/pending
- **Description**: Get pending callbacks to be sent, scoped to the authenticated tenant.
- **Authentication**: Required
- **Tenant Scoping**: Only callbacks for the authenticated tenant are returned. Admin tokens without tenant mapping see all.
- **Response**:
  - 200 OK: JSON object with `count` (number of pending callbacks) and `callbacks` (array of callback objects)

### GET /jobs/<int:job_id>
- **Description**: Get detailed status of a specific job, including retry attempts and callbacks. Cross-tenant access returns 404.
- **Authentication**: Required
- **Parameters**:
  - `job_id` (integer): The ID of the job.
- **Tenant Scoping**: The job must belong to the authenticated tenant. Cross-tenant queries return 404.
- **Response**:
  - 200 OK: Job object, which may include a `callback` field if a callback exists.
  - 404 Not Found: Job not found or belongs to a different tenant

### POST /jobs/<int:job_id>/retry
- **Description**: Manually retry a failed job (resets its status to 'queued').
- **Authentication**: Required
- **Parameters**:
  - `job_id` (integer): The ID of the job to retry.
- **Response**:
  - 200 OK: `{"status": "retry_scheduled", "jobId": <job_id>}`
  - 400 Bad Request: Job is not in a failed or dead_lettered state
  - 404 Not Found: Job not found

### GET /metrics/robustness
- **Description**: Get robustness metrics including retries, DLQ, and callback statistics, scoped to the authenticated tenant.
- **Authentication**: Required
- **Tenant Scoping**: Metrics are filtered by the authenticated tenant ID.
- **Response**:
  - 200 OK: JSON object containing:
    - `job_statuses`: Count of jobs by status
    - `dead_letter_queue_size`: Number of jobs in DLQ
    - `callbacks`: Count of callbacks by status
    - `error_rate`: Rate of errors
    - `solver_timeout_rate`: Rate of solver timeouts
    - `average_job_duration_seconds`: Average job duration

### GET /metrics/prometheus
- **Description**: Export metrics in Prometheus format, scoped to the authenticated tenant.
- **Authentication**: Required
- **Tenant Scoping**: Metrics are filtered by the authenticated tenant ID.
- **Response**:
  - 200 OK: Plain text in Prometheus exposition format

### GET /openapi.json
- **Description**: Retrieve the OpenAPI schema document for TiTO.
- **Authentication**: None
- **Response**:
  - 200 OK: OpenAPI JSON document describing endpoints and request/response schemas

> Hinweis: Das OpenAPI-Dokument kann in Swagger UI oder ReDoc geladen werden, um eine interaktive API-Dokumentation zu erhalten.
