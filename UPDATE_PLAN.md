# MAYDON next updates

Updated November 12, 2026. Priorities reflect risk to real bookings, then owner/customer value.

## 1. Reliable validation and deployment — implemented locally

- GitHub Actions runs backend tests with fresh PostgreSQL and builds the frontend on pull requests, main/owner pushes and manual runs. No production secrets are required.
- `/health` returns uncached 503 responses when the database is unavailable. Connection and query timeouts are explicit; public errors do not reveal database credentials.
- `python3 scripts/check_live.py` checks database/API health, owner endpoints, owner/admin authentication, frontend assets and the configured API origin. It changes no bookings and sends no messages.
- Validation: 34 backend tests passed; frontend build passed; the live checker passed against the existing deployment.
- Remaining release steps: push the workflow, verify hosted CI, deploy the backend change and rerun the live checker. CI has not yet run on GitHub. Workflow files alone do not enforce branch protection or gate deployments.

## 2. Abuse protection — deployed and live-checked (November 18, 2026)

- PostgreSQL quotas share account write limits across replicas, with separate read, failed-authentication, public telemetry and venue-submission budgets.
- HTTP 429 includes an Uzbek message and a browser-readable retry interval. Application code ignores forwarding headers by default; Railway explicitly trusts its edge X-Real-IP header.
- All bodies, including chunked uploads, are capped before parsing/photo decoding. Quota storage failures return 503.
- Validation: all 74 backend tests passed against disposable PostgreSQL, including concurrency, account isolation, expiry, streamed size limits and explicit Railway edge trust.
- Deployed backend `7190ecce-697b-4ee4-bada-dbd355f1b31e`. Live checks passed for health/database, owner/admin authentication, frontend compatibility, public availability, 413 body rejection and 429 with Uzbek retry guidance/CORS. Changing spoofed forwarding headers did not evade the quota; ordinary guest reads stayed available. Runtime confirmed edge trust, disabled implicit Uvicorn proxy parsing and the shared quota table. Evidence: `artifacts/operations/abuse-protection-2026-11-18.json`.
- Railway production explicitly trusts its public edge X-Real-IP header; private services in this environment remain within the trust boundary. See README for allowances and rollback. Real Telegram phone journeys and the other operational requirements below remain outstanding.

## 3. Recovery and monitoring — logical restore drill passed (November 19, 2026)

- Completed a consistent-snapshot logical backup and isolated PostgreSQL 18.6 restore. All 17 public table counts/content fingerprints matched, including 12 bookings and 8 photos; all photos decoded, foreign keys and ID sequences passed. Source database identity matches the live API. Private backup archives remain in Git-ignored `.backups/`; no production tables were changed and no API/bot was attached to the restore.
- Repeatable tool: `scripts/verify_backup_restore.py`; runbook: `RECOVERY_RUNBOOK.md`; sanitized evidence: `artifacts/operations/backup-restore-2026-11-19.json`.
- Scheduled Railway volume-backup frequency/retention and a scheduled-snapshot restore remain unverified. A fresh logical drill does not establish an RPO/RTO or off-machine backup policy.
- Introduce versioned migrations, testing upgrades from the current schema and repeat execution.
- Configure external uptime and notification-backlog alerts with an identified response owner.
- Application rollback is documented separately from database recovery in RECOVERY_RUNBOOK.md.

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
