-- Lincoln High School setup with local auth accounts
-- Idempotent: safe to run multiple times

-- School
INSERT INTO schools (school_id, name, contact_email, country, status, created_at)
VALUES (
  'a1b2c3d4-e5f6-7890-abcd-ef1234567890'::uuid,
  'Lincoln High',
  'admin@lincoln.demo',
  'USA',
  'active'::school_status,
  NOW()
)
ON CONFLICT (school_id) DO NOTHING;

-- Admin user
INSERT INTO teachers (teacher_id, external_auth_id, auth_provider, name, email, school_id, role, created_at, password_hash, account_status)
VALUES (
  'a1b2c3d4-e5f6-7890-abcd-ef1111111111'::uuid,
  'admin-lincoln-1'::text,
  'local'::auth_provider,
  'Admin User',
  'admin@lincoln.demo',
  'a1b2c3d4-e5f6-7890-abcd-ef1234567890'::uuid,
  'admin'::teacher_role,
  NOW(),
  '$2b$12$71wWexV7GEGzqxkCyZG/cemExwE3SSY56l2L7rq8PqW7b8EimasNS',  -- demo123
  'active'::account_status
)
ON CONFLICT (teacher_id) DO NOTHING;

-- 5 Teachers
INSERT INTO teachers (teacher_id, external_auth_id, auth_provider, name, email, school_id, role, created_at, password_hash, account_status)
VALUES
  ('a1b2c3d4-e5f6-7890-abcd-ef1111111112'::uuid, 'teacher-1', 'local', 'Marcus Rivera', 'marcus.rivera@lincoln.demo', 'a1b2c3d4-e5f6-7890-abcd-ef1234567890'::uuid, 'teacher'::teacher_role, NOW(), '$2b$12$71wWexV7GEGzqxkCyZG/cemExwE3SSY56l2L7rq8PqW7b8EimasNS', 'active'::account_status),
  ('a1b2c3d4-e5f6-7890-abcd-ef1111111113'::uuid, 'teacher-2', 'local', 'Jasmine Patel', 'jasmine.patel@lincoln.demo', 'a1b2c3d4-e5f6-7890-abcd-ef1234567890'::uuid, 'teacher'::teacher_role, NOW(), '$2b$12$71wWexV7GEGzqxkCyZG/cemExwE3SSY56l2L7rq8PqW7b8EimasNS', 'active'::account_status),
  ('a1b2c3d4-e5f6-7890-abcd-ef1111111114'::uuid, 'teacher-3', 'local', 'David Kim', 'david.kim@lincoln.demo', 'a1b2c3d4-e5f6-7890-abcd-ef1234567890'::uuid, 'teacher'::teacher_role, NOW(), '$2b$12$71wWexV7GEGzqxkCyZG/cemExwE3SSY56l2L7rq8PqW7b8EimasNS', 'active'::account_status),
  ('a1b2c3d4-e5f6-7890-abcd-ef1111111115'::uuid, 'teacher-4', 'local', 'Sophia Garcia', 'sophia.garcia@lincoln.demo', 'a1b2c3d4-e5f6-7890-abcd-ef1234567890'::uuid, 'teacher'::teacher_role, NOW(), '$2b$12$71wWexV7GEGzqxkCyZG/cemExwE3SSY56l2L7rq8PqW7b8EimasNS', 'active'::account_status),
  ('a1b2c3d4-e5f6-7890-abcd-ef1111111116'::uuid, 'teacher-5', 'local', 'James Thompson', 'james.thompson@lincoln.demo', 'a1b2c3d4-e5f6-7890-abcd-ef1234567890'::uuid, 'teacher'::teacher_role, NOW(), '$2b$12$71wWexV7GEGzqxkCyZG/cemExwE3SSY56l2L7rq8PqW7b8EimasNS', 'active'::account_status)
ON CONFLICT (teacher_id) DO NOTHING;

