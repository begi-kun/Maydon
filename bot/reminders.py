"""Durable customer reminders shared by both booking confirmation paths."""
from datetime import timedelta, timezone


def reminder_body(booking):
    local_time = booking['start_at'].astimezone(timezone(timedelta(hours=5)))
    return (
        f'⏰ Eslatma: oʻyiningiz tez orada boshlanadi!\n'
        f'📅 Bron #{booking["id"]} — {booking["name"]}\n'
        f'🕒 {local_time:%d.%m.%Y · %H:%M} (Oʻzbekiston vaqti, UTC+5)\n'
        f'📍 {booking["address"]}\n'
        'Broningiz tasdiqlangan. Iltimos, vaqtida yetib boring.'
    )


def queue_reminders(conn):
    # Catch up after restarts and late confirmations, but never after kickoff.
    bookings = conn.execute('''
        SELECT b.id,b.user_telegram_id,b.start_at,v.name,v.address
        FROM bookings b JOIN venues v ON v.id=b.venue_id
        WHERE b.status='confirmed' AND b.start_at > NOW()
          AND b.start_at <= NOW() + INTERVAL '1 hour'
          AND NOT EXISTS (SELECT 1 FROM notifications n WHERE n.reminder_booking_id=b.id)
        ORDER BY b.start_at,b.id LIMIT 100
    ''').fetchall()
    for booking in bookings:
        conn.execute('''
            INSERT INTO notifications(recipient_id,body,reminder_booking_id)
            VALUES (%s,%s,%s) ON CONFLICT (reminder_booking_id) DO NOTHING
        ''', (booking['user_telegram_id'], reminder_body(booking), booking['id']))


def pending_notifications(conn):
    # Recheck status/time on every retry so stale reminders are never delivered.
    return conn.execute('''
        SELECT n.id,n.recipient_id,n.body,n.reminder_booking_id
        FROM notifications n LEFT JOIN bookings b ON b.id=n.reminder_booking_id
        WHERE n.sent_at IS NULL AND n.retry_after <= NOW() AND
          (n.reminder_booking_id IS NULL OR (b.status='confirmed' AND b.start_at > NOW()))
        ORDER BY n.retry_after,n.id LIMIT 30
    ''').fetchall()


def reminder_is_current(conn, booking_id):
    return conn.execute("SELECT 1 FROM bookings WHERE id=%s AND status='confirmed' AND start_at > NOW()",
                        (booking_id,)).fetchone() is not None
