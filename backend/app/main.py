"""MAYDON API. Requires PostgreSQL and validated Telegram WebApp initData."""
import hashlib
import hmac
import json
import os
import re
import time
import base64
import binascii
from io import BytesIO
from datetime import date, datetime, time as day_time, timedelta, timezone
from urllib.parse import parse_qsl
from contextlib import contextmanager
from typing import Literal

import psycopg
from psycopg.rows import dict_row
from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, ValidationError, field_validator
from PIL import Image, ImageOps, UnidentifiedImageError
from starlette.concurrency import run_in_threadpool

DATABASE_URL = os.getenv('DATABASE_URL', '')
BOT_TOKEN = os.getenv('BOT_TOKEN', '')
ADMIN_ID = os.getenv('ADMIN_TELEGRAM_ID', '')
ORIGINS = [x.strip() for x in os.getenv('CORS_ORIGINS', '').split(',') if x.strip()]
UZBEKISTAN_TIME = timezone(timedelta(hours=5))

def booking_time_label(value: datetime) -> str:
    return value.astimezone(UZBEKISTAN_TIME).strftime('%d.%m.%Y · %H:%M') + ' (Oʻzbekiston vaqti, UTC+5)'

app = FastAPI(title='MAYDON API', docs_url=None, redoc_url=None)
app.add_middleware(CORSMiddleware, allow_origins=ORIGINS, allow_credentials=False, allow_methods=['GET','POST'], allow_headers=['Content-Type','X-Telegram-Init-Data'])

@contextmanager
def db():
    if not DATABASE_URL:
        raise HTTPException(503, 'Database not configured')
    with psycopg.connect(DATABASE_URL, row_factory=dict_row) as conn:
        yield conn

