-- 2-faza P2.4: ko'p instansiya — PQ Link sessiyalari va ishlatilgan ro'yxatdan o'tish nonce'lari
-- umumiy omborda. Sessiya kalitlari KEK bilan shifrlangan (`sealed`, AAD = sessiya ID va holat);
-- `seq` hisoblagichlari ochiq (atomar UPDATE), qurilma ma'lumoti — ochiq kalit va ID (maxfiy emas).
CREATE TABLE pqlink_sessions (
    session_id     BLOB PRIMARY KEY,
    state          TEXT    NOT NULL CHECK (state IN ('PENDING', 'ESTABLISHED')),
    nonce          BLOB    NOT NULL,
    sealed         BLOB    NOT NULL,
    device_id      TEXT,
    security_level INTEGER,
    attested_at    INTEGER,
    recv_seq       INTEGER NOT NULL DEFAULT 1,
    send_seq       INTEGER NOT NULL DEFAULT 1,
    expires_at     INTEGER NOT NULL
);
CREATE INDEX pqlink_sessions_expires ON pqlink_sessions (expires_at);

CREATE TABLE pqlink_used_nonces (
    nonce       BLOB PRIMARY KEY,
    expires_at  INTEGER NOT NULL
);
CREATE INDEX pqlink_used_nonces_expires ON pqlink_used_nonces (expires_at);
