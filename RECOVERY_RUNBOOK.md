# Bronn backup and recovery

A logical backup drill copies a consistent production snapshot into a fresh local
PostgreSQL cluster. It never restores into production. No API or bot is attached
to the restored database, so queued notifications cannot be delivered by the drill.

## Repeat the isolated drill

Use PostgreSQL binaries matching the source major version and a Python environment
with `psycopg` and Pillow. Railway CLI must already be signed into the intended project.

```sh
python scripts/verify_backup_restore.py \
  --project 77b9c3be-c670-4213-b7e3-5cfde3761dea \
  --environment production --service Postgres \
  --pg-bin /path/to/postgresql/bin \
  --report artifacts/operations/backup-restore-YYYY-MM-DD.json
```

The source connection is made inside the PostgreSQL Railway service through SSH;
production database credentials are never copied into the command or report.
The workflow verifies that this database matches the live API service using a
hashed cluster/database identity; it aborts on a mismatch.
`pg_dump` and the source table fingerprints use the same exported read-only
snapshot. Temporary source files are removed after transfer. The local restore
uses a newly initialized cluster, a unique Unix socket and no TCP listener.
Restore stops on the first error, then verifies every public table's row count
and content fingerprint, including all booking fields and photo bytes, then
decodes every restored photo. It also
checks restored ID sequences against existing IDs and counts validated foreign
keys. The local cluster is stopped and removed after the drill.

The backup and source manifest remain in `.backups/<UTC timestamp>/`, with a
0700 directory and 0600 files. This directory is excluded from Git and Docker.
The archive contains personal booking/contact data: restrict access and store
any durable copy in protected backup storage. The sanitized report includes
counts/check outcomes and an archive checksum, never customer rows or photos.
A local archive is a drill artifact, not proof of an off-machine retention policy.

To verify a retained archive later without connecting to Railway:

```sh
python scripts/verify_backup_restore.py \
  --from-backup .backups/<UTC timestamp> \
  --pg-bin /path/to/postgresql/bin \
  --report artifacts/operations/backup-recheck-YYYY-MM-DD.json
```

The archive checksum is checked before restore. `--capture-only` can create a
private archive independently; capture alone never produces a passing recovery
report. This workflow tests logical database data/schema, not cluster roles,
server configuration or a Railway volume replacement.

## Scheduled backups and recovery targets

Railway's volume-backup schedule must be checked separately in Postgres → Backups.
The CLI installed for this project does not expose volume-backup scheduling or
retrieval. A successful fresh logical dump/restore does not prove that an existing
scheduled volume snapshot is restorable. Record the chosen frequency, retention,
last successful backup and a named response owner before marking that requirement
complete. Choose acceptable data-loss and recovery windows from actual operation;
one drill duration does not establish a guaranteed RPO or RTO.

[Railway backup documentation](https://docs.railway.com/volumes/backups) describes
schedules and volume restore behavior. A Railway volume restore stages replacement
of the mounted production volume and redeploys the service; it is not the isolated
drill above.

## Application rollback

Redeploy the last known-good application image separately from database recovery.
For the abuse-protection release, retain its additive `request_limits` table when
rolling back. The previous backend deployment was
`18bbd596-aea9-4892-9aee-1ac9d95cc01e`; the new release is recorded in UPDATE_PLAN.md.
Retest `/health`, authentication and availability after application rollback.
Do not delete additive tables/columns while a service using them is running.

## Real database recovery

Before any production replacement, identify the affected data and backup time,
preserve the current database, and prevent API/bot writes. Restore and verify the
chosen backup in an isolated environment first. Reconcile bookings made after its
snapshot and queued/already-delivered notifications before switching services.
Restart exactly one bot worker only after notification reconciliation, then verify
health, booking availability and real account journeys. Replacing production
requires a separate explicit recovery instruction; the drill grants no such action.