def telegram_identity(init_data: str) -> dict:
    if not BOT_TOKEN or not init_data:
        raise HTTPException(401, 'Telegram authentication required')
    try:
        pairs = parse_qsl(init_data, keep_blank_values=True, strict_parsing=True)
        fields = dict(pairs)
        if len(fields) != len(pairs):
            raise ValueError('Duplicate fields')
        received_hash = fields.pop('hash')
        auth_date = int(fields['auth_date'])
        if auth_date > time.time() + 30 or time.time() - auth_date > 3600:
            raise ValueError('Expired Telegram login')
        data_check = '\n'.join(f'{key}={fields[key]}' for key in sorted(fields))
        secret = hmac.new(b'WebAppData', BOT_TOKEN.encode(), hashlib.sha256).digest()
        calculated = hmac.new(secret, data_check.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(received_hash, calculated):
            raise ValueError('Invalid signature')
        user = json.loads(fields['user'])
        user_id = user['id']
        if type(user_id) is not int or user_id <= 0:
            raise ValueError('Invalid user')
        return {'id': user_id, 'first_name': str(user.get('first_name', '')), 'username': str(user.get('username', ''))}
    except (KeyError, ValueError, TypeError, json.JSONDecodeError):
        raise HTTPException(401, 'Invalid Telegram authentication')

def authenticate(init_data: str = Header(default='', alias='X-Telegram-Init-Data')) -> int:
    return telegram_identity(init_data)['id']

@app.get('/auth/me')
def auth_me(response: Response, init_data: str = Header(default='', alias='X-Telegram-Init-Data')):
    user = telegram_identity(init_data)
    response.headers['Cache-Control'] = 'private, no-store'
    if DATABASE_URL:
        with db() as conn:
            conn.execute('INSERT INTO telegram_profiles(telegram_id,first_name,username) VALUES (%s,%s,%s) ON CONFLICT (telegram_id) DO UPDATE SET first_name=EXCLUDED.first_name,username=EXCLUDED.username', (user['id'],user['first_name'],user['username']))
    return {**user, 'admin': bool(ADMIN_ID and str(user['id']) == ADMIN_ID)}

@app.get('/auth/config')
def auth_config():
    return {'bot_username': os.getenv('BOT_USERNAME', '')}

@app.get('/auth/contact')
def contact_status(response: Response, user: int = Depends(authenticate)):
    response.headers['Cache-Control'] = 'private, no-store'
    with db() as conn:
        contact = conn.execute('SELECT phone FROM telegram_contacts WHERE telegram_id=%s', (user,)).fetchone()
    return {'phone': contact['phone'] if contact else None, 'shared': bool(contact)}

def admin(user: int = Depends(authenticate)) -> int:
    if not ADMIN_ID or str(user) != ADMIN_ID:
        raise HTTPException(403, 'Admin only')
    return user

def hours_window(value: str):
    # Empty legacy hours retain their existing all-day availability.
    if not value.strip() or value.strip() == '24/7':
        return (0, 24)
    match = re.fullmatch(r'(\d{2}):00\s*[-–—]\s*(\d{2}):00', value.strip())
    if not match:
        raise ValueError('Ish vaqti: 08:00–23:00 yoki 24/7. Faqat toʻliq soatlar.')
    opening, closing = map(int, match.groups())
    if opening > 23 or closing > 24 or opening == closing:
        raise ValueError('Ish vaqtini tekshiring. Kun boʻyi uchun 24/7 tanlang.')
    return opening, closing


def is_open(hours: str, start: datetime) -> bool:
    try:
        opening, closing = hours_window(hours)
    except ValueError:
        return False
    hour = start.astimezone(UZBEKISTAN_TIME).hour
    return opening <= hour < closing if opening < closing else hour >= opening or hour < closing


def valid_start(start: datetime) -> datetime:
    if start.tzinfo is None:
        raise HTTPException(422, 'Timezone required')
    start = start.astimezone(timezone.utc)
    now = datetime.now(timezone.utc)
    if start <= now + timedelta(minutes=5) or start > now + timedelta(days=60):
        raise HTTPException(422, 'Choose a time between 5 minutes and 60 days ahead')
    if start.minute or start.second or start.microsecond:
        raise HTTPException(422, 'Bookings start on the hour')
    return start


def ensure_free(conn, venue_id: int, start: datetime):
    if conn.execute("SELECT 1 FROM bookings WHERE venue_id=%s AND start_at=%s AND status IN ('pending','confirmed')", (venue_id, start)).fetchone() or conn.execute('SELECT 1 FROM owner_blocks WHERE venue_id=%s AND start_at=%s', (venue_id, start)).fetchone():
        raise HTTPException(409, 'Bu vaqt band. Boshqa vaqtni tanlang.')


class VenueIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    sport: Literal['football','table_tennis','billiards']
    address: str = Field(min_length=5, max_length=300)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    price: int = Field(ge=0, le=100000000)
    phone: str = Field(default='', max_length=40)
    hours: str = Field(default='', max_length=120)
    photos: list[str] = Field(min_length=1, max_length=5)

    @field_validator('hours')
    @classmethod
    def validate_hours(cls, value):
        hours_window(value)
        return value.strip()


class VenueEdit(VenueIn):
    photos: list[str] = Field(default_factory=list, max_length=5)
    keep_photos: list[int] = Field(default_factory=list, max_length=5)

def prepare_photo(encoded: str) -> bytes:
    if len(encoded) > 1400000:
        raise HTTPException(413, 'Each photo must be smaller than 1 MB')
    try:
        raw = base64.b64decode(encoded, validate=True)
        with Image.open(BytesIO(raw)) as source:
            if source.format not in ('JPEG', 'PNG', 'WEBP') or source.width * source.height > 20000000:
                raise ValueError('Unsupported image')
            if min(source.size) < 200:
                raise ValueError('Photo is too small')
            photo = ImageOps.exif_transpose(source).convert('RGB')
            photo.thumbnail((1600, 1600))
            output = BytesIO()
            photo.save(output, format='JPEG', quality=85)
            return output.getvalue()
    except (ValueError, binascii.Error, UnidentifiedImageError, OSError, Image.DecompressionBombError):
        raise HTTPException(422, 'Upload valid JPEG, PNG or WebP pitch photos, at least 200 pixels per side')

class AdminReason(BaseModel):
    reason: str = Field(min_length=3, max_length=500)

    @field_validator('reason', mode='before')
    @classmethod
    def trim_reason(cls, value):
        return value.strip() if isinstance(value, str) else value

class BookingIn(BaseModel):
    venue_id: int
    start_at: datetime

SCHEMA = '''
CREATE TABLE IF NOT EXISTS venues (
 id BIGSERIAL PRIMARY KEY, name TEXT NOT NULL, sport TEXT NOT NULL,
 address TEXT NOT NULL, latitude DOUBLE PRECISION NOT NULL, longitude DOUBLE PRECISION NOT NULL,
 price INTEGER NOT NULL, phone TEXT NOT NULL DEFAULT '', hours TEXT NOT NULL DEFAULT '',
 owner_telegram_id BIGINT NOT NULL, status TEXT NOT NULL DEFAULT 'pending'
 CHECK (status IN ('pending','approved','rejected')));
CREATE TABLE IF NOT EXISTS bookings (
 id BIGSERIAL PRIMARY KEY, venue_id BIGINT NOT NULL REFERENCES venues(id),
 user_telegram_id BIGINT NOT NULL, start_at TIMESTAMPTZ NOT NULL,
 status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','confirmed','rejected','cancelled')),
 created_at TIMESTAMPTZ NOT NULL DEFAULT NOW());
CREATE UNIQUE INDEX IF NOT EXISTS bookings_one_active_slot ON bookings(venue_id,start_at) WHERE status IN ('pending','confirmed');
CREATE TABLE IF NOT EXISTS notifications (id BIGSERIAL PRIMARY KEY, recipient_id BIGINT NOT NULL, body TEXT NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), sent_at TIMESTAMPTZ);
ALTER TABLE notifications ADD COLUMN IF NOT EXISTS reminder_booking_id BIGINT REFERENCES bookings(id);
ALTER TABLE notifications ADD COLUMN IF NOT EXISTS retry_after TIMESTAMPTZ NOT NULL DEFAULT NOW();
CREATE UNIQUE INDEX IF NOT EXISTS notifications_one_booking_reminder ON notifications(reminder_booking_id);
CREATE INDEX IF NOT EXISTS bookings_confirmed_start ON bookings(start_at) WHERE status='confirmed';
CREATE INDEX IF NOT EXISTS bookings_venue_start ON bookings(venue_id,start_at);
CREATE INDEX IF NOT EXISTS bookings_user ON bookings(user_telegram_id);
CREATE TABLE IF NOT EXISTS venue_photos (
 id BIGSERIAL PRIMARY KEY, venue_id BIGINT NOT NULL REFERENCES venues(id) ON DELETE CASCADE,
 image BYTEA NOT NULL);
CREATE INDEX IF NOT EXISTS venue_photos_venue ON venue_photos(venue_id);
ALTER TABLE venues ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;
ALTER TABLE venues ADD COLUMN IF NOT EXISTS suspended BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE venues ADD COLUMN IF NOT EXISTS review_reason TEXT;
CREATE TABLE IF NOT EXISTS admin_actions (
 id BIGSERIAL PRIMARY KEY, admin_id BIGINT NOT NULL, entity_type TEXT NOT NULL,
 entity_id BIGINT NOT NULL, action TEXT NOT NULL, reason TEXT,
 created_at TIMESTAMPTZ NOT NULL DEFAULT NOW());
ALTER TABLE bookings ADD COLUMN IF NOT EXISTS cancellation_reason TEXT;
ALTER TABLE bookings ADD COLUMN IF NOT EXISTS customer_phone TEXT;
ALTER TABLE bookings ADD COLUMN IF NOT EXISTS booked_price INTEGER CHECK (booked_price >= 0);
ALTER TABLE bookings ALTER COLUMN user_telegram_id DROP NOT NULL;
ALTER TABLE bookings ADD COLUMN IF NOT EXISTS customer_name TEXT NOT NULL DEFAULT '';
ALTER TABLE bookings ADD COLUMN IF NOT EXISTS source TEXT NOT NULL DEFAULT 'app';
ALTER TABLE bookings ADD COLUMN IF NOT EXISTS payment_status TEXT NOT NULL DEFAULT 'unpaid'
 CHECK (payment_status IN ('unpaid','deposit','paid'));
CREATE TABLE IF NOT EXISTS owner_blocks (
 id BIGSERIAL PRIMARY KEY, venue_id BIGINT NOT NULL REFERENCES venues(id),
 start_at TIMESTAMPTZ NOT NULL, reason TEXT NOT NULL DEFAULT '', UNIQUE(venue_id,start_at));
CREATE TABLE IF NOT EXISTS owner_payment_events (
 id BIGSERIAL PRIMARY KEY, booking_id BIGINT NOT NULL REFERENCES bookings(id),
 owner_id BIGINT NOT NULL, payment_status TEXT NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW());
CREATE TABLE IF NOT EXISTS telegram_contacts (
 telegram_id BIGINT PRIMARY KEY, phone TEXT NOT NULL, shared_at TIMESTAMPTZ NOT NULL DEFAULT NOW());
CREATE TABLE IF NOT EXISTS telegram_profiles (
 telegram_id BIGINT PRIMARY KEY, first_name TEXT NOT NULL DEFAULT '', username TEXT NOT NULL DEFAULT '');
CREATE TABLE IF NOT EXISTS booking_events (
 id BIGSERIAL PRIMARY KEY, booking_id BIGINT NOT NULL REFERENCES bookings(id),
 actor_id BIGINT, action TEXT NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW());
CREATE INDEX IF NOT EXISTS booking_events_booking ON booking_events(booking_id,id);
CREATE INDEX IF NOT EXISTS admin_actions_created ON admin_actions(created_at DESC,id DESC);
ALTER TABLE notifications ADD COLUMN IF NOT EXISTS booking_id BIGINT REFERENCES bookings(id);
ALTER TABLE notifications ADD COLUMN IF NOT EXISTS attempts INTEGER NOT NULL DEFAULT 0;
ALTER TABLE notifications ADD COLUMN IF NOT EXISTS last_error TEXT;
CREATE INDEX IF NOT EXISTS notifications_booking ON notifications(booking_id);
CREATE INDEX IF NOT EXISTS notifications_unsent_created ON notifications(created_at,id) WHERE sent_at IS NULL;
CREATE INDEX IF NOT EXISTS venues_owner ON venues(owner_telegram_id);
CREATE INDEX IF NOT EXISTS owner_payment_events_booking ON owner_payment_events(booking_id,id);
CREATE INDEX IF NOT EXISTS admin_actions_entity ON admin_actions(entity_type,entity_id);
CREATE TABLE IF NOT EXISTS contact_return_links (
 telegram_id BIGINT PRIMARY KEY, venue_id BIGINT, slot BIGINT, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW());
'''

@app.on_event('startup')
def initialize():
    if not DATABASE_URL or not BOT_TOKEN or not ORIGINS:
        raise RuntimeError('Set DATABASE_URL, BOT_TOKEN, and CORS_ORIGINS before starting')
    with db() as conn:
        conn.execute(SCHEMA)

@app.get('/health')
def health():
    # Bound both connection establishment and the probe query during outages.
    # Do not expose connection strings or database exception details publicly.
    headers = {'Cache-Control': 'no-store'}
    if not DATABASE_URL:
        return JSONResponse({'status': 'unavailable'}, status_code=503, headers=headers)
    try:
        with psycopg.connect(DATABASE_URL, connect_timeout=3,
                             options='-c statement_timeout=3000') as conn:
            conn.execute('SELECT 1')
    except psycopg.Error:
        return JSONResponse({'status': 'unavailable'}, status_code=503, headers=headers)
    return JSONResponse({'status': 'ok'}, headers=headers)

@app.get('/venues')
def venues(sport: str | None = None, available_at: datetime | None = None):
    start = valid_start(available_at) if available_at is not None else None
    query = """SELECT id,name,sport,address,latitude,longitude,price,phone,hours,
        ARRAY(SELECT p.id FROM venue_photos p WHERE p.venue_id=venues.id ORDER BY p.id) AS photos
        FROM venues WHERE deleted_at IS NULL AND NOT suspended AND status=%s"""
    params = ['approved']
    if sport:
        query += ' AND sport=%s'
        params.append(sport)
    if start:
        query += """ AND NOT EXISTS (SELECT 1 FROM bookings b WHERE b.venue_id=venues.id
            AND b.start_at=%s AND b.status IN ('pending','confirmed'))
            AND NOT EXISTS (SELECT 1 FROM owner_blocks ob WHERE ob.venue_id=venues.id AND ob.start_at=%s)"""
        params.extend([start, start])
    query += ' ORDER BY id DESC'
    with db() as conn:
        rows = conn.execute(query, params).fetchall()
    return [row for row in rows if not start or is_open(row['hours'], start)]

@app.get('/venues/{venue_id}/availability')
def availability(venue_id: int, day: date):
    local_zone = UZBEKISTAN_TIME
    now = datetime.now(timezone.utc)
    start = datetime.combine(day, day_time(), tzinfo=local_zone)
    if day < now.astimezone(local_zone).date() or day > (now + timedelta(days=60)).astimezone(local_zone).date():
        raise HTTPException(422, 'Choose a date within the next 60 days')
    with db() as conn:
        venue = conn.execute('SELECT hours FROM venues WHERE deleted_at IS NULL AND NOT suspended AND id=%s AND status=%s', (venue_id, 'approved')).fetchone()
        if not venue:
            raise HTTPException(404, 'Venue not found')
        busy = conn.execute("SELECT start_at FROM bookings WHERE venue_id=%s AND status IN ('pending','confirmed') AND start_at >= %s AND start_at < %s", (venue_id, start, start + timedelta(days=1))).fetchall()
        blocks = conn.execute('SELECT start_at FROM owner_blocks WHERE venue_id=%s AND start_at >= %s AND start_at < %s', (venue_id, start, start + timedelta(days=1))).fetchall()
    reserved = {row['start_at'] for row in busy + blocks}
    slots = []
    for hour in range(24):
        instant = start + timedelta(hours=hour)
        status = 'past' if instant <= now + timedelta(minutes=5) else 'unavailable' if instant > now + timedelta(days=60) else 'booked' if instant in reserved else 'closed' if not is_open(venue['hours'], instant) else 'available'
        slots.append({'start_at': instant.isoformat(), 'label': f'{hour:02}:00', 'status': status})
    return {'day': day.isoformat(), 'timezone': 'Asia/Tashkent', 'hours': venue['hours'], 'slots': slots}

@app.post('/venues', status_code=201)
async def request_venue(request: Request, user: int = Depends(authenticate)):
    venue = await read_venue(request, VenueIn)
    return await run_in_threadpool(save_venue, venue, user)

async def read_venue(request: Request, model):
    body = bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body) > 7500000:
            raise HTTPException(413, 'Photo submission is too large')
    try:
        return model.model_validate_json(body)
    except ValidationError:
        raise HTTPException(422, 'Check venue details and include 1–5 pitch photos')

