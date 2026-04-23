-- Weekly auto-generated blog posts. Keyed on slug (week-N-YYYY) so the
-- Mon cron can insert idempotently, and the frontend reads whichever
-- posts the generator has produced.
CREATE TABLE IF NOT EXISTS auto_blog_posts (
    slug         TEXT PRIMARY KEY,
    title        TEXT NOT NULL,
    excerpt      TEXT NOT NULL,
    body_md      TEXT NOT NULL,
    tags         TEXT[] NOT NULL DEFAULT '{}',
    lang         TEXT NOT NULL DEFAULT 'en',
    generated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    model        TEXT
);
CREATE INDEX IF NOT EXISTS idx_auto_blog_date ON auto_blog_posts (generated_at DESC);
