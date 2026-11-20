"""Pilot measurement and opt-in post-pilot tools. No payment processing."""
import os
import time as clock
from datetime import date, datetime, time, timedelta, timezone
from uuid import UUID
from typing import Literal

from fastapi.encoders import jsonable_encoder
from fastapi import Depends, HTTPException, Query, Response
from pydantic import BaseModel, ConfigDict, Field


class DiscoveryEvent(BaseModel):
    model_config = ConfigDict(extra='forbid')
    id: UUID
    search_id: UUID
    session_id: UUID
    event: Literal['discovery_results','venue_open']
    day: date | None = None
    hour: int | None = Field(default=None, ge=0, le=23)
    sport: Literal['all','football','table_tennis','billiards'] = 'all'
    result_count: int | None = Field(default=None, ge=0, le=100000)
    venue_id: int | None = Field(default=None, gt=0)

class RecurringBooking(BaseModel):
    model_config = ConfigDict(extra='forbid')
    venue_id: int
    start_at: datetime
    weeks: int = Field(default=4, ge=1, le=4)
    customer_name: str = Field(min_length=1, max_length=120)
    customer_phone: str = Field(pattern=r'^\+?[0-9 ()-]{7,40}$')
    request_id: UUID
    # When some weeks conflict the owner must explicitly submit the selected dates.
    selected_dates: list[date] | None = Field(default=None, min_length=1, max_length=4)

class SubscriptionIn(BaseModel):
    model_config = ConfigDict(extra='forbid')
    venue_id: int
    start_at: datetime

class OutcomeIn(BaseModel):
    model_config = ConfigDict(extra='forbid')
    outcome: Literal['attended','no_show','schedule_error','unknown']


def features():
    return {'recurring_bookings': os.getenv('ENABLE_RECURRING_BOOKINGS') == 'true',
            'availability_alerts': os.getenv('ENABLE_AVAILABILITY_ALERTS') == 'true'}