@app.post('/owner/venues/{venue_id}/edit')
async def edit_venue(venue_id: int, request: Request, user: int = Depends(authenticate)):
    venue = await read_venue(request, VenueEdit)
    return await run_in_threadpool(update_venue, venue_id, venue, user)

def update_venue(venue_id: int, venue: VenueEdit, user: int):
    kept = list(dict.fromkeys(venue.keep_photos))
    if not 1 <= len(kept) + len(venue.photos) <= 5:
        raise HTTPException(422, 'Keep or upload 1–5 pitch photos')
    with db() as conn:
        row = conn.execute('SELECT id FROM venues WHERE id=%s AND owner_telegram_id=%s AND deleted_at IS NULL FOR UPDATE', (venue_id, user)).fetchone()
        if not row:
            raise HTTPException(404, 'Your pitch was not found')
        active = conn.execute("SELECT start_at FROM bookings WHERE venue_id=%s AND status IN ('pending','confirmed') AND start_at + INTERVAL '1 hour' > NOW()", (venue_id,)).fetchall()
        if any(not is_open(venue.hours, row['start_at']) for row in active):
            raise HTTPException(409, 'Yangi ish vaqti mavjud bronlarga mos emas.')
        existing = {p['id'] for p in conn.execute('SELECT id FROM venue_photos WHERE venue_id=%s', (venue_id,)).fetchall()}
        if not set(kept).issubset(existing):
            raise HTTPException(422, 'Photo does not belong to this pitch')
        photos = [prepare_photo(photo) for photo in venue.photos]
        conn.execute("UPDATE venues SET name=%s,sport=%s,address=%s,latitude=%s,longitude=%s,price=%s,phone=%s,hours=%s,status='pending',review_reason=NULL WHERE id=%s", (*venue.model_dump(exclude={'photos', 'keep_photos'}).values(), venue_id))
        conn.execute('DELETE FROM venue_photos WHERE venue_id=%s AND NOT (id = ANY(%s::bigint[]))', (venue_id, kept))
        for photo in photos:
            conn.execute('INSERT INTO venue_photos(venue_id,image) VALUES (%s,%s)', (venue_id, photo))
        if ADMIN_ID:
            conn.execute('INSERT INTO notifications(recipient_id,body) VALUES (%s,%s)', (int(ADMIN_ID), f'✏️ Maydon yangilandi #{venue_id}: {venue.name}. Qayta tekshiring. /admin'))
    return {'id': venue_id, 'status': 'pending'}

