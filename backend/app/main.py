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
from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, ValidationError
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
CREATE INDEX IF NOT EXISTS bookings_venue_start ON bookings(venue_id,start_at);
CREATE INDEX IF NOT EXISTS bookings_user ON bookings(user_telegram_id);
CREATE TABLE IF NOT EXISTS venue_photos (
 id BIGSERIAL PRIMARY KEY, venue_id BIGINT NOT NULL REFERENCES venues(id) ON DELETE CASCADE,
 image BYTEA NOT NULL);
CREATE INDEX IF NOT EXISTS venue_photos_venue ON venue_photos(venue_id);
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
            return conn.execute('SELECT id,name,sport,address,latitude,longitude,price,phone,hours, ARRAY(SELECT p.id FROM venue_photos p WHERE p.venue_id=venues.id ORDER BY p.id) AS photos FROM venues WHERE status=%s AND sport=%s ORDER BY id DESC', ('approved',sport)).fetchall()
        return conn.execute('SELECT id,name,sport,address,latitude,longitude,price,phone,hours, ARRAY(SELECT p.id FROM venue_photos p WHERE p.venue_id=venues.id ORDER BY p.id) AS photos FROM venues WHERE status=%s ORDER BY id DESC', ('approved',)).fetchall()

@app.get('/venues/{venue_id}/availability')
def availability(venue_id: int, day: date):
    local_zone = UZBEKISTAN_TIME
    now = datetime.now(timezone.utc)
    start = datetime.combine(day, day_time(), tzinfo=local_zone)
    if day < now.astimezone(local_zone).date() or day > (now + timedelta(days=60)).astimezone(local_zone).date():
        raise HTTPException(422, 'Choose a date within the next 60 days')
    with db() as conn:
        venue = conn.execute('SELECT hours FROM venues WHERE id=%s AND status=%s', (venue_id, 'approved')).fetchone()
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
    body = bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body) > 7500000:
            raise HTTPException(413, 'Photo submission is too large')
    try:
        venue = VenueIn.model_validate_json(body)
    except ValidationError:
        raise HTTPException(422, 'Check venue details and include 1–5 pitch photos')
    return await run_in_threadpool(save_venue, venue, user)

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
        row = conn.execute('SELECT p.image,v.status,v.owner_telegram_id FROM venue_photos p JOIN venues v ON v.id=p.venue_id WHERE p.id=%s', (photo_id,)).fetchone()
    if not row:
        raise HTTPException(404, 'Photo not found')
    if row['status'] != 'approved':
        user = telegram_identity(init_data)['id']
        if user != row['owner_telegram_id'] and str(user) != ADMIN_ID:
            raise HTTPException(404, 'Photo not found')
    return Response(bytes(row['image']), media_type='image/jpeg', headers={'Cache-Control': 'private, no-store', 'X-Content-Type-Options': 'nosniff'})

@app.get('/admin/venues')
def pending_venues(_: int = Depends(admin)):
    with db() as conn:
        return conn.execute("SELECT *, ARRAY(SELECT p.id FROM venue_photos p WHERE p.venue_id=venues.id ORDER BY p.id) AS photos FROM venues WHERE status='pending' ORDER BY id").fetchall()

@app.post('/admin/venues/{venue_id}/{decision}')
def decide_venue(venue_id: int, decision: Literal['approved','rejected'], _: int = Depends(admin)):
    with db() as conn:
        row = conn.execute('UPDATE venues SET status=%s WHERE id=%s AND status=%s RETURNING id', (decision,venue_id,'pending')).fetchone()
        if not row: raise HTTPException(404,'Pending venue not found')
        info=conn.execute('SELECT owner_telegram_id,name FROM venues WHERE id=%s',(venue_id,)).fetchone()
        conn.execute('INSERT INTO notifications(recipient_id,body) VALUES (%s,%s)',(info['owner_telegram_id'],f'🏟 {info["name"]}: ariza {decision}.'))
    return {'status':decision}

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
        venue = conn.execute('SELECT id FROM venues WHERE id=%s AND status=%s FOR UPDATE', (booking.venue_id,'approved')).fetchone()
        if not venue: raise HTTPException(404,'Venue not found')
        conflict = conn.execute('''SELECT id FROM bookings WHERE venue_id=%s AND start_at=%s
          AND status IN ('pending','confirmed') LIMIT 1''', (booking.venue_id,start)).fetchone()
        if conflict: raise HTTPException(409,'This time slot is already reserved')
        row = conn.execute('INSERT INTO bookings(venue_id,user_telegram_id,start_at) VALUES (%s,%s,%s) RETURNING id', (booking.venue_id,user,start)).fetchone()
        owner=conn.execute('SELECT owner_telegram_id,name FROM venues WHERE id=%s',(booking.venue_id,)).fetchone()
        conn.execute('INSERT INTO notifications(recipient_id,body) VALUES (%s,%s)',(owner['owner_telegram_id'],f'📅 Yangi bron #{row["id"]} — {owner["name"]}\n🕒 {booking_time_label(start)}\n/owner'))
    return {'id':row['id'],'status':'pending'}

@app.get('/bookings/me')
def my_bookings(user: int = Depends(authenticate)):
    with db() as conn:
        return conn.execute('''SELECT b.id,b.venue_id,b.start_at,b.status,v.name AS venue_name
           FROM bookings b JOIN venues v ON v.id=b.venue_id
           WHERE b.user_telegram_id=%s ORDER BY b.start_at DESC LIMIT 100''',(user,)).fetchall()

@app.get('/owner/bookings')
def owner_bookings(user: int = Depends(authenticate)):
    with db() as conn:
        return conn.execute('''SELECT b.id,b.venue_id,b.start_at,b.status,b.user_telegram_id,v.name AS venue_name
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
        return conn.execute('SELECT id,name,sport,address,price,status, ARRAY(SELECT p.id FROM venue_photos p WHERE p.venue_id=venues.id ORDER BY p.id) AS photos FROM venues WHERE owner_telegram_id=%s ORDER BY id DESC',(user,)).fetchall()

@app.get('/admin/status')
def admin_status(user: int = Depends(authenticate)):
    return {'admin': bool(ADMIN_ID and str(user)==ADMIN_ID)}

@app.get('/owner/status')
def owner_status(user: int = Depends(authenticate)):
    with db() as conn:
        return {'owner': bool(conn.execute('SELECT 1 FROM venues WHERE owner_telegram_id=%s LIMIT 1',(user,)).fetchone())}
