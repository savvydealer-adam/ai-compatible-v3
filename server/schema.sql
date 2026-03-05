CREATE TABLE IF NOT EXISTS analyses (
    id TEXT PRIMARY KEY,
    url TEXT NOT NULL,
    score INTEGER,
    grade TEXT,
    status TEXT NOT NULL DEFAULT 'running',
    data_json JSONB,
    error TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS leads (
    id SERIAL PRIMARY KEY,
    analysis_id TEXT REFERENCES analyses(id) ON DELETE SET NULL,
    name TEXT NOT NULL,
    email TEXT NOT NULL,
    dealership TEXT NOT NULL DEFAULT '',
    phone TEXT NOT NULL DEFAULT '',
    method TEXT NOT NULL DEFAULT 'email',
    verified BOOLEAN NOT NULL DEFAULT false,
    created_account BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS accounts (
    email TEXT PRIMARY KEY,
    name TEXT NOT NULL DEFAULT '',
    dealership TEXT NOT NULL DEFAULT '',
    phone TEXT NOT NULL DEFAULT '',
    provider TEXT NOT NULL DEFAULT 'email',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
