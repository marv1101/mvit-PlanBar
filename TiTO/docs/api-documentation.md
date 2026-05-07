# API Documentation

## Endpoints

### GET /health
- **Description**: Health check endpoint to verify the service is running.
- **Authentication**: None
- **Response**:
  - 200 OK: `{"status": "ok"}`

### GET /metrics
- **Description**: Retrieve metrics about the job queue and system.
- **Authentication**: Required (Bearer token or X-API-Key)
- **Response**:
  - 200 OK: JSON object containing metrics data (see monitoring.get_metrics for details)

### GET /jobs
- **Description**: List all jobs in the queue, ordered by creation date (newest first).
- **Authentication**: Required
- **Response**:
  - 200 OK: Array of job objects, each containing: job_id, status, priority, created_at, updated_at

### POST /jobs
- **Description**: Enqueue a new job.
- **Authentication**: Required
- **Request Body**:
  - JSON object with the job payload. Optional metadata can include: idempotency_key, callback_url, max_retries, tenant_id.
- **Response**:
  - 201 Created: `{"status": "queued", "jobId": <job_id>}`
  - 400 Bad Request: Invalid JSON payload
  - 409 Conflict: Duplicate job (if idempotency_key provided and already exists)

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
- **Description**: Retrieve jobs in the Dead Letter Queue (DLQ).
- **Authentication**: Required
- **Response**:
  - 200 OK: JSON object with `count` (number of DLQ jobs) and `jobs` (array of job objects)

### GET /callbacks/pending
- **Description**: Get pending callbacks to be sent.
- **Authentication**: Required
- **Response**:
  - 200 OK: JSON object with `count` (number of pending callbacks) and `callbacks` (array of callback objects)

### GET /jobs/<int:job_id>
- **Description**: Get detailed status of a specific job, including retry attempts and callbacks.
- **Authentication**: Required
- **Parameters**:
  - `job_id` (integer): The ID of the job.
- **Response**:
  - 200 OK: Job object, which may include a `callback` field if a callback exists.
  - 404 Not Found: Job not found

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
- **Description**: Get robustness metrics including retries, DLQ, and callback statistics.
- **Authentication**: Required
- **Response**:
  - 200 OK: JSON object containing:
    - `job_statuses`: Count of jobs by status
    - `dead_letter_queue_size`: Number of jobs in DLQ
    - `callbacks`: Count of callbacks by status
    - `error_rate`: Rate of errors
    - `solver_timeout_rate`: Rate of solver timeouts
    - `average_job_duration_seconds`: Average job duration

### GET /metrics/prometheus
- **Description**: Export metrics in Prometheus format.
- **Authentication**: Required
- **Response**:
  - 200 OK: Plain text in Prometheus exposition format