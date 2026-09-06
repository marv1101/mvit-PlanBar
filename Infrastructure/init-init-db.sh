#!/bin/bash
set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

    CREATE TABLE IF NOT EXISTS job_queue (
        job_id SERIAL PRIMARY KEY,
        payload JSONB NOT NULL,
        status TEXT NOT NULL,
        result JSONB,
        priority INTEGER DEFAULT 0,
        created_at TIMESTAMP WITH TIME ZONE NOT NULL,
        updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
        attempts INTEGER DEFAULT 0,
        max_retries INTEGER DEFAULT 3,
        last_error TEXT,
        failed_at TIMESTAMP WITH TIME ZONE,
        scheduled_for TIMESTAMP WITH TIME ZONE,
        callback_url TEXT,
        idempotency_key TEXT UNIQUE,
        timeout_at TIMESTAMP WITH TIME ZONE,
        tenant_id TEXT
    );

    CREATE TABLE IF NOT EXISTS callback_queue (
        callback_id SERIAL PRIMARY KEY,
        job_id SERIAL NOT NULL,
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

    CREATE TABLE IF NOT EXISTS workers (
        worker_id TEXT PRIMARY KEY,
        ip TEXT NOT NULL,
        registered_at TIMESTAMP WITH TIME ZONE NOT NULL,
        last_heartbeat TIMESTAMP WITH TIME ZONE NOT NULL,
        cpu_usage REAL,
        ram_usage REAL,
        active_jobs INTEGER DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS dead_letter_queue (
        dlq_id SERIAL PRIMARY KEY,
        job_id SERIAL NOT NULL,
        original_payload JSONB NOT NULL,
        failure_reason TEXT NOT NULL,
        sent_to_dlq_at TIMESTAMP WITH TIME ZONE NOT NULL,
        attempts INTEGER NOT NULL,
        tenant_id TEXT,
        FOREIGN KEY(job_id) REFERENCES job_queue(job_id) ON DELETE CASCADE
    );

    CREATE INDEX IF NOT EXISTS idx_job_queue_status ON job_queue(status);
    CREATE INDEX IF NOT EXISTS idx_job_queue_tenant_id ON job_queue(tenant_id);
    CREATE INDEX IF NOT EXISTS idx_job_queue_priority ON job_queue(priority DESC);
    CREATE INDEX IF NOT EXISTS idx_job_queue_created_at ON job_queue(created_at);
    CREATE INDEX IF NOT EXISTS idx_callback_queue_status ON callback_queue(status);
    CREATE INDEX IF NOT EXISTS idx_callback_queue_job_id ON callback_queue(job_id);

    CREATE TABLE IF NOT EXISTS schema_version (
        version VARCHAR(50) PRIMARY KEY,
        applied_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );

    DO \$\$
    BEGIN
        IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'tito') THEN
            CREATE USER tito WITH PASSWORD '${TITO_DB_PASSWORD}';
        END IF;
    END
    \$\$;

    GRANT ALL PRIVILEGES ON job_queue TO tito;
    GRANT ALL PRIVILEGES ON callback_queue TO tito;
    GRANT ALL PRIVILEGES ON dead_letter_queue TO tito;
    GRANT ALL PRIVILEGES ON schema_version TO tito;

    GRANT USAGE ON SCHEMA public TO tito;
    GRANT SELECT ON ALL TABLES IN SCHEMA public TO tito;

    ALTER TABLE schema_version OWNER TO tito;

    GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO tito;
EOSQL
