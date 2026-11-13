# MAYDON production checklist

Updated November 12, 2026. Production runs on Railway; see README.md for deployment commands.

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

- [ ] Shared rate limits and request-size protection.
- [ ] Backups verified by an isolated restore.
- [ ] Versioned migrations with upgrade tests.
- [ ] External alerts and notification-backlog monitoring.
- [ ] Accurate privacy/support information, retention and deletion process.
- [ ] Real-account end-to-end checks for booking, confirmation, cancellation and reminders.
- [ ] Verify map provider domain restrictions and quota.
- [ ] Require hosted CI before merge; adding a workflow does not enforce this automatically.

## Known boundaries

- Bookings use fixed one-hour slots in Uzbekistan time.
- Payment states do not collect money or record deposit amounts.
- At-least-once notifications may duplicate after a worker crash.
- Telegram sign-in expires after one hour and may require reopening the app.
- Startup applies additive schema changes; versioned migrations are planned.

See UPDATE_PLAN.md for priorities and acceptance criteria.
