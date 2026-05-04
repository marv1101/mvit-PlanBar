# Phase 4: Job Queue Robustness Implementation

## Overview
This document describes the robustness features added to TiTO's job queue system in Phase 4, focusing on production-readiness through retry mechanisms, error handling, and callback support.

## Features Implemented

### 1. Retry Mechanism with Exponential Backoff
- **Automatic Retries**: Failed jobs are automatically retried up to `max_retries` times (default: 3)
- **Exponential Backoff**: Retry delay increases exponentially: `base_delay * (2 ^ attempts)`
  - Default base delay: 5 seconds
  - Delays: 5s, 10s, 20s, 40s, ...
- **Configuration**:
  - `MAX_RETRIES`: Maximum number of retry attempts
  - `RETRY_BASE_DELAY`: Base delay in seconds for exponential backoff

**Functions**:
- `mark_job_failed_with_retry()`: Marks job as failed and schedules retry if attempts remain

### 2. Dead Letter Queue (DLQ)
- **Permanent Failure Handling**: Jobs that exceed `max_retries` are moved to Dead Letter Queue
- **Investigation**: DLQ stores original payload, failure reason, and attempt count for debugging
- **New Endpoints**:
  - `GET /dlq`: View all dead-lettered jobs
  - `POST /jobs/{job_id}/retry`: Manually retry a dead-lettered job

**Functions**:
- `move_job_to_dlq()`: Move permanently failed job to DLQ

**Database Schema**:
```sql
CREATE TABLE dead_letter_queue (
    dlq_id SERIAL PRIMARY KEY,
    job_id INTEGER NOT NULL,
    original_payload JSONB NOT NULL,
    failure_reason TEXT NOT NULL,
    sent_to_dlq_at TIMESTAMP WITH TIME ZONE NOT NULL,
    attempts INTEGER NOT NULL,
    tenant_id TEXT
);
```

### 3. Job Timeout Handling
- **Timeout Detection**: Check if job processing exceeds `timeout_seconds`
- **Configuration**: `TIMEOUT_SECONDS` (default: 300s)
- **Function**: `check_job_timeout()` - Returns true if job has exceeded timeout

### 4. Idempotency Checks
- **Duplicate Prevention**: Jobs with same `idempotency_key` are not processed twice
- **Reuse Results**: If job with same idempotency_key already completed, return existing result
- **Configuration**: Pass `idempotency_key` in job metadata
- **HTTP Response**: Returns HTTP 409 (Conflict) if duplicate detected

**Functions**:
- `check_idempotency()`: Check if job with idempotency_key already exists

**Database Schema**:
```sql
idempotency_key TEXT UNIQUE  -- Added to job_queue table
```

### 5. Callback Queue Support
- **Async Notifications**: Jobs can request callbacks when completed
- **Automatic Retry**: Failed callbacks are retried with backoff
- **Configuration**:
  - `CALLBACK_MAX_ATTEMPTS`: Max callback delivery attempts (default: 3)
  - `CALLBACK_RETRY_DELAY`: Delay between callback retries (default: 60s)
- **New Endpoints**:
  - `GET /callbacks/pending`: View pending callbacks
  - `GET /jobs/{job_id}`: Get job with callback status

**Functions**:
- `enqueue_callback()`: Enqueue callback notification
- `fetch_pending_callbacks()`: Get pending callbacks to send
- `store_callback_result()`: Update callback status

**Database Schema**:
```sql
CREATE TABLE callback_queue (
    callback_id SERIAL PRIMARY KEY,
    job_id INTEGER NOT NULL,
    callback_url TEXT NOT NULL,
    callback_status TEXT DEFAULT 'pending',
    result_payload JSONB,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    attempted_at TIMESTAMP WITH TIME ZONE,
    attempts INTEGER DEFAULT 0,
    max_attempts INTEGER DEFAULT 3,
    tenant_id TEXT,
    FOREIGN KEY(job_id) REFERENCES job_queue(job_id) ON DELETE CASCADE
);
```

## Database Schema Updates

### New Fields in job_queue Table
| Field | Type | Purpose |
|-------|------|---------|
| `attempts` | INTEGER | Current retry attempt count |
| `max_retries` | INTEGER | Maximum retry attempts for this job |
| `last_error` | TEXT | Last error message |
| `failed_at` | TIMESTAMP | Timestamp of last failure |
| `scheduled_for` | TIMESTAMP | Retry scheduled time (for backoff) |
| `callback_url` | TEXT | Callback URL if job should trigger callback |
| `idempotency_key` | TEXT UNIQUE | Unique key for idempotency |
| `timeout_at` | TIMESTAMP | Job timeout deadline |
| `tenant_id` | TEXT | Tenant ID for multi-tenancy |

