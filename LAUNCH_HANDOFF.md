# MAYDON — deployment handoff (November 5, 2026)

## What is implemented
- React Telegram Mini App: venue discovery, sport filters, map pins, booking requests, booking history/cancellation, owner venue submission and booking decisions, admin venue approval.
- FastAPI: Telegram signed initData validation, PostgreSQL persistence, venue and booking permissions, transaction-serialized slot creation plus a partial unique index.
- Telegram bot: `/start` opens Mini App, `/owner` lets owners confirm/reject pending bookings, `/admin` lets the designated admin approve/reject venues. Background loop sends queued notifications. **Run exactly one bot worker**.

## What you must supply (never send secrets in chat)
1. Telegram BotFather token (private; put in hosting secrets).
2. Your numeric Telegram ID as ADMIN_TELEGRAM_ID.
3. Render PostgreSQL DATABASE_URL (private).
4. A Yandex Maps JavaScript API key restricted to your Vercel domain (this key is browser-visible).
5. Real venue names, addresses, coordinates, phone numbers, prices, and owner Telegram IDs; venue owners must start the bot to receive notifications.

## Deploy order
1. Push the package contents into your existing GitHub repository. Check `.env` is NOT tracked: `git ls-files .env`. If tracked, remove from Git index (`git rm --cached .env`) and rotate any exposed secrets. Do not commit `.env`.
2. Create PostgreSQL in Render. Save its connection string as DATABASE_URL in **both** services.
3. Create Render Web Service from GitHub. Root directory `backend`; runtime Docker (uses `backend/Dockerfile`). Set `BOT_TOKEN`, `DATABASE_URL`, `ADMIN_TELEGRAM_ID`, `CORS_ORIGINS=https://maydon-bot.vercel.app`. Set health check path `/health`. Wait for `/health` to return `{ "status": "ok" }`.
4. In Vercel project set Root Directory `miniapp`, framework Vite, build `npm run build`, output `dist`. Set `VITE_API_URL=https://YOUR-API.onrender.com`, `VITE_YANDEX_MAPS_KEY=YOUR_PUBLIC_MAPS_KEY`. Redeploy. Never place BOT_TOKEN or DATABASE_URL in Vercel's VITE_ variables.
5. Create a Render **Background Worker** from the same repository, root directory `bot`, Docker runtime (uses `bot/Dockerfile`). Set `BOT_TOKEN`, `DATABASE_URL`, `MINI_APP_URL=https://maydon-bot.vercel.app`, `ADMIN_TELEGRAM_ID`. Start **one** worker only; webhook and polling must not both run.
6. In BotFather configure menu button `Open MAYDON` to `https://maydon-bot.vercel.app/`.
7. Open Mini App from Telegram, not Chrome, to test authenticated features. Admin creates/approves venue through the owner form or `/admin`; owner must open the bot and run `/owner` to review booking requests.

## Launch acceptance checks (must pass before accepting real bookings)
- `GET /health` succeeds from outside hosting; Mini App loads without server error.
- On a real Telegram account, submit a venue; only the configured admin can approve it; public `/venues` only shows approved venues.
- Submit a future hour booking; owner gets a bot message and can approve; customer gets confirmation; bookings page shows updated status after refresh.
- Two accounts attempting the same venue/hour cannot both reserve it (second request returns 409).
- Unauthorized calls without signed initData to protected endpoints return 401; non-admin admin endpoint returns 403.
- Verify browser console, CORS, mobile layout, Yandex map key, time zones, notification delivery, owner permissions, cancellations.
- Verify database backups, monitoring, privacy/terms, owner permission to list venues, and support contact.

## Important limitations
- This is a **release candidate, not a verified production deployment**. No live hosting or credentials are accessible to this package.
- Frontend production build and live database integration have NOT been confirmed in this environment. Test on your Mac/CI before deploying.
- Notification worker uses basic polling and at-least-once delivery; in rare crashes a notification may be duplicated. A failed Telegram message (user has not started bot) will retry.
- Current reservations are fixed one-hour blocks, with hourly UTC starts. Before a public launch, verify that displayed local time and operating hours match venue expectations in Namangan (UTC+5). No payments or image uploads are implemented.
- Deploy only after all acceptance checks pass. Do not promise a next-day launch if they fail.
