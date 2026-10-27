-- Shield yuqori mavjudligi (ADR-0026): yetakchilik ijarasi (lease) va belgilar ombori snapshot'lari.
-- `epoch` har yetakchi almashganda oshadi — eski yetakchining kechikkan snapshot'i yozilmaydi.
CREATE TABLE shield_leader (
    id         INTEGER PRIMARY KEY CHECK (id = 1),
    holder     TEXT    NOT NULL,
    epoch      INTEGER NOT NULL,
    expires_at INTEGER NOT NULL
);

-- Snapshot'da PAN yo'q: kartalar — PanFingerprint (HMAC), qurilmalar — DeviceId.
CREATE TABLE shield_snapshots (
    snapshot_id TEXT    PRIMARY KEY,
    epoch       INTEGER NOT NULL,
    holder      TEXT    NOT NULL,
    created_at  INTEGER NOT NULL,
    size        INTEGER NOT NULL,
    sha256      TEXT    NOT NULL,
    data        BLOB    NOT NULL
);
CREATE INDEX shield_snapshots_created ON shield_snapshots (created_at);