-- 15 Students (3 per grade, 8-12)
INSERT INTO students (student_id, external_auth_id, auth_provider, name, email, grade, school_id, account_status, created_at, password_hash, first_login, locale)
VALUES
  -- Grade 8
  ('a1b2c3d4-e5f6-7890-abcd-ef2111111111'::uuid, 'student-g8-1', 'local', 'Alex Johnson', 'alex.johnson@lincoln.demo', 8, 'a1b2c3d4-e5f6-7890-abcd-ef1234567890'::uuid, 'active'::account_status, NOW(), '$2b$12$71wWexV7GEGzqxkCyZG/cemExwE3SSY56l2L7rq8PqW7b8EimasNS', false, 'en'),
  ('a1b2c3d4-e5f6-7890-abcd-ef2111111112'::uuid, 'student-g8-2', 'local', 'Bailey Martinez', 'bailey.martinez@lincoln.demo', 8, 'a1b2c3d4-e5f6-7890-abcd-ef1234567890'::uuid, 'active'::account_status, NOW(), '$2b$12$71wWexV7GEGzqxkCyZG/cemExwE3SSY56l2L7rq8PqW7b8EimasNS', false, 'en'),
  ('a1b2c3d4-e5f6-7890-abcd-ef2111111113'::uuid, 'student-g8-3', 'local', 'Casey Taylor', 'casey.taylor@lincoln.demo', 8, 'a1b2c3d4-e5f6-7890-abcd-ef1234567890'::uuid, 'active'::account_status, NOW(), '$2b$12$71wWexV7GEGzqxkCyZG/cemExwE3SSY56l2L7rq8PqW7b8EimasNS', false, 'en'),
  -- Grade 9
  ('a1b2c3d4-e5f6-7890-abcd-ef2111111114'::uuid, 'student-g9-1', 'local', 'Dana Anderson', 'dana.anderson@lincoln.demo', 9, 'a1b2c3d4-e5f6-7890-abcd-ef1234567890'::uuid, 'active'::account_status, NOW(), '$2b$12$71wWexV7GEGzqxkCyZG/cemExwE3SSY56l2L7rq8PqW7b8EimasNS', false, 'en'),
  ('a1b2c3d4-e5f6-7890-abcd-ef2111111115'::uuid, 'student-g9-2', 'local', 'Elliott Brown', 'elliott.brown@lincoln.demo', 9, 'a1b2c3d4-e5f6-7890-abcd-ef1234567890'::uuid, 'active'::account_status, NOW(), '$2b$12$71wWexV7GEGzqxkCyZG/cemExwE3SSY56l2L7rq8PqW7b8EimasNS', false, 'en'),
  ('a1b2c3d4-e5f6-7890-abcd-ef2111111116'::uuid, 'student-g9-3', 'local', 'Finley Davis', 'finley.davis@lincoln.demo', 9, 'a1b2c3d4-e5f6-7890-abcd-ef1234567890'::uuid, 'active'::account_status, NOW(), '$2b$12$71wWexV7GEGzqxkCyZG/cemExwE3SSY56l2L7rq8PqW7b8EimasNS', false, 'en'),
  -- Grade 10
  ('a1b2c3d4-e5f6-7890-abcd-ef2111111117'::uuid, 'student-g10-1', 'local', 'Gray Miller', 'gray.miller@lincoln.demo', 10, 'a1b2c3d4-e5f6-7890-abcd-ef1234567890'::uuid, 'active'::account_status, NOW(), '$2b$12$71wWexV7GEGzqxkCyZG/cemExwE3SSY56l2L7rq8PqW7b8EimasNS', false, 'en'),
  ('a1b2c3d4-e5f6-7890-abcd-ef2111111118'::uuid, 'student-g10-2', 'local', 'Harper Wilson', 'harper.wilson@lincoln.demo', 10, 'a1b2c3d4-e5f6-7890-abcd-ef1234567890'::uuid, 'active'::account_status, NOW(), '$2b$12$71wWexV7GEGzqxkCyZG/cemExwE3SSY56l2L7rq8PqW7b8EimasNS', false, 'en'),
  ('a1b2c3d4-e5f6-7890-abcd-ef2111111119'::uuid, 'student-g10-3', 'local', 'Iris Moore', 'iris.moore@lincoln.demo', 10, 'a1b2c3d4-e5f6-7890-abcd-ef1234567890'::uuid, 'active'::account_status, NOW(), '$2b$12$71wWexV7GEGzqxkCyZG/cemExwE3SSY56l2L7rq8PqW7b8EimasNS', false, 'en'),
  -- Grade 11
  ('a1b2c3d4-e5f6-7890-abcd-ef2111111120'::uuid, 'student-g11-1', 'local', 'Jules Jackson', 'jules.jackson@lincoln.demo', 11, 'a1b2c3d4-e5f6-7890-abcd-ef1234567890'::uuid, 'active'::account_status, NOW(), '$2b$12$71wWexV7GEGzqxkCyZG/cemExwE3SSY56l2L7rq8PqW7b8EimasNS', false, 'en'),
  ('a1b2c3d4-e5f6-7890-abcd-ef2111111121'::uuid, 'student-g11-2', 'local', 'Kelly White', 'kelly.white@lincoln.demo', 11, 'a1b2c3d4-e5f6-7890-abcd-ef1234567890'::uuid, 'active'::account_status, NOW(), '$2b$12$71wWexV7GEGzqxkCyZG/cemExwE3SSY56l2L7rq8PqW7b8EimasNS', false, 'en'),
  ('a1b2c3d4-e5f6-7890-abcd-ef2111111122'::uuid, 'student-g11-3', 'local', 'Logan Harris', 'logan.harris@lincoln.demo', 11, 'a1b2c3d4-e5f6-7890-abcd-ef1234567890'::uuid, 'active'::account_status, NOW(), '$2b$12$71wWexV7GEGzqxkCyZG/cemExwE3SSY56l2L7rq8PqW7b8EimasNS', false, 'en'),
  -- Grade 12
  ('a1b2c3d4-e5f6-7890-abcd-ef2111111123'::uuid, 'student-g12-1', 'local', 'Morgan Clark', 'morgan.clark@lincoln.demo', 12, 'a1b2c3d4-e5f6-7890-abcd-ef1234567890'::uuid, 'active'::account_status, NOW(), '$2b$12$71wWexV7GEGzqxkCyZG/cemExwE3SSY56l2L7rq8PqW7b8EimasNS', false, 'en'),
  ('a1b2c3d4-e5f6-7890-abcd-ef2111111124'::uuid, 'student-g12-2', 'local', 'River Lewis', 'river.lewis@lincoln.demo', 12, 'a1b2c3d4-e5f6-7890-abcd-ef1234567890'::uuid, 'active'::account_status, NOW(), '$2b$12$71wWexV7GEGzqxkCyZG/cemExwE3SSY56l2L7rq8PqW7b8EimasNS', false, 'en'),
  ('a1b2c3d4-e5f6-7890-abcd-ef2111111125'::uuid, 'student-g12-3', 'local', 'Sam Walker', 'sam.walker@lincoln.demo', 12, 'a1b2c3d4-e5f6-7890-abcd-ef1234567890'::uuid, 'active'::account_status, NOW(), '$2b$12$71wWexV7GEGzqxkCyZG/cemExwE3SSY56l2L7rq8PqW7b8EimasNS', false, 'en')
ON CONFLICT (student_id) DO NOTHING;
