import os
import unittest
from uuid import uuid4

from test_owner_flow import main
from app.migrate import MIGRATIONS, apply_migrations


@unittest.skipUnless(os.getenv("TEST_DATABASE_URL"), "Disposable PostgreSQL required")
class MigrationTests(unittest.TestCase):
    def test_legacy_upgrade_and_repeat_keep_data_and_history(self):
        with main.db() as conn:
            schema = "migration_test_" + uuid4().hex
            conn.execute(f"CREATE SCHEMA {schema}")
            conn.execute(f"SET LOCAL search_path TO {schema}")
            for path in sorted(MIGRATIONS.glob("00[123]_*.sql")):
                conn.execute(path.read_text())
            conn.execute("INSERT INTO telegram_profiles(telegram_id,first_name) VALUES (12,'Pilot')")
            apply_migrations(conn)
            history = conn.execute("SELECT * FROM schema_migrations ORDER BY version").fetchall()
            self.assertGreaterEqual(len(history), 3)
            apply_migrations(conn)
            self.assertEqual(conn.execute("SELECT * FROM schema_migrations ORDER BY version").fetchall(), history)
            self.assertEqual(conn.execute("SELECT first_name FROM telegram_profiles WHERE telegram_id=12").fetchone()['first_name'], 'Pilot')
            conn.rollback()
