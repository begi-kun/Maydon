CREATE TABLE admin_messages (
    admin_id BIGINT NOT NULL,
    request_id UUID NOT NULL,
    audience TEXT NOT NULL,
    body TEXT NOT NULL,
    queued INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (admin_id, request_id)
);
