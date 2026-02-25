# Architecture — AWS Serverless + FastAPI (MVP)

## Goals
- Minimize infra overhead and cost at low traffic.
- Keep request path fast: app reads precomputed briefings.
- Make auth + subscription gating correct and testable.

## High-level components
1) Mobile App (Expo/React Native)
   - Social login (Apple/Google) -> sends id_token to backend
   - RevenueCat SDK for purchase + entitlement
   - Calls backend with Bearer JWT (access_token)

2) Backend API (FastAPI)
   - Runs as ASGI
   - Deployed to AWS Lambda behind API Gateway HTTP API (later)
   - Issues JWT + refresh tokens
   - Stores users, devices, entitlements, briefings

3) Scheduled Workers (optional for MVP but planned)
   - EventBridge Scheduler triggers ingestion/build pipeline
   - Workers can be separate Lambdas or same codebase with different handlers
   - Writes precomputed briefings into DB

4) RevenueCat Webhook Receiver
   - POST /webhooks/revenuecat
   - Updates entitlement state (premium_active, expires_at, product_id, store)

## Runtime flow — Auth
- App gets provider id_token (Apple/Google).
- App calls POST /auth/oauth/exchange.
- Backend validates id_token (signature+claims in prod; stub allowed in dev).
- Backend creates user if missing (implicit signup).
- Backend returns:
  - access_token (JWT)
  - refresh_token
  - me flags (onboarding + entitlement)

## Runtime flow — Onboarding
- App reads GET /me.
- If onboarding not completed:
  - PUT /me/preferences
  - POST /me/accept-legal
- Backend updates user record and sets onboarding_completed when rules satisfied.

## Runtime flow — Briefing consumption
- App calls GET /briefings/today with Bearer token.
- Backend loads user preferences + entitlement.
- Backend returns:
  - window (computed based on user sleep window + timezone)
  - items list (limited by free/premium)
  - limits info (max_items, is_premium)

## Runtime flow — Paywall and entitlement
- App purchase handled by RevenueCat SDK.
- RevenueCat sends webhook events to backend.
- Backend stores entitlement state:
  - premium_active
  - expires_at
  - product_id
  - store
- Backend uses stored state to gate:
  - /briefings/{date} (premium-only)
  - limit counts for /briefings/today

## Deployment target (later)
- API Gateway (HTTP API) -> Lambda (FastAPI via Mangum)
- DynamoDB tables
- CloudWatch logs
- Optional:
  - S3 for raw ingestion payloads
  - SQS for queue-based pipeline
  - EventBridge Scheduler for recurring jobs

## Local development
- Run FastAPI with uvicorn locally.
- Use DynamoDB Local via docker-compose.
- Provide .env.example for configuration.

## Security basics
- JWT access tokens (short TTL).
- Refresh tokens (longer TTL, revocable if stored server-side).
- Webhook endpoint protected by shared secret header.
- Never use email as primary identity key.

## Observability
- Structured logs (JSON recommended).
- Correlation id per request (optional).