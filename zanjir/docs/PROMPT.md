# ZANJIR — Production'gacha bitta umumiy prompt (Claude Code uchun)

> Bu promptni yangi, bo'sh repozitoriyda Claude Code'ga to'liq holda bering.
> Agar `docs/SPEC.md` (texnik spetsifikatsiya) mavjud bo'lsa, uni ham repozitoriyga qo'ying.
> Bu prompt usiz ham ishlay oladigan qilib, barcha asosiy talablar ichiga kiritilgan.

---

## 0. Sen kimsan va vazifa nima

Sen Senior Flutter/Dart, Python/FastAPI, DevOps va xavfsizlik muhandisisan. Elektr qurilmalari sohasini (ПУЭ, ПТЭЭП, naryad-dopusk, 5 ta texnik tadbir) yaxshi tushunasan.

**Vazifa:** ZANJIR ilovasini noldan **production'gacha** olib chiqish. ZANJIR — elektrolaboratoriyalar va elektriklar uchun offline-first mobil ilova. U quyidagilarni qiladi:

1. Obyektning elektr grafini yuritadi: manbalar, shitlar, avtomatlar, UZO, kabellar, iste'molchilar.
2. Dalada o'lchovlarni internetsiz kiritadi: izolyatsiya qarshiligi, "faza-nol" sirtmog'i, UZO, yerga ulash qarshiligi, metallik bog'lanish.
3. O'lchovlarni normaga avtomatik solishtiradi (PASS / FAIL / NEEDS_REVIEW / NOT_APPLICABLE).
4. Imzolangan, o'zgartirib bo'lmaydigan PDF protokol va QR orqali tekshiriladigan sahifa yaratadi.
5. Grafdan foydalanib ajratish rejasini (5 ta texnik tadbir) tavsiya qiladi. Teskari ta'minot manbalari (PV inverter, generator, UPS, AVR) ham hisobga olinadi.

**Ish rejimi:** fazalar bo'yicha **mustaqil** ishlaysan va har faza tugagach keyingisiga o'tasan. Faqat `🛑 INSON DARVOZASI` belgisi bor joyda to'xtab, mendan aniq narsani so'raysan. Noaniqlik bo'lsa ham to'xtaysan: elektr xavfsizligi bo'yicha hech qachon taxmin qilma.

---

## 1. Til va hujjatlash qoidalari

- Kod izohlari, commit xabarlari, README, `docs/*` va menga yozadigan barcha hisobotlaring **o'zbek tilida (lotin)** bo'ladi.
- Kod, identifikatorlar, buyruqlar va log kalitlari ingliz tilida qoladi.
- Ilova interfeysi ikki tilli: `uz` (lotin, standart) va `ru`. Flutter `gen-l10n` va ARB fayllaridan foydalan, UI'da qattiq yozilgan matn bo'lmasin.

## 2. Doimiy kontekst (sessiyalar uzilsa ham davom etish uchun)

Birinchi ish sifatida quyidagi fayllarni yarat va **har faza oxirida yangilab bor**:

- `CLAUDE.md`: loyiha qisqacha tavsifi, stek, buyruqlar (test, build, run), o'zgarmas qoidalar (6-bo'lim). Keyingi sessiyalarda sen avval shu faylni o'qiysan.
- `docs/PROGRESS.md`: fazalar jadvali (holat, sana, commit), joriy faza, ochiq savollar, inson darvozalari holati.
- `docs/DECISIONS.md`: muhim arxitektura qarorlari ADR formatida (kontekst, qaror, oqibat).
- `CHANGELOG.md`: semver bo'yicha.

Sessiya yangidan boshlansa: `CLAUDE.md` → `docs/PROGRESS.md` ni o'qi va joriy fazadan davom et.

---

## 3. Stek (o'zgartirma; o'zgartirish kerak bo'lsa, ADR yoz va mendan so'ra)

