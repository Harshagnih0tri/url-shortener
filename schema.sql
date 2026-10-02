CREATE TABLE urls (
    id INTEGER PRIMARY KEY,
    code VARCHAR(8) NOT NULL UNIQUE,
    original_url TEXT NOT NULL,
    created_at DATETIME NOT NULL,
    expires_at DATETIME
);

CREATE TABLE clicks (
    id INTEGER PRIMARY KEY,
    url_id INTEGER NOT NULL REFERENCES urls(id),
    clicked_at DATETIME NOT NULL,
    user_agent TEXT,
    referrer TEXT
);