### New Job Status
- `dead_lettered`: Job permanently failed and moved to DLQ

## API Usage Examples

### 1. Submit Job with Idempotency
```json
POST /jobs
{
  "metadata": {
    "idempotency_key": "unique-client-request-id-123",
    "callback_url": "https://example.com/job-results",
    "max_retries": 3,
    "tenant_id": "tenant-001",
    "priority": 10
  },
  "config": {...},
  "shiftTemplates": [...],
  "requirements": [...],
  "employees": [...]
}
```

**Response (Success)**:
```json
HTTP 201
{
  "status": "queued",
  "jobId": 42
}
```

**Response (Duplicate)**:
```json
HTTP 409
{
  "error": "Duplicate job (idempotency_key already exists)",
  "status": "duplicate"
}
```

### 2. Check Job Status with Retries
```
GET /jobs/42
```

**Response**:
```json
{
  "job_id": 42,
  "status": "completed",
  "attempts": 1,
  "max_retries": 3,
  "last_error": null,
  "callback_url": "https://example.com/job-results",
  "callback": {
    "callback_id": 10,
    "callback_status": "sent",
    "attempts": 1,
    "max_attempts": 3
  },
  "result": {...}
}
```

### 3. View Dead Letter Queue
```
GET /dlq
```

**Response**:
```json
{
  "count": 2,
  "jobs": [
    {
      "dlq_id": 1,
      "job_id": 35,
      "failure_reason": "Max retries exceeded: Timeout in solver",
      "attempts": 3,
      "sent_to_dlq_at": "2026-05-04T10:30:00Z"
    }
  ]
}
```

### 4. Manual Retry Dead-lettered Job
```
POST /jobs/35/retry
```

**Response**:
```json
{
  "status": "retry_scheduled",
  "jobId": 35
}
```

### 5. Robustness Metrics
```
GET /metrics/robustness
```

**Response**:
```json
{
  "job_statuses": {
    "queued": 5,
    "processing": 2,
    "completed": 150,
    "failed": 3,
    "dead_lettered": 2
  },
  "dead_letter_queue_size": 2,
  "callbacks": {
    "pending": 2,
    "sent": 150,
    "failed": 1
  }
}
```

## Worker Implementation

### Processing Flow with Robustness
```
1. Fetch next job from queue
2. Check idempotency key (skip if duplicate)
3. Mark job as processing
4. Execute job/solve model
5. If successful:
   - Store result
   - Enqueue callback (if requested)
6. If fails:
   - Try retry with exponential backoff
   - If max retries exceeded:
     - Move to Dead Letter Queue
```

### Graceful Shutdown
- Worker handles SIGTERM/SIGINT signals gracefully
- Finishes current job before shutdown
- Maintains state for recovery

## Configuration

### Environment Variables
```bash
# Robustness settings
MAX_RETRIES=3
RETRY_BASE_DELAY=5
CALLBACK_MAX_ATTEMPTS=3
CALLBACK_RETRY_DELAY=60

# Database for PostgreSQL production
DATABASE_URL=postgresql://user:pass@localhost/tito
```

## PostgreSQL vs SQLite

### Automatic Schema Detection
- **PostgreSQL**: Uses JSONB payload storage, TIMESTAMP WITH TIME ZONE, indexes
- **SQLite**: Uses TEXT for JSON, uses ISO 8601 datetime strings
- Both implementations are transparent to the application

### Production Considerations
- **PostgreSQL**: Recommended for production with proper backup/replication
- **SQLite**: Suitable for development and testing
- Migration from SQLite to PostgreSQL supported via schema matching

## Testing

### Manual Testing
```bash
# Start worker
python main.py --mode worker

# Submit test job with idempotency
curl -X POST http://localhost:5001/jobs \
  -H "Authorization: Bearer test-token" \
  -H "Content-Type: application/json" \
  -d '{
    "metadata": {
      "idempotency_key": "test-123",
      "callback_url": "https://webhook.example.com"
    },
    "config": {...}
  }'

# Check job status
curl http://localhost:5001/jobs/1

# Check DLQ
curl http://localhost:5001/dlq

# View robustness metrics
curl http://localhost:5001/metrics/robustness
```

## Next Steps (Phase 5+)

1. **Monitoring**: Enhanced metrics collection for Prometheus
2. **Multi-tenancy**: Enforce tenant isolation across operations
3. **Data Encryption**: Add job payload encryption for sensitive data
4. **Audit Trail**: Log all state changes for compliance
5. **Advanced Solver Features**: Constraint violation details, rotation rules

## Known Limitations

- DLQ jobs require manual intervention to retry
- Callbacks don't support authentication/signing yet (future enhancement)
- No built-in alerting for DLQ jobs (should be added to monitoring)
- Idempotency keys are unique globally (could be scoped per tenant)
