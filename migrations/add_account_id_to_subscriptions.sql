-- Add account_id column to subscriptions table for automatic deduction
-- Run this in your Supabase SQL editor

ALTER TABLE subscriptions 
ADD COLUMN IF NOT EXISTS account_id UUID REFERENCES accounts(id) ON DELETE SET NULL;

-- Create index for faster lookups
CREATE INDEX IF NOT EXISTS idx_subscriptions_account_id ON subscriptions(account_id);

-- Comment for documentation
COMMENT ON COLUMN subscriptions.account_id IS 'Account to deduct from when subscription is processed automatically';
