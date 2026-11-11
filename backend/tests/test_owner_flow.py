"""Run against an empty, disposable database: TEST_DATABASE_URL=... python -m unittest discover -s backend/tests."""
import base64
import hashlib
import hmac
import json
import os
import sys
import time
import unittest
from io import BytesIO
from pathlib import Path
from urllib.parse import urlencode
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from PIL import Image

os.environ['BOT_TOKEN'] = 'test-token-not-a-real-bot'
os.environ['ADMIN_TELEGRAM_ID'] = '999'
os.environ['CORS_ORIGINS'] = 'https://example.test'
os.environ['DATABASE_URL'] = os.environ.get('TEST_DATABASE_URL', '')
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import main
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'bot'))
from contacts import verified_contact_phone

def headers(user=101, age=0):
    fields = {'auth_date': str(int(time.time()) - age), 'user': json.dumps({'id': user, 'first_name': 'Owner'})}
    check = '\n'.join(f'{k}={fields[k]}' for k in sorted(fields))
    secret = hmac.new(b'WebAppData', main.BOT_TOKEN.encode(), hashlib.sha256).digest()
    fields['hash'] = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
    return {'X-Telegram-Init-Data': urlencode(fields)}

def payload():
    output = BytesIO()
    Image.new('RGB', (400, 300), 'green').save(output, format='PNG')
    return {'name': 'Test pitch', 'sport': 'football', 'address': 'Selected map location',
            'latitude': 41.0011, 'longitude': 71.6726, 'price': 100000,
            'photos': [base64.b64encode(output.getvalue()).decode()]}

class AuthTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(main.app)

    def test_verified_identity(self):
        self.assertEqual(self.client.get('/auth/me', headers=headers()).json()['id'], 101)

    def test_booking_notification_uses_uzbekistan_time(self):
        self.assertEqual(main.booking_time_label(datetime(2026, 11, 11, 14, tzinfo=timezone.utc)),
                         '11.11.2026 · 19:00 (Oʻzbekiston vaqti, UTC+5)')
        self.assertEqual(main.booking_time_label(datetime(2026, 11, 11, 22, tzinfo=timezone.utc)),
                         '12.11.2026 · 03:00 (Oʻzbekiston vaqti, UTC+5)')

    def test_shared_contact_must_belong_to_sender(self):
        self.assertEqual(verified_contact_phone(101, 101, '998 90 123 45 67'), '+998901234567')
        for owner, phone in [(202, '+998901234567'), (None, '+998901234567'), (101, 'not-a-number')]:
            with self.assertRaises(ValueError): verified_contact_phone(101, owner, phone)

    def test_rejects_missing_expired_forged_duplicate_and_future_auth(self):
        for value in [{}, headers(age=4000), headers(age=-300),
                      {'X-Telegram-Init-Data': headers()['X-Telegram-Init-Data'].replace('101', '102')},
                      {'X-Telegram-Init-Data': headers()['X-Telegram-Init-Data'] + '&auth_date=0'}]:
            self.assertEqual(self.client.get('/auth/me', headers=value).status_code, 401)

    def test_photo_validation(self):
        photo = main.prepare_photo(payload()['photos'][0])
        self.assertEqual(Image.open(BytesIO(photo)).format, 'JPEG')
        for value in ['not base64', base64.b64encode(b'<svg/>').decode()]:
            with self.assertRaises(main.HTTPException): main.prepare_photo(value)

    def test_missing_photos_and_large_body(self):
        data = payload(); data['photos'] = []
        self.assertEqual(self.client.post('/venues', headers=headers(), json=data).status_code, 422)
        self.assertEqual(self.client.post('/venues', headers=headers(), content=b' ' * 7500001).status_code, 413)

