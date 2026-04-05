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
    admin_comments  TEXT DEFAULT NULL,
    expiration_status       VARCHAR(20) DEFAULT 'unknown',
    expiration_notice_sent  DATE DEFAULT NULL
);

CREATE TABLE IF NOT EXISTS password_reset_tokens (
    id          INT PRIMARY KEY AUTO_INCREMENT,
    user_id     INT NOT NULL,
    token       VARCHAR(255) NOT NULL,
    expires_at  DATETIME NOT NULL,
    used        BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (user_id) REFERENCES members(id) ON DELETE CASCADE
);
