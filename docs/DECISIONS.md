# Decisions — What Happened While I Slept (Backend + MVP)

## Product framing
- Product is a micro-SaaS B2C focused on daily news briefing: “what happened while I slept”.
- MVP goal: validate habit + paid conversion with minimal scope.

## Platforms
- Mobile app only for MVP.
- iOS + Android from day 1.

## Mobile stack
- React Native + Expo
- TypeScript
- RevenueCat for subscriptions/paywall entitlements.

## Backend stack
- Python 3.13 + FastAPI
- AWS serverless target:
  - API Gateway (HTTP API) -> AWS Lambda
  - EventBridge Scheduler for cron triggers
  - DynamoDB as primary database
  - S3 optional for raw payloads/logs
  - SQS optional for decoupling pipeline stages
- Local development must work without AWS (DynamoDB Local recommended).

## Authentication (no anonymous)
- No anonymous login.
- Signup is implicit via social login:
  - Sign in with Apple (iOS)
  - Sign in with Google (Android)
- Backend validates provider id_token and issues its own JWT:
  - access_token (short-lived)
  - refresh_token (longer-lived)
- User primary identity key:
  - provider + provider_user_id (NOT email).
  - Email may be missing or masked (Apple relay).

## Onboarding
- After first login, user must complete onboarding:
  - language: pt/en
  - sleep window: start/end + timezone (IANA)
  - accept legal (terms + privacy)
- `onboarding_completed` becomes true only when preferences AND legal acceptance are recorded.

## Core content model
- Briefing is pre-computed server-side.
- App consumes `GET /briefings/today` (fast; no heavy processing on request path).

## Free vs Premium (MVP rules)
- Free:
  - `GET /briefings/today` returns up to 5 stories.
  - No history (or history blocked).
- Premium:
  - `GET /briefings/today` returns more items (e.g., 10–15).
  - `GET /briefings/{date}` allowed (history).

## Subscriptions / Billing
- Purchases are native:
  - Apple In-App Purchase
  - Google Play Billing
- RevenueCat is the subscription hub:
  - app uses RevenueCat SDK for purchase + entitlement
  - backend receives RevenueCat webhooks and stores entitlement state
- Backend enforces premium gates using stored entitlement state.

## MVP API endpoints (source of truth)
- POST /auth/oauth/exchange
- POST /auth/refresh
- GET /me
- PUT /me/preferences
- POST /me/accept-legal
- POST /me/device
- GET /briefings/today
- GET /briefings/{date}
- POST /webhooks/revenuecat

No other public endpoints should be added without updating this doc and openapi.yaml.