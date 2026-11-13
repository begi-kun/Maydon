"""Health probes must fail predictably without leaking database credentials."""
import os
import unittest
from unittest.mock import patch

import psycopg
from test_owner_flow import main, TestClient


class HealthFailureTests(unittest.TestCase):
    def test_missing_database_returns_uncacheable_503(self):
        with patch.object(main, 'DATABASE_URL', ''):
            response = TestClient(main.app).get('/health')
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json(), {'status': 'unavailable'})
        self.assertEqual(response.headers['cache-control'], 'no-store')

    def test_database_errors_do_not_leak_details(self):
        client = TestClient(main.app)
        for error in (psycopg.OperationalError('password=secret host=private'),
                      psycopg.errors.QueryCanceled('internal query details')):
            with self.subTest(error=type(error).__name__), \
                    patch.object(main, 'DATABASE_URL', 'postgresql://test'), \
                    patch.object(main.psycopg, 'connect', side_effect=error):
                response = client.get('/health')
            self.assertEqual(response.status_code, 503)
            self.assertEqual(response.json(), {'status': 'unavailable'})
            self.assertEqual(response.headers['cache-control'], 'no-store')


@unittest.skipUnless(os.getenv('TEST_DATABASE_URL'), 'Disposable PostgreSQL required')
class HealthIntegrationTests(unittest.TestCase):
    def test_database_probe_succeeds(self):
        response = TestClient(main.app).get('/health')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'status': 'ok'})
        self.assertEqual(response.headers['cache-control'], 'no-store')
