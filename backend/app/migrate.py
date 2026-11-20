"""Apply append-only SQL migrations inside the caller's transaction."""
from hashlib import sha256
from pathlib import Path

MIGRATIONS = Path(__file__).with_name("migrations")


def apply_migrations(conn):
    conn.execute("SELECT pg_advisory_xact_lock(341480, 1)")
    conn.execute("""CREATE TABLE IF NOT EXISTS schema_migrations (
        version INTEGER PRIMARY KEY, filename TEXT NOT NULL, digest TEXT NOT NULL,
        applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW())""")
    rows = conn.execute("SELECT version, filename, digest FROM schema_migrations ORDER BY version").fetchall()
    files = sorted(MIGRATIONS.glob("*.sql"))
    if not files or len(rows) > len(files):
        raise RuntimeError("Database migration history does not match this release")
    for version, path in enumerate(files, start=1):
        if not path.name.startswith(f"{version:03}_"):
            raise RuntimeError(f"Unexpected migration sequence at {path.name}")
        contents = path.read_bytes()
        digest = sha256(contents).hexdigest()
        if version <= len(rows):
            row = rows[version - 1]
            if (row['version'], row['filename'], row['digest']) != (version, path.name, digest):
                raise RuntimeError(f"Migration history mismatch at {path.name}")
            continue
        conn.execute(contents.decode("utf-8"))
        conn.execute("INSERT INTO schema_migrations(version, filename, digest) VALUES (%s,%s,%s)",
                     (version, path.name, digest))
