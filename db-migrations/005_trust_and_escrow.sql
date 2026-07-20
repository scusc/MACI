-- Migration: Trust & Escrow Finalization
-- Adds KYC, Karma, and Stripe Connect fields to the User table

ALTER TABLE users 
ADD COLUMN IF NOT EXISTS kyc_status VARCHAR(50) DEFAULT 'unverified',
ADD COLUMN IF NOT EXISTS karma_score INTEGER DEFAULT 100,
ADD COLUMN IF NOT EXISTS stripe_connect_id VARCHAR(255);

-- Payment status updates for Escrow states
-- Note: 'held', 'captured', 'refunded' states are already handled as strings in code,
-- but if there is a CHECK constraint on payment status, it should be updated here.
