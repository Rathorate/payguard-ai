-- Existing PostgreSQL installations only. Back up the database first.
-- SQLite does not enforce VARCHAR lengths and needs no change for this fix.
BEGIN;
ALTER TABLE audit ALTER COLUMN actor TYPE VARCHAR(254);
COMMIT;
