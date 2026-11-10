# MAYDON — Telegram sports venue booking (launch candidate)

**Status:** development launch candidate, NOT production verified. See [PRODUCTION_CHECKLIST.md](PRODUCTION_CHECKLIST.md).

Monorepo:
- `miniapp/`: React + Vite Telegram Mini App, deployed to Vercel.
- `backend/`: FastAPI + PostgreSQL API, deploy as a Render Web Service.
- `bot/`: aiogram Telegram bot, deploy as an always-on Render background worker.

## Deployment
1. Push files to your own GitHub repo (do not commit `.env` or credentials).
2. Provision managed PostgreSQL. Configure backend Render root `backend`, Docker runtime, health check `/health`, and secrets `DATABASE_URL`, `BOT_TOKEN`, `ADMIN_TELEGRAM_ID`, `CORS_ORIGINS`.
3. Configure Vercel root `miniapp`, framework Vite, build `npm run build`, output `dist`; set `VITE_API_URL` to the HTTPS backend origin. Optional `VITE_YANDEX_MAPS_KEY` must be restricted by domain.
4. Configure bot Render background worker root `bot`, Docker runtime, secrets `BOT_TOKEN`, `MINI_APP_URL`.
5. Test using a real Telegram session; API rejects unverified user IDs and accepts signed Telegram WebApp initData.

## Booking rules
- One-hour slots starting on the hour, up to 60 days ahead.
- Pending or confirmed bookings block duplicate slots.
- Owners can confirm/reject; users can cancel pending requests.
- Admin approval required before venue appears publicly.

**Before public launch:** Add owner/admin UI, notification delivery, rate limits, monitoring, opening-hour validation, privacy policy, and run end-to-end tests. A passing Python syntax check is not a production acceptance test.
# Maydon
# Maydon
# Maydon
# Maydon
