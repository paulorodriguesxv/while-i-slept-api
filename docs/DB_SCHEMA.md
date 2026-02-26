# DynamoDB Schema (MVP)

This schema prioritizes simplicity and low cost. Start with 3 tables:
- users
- devices
- briefings
Optionally store entitlements in users (simplest) or separate table.

All timestamps should be ISO-8601 strings (UTC) unless stated.

---

## Table: users
Purpose: user profile, onboarding state, preferences, entitlement snapshot.

### Keys
- PK: "USER#<user_id>" (string, e.g., "USER#usr_<uuid>")
- SK: "PROFILE" (constant)

### Attributes (PROFILE item)
- user_id
- provider: "apple" | "google"
- provider_user_id: string (stable sub)
- email: string | null
- name: string | null

Preferences / onboarding:
- lang: "pt" | "en" | null
- sleep_start: "HH:MM" | null
- sleep_end: "HH:MM" | null
- timezone: IANA string | null (default "America/Sao_Paulo" if missing)
- topics: list[string] | null
- accepted_terms_version: string | null
- accepted_terms_at: string | null
- accepted_privacy_version: string | null
- accepted_privacy_at: string | null
- onboarding_completed: bool (default false)

Entitlements:
- premium_active: bool (default false)
- premium_expires_at: string | null
- premium_product_id: string | null
- premium_store: "apple" | "google" | null

Metadata:
- created_at: string
- updated_at: string

### GSI for lookup by provider identity
To find user by provider+sub during login:

- GSI1PK: "IDP#<provider>#<provider_user_id>"
- GSI1SK: "USER#<user_id>"

GSI1 definition:
- GSI1 partition key: GSI1PK
- GSI1 sort key: GSI1SK

On PROFILE item:
- GSI1PK = "IDP#apple#000123..."
- GSI1SK = "USER#usr_..."

---

## Table: devices
Purpose: per-user push tokens, devices.

### Keys
- PK: "USER#<user_id>"
- SK: "DEVICE#<device_id>"

### Attributes
- device_id
- platform: "ios" | "android"
- push_token: string
- app_version: string | null
- updated_at: string
- created_at: string

Query devices by user_id to send push notifications.

---

## Table: briefings
Purpose: store precomputed daily briefings per user or per (lang+window) strategy.
For MVP, simplest is per-user per-date.

### Keys (per-user per-date)
- PK: "USER#<user_id>"
- SK: "BRIEFING#<YYYY-MM-DD>"

### Attributes
- date: "YYYY-MM-DD"
- lang: "pt" | "en"
- window_start: ISO string with timezone offset
- window_end: ISO string with timezone offset
- items: list of story objects (see openapi schema)
- created_at: string
- updated_at: string

### Notes
- If you later want shared briefings (not per user), you can create another PK pattern:
  - PK: "BRIEFING#<YYYY-MM-DD>#<lang>#<tz>#<sleep_start>-<sleep_end>"
  - and store per “segment”.

---

## Webhook idempotency (optional)
If needed, you can add a small table:

Table: webhook_events
- PK: "RC#<event_id>"
- SK: "EVENT"
- processed_at, raw_hash, etc.

But for MVP you can do idempotency by:
- storing last_event_at + last_event_type in user record
- or using conditional updates based on expires_at.