@app.post('/owner/venues/{venue_id}/delete')
def delete_venue(venue_id: int, user: int = Depends(authenticate)):
    with db() as conn:
        row = conn.execute('SELECT id FROM venues WHERE id=%s AND owner_telegram_id=%s AND deleted_at IS NULL FOR UPDATE', (venue_id, user)).fetchone()
        if not row:
            raise HTTPException(404, 'Your pitch was not found')
        active = conn.execute("SELECT 1 FROM bookings WHERE venue_id=%s AND status IN ('pending','confirmed') AND start_at + INTERVAL '1 hour' > NOW() LIMIT 1", (venue_id,)).fetchone()
        if active:
            raise HTTPException(409, 'Kelgusi yoki davom etayotgan bronlar bor. Ular yakunlanmaguncha maydonni oʻchirib boʻlmaydi.')
        conn.execute('UPDATE venues SET deleted_at=NOW() WHERE id=%s', (venue_id,))
    return {'status': 'deleted'}

def save_venue(venue: VenueIn, user: int):
    photos = [prepare_photo(photo) for photo in venue.photos]
    with db() as conn:
        result = conn.execute('''INSERT INTO venues(name,sport,address,latitude,longitude,price,phone,hours,owner_telegram_id)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id''', (*venue.model_dump(exclude={'photos'}).values(),user)).fetchone()
        for photo in photos:
            conn.execute('INSERT INTO venue_photos(venue_id,image) VALUES (%s,%s)', (result['id'], photo))
        if ADMIN_ID:
            conn.execute('INSERT INTO notifications(recipient_id,body) VALUES (%s,%s)', (int(ADMIN_ID), f'🏟 Yangi maydon arizasi #{result["id"]}: {venue.name}. /admin'))
    return {'id':result['id'],'status':'pending'}

@app.get('/photos/{photo_id}')
def get_photo(photo_id: int, init_data: str = Header(default='', alias='X-Telegram-Init-Data')):
    with db() as conn:
        row = conn.execute('SELECT p.image,v.status,v.owner_telegram_id,v.suspended,v.deleted_at FROM venue_photos p JOIN venues v ON v.id=p.venue_id WHERE p.id=%s', (photo_id,)).fetchone()
    if not row:
        raise HTTPException(404, 'Photo not found')
    if row['status'] != 'approved' or row['suspended'] or row['deleted_at']:
        user = telegram_identity(init_data)['id']
        if user != row['owner_telegram_id'] and str(user) != ADMIN_ID:
            raise HTTPException(404, 'Photo not found')
    return Response(bytes(row['image']), media_type='image/jpeg', headers={'Cache-Control': 'private, no-store', 'X-Content-Type-Options': 'nosniff'})

def booking_event(conn, booking_id, actor, action):
    conn.execute('INSERT INTO booking_events(booking_id,actor_id,action) VALUES (%s,%s,%s)', (booking_id,actor,action))

def audit(conn, actor, entity, item_id, action, reason=None):
    conn.execute('INSERT INTO admin_actions(admin_id,entity_type,entity_id,action,reason) VALUES (%s,%s,%s,%s,%s)',
                 (actor, entity, item_id, action, reason))

@app.get('/admin/venues')
def admin_venues(response: Response, status: Literal['all','pending','approved','rejected','suspended','archived'] = 'pending',
                 q: str = Query(default='', max_length=120), offset: int = Query(default=0, ge=0), _: int = Depends(admin)):
    response.headers['Cache-Control'] = 'private, no-store'
    clauses, params = [], []
    if status == 'archived':
        clauses.append('deleted_at IS NOT NULL')
    elif status != 'all':
        clauses.append('deleted_at IS NULL')
        if status == 'suspended':
            clauses.append('suspended')
        else:
            clauses.append('status=%s'); params.append(status)
    if q.strip():
        clauses.append("(name ILIKE %s OR address ILIKE %s OR id::text=%s OR owner_telegram_id::text=%s)")
        params.extend([f'%{q.strip()}%', f'%{q.strip()}%', q.strip(), q.strip()])
    where = ' AND '.join(clauses) or 'TRUE'
    with db() as conn:
        return conn.execute(f"SELECT *, ARRAY(SELECT p.id FROM venue_photos p WHERE p.venue_id=venues.id ORDER BY p.id) AS photos FROM venues WHERE {where} ORDER BY id DESC LIMIT 50 OFFSET %s", (*params, offset)).fetchall()

@app.post('/admin/venues/{venue_id}/{decision}')
def decide_venue(venue_id: int, decision: Literal['approved','rejected','suspend','resume'],
                 body: AdminReason | None = None, actor: int = Depends(admin)):
    if decision in ('rejected', 'suspend') and body is None:
        raise HTTPException(422, 'Sababni kiriting (3–500 belgi).')
    reason = body.reason if body else None
    with db() as conn:
        info = conn.execute('SELECT * FROM venues WHERE id=%s AND deleted_at IS NULL FOR UPDATE', (venue_id,)).fetchone()
        if not info:
            raise HTTPException(404, 'Maydon topilmadi.')
        if decision in ('approved', 'rejected'):
            if info['status'] != 'pending':
                raise HTTPException(409, 'Ariza allaqachon koʻrib chiqilgan. Roʻyxatni yangilang.')
            conn.execute('UPDATE venues SET status=%s,review_reason=%s WHERE id=%s', (decision, reason, venue_id))
        else:
            if info['suspended'] == (decision == 'suspend'):
                raise HTTPException(409, 'Maydon holati allaqachon oʻzgargan. Roʻyxatni yangilang.')
            conn.execute('UPDATE venues SET suspended=%s WHERE id=%s', (decision == 'suspend', venue_id))
        audit(conn, actor, 'venue', venue_id, decision, reason)
        labels = {'approved':'Tasdiqlandi', 'rejected':'Rad etildi', 'suspend':'Vaqtincha toʻxtatildi', 'resume':'Toʻxtatish olib tashlandi'}
        message = f'🏟 {info["name"]}: {labels[decision]}.' + (f'\nSabab: {reason}' if reason else '')
        conn.execute('INSERT INTO notifications(recipient_id,body) VALUES (%s,%s)', (info['owner_telegram_id'], message))
    return {'status': decision}

@app.get('/admin/bookings')
def admin_bookings(response: Response, status: Literal['all','pending','confirmed','rejected','cancelled'] = 'all',
                   day: date | None = None, venue_id: int | None = None, booking_id: int | None = None,
                   customer_id: int | None = None, owner_id: int | None = None, upcoming: bool = False,
                   offset: int = Query(default=0, ge=0), _: int = Depends(admin)):
    response.headers['Cache-Control'] = 'private, no-store'
    clauses, params = [], []
    for field, value in [('b.status', status if status != 'all' else None), ('b.venue_id', venue_id), ('b.id', booking_id), ('b.user_telegram_id', customer_id), ('v.owner_telegram_id', owner_id)]:
        if value is not None:
            clauses.append(f'{field}=%s'); params.append(value)
    if upcoming:
        clauses.append('b.start_at>NOW()')
    if day:
        if day == date.max:
            raise HTTPException(422, 'Sanani tekshiring.')
        start = datetime.combine(day, day_time(), tzinfo=UZBEKISTAN_TIME)
        clauses.append('b.start_at >= %s AND b.start_at < %s'); params.extend([start, start + timedelta(days=1)])
    where = ' AND '.join(clauses) or 'TRUE'
    with db() as conn:
        return conn.execute(f"SELECT b.*,v.name AS venue_name,v.owner_telegram_id FROM bookings b JOIN venues v ON v.id=b.venue_id WHERE {where} ORDER BY b.start_at DESC,b.id DESC LIMIT 50 OFFSET %s", (*params, offset)).fetchall()

