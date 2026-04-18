-- Phase 4.1 — on-chain commitment columns on predictions.
-- Idempotent; safe to re-run.

ALTER TABLE predictions
    ADD COLUMN IF NOT EXISTS commitment_hash  TEXT,
    ADD COLUMN IF NOT EXISTS commitment_tx    TEXT,
    ADD COLUMN IF NOT EXISTS commitment_chain TEXT;

CREATE INDEX IF NOT EXISTS idx_predictions_commitment_hash
    ON predictions (commitment_hash);

CREATE INDEX IF NOT EXISTS idx_predictions_needs_publish
    ON predictions (commitment_tx)
    WHERE commitment_hash IS NOT NULL AND commitment_tx IS NULL;
