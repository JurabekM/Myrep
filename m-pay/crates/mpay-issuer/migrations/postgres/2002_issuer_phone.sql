-- PostgreSQL varianti (2-faza P2.3): INTEGER → BIGINT (Rust i64), BLOB → BYTEA.
-- 2-faza P2.1: karta egasining telefon raqami (OTP SMS uchun). Faqat emitent saqlaydi.
ALTER TABLE issuer_accounts ADD COLUMN phone TEXT;
