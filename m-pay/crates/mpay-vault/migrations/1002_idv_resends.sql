-- 2-faza P2.1: OTP SMS qayta yuborishlar soni (SMS bombardimoni va xarajatga qarshi chegara).
ALTER TABLE vault_idv_challenges ADD COLUMN resends INTEGER NOT NULL DEFAULT 0;
