# Credentials Matrix

This maps the v2 blueprint credentials that must be configured before paper/live operation.

## Owner Login

| Field | Required | Used For | Notes |
|---|---:|---|---|
| Owner email | Yes | Web UI login | Stored in `users.email`. |
| Owner password | Yes | Web UI login | Hash with Argon2id only. Never store plaintext. |
| TOTP secret/code | Yes | Mandatory 2FA | Show provisioning URI/QR during setup only. |

## Bybit

| Field | Required | Used For | Notes |
|---|---:|---|---|
| `BYBIT_API_KEY` | Yes for paper/live | Exchange account/trading API | Must be trade-only. |
| `BYBIT_API_SECRET` | Yes for paper/live | Request signing | Never display full value after save. |
| `BYBIT_TESTNET` | Yes | Paper/test environment switch | `true` for testnet or demo-key workflows. |
| `BYBIT_API_BASE_URL` | Optional | Override mainnet/testnet API endpoint | Leave empty unless routing through a custom endpoint. |
| `BYBIT_ACCOUNT_TYPE` | Yes | Venue account mode | Use `UNIFIED`. |
| `BYBIT_WITHDRAWAL_ENABLED` | Yes before live | Operator safety acknowledgement | Must remain `false`. |
| `EXECUTION_LIVE_TRANSPORT_ENABLED` | Yes before venue order tests | Final execution safety switch | Keep `false` while validating dashboard/runtime only. |
| `BYBIT_VIP_TIER` | Yes | Fee model and net PnL | Default `0`. |
| `BYBIT_WHITELISTED_IP` | Yes before live | Bybit IP whitelist | Current VPS IP: `103.150.197.225`. |

Hard rules from blueprint:

- Withdrawal permission must be disabled.
- IP restriction must be enabled.
- Unified Trading Account should be enabled.
- Bot should refuse startup if withdrawal is enabled or IP restriction is missing.
- For demo testing, use matching demo/testnet credentials and set `BYBIT_TESTNET=true`.
- Do not set `EXECUTION_LIVE_TRANSPORT_ENABLED=true` until the runtime panel shows the account is ready and you intend to test actual venue order placement.

Current runtime note:

- the app is already able to read Bybit runtime readiness and reflect it in the dashboard/operator surfaces
- market-data stream is now maintained inside the app lifecycle, not only via request-time fallback

## AI / OpenRouter

| Field | Required | Used For | Notes |
|---|---:|---|---|
| `OPENROUTER_API_KEY` | Phase 4 | AI Analyst | AI cannot execute orders or modify live config. |
| `AI_PRIMARY_MODEL` | Phase 4 | Analyst reasoning | Current recommended default: `openai/gpt-4.1-mini`. |
| `AI_FAST_MODEL` | Phase 4 | Fast classification | Current recommended default: `google/gemini-2.5-flash-lite`. |
| `AI_HEAVY_MODEL` | Phase 4 | Heavy analysis | Current recommended default: `google/gemini-2.5-flash`. |
| `AI_MAX_COST_USD_PER_DAY` | Phase 4 | Cost guardrail | Current recommended default `$3.00`. |

## Notifications

| Field | Required | Used For | Notes |
|---|---:|---|---|
| `TELEGRAM_BOT_TOKEN` | Phase 1+ | Primary alerts | Critical alerts need sound/repeat until ack. |
| `TELEGRAM_CHAT_ID` | Phase 1+ | Alert routing | Use owner chat/group ID. |
| `SMTP_HOST` | Phase 4+ | Email digest/critical backup | Optional until email notifications. |
| `SMTP_USER` | Phase 4+ | SMTP auth | Secret. |
| `SMTP_PASSWORD` | Phase 4+ | SMTP auth | Secret. |
| `EMAIL_FROM` | Phase 4+ | Sender address | Example: `alerts@domain.com`. |
| `EMAIL_TO` | Phase 4+ | Recipient address | Owner email. |

## Monitoring / Recovery

| Field | Required | Used For | Notes |
|---|---:|---|---|
| `HEALTHCHECK_PING_URL` | Before live | External heartbeat | Healthchecks.io ping every 30s. |
| `DEAD_MAN_SWITCH_WEBHOOK` | Before live | Independent flatten trigger | Must be deployed separately from main bot. |
| `PROMETHEUS_ENABLED` | Yes | Metrics endpoint | Default `true`. |

## Infrastructure Secrets

| Field | Required | Used For | Notes |
|---|---:|---|---|
| `POSTGRES_PASSWORD` | Yes | Database auth | Change before production. |
| `DATABASE_URL` | Yes | Backend DB connection | Async SQLAlchemy URL. |
| `REDIS_PASSWORD` | Production | Redis auth/session/rate limit | Development can run without password. |
| `REDIS_URL` | Yes | Redis connection | Include password in production. |
| `JWT_SECRET` | Yes | API auth tokens | Generate with `openssl rand -hex 64`. |

## Storage Rule

Settings UI must not persist secrets to browser storage. The current v2 foundation saves allowed settings server-side in `app_settings`, encrypts values before database persistence, and only returns masked values for secret fields such as `sk_****abcd`.

Longer-term production hardening can replace or wrap this storage with Vault, Docker secrets, or age-encrypted sealed config.
