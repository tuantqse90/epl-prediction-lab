-- Flag cup vs league fixtures. Ingest currently only pulls league
-- matches from Understat so every row is 'league' today; adding cup
-- data (Copa del Rey, FA Cup, DFB-Pokal etc.) requires a separate
-- ingest. Schema lands now so the predictor can branch on it.
ALTER TABLE matches
    ADD COLUMN IF NOT EXISTS competition_type TEXT NOT NULL DEFAULT 'league';

CREATE INDEX IF NOT EXISTS idx_matches_comp_type ON matches (competition_type);
