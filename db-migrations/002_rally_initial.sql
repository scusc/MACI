-- Rally Platform — Initial Database Schema
-- Supports: Trip lifecycle, member commitments, escrow payments, price tracking

-- ── Users ─────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS rally_users (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email                 VARCHAR(255) UNIQUE NOT NULL,
    display_name          VARCHAR(100),
    phone                 VARCHAR(20),
    country_code          VARCHAR(2) DEFAULT 'US',
    stripe_customer_id    VARCHAR(100),
    razorpay_customer_id  VARCHAR(100),
    created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at            TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_rally_users_email ON rally_users(email);


-- ── Trips ─────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS rally_trips (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title                       VARCHAR(200) NOT NULL,
    destination                 VARCHAR(200) NOT NULL,
    start_date                  DATE NOT NULL,
    end_date                    DATE,
    description                 TEXT,
    status                      VARCHAR(20) NOT NULL DEFAULT 'draft',
    currency                    VARCHAR(3) NOT NULL DEFAULT 'USD',
    threshold_pct               INT NOT NULL DEFAULT 80,
    estimated_cost_per_person   INT,                -- in cents/paise
    commitment_deadline         TIMESTAMPTZ,
    invite_code                 VARCHAR(20) UNIQUE NOT NULL,
    organizer_id                UUID NOT NULL REFERENCES rally_users(id),
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at                  TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT chk_trip_status CHECK (status IN ('draft', 'collecting', 'active', 'completed', 'cancelled')),
    CONSTRAINT chk_threshold CHECK (threshold_pct >= 50 AND threshold_pct <= 100)
);

CREATE INDEX idx_rally_trips_organizer ON rally_trips(organizer_id);
CREATE INDEX idx_rally_trips_status ON rally_trips(status);
CREATE INDEX idx_rally_trips_invite_code ON rally_trips(invite_code);


-- ── Trip Members ──────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS rally_trip_members (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trip_id         UUID NOT NULL REFERENCES rally_trips(id) ON DELETE CASCADE,
    user_id         UUID REFERENCES rally_users(id),
    email           VARCHAR(255) NOT NULL,
    display_name    VARCHAR(100),
    role            VARCHAR(20) NOT NULL DEFAULT 'member',
    status          VARCHAR(20) NOT NULL DEFAULT 'invited',
    share_amount    INT,                -- in cents/paise (their portion)
    platform_fee    INT,                -- in cents/paise (transparent fee)
    origin_airport  VARCHAR(3),
    invited_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    viewed_at       TIMESTAMPTZ,
    committed_at    TIMESTAMPTZ,
    paid_at         TIMESTAMPTZ,
    declined_at     TIMESTAMPTZ,

    CONSTRAINT chk_member_role CHECK (role IN ('organizer', 'member')),
    CONSTRAINT chk_member_status CHECK (status IN ('invited', 'viewed', 'committed', 'paid', 'declined')),
    CONSTRAINT uq_trip_member_email UNIQUE (trip_id, email)
);

CREATE INDEX idx_rally_members_trip ON rally_trip_members(trip_id);
CREATE INDEX idx_rally_members_user ON rally_trip_members(user_id);
CREATE INDEX idx_rally_members_status ON rally_trip_members(status);


-- ── Payments ──────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS rally_payments (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trip_id               UUID NOT NULL REFERENCES rally_trips(id),
    member_id             UUID NOT NULL REFERENCES rally_trip_members(id),
    amount                INT NOT NULL,              -- in cents/paise
    platform_fee          INT NOT NULL DEFAULT 0,    -- in cents/paise
    currency              VARCHAR(3) NOT NULL DEFAULT 'USD',
    gateway               VARCHAR(20) NOT NULL,
    gateway_payment_id    VARCHAR(200),               -- Stripe PaymentIntent ID or Razorpay order_id
    gateway_transfer_id   VARCHAR(200),               -- Stripe Transfer ID or Razorpay settlement_id
    status                VARCHAR(20) NOT NULL DEFAULT 'pending',
    payment_type          VARCHAR(20) NOT NULL DEFAULT 'deposit',
    escrow_released_at    TIMESTAMPTZ,
    refunded_at           TIMESTAMPTZ,
    created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT chk_payment_gateway CHECK (gateway IN ('stripe', 'razorpay')),
    CONSTRAINT chk_payment_status CHECK (status IN ('pending', 'held', 'released', 'refunded', 'failed')),
    CONSTRAINT chk_payment_type CHECK (payment_type IN ('deposit', 'installment', 'final'))
);

CREATE INDEX idx_rally_payments_trip ON rally_payments(trip_id);
CREATE INDEX idx_rally_payments_member ON rally_payments(member_id);
CREATE INDEX idx_rally_payments_status ON rally_payments(status);
CREATE INDEX idx_rally_payments_gateway_id ON rally_payments(gateway_payment_id);


-- ── Price Snapshots (for "cost of delay" tracking) ────────────────────────────

CREATE TABLE IF NOT EXISTS rally_price_snapshots (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trip_id         UUID NOT NULL REFERENCES rally_trips(id) ON DELETE CASCADE,
    origin_airport  VARCHAR(3) NOT NULL,
    estimated_price INT NOT NULL,              -- in cents
    snapshot_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_rally_snapshots_trip ON rally_price_snapshots(trip_id);
CREATE INDEX idx_rally_snapshots_trip_origin ON rally_price_snapshots(trip_id, origin_airport);
