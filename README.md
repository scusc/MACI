# Rally — Privacy-First Travel Companion Network

> The verified trust ecosystem for co-traveling, local vibe checks, zero-knowledge privacy, and AI-driven psychological matching.

## What is Rally?

Rally is a privacy-first social travel platform engineered to solve stranger anxiety, room-sharing safety, and single-occupancy "solo tax" friction. Instead of broadcasting user identities on public bulletin boards, Rally shields traveler identities behind dynamically generated pseudonymous profiles until mutual, progressive identity disclosure handshakes occur.

### Core Architecture

```
Frontend (Angular 22) → FastAPI API Gateway → Internal Microservices Network → PostgreSQL (pgvector) + Redis
                                           ├── Auth & KYC Service (JWT, Stripe Identity, Plaid, Trust Passport)
                                           ├── Group & Meetup Service (Swarms, PostGIS Micro-Commitments, Skill Swaps)
                                           ├── Payment & Escrow Service (Stripe Auth Holds & Direct Escrow Charges)
                                           └── Asset & Intelligence Service (Psychometric AI Matching Engine)
```

## Core Features

- **Zero-Knowledge Privacy Vault:** Users browse and match using dynamic avatars and psychometric badges. Real identities and contact details are unmasked only upon mutual double-opt-in handshakes.
- **Psychometric AI Matching:** Matches co-travelers using 5-factor compatibility vectors (social battery, pacing, budget tolerance, spontaneity, conflict resolution style) and 768-dimensional Gemini embeddings.
- **Local Micro-Commitments & Escrow:** Facilitates low-risk local "Vibe Check" meetups secured by Stripe card authorization holds with 4-digit PIN and scanned QR code physical check-ins. Automated penalties slash flakers' Karma score.
- **Pod Barter & Skill-Swapping Economy:** Allows travelers within a trip pod to offer verified skills (drone photography, local language, driving, cooking) to offset shared accommodation and activity expenses.
- **Trust Passport Subscription:** Premium $9.99/month tier offering verified trust badges, priority AI psychometric matching, and identity vault features.

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Angular 22 / RxJS / SCSS (Nx Monorepo) |
| API Gateway | FastAPI Gateway Router |
| Microservices | Python 3.12+ / FastAPI / SQLAlchemy Async |
| Database | PostgreSQL 16 + pgvector |
| Cache & Messaging | Redis 7 / PubSub |
| AI Engine | LiteLLM + Google Gemini (text-embedding-004) |
| Payments & Verification | Stripe (Identity, Connect, PaymentIntents) + Plaid |
| Testing | Playwright E2E & Async QA Live Simulation |

## Microservices Port Allocation

- `api-gateway`: Port `8000` (Unified Public Entrypoint)
- `auth-service`: Internal Port `8000` (`/api/v1/auth`)
- `group-service`: Internal Port `80` (`/api/v1/trips`, `/api/v1/meetups`, `/api/v1/handshake`, `/api/v1/skills`)
- `payment-service`: Internal Port `80` (`/api/v1/payments`, `/api/v1/escrow`)
- `asset-service`: Internal Port `8000` (`/api/v1/assets`, `/api/v1/matching`, `/api/v1/insurance`)

## Quick Start

```bash
# 1. Start infrastructure and microservices
docker-compose up -d --build

# 2. Run Database Migrations
python3 run_migration.py

# 3. Start Angular Frontend
cd frontend
npm start
```
