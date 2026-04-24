-- Phase 42.1: long-form post-match narrative (300-500 words) in addition to
-- the 2-3 sentence `recap`. Used on /match/:id for SEO + shareable content.
ALTER TABLE matches
    ADD COLUMN IF NOT EXISTS story TEXT,
    ADD COLUMN IF NOT EXISTS story_model TEXT,
    ADD COLUMN IF NOT EXISTS story_generated_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_matches_story_status
    ON matches (status, kickoff_time DESC)
    WHERE story IS NOT NULL;
