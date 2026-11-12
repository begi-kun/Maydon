"""Analytics cover full history, owner isolation and immutable booking prices."""
import os
import unittest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from test_owner_flow import main, headers, payload


class AnalyticsAccessTests(unittest.TestCase):
    def test_access_and_range_validation(self):
        client=TestClient(main.app)
        for scope in ['admin','owner']:
            self.assertEqual(client.get(f'/{scope}/analytics').status_code,401)
        self.assertEqual(client.get('/admin/analytics',headers=headers(101)).status_code,403)
        for query in ['from_date=2026-11-12&to_date=2026-11-01','from_date=2020-01-01&to_date=2026-01-01','all_time=true&from_date=2026-01-01','to_date=9999-12-31']:
            self.assertEqual(client.get('/owner/analytics?'+query,headers=headers(101)).status_code,422)


@unittest.skipUnless(os.environ.get('TEST_DATABASE_URL'), 'Disposable PostgreSQL required')
class AnalyticsIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.context=TestClient(main.app)
        cls.client=cls.context.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.context.__exit__(None,None,None)

    def setUp(self):
        # Unique owners keep fixtures isolated if the disposable DB is reused.
        with main.db() as conn:
            self.owner=conn.execute('SELECT COALESCE(MAX(owner_telegram_id),10000)+1 AS id FROM venues').fetchone()['id']
            self.other=self.owner+1
            self.venues=[]
            for owner,name in [(self.owner,'Analytics active'),(self.owner,'Analytics archive'),(self.other,'Private competitor')]:
                self.venues.append(conn.execute("INSERT INTO venues(name,sport,address,latitude,longitude,price,owner_telegram_id,status) VALUES (%s,'football','Namangan',41,71,900000,%s,'approved') RETURNING id",(name,owner)).fetchone()['id'])
            conn.execute('UPDATE venues SET deleted_at=NOW() WHERE id=%s',(self.venues[1],))
            # 105 bookings exceed the old owner listing's 100-row cap.
            for n in range(105):
                conn.execute("INSERT INTO bookings(venue_id,user_telegram_id,start_at,status,booked_price) VALUES (%s,801,%s,'confirmed',1000)",(self.venues[0],datetime(2026,1,1,tzinfo=main.UZBEKISTAN_TIME)+timedelta(hours=n)))
            for index,(status,price,customer) in enumerate([('confirmed',None,802),('confirmed',0,803),('pending',2000,802),('cancelled',3000,804),('rejected',4000,805)]):
                conn.execute('INSERT INTO bookings(venue_id,user_telegram_id,start_at,status,booked_price) VALUES (%s,%s,%s,%s,%s)',(self.venues[1],customer,datetime(2026,2,1,tzinfo=main.UZBEKISTAN_TIME)+timedelta(hours=index),status,price))
            conn.execute("INSERT INTO bookings(venue_id,user_telegram_id,start_at,status,booked_price) VALUES (%s,9999,'2026-01-01T00:00:00+05:00','confirmed',999999)",(self.venues[2],))

    def report(self,scope='owner',user=None,**params):
        result=self.client.get(f'/{scope}/analytics',headers=headers(user or self.owner),params=params)
        self.assertEqual(result.status_code,200,result.text)
        self.assertEqual(result.headers['cache-control'],'private, no-store')
        return result.json()

    def test_full_history_archives_statuses_unique_customers_and_unknown_prices(self):
        report=self.report(all_time=True)
        self.assertEqual(report['bucket'],'month')
        self.assertEqual(report['summary'],{'total':110,'pending':1,'confirmed':107,'rejected':1,'cancelled':1,'customers':5,'confirmed_value':105000,'unpriced_confirmed':1})
        self.assertEqual({v['id'] for v in report['venues']},set(self.venues[:2]))
        self.assertEqual({v['id'] for v in report['available_venues']},set(self.venues[:2]))
        self.assertEqual([r['total'] for r in report['trend']],[105,5])
        self.assertNotIn('999999',str(report))

    def test_owner_cannot_query_other_venue_and_admin_can(self):
        self.assertEqual(self.client.get('/owner/analytics',headers=headers(self.owner),params={'venue_id':self.venues[2]}).status_code,404)
        report=self.report('admin',999,all_time=True,venue_id=self.venues[2])
        self.assertEqual(report['summary']['confirmed_value'],999999)
        self.assertEqual(report['summary']['total'],1)
        report=self.report(user=self.other,all_time=True)
        self.assertEqual([v['id'] for v in report['venues']],[self.venues[2]])
        report=self.report(user=self.other+1,all_time=True)
        self.assertEqual(report['summary']['total'],0)
        self.assertEqual(report['venues'],[])

    def test_local_date_boundaries_zero_results_and_venue_filter(self):
        report=self.report(from_date='2026-01-01',to_date='2026-01-01',venue_id=self.venues[0])
        self.assertEqual(report['summary']['total'],24)
        self.assertEqual(report['trend'][0]['date'],'2026-01-01')
        self.assertEqual(report['bucket'],'day')
        report=self.report(from_date='2025-01-01',to_date='2025-01-02')
        self.assertEqual(report['summary']['total'],0)
        self.assertEqual(report['summary']['confirmed_value'],0)
        self.assertEqual(report['trend'],[])
        self.assertEqual(len(report['venues']),2)

    def test_booking_price_is_snapshotted_and_not_recalculated(self):
        with main.db() as conn:
            conn.execute("INSERT INTO telegram_contacts(telegram_id,phone) VALUES (806,'+998901234567') ON CONFLICT DO NOTHING")
        start=(datetime.now(main.UZBEKISTAN_TIME)+timedelta(days=2)).replace(minute=0,second=0,microsecond=0)
        result=self.client.post('/bookings',headers=headers(806),json={'venue_id':self.venues[0],'start_at':start.isoformat()})
        self.assertEqual(result.status_code,201,result.text)
        booking_id=result.json()['id']
        self.client.post(f'/owner/bookings/{booking_id}/confirmed',headers=headers(self.owner))
        with main.db() as conn:
            conn.execute('UPDATE venues SET price=123 WHERE id=%s',(self.venues[0],))
        report=self.report(from_date=start.date().isoformat(),to_date=start.date().isoformat())
        self.assertEqual(report['summary']['confirmed_value'],900000)
        self.assertEqual(report['summary']['unpriced_confirmed'],0)
