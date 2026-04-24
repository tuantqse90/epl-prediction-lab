-- Dixon-Coles ρ calibrated per (league, season, quarter). When a
-- lookup hits empty, the predictor falls back to the static default.
CREATE TABLE IF NOT EXISTS rho_calibration (
    league_code TEXT NOT NULL,
    season      TEXT NOT NULL,
    quarter     INTEGER NOT NULL CHECK (quarter BETWEEN 1 AND 4),
    rho         DOUBLE PRECISION NOT NULL,
    log_loss    DOUBLE PRECISION,
    n_matches   INTEGER,
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (league_code, season, quarter)
);
