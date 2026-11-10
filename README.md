# MAYDON — Telegram sports venue booking (launch candidate)

**Status:** development launch candidate, NOT production verified. See [PRODUCTION_CHECKLIST.md](PRODUCTION_CHECKLIST.md).

Monorepo:
- `miniapp/`: React + Vite Telegram Mini App, deployed to Vercel.
- `backend/`: FastAPI + PostgreSQL API, deploy as a Render Web Service.
- `bot/`: aiogram Telegram bot, deploy as an always-on Render background worker.

## Deployment

### Railway

Deploy the API and bot as **two separate services** from this repository. In each
service, open **Settings → Source → Root Directory** and use the settings below:

| Setting | API service | Bot service |
| --- | --- | --- |
| Root Directory | `/backend` | `/bot` |
| Builder | Dockerfile (automatically detected) | Dockerfile (automatically detected) |
| Custom build/start commands | Leave empty; use Dockerfile defaults | Leave empty; use Dockerfile defaults |
| Healthcheck path | `/health` | Leave empty (polling worker) |
| Replicas | 1 initially | Exactly 1 |
| Variables | `DATABASE_URL`, `BOT_TOKEN`, `ADMIN_TELEGRAM_ID`, `CORS_ORIGINS` | `DATABASE_URL`, `BOT_TOKEN`, `ADMIN_TELEGRAM_ID`, `MINI_APP_URL` |

Provision PostgreSQL and set `DATABASE_URL` in both services to the same database.
Deploy the API first so it initializes the database tables. Generate a public
domain for the API and use its HTTPS origin as the miniapp's `VITE_API_URL`.
Set `CORS_ORIGINS` and `MINI_APP_URL` to the deployed miniapp's HTTPS origin.
Deploy the miniapp as a third Railway service using `miniapp/Dockerfile`, with
`VITE_API_URL` set to the API's HTTPS origin before building. The image serves
the built app with nginx on port `8080`; generate its Railway domain targeting
that port. Set the API's `CORS_ORIGINS` and the bot's `MINI_APP_URL` to this web
domain. Run the bot continuously with sleeping/serverless disabled.

Current Railway frontend: https://maydon-web-production-3612.up.railway.app

Current Railway API: https://maydon-production-ba2c.up.railway.app

The frontend was deployed from this checkout using
`railway up miniapp --path-as-root -s Maydon-web --detach`. Repeat that command
after frontend changes, or connect its GitHub source with root `/miniapp` after
pushing the Dockerfile and lockfile.

If deployment says **“Script start.sh not found”** or **“Railpack could not
determine how to build the app”** and lists `backend/`, `bot/`, and `miniapp/`,
Railway is building the repository root. Set the service's Root Directory as
above and redeploy. No `start.sh` is needed: each Python service already has a
Dockerfile that installs its dependencies and starts its process. Adding a
`.dockerignore` only excludes files; it does not fix the incorrect build root.

See [Railway monorepo deployment](https://docs.railway.com/deployments/monorepo)
and [Dockerfile detection](https://docs.railway.com/builds/dockerfiles).

### Render + Vercel

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

## Owner sign-in and pitch submissions

Open [@maydontopbot](https://t.me/maydontopbot), press Start, then use the
MAYDON button. The website's Telegram sign-in link opens this flow; ordinary
browser visits remain guests. `/auth/me` verifies Telegram's signed Mini App
data before displaying an account. Set backend `BOT_USERNAME=maydontopbot`.

Owners use Profile → Maydon egasi paneli (or `/owner` in the bot) to submit
their pitch. Select a point on the map or use GPS, then confirm the location;
there are no manual address or coordinate inputs. Address lookup is automatic
when available; coordinates remain usable if lookup fails. Directions links
use the saved coordinates.

New submissions require 1–5 actual pitch photos. The browser resizes photos;
the API validates and re-encodes them as JPEG, removing image metadata.
Photos are stored in PostgreSQL, survive redeploys, and remain private to the
owner and admin until approval. Admins review photos, location and the owner's
Telegram ID. Photos are supporting evidence, not automatic ownership verification.
Existing listings without photos remain readable.

Deploy the bot as one persistent Railway service, root `bot`, with `BOT_TOKEN`,
`DATABASE_URL`, `ADMIN_TELEGRAM_ID`, and `MINI_APP_URL` set to the Railway frontend.
The worker configures the Telegram menu button on startup. CLI deployment:
`railway up bot --path-as-root -s Maydon-bot --detach`.

Backend checks (use an empty disposable PostgreSQL database): install
`backend/requirements.txt` and `httpx`, then run
`TEST_DATABASE_URL=postgresql://... python -m unittest discover -s backend/tests -v`.
Frontend check: run `npm ci && npm run build` in `miniapp/`.

**Before public launch:** Add owner/admin UI, notification delivery, rate limits, monitoring, opening-hour validation, privacy policy, and run end-to-end tests. A passing Python syntax check is not a production acceptance test.
# Maydon
# Maydon
# Maydon
# Maydon
# Maydon
# Maydon
