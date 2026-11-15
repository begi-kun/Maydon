"""Pilot attribution, atomic recurrence and availability alert regression tests."""
import os
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from unittest.mock import patch
from uuid import uuid4
from test_owner_flow import main, headers, payload, TestClient
from availability_alerts import queue_availability_alerts, subscription_is_current, slot_is_open
from reminders import pending_notifications


class ProductAccessTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(main.app)

    def test_private_endpoints_and_telemetry_allowlist(self):
        for path in ['/availability-subscriptions', '/admin/pilot?from_date=2026-11-15']:
            self.assertEqual(self.client.get(path).status_code, 401)
        body = {'id':str(uuid4()), 'session_id':str(uuid4()), 'search_id':str(uuid4()), 'event':'discovery_results', 'result_count':0}
        for field in ['phone','query','latitude','telegram_id','name']:
            self.assertEqual(self.client.post('/discovery/events',json={**body,field:'private'}).status_code,422)
        for bad in [{'event':'booking_request_created'}, {'sport':'unknown'}, {'hour':24}, {'result_count':-1}]:
            self.assertEqual(self.client.post('/discovery/events',json={**body,**bad}).status_code,422)
        self.assertEqual(self.client.get('/admin/pilot?from_date=2026-11-15',headers=headers(200)).status_code,403)

    def test_flags_default_off(self):
        with patch.dict(os.environ, {'ENABLE_RECURRING_BOOKINGS':'false','ENABLE_AVAILABILITY_ALERTS':'false'}):
            self.assertEqual(self.client.get('/product/features').json(), {'recurring_bookings':False,'availability_alerts':False})
            self.assertEqual(self.client.post('/availability-subscriptions',headers=headers(),json={'venue_id':1,'start_at':'2030-01-01T12:00:00+05:00'}).status_code,404)

    def test_worker_opening_hours_match_api(self):
        for hours in ['', '24/7', '08:00–23:00', '18:00–02:00', 'broken', '24:00–24:00', '08:00–24:00']:
            for hour in range(24):
                instant = datetime(2030,1,1,hour,tzinfo=main.UZBEKISTAN_TIME)
                self.assertEqual(slot_is_open(hours, instant), main.is_open(hours,instant))


