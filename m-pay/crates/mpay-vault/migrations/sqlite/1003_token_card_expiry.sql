-- 3-faza tayyorgarligi: token muddatini yangilash (ADR-0022). Har token o'z provisioning'ida (ID&V
-- bilan) tasdiqlangan karta muddatini saqlaydi — uzaytirish shundan oshmaydi.
ALTER TABLE vault_tokens ADD COLUMN card_expiry TEXT;
UPDATE vault_tokens SET card_expiry = (SELECT c.expiry FROM vault_cards c WHERE c.card_id = vault_tokens.card_id);
