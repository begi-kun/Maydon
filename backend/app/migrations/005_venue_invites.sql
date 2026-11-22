CREATE TABLE venue_invites (
    token UUID PRIMARY KEY,
    expires_at TIMESTAMPTZ NOT NULL DEFAULT (NOW() + INTERVAL '7 days')
);