@app.post('/admin/bookings/{booking_id}/cancel')
def admin_cancel(booking_id: int, body: AdminReason, actor: int = Depends(admin)):
    with db() as conn:
        row = conn.execute("UPDATE bookings SET status='cancelled',cancellation_reason=%s WHERE id=%s AND status IN ('pending','confirmed') AND start_at > NOW() RETURNING *", (body.reason, booking_id)).fetchone()
        if not row:
            raise HTTPException(409, 'Faqat kelgusi faol bronni bekor qilish mumkin. Roʻyxatni yangilang.')
        venue = conn.execute('SELECT name,owner_telegram_id FROM venues WHERE id=%s', (row['venue_id'],)).fetchone()
        audit(conn, actor, 'booking', booking_id, 'cancelled', body.reason)
        booking_event(conn, booking_id, actor, 'cancelled')
        message = f'📅 Bron #{booking_id} — {venue["name"]} admin tomonidan bekor qilindi.\n{booking_time_label(row["start_at"])}\nSabab: {body.reason}'
        for recipient in {row['user_telegram_id'], venue['owner_telegram_id']} - {None}:
            conn.execute('INSERT INTO notifications(recipient_id,body,booking_id) VALUES (%s,%s,%s)', (recipient, message,booking_id))
    return {'status': 'cancelled'}

@app.post('/bookings', status_code=201)
def book(booking: BookingIn, user: int = Depends(authenticate)):
    start = valid_start(booking.start_at)
    with db() as conn:
        # Serialize requests per venue, preventing concurrent overlapping slots.
        contact = conn.execute('SELECT phone FROM telegram_contacts WHERE telegram_id=%s', (user,)).fetchone()
        if not contact:
            raise HTTPException(428, 'Bron qilishdan oldin Telegram orqali oʻz telefon raqamingizni ulashing.')
        venue = conn.execute('SELECT id,price,hours FROM venues WHERE deleted_at IS NULL AND NOT suspended AND id=%s AND status=%s FOR UPDATE', (booking.venue_id,'approved')).fetchone()
        if not venue: raise HTTPException(404,'Venue not found')
        if not is_open(venue['hours'], start):
            raise HTTPException(422, 'Maydon bu vaqtda yopiq.')
        ensure_free(conn, booking.venue_id, start)
        row = conn.execute('INSERT INTO bookings(venue_id,user_telegram_id,start_at,customer_phone,booked_price) VALUES (%s,%s,%s,%s,%s) RETURNING id', (booking.venue_id,user,start,contact['phone'],venue['price'])).fetchone()
        booking_event(conn, row['id'], user, 'created')
        owner=conn.execute('SELECT owner_telegram_id,name FROM venues WHERE id=%s',(booking.venue_id,)).fetchone()
        conn.execute('INSERT INTO notifications(recipient_id,body,booking_id) VALUES (%s,%s,%s)',(owner['owner_telegram_id'],f'📅 Yangi bron #{row["id"]} — {owner["name"]}\n🕒 {booking_time_label(start)}\n📞 Mijoz: {contact["phone"]} (Telegram orqali ulashilgan)\n/owner',row['id']))
    return {'id':row['id'],'status':'pending'}

@app.get('/bookings/me')
def my_bookings(response: Response, user: int = Depends(authenticate)):
    response.headers['Cache-Control'] = 'private, no-store'
    with db() as conn:
        return conn.execute('''SELECT b.id,b.venue_id,b.start_at,b.status,b.customer_phone,v.name AS venue_name
           FROM bookings b JOIN venues v ON v.id=b.venue_id
           WHERE b.user_telegram_id=%s ORDER BY b.start_at DESC LIMIT 100''',(user,)).fetchall()

@app.get('/owner/bookings')
def owner_bookings(response: Response, user: int = Depends(authenticate),
                   from_date: date | None = None, to_date: date | None = None,
                   venue_id: int | None = None, status: Literal['pending','confirmed','cancelled','rejected'] | None = None,
                   search: str = Query(default='', max_length=100), offset: int = Query(default=0, ge=0)):
    response.headers['Cache-Control'] = 'private, no-store'
    clauses, params = ['v.owner_telegram_id=%s'], [user]
    if from_date:
        clauses.append('b.start_at >= %s'); params.append(datetime.combine(from_date, day_time(), tzinfo=UZBEKISTAN_TIME))
    if to_date:
        if to_date == date.max or (from_date and from_date > to_date):
            raise HTTPException(422, 'Sanalarni tekshiring.')
        clauses.append('b.start_at < %s'); params.append(datetime.combine(to_date + timedelta(days=1), day_time(), tzinfo=UZBEKISTAN_TIME))
    if venue_id:
        clauses.append('v.id=%s'); params.append(venue_id)
    if status:
        clauses.append('b.status=%s'); params.append(status)
    if search:
        clauses.append("(b.customer_name ILIKE %s OR b.customer_phone ILIKE %s OR b.id::text=%s)")
        params.extend([f'%{search}%', f'%{search}%', search])
    with db() as conn:
        return conn.execute(f"SELECT b.*,v.name AS venue_name FROM bookings b JOIN venues v ON v.id=b.venue_id WHERE {' AND '.join(clauses)} ORDER BY b.start_at DESC,b.id DESC LIMIT 50 OFFSET %s", (*params, offset)).fetchall()


class ManualBooking(BookingIn):
    customer_name: str = Field(min_length=1, max_length=120)
    customer_phone: str = Field(pattern=r'^\+?[0-9 ()-]{7,40}$')

    @field_validator('customer_name')
    @classmethod
    def name_not_blank(cls, value):
        if not value.strip():
            raise ValueError('Customer name required')
        return value.strip()


class BlockIn(BookingIn):
    reason: str = Field(default='', max_length=300)


class HoursIn(BaseModel):
    hours: str = Field(min_length=1, max_length=120)

    @field_validator('hours')
    @classmethod
    def validate_hours(cls, value):
        hours_window(value)
        if not value.strip():
            raise ValueError('Hours required')
        return value.strip()


class PaymentIn(BaseModel):
    status: Literal['unpaid','deposit','paid']


def owned_venue(conn, venue_id, user):
    row = conn.execute('SELECT * FROM venues WHERE id=%s AND owner_telegram_id=%s AND deleted_at IS NULL FOR UPDATE', (venue_id, user)).fetchone()
    if not row:
        raise HTTPException(404, 'Maydon topilmadi.')
    return row


@app.post('/owner/manual-bookings', status_code=201)
def manual_booking(body: ManualBooking, user: int = Depends(authenticate)):
    start = valid_start(body.start_at)
    with db() as conn:
        venue = owned_venue(conn, body.venue_id, user)
        if venue['status'] != 'approved' or venue['suspended']:
            raise HTTPException(409, 'Maydon faol emas.')
        if not is_open(venue['hours'], start):
            raise HTTPException(422, 'Maydon bu vaqtda yopiq.')
        ensure_free(conn, body.venue_id, start)
        row = conn.execute("INSERT INTO bookings(venue_id,start_at,status,customer_name,customer_phone,booked_price,source) VALUES (%s,%s,'confirmed',%s,%s,%s,'manual') RETURNING *", (body.venue_id,start,body.customer_name,body.customer_phone,venue['price'])).fetchone()
        booking_event(conn, row['id'], user, 'created_manual')
        return row


