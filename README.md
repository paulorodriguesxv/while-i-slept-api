# What Happened While I Slept API (MVP)

FastAPI backend for the mobile micro-SaaS app "What Happened While I Slept".

This implementation follows the API contract in `openapi.yaml` and the MVP docs in `docs/`.

## Stack

- Python 3.12
- FastAPI (ASGI; Lambda-compatible, can be wrapped with Mangum later)
- DynamoDB (repository-backed; in-memory backend available for local dev/tests)
- Pydantic v2
- JWT access + refresh tokens
- RevenueCat webhook ingestion for entitlements

## Implemented Public Endpoints

- `POST /auth/oauth/exchange`
- `POST /auth/refresh`
- `GET /me`
- `PUT /me/preferences`
- `POST /me/accept-legal`
- `POST /me/device`
- `GET /briefings/today`
- `GET /briefings/{date}`
- `POST /webhooks/revenuecat`

No other application routes are added.

## Local Run

1. Create a virtual environment and install dependencies.

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
```

2. Configure environment variables.

```bash
cp .env.example .env
```

3. Run the API locally.

```bash
uvicorn while_i_slept_api.main:app --reload
```

## Local Authentication (stub tokens)

For local development, `POST /auth/oauth/exchange` accepts stub provider tokens in this format:

- `stub:<provider_user_id>|<email>|<name>`

Example:

- `stub:google-user-123|user@example.com|Paulo`

If `APP_ALLOW_INSECURE_OAUTH_TOKENS=true`, non-stub tokens are accepted in dev and hashed into a local provider id.

## Storage Backends

### In-memory (default)

- Set `APP_STORAGE_BACKEND=memory`
- Useful for local API iteration and unit tests

### DynamoDB / DynamoDB Local

- Set `APP_STORAGE_BACKEND=dynamodb`
- Configure:
  - `APP_AWS_ENDPOINT_URL`
  - `APP_USERS_TABLE`
  - `APP_DEVICES_TABLE`
  - `APP_BRIEFINGS_TABLE`
  - `APP_AWS_REGION`

Repository implementations keep DynamoDB access isolated from routers.

## Testing

Run unit tests:

```bash
pytest
```

Covered core logic:

- Stub OAuth token validation behavior
- Entitlement gating and premium checks
- Briefing item limits for free vs premium

## Development Environment (AWS)

Use a real AWS development stack managed by Terraform:

```bash
make deploy-dev
```

This workflow creates AWS resources isolated by the `dev` environment prefix (for example, `while-i-slept-dev-*`) so development stays separate from production. It is safe for iterative development and designed to remain low cost with serverless primitives and on-demand DynamoDB billing.

## Notes

- Signup is implicit on first Apple/Google login.
- Onboarding is completed only after preferences and legal acceptance are both recorded.
- `GET /briefings/today` applies free/premium item caps.
- `GET /briefings/{date}` is premium-only.
- Default timezone fallback is `America/Sao_Paulo`.
