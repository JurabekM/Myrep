# ZANJIR — Deploy

> 11-fazada to'ldiriladi. Undan oldin 🛑 2-inson darvozasi: domen, server (IP, SSH foydalanuvchi), SMTP/SMS.
> Maxfiy ma'lumotlar faqat `.env` orqali, hech qachon commit qilinmaydi.

## Ma'lumotlarni lokalizatsiya qilish

> ⚠️ **Huquqshunos bilan tekshirilsin.** O'zbekiston fuqarolarining shaxsiy ma'lumotlari O'zbekiston hududidagi
> serverlarda saqlanishi talab qilinadi ("Shaxsga doir ma'lumotlar to'g'risida"gi qonun). Talabning joriy tahriri,
> zaxira nusxalar va CDN/log xizmatlariga tatbiqi huquqshunos tomonidan tasdiqlanmagan.

Reja: PostgreSQL, ilova serveri va shifrlangan zaxiralar — O'zbekistondagi serverda; tashqi xizmatlarga
(xato hisobotlari, metrikalar) shaxsiy ma'lumot yuborilmaydi.

## Server (7-faza, ADR-0011)

Ishga tushirish: `uv run alembic upgrade head` (migratsiya egasi roli bilan), so'ng
`uv run uvicorn --factory zanjir_server.main:app --proxy-headers --forwarded-allow-ips=<Caddy IP>`.

**Baza rollari** (RLS chetlab o'tilmasligi uchun):
- `zanjir_owner` — jadvallar egasi, faqat migratsiya uchun (`alembic upgrade head`). Migratsiya `zanjir_app` rolini
  (NOLOGIN, NOSUPERUSER, NOBYPASSRLS), RLS siyosatlari, triggerlar va `SECURITY DEFINER` qidiruv funksiyalarini yaratadi.
- `zanjir_api` — ilova ulanadigan login roli, **faqat** `zanjir_app` a'zosi:
  `CREATE ROLE zanjir_api LOGIN PASSWORD '...' NOSUPERUSER NOBYPASSRLS; GRANT zanjir_app TO zanjir_api;`
  Ilova har so'rovda `SET LOCAL ROLE zanjir_app` + `app.org_id` qiladi; tashkilot noma'lum yo'llar (kirish, refresh, taklif,
  `/v/{qr_token}`) faqat `zanjir_org_of_*` funksiyalari orqali `org_id` ni topadi. Testlar aynan shunday rol bilan ishlaydi.
- Ilovani superuser yoki jadval egasi bilan ishga tushirmang.

**Muhit o'zgaruvchilari** — `server/.env.example` (faqat `.env` orqali; maxfiy qiymatlar commit qilinmaydi).
- `ZANJIR_REGISTRATION_OPEN=false` (prod): yangi laboratoriyani faqat operator ochadi (vaqtincha true qilib).
- `/metrics` tashqariga ochilmaydi (Caddy'da yopiladi). Rate limiting bitta jarayon xotirasida — bir nechta nusxa bo'lsa
  Redis'ga o'tkaziladi.
