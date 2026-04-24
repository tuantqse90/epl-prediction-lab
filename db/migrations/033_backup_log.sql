-- Backup observability — one row per successful daily dump + R2 upload.
-- ops_watchdog reads this to alert when the latest row is stale.
CREATE TABLE IF NOT EXISTS backup_log (
    id          BIGSERIAL PRIMARY KEY,
    run_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    dump_path   TEXT NOT NULL,
    size_bytes  BIGINT NOT NULL,
    r2_uploaded BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_backup_log_run_at_desc
    ON backup_log (run_at DESC);
