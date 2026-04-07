-- Migration: Add 2FA support (TOTP + WebAuthn)

ALTER TABLE members
  ADD COLUMN totp_secret      VARCHAR(32)   NULL        AFTER is_admin,
  ADD COLUMN totp_enabled     TINYINT(1)    NOT NULL DEFAULT 0 AFTER totp_secret,
  ADD COLUMN webauthn_enabled TINYINT(1)    NOT NULL DEFAULT 0 AFTER totp_enabled;

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
