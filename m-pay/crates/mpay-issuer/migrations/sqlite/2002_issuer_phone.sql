-- 2-faza P2.1: karta egasining telefon raqami (OTP SMS uchun). Faqat emitent saqlaydi.
ALTER TABLE issuer_accounts ADD COLUMN phone TEXT;
