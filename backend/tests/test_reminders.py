"""Reminder integration checks use the same disposable DB as owner-flow tests."""
import os
import unittest
import psycopg
from psycopg.rows import dict_row
from datetime import datetime, timezone
from test_owner_flow import main
from reminders import queue_reminders, pending_notifications, reminder_is_current, reminder_body


class ReminderTextTests(unittest.TestCase):
    def test_customer_details_and_local_date_rollover(self):
        body = reminder_body({'id': 12, 'name': 'Tennis club', 'address': 'Namangan',
                              'start_at': datetime(2026, 11, 11, 22, tzinfo=timezone.utc)})
        for text in ('#12', 'Tennis club', 'Namangan', '12.11.2026 · 03:00', 'UTC+5'):
            self.assertIn(text, body)


@unittest.skipUnless(os.environ.get('TEST_DATABASE_URL'), 'Disposable PostgreSQL required')
class ReminderIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.conn = psycopg.connect(main.DATABASE_URL, row_factory=dict_row)
        self.conn.execute(main.SCHEMA)
        self.conn.commit()
        # Isolate the delivery batch from notifications left by other test classes.
        # This change rolls back with the reminder test transaction.
        self.conn.execute("UPDATE notifications SET sent_at=NOW() WHERE sent_at IS NULL")
        self.venue = self.conn.execute("""INSERT INTO venues
            (name,sport,address,latitude,longitude,price,owner_telegram_id,status)
            VALUES ('Reminder pitch','football','Namangan',41,71,100000,999,'approved') RETURNING id""").fetchone()['id']

    def tearDown(self):
        self.conn.rollback()
        self.conn.close()

    def booking(self, minutes, status='confirmed'):
        return self.conn.execute("""INSERT INTO bookings(venue_id,user_telegram_id,start_at,status)
            VALUES (%s,123456,NOW() + %s * INTERVAL '1 minute',%s) RETURNING id""",
            (self.venue, minutes, status)).fetchone()['id']

    def reminders(self):
        return self.conn.execute('SELECT * FROM notifications WHERE reminder_booking_id IN (SELECT id FROM bookings WHERE venue_id=%s)', (self.venue,)).fetchall()

    def test_due_window_statuses_recipient_and_restart_deduplication(self):
        due = {self.booking(60), self.booking(20), self.booking(1)}
        for minutes, status in [(61, 'confirmed'), (0, 'confirmed'), (-1, 'confirmed'),
                                (10, 'pending'), (11, 'rejected'), (12, 'cancelled')]:
            self.booking(minutes, status)
        queue_reminders(self.conn)
        queue_reminders(self.conn)
        rows = self.reminders()
        self.assertEqual({r['reminder_booking_id'] for r in rows}, due)
        self.assertEqual(len(rows), 3)
        self.assertTrue(all(r['recipient_id'] == 123456 for r in rows))
        self.conn.execute('UPDATE notifications SET sent_at=NOW() WHERE reminder_booking_id=ANY(%s)', (list(due),))
        queue_reminders(self.conn)
        self.assertEqual(len(self.reminders()), 3)
        self.assertFalse(due & {r['reminder_booking_id'] for r in pending_notifications(self.conn)})

    def test_late_confirmation_and_retry_expiry(self):
        booking = self.booking(15, 'pending')
        queue_reminders(self.conn)
        self.assertEqual(self.reminders(), [])
        self.conn.execute("UPDATE bookings SET status='confirmed' WHERE id=%s", (booking,))
        queue_reminders(self.conn)
        self.assertTrue(reminder_is_current(self.conn, booking))
        self.assertIn(booking, {r['reminder_booking_id'] for r in pending_notifications(self.conn)})
        # A transient send failure stays queued without creating a second reminder.
        self.conn.execute("UPDATE notifications SET retry_after=NOW()+INTERVAL '1 minute' WHERE reminder_booking_id=%s", (booking,))
        queue_reminders(self.conn)
        self.assertEqual(len(self.reminders()), 1)
        self.assertNotIn(booking, {r['reminder_booking_id'] for r in pending_notifications(self.conn)})
        self.conn.execute('UPDATE notifications SET retry_after=NOW() WHERE reminder_booking_id=%s', (booking,))
        self.assertIn(booking, {r['reminder_booking_id'] for r in pending_notifications(self.conn)})
        self.conn.execute("UPDATE bookings SET start_at=NOW() WHERE id=%s", (booking,))
        self.assertFalse(reminder_is_current(self.conn, booking))
        self.assertNotIn(booking, {r['reminder_booking_id'] for r in pending_notifications(self.conn)})

    def test_cancelled_reminder_is_suppressed_and_normal_notifications_continue(self):
        booking = self.booking(30)
        queue_reminders(self.conn)
        self.conn.execute("UPDATE bookings SET status='cancelled' WHERE id=%s", (booking,))
        ordinary = self.conn.execute("INSERT INTO notifications(recipient_id,body) VALUES (123456,'Confirmation') RETURNING id").fetchone()['id']
        rows = pending_notifications(self.conn)
        self.assertFalse(reminder_is_current(self.conn, booking))
        self.assertNotIn(booking, {r['reminder_booking_id'] for r in rows})
        self.assertIn(ordinary, {r['id'] for r in rows})
