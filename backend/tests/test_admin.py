"""Admin authorization, moderation, filtering and cancellation regression coverage."""
import os
import unittest
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
from test_owner_flow import main, headers, payload


class AdminAccessTests(unittest.TestCase):
    def test_management_requires_admin_and_valid_reason(self):
        client = TestClient(main.app)
        for path in ['/admin/venues?status=all', '/admin/bookings']:
            self.assertEqual(client.get(path).status_code, 401)
            self.assertEqual(client.get(path, headers=headers(101)).status_code, 403)
        for path in ['/admin/venues/1/suspend', '/admin/venues/1/rejected', '/admin/bookings/1/cancel']:
            self.assertEqual(client.post(path, headers=headers(101), json={'reason':'test'}).status_code, 403)
            for body in [None, {'reason':'   '}, {'reason':'ab'}, {'reason':'x'*501}]:
                self.assertEqual(client.post(path, headers=headers(999), json=body).status_code, 422)


@unittest.skipUnless(os.environ.get('TEST_DATABASE_URL'), 'Disposable PostgreSQL required')
class AdminIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.context = TestClient(main.app)
        cls.client = cls.context.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.context.__exit__(None, None, None)

    def setUp(self):
        self.venue = self.client.post('/venues', headers=headers(701), json=payload()).json()['id']
        self.url = f'/admin/venues/{self.venue}'

    def decide(self, action, reason=None):
        return self.client.post(f'{self.url}/{action}', headers=headers(999), **({'json':{'reason':reason}} if reason else {}))

    def listing(self, status='all'):
        result = self.client.get('/admin/venues', headers=headers(999), params={'status':status,'q':str(self.venue)})
        self.assertEqual(result.headers['cache-control'], 'private, no-store')
        return next((v for v in result.json() if v['id']==self.venue), None)

    def test_rejection_reason_notification_and_resubmission(self):
        self.assertEqual(self.decide('rejected', '  Rasmlar aniq emas  ').status_code, 200)
        self.assertEqual(self.listing('rejected')['review_reason'], 'Rasmlar aniq emas')
        self.assertEqual(self.decide('approved').status_code, 409)
        with main.db() as conn:
            row = conn.execute("SELECT * FROM admin_actions WHERE entity_type='venue' AND entity_id=%s", (self.venue,)).fetchone()
            self.assertEqual((row['admin_id'], row['reason']), (999, 'Rasmlar aniq emas'))
            self.assertTrue(conn.execute("SELECT 1 FROM notifications WHERE recipient_id=701 AND body LIKE '%%Rasmlar aniq emas%%'").fetchone())
        own = next(v for v in self.client.get('/owner/venues', headers=headers(701)).json() if v['id']==self.venue)
        self.assertEqual(own['review_reason'], 'Rasmlar aniq emas')
        result = self.client.post(f'/owner/venues/{self.venue}/edit', headers=headers(701), json={**payload(),'photos':[],'keep_photos':own['photos']})
        self.assertEqual(result.status_code, 200)
        self.assertIsNone(self.listing('pending')['review_reason'])

    def test_suspension_blocks_public_booking_and_survives_owner_edit(self):
        self.assertEqual(self.decide('approved').status_code, 200)
        self.assertEqual(self.decide('suspend', 'Tekshiruv davom etmoqda').status_code, 200)
        self.assertIsNotNone(self.listing('suspended'))
        self.assertNotIn(self.venue, [v['id'] for v in self.client.get('/venues').json()])
        photo = self.listing()['photos'][0]
        self.assertEqual(self.client.get(f'/photos/{photo}').status_code, 401)
        self.assertEqual(self.client.get(f'/photos/{photo}', headers=headers(999)).status_code, 200)
        day = (datetime.now(main.UZBEKISTAN_TIME)+timedelta(days=2)).date().isoformat()
        self.assertEqual(self.client.get(f'/venues/{self.venue}/availability?day={day}').status_code, 404)
        with main.db() as conn:
            conn.execute("INSERT INTO telegram_contacts(telegram_id,phone) VALUES (702,'+998901234567') ON CONFLICT DO NOTHING")
        self.assertEqual(self.client.post('/bookings', headers=headers(702), json={'venue_id':self.venue,'start_at':day+'T12:00:00+05:00'}).status_code, 404)
        self.client.post(f'/owner/venues/{self.venue}/edit', headers=headers(701), json=payload())
        self.decide('approved')
        self.assertTrue(self.listing()['suspended'])
        self.assertEqual(self.decide('resume').status_code, 200)
        self.assertIn(self.venue, [v['id'] for v in self.client.get('/venues').json()])
        self.assertEqual(self.decide('resume').status_code, 409)

    def test_archived_venues_remain_reviewable_but_cannot_be_changed(self):
        self.client.post(f'/owner/venues/{self.venue}/delete', headers=headers(701))
        venue = self.listing('archived')
        self.assertIsNotNone(venue)
        self.assertEqual(self.client.get(f'/photos/{venue["photos"][0]}', headers=headers(999)).status_code, 200)
        self.assertEqual(self.decide('approved').status_code, 404)
        self.assertEqual(self.decide('suspend', 'Testing archive').status_code, 404)

    def test_booking_date_filters_cancellation_and_notifications(self):
        self.decide('approved')
        day = (datetime.now(main.UZBEKISTAN_TIME)+timedelta(days=2)).date()
        midnight = datetime.combine(day, datetime.min.time(), tzinfo=main.UZBEKISTAN_TIME)
        with main.db() as conn:
            ids = []
            for start in [midnight-timedelta(hours=1), midnight, midnight+timedelta(hours=23), midnight+timedelta(days=1)]:
                ids.append(conn.execute("INSERT INTO bookings(venue_id,user_telegram_id,start_at,status) VALUES (%s,702,%s,'confirmed') RETURNING id",(self.venue,start)).fetchone()['id'])
        query = {'venue_id':self.venue,'day':day.isoformat(),'status':'confirmed'}
        result = self.client.get('/admin/bookings', headers=headers(999), params=query)
        self.assertEqual(result.headers['cache-control'],'private, no-store')
        self.assertEqual({b['id'] for b in result.json()},set(ids[1:3]))
        target = ids[1]
        endpoint = f'/admin/bookings/{target}/cancel'
        self.assertEqual(self.client.post(endpoint, headers=headers(999), json={'reason':'Maydon taʼmirlanmoqda'}).status_code,200)
        self.assertEqual(self.client.post(endpoint, headers=headers(999), json={'reason':'Takroriy bekor qilish'}).status_code,409)
        result = self.client.get('/admin/bookings', headers=headers(999), params={'booking_id':target}).json()
        self.assertEqual(len(result),1)
        self.assertEqual(result[0]['cancellation_reason'],'Maydon taʼmirlanmoqda')
        with main.db() as conn:
            notices=conn.execute("SELECT recipient_id FROM notifications WHERE body LIKE %s",(f'📅 Bron #{target} —%',)).fetchall()
            self.assertEqual({r['recipient_id'] for r in notices},{701,702})
            self.assertEqual(len(notices),2)
            self.assertEqual(conn.execute("SELECT count(*) AS n FROM admin_actions WHERE entity_type='booking' AND entity_id=%s",(target,)).fetchone()['n'],1)
            conn.execute('UPDATE bookings SET start_at=NOW()-INTERVAL \'2 hours\' WHERE id=%s',(ids[2],))
        self.assertEqual(self.client.post(f'/admin/bookings/{ids[2]}/cancel', headers=headers(999),json={'reason':'Past booking'}).status_code,409)
        slots=self.client.get(f'/venues/{self.venue}/availability?day={day}').json()['slots']
        self.assertEqual(slots[0]['status'],'available')

    def test_venue_pagination_and_status_validation(self):
        with main.db() as conn:
            for i in range(52):
                conn.execute("INSERT INTO venues(name,sport,address,latitude,longitude,price,owner_telegram_id) VALUES (%s,'football','Test',41,71,0,703)",(f'Paging-{self.venue}-{i}',))
        params={'status':'all','q':f'Paging-{self.venue}-'}
        first=self.client.get('/admin/venues',headers=headers(999),params=params).json()
        second=self.client.get('/admin/venues',headers=headers(999),params={**params,'offset':50}).json()
        self.assertEqual((len(first),len(second)),(50,2))
        self.assertFalse({v['id'] for v in first}&{v['id'] for v in second})
        self.assertEqual(self.client.get('/admin/venues?offset=-1',headers=headers(999)).status_code,422)
        self.assertEqual(self.client.get('/admin/bookings?status=invalid',headers=headers(999)).status_code,422)
