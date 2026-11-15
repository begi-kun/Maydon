# Design release evidence

Archived evidence from the 2026-11-15 design release. These files record earlier
checks; they do not claim that the current branch was freshly tested.

- `check-results.json`: local browser checks with controlled API/Telegram doubles.
- `real-api-results.json`: local real API checks with a simulated Telegram bridge.
- `live-results.json`: public production browser checks without mutations.
- `accessibility-audit.json`: automated accessibility results after fixes.
- `accessibility-before-fixes.json`: historical findings before fixes.
- `backend-test-results.json`: backend results for source commit `2ae3d59`.
- `deployment.json`: deployment identifiers and recorded verification limits.
- `release-source.json`: isolated release source paths and file hashes.
- `design-release.patch`: historical patch against `2ae3d59`; do not apply it to
  current source without review. Subsequent product work is already committed.
- PNG files: before/after, responsive, loading/error, booking, owner, and live
  screenshots captured during these checks.

Physical Telegram device and manual screen reader verification were not performed.