@app.post('/owner/blocks', status_code=201)
def block_slot(body: BlockIn, user: int = Depends(authenticate)):
    start = valid_start(body.start_at)
    with db() as conn:
        owned_venue(conn, body.venue_id, user)
        ensure_free(conn, body.venue_id, start)
        return conn.execute('INSERT INTO owner_blocks(venue_id,start_at,reason) VALUES (%s,%s,%s) RETURNING *', (body.venue_id,start,body.reason)).fetchone()


@app.post('/owner/blocks/{block_id}/remove')
def remove_block(block_id: int, user: int = Depends(authenticate)):
    with db() as conn:
        row = conn.execute('SELECT venue_id FROM owner_blocks WHERE id=%s', (block_id,)).fetchone()
        if not row:
            raise HTTPException(404, 'Yopilgan vaqt topilmadi.')
        owned_venue(conn, row['venue_id'], user)
        conn.execute('DELETE FROM owner_blocks WHERE id=%s', (block_id,))
    return {'status': 'removed'}


@app.post('/owner/venues/{venue_id}/hours')
def set_hours(venue_id: int, body: HoursIn, user: int = Depends(authenticate)):
    with db() as conn:
        owned_venue(conn, venue_id, user)
        active = conn.execute("SELECT start_at FROM bookings WHERE venue_id=%s AND status IN ('pending','confirmed') AND start_at + INTERVAL '1 hour' > NOW()", (venue_id,)).fetchall()
        if any(not is_open(body.hours, row['start_at']) for row in active):
            raise HTTPException(409, 'Yangi ish vaqti mavjud bronlarga mos emas. Avval bronlarni tekshiring.')
        conn.execute('UPDATE venues SET hours=%s WHERE id=%s', (body.hours, venue_id))
    return {'hours': body.hours}


@app.post('/owner/payments/{booking_id}')
def set_payment(booking_id: int, body: PaymentIn, user: int = Depends(authenticate)):
    with db() as conn:
        row = conn.execute("UPDATE bookings SET payment_status=%s WHERE id=%s AND status='confirmed' AND venue_id IN (SELECT id FROM venues WHERE owner_telegram_id=%s) RETURNING id", (body.status,booking_id,user)).fetchone()
        if not row:
            raise HTTPException(404, 'Tasdiqlangan bron topilmadi.')
        conn.execute('INSERT INTO owner_payment_events(booking_id,owner_id,payment_status) VALUES (%s,%s,%s)', (booking_id,user,body.status))
    return {'payment_status': body.status}


@app.post('/owner/manual-bookings/{booking_id}/cancel')
def cancel_manual(booking_id: int, user: int = Depends(authenticate)):
    with db() as conn:
        row = conn.execute("UPDATE bookings SET status='cancelled' WHERE id=%s AND source='manual' AND status='confirmed' AND start_at > NOW() AND venue_id IN (SELECT id FROM venues WHERE owner_telegram_id=%s) RETURNING id", (booking_id,user)).fetchone()
        if not row:
            raise HTTPException(404, 'Kelgusi qoʻlda kiritilgan bron topilmadi.')
        booking_event(conn, booking_id, user, 'cancelled')
    return {'status': 'cancelled'}


@app.get('/owner/schedule')
def owner_schedule(response: Response, venue_id: int, day: date, days: int = Query(default=1, ge=1, le=7), user: int = Depends(authenticate)):
    response.headers['Cache-Control'] = 'private, no-store'
    if day > date.max - timedelta(days=7):
        raise HTTPException(422, 'Sanani tekshiring.')
    start = datetime.combine(day, day_time(), tzinfo=UZBEKISTAN_TIME)
    end = start + timedelta(days=days)
    with db() as conn:
        venue = conn.execute('SELECT hours,status,suspended FROM venues WHERE id=%s AND owner_telegram_id=%s AND deleted_at IS NULL', (venue_id,user)).fetchone()
        if not venue:
            raise HTTPException(404, 'Maydon topilmadi.')
        bookings = conn.execute("SELECT * FROM bookings WHERE venue_id=%s AND start_at >= %s AND start_at < %s AND status IN ('pending','confirmed')", (venue_id,start,end)).fetchall()
        blocks = conn.execute('SELECT * FROM owner_blocks WHERE venue_id=%s AND start_at >= %s AND start_at < %s', (venue_id,start,end)).fetchall()
    by_time = {b['start_at']: b for b in bookings}
    blocked = {b['start_at']: b for b in blocks}
    now = datetime.now(timezone.utc)
    slots = []
    for index in range(days * 24):
        instant = start + timedelta(hours=index)
        booking, block = by_time.get(instant), blocked.get(instant)
        state = 'booked' if booking else 'blocked' if block else 'past' if instant <= now + timedelta(minutes=5) else 'unavailable' if instant > now + timedelta(days=60) or venue['status'] != 'approved' or venue['suspended'] else 'available' if is_open(venue['hours'], instant) else 'closed'
        slots.append({'start_at':instant.isoformat(), 'status':state, 'booking':booking, 'block':block})
    return {'hours':venue['hours'], 'slots':slots}


@app.get('/owner/overview')
def owner_overview(response: Response, user: int = Depends(authenticate)):
    response.headers['Cache-Control'] = 'private, no-store'
    start = datetime.combine(datetime.now(UZBEKISTAN_TIME).date(), day_time(), tzinfo=UZBEKISTAN_TIME)
    with db() as conn:
        return conn.execute("""SELECT
          COUNT(*) FILTER (WHERE b.start_at >= %s AND b.start_at < %s AND b.status IN ('pending','confirmed')) AS today,
          COUNT(*) FILTER (WHERE b.status='pending' AND b.start_at > NOW()) AS pending,
          COALESCE(SUM(b.booked_price) FILTER (WHERE b.status='confirmed' AND b.start_at >= %s AND b.start_at < %s),0) AS value,
          COUNT(*) FILTER (WHERE b.status='confirmed' AND b.payment_status='unpaid') AS unpaid
          FROM bookings b JOIN venues v ON v.id=b.venue_id WHERE v.owner_telegram_id=%s""", (start,start+timedelta(days=1),start,start+timedelta(days=1),user)).fetchone()


@app.post('/owner/bookings/{booking_id}/{decision}')
def owner_decide(booking_id: int, decision: Literal['confirmed','rejected'], user: int = Depends(authenticate)):
    with db() as conn:
        row = conn.execute('''UPDATE bookings SET status=%s WHERE id=%s AND status='pending'
           AND venue_id IN (SELECT id FROM venues WHERE owner_telegram_id=%s) RETURNING id''',(decision,booking_id,user)).fetchone()
        if not row: raise HTTPException(404,'Pending booking not found for owner')
        booking_event(conn, booking_id, user, decision)
        client=conn.execute('SELECT user_telegram_id FROM bookings WHERE id=%s',(booking_id,)).fetchone()
        conn.execute('INSERT INTO notifications(recipient_id,body,booking_id) VALUES (%s,%s,%s)',(client['user_telegram_id'],f'📅 Bron #{booking_id}: {decision}.',booking_id))
    return {'status':decision}

