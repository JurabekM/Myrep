-- PostgreSQL varianti (2-faza P2.3): INTEGER → BIGINT (Rust i64), BLOB → BYTEA.
-- 2-faza P2.4: ko'p instansiya — PQ Link sessiyalari va ishlatilgan ro'yxatdan o'tish nonce'lari
-- umumiy omborda. Sessiya kalitlari KEK bilan shifrlangan (`sealed`, AAD = sessiya ID va holat);
-- `seq` hisoblagichlari ochiq (atomar UPDATE), qurilma ma'lumoti — ochiq kalit va ID (maxfiy emas).
CREATE TABLE pqlink_sessions (
    session_id     BYTEA PRIMARY KEY,
    state          TEXT    NOT NULL CHECK (state IN ('PENDING', 'ESTABLISHED')),
    nonce          BYTEA    NOT NULL,
    sealed         BYTEA    NOT NULL,
    device_id      TEXT,
    security_level BIGINT,
    attested_at    BIGINT,
    recv_seq       BIGINT NOT NULL DEFAULT 1,
    send_seq       BIGINT NOT NULL DEFAULT 1,
    expires_at     BIGINT NOT NULL
);
CREATE INDEX pqlink_sessions_expires ON pqlink_sessions (expires_at);

CREATE TABLE pqlink_used_nonces (
    nonce       BYTEA PRIMARY KEY,
    expires_at  BIGINT NOT NULL
);
CREATE INDEX pqlink_used_nonces_expires ON pqlink_used_nonces (expires_at);
