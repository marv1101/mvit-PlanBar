-- Demo seed data for PlanBar demonstration instance
-- Run after the backend has started and created the schema:
--   PGPASSWORD=<pwd> psql -h localhost -U planbar -d demo_planbar -f init-demo-data.sql

-- Demo users are seeded by the backend (see PlanBar - Backend/src/app/main.py seed_initial_users)
-- Only insert demo data that references backend-seeded users

-- Demo employees (referencing admin user)
INSERT INTO employees (name, color, user_id, created_at, updated_at)
SELECT 'Max Mustermann', '#3b82f6', id, now(), now() FROM users WHERE email = 'admin@mphion.de'
AND NOT EXISTS (SELECT 1 FROM employees WHERE name = 'Max Mustermann' AND user_id = (SELECT id FROM users WHERE email = 'admin@mphion.de'));

INSERT INTO employees (name, color, user_id, created_at, updated_at)
SELECT 'Erika Musterfrau', '#ef4444', id, now(), now() FROM users WHERE email = 'admin@mphion.de'
AND NOT EXISTS (SELECT 1 FROM employees WHERE name = 'Erika Musterfrau' AND user_id = (SELECT id FROM users WHERE email = 'admin@mphion.de'));

INSERT INTO employees (name, color, user_id, created_at, updated_at)
SELECT 'John Doe', '#22c55e', id, now(), now() FROM users WHERE email = 'admin@mphion.de'
AND NOT EXISTS (SELECT 1 FROM employees WHERE name = 'John Doe' AND user_id = (SELECT id FROM users WHERE email = 'admin@mphion.de'));

INSERT INTO employees (name, color, user_id, created_at, updated_at)
SELECT 'Jane Smith', '#f59e0b', id, now(), now() FROM users WHERE email = 'admin@mphion.de'
AND NOT EXISTS (SELECT 1 FROM employees WHERE name = 'Jane Smith' AND user_id = (SELECT id FROM users WHERE email = 'admin@mphion.de'));

INSERT INTO employees (name, color, user_id, created_at, updated_at)
SELECT 'Anna Schmidt', '#8b5cf6', id, now(), now() FROM users WHERE email = 'admin@mphion.de'
AND NOT EXISTS (SELECT 1 FROM employees WHERE name = 'Anna Schmidt' AND user_id = (SELECT id FROM users WHERE email = 'admin@mphion.de'));

-- Demo roles
INSERT INTO roles (name, description, user_id, created_at, updated_at)
SELECT 'Frühschicht', '06:00 - 14:00 Uhr', id, now(), now() FROM users WHERE email = 'admin@mphion.de'
AND NOT EXISTS (SELECT 1 FROM roles WHERE name = 'Frühschicht' AND user_id = (SELECT id FROM users WHERE email = 'admin@mphion.de'));

INSERT INTO roles (name, description, user_id, created_at, updated_at)
SELECT 'Spätschicht', '14:00 - 22:00 Uhr', id, now(), now() FROM users WHERE email = 'admin@mphion.de'
AND NOT EXISTS (SELECT 1 FROM roles WHERE name = 'Spätschicht' AND user_id = (SELECT id FROM users WHERE email = 'admin@mphion.de'));

INSERT INTO roles (name, description, user_id, created_at, updated_at)
SELECT 'Nachtschicht', '22:00 - 06:00 Uhr', id, now(), now() FROM users WHERE email = 'admin@mphion.de'
AND NOT EXISTS (SELECT 1 FROM roles WHERE name = 'Nachtschicht' AND user_id = (SELECT id FROM users WHERE email = 'admin@mphion.de'));