| Qatlam | Tanlov |
|---|---|
| Mobil | Flutter 3 (stable), Dart 3, Riverpod, go_router |
| Lokal baza | Drift (SQLite), versiyalangan migratsiyalar |
| Yadro mantiq | `packages/zanjir_core`: sof Dart, Flutter'ga bog'liq emas |
| PDF / QR | `pdf`, `printing`, `qr_flutter` |
| Kriptografiya | `cryptography` (SHA-256, Ed25519), `flutter_secure_storage` (Android Keystore) |
| Server | Python 3.12, FastAPI, SQLAlchemy 2 (async), Alembic, Pydantic v2 |
| Server bazasi | PostgreSQL 16, Row-Level Security |
| Testlar | `dart test`, `flutter test`, `integration_test`, pytest, testcontainers-python |
| Infra | Docker, docker compose, Caddy (avtomatik HTTPS), GitHub Actions |
| Normalar | `norms/*.yaml` + `norms/schema.json` |

**Repozitoriy tuzilishi:**

```
app/                     # Flutter ilova
packages/zanjir_core/    # graf, baholash, solver, kanonik JSON, hash-zanjir
server/                  # FastAPI
norms/                   # normalar YAML + JSON Schema
tools/vectors/           # Dart va Python uchun umumiy kripto test vektorlari
deploy/                  # Dockerfile, compose, Caddyfile, backup skriptlari
docs/                    # SPEC, PROGRESS, DECISIONS, DEPLOY, RUNBOOK, SECURITY, NORMS_REVIEW
```

---

## 4. Ma'lumotlar modeli

