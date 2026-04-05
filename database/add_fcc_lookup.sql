-- Migration: Add FCC license lookup table
-- Run with: docker exec -i <db_container> mariadb -u root -p"${DB_ROOT_PASSWORD}" "${DB_NAME}" < database/add_fcc_lookup.sql

CREATE TABLE IF NOT EXISTS fcc_licenses (
    callsign        VARCHAR(10)  NOT NULL PRIMARY KEY,
    fname           VARCHAR(100),
    mi              VARCHAR(5),
    lname           VARCHAR(100),
    suffix          VARCHAR(20),
    address         VARCHAR(255),
    city            VARCHAR(100),
    state           CHAR(2),
    zip             VARCHAR(10),
    license_class   VARCHAR(20),
    license_status  CHAR(1),
    updated_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

SELECT 'fcc_licenses table ready.' AS status;
