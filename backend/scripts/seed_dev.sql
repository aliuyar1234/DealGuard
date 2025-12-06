-- Seed script for development environment
-- Creates the dev organization and user required for AUTH_PROVIDER=dev

-- Insert dev organization (if not exists)
INSERT INTO organizations (id, name, slug, plan_tier, settings, created_at, updated_at)
VALUES (
    '00000000-0000-0000-0000-000000000001'::uuid,
    'Dev Organization',
    'dev-org',
    'enterprise',
    '{"is_dev": true}'::jsonb,
    NOW(),
    NOW()
)
ON CONFLICT (id) DO NOTHING;

-- Insert dev user (if not exists)
INSERT INTO users (id, organization_id, supabase_user_id, email, full_name, role, settings, created_at, updated_at)
VALUES (
    '00000000-0000-0000-0000-000000000001'::uuid,
    '00000000-0000-0000-0000-000000000001'::uuid,
    '00000000-0000-0000-0000-000000000001',
    'dev@dealguard.local',
    'Dev User',
    'owner',
    '{}'::jsonb,
    NOW(),
    NOW()
)
ON CONFLICT (id) DO NOTHING;
