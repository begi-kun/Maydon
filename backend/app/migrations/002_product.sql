CREATE TABLE IF NOT EXISTS product_rate_limits (
 key TEXT NOT NULL, bucket BIGINT NOT NULL, count INTEGER NOT NULL, PRIMARY KEY(key,bucket));
CREATE INDEX IF NOT EXISTS product_rate_limits_bucket ON product_rate_limits(bucket);
CREATE TABLE IF NOT EXISTS discovery_events (
 id UUID PRIMARY KEY, search_id UUID NOT NULL, session_id UUID NOT NULL,
 event TEXT NOT NULL CHECK(event IN ('discovery_results','venue_open','booking_request_created')),
 day DATE, hour INTEGER CHECK(hour BETWEEN 0 AND 23),
 sport TEXT NOT NULL CHECK(sport IN ('all','football','table_tennis','billiards')),
 result_count INTEGER CHECK(result_count BETWEEN 0 AND 100000),
 venue_id BIGINT REFERENCES venues(id), booking_id BIGINT UNIQUE REFERENCES bookings(id),
 created_at TIMESTAMPTZ NOT NULL DEFAULT NOW());
CREATE UNIQUE INDEX IF NOT EXISTS discovery_search_result ON discovery_events(search_id) WHERE event='discovery_results';
CREATE INDEX IF NOT EXISTS discovery_events_created ON discovery_events(created_at);
CREATE TABLE IF NOT EXISTS recurring_requests (
 owner_id BIGINT NOT NULL, request_id UUID NOT NULL, payload JSONB NOT NULL,
 booking_ids BIGINT[] NOT NULL, PRIMARY KEY(owner_id,request_id));
CREATE TABLE IF NOT EXISTS availability_subscriptions (
 id BIGSERIAL PRIMARY KEY, user_id BIGINT NOT NULL, venue_id BIGINT NOT NULL REFERENCES venues(id),
 start_at TIMESTAMPTZ NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
 cancelled_at TIMESTAMPTZ, queued_at TIMESTAMPTZ);
CREATE UNIQUE INDEX IF NOT EXISTS availability_one_active ON availability_subscriptions(user_id,venue_id,start_at) WHERE cancelled_at IS NULL;
ALTER TABLE availability_subscriptions ADD COLUMN IF NOT EXISTS next_check_at TIMESTAMPTZ NOT NULL DEFAULT NOW();
CREATE INDEX IF NOT EXISTS availability_waiting ON availability_subscriptions(start_at) WHERE cancelled_at IS NULL AND queued_at IS NULL;
ALTER TABLE notifications ADD COLUMN IF NOT EXISTS availability_subscription_id BIGINT REFERENCES availability_subscriptions(id);
CREATE UNIQUE INDEX IF NOT EXISTS notifications_one_availability ON notifications(availability_subscription_id);
CREATE TABLE IF NOT EXISTS booking_outcomes (
 booking_id BIGINT PRIMARY KEY REFERENCES bookings(id), outcome TEXT NOT NULL
 CHECK(outcome IN ('attended','no_show','schedule_error','unknown')),
 actor_id BIGINT NOT NULL, updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW());
