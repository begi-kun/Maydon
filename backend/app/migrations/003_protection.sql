CREATE TABLE IF NOT EXISTS request_limits (
 scope TEXT NOT NULL, subject TEXT NOT NULL, hits INTEGER NOT NULL,
 expires_at TIMESTAMPTZ NOT NULL, PRIMARY KEY(scope,subject));
CREATE INDEX IF NOT EXISTS request_limits_expiry ON request_limits(expires_at);
