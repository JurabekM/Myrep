# ZANJIR — Xavfsizlik

> RBAC matritsasi — 7-faza; tahdid modeli, OWASP MASVS L1 checklist, topilmalar reestri — 10-faza (ADR-0014).

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
  `LAB_UPDATED`, `PLAN_APPROVED` — LEAD/ADMIN. Protokolni imzolovchi — LEAD/ENGINEER (ADR-0010), NEEDS_REVIEW bo'lsa faqat LEAD izoh bilan.
- Ajratish rejasini APPROVED/EXECUTED holatiga faqat LEAD/ADMIN tasdiqlagan bo'lsa o'tkazish mumkin.

## Tahdid modeli (STRIDE, 10-faza)

**Himoyalanadigan aktivlar:** o'lchov natijalari va imzolangan protokollar (yuridik ahamiyatli hujjat), audit zanjiri,
qurilma maxfiy kaliti (Ed25519 seed), server tokenlari, foydalanuvchilarning shaxsiy ma'lumotlari (F.I.Sh., telefon),
obyektlar sxemasi va ajratish rejalari (xavfsizlikka ta'sir qiladi), normalar to'plami.

**Ishonch chegaralari:** (1) qurilma ↔ server (internet, HTTPS); (2) server ↔ PostgreSQL (ilova roli RLS ostida);
(3) tashkilot ↔ tashkilot (RLS); (4) ochiq tekshirish sahifasi ↔ QR egasi (anonim); (5) qurilma egasi ↔ boshqa ilovalar
(deep link, zaxira nusxa, ekranshot).

| # | Tahdid (STRIDE) | Misol | Himoya | Qoldiq xavf |
|---|---|---|---|---|
| T1 | S — boshqa foydalanuvchi nomidan kirish | parol tanlash, o'g'irlangan refresh token | argon2id; IP bo'yicha va hisob bo'yicha cheklov (10 xato / 15 daq); refresh rotatsiya + qayta ishlatishda oila bekor; access 15 daq | SMS OTP/2FA yo'q (MVP) |
| T2 | S — boshqa qurilma nomidan audit/protokol | soxta imzo, boshqa qurilma ID si | Ed25519 imzo, qurilma — faqat o'z egasi, bekor qilingan qurilma rad | seed qurilmada (Keystore) — root qilingan qurilmada o'g'irlanishi mumkin |
| T3 | T — o'lchov/protokolni o'zgartirish | natijani PASS ga almashtirish | append-only (ilova + DB trigger + huquqlar), audit hash-zanjiri, o'lchov ↔ imzolangan audit hodisasi, protokol payload ↔ serverdagi o'lchovlar, PDF/payload hash, `/ID` | qurilmada sync dan oldin root egasi o'z ma'lumotini o'zgartirishi mumkin — server zanjir bo'yicha aniqlaydi (E2E testi) |
| T4 | T — LWW ni "kelajak" vaqt bilan egallash | soati oldinda qurilma | server `updated_at > hozir + 10 daq` ni rad etadi (`clock_skew`) | soati orqada qurilma o'zgarishi yutqazishi mumkin |
| T5 | R — "men imzolamaganman" | protokol, reja tasdig'i, qadam | har amal — imzolangan audit hodisasi (aktor, qurilma, vaqt), zanjir serverda tekshiriladi | — |
| T6 | I — boshqa tashkilot ma'lumoti | ID ni taxmin qilish, SQL | RLS + kodda `org_id` filtri; ilova imtiyozsiz rol; kompozit FK; ORM/parametrlangan SQL | — |
| T7 | I — ochiq sahifa orqali shaxsiy ma'lumot | QR token | 128 bit token; sahifada faqat imzolovchi F.I.Sh. va tashkilot; `noindex`, `no-store` | PDF (QR egasi uchun hujjatning o'zi) manzil va ismlarni o'z ichiga oladi — qabul qilingan |
| T8 | I — qurilmadagi ma'lumot sizishi | zaxira nusxa, ekranshot, log | `allowBackup=false` + `dataExtractionRules`; FLAG_SECURE imzolash ekranida; logda sir yo'q | SQLite shifrlanmagan (Android FBE ga tayanadi) — M-xavf, reestrda |
| T9 | I — tarmoqda tinglash | ochiq Wi-Fi | faqat HTTPS (ilova URL tekshiruvi + `cleartextTrafficPermitted=false`, faqat tizim CA); serverda HSTS — Caddy (11-faza) | sertifikat pinning yo'q (L2) |
| T10 | D — serverni band qilish | ko'p so'rov, katta paket | rate limiting, 5 MB chegara, push ≤ 500 op, pull sahifalari | bitta jarayon xotirasidagi cheklovlar (ko'p nusxada Redis) |
| T11 | E — rolni oshirish | ENGINEER sozlama/tasdiq yuboradi | API rol talablari (matritsa testi), sync jadval/hodisa rollari, rol bazadan har so'rovda | — |
| T12 | E — xavfli ish ruxsati | reja qadamini o'tkazib yuborish | qadamlar ketma-ket, kuchlanish tekshiruvi — 2 aniq tasdiq (yadro + repozitoriy + UI testlari); ilova "xavfsiz" demaydi | javobgarlik — naryad beruvchi va ish rahbarida (1-qoida) |

## OWASP MASVS L1 checklist (MASVS v2)

| Nazorat | Holat | Dalil |
|---|---|---|
| MASVS-STORAGE-1 maxfiy ma'lumot xavfsiz saqlanadi | ✅ | seed va tokenlar `flutter_secure_storage` (Keystore); SQLite — ⚠️ shifrlanmagan (R-03) |
| MASVS-STORAGE-2 ma'lumot sizib chiqmaydi | ✅ | `allowBackup=false`, `dataExtractionRules`; logga sir yozilmaydi; clipboard — faqat taklif kodi (foydalanuvchi bosganda) |
| MASVS-CRYPTO-1 kuchli kriptografiya | ✅ | Ed25519, SHA-256, RFC 8785; `Random.secure` (seed, QR token); serverda argon2id, HS256 (≥ 32 belgi kalit) |
| MASVS-CRYPTO-2 kalitlar boshqaruvi | ✅ | seed qurilmadan chiqmaydi, `sig_alg` har yozuvda (almashtirish yo'li), qurilmani ADMIN bekor qiladi; JWT kaliti faqat `.env` (rotatsiya — 11-faza RUNBOOK) |
| MASVS-AUTH-1 xavfsiz autentifikatsiya | ✅ | server tomonda; parol + qisqa access + refresh rotatsiya |
| MASVS-AUTH-2 lokal autentifikatsiya | ➖ | ilova biometrik/lokal PIN talab qilmaydi (MVP); qurilma qulfi — foydalanuvchi siyosati (R-05) |
| MASVS-AUTH-3 muhim amallar qo'shimcha tasdiq | ✅ | protokol imzolash, reja tasdiqlash/yakunlash, kuchlanish tekshiruvi — tasdiq dialoglari, hech narsa oldindan belgilanmagan |
| MASVS-NETWORK-1 xavfsiz aloqa | ✅ | faqat HTTPS (kod + network security config), cleartext taqiq |
| MASVS-NETWORK-2 identifikatsiya (pinning) | ➖ | L2; tizim CA (foydalanuvchi CA lariga ishonilmaydi) |
| MASVS-PLATFORM-1 IPC xavfsiz | ✅ | deep link `zanjir://app/n|v/...` faqat ekranni ochadi, amal bajarmaydi; `MethodChannel` faqat FLAG_SECURE |
| MASVS-PLATFORM-2 WebView | ➖ | WebView yo'q |
| MASVS-PLATFORM-3 UI orqali sizish | ✅ | FLAG_SECURE imzolash ekranida (talab bo'yicha faqat shu ekranda); parol maydonlari yashirin |
| MASVS-CODE-1 yangilangan platforma | ✅ | Flutter stable, `targetSdk` Flutter standart (eng yangi) |
| MASVS-CODE-2 yangilanish mexanizmi | ⚠️ | Play orqali; majburiy yangilash yo'q (R-06) |
| MASVS-CODE-3 zaif bog'liqliklar yo'q | ✅ | `tools/audit/osv_audit.py` (OSV.dev) — CI'da har push va haftalik; 2026-10-27: 379 paket, zaiflik yo'q |
| MASVS-CODE-4 kiritishni tekshirish | ✅ | raqamlar qat'iy tahlil, normalar qat'iy YAML yuklovchi, server Pydantic `extra=forbid`, sim formati turlari |
| MASVS-RESILIENCE-* | ➖ | L2/R — obfuskatsiya release build'da (`--obfuscate --split-debug-info`, 12-faza) |
| MASVS-PRIVACY-1..4 | ✅ | minimal ma'lumot (F.I.Sh., telefon); tashqi analitika/xato xizmatlari yo'q; ma'lumot lokalizatsiyasi — DEPLOY.md (huquqshunos) |

## Topilmalar reestri (10-faza xavfsizlik ko'rigi)

Daraja: **Y** — yuqori, **O** — o'rta, **P** — past. Mezon: barcha "yuqori" topilmalar yopilgan.

| # | Daraja | Topilma | Holat |
|---|---|---|---|
| F-01 | Y | Android `allowBackup` standart yoqilgan — baza (shaxsiy ma'lumot, audit) zaxira/ko'chirish orqali chiqib ketishi mumkin | ✅ tuzatildi: `allowBackup=false`, `fullBackupContent=false`, `dataExtractionRules` |
| F-02 | Y | Release build debug kaliti bilan imzolanardi (shablon) | ✅ tuzatildi: imzo faqat `key.properties` dan, kalitsiz release build yiqiladi; `key.properties.example` |
| F-03 | O | Server URL `http://` bo'lishi mumkin edi; cleartext aniq taqiqlanmagan | ✅ tuzatildi: `isAllowedServerUrl` (faqat https; debug'da lokal http), `network_security_config` |
| F-04 | O | `/metrics` ochiq (marshrut, statistik ma'lumot) | ✅ tuzatildi: standart o'chiq, `ZANJIR_METRICS_TOKEN` bilan |
| F-05 | O | Parol tanlash bitta hisobga turli IP lardan | ✅ tuzatildi: hisob bo'yicha cheklov (10 xato / 15 daq → 429) |
| F-06 | O | Soati oldinda qurilma LWW da doim yutadi | ✅ tuzatildi: `clock_skew` (> 10 daq kelajak — rad) |
| F-07 | P | API javoblarida `nosniff`, `no-store`, `X-Frame-Options` yo'q | ✅ tuzatildi: `SecurityHeadersMiddleware` |
| F-08 | P | Katta shriftda (×2) sozlamalar ekrani layout xatosi (accessibility) | ✅ tuzatildi; ×2 shrift testi |

**Qabul qilingan qoldiq xavflar (R):**
- R-01 (O) Sertifikat pinning yo'q — L2; domen va sertifikat siyosati 11-fazada ko'rib chiqiladi.
- R-02 (O) Rate limiting va hisob cheklovi bitta jarayon xotirasida — bitta server nusxasi (11-faza); ko'p nusxada Redis.
- R-03 (O) Lokal SQLite shifrlanmagan — Android FBE (qurilma qulflangan bo'lsa shifrlangan), zaxira o'chirilgan; SQLCipher —
  pilotdan keyin baholanadi (unumdorlik va kalit tiklash).
- R-04 (P) JWT HS256 bitta kalit, rotatsiya qo'lda — RUNBOOK (11-faza).
- R-05 (P) Ilovaga kirishda lokal PIN/biometrik yo'q — qurilma qulfi tashkilot siyosati.
- R-06 (P) Majburiy yangilash yo'q — Play in-app update keyingi bosqichda.
- R-07 (P) Ochiq PDF QR egasiga hujjatdagi shaxsiy ma'lumotni ko'rsatadi — protokolning maqsadi (buyurtmachiga beriladi).
