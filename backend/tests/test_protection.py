"""Request boundaries plus real PostgreSQL quota concurrency/expiry checks."""
import asyncio
import os
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

from test_owner_flow import main, TestClient, headers
from app.migrate import MIGRATIONS
quota_sql = (MIGRATIONS / "003_protection.sql").read_text()
from app import protection


class BoundaryTests(unittest.TestCase):
    def test_railway_peer_requires_explicit_trust_and_valid_ip(self):
        scope = {'client': ('127.0.0.1', 123)}
        forwarded = {b'x-real-ip': b'203.0.113.7', b'x-forwarded-for': b'198.51.100.1'}
        with patch.dict(os.environ, {'TRUST_RAILWAY_EDGE': 'false', 'RAILWAY_PROJECT_ID': 'test'}):
            self.assertEqual(protection.client_peer(scope, forwarded), '127.0.0.1')
        with patch.dict(os.environ, {'TRUST_RAILWAY_EDGE': 'true', 'RAILWAY_PROJECT_ID': 'test'}):
            self.assertEqual(protection.client_peer(scope, forwarded), '203.0.113.7')
            self.assertEqual(protection.client_peer(scope, {b'x-real-ip': b'bad'}), '127.0.0.1')
            self.assertEqual(protection.client_peer(scope, {b'x-real-ip': b'203.0.113.7, 1.1.1.1'}), '127.0.0.1')
        with patch.dict(os.environ, {'TRUST_RAILWAY_EDGE': 'true', 'RAILWAY_PROJECT_ID': ''}):
            self.assertEqual(protection.client_peer(scope, forwarded), '127.0.0.1')

    def test_chunked_body_rejected_before_app(self):
        reached = []
        async def app(scope, receive, send):
            reached.append(True)
        middleware = protection.ProtectionMiddleware(app, None, None, lambda: False)
        async def run():
            messages = iter([{'type': 'http.request', 'body': b'a' * 4, 'more_body': True},
                             {'type': 'http.request', 'body': b'b' * 4, 'more_body': False}])
            output = []
            async def receive():
                return next(messages)
            async def send(message):
                output.append(message)
            with patch.object(protection, 'MAX_BODY', 6):
                await middleware({'type': 'http', 'method': 'POST', 'path': '/bookings', 'headers': []}, receive, send)
            self.assertEqual(output[0]['status'], 413)
            self.assertFalse(reached)
        asyncio.run(run())

    def test_declared_size_rejected_on_all_writes(self):
        response = TestClient(main.app).post('/bookings', headers={'content-length': '7500001'}, content=b'{}')
        self.assertEqual(response.status_code, 413)

    def test_quota_response_and_verified_identity(self):
        with patch.object(main, 'DATABASE_URL', 'configured'), patch.object(protection, 'consume', return_value=12) as consume:
            response = TestClient(main.app).post('/bookings', headers={**headers(712), 'X-Forwarded-For': 'fake'}, json={})
        self.assertEqual(response.status_code, 429)
        self.assertEqual(response.headers['retry-after'], '12')
        self.assertEqual(response.headers['cache-control'], 'no-store')
        self.assertEqual(consume.call_args.args[1:], ('write', 'user:712'))

    def test_failed_auth_ignores_forwarded_headers(self):
        with patch.object(main, 'DATABASE_URL', 'configured'), patch.object(protection, 'consume', return_value=10) as consume:
            TestClient(main.app).get('/auth/me', headers={'X-Telegram-Init-Data': 'forged', 'X-Forwarded-For': 'fake'})
        self.assertEqual(consume.call_args.args[1:], ('auth', 'peer:testclient'))

    def test_calendar_reads_have_separate_budget(self):
        with patch.object(main, 'DATABASE_URL', 'configured'), patch.object(protection, 'consume', return_value=0) as consume:
            response = TestClient(main.app).get('/auth/config', headers=headers(712))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(consume.call_args.args[1:], ('read', 'user:712'))


@unittest.skipUnless(os.getenv('TEST_DATABASE_URL'), 'Disposable PostgreSQL required')
class SharedQuotaTests(unittest.TestCase):
    def setUp(self):
        with main.db() as conn:
            conn.execute(quota_sql)
            conn.execute('TRUNCATE request_limits')

    def test_concurrent_requests_and_account_isolation(self):
        with patch.dict(protection.POLICIES, {'write': (5, 60)}):
            with ThreadPoolExecutor(max_workers=8) as pool:
                results = list(pool.map(lambda _: protection.consume(main.db, 'write', 'user:a'), range(20)))
            self.assertEqual(results.count(0), 5)
            self.assertTrue(all(1 <= value <= 60 for value in results if value))
            self.assertEqual(protection.consume(main.db, 'write', 'user:b'), 0)
            self.assertEqual(protection.consume(main.db, 'read', 'user:a'), 0)

    def test_expired_window_resets_and_old_subjects_are_cleaned(self):
        with patch.dict(protection.POLICIES, {'write': (1, 60)}):
            self.assertEqual(protection.consume(main.db, 'write', 'user:a'), 0)
            self.assertGreater(protection.consume(main.db, 'write', 'user:a'), 0)
            with main.db() as conn:
                conn.execute("UPDATE request_limits SET expires_at=NOW()-interval '1 second'")
            self.assertEqual(protection.consume(main.db, 'write', 'user:a'), 0)
            with main.db() as conn:
                self.assertEqual(conn.execute('SELECT hits FROM request_limits').fetchone()['hits'], 1)