Barcha jadvallarda: `id` (UUIDv7), `org_id` (`organization` dan tashqari), `created_at`, `updated_at`, `rev` (sinxronlash uchun), `deleted` (soft delete; append-only jadvallarda yo'q).

| Jadval | Asosiy maydonlar |
|---|---|
| `organization` | `name`, `license_no`, `license_valid_until` |
| `app_user` | `full_name`, `phone`, `password_hash` (argon2id), `role` (ADMIN, LEAD, ENGINEER, VIEWER), `safety_group` (I–V) |
| `device` | `user_id`, `public_key_ed25519`, `sig_alg`, `registered_at`, `revoked_at` |
| `instrument` | `kind`, `model`, `serial_no`, `verification_cert_no`, `verified_until` |
| `site` | `name`, `address`, `customer`, `earthing_system` (TN-C, TN-S, TN-C-S, TT, IT), `u0_volts` |
| `node` | `site_id`, `kind`, `label`, `panel_id`, `state` (CLOSED/OPEN, faqat kommutatsiya apparatlarida), `attrs` JSON, `verified` bool, `x`, `y` |
| `edge` | `site_id`, `a_node_id`, `b_node_id`, `conductors` (masalan, "L1 L2 L3 N PE") |
| `measurement_session` | `site_id`, `kind` (QABUL_TOPSHIRISH, DAVRIY, NAVBATDAN_TASHQARI), `engineer_id`, `ambient_temp_c`, `humidity_pct`, `started_at`, `closed_at` |
| `measurement` (**append-only**) | `session_id`, `node_id`, `type`, `instrument_id`, `values` JSON, `entered_via` (MANUAL/OCR/BT), `verdict`, `norm_id`, `norm_set_version`, `eval_detail` JSON, `supersedes_id` |
| `protocol` (**append-only**, holat hodisa orqali o'zgaradi) | `session_id`, `number`, `payload_sha256`, `pdf_sha256`, `signed_by`, `device_id`, `signature`, `sig_alg`, `qr_token` |
| `audit_event` (**append-only**) | `device_id`, `seq`, `prev_hash`, `event_hash`, `actor_id`, `event_type`, `entity_id`, `payload_hash`, `device_sig`, `created_at` |
| `isolation_plan` | `site_id`, `target_node_ids`, `solver_version`, `graph_snapshot_hash`, `steps` JSON, `warnings` JSON, `status` (DRAFT/APPROVED/EXECUTED/CANCELLED/STALE), `approved_by` |
| `norm_set` | `version`, `sha256`, `yaml`, `reviewed_by`, `reviewed_at` |

**`node.kind` qiymatlari:**

- Manbalar: `SRC_GRID`, `SRC_TRANSFORMER`, `SRC_GENERATOR`, `SRC_PV_INVERTER`, `SRC_UPS`, `SRC_BATTERY`, `SRC_CAPACITOR`
- Kommutatsiya apparatlari: `BREAKER`, `RCD`, `RCBO`, `FUSE`, `SWITCH`, `ATS`, `CONTACTOR`
- Qolganlari: `BUSBAR`, `PANEL`, `CABLE`, `LOAD`, `SOCKET_GROUP`, `EARTH_ELECTRODE`, `PE_BAR`

**`node.attrs` misollari:**

- Avtomat: `{"in_a":16,"curve":"C","icu_ka":6}`
- UZO: `{"in_a":40,"idn_ma":30,"rcd_type":"A","selective":false}`
- Kabel: `{"cores":3,"csa_mm2":2.5,"material":"Cu","length_m":22}`
- PV inverter: `{"anti_islanding":true}`

**`measurement.values` tuzilishi:**

```json
{
  "INSULATION":         {"test_voltage_v":1000,"pairs":[{"pair":"L1-PE","mohm":120.0}]},
  "LOOP_IMPEDANCE":     {"pair":"L1-PE","zs_ohm":0.84},
  "RCD_TRIP":           {"multiplier":1.0,"trip_time_ms":24,"trip_current_ma":21,"tripped":true},
  "EARTH_RESISTANCE":   {"r_ohm":3.1,"method":"3-wire","season_coeff":1.0},
  "CONTINUITY_BONDING": {"r_ohm":0.03,"from":"PE shina SHR-1","to":"Quvur korpusi"}
}
```

Xato o'lchov o'chirilmaydi: uning o'rniga `supersedes_id` bilan yangi yozuv qo'shiladi.

---

## 5. Domen mantig'i (`zanjir_core`)

### 5.1 Normalar (`norms/v0.yaml`)

Har bir normada quyidagi maydonlar bo'ladi: `id`, `measurement_type`, `applies_to` (node_kinds, earthing_systems, u0 diapazoni), `test_voltage_v` (agar kerak bo'lsa), `rule` (`min` / `max` / `range` / `max_time_ms`), `unit`, `source` (hujjat va band), `status` (`source_seen` | `needs_verification`).

Boshlang'ich to'plam (barcha qiymatlar faqat YAML'da saqlanadi, kodda bo'lmaydi):

| ID | Norma | Manba | status |
|---|---|---|---|
| INS-WIRING | Elektr simlari izolyatsiyasi ≤1 kV, megaommetr 1000 V: ≥ 0,5 MΩ | ПУЭ 1.8.37, jadval 1.8.34 | source_seen |
| INS-SWGR | Shitlar va taqsimlash qurilmalari, 1000–2500 V: ≥ 0,5 MΩ (har seksiya) | ПУЭ jadval 1.8.34 | needs_verification |
| INS-SECONDARY | Ikkilamchi zanjirlar: ≥ 1 MΩ | ПУЭ jadval 1.8.34 | needs_verification |
| INS-CABLE-LV | Kuch kabellari ≤1 kV, 2500 V: ≥ 0,5 MΩ | ПУЭ 1.8.40 | needs_verification |
| LOOP-TN-FINAL | TN, oxirgi zanjirlar, U0 = 220 V: t ≤ 0,4 s | ПУЭ 1.7.79, jadval 1.7.1 | source_seen |
| LOOP-TN-DIST | TN, taqsimlovchi zanjirlar: t ≤ 5 s | ПУЭ 1.7.79 | source_seen |
| LOOP-TN-OTHER-U0 | U0 = 127 / 380 / >380 V: 0,8 / 0,2 / 0,1 s | ПУЭ jadval 1.7.1 | needs_verification |
| RCD-1X | Umumiy turdagi UZO, IΔn da: ≤ 300 ms | ГОСТ IEC 61008-1 | needs_verification |
| RCD-1X-S | Selektiv UZO, IΔn da: 130–500 ms | ГОСТ IEC 61008-1 | needs_verification |
| RCD-5X | Umumiy turdagi UZO, 5·IΔn da: ≤ 40 ms | ГОСТ IEC 61008-1 | needs_verification |
| RCD-RAMP | Differensial o'chish toki: 0,5·IΔn < I ≤ IΔn | ГОСТ IEC 61008-1 | needs_verification |
| EARTH-NEUTRAL-380 | Neytral yerga ulash qurilmasi, 380/220 V: ≤ 4 Ω | ПУЭ 1.7.101 | needs_verification |
| EARTH-REPEAT-380 | Takroriy yerga ulash: jami ≤ 10 Ω, har biri ≤ 30 Ω | ПУЭ 1.7.103 | needs_verification |
| EARTH-TT | TT tizimi: Ra·Ia ≤ 50 V | ПУЭ 1.7.59 | needs_verification |
| BOND-CONTACT | Ulanish qarshiligi: ≤ 0,05 Ω | ПТЭЭП, 3-ilova, 26-band | source_seen |

Yuqori darajadagi `reviewed_by` va `reviewed_at` maydonlari bo'sh bo'lsa, CI release build'ni **yiqitadi**.

### 5.2 Baholash: `evaluate(measurement, node, site, session, normSet) → Verdict`

- Sof funksiya, deterministik. `eval_detail` ichiga quyidagilar yoziladi: hisoblangan chegara, formula, kirish qiymatlari, norma ID va `norm_set_version`.
- **Ma'lumot yetishmasa natija NEEDS_REVIEW bo'ladi, hech qachon PASS emas.**
- Bir nechta norma mos kelsa, eng qat'iysi qo'llanadi va bu `eval_detail` da qayd etiladi.
- **Izolyatsiya:** har bir juftlik ≥ min bo'lishi kerak. Asbob kuchlanishi normadagidan past bo'lsa yoki sessiya harorati kiritilmagan bo'lsa → NEEDS_REVIEW.
- **Sirtmoq:** graf orqali tugundan manbaga tomon eng yaqin himoya apparati topiladi. Ia: B = 5·In, C = 10·In, D = 20·In. Chegara: `Zs_max = k_corr · U0 / Ia` (`k_corr` laboratoriya sozlamasi, standart 1,0).
  - Zs > Zs_max bo'lsa-yu, yuqorida UZO bo'lsa → NEEDS_REVIEW.
  - `FUSE` bo'lsa yoki himoya apparati topilmasa → NEEDS_REVIEW.
- **UZO:** `multiplier` bo'yicha norma tanlanadi; `selective = true` bo'lsa S-normalar ishlatiladi. `tripped = false` → FAIL.
- **Yerga ulash:** `r_ohm × season_coeff` normadagi maksimum bilan solishtiriladi. Koeffitsient kiritilmasa → NEEDS_REVIEW.
- **Metallik bog'lanish:** `r_ohm ≤ max`.
- Qat'iy bo'lmagan tengsizlikda aynan chegaradagi qiymat PASS hisoblanadi. `margin_pct` parametri `norm_set` darajasida sozlanadi (standart 0).

### 5.3 Ajratish solveri: `planIsolation(graph, zone) → Plan | Blocked`

1. **Konservativ faraz:** apparatlarning joriy `state` holati e'tiborga olinmaydi. Barcha qirralar o'tkazuvchan deb qaraladi.
2. S = barcha `SRC_*` tugunlar. Har biridan Z gacha BFS o'tkaziladi; yetib boradiganlar S_r to'plamini tashkil qiladi.
3. **Kesish narxlari:** `SWITCH` = 1, `FUSE` = 2, `BREAKER`/`RCBO` = 3, `RCD` = 5, `CONTACTOR`/`ATS` = 50 (bu holda ogohlantirish chiqadi). Boshqa tugunlar va Z ichidagi tugunlar = ∞.
4. Har bir tugun `v_in → v_out` ga bo'linadi; super-manba S_r ga, Z esa super-oqimga ulanadi. Edmonds–Karp bilan maksimal oqim hisoblanib, minimal kesim C topiladi. Narxi teng kesimlar orasida ish zonasiga yaqinrog'i tanlanadi.
5. Oqim = ∞ bo'lsa → **Blocked**, kommutatsiya apparati bo'lmagan yo'lning o'zi ko'rsatiladi.
6. **Mustaqil tekshiruv:** C ni grafdan olib tashlab, BFS qayta ishga tushiriladi. Yo'l topilsa → Blocked va xato logga yoziladi.
7. **Qadamlar tartibi:**
   1. Teskari manbalarni to'xtatish (PV: avval AC, keyin DC ajratgich; generator; UPS).
   2. C dagi apparatlarni o'chirish.
   3. Blokirovka va "Yoqilmasin! Odamlar ishlamoqda" plakati.
   4. Z ning har bir kirish nuqtasida kuchlanish yo'qligini tekshirish. Bu qadam **majburiy, o'tkazib yuborilmaydi**; ko'rsatkichni oldin kuchlanish borligi ma'lum joyda sinash talab qilinadi.
   5. Kuchlanish kelishi mumkin bo'lgan har bir tomonda yerga ulagich o'rnatish.
   6. To'siq va "Shu yerda ishlang" plakati.
8. **Ogohlantirishlar:** `verified = false` tugunlar, Z ichidagi kondensator yoki uzun kabel (zaryadsizlantirish), PV'ning DC tomoni, TN-C dagi PEN, kesimdagi CONTACTOR/ATS.
9. `graph_snapshot_hash` = kanonik grafning SHA-256 hash'i. Graf o'zgarsa, reja STALE holatiga o'tadi.
10. **Unumdorlik:** 2000 tugunli graf o'rta darajadagi Android qurilmada < 500 ms.

### 5.4 Kanonik JSON, hash-zanjir va imzo

- **Kanonik JSON:** kalitlar saralangan, bo'sh joy yo'q, sonlar qat'iy formatda, vaqt UTC ISO-8601 da, UTF-8. Dart va Python bir xil `tools/vectors/*.json` vektorlaridan o'tishi shart.
- `event_hash = SHA256(canonical({seq, prev_hash, actor_id, event_type, entity_id, payload_hash, created_at}))`
- `device_sig = Ed25519(event_hash)`. Zanjir har bir qurilma uchun alohida yuritiladi.
- **Protokol imzosi:** `payload` (sessiya, o'lchovlar, verdiktlar, `norm_set_version`, asbob guvohnomalari) → `payload_sha256`. Deterministik PDF → `pdf_sha256`. `signature = Ed25519(payload_sha256 ‖ pdf_sha256)`.
- Har bir yozuvda `sig_alg` maydoni bor: kelajakda ML-DSA gibrid imzo yoki E-IMZO'ga o'tish sxemani buzmaydi.
- Bekor qilish faqat `PROTOCOL_REVOKED` hodisasi orqali amalga oshadi; hech narsa o'chirilmaydi.

---

## 6. O'zgarmas qoidalar (hech qachon buzilmaydi)

1. Ilova hech qachon "ishlash xavfsiz" degan matn chiqarmaydi. U faqat **tavsiya** beradi, javobgarlik naryad beruvchi va ish rahbari zimmasida qoladi. Bu matn UI'da va PDF'da ko'rinadi.
2. "Kuchlanish yo'qligini tekshirish" qadamini o'tkazib yuborib ham, yashirib ham, avtomatik belgilab ham bo'lmaydi.
3. Ma'lumot yetishmasa natija NEEDS_REVIEW bo'ladi. PASS hech qachon standart qiymat emas.
4. Norma qiymatlari faqat YAML'da saqlanadi; kodda "magic number" bo'lmaydi.
5. `measurement`, `protocol`, `audit_event` jadvallarida UPDATE va DELETE yo'q. Bu serverda DB trigger, ilovada esa repozitoriy darajasida majburlanadi.
6. Qiyoslash muddati o'tgan asbob bilan olingan o'lchov imzolanmaydi. NEEDS_REVIEW qolgan bo'lsa, sessiyani faqat LEAD izoh bilan imzolay oladi.
7. Har bir tashkilot ma'lumoti boshqasidan ajratilgan: `org_id` filtri va Postgres RLS birga ishlaydi.
8. Maxfiy ma'lumot (parol, token, maxfiy kalit, shaxsiy ma'lumot) logga yozilmaydi.
9. `zanjir_core` uchun avval test, keyin kod.
10. Elektr xavfsizligi bo'yicha noaniqlik bo'lsa → to'xta va so'ra.

---

## 7. Server talablari

- **Auth:** telefon raqami + parol (argon2id). Access JWT 15 daqiqa, refresh token rotatsiya va qayta ishlatilishini aniqlash bilan. Foydalanuvchini tashkilotga faqat LEAD/ADMIN yuborgan taklif kodi orqali qo'shish mumkin. Har bir qurilma ochiq kalit bilan ro'yxatdan o'tadi va ADMIN uni bekor qila oladi. SMS OTP adapter interfeysi tayyorlanadi, lekin MVP'da o'chirilgan bo'ladi.
- **RBAC:** ADMIN > LEAD > ENGINEER > VIEWER. Har bir endpoint uchun ruxsatlar matritsasi `docs/SECURITY.md` da yoziladi va testlar bilan qoplanadi.
- **Sinxronlash:**
  - `GET /sync/pull?since=<server_rev>`, `POST /sync/push` (idempotent; `client_op_id` bo'yicha takrorlanish olib tashlanadi).
  - Metadata uchun last-writer-wins; append-only jadvallar faqat qo'shiladi.
  - Audit zanjiri `push` paytida tekshiriladi: `seq`, `prev_hash` va imzo. Xato bo'lsa butun paket rad etiladi.
- **Ochiq tekshirish sahifasi:** `GET /v/{qr_token}`, server tomonda render qilinadi (Jinja2). Sahifada holat, imzolovchi, sana va hash'lar ko'rsatiladi, PDF'ni yuklab hash'ini solishtirish imkoni bor. Shaxsiy ma'lumot minimal (imzolovchining faqat F.I.Sh. va tashkiloti).
- **Himoya:** endpoint bo'yicha rate limiting, CORS faqat kerakli domenlar uchun, so'rov hajmi cheklovi, Pydantic validatsiya, SQL faqat ORM yoki parametrlangan so'rovlar orqali.
- **Kuzatuv:** strukturalangan JSON log, `/healthz` va `/readyz`, Prometheus metrikalari. Xato hisobotlari adapter orqali, standart holatda o'chirilgan.
- **Ma'lumotlarni lokalizatsiya qilish:** O'zbekiston fuqarolarining shaxsiy ma'lumotlari O'zbekiston hududidagi serverlarda saqlanishi talab qilinadi. Deploy shunga mos rejalashtiriladi. Bu talabning joriy holatini `docs/DEPLOY.md` da "huquqshunos bilan tekshirilsin" deb belgilab qo'y.

## 8. Mobil ilova talablari

- To'liq offline ishlash: lokal baza asosiy manba, sinxronlash fonda, tarmoq paydo bo'lganda va qo'lda ishga tushiriladi.
- Bitta o'lchovni kiritish ≤ 10 soniya: raqamli klaviatura, birliklar, rangli natija (yashil/qizil/sariq), "keyingi nuqta"ga avtomatik o'tish, apparatni nusxalash (QF1 → QF2…).
- **Ekranlar:** kirish; obyektlar; obyekt grafi (daraxt va graf rejimi); tugun kartasi (QR orqali ochiladi); sessiya boshlash; o'lchov kiritish; sessiya xulosasi; protokol (PDF, ulashish, QR); ajratish rejasi (qadamlar checklist'i); sozlamalar (laboratoriya, foydalanuvchilar, asboblar, normalar versiyasi, `k_corr`, `margin_pct` — oxirgi ikkitasi faqat LEAD uchun).
- **Dala sharoiti:** tugmalar ≥ 48 dp, tungi rejim, katta shrift rejimi, TalkBack bilan foydalanish mumkin.
- **Mobil xavfsizlik:** OWASP MASVS L1 checklist; maxfiy kalitlar Keystore'da saqlanadi; release'da obfuskatsiya; ekranshotdan himoya faqat imzolash ekranida.

---

## 9. Fazalar (har biri: branch → testlar → PR tavsifi → `docs/PROGRESS.md` yangilash)

Har faza "Tayyor" deb hisoblanishi uchun quyidagilar bajarilishi kerak: barcha testlar o'tadi, `dart analyze` / `ruff` / `mypy` toza, yangi kod uchun testlar yozilgan, hujjatlar yangilangan.

| # | Faza | "Tayyor" mezoni |
|---|---|---|
| 0 | Skelet: monorepo, `CLAUDE.md`, `docs/*`, CI (analyze, test, pytest, norms schema, release gate) | CI yashil, bo'sh testlar ishlaydi |
| 1 | `zanjir_core`: modellar, YAML parser + schema, `evaluate()` | Har normaga ≥ 3 golden test, evaluator'da 100% branch coverage |
| 2 | Solver | 7 ta stsenariy (radial; ikki kirishli AVR; PV teskari ta'minot; UPS aylanma yo'li; ikki fiderli halqa; qo'lda almashtiriladigan generator; apparatsiz yo'l → Blocked), 1000 ta tasodifiy grafda property test, unumdorlik testi |
| 3 | Kanonik JSON + hash-zanjir + imzo (Dart va Python) | Ikki tomon bir xil vektorlardan o'tadi; buzilgan bayt aniqlanadi |
| 4 | Ilova ma'lumot qatlami (Drift, repozitoriylar, migratsiyalar, append-only himoya) | Migratsiya testlari, repozitoriy testlari |
| 5 | Ilova UI (8-bo'lim), l10n uz/ru | Widget testlari; asosiy oqim uchun integration test |
| 6 | Deterministik PDF, QR, imzolash va bloklash shartlari | Bir xil payload → baytma-bayt bir xil PDF; imzolashni bloklash testlari |
| 7 | Server: auth, RBAC, RLS, sync, `/v/{qr_token}` | pytest + testcontainers; RBAC matritsasi to'liq qoplangan |
| 8 | Sinxronlash integratsiyasi | E2E: ikki qurilma offline ishlaydi → sync → o'lchovlar yo'qolmaydi va takrorlanmaydi; zanjir buzilishi rad etiladi |
| 9 | Ajratish rejasi UI, tasdiqlash oqimi, STALE holati | Integration test; majburiy qadamni o'tkazib bo'lmasligi testlangan |
| 10 | Mustahkamlash: xavfsizlik ko'rigi (`docs/SECURITY.md`: tahdid modeli, MASVS checklist, RBAC matritsasi), bog'liqliklar auditi, unumdorlik, accessibility | Topilgan barcha "yuqori" darajadagi muammolar yopilgan |
| 11 | Deploy: Dockerfile'lar, compose (staging + prod profillari), Caddy, Alembic migratsiyalari deploy'da, shifrlangan kunlik `pg_dump` + tiklash skripti, `docs/DEPLOY.md`, `docs/RUNBOOK.md` | Staging'da bitta buyruq bilan ko'tariladi; zaxiradan tiklash sinovdan o'tgan |
| 12 | Release: Android imzolash konfiguratsiyasi, AAB build, versiyalash, Play internal testing tayyorgarligi, pilot uchun yo'riqnoma | `flutter build appbundle --release` muvaffaqiyatli; release checklist to'liq |

### 🛑 INSON DARVOZALARI (bu joylarda to'xta va mendan aynan shuni so'ra)

1. **1-fazadan keyin:** `docs/NORMS_REVIEW.md` ni tayyorla. Unda har bir norma uchun qiymat, manba bandi, holat va imzo uchun bo'sh joy bo'lsin. Litsenziyali muhandis normalarni tekshirmaguncha `reviewed_by` ni o'zing to'ldirma; buni hech qachon qilma.
2. **11-fazadan oldin:** domen, O'zbekistondagi server (IP, SSH foydalanuvchisi), SMTP/SMS ma'lumotlari. Maxfiy ma'lumotlar faqat `.env` orqali uzatiladi va hech qachon commit qilinmaydi.
3. **12-fazadan oldin:** release keystore. Uni men yarataman yoki beraman, sen faqat `key.properties` shablonini tayyorlaysan. Play Console'ga yuklashni men bajaraman.
4. **Pilotdan keyin:** laboratoriyadan kelgan fikr-mulohazalar asosida keyingi rejani birga tuzamiz.

Darvozada to'xtaganingda menga quyidagilarni ber: nima tayyor, aynan nima kerak, keyingi qadam.

---

## 10. Hisobot formati (har faza oxirida, o'zbek tilida)

```
## Faza N — <nomi>: TAYYOR / BLOKLANGAN
- Nima qilindi: ...
- Testlar: X ta o'tdi, coverage: ...
- Qarorlar (ADR): ...
- Xavflar / ochiq savollar: ...
- Keyingi faza: ...
```

## 11. Birinchi qadam

1. Ushbu promptni `docs/PROMPT.md` ga saqla.
2. `CLAUDE.md` va `docs/PROGRESS.md` ni yarat.
3. Fazalar bo'yicha qisqa reja va `zanjir_core` uchun fayl tuzilishini menga ko'rsat. Bu yagona joy bo'lib, unda boshlashdan oldin tasdiqlashimni kutasan.
4. Tasdiqdan keyin 0-fazadan boshlab mustaqil ravishda ishlab, inson darvozalarigacha davom et.
