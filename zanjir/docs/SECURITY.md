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
| T4 | T — LWW ni "kelajak" vaqt bilan egallash | soati oldinda qurilma | server LWW jadvallarida `updated_at > hozir + 10 daq` ni rad etadi (`clock_skew`); append-only imzolangan yozuvlar LWW'da qatnashmaydi | soati orqada qurilma o'zgarishi yutqazishi mumkin; qurilma soatini orqaga surib imzo sanasini "eskirtirish" (offline-first'ning o'zi) |
| T5 | R — "men imzolamaganman" | protokol, reja tasdig'i, qadam | har amal — imzolangan audit hodisasi (aktor, qurilma, vaqt), zanjir serverda tekshiriladi | — |
| T6 | I — boshqa tashkilot ma'lumoti | ID ni taxmin qilish, SQL | RLS + kodda `org_id` filtri; ilova imtiyozsiz rol; kompozit FK; ORM/parametrlangan SQL | — |
| T7 | I — ochiq sahifa orqali shaxsiy ma'lumot | QR token | 128 bit token, qurilma imzosidan (oldindan bilinmaydi, boshqa tashkilot band qila olmaydi); sahifada faqat imzolovchi F.I.Sh. va tashkilot; `noindex`, `no-store` | PDF (QR egasi uchun hujjatning o'zi) manzil va ismlarni o'z ichiga oladi — qabul qilingan |
| T8 | I — qurilmadagi ma'lumot sizishi | zaxira nusxa, ekranshot, log | `allowBackup=false` + `dataExtractionRules`; FLAG_SECURE imzolash ekranida; logda sir yo'q | SQLite shifrlanmagan (Android FBE ga tayanadi) — M-xavf, reestrda |
| T9 | I — tarmoqda tinglash | ochiq Wi-Fi | faqat HTTPS (ilova URL tekshiruvi + `cleartextTrafficPermitted=false`, faqat tizim CA); serverda HSTS — Caddy (ADR-0015) | sertifikat pinning yo'q (L2) |
| T10 | D — serverni band qilish | ko'p so'rov, katta paket | rate limiting, 5 MB chegara, push ≤ 500 op, pull sahifalari | bitta jarayon xotirasidagi cheklovlar (ko'p nusxada Redis) |
| T11 | E — rolni oshirish | ENGINEER sozlama/tasdiq yuboradi, rejani o'zi "tasdiqlaydi" | API rol talablari (matritsa testi), sync jadval/hodisa rollari, rol bazadan har so'rovda; reja tasdig'i — LEAD/ADMIN ning aynan shu qadamlarga imzolangan hodisasi, holat o'tishlari va mazmun serverda qulflangan | — |
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
| MASVS-CODE-1 yangilangan platforma | ✅ | Flutter stable, `minSdk 24`, `targetSdk 36` (AAB tekshiruvi `verify_aab.sh`) |
| MASVS-CODE-2 yangilanish mexanizmi | ⚠️ | Play orqali; majburiy yangilash yo'q (R-06) |
| MASVS-CODE-3 zaif bog'liqliklar yo'q | ✅ | `tools/audit/osv_audit.py` (OSV.dev) — CI'da har push va haftalik; 2026-10-27: 379 paket, zaiflik yo'q |
| MASVS-CODE-4 kiritishni tekshirish | ✅ | raqamlar qat'iy tahlil, normalar qat'iy YAML yuklovchi, server Pydantic `extra=forbid`, sim formati turlari |
| MASVS-RESILIENCE-* | ➖ | L2/R; baribir: R8 + Dart obfuskatsiyasi, `libapp.so` da DWARF yo'q, `debuggable` yo'q — har AAB'da tekshiriladi (ADR-0016) |
| MASVS-PRIVACY-1..4 | ✅ | minimal ma'lumot (F.I.Sh., telefon); tashqi analitika/xato xizmatlari yo'q; ma'lumot lokalizatsiyasi — DEPLOY.md (huquqshunos) |

## Deploy (11-faza, ADR-0015)

- Tashqariga faqat Caddy (80 → 443, HSTS); `api` va baza — ichki Docker tarmoqlarida, baza tarmog'i internetsiz.
- Konteynerlar: root emas (`api` uid 10001), faqat o'qiladigan FS, `cap_drop: ALL`, `no-new-privileges`; image'lar digest bilan.
- Baza rollari: superuser faqat lokal socket; migratsiya — `zanjir_owner`; ilova — `zanjir_api` (faqat `zanjir_app`, RLS).
- Maxfiy qiymatlar — `deploy/environments/<muhit>.env` (0600, `.gitignore`); zaxira — `age` bilan shifrlangan, ochish
  kaliti serverda yo'q. Kirish logi Caddy'da o'chiq (QR token URL'da).

