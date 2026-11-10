# MAYDON launch checklist — November 6 target

## Deploy order
1. Create a managed PostgreSQL database with backups. Do not use ephemeral SQLite for live bookings.
2. Deploy `backend/` as a Render **Web Service**, Docker runtime, health check `/health`. Set `DATABASE_URL`, `BOT_TOKEN`, `ADMIN_TELEGRAM_ID`, `CORS_ORIGINS=https://maydon-bot.vercel.app` as service secrets. Never expose BOT_TOKEN in `VITE_` variables.
3. In Vercel, set Root Directory `miniapp`, Framework `Vite`, Build `npm run build`, Output `dist`, and `VITE_API_URL=https://<backend-domain>`; optionally `VITE_YANDEX_MAPS_KEY` with domain restrictions. Redeploy after changing environment variables.
4. Deploy `bot/` as an **always-on background worker**, Docker runtime, with `BOT_TOKEN` and `MINI_APP_URL=https://maydon-bot.vercel.app`. Only run **one** polling worker for the bot token. Alternatively use a webhook implementation; this starter uses polling.
5. In BotFather, configure menu button URL `https://maydon-bot.vercel.app`.
6. From Telegram, open Mini App and verify live venue list, request booking, owner confirmation, user booking history, cancellation, and admin venue approval.
7. Have real venue owners register their venues. Admin approval required before listing; do not publish invented listings.

## Current limitations — do not claim full production readiness until addressed
- Admin and owner APIs exist, but **there is no admin/owner dashboard UI**. They require a secure authenticated API client or additional UI work.
- There are no automatic owner/user Telegram booking notifications yet. Owners must manually check pending bookings via authenticated API.
- Booking slots are **fixed one-hour slots starting on the hour**; opening-hours validation and more flexible durations are not implemented.
- Photos, favorites, search, payments, venue verification, and polished Figma fidelity are not implemented.
- Add monitoring, rate limiting, abuse prevention, database migrations, backups/restore tests, privacy policy, and incident response before public marketing.
- The React application only displays approved venues. There are no fabricated production venue listings.
- Set the Yandex Maps API key and check allowed domains and quota.
- Telegram WebApp initData expires after one hour in this API; users may need to reopen the Mini App to refresh it.

## Smoke tests
- `GET /health` should return `{ "status": "ok" }`.
- `GET /venues` should return `[]` until approved venues exist.
- `POST /bookings` without `X-Telegram-Init-Data` must return 401.
- `GET /admin/venues` without auth must return 401.
- Try two simultaneous bookings for the same venue and start hour; one should return 409.
- Verify CORS only allows the deployed Mini App origin.
- Check Vercel deployment logs and Render backend logs for errors.
