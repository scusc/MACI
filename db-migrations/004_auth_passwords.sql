-- Migration: Phase 5 Security Hardening
-- Add password_hash to rally_users

ALTER TABLE rally_users ADD COLUMN IF NOT EXISTS password_hash VARCHAR(255);
