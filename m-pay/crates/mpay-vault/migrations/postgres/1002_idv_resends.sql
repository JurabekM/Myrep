-- PostgreSQL varianti (2-faza P2.3): INTEGER → BIGINT (Rust i64), BLOB → BYTEA.
-- 2-faza P2.1: OTP SMS qayta yuborishlar soni (SMS bombardimoni va xarajatga qarshi chegara).
ALTER TABLE vault_idv_challenges ADD COLUMN resends BIGINT NOT NULL DEFAULT 0;
