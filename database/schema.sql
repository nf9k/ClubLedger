-- ClubLedger base schema
-- Applied automatically on first container start via docker-entrypoint-initdb.d

CREATE TABLE IF NOT EXISTS members (
    id              INT PRIMARY KEY AUTO_INCREMENT,
    call_sign       VARCHAR(20) UNIQUE NOT NULL,
    password_hash   VARCHAR(255) NOT NULL,
    email           VARCHAR(255),
    name            VARCHAR(255),
    primary_rep     VARCHAR(255),
    rep_call        VARCHAR(20),
    address         VARCHAR(255),
    city            VARCHAR(100),
    state           VARCHAR(2),
    zip             VARCHAR(10),
    telephone       VARCHAR(20),
    paid_thru       VARCHAR(4),
    member_type     VARCHAR(20),
    is_admin        TINYINT DEFAULT 0,
    totp_secret     VARCHAR(32)  NULL,
    totp_enabled    TINYINT(1)   NOT NULL DEFAULT 0,
    webauthn_enabled TINYINT(1)  NOT NULL DEFAULT 0,
    admin_comments  TEXT DEFAULT NULL,
    expiration_status       VARCHAR(20) DEFAULT 'unknown',
    expiration_notice_sent  DATE DEFAULT NULL
);

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
    updated_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_zip (zip)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS password_reset_tokens (
    id          INT PRIMARY KEY AUTO_INCREMENT,
    user_id     INT NOT NULL,
    token       VARCHAR(255) NOT NULL,
    expires_at  DATETIME NOT NULL,
    used        BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (user_id) REFERENCES members(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS totp_backup_codes (
  id         INT           NOT NULL AUTO_INCREMENT PRIMARY KEY,
  user_id    INT           NOT NULL,
  code_hash  VARCHAR(255)  NOT NULL,
  used       TINYINT(1)    NOT NULL DEFAULT 0,
  created_at DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_tbc_user FOREIGN KEY (user_id) REFERENCES members(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS webauthn_credentials (
  id            INT           NOT NULL AUTO_INCREMENT PRIMARY KEY,
  user_id       INT           NOT NULL,
  credential_id VARCHAR(512)  NOT NULL,
  public_key    TEXT          NOT NULL,
  sign_count    INT           NOT NULL DEFAULT 0,
  name          VARCHAR(100)  NOT NULL DEFAULT 'Security Key',
  created_at    DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_wac_user   FOREIGN KEY (user_id) REFERENCES members(id) ON DELETE CASCADE,
  CONSTRAINT uq_credential UNIQUE KEY (credential_id(255))
);
