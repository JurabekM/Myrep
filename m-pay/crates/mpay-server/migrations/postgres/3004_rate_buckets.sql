-- 3-faza tayyorgarligi: ko'p instansiyada umumiy so'rovlar chegarasi (token bucket). Kalit —
-- SHA-256(doira ‖ IP yoki qurilma ID) hex: IP manzillar DB'ga ochiq yozilmaydi.
CREATE TABLE rate_buckets (
    k      TEXT PRIMARY KEY,
    tokens DOUBLE PRECISION NOT NULL,
    ts     BIGINT NOT NULL
);
CREATE INDEX rate_buckets_ts ON rate_buckets (ts);
