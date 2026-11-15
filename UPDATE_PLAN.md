# MAYDON next updates

Updated November 12, 2026. Priorities reflect risk to real bookings, then owner/customer value.

## 1. Reliable validation and deployment — implemented locally

- GitHub Actions runs backend tests with fresh PostgreSQL and builds the frontend on pull requests, main/owner pushes and manual runs. No production secrets are required.
- `/health` returns uncached 503 responses when the database is unavailable. Connection and query timeouts are explicit; public errors do not reveal database credentials.
- `python3 scripts/check_live.py` checks database/API health, owner endpoints, owner/admin authentication, frontend assets and the configured API origin. It changes no bookings and sends no messages.
- Validation: 34 backend tests passed; frontend build passed; the live checker passed against the existing deployment.
- Remaining release steps: push the workflow, verify hosted CI, deploy the backend change and rerun the live checker. CI has not yet run on GitHub. Workflow files alone do not enforce branch protection or gate deployments.

## 2. Abuse protection

- Add shared per-account write limits for bookings, venue/photo submissions and owner actions, plus separate public-read and failed-authentication limits.
- Return 429 with a retry interval and a clear Uzbek message. Do not trust arbitrary forwarded IP headers.
- Test account isolation, concurrency, expiry and normal calendar usage. Limits must work across replicas.
- Enforce request-size limits before photo decoding.

## 3. Recovery and monitoring

- Verify backups by restoring into an isolated database and checking booking counts and photos.
- Introduce versioned migrations, testing upgrades from the current schema and repeat execution.
- Configure external uptime and notification-backlog alerts with an identified response owner.
- Document application rollback separately from database recovery.

## 4. Customer trust and support

- Add privacy/support information reflecting actual Telegram identity, phone, photo and booking-data usage.
- Establish the real support contact, retention periods and deletion process before publishing promises.
- Explain cancellation rules and the distinction between payment status and money collection.
- Verify real Telegram customer/owner journeys, reminder delivery and expired-login recovery.

## 5. Booking improvements

- Add recurring owner blocks and multi-hour bookings after defining overlap, overnight-hours and partial-cancellation rules.
- Add booking/payment exports with owner isolation and spreadsheet-formula escaping.
- Add customer favorites and improved venue discovery after operational work.

Actual payment collection needs a separate integration covering provider onboarding, callbacks, reconciliation and refunds.
