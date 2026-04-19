-- Preserve the raw API-Football short status ('1H' | 'HT' | '2H' | 'FT' | 'AET' | 'PEN')
-- so the FE can distinguish Half Time from in-play and Full Time from scheduled.
-- Also backfill any matches that got stuck at minute=90 in 'live' state because
-- the polling window closed before their FT transition.

ALTER TABLE matches
    ADD COLUMN IF NOT EXISTS live_period TEXT;

-- Sweep stuck rows: any match kicked off >150min ago still labelled 'live' is
-- almost certainly over. Move to 'final' so the UI stops showing the pulse.
UPDATE matches
SET status = 'final',
    live_period = 'FT'
WHERE status = 'live'
  AND kickoff_time < NOW() - INTERVAL '150 minutes';
