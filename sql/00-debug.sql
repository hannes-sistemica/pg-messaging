-- Debug information
\echo 'Starting database initialization...'
\echo 'PostgreSQL version:'
SELECT version();

-- Check installed extensions
\echo 'Checking available extensions:'
SELECT name, default_version, installed_version, comment 
FROM pg_available_extensions 
WHERE name = 'http';

-- Set error handling to verbose
\set ON_ERROR_STOP on
\set VERBOSITY verbose