-- Slice Payment Service — Treasury Pivot Migration

DROP TABLE IF EXISTS slice_payments;

CREATE TABLE IF NOT EXISTS slice_swarm_treasuries (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    swarm_id              UUID NOT NULL UNIQUE,
    balance               INT NOT NULL DEFAULT 0,
    currency              VARCHAR(3) NOT NULL DEFAULT 'USD',
    virtual_card_id       VARCHAR(100),
    virtual_card_last4    VARCHAR(4),
    is_active             BOOLEAN DEFAULT TRUE,
    created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at            TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_slice_treasuries_swarm ON slice_swarm_treasuries(swarm_id);

CREATE TABLE IF NOT EXISTS slice_treasury_transactions (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    treasury_id           UUID NOT NULL REFERENCES slice_swarm_treasuries(id),
    peer_id               UUID,
    amount                INT NOT NULL,
    currency              VARCHAR(3) NOT NULL DEFAULT 'USD',
    transaction_type      VARCHAR(20) NOT NULL,
    gateway_reference     VARCHAR(200),
    status                VARCHAR(20) NOT NULL DEFAULT 'pending',
    created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    
    CONSTRAINT chk_txn_type CHECK (transaction_type IN ('deposit', 'card_spend', 'refund')),
    CONSTRAINT chk_txn_status CHECK (status IN ('pending', 'completed', 'failed', 'reversed'))
);

CREATE INDEX idx_slice_txn_treasury ON slice_treasury_transactions(treasury_id);
CREATE INDEX idx_slice_txn_peer ON slice_treasury_transactions(peer_id);
CREATE INDEX idx_slice_txn_ref ON slice_treasury_transactions(gateway_reference);