@app.post('/bookings/{booking_id}/cancel')
def cancel(booking_id: int, user: int = Depends(authenticate)):
    with db() as conn:
        row = conn.execute("UPDATE bookings SET status='cancelled' WHERE id=%s AND user_telegram_id=%s AND status='pending' RETURNING id",(booking_id,user)).fetchone()
        if not row: raise HTTPException(404,'Pending booking not found')
        booking_event(conn, booking_id, user, 'cancelled')
    return {'status':'cancelled'}

@app.get('/owner/venues')
def owner_venues(user: int = Depends(authenticate)):
    with db() as conn:
        return conn.execute('SELECT id,name,sport,address,latitude,longitude,price,phone,hours,status,suspended,review_reason, ARRAY(SELECT p.id FROM venue_photos p WHERE p.venue_id=venues.id ORDER BY p.id) AS photos FROM venues WHERE owner_telegram_id=%s AND deleted_at IS NULL ORDER BY id DESC',(user,)).fetchall()

@app.get('/admin/status')
def admin_status(user: int = Depends(authenticate)):
    return {'admin': bool(ADMIN_ID and str(user)==ADMIN_ID)}

@app.get('/owner/status')
def owner_status(user: int = Depends(authenticate)):
    with db() as conn:
        return {'owner': bool(conn.execute('SELECT 1 FROM venues WHERE owner_telegram_id=%s LIMIT 1',(user,)).fetchone())}


ANALYTICS_METRICS = """
 COUNT(b.id) AS total,
 COUNT(b.id) FILTER (WHERE b.status='pending') AS pending,
 COUNT(b.id) FILTER (WHERE b.status='confirmed') AS confirmed,
 COUNT(b.id) FILTER (WHERE b.status='rejected') AS rejected,
 COUNT(b.id) FILTER (WHERE b.status='cancelled') AS cancelled,
 COUNT(DISTINCT b.user_telegram_id) AS customers,
 COALESCE(SUM(b.booked_price) FILTER (WHERE b.status='confirmed'),0) AS confirmed_value,
 COUNT(b.id) FILTER (WHERE b.status='confirmed' AND b.booked_price IS NULL) AS unpriced_confirmed
"""

def booking_analytics(response: Response, owner: int | None, from_date: date | None,
                      to_date: date | None, all_time: bool, venue_id: int | None):
    response.headers['Cache-Control'] = 'private, no-store'
    today = datetime.now(UZBEKISTAN_TIME).date()
    if all_time and (from_date or to_date):
        raise HTTPException(422, 'Barcha davr yoki sanalar oraligʻini tanlang.')
    if not all_time:
        to_date = to_date or today
        from_date = from_date or date.fromordinal(max(1, to_date.toordinal() - 29))
        if from_date > to_date or (to_date - from_date).days > 365:
            raise HTTPException(422, 'Sanalar oraligʻi 1–366 kun boʻlishi kerak.')
    if to_date == date.max:
        raise HTTPException(422, 'Boshqa tugash sanasini tanlang.')
    scope, scope_params = ('v.owner_telegram_id=%s', [owner]) if owner is not None else ('TRUE', [])
    with db() as conn:
        # Keep summary, per-venue totals and trend on one database snapshot.
        conn.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
        available = conn.execute(f'SELECT v.id,v.name,v.status,v.suspended,v.deleted_at FROM venues v WHERE {scope} ORDER BY v.name,v.id', scope_params).fetchall()
        if venue_id is not None and not any(v['id'] == venue_id for v in available):
            raise HTTPException(404, 'Maydon topilmadi.')
        if venue_id is not None:
            scope += ' AND v.id=%s'; scope_params.append(venue_id)
        dates, date_params = '', []
        if not all_time:
            dates = ' AND b.start_at >= %s AND b.start_at < %s'
            date_params = [datetime.combine(from_date, day_time(), tzinfo=UZBEKISTAN_TIME),
                           datetime.combine(to_date + timedelta(days=1), day_time(), tzinfo=UZBEKISTAN_TIME)]
        joined = f'FROM venues v LEFT JOIN bookings b ON b.venue_id=v.id{dates} WHERE {scope}'
        params = [*date_params, *scope_params]
        summary = conn.execute(f'SELECT {ANALYTICS_METRICS} {joined}', params).fetchone()
        per_venue = conn.execute(f'SELECT v.id,v.name,v.status,v.suspended,v.deleted_at,{ANALYTICS_METRICS} {joined} GROUP BY v.id ORDER BY total DESC,v.id', params).fetchall()
        bucket = 'month' if all_time or (to_date - from_date).days > 90 else 'day'
        trend = conn.execute(f"SELECT date_trunc('{bucket}', b.start_at AT TIME ZONE 'Asia/Tashkent')::date AS date,{ANALYTICS_METRICS} {joined} AND b.id IS NOT NULL GROUP BY 1 ORDER BY 1", params).fetchall()
    return {'from_date':from_date, 'to_date':to_date, 'all_time':all_time, 'bucket':bucket,
            'summary':summary, 'venues':per_venue, 'available_venues':available, 'trend':trend}

@app.get('/admin/analytics')
def admin_analytics(response: Response, from_date: date | None = None, to_date: date | None = None,
                    all_time: bool = False, venue_id: int | None = None, _: int = Depends(admin)):
    return booking_analytics(response, None, from_date, to_date, all_time, venue_id)

@app.get('/owner/analytics')
def owner_analytics(response: Response, from_date: date | None = None, to_date: date | None = None,
                    all_time: bool = False, venue_id: int | None = None, user: int = Depends(authenticate)):
    return booking_analytics(response, user, from_date, to_date, all_time, venue_id)

# Admin operations: all personal information is authenticated and never cached.
@app.get('/admin/attention')
def admin_attention(response: Response, _: int = Depends(admin)):
    response.headers['Cache-Control'] = 'private, no-store'
    with db() as conn:
        counts = conn.execute("""SELECT
            (SELECT count(*) FROM venues WHERE status='pending' AND deleted_at IS NULL) AS venues,
            (SELECT count(*) FROM bookings WHERE status='pending' AND start_at>NOW()) AS bookings,
            (SELECT count(*) FROM notifications n LEFT JOIN bookings b ON b.id=n.reminder_booking_id
             WHERE n.sent_at IS NULL AND (n.attempts>0 OR n.created_at<NOW()-INTERVAL '5 minutes')
             AND (n.reminder_booking_id IS NULL OR (b.status='confirmed' AND b.start_at>NOW()))) AS notifications""").fetchone()
        venues = conn.execute("SELECT id,name,owner_telegram_id,suspended FROM venues WHERE status='pending' AND deleted_at IS NULL ORDER BY id LIMIT 20").fetchall()
        bookings = conn.execute("""SELECT b.id,b.venue_id,v.name AS venue_name,b.start_at,b.created_at,v.owner_telegram_id
            FROM bookings b JOIN venues v ON v.id=b.venue_id WHERE b.status='pending' AND b.start_at>NOW()
            ORDER BY b.start_at,b.id LIMIT 20""").fetchall()
    return {'counts': counts, 'venues': venues, 'bookings': bookings}


