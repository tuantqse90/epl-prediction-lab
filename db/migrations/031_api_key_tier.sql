-- Phase 41: api-key tier + Stripe linkage.
-- tier: free | pro-free (grandfathered) | pro (paying).
-- stripe_* columns nullable — billing inactive unless STRIPE_API_KEY is set.
ALTER TABLE api_keys
    ADD COLUMN IF NOT EXISTS tier TEXT NOT NULL DEFAULT 'free',
    ADD COLUMN IF NOT EXISTS email TEXT,
    ADD COLUMN IF NOT EXISTS stripe_customer_id TEXT,
    ADD COLUMN IF NOT EXISTS stripe_subscription_id TEXT,
    ADD COLUMN IF NOT EXISTS subscription_status TEXT,
    ADD COLUMN IF NOT EXISTS current_period_end TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS grandfather_until TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_api_keys_tier ON api_keys (tier);
CREATE INDEX IF NOT EXISTS idx_api_keys_stripe_sub ON api_keys (stripe_subscription_id)
  WHERE stripe_subscription_id IS NOT NULL;

-- Grandfather every existing active key as pro-free until 2027-01-01.
-- grandfather_until documents the expiry; current_period_end stays null for
-- free/pro-free keys and is only populated by Stripe webhooks for paying pros.
UPDATE api_keys
SET tier = 'pro-free',
    grandfather_until = '2027-01-01T00:00:00Z'
WHERE tier = 'free' AND revoked_at IS NULL;