def install(app, db, authenticate, admin, valid_start, owned_venue, ensure_free, is_open, booking_event, local_zone):
    from psycopg.types.json import Jsonb
    from uuid import uuid4

    def enabled(name):
        if not features()[name]:
            raise HTTPException(404, 'Bu imkoniyat hali pilot uchun ochilmagan.')

    def limit(conn, key, maximum):
        bucket = int(clock.time()) // 60
        row = conn.execute('''INSERT INTO product_rate_limits(key,bucket,count) VALUES (%s,%s,1)
            ON CONFLICT(key,bucket) DO UPDATE SET count=product_rate_limits.count+1 RETURNING count''', (key,bucket)).fetchone()
        if row['count'] > maximum:
            raise HTTPException(429, 'Juda koʻp soʻrov. Bir daqiqadan keyin qayta urinib koʻring.', headers={'Retry-After':'60'})
        conn.execute('DELETE FROM product_rate_limits WHERE bucket < %s', (bucket-1440,))

    @app.get('/product/features')
    def product_features(response: Response):
        response.headers['Cache-Control'] = 'no-store'
        return features()

    @app.post('/discovery/events', status_code=202)
    def discovery_event(body: DiscoveryEvent):
        if (body.day is None) != (body.hour is None):
            raise HTTPException(422, 'Sana va soat birga yuboriladi.')
        if body.event == 'discovery_results' and (body.result_count is None or body.venue_id is not None):
            raise HTTPException(422, 'Natijalar sonini yuboring.')
        if body.event == 'venue_open' and body.venue_id is None:
            raise HTTPException(422, 'Maydonni tanlang.')
        with db() as conn:
            if conn.execute('SELECT 1 FROM discovery_events WHERE id=%s', (body.id,)).fetchone():
                return {'accepted': True}
            limit(conn, 'discovery:global', 2000)
            limit(conn, f'discovery:{body.session_id}', 60)
            if body.venue_id is not None and not conn.execute("SELECT 1 FROM venues WHERE id=%s AND status='approved' AND NOT suspended AND deleted_at IS NULL", (body.venue_id,)).fetchone():
                raise HTTPException(404, 'Maydon topilmadi.')
            conn.execute('''INSERT INTO discovery_events(id,search_id,session_id,event,day,hour,sport,result_count,venue_id)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING''',
                (body.id,body.search_id,body.session_id,body.event,body.day,body.hour,body.sport,body.result_count,body.venue_id))
        return {'accepted': True}

    @app.post('/owner/recurring-bookings/preview')
    def preview(body: RecurringBooking, user: int = Depends(authenticate)):
        enabled('recurring_bookings')
        with db() as conn:
            limit(conn, f'recurring:{user}', 30)
            venue = owned_venue(conn, body.venue_id, user)
            return recurrence_slots(conn, body, venue)

    def recurrence_slots(conn, body, venue):
        valid_start(body.start_at)
        if not body.customer_name.strip():
            raise HTTPException(422, 'Mijoz ismini kiriting.')
        if venue['status'] != 'approved' or venue['suspended']:
            raise HTTPException(409, 'Maydon faol emas.')
        slots = []
        for week in range(body.weeks):
            start = valid_start(body.start_at + timedelta(weeks=week))
            reason = None
            if not is_open(venue['hours'], start):
                reason = 'closed'
            else:
                try:
                    ensure_free(conn, body.venue_id, start)
                except HTTPException as exc:
                    if exc.status_code != 409:
                        raise
                    reason = 'booked'
            slots.append({'start_at': start, 'day': start.astimezone(local_zone).date(), 'available': reason is None, 'reason': reason, 'price': venue['price']})
        return {'slots': slots, 'has_conflicts': any(not s['available'] for s in slots)}

    @app.post('/owner/recurring-bookings', status_code=201)
    def create_recurring(body: RecurringBooking, user: int = Depends(authenticate)):
        enabled('recurring_bookings')
        payload = body.model_dump(mode='json')
        with db() as conn:
            limit(conn, f'recurring:{user}', 30)
            conn.execute('SELECT pg_advisory_xact_lock(hashtext(%s))', (f'recurring:{user}:{body.request_id}',))
            venue = owned_venue(conn, body.venue_id, user)
            # Venue lock also serializes identical request retries.
            previous = conn.execute('SELECT payload,booking_ids FROM recurring_requests WHERE owner_id=%s AND request_id=%s', (user,body.request_id)).fetchone()
            if previous:
                if previous['payload'] != payload:
                    raise HTTPException(409, 'Bu soʻrov kaliti boshqa bron uchun ishlatilgan.')
                return {'booking_ids': previous['booking_ids'], 'replayed': True}
            result = recurrence_slots(conn, body, venue)
            dates = body.selected_dates
            if dates is None and result['has_conflicts']:
                raise HTTPException(409, jsonable_encoder({'message': 'Band sanalar bor. Saqlanadigan sanalarni aniq tanlang.', **result}))
            candidates = {s['day']: s for s in result['slots']}
            if dates is not None and (len(set(dates)) != len(dates) or any(d not in candidates for d in dates)):
                raise HTTPException(422, 'Faqat koʻrsatilgan takroriy sanalarni tanlang.')
            chosen = [candidates[d] for d in dates] if dates is not None else result['slots']
            if any(not s['available'] for s in chosen):
                raise HTTPException(409, jsonable_encoder({'message': 'Tanlangan vaqt hozir band. Qayta tekshiring.', **result}))
            ids = []
            for slot in chosen:
                row = conn.execute("""INSERT INTO bookings(venue_id,start_at,status,customer_name,customer_phone,booked_price,source)
                    VALUES (%s,%s,'confirmed',%s,%s,%s,'manual') RETURNING id""", (body.venue_id,slot['start_at'],body.customer_name.strip(),body.customer_phone,slot['price'])).fetchone()
                ids.append(row['id'])
                booking_event(conn, row['id'], user, 'created_manual_recurring')
            conn.execute('INSERT INTO recurring_requests(owner_id,request_id,payload,booking_ids) VALUES (%s,%s,%s,%s)', (user,body.request_id,Jsonb(payload),ids))
            return {'booking_ids': ids, 'replayed': False}

    @app.post('/availability-subscriptions', status_code=201)
    def subscribe(body: SubscriptionIn, user: int = Depends(authenticate)):
        enabled('availability_alerts')
        start = valid_start(body.start_at)
        with db() as conn:
            limit(conn, f'subscriptions:{user}', 30)
            conn.execute('SELECT pg_advisory_xact_lock(hashtext(%s))', (f'subscriptions:{user}',))
            active = conn.execute('SELECT COUNT(*) AS count FROM availability_subscriptions WHERE user_id=%s AND cancelled_at IS NULL AND start_at>NOW()', (user,)).fetchone()['count']
            existing = conn.execute('SELECT 1 FROM availability_subscriptions WHERE user_id=%s AND venue_id=%s AND start_at=%s AND cancelled_at IS NULL', (user,body.venue_id,start)).fetchone()
            if active >= 100 and not existing:
                raise HTTPException(409, '100 ta faol obuna chegarasi. Eski obunani oʻchiring.')
            venue = conn.execute("SELECT * FROM venues WHERE id=%s AND status='approved' AND NOT suspended AND deleted_at IS NULL FOR UPDATE", (body.venue_id,)).fetchone()
            if not venue:
                raise HTTPException(404, 'Maydon topilmadi.')
            if not is_open(venue['hours'], start):
                raise HTTPException(422, 'Maydon bu vaqtda yopiq.')
            try:
                ensure_free(conn, body.venue_id, start)
            except HTTPException as exc:
                if exc.status_code != 409:
                    raise
            else:
                raise HTTPException(409, 'Bu vaqt hozir boʻsh. Bron soʻrovini yuboring.')
            return conn.execute('''INSERT INTO availability_subscriptions(user_id,venue_id,start_at) VALUES (%s,%s,%s)
                ON CONFLICT (user_id,venue_id,start_at) WHERE cancelled_at IS NULL DO UPDATE SET user_id=EXCLUDED.user_id RETURNING id,start_at,queued_at''', (user,body.venue_id,start)).fetchone()

    @app.get('/availability-subscriptions')
    def subscriptions(response: Response, user: int = Depends(authenticate)):
        response.headers['Cache-Control'] = 'private, no-store'
        with db() as conn:
            return conn.execute('''SELECT s.id,s.venue_id,s.start_at,s.queued_at,v.name AS venue_name FROM availability_subscriptions s JOIN venues v ON v.id=s.venue_id
                WHERE s.user_id=%s AND s.cancelled_at IS NULL AND s.start_at>NOW() ORDER BY s.start_at LIMIT 100''', (user,)).fetchall()

    @app.post('/availability-subscriptions/{subscription_id}/cancel')
    def unsubscribe(subscription_id: int, user: int = Depends(authenticate)):
        with db() as conn:
            row = conn.execute('UPDATE availability_subscriptions SET cancelled_at=COALESCE(cancelled_at,NOW()) WHERE id=%s AND user_id=%s RETURNING id', (subscription_id,user)).fetchone()
            if not row:
                raise HTTPException(404, 'Obuna topilmadi.')
        return {'cancelled': True}

    @app.post('/owner/bookings/{booking_id}/outcome')
    def outcome(booking_id: int, body: OutcomeIn, user: int = Depends(authenticate)):
        with db() as conn:
            booking = conn.execute('SELECT b.* FROM bookings b JOIN venues v ON v.id=b.venue_id WHERE b.id=%s AND v.owner_telegram_id=%s FOR UPDATE OF b', (booking_id,user)).fetchone()
            if not booking:
                raise HTTPException(404, 'Bron topilmadi.')
            if booking['start_at'] + timedelta(hours=1) > datetime.now(timezone.utc):
                raise HTTPException(409, 'Natija seans tugagach qayd qilinadi.')
            if body.outcome in ('attended','no_show') and booking['status'] != 'confirmed':
                raise HTTPException(409, 'Faqat tasdiqlangan bron uchun qayd qilinadi.')
            conn.execute('''INSERT INTO booking_outcomes(booking_id,outcome,actor_id) VALUES (%s,%s,%s)
                ON CONFLICT (booking_id) DO UPDATE SET outcome=EXCLUDED.outcome,actor_id=EXCLUDED.actor_id,updated_at=NOW()''', (booking_id,body.outcome,user))
            booking_event(conn, booking_id, user, 'outcome_' + body.outcome)
        return {'outcome': body.outcome}

    @app.get('/admin/pilot')
    def pilot(response: Response, from_date: date, _: int = Depends(admin)):
        response.headers['Cache-Control'] = 'private, no-store'
        start = datetime.combine(from_date, time(), tzinfo=local_zone)
        if from_date > date.max-timedelta(days=14):
            raise HTTPException(422, 'Sanani tekshiring.')
        end = start + timedelta(days=14)
        with db() as conn:
            discovery = conn.execute('''WITH cohort AS (SELECT search_id FROM discovery_events WHERE event='discovery_results' AND created_at >= %s AND created_at < %s) SELECT COUNT(*) FILTER(WHERE event='discovery_results') AS searches,
                COUNT(*) FILTER(WHERE event='discovery_results' AND hour IS NOT NULL) AS timed_searches,
                COUNT(*) FILTER(WHERE event='venue_open') AS venue_opens,
                COUNT(DISTINCT search_id) FILTER(WHERE event='booking_request_created' AND hour IS NOT NULL AND search_id IN (SELECT search_id FROM cohort)) AS converted_timed_searches,
                COUNT(DISTINCT search_id) FILTER(WHERE event='booking_request_created' AND search_id IN (SELECT search_id FROM cohort)) AS converted_searches,
                COUNT(*) FILTER(WHERE event='booking_request_created' AND search_id IN (SELECT search_id FROM cohort)) AS attributed_requests
                FROM discovery_events WHERE created_at >= %s AND created_at < %s''', (start,end,start,end)).fetchone()
            bookings = conn.execute('''SELECT COUNT(*) AS booking_requests,COUNT(DISTINCT user_telegram_id) AS unique_customers,
                COUNT(*) FILTER(WHERE status='cancelled') AS cancellations
                FROM bookings WHERE source='app' AND created_at >= %s AND created_at < %s''', (start,end)).fetchone()
            decisions = conn.execute('''SELECT COUNT(*) AS measured_decisions,AVG(EXTRACT(EPOCH FROM (e.decided_at-b.created_at))) AS mean_decision_seconds
                FROM bookings b JOIN LATERAL (SELECT MIN(created_at) AS decided_at FROM booking_events WHERE booking_id=b.id AND action IN ('confirmed','rejected')) e ON e.decided_at IS NOT NULL
                WHERE b.source='app' AND b.created_at >= %s AND b.created_at < %s''', (start,end)).fetchone()
            outcomes = conn.execute('''SELECT o.outcome,COUNT(*) AS count FROM booking_outcomes o JOIN bookings b ON b.id=o.booking_id
                WHERE b.start_at >= %s AND b.start_at < %s GROUP BY o.outcome''', (start,end)).fetchall()
            unrecorded = conn.execute('''SELECT COUNT(*) AS unrecorded_outcomes FROM bookings b WHERE b.start_at >= %s AND b.start_at < %s
                AND b.start_at+INTERVAL '1 hour' <= NOW() AND NOT EXISTS(SELECT 1 FROM booking_outcomes o WHERE o.booking_id=b.id)''', (start,end)).fetchone()
            repeats = conn.execute('''SELECT COUNT(DISTINCT b.user_telegram_id) AS second_week_returning_customers FROM bookings b
                WHERE b.source='app' AND b.status='confirmed' AND b.start_at >= %s AND b.start_at < %s
                AND EXISTS(SELECT 1 FROM bookings first WHERE first.user_telegram_id=b.user_telegram_id AND first.source='app'
                AND first.status='confirmed' AND first.start_at >= %s AND first.start_at < %s)''', (start+timedelta(days=7),end,start,start+timedelta(days=7))).fetchone()
        return {'from_date': from_date, 'to_date': (end-timedelta(days=1)).date(), **discovery, **bookings, **decisions, **repeats, **unrecorded,
                'timed_search_conversion': discovery['converted_timed_searches']/discovery['timed_searches'] if discovery['timed_searches'] else None,
                'outcomes': outcomes, 'measurement_note': 'Qidiruv hodisalari mijoz qurilmasidan keladi; soʻrovlar mijozlar soni emas. Qayta bron tasdiqlangan seans sanasi bilan oʻlchanadi. Qayd qilinmagan natijalar nomaʼlum.'}

    def attribute_booking(conn, booking_id, search_id):
        if search_id is not None:
            conn.execute('''INSERT INTO discovery_events(id,search_id,session_id,event,day,hour,sport,booking_id)
                SELECT %s,search_id,session_id,'booking_request_created',day,hour,sport,%s
                FROM discovery_events WHERE search_id=%s AND event='discovery_results'
                AND created_at > NOW()-INTERVAL '24 hours' ON CONFLICT DO NOTHING''', (uuid4(),booking_id,search_id))
    return attribute_booking