@unittest.skipUnless(os.getenv('TEST_DATABASE_URL'), 'Disposable PostgreSQL required')
class ProductIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.context = TestClient(main.app)
        cls.client = cls.context.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.context.__exit__(None,None,None)

    def setUp(self):
        self.flags=patch.dict(os.environ, {'ENABLE_RECURRING_BOOKINGS':'true','ENABLE_AVAILABILITY_ALERTS':'true'})
        self.flags.start();self.addCleanup(self.flags.stop)
        self.owner=headers(8801);self.customer=headers(8802);self.other=headers(8803)
        self.venue=self.client.post('/venues',headers=self.owner,json={**payload(),'hours':'08:00–23:00'}).json()['id']
        self.client.post(f'/admin/venues/{self.venue}/approved',headers=headers(999))
        self.day=(datetime.now(main.UZBEKISTAN_TIME)+timedelta(days=2)).date()
        with main.db() as conn:
            conn.execute("DELETE FROM product_rate_limits WHERE key IN ('recurring:8801','subscriptions:8802')")
            conn.execute("INSERT INTO telegram_contacts(telegram_id,phone) VALUES(8802,'+998901234567') ON CONFLICT DO NOTHING")

    def body(self, hour=10):
        return {'venue_id':self.venue,'start_at':f'{self.day}T{hour:02}:00:00+05:00'}

    def recurring(self):
        return {**self.body(),'weeks':4,'customer_name':'Test client','customer_phone':'+998901234567','request_id':str(uuid4())}

    def test_recurring_conflicts_are_atomic_and_subset_explicit(self):
        body=self.recurring()
        blocked=self.day+timedelta(weeks=1)
        self.client.post('/owner/blocks',headers=self.owner,json={**self.body(),'start_at':f'{blocked}T10:00:00+05:00'})
        preview=self.client.post('/owner/recurring-bookings/preview',headers=self.owner,json=body)
        self.assertEqual(preview.status_code,200,preview.text)
        self.assertEqual([s['available'] for s in preview.json()['slots']],[True,False,True,True])
        self.assertEqual(self.client.post('/owner/recurring-bookings',headers=self.owner,json=body).status_code,409)
        with main.db() as conn:
            self.assertEqual(conn.execute('SELECT COUNT(*) AS n FROM bookings WHERE venue_id=%s',(self.venue,)).fetchone()['n'],0)
        selected=[str(self.day),str(self.day+timedelta(weeks=2))]
        result=self.client.post('/owner/recurring-bookings',headers=self.owner,json={**body,'selected_dates':selected})
        self.assertEqual(result.status_code,201,result.text)
        ids=result.json()['booking_ids'];self.assertEqual(len(ids),2)
        self.assertEqual(self.client.post('/owner/recurring-bookings',headers=self.owner,json={**body,'selected_dates':selected}).json()['booking_ids'],ids)
        self.assertEqual(self.client.post('/owner/recurring-bookings',headers=self.owner,json={**body,'selected_dates':[str(blocked)]}).status_code,409)
        self.assertEqual(self.client.post(f'/owner/manual-bookings/{ids[0]}/cancel',headers=self.owner).status_code,200)
        with main.db() as conn:
            rows=conn.execute('SELECT status,booked_price,payment_status,user_telegram_id FROM bookings WHERE id=ANY(%s) ORDER BY id',(ids,)).fetchall()
        self.assertEqual([r['status'] for r in rows],['cancelled','confirmed'])
        self.assertTrue(all(r['booked_price']==100000 and r['payment_status']=='unpaid' and r['user_telegram_id'] is None for r in rows))

    def test_recurring_concurrent_retry_and_customer_conflict(self):
        body=self.recurring()
        with ThreadPoolExecutor(max_workers=2) as pool:
            results=list(pool.map(lambda _: self.client.post('/owner/recurring-bookings',headers=self.owner,json=body),range(2)))
        self.assertEqual([r.status_code for r in results],[201,201])
        self.assertEqual(results[0].json()['booking_ids'],results[1].json()['booking_ids'])
        self.assertEqual(self.client.post('/bookings',headers=self.customer,json=self.body()).status_code,409)
        with main.db() as conn:
            self.assertEqual(conn.execute('SELECT COUNT(*) AS n FROM bookings WHERE venue_id=%s',(self.venue,)).fetchone()['n'],4)

    def test_recurring_race_with_single_booking_leaves_no_partial_series(self):
        body=self.recurring()
        with ThreadPoolExecutor(max_workers=2) as pool:
            calls=[pool.submit(self.client.post,'/owner/recurring-bookings',headers=self.owner,json=body),pool.submit(self.client.post,'/bookings',headers=self.customer,json=self.body())]
            results=[c.result() for c in calls]
        self.assertEqual(sorted(r.status_code for r in results),[201,409])
        with main.db() as conn:
            count=conn.execute('SELECT COUNT(*) AS n FROM bookings WHERE venue_id=%s',(self.venue,)).fetchone()['n']
        self.assertIn(count,[1,4])

    def test_recurring_hours_ownership_and_date_validation(self):
        body=self.recurring()
        self.assertEqual(self.client.post('/owner/recurring-bookings/preview',headers=self.other,json=body).status_code,404)
        for changes in [{'weeks':5},{'weeks':0},{'customer_name':' '},{'selected_dates':[str(self.day),str(self.day)]},{'selected_dates':['2030-01-01']},{'selected_dates':[]}]:
            self.assertEqual(self.client.post('/owner/recurring-bookings',headers=self.owner,json={**body,**changes}).status_code,422)
        body['start_at']=f'{self.day}T23:00:00+05:00'
        self.assertEqual(self.client.post('/owner/recurring-bookings',headers=self.owner,json=body).status_code,409)
        with main.db() as conn:
            self.assertEqual(conn.execute('SELECT COUNT(*) AS n FROM bookings WHERE venue_id=%s',(self.venue,)).fetchone()['n'],0)

    def test_waitlist_cancel_dedup_expiry_and_rebooking(self):
        body=self.body()
        self.assertEqual(self.client.post('/availability-subscriptions',headers=self.customer,json=body).status_code,409)
        block=self.client.post('/owner/blocks',headers=self.owner,json=body).json()['id']
        sub=self.client.post('/availability-subscriptions',headers=self.customer,json=body)
        self.assertEqual(sub.status_code,201,sub.text)
        sid=sub.json()['id']
        self.assertEqual(self.client.post('/availability-subscriptions',headers=self.customer,json=body).json()['id'],sid)
        self.assertNotIn(sid,[row['id'] for row in self.client.get('/availability-subscriptions',headers=self.other).json()])
        self.assertEqual(self.client.post(f'/availability-subscriptions/{sid}/cancel',headers=self.other).status_code,404)
        with main.db() as conn:
            queue_availability_alerts(conn)
            self.assertIsNone(conn.execute('SELECT 1 FROM notifications WHERE availability_subscription_id=%s',(sid,)).fetchone())
        self.client.post(f'/owner/blocks/{block}/remove',headers=self.owner)
        with main.db() as conn:
            queue_availability_alerts(conn);queue_availability_alerts(conn)
            self.assertEqual(conn.execute('SELECT COUNT(*) AS n FROM notifications WHERE availability_subscription_id=%s',(sid,)).fetchone()['n'],1)
            self.assertTrue(subscription_is_current(conn,sid))
        # An alert does not reserve the slot.
        booking=self.client.post('/bookings',headers=self.customer,json=body)
        self.assertEqual(booking.status_code,201)
        with main.db() as conn:
            self.assertFalse(subscription_is_current(conn,sid))
        self.client.post(f'/bookings/{booking.json()["id"]}/cancel',headers=self.customer)
        self.client.post(f'/availability-subscriptions/{sid}/cancel',headers=self.customer)
        with main.db() as conn:
            self.assertFalse(subscription_is_current(conn,sid))
            self.assertNotIn(sid,[r['availability_subscription_id'] for r in pending_notifications(conn)])

    def test_waitlist_closing_hours_and_expired_subscription(self):
        body=self.body()
        block=self.client.post('/owner/blocks',headers=self.owner,json=body).json()['id']
        sid=self.client.post('/availability-subscriptions',headers=self.customer,json=body).json()['id']
        self.client.post(f'/owner/blocks/{block}/remove',headers=self.owner)
        self.client.post(f'/owner/venues/{self.venue}/hours',headers=self.owner,json={'hours':'12:00–23:00'})
        with main.db() as conn:
            queue_availability_alerts(conn)
            self.assertFalse(subscription_is_current(conn,sid))
            self.assertIsNone(conn.execute('SELECT 1 FROM notifications WHERE availability_subscription_id=%s',(sid,)).fetchone())
            conn.execute("UPDATE availability_subscriptions SET start_at=NOW()-INTERVAL '1 hour' WHERE id=%s",(sid,))
            queue_availability_alerts(conn)
            self.assertFalse(subscription_is_current(conn,sid))

    def test_telemetry_is_deduplicated_and_booking_is_server_attributed(self):
        event={'id':str(uuid4()),'search_id':str(uuid4()),'session_id':str(uuid4()),'event':'discovery_results','day':str(self.day),'hour':10,'sport':'football','result_count':1}
        for _ in range(2):
            self.assertEqual(self.client.post('/discovery/events',json=event).status_code,202)
        r=self.client.post('/bookings',headers=self.customer,json={**self.body(),'discovery_id':event['search_id']})
        self.assertEqual(r.status_code,201,r.text)
        with main.db() as conn:
            rows=conn.execute('SELECT event,booking_id FROM discovery_events WHERE search_id=%s',(event['search_id'],)).fetchall()
        self.assertEqual(sorted(row['event'] for row in rows),['booking_request_created','discovery_results'])
        report=self.client.get(f'/admin/pilot?from_date={datetime.now(main.UZBEKISTAN_TIME).date()}',headers=headers(999))
        self.assertEqual(report.status_code,200,report.text)
        self.assertGreaterEqual(report.json()['converted_searches'],1)
        self.assertNotIn('phone',report.text)
        self.assertEqual(report.headers['cache-control'],'private, no-store')
        self.assertEqual(self.client.get('/admin/pilot?from_date=9999-12-31',headers=headers(999)).status_code,422)

    def test_outcome_requires_owner_and_completed_session(self):
        booking=self.client.post('/owner/manual-bookings',headers=self.owner,json={**self.body(),'customer_name':'Test','customer_phone':'+998901234567'}).json()['id']
        path=f'/owner/bookings/{booking}/outcome'
        self.assertEqual(self.client.post(path,headers=self.other,json={'outcome':'no_show'}).status_code,404)
        self.assertEqual(self.client.post(path,headers=self.owner,json={'outcome':'no_show'}).status_code,409)
        with main.db() as conn:
            conn.execute("UPDATE bookings SET start_at=NOW()-INTERVAL '2 hours' WHERE id=%s",(booking,))
        self.assertEqual(self.client.post(path,headers=self.owner,json={'outcome':'no_show'}).status_code,200)
        self.assertEqual(self.client.post(path,headers=self.owner,json={'outcome':'attended'}).status_code,200)
        with main.db() as conn:
            self.assertEqual(conn.execute('SELECT outcome FROM booking_outcomes WHERE booking_id=%s',(booking,)).fetchone()['outcome'],'attended')

    def test_telemetry_rate_limit_is_shared_and_returns_retry_after(self):
        session=str(uuid4())
        for _ in range(60):
            body={'id':str(uuid4()),'search_id':str(uuid4()),'session_id':session,'event':'discovery_results','result_count':0}
            self.assertEqual(self.client.post('/discovery/events',json=body).status_code,202)
        body={**body,'id':str(uuid4()),'search_id':str(uuid4())}
        response=self.client.post('/discovery/events',json=body)
        self.assertEqual(response.status_code,429)
        self.assertEqual(response.headers['retry-after'],'60')
        self.assertEqual(self.client.post('/discovery/events',json={**body,'session_id':str(uuid4())}).status_code,202)

    def test_parallel_alert_workers_queue_one_message(self):
        body=self.body()
        block=self.client.post('/owner/blocks',headers=self.owner,json=body).json()['id']
        sid=self.client.post('/availability-subscriptions',headers=self.customer,json=body).json()['id']
        self.client.post(f'/owner/blocks/{block}/remove',headers=self.owner)
        def queue(_):
            with main.db() as conn:
                queue_availability_alerts(conn)
        with ThreadPoolExecutor(max_workers=2) as pool:
            list(pool.map(queue,range(2)))
        with main.db() as conn:
            self.assertEqual(conn.execute('SELECT COUNT(*) AS n FROM notifications WHERE availability_subscription_id=%s',(sid,)).fetchone()['n'],1)

    def test_owner_rejection_releases_slot_for_subscribers(self):
        body=self.body()
        booking=self.client.post('/bookings',headers=self.customer,json=body).json()['id']
        sid=self.client.post('/availability-subscriptions',headers=self.other,json=body).json()['id']
        self.client.post(f'/owner/bookings/{booking}/rejected',headers=self.owner)
        with main.db() as conn:
            queue_availability_alerts(conn)
            self.assertTrue(subscription_is_current(conn,sid))
            self.assertIsNotNone(conn.execute('SELECT 1 FROM notifications WHERE availability_subscription_id=%s',(sid,)).fetchone())

    def test_pilot_uses_local_cohort_and_counts_returning_customers(self):
        path='/admin/pilot?from_date=2044-01-02'
        before=self.client.get(path,headers=headers(999)).json()
        user=1000000000+uuid4().int%1000000000
        inside,outside,session=uuid4(),uuid4(),uuid4()
        with main.db() as conn:
            for search,created in [(inside,'2044-01-01T19:30:00Z'),(outside,'2044-01-01T00:00:00Z')]:
                conn.execute("INSERT INTO discovery_events(id,search_id,session_id,event,day,hour,sport,result_count,created_at) VALUES(%s,%s,%s,'discovery_results','2044-01-03',10,'football',1,%s)", (uuid4(),search,session,created))
            for day,search in [('2044-01-03',inside),('2044-01-10',outside)]:
                booking=conn.execute("INSERT INTO bookings(venue_id,user_telegram_id,start_at,status,created_at) VALUES(%s,%s,%s,'confirmed',%s) RETURNING id",(self.venue,user,day+'T10:00:00+05:00',day+'T06:00:00Z')).fetchone()['id']
                conn.execute("INSERT INTO discovery_events(id,search_id,session_id,event,day,hour,sport,booking_id,created_at) VALUES(%s,%s,%s,'booking_request_created',%s,10,'football',%s,%s)",(uuid4(),search,session,day,booking,day+'T06:00:00Z'))
                conn.execute("INSERT INTO booking_events(booking_id,actor_id,action,created_at) VALUES(%s,8801,'confirmed',%s)",(booking,day+'T06:01:00Z'))
        after=self.client.get(path,headers=headers(999)).json()
        for key,delta in [('timed_searches',1),('converted_timed_searches',1),('converted_searches',1),('attributed_requests',1),('booking_requests',2),('unique_customers',1),('second_week_returning_customers',1),('measured_decisions',2)]:
            self.assertEqual(after[key]-before[key],delta,key)
        self.assertEqual(after['mean_decision_seconds'],60)
        self.assertEqual(after['timed_search_conversion'],1)

    def test_schema_can_be_reapplied(self):
        main.initialize()
        main.initialize()
