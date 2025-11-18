-- Migration: 002_job_history.sql
-- Description: Add job execution history and audit trail table
-- Date: 2025-11-10

-- Job execution history table
CREATE TABLE IF NOT EXISTS job_executions (
    execution_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    schedule_id UUID REFERENCES schedules(schedule_id) ON DELETE CASCADE,
    job_id VARCHAR(255) NOT NULL,
    domain VARCHAR(255) NOT NULL,
    domain_config_id UUID NOT NULL,
    status VARCHAR(50) NOT NULL CHECK (status IN ('started', 'success', 'failed', 'cancelled')),
    started_at TIMESTAMP NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMP,
    duration_seconds FLOAT,
    scan_id UUID,
    error_message TEXT,
    error_details JSONB,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for job executions
CREATE INDEX IF NOT EXISTS idx_job_executions_schedule_id ON job_executions(schedule_id);
CREATE INDEX IF NOT EXISTS idx_job_executions_job_id ON job_executions(job_id);
CREATE INDEX IF NOT EXISTS idx_job_executions_domain ON job_executions(domain);
CREATE INDEX IF NOT EXISTS idx_job_executions_status ON job_executions(status);
CREATE INDEX IF NOT EXISTS idx_job_executions_started_at ON job_executions(started_at DESC);
CREATE INDEX IF NOT EXISTS idx_job_executions_domain_config_id ON job_executions(domain_config_id);

-- Composite index for common queries
CREATE INDEX IF NOT EXISTS idx_job_executions_schedule_started ON job_executions(schedule_id, started_at DESC);
CREATE INDEX IF NOT EXISTS idx_job_executions_domain_started ON job_executions(domain, started_at DESC);
