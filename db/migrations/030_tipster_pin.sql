-- Extend tipsters with pin_hash + display_name so the community layer
-- can let users self-signup without full auth.
ALTER TABLE tipsters
    ADD COLUMN IF NOT EXISTS pin_hash TEXT,
    ADD COLUMN IF NOT EXISTS display_name TEXT;

-- Tipster picks already has scoring columns (hit, log_loss) from the
-- earlier schema. This migration is schema-only; no backfill.
