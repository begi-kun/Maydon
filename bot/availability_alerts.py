"""One notification per opt-in subscription; the notification never reserves a slot."""
import os
import re
from datetime import timedelta, timezone


def slot_is_open(hours, start):
    value = hours.strip()
    if not value or value == '24/7':
        return True
    match = re.fullmatch(r'(\d{2}):00\s*[-–—]\s*(\d{2}):00', value)
    if not match:
        return False
    opening, closing = map(int, match.groups())
    if opening > 23 or closing > 24 or opening == closing:
        return False
    hour = start.astimezone(timezone(timedelta(hours=5))).hour
    return opening <= hour < closing if opening < closing else hour >= opening or hour < closing


def subscription_is_current(conn, subscription_id):
    if os.getenv('ENABLE_AVAILABILITY_ALERTS') != 'true':
        return False
    row = conn.execute('''SELECT v.hours,s.start_at FROM availability_subscriptions s JOIN venues v ON v.id=s.venue_id
        WHERE s.id=%s AND s.cancelled_at IS NULL AND s.start_at > NOW()+INTERVAL '5 minutes'
        AND v.status='approved' AND NOT v.suspended AND v.deleted_at IS NULL
        AND NOT EXISTS(SELECT 1 FROM bookings b WHERE b.venue_id=s.venue_id AND b.start_at=s.start_at AND b.status IN ('pending','confirmed'))
        AND NOT EXISTS(SELECT 1 FROM owner_blocks ob WHERE ob.venue_id=s.venue_id AND ob.start_at=s.start_at)''', (subscription_id,)).fetchone()
    return row is not None and slot_is_open(row['hours'], row['start_at'])


def queue_availability_alerts(conn):
    if os.getenv('ENABLE_AVAILABILITY_ALERTS') != 'true':
        return
    rows = conn.execute('''SELECT s.id,s.user_id,s.start_at,v.name,v.hours FROM availability_subscriptions s
        JOIN venues v ON v.id=s.venue_id WHERE s.cancelled_at IS NULL AND s.queued_at IS NULL AND s.next_check_at<=NOW()
        AND s.start_at > NOW()+INTERVAL '5 minutes' AND v.status='approved' AND NOT v.suspended AND v.deleted_at IS NULL
        AND NOT EXISTS(SELECT 1 FROM bookings b WHERE b.venue_id=s.venue_id AND b.start_at=s.start_at AND b.status IN ('pending','confirmed'))
        AND NOT EXISTS(SELECT 1 FROM owner_blocks ob WHERE ob.venue_id=s.venue_id AND ob.start_at=s.start_at)
        ORDER BY s.next_check_at,s.start_at,s.id LIMIT 100''').fetchall()
    for row in rows:
        # Use the same venue-then-subscription lock order as subscription creation.
        venue = conn.execute('SELECT hours FROM venues WHERE id=(SELECT venue_id FROM availability_subscriptions WHERE id=%s) FOR UPDATE SKIP LOCKED', (row['id'],)).fetchone()
        if not venue:
            continue
        current = conn.execute('SELECT queued_at,cancelled_at FROM availability_subscriptions WHERE id=%s FOR UPDATE SKIP LOCKED', (row['id'],)).fetchone()
        if not current or current['queued_at'] is not None or current['cancelled_at'] is not None:
            continue
        if not subscription_is_current(conn, row['id']):
            conn.execute("UPDATE availability_subscriptions SET next_check_at=NOW()+INTERVAL '1 minute' WHERE id=%s", (row['id'],))
            continue
        local = row['start_at'].astimezone(timezone(timedelta(hours=5)))
        body = f'🔔 {row["name"]}: {local:%d.%m.%Y · %H:%M} (UTC+5) vaqti boʻshadi.\nBu xabar joyni band qilmaydi. Bronnda bron yuboring; server vaqtni qayta tekshiradi va egasi tasdiqlaydi.'
        conn.execute('''INSERT INTO notifications(recipient_id,body,availability_subscription_id) VALUES (%s,%s,%s)
            ON CONFLICT (availability_subscription_id) DO NOTHING''', (row['user_id'],body,row['id']))
        conn.execute('UPDATE availability_subscriptions SET queued_at=NOW() WHERE id=%s', (row['id'],))
