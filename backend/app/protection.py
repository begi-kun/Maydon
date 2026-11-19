"""Shared fixed-window quotas and bounded request bodies."""
import hashlib
import math
import logging
import os
import ipaddress

from fastapi import HTTPException
from starlette.concurrency import run_in_threadpool
from starlette.responses import JSONResponse

SCHEMA = '''
CREATE TABLE IF NOT EXISTS request_limits (
 scope TEXT NOT NULL, subject TEXT NOT NULL, hits INTEGER NOT NULL,
 expires_at TIMESTAMPTZ NOT NULL, PRIMARY KEY(scope,subject));
CREATE INDEX IF NOT EXISTS request_limits_expiry ON request_limits(expires_at);
'''
# Reads accommodate calendars and photo galleries; writes share an account budget.
POLICIES = {'read': (600, 60), 'auth': (20, 60),
            'write': (60, 60), 'public_write': (120, 60), 'submission': (10, 600)}
MAX_BODY = 7_500_000


def client_peer(scope, headers):
    peer = str((scope.get('client') or ('unknown',))[0])
    # Opt-in only for a Railway environment whose public HTTP edge is the sole
    # untrusted ingress. Private project services remain inside this trust boundary.
    if os.getenv('TRUST_RAILWAY_EDGE') == 'true' and os.getenv('RAILWAY_PROJECT_ID'):
        raw = headers.get(b'x-real-ip', b'').decode('ascii', errors='replace')
        try:
            return str(ipaddress.ip_address(raw))
        except ValueError:
            pass
    return peer


def consume(db, scope, subject):
    limit, seconds = POLICIES[scope]
    # Hash peer addresses/account IDs; no raw identity is stored in this table.
    subject = hashlib.sha256(subject.encode()).hexdigest()
    with db() as conn:
        row = conn.execute('''
            INSERT INTO request_limits(scope,subject,hits,expires_at)
            VALUES (%s,%s,1,clock_timestamp() + %s * interval '1 second')
            ON CONFLICT (scope,subject) DO UPDATE SET
              hits=CASE WHEN request_limits.expires_at <= clock_timestamp()
                        THEN 1 ELSE request_limits.hits + 1 END,
              expires_at=CASE WHEN request_limits.expires_at <= clock_timestamp()
                        THEN EXCLUDED.expires_at ELSE request_limits.expires_at END
            RETURNING hits, EXTRACT(EPOCH FROM (expires_at-clock_timestamp())) AS remaining
        ''', (scope, subject, seconds)).fetchone()
        # Bound cleanup work; serialize with active upserts through PostgreSQL locks.
        conn.execute('''DELETE FROM request_limits WHERE (scope,subject) IN (
            SELECT scope,subject FROM request_limits WHERE expires_at < clock_timestamp()
            ORDER BY expires_at LIMIT 100 FOR UPDATE SKIP LOCKED)''')
    return max(1, math.ceil(row['remaining'])) if row['hits'] > limit else 0


class ProtectionMiddleware:
    def __init__(self, app, db, identity, configured):
        self.app, self.db, self.identity, self.configured = app, db, identity, configured

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http' or scope['method'] == 'OPTIONS' or scope['path'] == '/health':
            return await self.app(scope, receive, send)

        async def reject(status, detail, retry=None):
            headers = {'Cache-Control': 'no-store'}
            if retry:
                headers['Retry-After'] = str(retry)
            await JSONResponse({'detail': detail}, status_code=status, headers=headers)(scope, receive, send)

        headers = dict(scope.get('headers', []))
        try:
            length = int(headers.get(b'content-length', b'0'))
            if length < 0:
                raise ValueError()
        except ValueError:
            return await reject(400, 'Soʻrov hajmi notoʻgʻri.')
        if length > MAX_BODY:
            return await reject(413, 'Soʻrov hajmi juda katta. Rasmlar hajmini kamaytiring.')

        if self.configured():
            raw = headers.get(b'x-telegram-init-data', b'').decode('latin1')
            try:
                user = self.identity(raw)['id'] if raw else None
                invalid = False
            except HTTPException:
                user, invalid = None, True
            peer = client_peer(scope, headers)
            # Forwarded headers are ignored unless the Railway edge is explicitly trusted.
            subject = f'user:{user}' if user else f'peer:{peer}'
            write = scope['method'] not in ('GET', 'HEAD')
            protected_read = scope['path'].startswith(('/owner/', '/admin/', '/bookings', '/auth/contact', '/subscriptions', '/availability-subscriptions'))
            public_write = scope['path'] == '/discovery/events'
            failed_auth = invalid or (not user and ((write and not public_write) or protected_read or scope['path'] == '/auth/me'))
            category = 'auth' if failed_auth else 'public_write' if public_write else 'write' if write else 'read'
            categories = [category]
            if write and user and (scope['path'] == '/venues' or scope['path'].endswith('/edit')):
                categories.append('submission')
            try:
                for category in categories:
                    retry = await run_in_threadpool(consume, self.db, category, subject)
                    if retry:
                        return await reject(429, 'Juda koʻp soʻrov yuborildi. Biroz kutib, qayta urinib koʻring.', retry)
            except Exception:
                logging.getLogger(__name__).error('Request quota storage unavailable')
                return await reject(503, 'Xizmat vaqtincha ishlamayapti. Keyinroq urinib koʻring.')

        # Buffer at most MAX_BODY before JSON parsing or photo decoding, even without Content-Length.
        body = bytearray()
        while True:
            message = await receive()
            if message['type'] == 'http.disconnect':
                return
            body.extend(message.get('body', b''))
            if len(body) > MAX_BODY:
                return await reject(413, 'Soʻrov hajmi juda katta. Rasmlar hajmini kamaytiring.')
            if not message.get('more_body', False):
                break

        delivered = False
        async def bounded_receive():
            nonlocal delivered
            if delivered:
                return await receive()
            delivered = True
            return {'type': 'http.request', 'body': bytes(body), 'more_body': False}
        await self.app(scope, bounded_receive, send)
