-- Migration 002: Add Trash System, Retention Purge Index, and Audit Log Table

ALTER TABLE contenidos ADD COLUMN deleted_at TEXT NULL;
ALTER TABLE contenidos ADD COLUMN purge_at TEXT NULL;
ALTER TABLE contenidos ADD COLUMN deleted_by TEXT NULL;
ALTER TABLE contenidos ADD COLUMN purge_failed INTEGER DEFAULT 0;

CREATE INDEX IF NOT EXISTS idx_contenidos_purge_at ON contenidos (purge_at);
CREATE INDEX IF NOT EXISTS idx_contenidos_user_deleted ON contenidos (user_id, deleted_at);

CREATE TABLE IF NOT EXISTS audit_log (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    action TEXT NOT NULL,
    resource_id TEXT,
    details TEXT,
    timestamp REAL NOT NULL
);
