-- Kickoff-time weather forecast per match (from open-meteo, no API key).
-- One row per match_id; re-fetching updates in place.

CREATE TABLE IF NOT EXISTS match_weather (
    match_id     INT PRIMARY KEY REFERENCES matches(id) ON DELETE CASCADE,
    temp_c       FLOAT,        -- at kickoff hour
    wind_kmh     FLOAT,         -- wind speed, km/h
    precip_mm    FLOAT,         -- expected rainfall mm
    condition    TEXT,          -- short code: clear/rain/snow/cloudy/etc.
    fetched_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