@app.get('/admin/notifications')
def admin_notifications(response: Response, offset: int = Query(default=0, ge=0), _: int = Depends(admin)):
    response.headers['Cache-Control'] = 'private, no-store'
    with db() as conn:
        return conn.execute("""SELECT n.id,n.recipient_id,COALESCE(n.booking_id,n.reminder_booking_id) AS booking_id,
            n.created_at,n.retry_after,n.attempts,n.last_error
            FROM notifications n LEFT JOIN bookings b ON b.id=n.reminder_booking_id
            WHERE n.sent_at IS NULL AND (n.attempts>0 OR n.created_at<NOW()-INTERVAL '5 minutes')
              AND (n.reminder_booking_id IS NULL OR (b.status='confirmed' AND b.start_at>NOW()))
            ORDER BY n.created_at,n.id LIMIT 50 OFFSET %s""", (offset,)).fetchall()


PEOPLE_CTE = """WITH identities AS (
 SELECT telegram_id FROM telegram_contacts UNION SELECT telegram_id FROM telegram_profiles
 UNION SELECT owner_telegram_id FROM venues
 UNION SELECT user_telegram_id FROM bookings WHERE user_telegram_id IS NOT NULL
), people AS (
 SELECT 'telegram:'||i.telegram_id AS key,i.telegram_id,NULL::bigint AS booking_id,
 COALESCE(p.first_name,'') AS name,COALESCE(p.username,'') AS username,
 COALESCE(c.phone,(SELECT customer_phone FROM bookings WHERE user_telegram_id=i.telegram_id
     AND customer_phone IS NOT NULL ORDER BY id DESC LIMIT 1),
     (SELECT NULLIF(phone,'') FROM venues WHERE owner_telegram_id=i.telegram_id AND phone<>'' ORDER BY id DESC LIMIT 1),'') AS phone,
 (SELECT count(*) FROM venues WHERE owner_telegram_id=i.telegram_id) AS venue_count,
 (SELECT count(*) FROM bookings WHERE user_telegram_id=i.telegram_id) AS booking_count,
 (SELECT count(*) FROM bookings WHERE user_telegram_id=i.telegram_id AND status='cancelled') AS cancelled_count
 FROM identities i LEFT JOIN telegram_profiles p USING(telegram_id) LEFT JOIN telegram_contacts c USING(telegram_id)
 UNION ALL
 SELECT 'manual:'||b.id,NULL::bigint,b.id,b.customer_name,''::text,COALESCE(b.customer_phone,''),0::bigint,1::bigint,
 CASE WHEN b.status='cancelled' THEN 1::bigint ELSE 0::bigint END
 FROM bookings b WHERE b.user_telegram_id IS NULL
) """


@app.get('/admin/people')
def admin_people(response: Response, q: str = Query(default='', max_length=120),
                 role: Literal['all','owners','customers','manual'] = 'all',
                 offset: int = Query(default=0, ge=0), _: int = Depends(admin)):
    response.headers['Cache-Control'] = 'private, no-store'
    clauses, params = [], []
    if role == 'owners':
        clauses.append('venue_count>0')
    elif role == 'customers':
        clauses.append('booking_count>0')
    elif role == 'manual':
        clauses.append('telegram_id IS NULL')
    if q.strip():
        clauses.append("(name ILIKE %s OR username ILIKE %s OR phone ILIKE %s OR telegram_id::text=%s)")
        params.extend([f'%{q.strip()}%']*3+[q.strip()])
    with db() as conn:
        return conn.execute(PEOPLE_CTE + 'SELECT * FROM people WHERE '+(' AND '.join(clauses) or 'TRUE')+
                            ' ORDER BY venue_count DESC,key LIMIT 50 OFFSET %s', (*params,offset)).fetchall()


@app.get('/admin/activity')
def admin_activity(response: Response, entity: Literal['all','venue','booking'] = 'all',
                   entity_id: int | None = Query(default=None, ge=1),
                   actor_id: int | None = Query(default=None, ge=1),
                   action: Literal['all','approved','rejected','suspend','resume','cancelled'] = 'all',
                   day: date | None = None, offset: int = Query(default=0, ge=0), _: int = Depends(admin)):
    response.headers['Cache-Control'] = 'private, no-store'
    clauses, params = [], []
    for field,value in [('entity_type',entity if entity!='all' else None),('entity_id',entity_id),
                        ('admin_id',actor_id),('action',action if action!='all' else None)]:
        if value is not None:
            clauses.append(field+'=%s'); params.append(value)
    if day:
        if day == date.max:
            raise HTTPException(422, 'Sanani tekshiring.')
        start = datetime.combine(day,day_time(),tzinfo=UZBEKISTAN_TIME)
        clauses.append('created_at >= %s AND created_at < %s'); params.extend([start,start+timedelta(days=1)])
    with db() as conn:
        return conn.execute('SELECT * FROM admin_actions WHERE '+(' AND '.join(clauses) or 'TRUE')+
                            ' ORDER BY created_at DESC,id DESC LIMIT 50 OFFSET %s', (*params,offset)).fetchall()


@app.get('/admin/bookings/{booking_id}')
def admin_booking_detail(booking_id: int, response: Response, offset: int = Query(default=0, ge=0), _: int = Depends(admin)):
    response.headers['Cache-Control'] = 'private, no-store'
    with db() as conn:
        booking = conn.execute('SELECT b.*,v.name AS venue_name,v.owner_telegram_id FROM bookings b JOIN venues v ON v.id=b.venue_id WHERE b.id=%s', (booking_id,)).fetchone()
        if not booking:
            raise HTTPException(404, 'Bron topilmadi.')
        complete = conn.execute("SELECT 1 FROM booking_events WHERE booking_id=%s AND action IN ('created','created_manual')", (booking_id,)).fetchone() is not None
        timeline = conn.execute("""SELECT * FROM (
            SELECT e.id,e.created_at,e.actor_id,e.action,'booking' AS kind,
                (SELECT reason FROM admin_actions a WHERE a.entity_type='booking' AND a.entity_id=e.booking_id
                 AND a.admin_id=e.actor_id AND a.action=e.action AND a.created_at=e.created_at LIMIT 1) AS reason
            FROM booking_events e WHERE e.booking_id=%s
            UNION ALL SELECT id,created_at,owner_id,payment_status,'payment',NULL FROM owner_payment_events WHERE booking_id=%s
            UNION ALL SELECT a.id,a.created_at,a.admin_id,a.action,'admin',a.reason FROM admin_actions a
              WHERE a.entity_type='booking' AND a.entity_id=%s AND NOT EXISTS (
                SELECT 1 FROM booking_events e WHERE e.booking_id=a.entity_id AND e.actor_id=a.admin_id
                  AND e.action=a.action AND e.created_at=a.created_at)
            ) events ORDER BY created_at,id,kind LIMIT 50 OFFSET %s""", (booking_id,booking_id,booking_id,offset)).fetchall()
        notifications = conn.execute("""SELECT id,recipient_id,created_at,sent_at,retry_after,attempts,last_error,
            CASE WHEN sent_at IS NOT NULL THEN 'sent'
                 WHEN reminder_booking_id IS NOT NULL AND NOT EXISTS (
                    SELECT 1 FROM bookings WHERE id=reminder_booking_id AND status='confirmed' AND start_at>NOW()) THEN 'expired'
                 WHEN attempts>0 THEN 'retrying' ELSE 'queued' END AS delivery_status
            FROM notifications WHERE booking_id=%s OR reminder_booking_id=%s ORDER BY id DESC LIMIT 50""", (booking_id,booking_id)).fetchall()
    return {'booking':booking,'history_complete':complete,'timeline':timeline,'notifications':notifications}
