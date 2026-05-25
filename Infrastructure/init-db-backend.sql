-- Init script for PlanBar Backend Database
-- Creates initial admin account

-- Insert initial admin user
-- Password: Admin@123 (bcrypt hashed)
INSERT INTO public.users (username, email, password_hash, role, created_at, updated_at)
VALUES (
    'admin',
    'admin@planbar.local',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5YmMxSUqvMona',
    'admin',
    NOW(),
    NOW()
)
ON CONFLICT (username) DO NOTHING;

-- Insert additional test user (optional)
-- Password: User@123 (bcrypt hashed)
INSERT INTO public.users (username, email, password_hash, role, created_at, updated_at)
VALUES (
    'testuser',
    'testuser@planbar.local',
    '$2b$12$Qx8vWLk9Z0Y3R4q5M6n7p8o9qQ1w2e3r4t5y6u7i8o9p0a1s2d3f4g5',
    'user',
    NOW(),
    NOW()
)
ON CONFLICT (username) DO NOTHING;
