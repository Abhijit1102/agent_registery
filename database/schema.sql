-- ============================================================
-- Agent Registry & Usage Tracking Platform
-- Raw SQL Schema (SQLite)
-- ============================================================

-- Agents table
CREATE TABLE IF NOT EXISTS agents (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL UNIQUE,
    description TEXT NOT NULL,
    endpoint    TEXT NOT NULL,
    tags        TEXT NOT NULL DEFAULT '[]'   -- JSON array stored as text
);

-- Usage logs table
-- request_id has a UNIQUE constraint to enforce idempotency at DB level
CREATE TABLE IF NOT EXISTS usage_logs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    caller      TEXT NOT NULL,
    target      TEXT NOT NULL,
    units       INTEGER NOT NULL,
    request_id  TEXT NOT NULL UNIQUE
);

-- Usage summary table
-- Stores pre-aggregated totals per target to avoid full recompute
CREATE TABLE IF NOT EXISTS usage_summary (
    target      TEXT PRIMARY KEY,
    total_units INTEGER NOT NULL DEFAULT 0
);

-- ============================================================
-- Indexes
-- ============================================================

CREATE INDEX IF NOT EXISTS idx_agents_name        ON agents (name);
CREATE INDEX IF NOT EXISTS idx_usage_logs_request ON usage_logs (request_id);
CREATE INDEX IF NOT EXISTS idx_usage_logs_target  ON usage_logs (target);

-- ============================================================
-- UPSERT pattern (used from application layer via SQLAlchemy):
--
-- When inserting a new usage_log, we simultaneously UPSERT
-- into usage_summary to keep totals up to date:
--
--   INSERT INTO usage_summary (target, total_units)
--   VALUES (:target, :units)
--   ON CONFLICT(target) DO UPDATE SET
--       total_units = usage_summary.total_units + excluded.total_units;
--
-- This avoids re-scanning usage_logs for every summary request.
-- ============================================================
