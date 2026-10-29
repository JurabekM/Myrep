-- Hamyon (product ilova): kim to'xtatgan — `DEVICE` (foydalanuvchi o'zi) yoki `BANK` (operator, emitent).
-- Foydalanuvchi faqat o'zi to'xtatgan tokenni qayta yoqa oladi (bank to'xtatganini — yo'q).
ALTER TABLE vault_tokens ADD COLUMN suspended_by TEXT;
