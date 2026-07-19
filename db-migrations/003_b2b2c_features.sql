-- Migration: Phase 3 B2B2C Features
-- Add Brand Configs Table

CREATE TABLE rally_brand_configs (
    organizer_id UUID PRIMARY KEY REFERENCES rally_users(id) ON DELETE CASCADE,
    primary_color VARCHAR(7) NOT NULL DEFAULT '#000000',
    logo_url VARCHAR(1000),
    company_name VARCHAR(100) NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Note: We are using JSON requests for bulk invites rather than CSV uploads to keep the API clean.
-- The Organizer Dashboard relies entirely on aggregations of existing fields.
