-- D1337 Telegram Bot Database Schema

-- Users table to track Telegram users and their premium status
CREATE TABLE IF NOT EXISTS telegram_users (
    id SERIAL PRIMARY KEY,
    telegram_id BIGINT UNIQUE NOT NULL,
    username VARCHAR(255),
    first_name VARCHAR(255),
    last_name VARCHAR(255),
    is_premium BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Usage logs table to track all queries
CREATE TABLE IF NOT EXISTS usage_logs (
    id SERIAL PRIMARY KEY,
    telegram_user_id BIGINT NOT NULL REFERENCES telegram_users(telegram_id),
    chat_id BIGINT NOT NULL,
    chat_type VARCHAR(50) NOT NULL,
    message_text TEXT,
    response_text TEXT,
    tokens_used INTEGER DEFAULT 0,
    response_time_ms INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Admin users table
CREATE TABLE IF NOT EXISTS admin_users (
    id SERIAL PRIMARY KEY,
    telegram_id BIGINT UNIQUE NOT NULL,
    granted_by BIGINT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_telegram_users_telegram_id ON telegram_users(telegram_id);
CREATE INDEX IF NOT EXISTS idx_usage_logs_telegram_user_id ON usage_logs(telegram_user_id);
CREATE INDEX IF NOT EXISTS idx_usage_logs_created_at ON usage_logs(created_at);
CREATE INDEX IF NOT EXISTS idx_admin_users_telegram_id ON admin_users(telegram_id);

-- Function to update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger to auto-update updated_at on telegram_users
DROP TRIGGER IF EXISTS update_telegram_users_updated_at ON telegram_users;
CREATE TRIGGER update_telegram_users_updated_at
    BEFORE UPDATE ON telegram_users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
