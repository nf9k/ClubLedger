-- Migration: Add expiration notification tracking
-- Run with: docker exec -i <db_container> mariadb -u root -p"${DB_ROOT_PASSWORD}" "${DB_NAME}" < database/add_expiration_tracking.sql

-- Add columns for tracking expiration notifications
ALTER TABLE members 
ADD COLUMN expiration_notice_sent DATE DEFAULT NULL COMMENT 'Last date expiration notice was sent',
ADD COLUMN expiration_status VARCHAR(20) DEFAULT 'unknown' COMMENT 'Last known status: active, expiring, expired, unknown';

-- Update existing records to set initial status based on paid_thru
UPDATE members 
SET expiration_status = CASE
    WHEN paid_thru IS NULL THEN 'unknown'
    WHEN CAST(paid_thru AS UNSIGNED) < YEAR(CURDATE()) THEN 'expired'
    WHEN CAST(paid_thru AS UNSIGNED) = YEAR(CURDATE()) AND MONTH(CURDATE()) >= 11 THEN 'expiring'
    WHEN CAST(paid_thru AS UNSIGNED) >= YEAR(CURDATE()) THEN 'active'
    ELSE 'unknown'
END
WHERE paid_thru IS NOT NULL AND paid_thru != '';

-- Show results
SELECT 
    COUNT(*) as total,
    SUM(CASE WHEN expiration_status = 'active' THEN 1 ELSE 0 END) as active,
    SUM(CASE WHEN expiration_status = 'expiring' THEN 1 ELSE 0 END) as expiring,
    SUM(CASE WHEN expiration_status = 'expired' THEN 1 ELSE 0 END) as expired,
    SUM(CASE WHEN expiration_status = 'unknown' THEN 1 ELSE 0 END) as unknown
FROM members;
