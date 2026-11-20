# Bronn production checklist

Updated November 19, 2026. Production runs on Railway; see README.md for deployment commands.

## Shipped

- [x] Customer bookings, verified Telegram contact, cancellation and owner decisions.
- [x] Owner daily/weekly schedule, manual bookings, blocked hours and opening-hour enforcement.
- [x] Searchable history, payment-status tracking, overview and analytics.
- [x] Venue editing/photos and admin moderation, suspension and booking management.
- [x] Telegram notifications and reminders; manual bookings excluded from customer reminders.
- [x] Owner frontend and bot deployed; backend deployed from the merged owner commit.

## Every release

- [ ] Run backend tests against fresh disposable PostgreSQL, never production.
- [ ] Run `npm ci` and `npm run build` in `miniapp/`.
- [ ] Review schema compatibility; deploy backend before dependent bot/frontend changes.
- [ ] Verify successful Railway deployments and startup logs. Keep exactly one bot polling worker.
- [ ] Run `python3 scripts/check_live.py`. This checks public health/assets and auth boundaries, not a signed Telegram journey.
- [ ] Test changed user flows in Telegram, mobile layout and account isolation.

## Remaining before wider public promotion

- [x] Shared rate limits and request-size protection deployed and live-checked.
- [x] Fresh logical backup verified by an isolated PostgreSQL 18.6 restore: all 17 tables, 12 bookings and 8 photos matched; photos decoded. See RECOVERY_RUNBOOK.md and the November 19 recovery evidence.
- [ ] Verify scheduled Railway backup frequency/retention and recovery from an existing scheduled snapshot; name the response owner.
- [x] Versioned SQL migrations with legacy upgrade and repeat-start tests.
- [ ] External alerts and notification-backlog monitoring.
- [ ] Accurate privacy/support information, retention and deletion process.
- [ ] Real-account end-to-end checks for booking, confirmation, cancellation and reminders.
- [ ] Verify map provider domain restrictions and quota.
- [x] GitHub main branch protection requires both frontend and backend checks (verified November 20).

## Known boundaries

- Bookings use fixed one-hour slots in Uzbekistan time.
- Payment states do not collect money or record deposit amounts.
- At-least-once notifications may duplicate after a worker crash.
- Telegram sign-in expires after one hour and may require reopening the app.
- Startup applies ordered SQL migrations in a single transaction. Append new numbered files in backend/app/migrations and preserve previously applied files.

See UPDATE_PLAN.md for priorities and acceptance criteria.
