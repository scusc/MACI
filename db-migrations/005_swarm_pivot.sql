-- Rally Platform — Architecture Pivot to Swarm Topology
-- Migrating from Organizer-led Trips to Peer-to-Peer Swarms

-- 1. Trust Graph (New)
CREATE TABLE IF NOT EXISTS rally_trust_graphs (
    user_id               UUID PRIMARY KEY REFERENCES rally_users(id) ON DELETE CASCADE,
    verified_domain       VARCHAR(255),
    instagram_handle      VARCHAR(100),
    linkedin_id           VARCHAR(100),
    trust_score           INT DEFAULT 0,
    updated_at            TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 2. Rename rally_trips to rally_swarms
ALTER TABLE rally_trips RENAME TO rally_swarms;
ALTER INDEX idx_rally_trips_status RENAME TO idx_rally_swarms_status;
ALTER INDEX idx_rally_trips_invite_code RENAME TO idx_rally_swarms_invite_code;

-- Remove organizer from swarms
ALTER TABLE rally_swarms DROP CONSTRAINT IF EXISTS rally_trips_organizer_id_fkey;
ALTER TABLE rally_swarms DROP COLUMN IF EXISTS organizer_id;
DROP INDEX IF EXISTS idx_rally_trips_organizer;

-- Update swarm constraints
ALTER TABLE rally_swarms DROP CONSTRAINT IF EXISTS chk_trip_status;
ALTER TABLE rally_swarms ADD CONSTRAINT chk_swarm_status CHECK (status IN ('draft', 'collecting', 'active', 'completed', 'cancelled'));

-- 3. Rename rally_trip_members to rally_swarm_peers
ALTER TABLE rally_trip_members RENAME TO rally_swarm_peers;
ALTER TABLE rally_swarm_peers RENAME COLUMN trip_id TO swarm_id;
ALTER INDEX idx_rally_members_user RENAME TO idx_rally_peers_user;
ALTER INDEX idx_rally_members_status RENAME TO idx_rally_peers_status;
ALTER INDEX idx_rally_members_trip RENAME TO idx_rally_peers_swarm;

-- Update peer constraints
ALTER TABLE rally_swarm_peers DROP CONSTRAINT IF EXISTS chk_member_role;
ALTER TABLE rally_swarm_peers ALTER COLUMN role SET DEFAULT 'peer';
-- Force all existing to peer
UPDATE rally_swarm_peers SET role = 'peer';
ALTER TABLE rally_swarm_peers ADD CONSTRAINT chk_peer_role CHECK (role IN ('peer'));

ALTER TABLE rally_swarm_peers DROP CONSTRAINT IF EXISTS chk_member_status;
ALTER TABLE rally_swarm_peers ADD CONSTRAINT chk_peer_status CHECK (status IN ('invited', 'viewed', 'committed', 'paid', 'declined'));

ALTER TABLE rally_swarm_peers DROP CONSTRAINT IF EXISTS uq_trip_member_email;
ALTER TABLE rally_swarm_peers ADD CONSTRAINT uq_swarm_peer_email UNIQUE (swarm_id, email);

-- 4. Update Payments
ALTER TABLE rally_payments RENAME COLUMN trip_id TO swarm_id;
ALTER TABLE rally_payments RENAME COLUMN member_id TO peer_id;
ALTER INDEX idx_rally_payments_trip RENAME TO idx_rally_payments_swarm;
ALTER INDEX idx_rally_payments_member RENAME TO idx_rally_payments_peer;

-- 5. Update Price Snapshots
ALTER TABLE rally_price_snapshots RENAME COLUMN trip_id TO swarm_id;
ALTER INDEX idx_rally_snapshots_trip RENAME TO idx_rally_snapshots_swarm;
ALTER INDEX idx_rally_snapshots_trip_origin RENAME TO idx_rally_snapshots_swarm_origin;

-- 6. Clean up User relationships (if DB level)
-- (No specific FKs to drop on User for brand config as brand_config is child)
DROP TABLE IF EXISTS rally_brand_configs;

