"""MAYDON API. Requires PostgreSQL and validated Telegram WebApp initData."""
import hashlib
import hmac
import json
import os
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
def auth_me(init_data: str = Header(default='', alias='X-Telegram-Init-Data')):
    user = telegram_identity(init_data)
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
CREATE TABLE IF NOT EXISTS telegram_contacts (
 telegram_id BIGINT PRIMARY KEY, phone TEXT NOT NULL, shared_at TIMESTAMPTZ NOT NULL DEFAULT NOW());
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
    with db() as conn:
        conn.execute('SELECT 1')
    return {'status':'ok'}

@app.get('/venues')
def venues(sport: str | None = None):
    with db() as conn:
        if sport:
            return conn.execute('SELECT id,name,sport,address,latitude,longitude,price,phone,hours, ARRAY(SELECT p.id FROM venue_photos p WHERE p.venue_id=venues.id ORDER BY p.id) AS photos FROM venues WHERE deleted_at IS NULL AND NOT suspended AND status=%s AND sport=%s ORDER BY id DESC', ('approved',sport)).fetchall()
        return conn.execute('SELECT id,name,sport,address,latitude,longitude,price,phone,hours, ARRAY(SELECT p.id FROM venue_photos p WHERE p.venue_id=venues.id ORDER BY p.id) AS photos FROM venues WHERE deleted_at IS NULL AND NOT suspended AND status=%s ORDER BY id DESC', ('approved',)).fetchall()

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
    reserved = {row['start_at'] for row in busy}
    slots = []
    for hour in range(24):
        instant = start + timedelta(hours=hour)
        status = 'past' if instant <= now + timedelta(minutes=5) else 'unavailable' if instant > now + timedelta(days=60) else 'booked' if instant in reserved else 'available'
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
                   offset: int = Query(default=0, ge=0), _: int = Depends(admin)):
    response.headers['Cache-Control'] = 'private, no-store'
    clauses, params = [], []
    for field, value in [('b.status', status if status != 'all' else None), ('b.venue_id', venue_id), ('b.id', booking_id)]:
        if value is not None:
            clauses.append(f'{field}=%s'); params.append(value)
    if day:
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
        message = f'📅 Bron #{booking_id} — {venue["name"]} admin tomonidan bekor qilindi.\n{booking_time_label(row["start_at"])}\nSabab: {body.reason}'
        for recipient in {row['user_telegram_id'], venue['owner_telegram_id']}:
            conn.execute('INSERT INTO notifications(recipient_id,body) VALUES (%s,%s)', (recipient, message))
    return {'status': 'cancelled'}

@app.post('/bookings', status_code=201)
def book(booking: BookingIn, user: int = Depends(authenticate)):
    start = booking.start_at
    if start.tzinfo is None:
        raise HTTPException(422,'Timezone required')
    start = start.astimezone(timezone.utc)
    if start <= datetime.now(timezone.utc) + timedelta(minutes=5) or start > datetime.now(timezone.utc) + timedelta(days=60):
        raise HTTPException(422,'Choose a time between 5 minutes and 60 days ahead')
    if start.minute != 0 or start.second != 0 or start.microsecond != 0:
        raise HTTPException(422,'Bookings start on the hour')
    with db() as conn:
        # Serialize requests per venue, preventing concurrent overlapping slots.
        contact = conn.execute('SELECT phone FROM telegram_contacts WHERE telegram_id=%s', (user,)).fetchone()
        if not contact:
            raise HTTPException(428, 'Bron qilishdan oldin Telegram orqali oʻz telefon raqamingizni ulashing.')
        venue = conn.execute('SELECT id FROM venues WHERE deleted_at IS NULL AND NOT suspended AND id=%s AND status=%s FOR UPDATE', (booking.venue_id,'approved')).fetchone()
        if not venue: raise HTTPException(404,'Venue not found')
        conflict = conn.execute('''SELECT id FROM bookings WHERE venue_id=%s AND start_at=%s
          AND status IN ('pending','confirmed') LIMIT 1''', (booking.venue_id,start)).fetchone()
        if conflict: raise HTTPException(409,'This time slot is already reserved')
        row = conn.execute('INSERT INTO bookings(venue_id,user_telegram_id,start_at,customer_phone) VALUES (%s,%s,%s,%s) RETURNING id', (booking.venue_id,user,start,contact['phone'])).fetchone()
        owner=conn.execute('SELECT owner_telegram_id,name FROM venues WHERE id=%s',(booking.venue_id,)).fetchone()
        conn.execute('INSERT INTO notifications(recipient_id,body) VALUES (%s,%s)',(owner['owner_telegram_id'],f'📅 Yangi bron #{row["id"]} — {owner["name"]}\n🕒 {booking_time_label(start)}\n📞 Mijoz: {contact["phone"]} (Telegram orqali ulashilgan)\n/owner'))
    return {'id':row['id'],'status':'pending'}

@app.get('/bookings/me')
def my_bookings(response: Response, user: int = Depends(authenticate)):
    response.headers['Cache-Control'] = 'private, no-store'
    with db() as conn:
        return conn.execute('''SELECT b.id,b.venue_id,b.start_at,b.status,b.customer_phone,v.name AS venue_name
           FROM bookings b JOIN venues v ON v.id=b.venue_id
           WHERE b.user_telegram_id=%s ORDER BY b.start_at DESC LIMIT 100''',(user,)).fetchall()

@app.get('/owner/bookings')
def owner_bookings(response: Response, user: int = Depends(authenticate)):
    response.headers['Cache-Control'] = 'private, no-store'
    with db() as conn:
        return conn.execute('''SELECT b.id,b.venue_id,b.start_at,b.status,b.user_telegram_id,b.customer_phone,v.name AS venue_name
          FROM bookings b JOIN venues v ON v.id=b.venue_id
          WHERE v.owner_telegram_id=%s ORDER BY b.start_at DESC LIMIT 100''',(user,)).fetchall()

@app.post('/owner/bookings/{booking_id}/{decision}')
def owner_decide(booking_id: int, decision: Literal['confirmed','rejected'], user: int = Depends(authenticate)):
    with db() as conn:
        row = conn.execute('''UPDATE bookings SET status=%s WHERE id=%s AND status='pending'
           AND venue_id IN (SELECT id FROM venues WHERE owner_telegram_id=%s) RETURNING id''',(decision,booking_id,user)).fetchone()
        if not row: raise HTTPException(404,'Pending booking not found for owner')
        client=conn.execute('SELECT user_telegram_id FROM bookings WHERE id=%s',(booking_id,)).fetchone()
        conn.execute('INSERT INTO notifications(recipient_id,body) VALUES (%s,%s)',(client['user_telegram_id'],f'📅 Bron #{booking_id}: {decision}.'))
    return {'status':decision}

@app.post('/bookings/{booking_id}/cancel')
def cancel(booking_id: int, user: int = Depends(authenticate)):
    with db() as conn:
        row = conn.execute("UPDATE bookings SET status='cancelled' WHERE id=%s AND user_telegram_id=%s AND status='pending' RETURNING id",(booking_id,user)).fetchone()
        if not row: raise HTTPException(404,'Pending booking not found')
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
