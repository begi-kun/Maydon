"""Public exact-time search agrees with the booking calendar."""
import os
import unittest
from datetime import datetime, timedelta
from test_owner_flow import main, TestClient


@unittest.skipUnless(os.getenv('TEST_DATABASE_URL'), 'Requires disposable PostgreSQL')
class SearchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.context = TestClient(main.app)
        cls.client = cls.context.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.context.__exit__(None, None, None)

    def test_search_matches_calendar_and_sport(self):
        day = (datetime.now(main.UZBEKISTAN_TIME) + timedelta(days=2)).date()
        start = datetime.combine(day, datetime.min.time(), main.UZBEKISTAN_TIME).replace(hour=21)
        ids = []
        with main.db() as conn:
            for name, hours, status, suspended, sport in [
                ('free', '08:00–23:00', 'approved', False, 'football'),
                ('closed', '08:00–21:00', 'approved', False, 'football'),
                ('overnight', '18:00–02:00', 'approved', False, 'football'),
                ('pending booking', '24/7', 'approved', False, 'football'),
                ('confirmed booking', '24/7', 'approved', False, 'football'),
                ('cancelled booking', '24/7', 'approved', False, 'football'),
                ('rejected booking', '24/7', 'approved', False, 'football'),
                ('blocked', '24/7', 'approved', False, 'football'),
                ('unapproved', '24/7', 'pending', False, 'football'),
                ('suspended', '24/7', 'approved', True, 'football'),
                ('other sport', '24/7', 'approved', False, 'billiards'),
            ]:
                row = conn.execute("""INSERT INTO venues(name,sport,address,latitude,longitude,price,
                    owner_telegram_id,hours,status,suspended) VALUES (%s,%s,'Test',41,71,100000,101,%s,%s,%s) RETURNING id""",
                    (name, sport, hours, status, suspended)).fetchone()
                ids.append(row['id'])
            for index, status in [(3, 'pending'), (4, 'confirmed'), (5, 'cancelled'), (6, 'rejected')]:
                conn.execute('INSERT INTO bookings(venue_id,user_telegram_id,start_at,status) VALUES (%s,202,%s,%s)', (ids[index], start, status))
            conn.execute('INSERT INTO owner_blocks(venue_id,start_at) VALUES (%s,%s)', (ids[7], start))
        response = self.client.get('/venues', params={'available_at': start.isoformat(), 'sport': 'football'})
        self.assertEqual(response.status_code, 200, response.text)
        found = {row['id'] for row in response.json()} & set(ids)
        self.assertEqual(found, {ids[i] for i in [0, 2, 5, 6]})
        for venue_id in ids[:8]:
            slots = self.client.get(f'/venues/{venue_id}/availability', params={'day': day.isoformat()}).json()['slots']
            self.assertEqual(venue_id in found, slots[21]['status'] == 'available')
        # UTC input identifies the same slot.
        utc = start.astimezone(main.timezone.utc).isoformat()
        result = self.client.get('/venues', params={'available_at': utc, 'sport': 'football'}).json()
        self.assertEqual(found, {row['id'] for row in result} & set(ids))
        all_ids = {row['id'] for row in self.client.get('/venues').json()}
        self.assertTrue(set(ids[:8]).issubset(all_ids))
        self.assertNotIn(ids[8], all_ids)
        self.assertNotIn(ids[9], all_ids)

    def test_invalid_search_times(self):
        start = (datetime.now(main.UZBEKISTAN_TIME) + timedelta(days=2)).replace(hour=21, minute=0, second=0, microsecond=0)
        for value in [start.replace(tzinfo=None).isoformat(), start.replace(minute=30).isoformat(),
                      (start - timedelta(days=5)).isoformat(), (start + timedelta(days=61)).isoformat(), 'bad']:
            self.assertEqual(self.client.get('/venues', params={'available_at': value}).status_code, 422)
