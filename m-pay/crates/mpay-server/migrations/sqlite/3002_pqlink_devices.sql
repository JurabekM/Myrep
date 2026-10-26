-- PQ Link: ro'yxatga olingan qurilmalar (1-faza P1.7, ADR-0013). Yangi qurilma attestatsiya
-- challenge'i sifatida server nonce'ini ko'rsatib ro'yxatga olinadi; keyin nonce talab qilinmaydi.
CREATE TABLE pqlink_devices (
    device_id      TEXT    PRIMARY KEY,
    security_level TEXT    NOT NULL,
    enrolled_at    INTEGER NOT NULL
);
