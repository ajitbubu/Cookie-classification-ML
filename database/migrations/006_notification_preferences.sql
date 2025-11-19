-- Migration: Add notification_preferences table
-- Description: Create table for storing user notification preferences

-- Create notification_preferences table
CREATE TABLE IF NOT EXISTS notification_preferences (
    preference_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    enabled_events JSONB NOT NULL DEFAULT '[]'::jsonb,
    enabled_channels JSONB NOT NULL DEFAULT '[]'::jsonb,
    email_address VARCHAR(255),
    webhook_url TEXT,
    slack_webhook_url TEXT,
    quiet_hours JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE(user_id)
);

-- Create index on user_id for fast lookups
CREATE INDEX IF NOT EXISTS idx_notification_preferences_user_id 
ON notification_preferences(user_id);

-- Create index on enabled_events for finding users with specific events enabled
CREATE INDEX IF NOT EXISTS idx_notification_preferences_enabled_events 
ON notification_preferences USING GIN(enabled_events);

-- Add comment
COMMENT ON TABLE notification_preferences IS 'User notification preferences for events and channels';
