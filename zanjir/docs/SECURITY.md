# ZANJIR — Xavfsizlik

> 7-fazada RBAC matritsasi, 10-fazada tahdid modeli va OWASP MASVS L1 checklist to'ldiriladi.

## Asosiy tamoyillar (`CLAUDE.md` o'zgarmas qoidalaridan)
- `measurement`, `protocol`, `audit_event` — faqat qo'shiladi (DB trigger + repozitoriy darajasi).
- Tashkilotlar ajratilgan: `org_id` filtri + Postgres RLS.
- Maxfiy kalitlar Android Keystore'da; serverga faqat ochiq kalit yuboriladi.
- Logga parol, token, kalit va shaxsiy ma'lumot yozilmaydi.
- Protokol: payload (kanonik JSON) va PDF hash'lari Ed25519 bilan imzolanadi; imzolangan PDF saqlanadi, `/ID` = payload hash
  (ADR-0010). Imzolash ekranida ekranshot va ekran yozuvi taqiqlangan (Android `FLAG_SECURE`).
- Server: argon2id (RFC 9106 parametrlari), access JWT 15 daqiqa (HS256, kalit faqat `.env`), refresh rotatsiya — eski
  token qayta kelsa butun oila bekor qilinadi; kirish xatolari bir xil (telefon mavjudligini bilib bo'lmaydi).
- RLS: ilova imtiyozsiz rol bilan ulanadi, har so'rov `SET LOCAL ROLE zanjir_app` + `app.org_id`; tashkilot noma'lum
  yo'llar (kirish, refresh, taklif, `/v/`) faqat aniq kalit bo'yicha `org_id` qaytaradigan `SECURITY DEFINER` funksiyalar orqali; jadvallar orasidagi havolalar `(org_id, id)` kompozit
  kalit — boshqa tashkilot yozuviga bog'lanib bo'lmaydi. Append-only jadvallarda UPDATE/DELETE/TRUNCATE trigger bilan
  taqiqlangan (egasi uchun ham).
- `sync/push`: audit zanjiri (seq, prev_hash, hash, Ed25519) tekshiriladi; o'lchov va protokol imzolangan audit hodisasi
  bilan bog'langan bo'lishi shart; protokol hujjati qayta tekshiriladi (payload/PDF hash, `/ID`, imzo, 6-qoida,
  payload'dagi natijalar serverdagilar bilan bir xil). Bitta xato — butun paket rad etiladi.
- Himoya: rate limiting (`/auth/*` — daqiqasiga 10 ta IP bo'yicha), so'rov hajmi 5 MB, CORS faqat sozlangan domenlar,
  tekshirish sahifasida qat'iy CSP, logda faqat marshrut shabloni (token, telefon, parol yo'q).
- Ilova: server tokenlari va qurilma kaliti `flutter_secure_storage` (Android Keystore) da; serverga faqat ochiq kalit.
  Sinxronlash xatolari foydalanuvchiga barqaror kod bilan ko'rsatiladi, navbatdagi ma'lumot o'chirilmaydi (ADR-0012).
- Imzolash bloklanadi: muddati o'tgan asbob, tekshirilmagan normalar, litsenziya yo'q/muddati o'tgan, NEEDS_REVIEW (faqat LEAD
  izoh bilan), bekor qilingan qurilma, VIEWER/ADMIN roli (ADR-0010, 5-band).

## RBAC matritsasi (7-faza, ADR-0011)

Rollar: ADMIN > LEAD > ENGINEER > VIEWER. Rol har so'rovda bazadan olinadi (o'zgarish va o'chirish darhol amal qiladi).
Jadval `server/tests/test_rbac_matrix.py` dagi `MATRIX` bilan bir xil; test har endpointni har rol (+ anonim) bilan
chaqiradi va matritsada yo'q endpoint qolmaganini tekshiradi.

| Endpoint | Anonim | VIEWER | ENGINEER | LEAD | ADMIN |
|---|---|---|---|---|---|
| `POST /auth/register` (faqat `REGISTRATION_OPEN`), `/auth/login`, `/auth/refresh`, `/auth/logout`, `/auth/accept-invite`, `/auth/otp/request` (o'chiq) | ✅ | ✅ | ✅ | ✅ | ✅ |
| `GET /v/{qr_token}`, `GET /v/{qr_token}/pdf`, `/healthz`, `/readyz`, `/metrics` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `GET /me`, `GET /devices`, `GET /sync/pull` | ❌ 401 | ✅ | ✅ | ✅ | ✅ |
| `POST /devices`, `POST /sync/push` | ❌ 401 | ❌ 403 | ✅ | ✅ | ✅ |
| `POST /invites`, `GET /invites`, `GET /users` | ❌ 401 | ❌ 403 | ❌ 403 | ✅ | ✅ |
| `PATCH /users/{id}/role`, `DELETE /users/{id}`, `POST /devices/{id}/revoke` | ❌ 401 | ❌ 403 | ❌ 403 | ❌ 403 | ✅ |

Qo'shimcha qoidalar:
- Taklif: ADMIN — istalgan rolga, LEAD — faqat ENGINEER/VIEWER. Kod 80 bit, bir martalik, muddatli; bazada hash'i.
- `sync/push` jadval darajasida: `organization`, `org_setting`, `norm_set` — LEAD/ADMIN; `app_user`, `device` — push qilinmaydi
  (faqat API). Audit hodisalari: faqat o'z qurilmasi va o'z nomidan; `PROTOCOL_REVOKED`, `SETTINGS_CHANGED`,
  `LAB_UPDATED` — LEAD/ADMIN. Protokolni imzolovchi — LEAD/ENGINEER (ADR-0010), NEEDS_REVIEW bo'lsa faqat LEAD izoh bilan.
- Ajratish rejasini APPROVED/EXECUTED holatiga faqat LEAD/ADMIN tasdiqlagan bo'lsa o'tkazish mumkin.

## Tahdid modeli
_10-fazada._