## To'liq oflayn ilova (13-faza, ADR-0017)

Server yo'q: yuqoridagi T1, T4 (server qismi), T6 (RLS), T7, T9, T10 va "Deploy" bo'limi tarixiy; ishonch chegaralari —
qurilma ↔ qurilma egasi va **fayllar** (zaxira, almashish, taklif). Almashish faylidagi har bir qator importda serverdagi
push tekshiruvlari bilan tekshiriladi; hujumchi modeli — **laboratoriya kalitiga ega insayder** (o'z qurilma kaliti bilan
faylni qayta imzolay oladi), testlar shu model bo'yicha (`zanjir_data/test/exchange*_test.dart`).

| # | Tahdid | Himoya | Qoldiq xavf |
|---|---|---|---|
| T13 | I — zaxira fayli begona qo'lga tushdi | Argon2id (64 MiB, t=3) + ChaCha20-Poly1305; parol ≥ 10 belgi, hech qayerda saqlanmaydi; sarlavhada shaxsiy ma'lumot yo'q | kuchsiz parolni oflayn tanlash (Argon2id sekinlashtiradi); parol siyosati — tashkilotda |
| T14 | T — zaxirani o'zgartirib tiklatish (soxta o'lchov/protokol) | AEAD (sarlavha ham AAD da); tiklashda yaxlitlik va **barcha** audit zanjirlari tekshiriladi; tiklash faqat bo'sh ilovaga | parol egasi o'z bazasini o'zgartirib, zanjirni qayta imzolay olmaydi (eski qurilma kaliti zaxirada yo'q) |
| T15 | D — zararli fayl telefon xotirasini to'ldiradi | KDF parametrlari chegaralangan (≤ 256 MiB, t ≤ 10, p ≤ 4); sarlavha ≤ 4 KiB; parolsiz faqat sarlavha o'qiladi | katta (lekin to'g'ri) zaxira — telefon xotirasiga sig'ishi kerak |
| T16 | S — tiklangan telefon eski qurilma nomidan yozadi | qurilma maxfiy kaliti zaxirada **yo'q**; tiklash — yangi qurilma + `BACKUP_RESTORED`; boshqa telefonlar uni faqat LEAD/ADMIN `DEVICE_APPROVED` bilan qabul qiladi | — |
| T17 | S/E — insayder boshqa xodim (masalan, LEAD) nomidan qurilma qo'shadi yoki o'z rolini oshiradi | yangi qurilma — faqat LEAD/ADMIN taklifi (`INVITE_CREATED` → `DEVICE_REGISTERED`, bir martalik, 7 kun) yoki `DEVICE_APPROVED`; foydalanuvchi o'zgarishi — LEAD/ADMIN `USER_SAVED` bilan; muharrir hodisalari faqat LEAD/ADMIN dan | taklif fayli va parol birga sizsa — begona qurilma qo'shiladi (parol yuzma-yuz, fayl alohida) |
| T18 | T — almashish faylida o'lchov/protokol/rejani o'zgartirish | muallifi qayd etilmaydigan LWW o'zgarishlari (obyekt, sxema, asbob, sessiya, reja) faqat ENGINEER+ va bekor qilinmagan yuboruvchidan; imzolangan audit hodisasi payload'i bilan bog'lash, append-only (bor qator aynan bir xil), zanjir, protokol hujjati/imzo/QR/o'lchovlar, reja holat o'tishlari va tasdiq; hammasi yoki hech narsa | — |
| T19 | S — yo'qolgan/o'g'irlangan telefon yozishda davom etadi | `DEVICE_REVOKED` (LEAD/ADMIN, `last_seq`) — undan keyingi hodisalar hech bir telefonda qabul qilinmaydi; bekor qilish fayl bilan tarqaladi | bekor qilish yetib kelguncha boshqa telefon o'sha fayllarni qabul qilishi mumkin; bekor qilingan telefonda laboratoriya kaliti qoladi (R-12) |
| T20 | D — katta yoki buzilgan almashish fayli | AEAD, sarlavha ≤ 4 KiB, qat'iy sim formati (ustunlar, turlar), soat siljishi ≤ 10 daq | to'liq surat — fayl hajmi laboratoriya bilan o'sadi (R-13) |

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
| F-09 | Y | ENGINEER sinxronlash orqali rejani "tasdiqlay" olardi (`approved_by` ga LEAD ID sini yozib), tasdiqlangan rejaning qadamlarini almashtira yoki bekor qilinganini qayta tiriltira olardi — xavfli ish ruxsatiga ta'sir qiladi | ✅ tuzatildi: holat o'tishlari, imzolangan `PLAN_APPROVED` (`actor_id = approved_by`, qadamlar hash'i), EXECUTED — barcha qadamlar bilan, mazmun qulflangan; testlar `test_plan_*` |
| F-10 | O | Protokolni server qayta tekshirishini o'lchovni payload'dan tushirib qoldirib (masalan, NEEDS_REVIEW) yoki asbob/litsenziya/norma ma'lumotini payload'da "to'g'rilab" chetlab o'tish mumkin edi | ✅ tuzatildi: payload o'lchovlari = sessiyaning amaldagi o'lchovlari (ID, natija, qiymat, asbob, vaqt); qoida kirishlari bazadan; `signed_at` oynasi |
| F-11 | O | QR token mijoz tanlaydi va global yagona — chop etilgan QR'ni ko'rgan boshqa tashkilot uni oldinroq band qilib, haqiqiy protokolni bloklashi va ochiq sahifada o'z hujjatini ko'rsatishi mumkin edi; raqamni ham band qilish mumkin edi | ✅ tuzatildi: `qr_token = sha256(Ed25519(org, raqam))[:32]`, imzo qurilma kaliti bilan tekshiriladi; raqam qurilma belgisi bilan (belgi 6 hex — to'qnashuv uchun ~16 mln qurilma ro'yxatdan o'tkazish kerak, R-10) |
| F-12 | O | Doimiy rad etish qurilmani to'liq to'xtatardi (pull ham); `clock_skew` imzolangan append-only yozuvga ham qo'llanib, uni abadiy rad etardi | ✅ tuzatildi: `clock_skew` faqat LWW jadvallariga; rad etilsa ham pull; qotgan yozuv (jadval, ID, sabab) UI'da |
| F-13 | P | `PROTOCOL_SIGNED` hodisasi imzolovchi va qurilmaga bog'lanmagan edi | ✅ tuzatildi: hodisa `actor_id = signed_by`, `device_id` mos |
| F-14 | P | Parallel so'rovlarda ikki marta refresh — server reuse detection'i sessiyani yopib, foydalanuvchini chiqarib yuborardi | ✅ tuzatildi: bitta oqimli refresh, token allaqachon yangilangan bo'lsa refresh'siz; test `server_api_test` |
| F-15 | P | `Content-Disposition` (PDF fayl nomi) tekshirilmagan `number` dan | ✅ tuzatildi: raqam push'da `^[0-9]{4}-[0-9A-F]{6}-[0-9]{3,9}$` (faqat ASCII) |
| F-16 | P | NaN/Infinity yoki 2^53 dan katta son JSON ustunda — 500 xato | ✅ tuzatildi: sim formatida kanonik JSON tekshiruvi, payload'da `parse_constant` — aniq rad etish |
| F-17 | P | Hisob bo'yicha kirish cheklovi tekshiruvning o'zida yozuv yaratardi va tozalash zaif edi (xotira o'sishi); cheklov orqali begona hisobni vaqtincha bloklash (lockout DoS) | ✅ xotira qismi tuzatildi; lockout DoS — R-08 |
| F-18 | P | Telefon raqami o'chirilgan foydalanuvchilar bilan birga global yagona — o'chirilgan xodim raqamini qayta ishlatib bo'lmaydi | ⏳ R-09 (11-faza, OTP bilan birga) |
| F-19 | P | Laboratoriya rekvizitlari va sozlamalari o'zgarishi audit hodisasini talab qilmasdi | ✅ tuzatildi: imzolangan `LAB_UPDATED` / `SETTINGS_CHANGED` hodisasi (payload hash) talab qilinadi |

| F-20 | Y | 6-qoida: protokol asbob guvohnomasini *hozirgi* muddat bo'yicha tekshirardi — muddati o'tgan asbob bilan olingan o'lchov asbob keyin qayta qiyoslangach imzolanib ketardi | ✅ tuzatildi: o'lchov paytidagi muddat `eval_detail.instrument_verified_until` ga yoziladi; ilova va server ikkalasini ham tekshiradi |
| F-21 | O | `registerLab` o'rtada uzilsa (ro'yxatdan o'tdi, qurilma/push yo'q) — qayta urinish 409, kirish qurilmani ro'yxatdan o'tkazmasdi: laboratoriya umuman sinxronlanmasdi | ✅ tuzatildi: 409 da shu profil bilan kirish, qurilma har doim tekshiriladi (kirishda ham); E2E testi |
| F-22 | O | LWW'da yutqazgan qurilma (soati orqada) o'z qiymatida qolib ketardi — server qatori qayta yuborilmasdi | ✅ tuzatildi: mazmuni farq qiladigan `stale` push'da server qatori qayta yuboriladi (`server_rev`) |
| F-23 | P | Kirish cheklovi va rate limiter 100k kalitdan keyin har so'rovda butun lug'atni aylanardi (CPU) | ✅ tuzatildi: tozalash daqiqasiga/oynaga bir marta |
| F-24 | P | Server protokol qoidasi litsenziya raqami yo'qligini tekshirmasdi (ilova tekshiradi) | ✅ tuzatildi: `license_no` bazadan, bo'sh bo'lsa `license_invalid` |
| F-25 | O | Laboratoriyani LEAD yaratsa, tashkilotda ADMIN bo'lmaydi (LEAD ADMIN taklif qila olmaydi) — qurilmani bekor qilish, rol o'zgartirish, xodimni o'chirish faqat ADMIN'da; ilovada qurilmani bekor qilish ekrani yo'q | ⏳ foydalanuvchi qarori (LEAD'ga qurilma bekor qilishni berish yoki yaratuvchini doim ADMIN qilish); hozircha operator yo'li — RUNBOOK |
| F-26 | O | Bir sessiyaga ikki oflayn qurilma ikkita amaldagi protokol imzolay oladi (ilova `already_signed` ni faqat lokal tekshiradi) | ⏳ foydalanuvchi qarori: rad etish qurilmani to'xtatadi (imzolangan hujjat allaqachon chop etilgan) — tavsiya: qabul qilish va `/v/` sahifasida "sessiyada boshqa protokol bor" ogohlantirishi |

Ko'rik uch bosqichda: F-01…F-08 — o'z ko'rigim, F-09…F-19 — mustaqil ko'rik (alohida agent, koddan; ADR-0014),
F-20…F-26 — PR'dagi code review (JurabekM/Myrep#33).
Tasdiqlangan to'g'ri qismlar: tashkilotlar ajratilishi (RLS), append-only, `server_rev`, audit zanjiri, push atomarligi,
taklif kodlari, refresh rotatsiyasi, JWT, ochiq sahifa, loglar, ilova xotirasi, HTTPS, zaxira.

**Qabul qilingan qoldiq xavflar (R):**
- R-01 (O) Sertifikat pinning yo'q — L2; domen va sertifikat siyosati 11-fazada ko'rib chiqiladi.
- R-02 (O) Rate limiting va hisob cheklovi bitta jarayon xotirasida — `api` bitta jarayon (ADR-0015); ko'p nusxada Redis.
- R-03 (O) Lokal SQLite shifrlanmagan — Android FBE (qurilma qulflangan bo'lsa shifrlangan), zaxira o'chirilgan; SQLCipher —
  pilotdan keyin baholanadi (unumdorlik va kalit tiklash).
- R-04 (P) JWT HS256 bitta kalit, rotatsiya qo'lda — `RUNBOOK.md` "Kalitlar va kirish" (yiliga yoki sizishda).
- R-05 (P) Ilovaga kirishda lokal PIN/biometrik yo'q — qurilma qulfi tashkilot siyosati.
- R-06 (P) Majburiy yangilash yo'q — Play in-app update keyingi bosqichda.
- R-07 (P) Ochiq PDF QR egasiga hujjatdagi shaxsiy ma'lumotni ko'rsatadi — protokolning maqsadi (buyurtmachiga beriladi).
- R-08 (P) Hisob cheklovi (10 xato / 15 daq) begona hisobni vaqtincha bloklash uchun ishlatilishi mumkin — oyna qisqa,
  IP cheklovi ham bor; SMS OTP/CAPTCHA 11-fazada ko'rib chiqiladi.
- R-09 (P) O'chirilgan foydalanuvchining telefoni qayta ishlatilmaydi (F-18) — qisman yagona indeks va migratsiya OTP bilan
  birga (11-faza); hozircha administrator yangi raqam bilan qo'shadi.
- R-10 (P) Protokol raqamidagi qurilma belgisi 6 hex — shu tashkilotdagi ENGINEER ~16 mln qurilma ro'yxatdan o'tkazib
  boshqa qurilma raqamini band qilishi nazariy jihatdan mumkin (rate limiting bilan amalda yo'q).
- R-12 (O) Bekor qilingan telefonda laboratoriya kaliti qoladi — u keyingi almashish fayllarini o'qiy oladi (yoza olmaydi).
  Kalitni almashtirish (yangi kalitni taklif kabi tarqatish) — keyingi bosqich; hozircha yo'qolgan telefonda Android qulfi.
- R-13 (P) Almashish fayli — to'liq surat (PDF'lar bilan): katta laboratoriyada fayl o'sadi; "faqat yangilari" rejimi keyin.
- R-14 (P) Muharrir roli importda **hozirgi** rol bo'yicha tekshiriladi — rol pasaytirilgandan keyin yetib kelgan eski
  muharrir hodisalari rad etiladi (yo'riqnoma: avval almashish, keyin rolni o'zgartirish).
- R-15 (Y) Normalar litsenziyali muhandis tomonidan tekshirilmagan holda protokol imzolanadi (ADR-0019, foydalanuvchi qarori):
  normada xato bo'lsa, noto'g'ri PASS rasmiy hujjatga tushishi mumkin. Yumshatish: chegaralar AI ko'rigi va IEC/ПУЭ bilan
  solishtirilgan, shubhali joylarda qat'iyroq qiymat (K1 → 1,0 MΩ), ma'lumot yetishmasa NEEDS_REVIEW; PDF va ilova
  "muhandis tekshiruvidan o'tmagan" deb ochiq ko'rsatadi; `reviewed_by` soxta to'ldirilmaydi.
- R-11 (O) Asbob guvohnomasi muddati (`verified_until`) — oddiy LWW metadata: ENGINEER uni audit hodisasisiz o'zgartira
  oladi. O'lchov paytidagi muddat qayd etiladi (F-20), lekin noto'g'ri muddat kiritishni texnik yo'l bilan to'xtatib
  bo'lmaydi — guvohnoma raqami protokolda ko'rinadi; `INSTRUMENT_VERIFIED` audit hodisasi — keyingi bosqichda.
