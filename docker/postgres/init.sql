-- PostgreSQL initialization script for AI Memory Assistant
-- This runs on first container start-up.

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- for trigram text search

-- Set timezone
SET timezone = 'UTC';

-- Create database if not exists (handled by POSTGRES_DB env)
-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE ai_memory TO postgres;

\echo 'Database initialization complete.'