@unittest.skipUnless(os.environ.get('TEST_DATABASE_URL'), 'Disposable PostgreSQL required')
class OwnerIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.context = TestClient(main.app)
        cls.client = cls.context.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.context.__exit__(None, None, None)

    def test_submission_owner_isolation_moderation_and_photo_access(self):
        data = payload(); data['owner_telegram_id'] = 202
        response = self.client.post('/venues', headers=headers(101), json=data)
        self.assertEqual(response.status_code, 201, response.text)
        venue_id = response.json()['id']
        own = self.client.get('/owner/venues', headers=headers(101)).json()
        venue = next(v for v in own if v['id'] == venue_id)
        self.assertNotIn(venue_id, [v['id'] for v in self.client.get('/owner/venues', headers=headers(202)).json()])
        self.assertNotIn(venue_id, [v['id'] for v in self.client.get('/venues').json()])
        photo = '/photos/' + str(venue['photos'][0])
        self.assertEqual(self.client.get(photo).status_code, 401)
        self.assertEqual(self.client.get(photo, headers=headers(202)).status_code, 404)
        self.assertEqual(self.client.get(photo, headers=headers(101)).status_code, 200)
        self.assertEqual(self.client.get(photo, headers=headers(999)).status_code, 200)
        self.assertEqual(self.client.post(f'/admin/venues/{venue_id}/approved', headers=headers(101)).status_code, 403)
        self.assertEqual(self.client.post(f'/admin/venues/{venue_id}/approved', headers=headers(999)).status_code, 200)
        public = next(v for v in self.client.get('/venues').json() if v['id'] == venue_id)
        self.assertEqual(public['latitude'], data['latitude'])
        self.assertEqual(public['longitude'], data['longitude'])
        self.assertEqual(self.client.get(photo).status_code, 200)

    def test_invalid_photo_does_not_create_venue(self):
        before = self.client.get('/owner/venues', headers=headers(303)).json()
        data = payload(); data['photos'].append('invalid')
        self.assertEqual(self.client.post('/venues', headers=headers(303), json=data).status_code, 422)
        self.assertEqual(self.client.get('/owner/venues', headers=headers(303)).json(), before)

    def test_availability_uses_namangan_day_and_updates_after_cancel(self):
        with main.db() as conn:
            conn.execute("INSERT INTO telegram_contacts(telegram_id,phone) VALUES (202,'+998901234567') ON CONFLICT DO NOTHING")
        response = self.client.post('/venues', headers=headers(101), json=payload())
        venue_id = response.json()['id']
        day = (datetime.now(timezone(timedelta(hours=5))) + timedelta(days=1)).date().isoformat()
        url = f'/venues/{venue_id}/availability?day={day}'
        self.assertEqual(self.client.get(url).status_code, 404)
        self.client.post(f'/admin/venues/{venue_id}/approved', headers=headers(999))
        result = self.client.get(url).json()
        self.assertEqual(result['timezone'], 'Asia/Tashkent')
        self.assertEqual(len(result['slots']), 24)
        slot = result['slots'][0]
        self.assertEqual(slot['start_at'], day + 'T00:00:00+05:00')
        self.assertEqual(slot['status'], 'available')
        booking = self.client.post('/bookings', headers=headers(202), json={'venue_id': venue_id, 'start_at': slot['start_at']})
        self.assertEqual(booking.status_code, 201, booking.text)
        self.assertEqual(self.client.get(url).json()['slots'][0]['status'], 'booked')
        self.assertEqual(self.client.get(url).json()['slots'][1]['status'], 'available')
        self.client.post(f'/bookings/{booking.json()["id"]}/cancel', headers=headers(202))
        self.assertEqual(self.client.get(url).json()['slots'][0]['status'], 'available')
        self.assertEqual(self.client.get(f'/venues/{venue_id}/availability?day=2020-01-01').status_code, 422)

    def test_edit_requires_owner_and_reapproval(self):
        venue_id = self.client.post('/venues', headers=headers(401), json=payload()).json()['id']
        self.client.post(f'/admin/venues/{venue_id}/approved', headers=headers(999))
        venue = next(v for v in self.client.get('/owner/venues', headers=headers(401)).json() if v['id'] == venue_id)
        change = {**payload(), 'name': 'Updated pitch', 'photos': [], 'keep_photos': venue['photos']}
        endpoint = f'/owner/venues/{venue_id}/edit'
        self.assertEqual(self.client.post(endpoint, headers=headers(402), json=change).status_code, 404)
        self.assertEqual(self.client.post(endpoint, headers=headers(401), json={**change, 'keep_photos': [999999]}).status_code, 422)
        self.assertEqual(self.client.post(endpoint, headers=headers(401), json=change).status_code, 200)
        updated = next(v for v in self.client.get('/owner/venues', headers=headers(401)).json() if v['id'] == venue_id)
        self.assertEqual(updated['name'], 'Updated pitch')
        self.assertEqual(updated['status'], 'pending')
        self.assertEqual(updated['photos'], venue['photos'])
        self.assertNotIn(venue_id, [v['id'] for v in self.client.get('/venues').json()])

    def test_verified_phone_snapshot_privacy_and_deletion_safeguard(self):
        venue_id = self.client.post('/venues', headers=headers(501), json=payload()).json()['id']
        self.client.post(f'/admin/venues/{venue_id}/approved', headers=headers(999))
        start = (datetime.now(timezone.utc) + timedelta(days=1)).replace(minute=0,second=0,microsecond=0).isoformat()
        data = {'venue_id': venue_id, 'start_at': start, 'customer_phone': '+998999999999'}
        with main.db() as conn:
            conn.execute('DELETE FROM telegram_contacts WHERE telegram_id=502')
        self.assertEqual(self.client.post('/bookings', headers=headers(502), json=data).status_code, 428)
        with main.db() as conn:
            conn.execute("INSERT INTO telegram_contacts(telegram_id,phone) VALUES (502,'+998901112233')")
        result = self.client.post('/bookings', headers=headers(502), json=data)
        self.assertEqual(result.status_code, 201, result.text)
        booking_id = result.json()['id']
        owner_response = self.client.get('/owner/bookings', headers=headers(501))
        self.assertEqual(owner_response.headers['cache-control'], 'private, no-store')
        self.assertEqual(next(b for b in owner_response.json() if b['id']==booking_id)['customer_phone'], '+998901112233')
        self.assertNotIn('+998901112233', self.client.get('/owner/bookings', headers=headers(503)).text)
        self.assertNotIn('+998901112233', self.client.get('/venues').text)
        self.assertIsNone(self.client.get('/auth/contact', headers=headers(503)).json()['phone'])
        endpoint = f'/owner/venues/{venue_id}/delete'
        self.assertEqual(self.client.post(endpoint, headers=headers(503)).status_code, 404)
        self.assertEqual(self.client.post(endpoint, headers=headers(501)).status_code, 409)
        self.client.post(f'/bookings/{booking_id}/cancel', headers=headers(502))
        self.assertEqual(self.client.post(endpoint, headers=headers(501)).status_code, 200)
        self.assertNotIn(venue_id, [v['id'] for v in self.client.get('/venues').json()])
        self.assertNotIn(venue_id, [v['id'] for v in self.client.get('/owner/venues', headers=headers(501)).json()])
        self.assertIn(booking_id, [b['id'] for b in self.client.get('/bookings/me', headers=headers(502)).json()])
        self.assertEqual(self.client.post('/bookings', headers=headers(502), json=data).status_code, 404)
        self.assertEqual(self.client.post(f'/admin/venues/{venue_id}/approved', headers=headers(999)).status_code, 404)

if __name__ == '__main__':
    unittest.main()
