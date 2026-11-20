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
ALTER TABLE venues ADD COLUMN IF NOT EXISTS amenities TEXT[] NOT NULL DEFAULT '{}';
ALTER TABLE venues ADD COLUMN IF NOT EXISTS extra_amenities TEXT NOT NULL DEFAULT '';
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
