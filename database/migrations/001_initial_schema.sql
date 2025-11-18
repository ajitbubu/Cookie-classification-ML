-- Migration: 001_initial_schema.sql
-- Description: Create initial database schema for Cookie Scanner Platform
-- Date: 2025-11-04

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Users table
CREATE TABLE IF NOT EXISTS users (
    user_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255),
    role VARCHAR(50) NOT NULL CHECK (role IN ('admin', 'user', 'viewer')),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- API keys table
CREATE TABLE IF NOT EXISTS api_keys (
    api_key_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(user_id) ON DELETE CASCADE,
    key_hash VARCHAR(64) UNIQUE NOT NULL,
    scopes JSONB DEFAULT '[]'::jsonb,
    rate_limit INT DEFAULT 100,
    enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP,
    last_used_at TIMESTAMP
);

-- Scan profiles table
CREATE TABLE IF NOT EXISTS scan_profiles (
    profile_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    scan_mode VARCHAR(50) NOT NULL CHECK (scan_mode IN ('quick', 'deep', 'scheduled', 'realtime')),
    config JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_by UUID REFERENCES users(user_id) ON DELETE SET NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Scan results table
CREATE TABLE IF NOT EXISTS scan_results (
    scan_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    domain_config_id UUID NOT NULL,
    domain VARCHAR(255) NOT NULL,
    scan_mode VARCHAR(50) NOT NULL CHECK (scan_mode IN ('quick', 'deep', 'scheduled', 'realtime')),
    timestamp_utc TIMESTAMP NOT NULL DEFAULT NOW(),
    status VARCHAR(50) NOT NULL CHECK (status IN ('pending', 'running', 'success', 'failed', 'cancelled')),
    duration_seconds FLOAT,
    total_cookies INT DEFAULT 0,
    page_count INT DEFAULT 0,
    error TEXT,
    params JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Cookies table (normalized)
CREATE TABLE IF NOT EXISTS cookies (
    cookie_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    scan_id UUID REFERENCES scan_results(scan_id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    domain VARCHAR(255) NOT NULL,
    path VARCHAR(500) DEFAULT '/',
    hashed_value VARCHAR(64),
    cookie_duration VARCHAR(50),
    size INT,
    http_only BOOLEAN DEFAULT FALSE,
    secure BOOLEAN DEFAULT FALSE,
    same_site VARCHAR(20),
    category VARCHAR(50),
    vendor VARCHAR(255),
    cookie_type VARCHAR(50) CHECK (cookie_type IN ('First Party', 'Third Party', 'unknown')),
    set_after_accept BOOLEAN DEFAULT FALSE,
    iab_purposes JSONB DEFAULT '[]'::jsonb,
    description TEXT,
    source VARCHAR(50),
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Schedules table
CREATE TABLE IF NOT EXISTS schedules (
    schedule_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    domain_config_id UUID NOT NULL,
    domain VARCHAR(255) NOT NULL,
    profile_id UUID REFERENCES scan_profiles(profile_id) ON DELETE SET NULL,
    frequency VARCHAR(50) NOT NULL CHECK (frequency IN ('hourly', 'daily', 'weekly', 'monthly', 'custom')),
    time_config JSONB NOT NULL DEFAULT '{}'::jsonb,
    enabled BOOLEAN DEFAULT TRUE,
    next_run TIMESTAMP,
    last_run TIMESTAMP,
    last_status VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Reports table
CREATE TABLE IF NOT EXISTS reports (
    report_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    scan_id UUID REFERENCES scan_results(scan_id) ON DELETE CASCADE,
    report_type VARCHAR(50) NOT NULL CHECK (report_type IN ('compliance', 'comparison', 'trend', 'custom')),
    format VARCHAR(20) NOT NULL CHECK (format IN ('pdf', 'html', 'json', 'csv')),
    generated_at TIMESTAMP DEFAULT NOW(),
    data JSONB DEFAULT '{}'::jsonb,
    file_path VARCHAR(500),
    file_size INT,
    created_by UUID REFERENCES users(user_id) ON DELETE SET NULL
);

-- Notifications table
CREATE TABLE IF NOT EXISTS notifications (
    notification_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    event VARCHAR(100) NOT NULL,
    channel VARCHAR(50) NOT NULL CHECK (channel IN ('email', 'webhook', 'slack')),
    status VARCHAR(50) NOT NULL CHECK (status IN ('pending', 'sent', 'failed', 'retrying')),
    created_at TIMESTAMP DEFAULT NOW(),
    sent_at TIMESTAMP,
    retry_count INT DEFAULT 0,
    data JSONB DEFAULT '{}'::jsonb,
    error TEXT
);

-- Create indexes for performance optimization

-- Scan results indexes
CREATE INDEX IF NOT EXISTS idx_scan_results_domain_config ON scan_results(domain_config_id);
CREATE INDEX IF NOT EXISTS idx_scan_results_domain ON scan_results(domain);
CREATE INDEX IF NOT EXISTS idx_scan_results_timestamp ON scan_results(timestamp_utc DESC);
CREATE INDEX IF NOT EXISTS idx_scan_results_status ON scan_results(status);
CREATE INDEX IF NOT EXISTS idx_scan_results_scan_mode ON scan_results(scan_mode);
CREATE INDEX IF NOT EXISTS idx_scan_results_created_at ON scan_results(created_at DESC);

-- Cookies indexes
CREATE INDEX IF NOT EXISTS idx_cookies_scan_id ON cookies(scan_id);
CREATE INDEX IF NOT EXISTS idx_cookies_name ON cookies(name);
CREATE INDEX IF NOT EXISTS idx_cookies_domain ON cookies(domain);
CREATE INDEX IF NOT EXISTS idx_cookies_category ON cookies(category);
CREATE INDEX IF NOT EXISTS idx_cookies_cookie_type ON cookies(cookie_type);
CREATE INDEX IF NOT EXISTS idx_cookies_vendor ON cookies(vendor);

-- Schedules indexes
CREATE INDEX IF NOT EXISTS idx_schedules_domain_config ON schedules(domain_config_id);
CREATE INDEX IF NOT EXISTS idx_schedules_next_run ON schedules(next_run) WHERE enabled = TRUE;
CREATE INDEX IF NOT EXISTS idx_schedules_enabled ON schedules(enabled);
CREATE INDEX IF NOT EXISTS idx_schedules_domain ON schedules(domain);

-- Scan profiles indexes
CREATE INDEX IF NOT EXISTS idx_scan_profiles_created_by ON scan_profiles(created_by);
CREATE INDEX IF NOT EXISTS idx_scan_profiles_scan_mode ON scan_profiles(scan_mode);

-- Reports indexes
CREATE INDEX IF NOT EXISTS idx_reports_scan_id ON reports(scan_id);
CREATE INDEX IF NOT EXISTS idx_reports_report_type ON reports(report_type);
CREATE INDEX IF NOT EXISTS idx_reports_generated_at ON reports(generated_at DESC);
CREATE INDEX IF NOT EXISTS idx_reports_created_by ON reports(created_by);

-- Notifications indexes
CREATE INDEX IF NOT EXISTS idx_notifications_user_id ON notifications(user_id);
CREATE INDEX IF NOT EXISTS idx_notifications_status ON notifications(status);
CREATE INDEX IF NOT EXISTS idx_notifications_created_at ON notifications(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_notifications_event ON notifications(event);

-- API keys indexes
CREATE INDEX IF NOT EXISTS idx_api_keys_user_id ON api_keys(user_id);
CREATE INDEX IF NOT EXISTS idx_api_keys_enabled ON api_keys(enabled) WHERE enabled = TRUE;
CREATE INDEX IF NOT EXISTS idx_api_keys_expires_at ON api_keys(expires_at) WHERE expires_at IS NOT NULL;

-- Users indexes
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);

-- Create composite indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_scan_results_domain_timestamp ON scan_results(domain, timestamp_utc DESC);
CREATE INDEX IF NOT EXISTS idx_cookies_scan_category ON cookies(scan_id, category);
CREATE INDEX IF NOT EXISTS idx_notifications_user_status ON notifications(user_id, status);
