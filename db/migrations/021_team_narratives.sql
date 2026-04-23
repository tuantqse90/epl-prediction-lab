-- LLM-generated long-form text per team, refreshed weekly.
-- Keyed on (team_slug, season) so we can evolve the story across seasons.
CREATE TABLE IF NOT EXISTS team_narratives (
    team_slug   TEXT NOT NULL,
    season      TEXT NOT NULL,
    lang        TEXT NOT NULL DEFAULT 'en',
    story       TEXT NOT NULL,
    model       TEXT,
    generated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (team_slug, season, lang)
);
