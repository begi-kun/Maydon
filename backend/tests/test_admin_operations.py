"""Admin operational views, privacy boundaries and durable booking history."""
import os
import unittest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from test_owner_flow import main, headers, payload


class OperationsAccessTests(unittest.TestCase):
    def test_all_operational_views_require_admin(self):
        client = TestClient(main.app)
        for path in ['/admin/attention','/admin/people','/admin/activity','/admin/notifications','/admin/bookings/1']:
            with self.subTest(path=path):
                self.assertEqual(client.get(path).status_code,401)
                self.assertEqual(client.get(path,headers=headers(101)).status_code,403)


@unittest.skipUnless(os.getenv('TEST_DATABASE_URL'), 'Disposable PostgreSQL required')
class OperationsIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.context=TestClient(main.app)
        cls.client=cls.context.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.context.__exit__(None,None,None)

    def setUp(self):
        self.owner=8101
        self.customer=8102
        self.venue=self.client.post('/venues',headers=headers(self.owner),json=payload()).json()['id']
        self.start=(datetime.now(main.UZBEKISTAN_TIME)+timedelta(days=3)).replace(hour=12,minute=0,second=0,microsecond=0)
        with main.db() as conn:
            conn.execute("INSERT INTO telegram_contacts(telegram_id,phone) VALUES (%s,'+998991234567') ON CONFLICT DO NOTHING",(self.customer,))

    def get(self,path,**params):
        result=self.client.get(path,headers=headers(999),params=params)
        self.assertEqual(result.status_code,200,result.text)
        self.assertEqual(result.headers['cache-control'],'private, no-store')
        return result.json()

    def all_notifications(self):
        rows=[]
        while True:
            page=self.get('/admin/notifications',offset=len(rows))
            rows.extend(page)
            if len(page)<50:
                return rows

    def book(self):
        self.client.post(f'/admin/venues/{self.venue}/approved',headers=headers(999))
        response=self.client.post('/bookings',headers=headers(self.customer),json={'venue_id':self.venue,'start_at':self.start.isoformat()})
        self.assertEqual(response.status_code,201,response.text)
        return response.json()['id']

    def test_timeline_records_customer_owner_payment_and_admin(self):
        booking=self.book()
        self.assertEqual(self.client.post(f'/owner/bookings/{booking}/confirmed',headers=headers(self.owner)).status_code,200)
        self.assertEqual(self.client.post(f'/owner/payments/{booking}',headers=headers(self.owner),json={'status':'deposit'}).status_code,200)
        self.assertEqual(self.client.post(f'/admin/bookings/{booking}/cancel',headers=headers(999),json={'reason':'Closed for repairs'}).status_code,200)
        detail=self.get(f'/admin/bookings/{booking}')
        self.assertTrue(detail['history_complete'])
        self.assertEqual([e['action'] for e in detail['timeline']],['created','confirmed','deposit','cancelled'])
        self.assertEqual([e['actor_id'] for e in detail['timeline']],[self.customer,self.owner,self.owner,999])
        self.assertEqual(detail['timeline'][-1]['reason'],'Closed for repairs')
        self.assertEqual(len(detail['notifications']),4)
        self.assertTrue(all(n['delivery_status']=='queued' for n in detail['notifications']))
        self.assertEqual(detail['booking']['payment_status'],'deposit')
        self.assertEqual(len(self.get('/admin/activity',entity='booking',entity_id=booking,action='cancelled')),1)
        self.assertEqual(self.get('/admin/activity',entity='booking',entity_id=booking,actor_id=self.owner),[])

    def test_legacy_history_and_expired_reminders_are_honest(self):
        with main.db() as conn:
            booking=conn.execute("INSERT INTO bookings(venue_id,user_telegram_id,start_at,status) VALUES (%s,%s,%s,'cancelled') RETURNING id",(self.venue,self.customer,self.start)).fetchone()['id']
            conn.execute("INSERT INTO notifications(recipient_id,body,reminder_booking_id,attempts,last_error) VALUES (%s,'test',%s,2,'TelegramForbiddenError')",(self.customer,booking))
        detail=self.get(f'/admin/bookings/{booking}')
        self.assertFalse(detail['history_complete'])
        self.assertEqual(detail['timeline'],[])
        self.assertEqual(detail['notifications'][0]['delivery_status'],'expired')
        self.assertNotIn(booking,[n['booking_id'] for n in self.all_notifications()])
        self.assertEqual(self.client.get('/admin/bookings/9223372036854775807',headers=headers(999)).status_code,404)

    def test_directory_search_and_relationship_filters(self):
        booking=self.book()
        self.client.get('/auth/me',headers=headers(self.owner))
        owners=self.get('/admin/people',role='owners',q=str(self.owner))
        self.assertEqual(len(owners),1)
        self.assertEqual(owners[0]['name'],'Owner')
        self.assertGreater(owners[0]['venue_count'],0)
        customers=self.get('/admin/people',q='+998991234567')
        self.assertIn(self.customer,[p['telegram_id'] for p in customers])
        self.assertIn(booking,[b['id'] for b in self.get('/admin/bookings',customer_id=self.customer)])
        self.assertIn(booking,[b['id'] for b in self.get('/admin/bookings',owner_id=self.owner)])
        self.assertEqual(self.get('/admin/bookings',customer_id=987654321),[])

    def test_manual_people_are_not_merged_and_have_creation_events(self):
        self.client.post(f'/admin/venues/{self.venue}/approved',headers=headers(999))
        ids=[]
        name=f'Manual person {self.venue}'
        for hour in [0,1]:
            result=self.client.post('/owner/manual-bookings',headers=headers(self.owner),json={'venue_id':self.venue,'start_at':(self.start+timedelta(hours=hour)).isoformat(),'customer_name':name,'customer_phone':'+998901234567'})
            self.assertEqual(result.status_code,201,result.text)
            ids.append(result.json()['id'])
        people=self.get('/admin/people',role='manual',q=name)
        self.assertEqual({p['booking_id'] for p in people},set(ids))
        self.assertTrue(all(p['telegram_id'] is None for p in people))
        self.client.post(f'/owner/manual-bookings/{ids[0]}/cancel',headers=headers(self.owner))
        detail=self.get(f'/admin/bookings/{ids[0]}')
        self.assertEqual([e['action'] for e in detail['timeline']],['created_manual','cancelled'])
        self.assertEqual(detail['notifications'],[])

    def test_attention_excludes_archives_and_resolved_notifications(self):
        booking=self.book()
        with main.db() as conn:
            active=conn.execute("INSERT INTO notifications(recipient_id,body,booking_id,attempts,last_error) VALUES (%s,'test',%s,1,'TelegramForbiddenError') RETURNING id",(self.customer,booking)).fetchone()['id']
            old=conn.execute("INSERT INTO notifications(recipient_id,body,created_at) VALUES (%s,'old',NOW()-INTERVAL '10 minutes') RETURNING id",(self.customer,)).fetchone()['id']
        attention=self.get('/admin/attention')
        self.assertGreaterEqual(attention['counts']['bookings'],1)
        self.assertGreaterEqual(attention['counts']['notifications'],2)
        rows=self.all_notifications()
        self.assertTrue({active,old}.issubset({r['id'] for r in rows}))
        with main.db() as conn:
            conn.execute('UPDATE notifications SET sent_at=NOW() WHERE id=ANY(%s)',([active,old],))
        self.assertFalse({active,old}&{r['id'] for r in self.all_notifications()})

    def test_timeline_pagination_validation_and_idempotent_schema(self):
        booking=self.book()
        with main.db() as conn:
            conn.execute(main.SCHEMA)
            for i in range(51):
                conn.execute("INSERT INTO owner_payment_events(booking_id,owner_id,payment_status) VALUES (%s,%s,'paid')",(booking,self.owner))
        first=self.get(f'/admin/bookings/{booking}')['timeline']
        second=self.get(f'/admin/bookings/{booking}',offset=50)['timeline']
        self.assertEqual((len(first),len(second)),(50,2))
        self.assertFalse({(x['kind'],x['id']) for x in first}&{(x['kind'],x['id']) for x in second})
        for path in ['/admin/people?role=invalid','/admin/activity?entity_id=0','/admin/notifications?offset=-1','/admin/bookings/1?offset=-1']:
            self.assertEqual(self.client.get(path,headers=headers(999)).status_code,422)

    def test_customer_cancellation_is_recorded(self):
        booking=self.book()
        self.assertEqual(self.client.post(f'/bookings/{booking}/cancel',headers=headers(self.customer)).status_code,200)
        detail=self.get(f'/admin/bookings/{booking}')
        self.assertEqual(detail['timeline'][-1]['action'],'cancelled')
        self.assertEqual(detail['timeline'][-1]['actor_id'],self.customer)

    def test_delivery_retry_then_success_updates_admin_views(self):
        from reminders import mark_notification_sent, mark_notification_failed
        booking=self.book()
        with main.db() as conn:
            notification=conn.execute('SELECT id FROM notifications WHERE booking_id=%s',(booking,)).fetchone()['id']
            mark_notification_failed(conn,notification,'TelegramForbiddenError')
        notice=next(n for n in self.all_notifications() if n['id']==notification)
        self.assertEqual(notice['attempts'],1)
        self.assertEqual(notice['last_error'],'TelegramForbiddenError')
        with main.db() as conn:
            mark_notification_sent(conn,notification)
            mark_notification_failed(conn,notification,'LateFailure')
        self.assertNotIn(notification,[n['id'] for n in self.all_notifications()])
        sent=self.get(f'/admin/bookings/{booking}')['notifications'][0]
        self.assertEqual(sent['delivery_status'],'sent')
        self.assertEqual(sent['attempts'],2)
        self.assertIsNone(sent['last_error'])

    def test_activity_date_is_local_and_future_filter_excludes_past(self):
        booking=self.book()
        midnight=self.start.replace(hour=0)
        with main.db() as conn:
            for stamp in [midnight-timedelta(seconds=1),midnight,midnight+timedelta(days=1)]:
                conn.execute("INSERT INTO admin_actions(admin_id,entity_type,entity_id,action,created_at) VALUES (999,'booking',%s,'cancelled',%s)",(booking,stamp))
            conn.execute("UPDATE bookings SET start_at=NOW()-INTERVAL '1 day' WHERE id=%s",(booking,))
        self.assertEqual(len(self.get('/admin/activity',entity='booking',entity_id=booking,day=midnight.date().isoformat())),1)
        self.assertEqual(self.get('/admin/bookings',booking_id=booking,upcoming='true'),[])
        for path in ['/admin/activity?day=9999-12-31','/admin/bookings?day=9999-12-31']:
            self.assertEqual(self.client.get(path,headers=headers(999)).status_code,422)
