-- PostgreSQL varianti: INTEGER → BIGINT, BLOB → BYTEA.
-- Shield yuqori mavjudligi (ADR-0026): yetakchilik ijarasi (lease) va belgilar ombori snapshot'lari.
-- `epoch` har yetakchi almashganda oshadi — eski yetakchining kechikkan snapshot'i yozilmaydi.
CREATE TABLE shield_leader (
    id         BIGINT PRIMARY KEY CHECK (id = 1),
    holder     TEXT    NOT NULL,
    epoch      BIGINT NOT NULL,
    expires_at BIGINT NOT NULL
);

-- Snapshot'da PAN yo'q: kartalar — PanFingerprint (HMAC), qurilmalar — DeviceId.
CREATE TABLE shield_snapshots (
    snapshot_id TEXT    PRIMARY KEY,
    epoch       BIGINT NOT NULL,
    holder      TEXT    NOT NULL,
    created_at  BIGINT NOT NULL,
    size        BIGINT NOT NULL,
    sha256      TEXT    NOT NULL,
    data        BYTEA    NOT NULL
);
CREATE INDEX shield_snapshots_created ON shield_snapshots (created_at);
