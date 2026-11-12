"""Owner schedule, offline bookings, hours and payment isolation."""
import os
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from test_owner_flow import main, headers, payload, TestClient

class HoursTests(unittest.TestCase):
    def test_boundaries_and_overnight(self):
        def at(hour):
            return datetime(2030, 1, 1, hour, tzinfo=main.UZBEKISTAN_TIME)
        for hour in range(24):
            self.assertEqual(main.is_open('08:00–23:00', at(hour)), 8 <= hour < 23)
            self.assertEqual(main.is_open('18:00–02:00', at(hour)), hour >= 18 or hour < 2)
            self.assertTrue(main.is_open('24/7', at(hour)))
        self.assertFalse(main.is_open('unknown legacy text', at(12)))
        for hours in ['25:00–26:00','08:30–23:00','08:00–08:00']:
            with self.assertRaises(ValueError): main.hours_window(hours)

@unittest.skipUnless(os.getenv('TEST_DATABASE_URL'), 'Disposable PostgreSQL required')
class OwnerOperationsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.context = TestClient(main.app)
        cls.client = cls.context.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.context.__exit__(None, None, None)

    def setUp(self):
        self.owner = headers(7101)
        self.other = headers(7102)
        data = {**payload(), 'hours':'08:00–23:00'}
        self.venue = self.client.post('/venues', headers=self.owner, json=data).json()['id']
        self.client.post(f'/admin/venues/{self.venue}/approved', headers=headers(999))
        self.day = (datetime.now(main.UZBEKISTAN_TIME)+timedelta(days=2)).date().isoformat()
        with main.db() as conn:
            conn.execute("INSERT INTO telegram_contacts(telegram_id,phone) VALUES (7102,'+998901234567') ON CONFLICT DO NOTHING")

    def body(self, hour=10):
        return {'venue_id':self.venue, 'start_at':f'{self.day}T{hour:02}:00:00+05:00', 'customer_name':'Phone customer', 'customer_phone':'+998901234567'}

    def test_manual_conflicts_payment_privacy_history_and_cancel(self):
        self.assertEqual(self.client.post('/owner/manual-bookings',headers=self.other,json=self.body()).status_code,404)
        r=self.client.post('/owner/manual-bookings',headers=self.owner,json=self.body())
        self.assertEqual(r.status_code,201,r.text)
        booking=r.json()['id']
        self.assertIsNone(r.json()['user_telegram_id'])
        self.assertEqual(self.client.post('/bookings',headers=self.other,json=self.body()).status_code,409)
        self.assertEqual(self.client.post('/owner/blocks',headers=self.owner,json=self.body()).status_code,409)
        for status in ['deposit','paid','unpaid']:
            self.assertEqual(self.client.post(f'/owner/payments/{booking}',headers=self.other,json={'status':status}).status_code,404)
            self.assertEqual(self.client.post(f'/owner/payments/{booking}',headers=self.owner,json={'status':status}).status_code,200)
        self.assertEqual(self.client.post(f'/owner/payments/{booking}',headers=self.owner,json={'status':'invalid'}).status_code,422)
        r=self.client.get(f'/owner/bookings?venue_id={self.venue}&search=Phone&status=confirmed&from_date={self.day}&to_date={self.day}',headers=self.owner)
        self.assertEqual([b['id'] for b in r.json()],[booking])
        self.assertEqual(r.headers['cache-control'],'private, no-store')
        self.assertEqual(self.client.get(f'/owner/bookings?venue_id={self.venue}',headers=self.other).json(),[])
        self.assertEqual(self.client.post(f'/owner/manual-bookings/{booking}/cancel',headers=self.other,json={}).status_code,404)
        self.assertEqual(self.client.post(f'/owner/manual-bookings/{booking}/cancel',headers=self.owner,json={}).status_code,200)
        self.assertEqual(self.client.post('/bookings',headers=self.other,json=self.body()).status_code,201)

    def test_blocks_hours_schedule_and_admin_manual_cancel(self):
        self.assertEqual(self.client.post('/owner/manual-bookings',headers=self.owner,json=self.body(7)).status_code,422)
        self.assertEqual(self.client.post('/bookings',headers=self.other,json=self.body(23)).status_code,422)
        block=self.client.post('/owner/blocks',headers=self.owner,json={**self.body(),'reason':'Maintenance'}).json()['id']
        r=self.client.get(f'/venues/{self.venue}/availability?day={self.day}').json()
        self.assertEqual(r['slots'][7]['status'],'closed')
        self.assertEqual(r['slots'][10]['status'],'booked')
        self.assertNotIn('Maintenance',str(r))
        self.assertEqual(self.client.post('/bookings',headers=self.other,json=self.body()).status_code,409)
        url=f'/owner/schedule?venue_id={self.venue}&day={self.day}&days=7'
        self.assertEqual(self.client.get(url,headers=self.other).status_code,404)
        self.assertEqual(len(self.client.get(url,headers=self.owner).json()['slots']),168)
        self.assertEqual(self.client.post(f'/owner/blocks/{block}/remove',headers=self.other,json={}).status_code,404)
        self.assertEqual(self.client.post(f'/owner/blocks/{block}/remove',headers=self.owner,json={}).status_code,200)
        booking=self.client.post('/owner/manual-bookings',headers=self.owner,json=self.body()).json()['id']
        url=f'/owner/venues/{self.venue}/hours'
        self.assertEqual(self.client.post(url,headers=self.owner,json={'hours':'12:00–22:00'}).status_code,409)
        self.assertEqual(self.client.post(url,headers=self.other,json={'hours':'24/7'}).status_code,404)
        self.assertEqual(self.client.post(url,headers=self.owner,json={'hours':'24/7'}).status_code,200)
        self.assertEqual(self.client.post(f'/admin/bookings/{booking}/cancel',headers=headers(999),json={'reason':'Customer request'}).status_code,200)

    def test_concurrent_manual_and_customer_booking(self):
        with ThreadPoolExecutor(max_workers=2) as pool:
            calls=[pool.submit(self.client.post,'/owner/manual-bookings',headers=self.owner,json=self.body()),pool.submit(self.client.post,'/bookings',headers=self.other,json=self.body())]
            self.assertEqual(sorted(call.result().status_code for call in calls),[201,409])

    def test_manual_bookings_do_not_generate_customer_reminders(self):
        from reminders import queue_reminders
        booking=self.client.post('/owner/manual-bookings',headers=self.owner,json=self.body()).json()['id']
        with main.db() as conn:
            conn.execute("UPDATE bookings SET start_at=NOW()+INTERVAL '30 minutes' WHERE id=%s",(booking,))
            queue_reminders(conn)
            self.assertIsNone(conn.execute('SELECT 1 FROM notifications WHERE reminder_booking_id=%s',(booking,)).fetchone())
