# ZANJIR — Xavfsizlik

> 7-fazada RBAC matritsasi, 10-fazada tahdid modeli va OWASP MASVS L1 checklist to'ldiriladi.

## Asosiy tamoyillar (`CLAUDE.md` o'zgarmas qoidalaridan)
- `measurement`, `protocol`, `audit_event` — faqat qo'shiladi (DB trigger + repozitoriy darajasi).
- Tashkilotlar ajratilgan: `org_id` filtri + Postgres RLS.
- Maxfiy kalitlar Android Keystore'da; serverga faqat ochiq kalit yuboriladi.
- Logga parol, token, kalit va shaxsiy ma'lumot yozilmaydi.
- Protokol: payload (kanonik JSON) va PDF hash'lari Ed25519 bilan imzolanadi; imzolangan PDF saqlanadi, `/ID` = payload hash
  (ADR-0010). Imzolash ekranida ekranshot va ekran yozuvi taqiqlangan (Android `FLAG_SECURE`).
- Imzolash bloklanadi: muddati o'tgan asbob, tekshirilmagan normalar, litsenziya yo'q/muddati o'tgan, NEEDS_REVIEW (faqat LEAD
  izoh bilan), bekor qilingan qurilma, VIEWER/ADMIN roli (ADR-0010, 5-band).

## RBAC matritsasi
_7-fazada._

## Tahdid modeli
_10-fazada._
