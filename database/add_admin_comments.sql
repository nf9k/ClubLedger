-- Migration: Add admin comments field for internal notes
-- Run with: docker exec -i <db_container> mariadb -u root -p"${DB_ROOT_PASSWORD}" "${DB_NAME}" < database/add_admin_comments.sql

-- Add admin comments field
ALTER TABLE members 
ADD COLUMN admin_comments TEXT DEFAULT NULL COMMENT 'Administrator-only notes for payment tracking, etc. Max 500 chars';

-- Show results
SELECT COUNT(*) as total_members FROM members;
DESCRIBE members;
