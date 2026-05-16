-- Initialize database for TiTO application
-- Create tables based on the application schema

-- Enable UUID extension if needed
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create job queue table
CREATE TABLE IF NOT EXISTS job_queue (
    id SERIAL PRIMARY KEY,
    job_id VARCHAR(255) UNIQUE,
    tenant_id INTEGER NOT NULL,
    payload JSONB NOT NULL,
    status VARCHAR(50) DEFAULT 'pending',
    priority INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    scheduled_at TIMESTAMP WITH TIME ZONE,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    failed_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3
);

-- Create callback queue table
CREATE TABLE IF NOT EXISTS callback_queue (
    id SERIAL PRIMARY KEY,
    job_id VARCHAR(255) NOT NULL,
    tenant_id INTEGER NOT NULL,
    callback_url VARCHAR(2048) NOT NULL,
    payload JSONB NOT NULL,
    status VARCHAR(50) DEFAULT 'pending',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_job_queue_status ON job_queue(status);
CREATE INDEX IF NOT EXISTS idx_job_queue_tenant_id ON job_queue(tenant_id);
CREATE INDEX IF NOT EXISTS idx_job_queue_priority ON job_queue(priority DESC);
CREATE INDEX IF NOT EXISTS idx_job_queue_created_at ON job_queue(created_at);
CREATE INDEX IF NOT EXISTS idx_callback_queue_status ON callback_queue(status);
CREATE INDEX IF NOT EXISTS idx_callback_queue_job_id ON callback_queue(job_id);

-- Create table for schema version tracking
CREATE TABLE IF NOT EXISTS schema_version (
    version VARCHAR(50) PRIMARY KEY,
    applied_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create dedicated user for TiTO application
CREATE USER tito WITH PASSWORD 'secure_password_123';

-- Grant necessary permissions on all tables
GRANT ALL PRIVILEGES ON job_queue TO tito;
GRANT ALL PRIVILEGES ON callback_queue TO tito;
GRANT ALL PRIVILEGES ON schema_version TO tito;

-- Optional: Grant usage on schemas/extensions if needed
GRANT USAGE ON SCHEMA public TO tito;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO tito;

-- Update the schema_version table ownership (optional, but good practice)
ALTER TABLE schema_version OWNER TO tito;