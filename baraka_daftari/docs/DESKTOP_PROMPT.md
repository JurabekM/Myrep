# «BARAKA DAFTARI DESKTOP» — UMUMIY LOYIHA PROMPTI
### Tauri 2 + Rust + React · Windows birinchi navbatda · Mobil ilova bilan test vektorlari orqali mos

> Versiya: v1.0 · AI-dasturchi (Claude Code va h.k.) uchun.
> Funksional manba: `docs/SPEC.md` (= `FINTECH_PROMPT.md` v0.7, 1–5-qonunlar).
> Bu fayl desktop uchun **stek, arxitektura, farqlar va ish rejasi**ni belgilaydi. SPEC bilan zid kelgan joyda **texnik masalalarda shu fayl**, **mahsulot va diniy-moliyaviy qoidalarda SPEC** ustun turadi.

---

## 0. ROL
Sen — senior Rust + TypeScript dasturchisan. Desktop ilovalar, amaliy kriptografiya va moliyaviy dasturiy ta'minot bo'yicha tajribang bor. Kodni production-sifatda, testlar bilan yozasan, xavfsizlik va **pul hisobining aniqligi** birinchi o'rinda turadi.

## 1. MAHSULOT VA DESKTOPNING O'RNI
- **«Baraka daftari»** — O'zbekiston o'rta qatlami uchun ribosiz (islom moliyasi tamoyillari asosidagi) shaxsiy va oilaviy moliya ilovasi.
- U ta'lim va amaliyotni birlashtiradi: 12 ta qissa orqali **halol boylikning 7 qonuni** o'rgatiladi va har biri ilovadagi vositalar bilan amalda bajariladi. Hozircha 1–5-qonunlar spetsifikatsiya qilingan. Ularning batafsil tavsifi `docs/SPEC.md` ning 1, 2, 2B–2E bo'limlarida.
- Mobil ilova (Flutter + Kotlin) kundalik tez kiritish uchun mo'ljallangan. **Desktop esa uning nusxasi emas, «Oila kengashi va biznes stoli»**:
  - katta ekranda oylik audit va oila kengashi (havas chegarasi, marosim stsenariylari);
  - qarzdan chiqish rejasini chuqur tahlil qilish va amortizatsiya jadvallari;
  - sheriklik shartnomalari, venture ledger, PDF va **chop etish**;
  - klaviatura bilan tez kiritish (hafta yoki oyning ma'lumotlarini bir o'tirishda kiritish);
  - eksport va import orqali telefon bilan ma'lumot almashish.
- **To'liq offline** ishlaydi. Server ham, akkaunt ham yo'q.

### 1.1. 1–5-qonunlarning qisqa mazmuni (SPEC'ga havola bilan)
| # | Qonun | Desktopdagi asosiy vositalar | SPEC |
|---|---|---|---|
| 1 | Avval o'zingga to'la | Daromad, avto-ulush, «Kelajagim», streak, oylik audit, «Kimning puli?» | 2 |
| 2 | Xurjunning teshigini yama | Zarur/Kerak/Havas, havas chegarasi (oila roziligi bilan), obunalar, konvertlar, «Qutqarilgan pul», sadaqa ajratmasi | 2B |
| 3 | Pul ikki xil yashaydi | Qorovul/O'sadigan jamg'arma (6 oy), «Narx daftari», shaxsiy inflyatsiya, tayyorgarlik darvozasi, ribo filtri | 2C |
| 4 | Ribodan qoch, reja bilan chiq | Qarz inventari, haqiqiy narx, 70/20/10, payoff planner, tilxat, marosim rejalovchisi | 2D |
| 5 | Pulni halol ishga sol | Mudoraba/Musharaka, shartnoma, buyout, venture ledger, taklif detektori | 2E |

## 2. TEXNOLOGIK STEK — QAT'IY QARORLAR (ADR)
> Bu qarorlar o'zgarmaydi. O'zgartirish kerak bo'lsa, avval sababini yozib, ruxsat so'raysan. Yangi crate yoki npm paket qo'shishdan oldin uning nima uchun kerakligini yozasan.

| Qatlam | Tanlov |
|---|---|
| Shell | **Tauri 2** (stable). Platformalar: **Windows 10/11 x64 — 1-navbat**, macOS (arm64/x64) — 2-navbat, Linux — 3-navbat |
| Yadro tili | **Rust** (stable, `rust-toolchain.toml` bilan qotiriladi), edition 2021+ |
| Baza | **SQLite + SQLCipher**: `rusqlite` (`bundled-sqlcipher-vendored-openssl`). Migratsiyalar `refinery` yoki `rusqlite_migration` orqali |
| Kalit saqlash | `keyring` crate (Windows Credential Manager / DPAPI, macOS Keychain, Linux Secret Service) |
| KDF va kripto | `argon2` (Argon2id), `chacha20poly1305` yoki `aes-gcm` (eksport fayllari uchun), `rand` (OsRng), `zeroize` |
| Pul | O'zimizning `money` crate: `i64` minor birlik. `f32`/`f64` pul uchun **taqiqlanadi** (clippy lint bilan) |
| Sana va vaqt | `time` (yoki `chrono`) + `chrono-tz`: `Asia/Tashkent`, `weekAnchor = FRIDAY` |
| ID | `uuid` v7 |
| PDF | **`typst`** (embedded, kutubxona sifatida). Shablonlar `.typ` fayllarda, shriftlar ilovaga o'rnatiladi (`ʻ` U+02BB va `ʼ` U+02BC belgilari to'g'ri chiqishi shart) |
| Serializatsiya | `serde`, `serde_json`; JSON Schema — `schemars` |
| Xatolar va loglar | `thiserror`, `tracing` (+ `tracing-appender`). Loglarda summa, ism va izoh **bo'lmaydi** |
| Frontend | **React 18+**, **TypeScript (strict)**, **Vite** |
| UI | Tailwind CSS + Radix UI primitivlari (yoki shadcn/ui). Mavzu: «daftar» (qog'oz fon), light va dark |
| State | **TanStack Query** (yadrodan keladigan ma'lumotlar), **Zustand** (faqat UI holati) |
| Jadvallar va grafiklar | **TanStack Table** (virtualizatsiya bilan), **ECharts** |
| Formalar | `react-hook-form` + `zod` |
| i18n | `i18next`: `uz` (asosiy, lotin), `ru` |
| Rust ↔ TS chegarasi | **`tauri-specta`**: barcha commandlar va DTO'lar uchun TS tiplari avtomatik generatsiya qilinadi. Qo'lda yozilgan `invoke('...')` taqiqlanadi |
| Testlar | Rust: `cargo test`, `proptest`, `insta` (snapshot). TS: `vitest`, `@testing-library/react`. E2E: `tauri-driver` + WebdriverIO (Windows) |
| Lint | `clippy -D warnings` (+ `clippy::float_arithmetic` pul crate'larida `deny`), `rustfmt`; ESLint (strict) + Prettier |
| CI | GitHub Actions: `windows-latest` (asosiy), `macos-latest`, `ubuntu-latest`. Bosqichlar: fmt → clippy → test → **test vektorlari** → frontend lint/test → build |
| Paketlash | Windows: **NSIS** installer (va keyinroq MSIX). Kod imzolash sertifikati CI secret'da. macOS: DMG (notarization). Linux: AppImage + deb |
| Yangilanish | `tauri-plugin-updater` (imzolangan manifest). MVP'da faqat qo'lda tekshirish |

## 3. ARXITEKTURA

### 3.1. Repo tuzilmasi (Cargo workspace + pnpm)
```
baraka-desktop/
  Cargo.toml                 (workspace)
  rust-toolchain.toml
  crates/
    money/                   Money, Currency, allocate, percent_of, FxRate, formatlash
    domain/                  Barcha entitylar, qoidalar, kalkulyatorlar (IO yo'q, sof funksiyalar)
      src/ income/ vault/ budget/ subscriptions/ envelopes/ prices/ gate/
           debts/ payoff/ ceremonies/ partnerships/ ventures/ offers/ content/
    storage/                 SQLCipher, migratsiyalar, repository implementatsiyalari
    security/                Kalit boshqaruvi (keyring), PIN KDF, lock holati, eksport shifrlash
    pdf/                     typst shablonlari va renderer
    interchange/             Eksport/import formati (JSON Schema + shifrlangan konteyner)
    vectors/                 Test vektorlarini yuklovchi va runner (dev-dependency)
  src-tauri/                 Tauri ilovasi: commandlar (yupqa qatlam), oyna, tray, hotkey
  ui/                        React ilovasi
    src/ app/ features/<feature>/ components/ i18n/ bindings/ (generatsiya qilingan)
  spec/
    test-vectors/            *.json — mobil va desktop uchun UMUMIY oltin vektorlar
    interchange/             export-format.schema.json
  docs/  SPEC.md  CHANGELOG.md  OPEN_QUESTIONS.md  ADR/
```

### 3.2. Qatlam qoidalari
- `money` va `domain` **sof** bo'ladi: IO, vaqt yoki tasodifiylik yo'q. `Clock` va `IdGen` trait orqali beriladi. Barcha biznes qoidalari shu yerda yashaydi.
- `src-tauri` commandlari **yupqa** bo'ladi: argumentni validatsiya qiladi → domain/storage'ni chaqiradi → DTO qaytaradi. Command ichida biznes mantiq bo'lmaydi.
- **Frontend pul hisoblamaydi.** U faqat yadrodan kelgan, tayyor formatlangan qiymatlarni ko'rsatadi. Foiz, ulush va jami summa — barchasi Rustda hisoblanadi. Formada kiritilgan summa string sifatida yuboriladi va Rustda parse qilinadi.
- DTO'larda pul `{ minor: string, currency: "UZS" }` ko'rinishida uzatiladi (JS `number` ning 2^53 chegarasidan himoya uchun), ko'rsatish uchun `formatted: string` ham qo'shiladi.

### 3.3. Tauri xavfsizlik konfiguratsiyasi
- **Capabilities:** har bir oyna faqat o'ziga kerakli commandlarga ruxsat oladi. `shell`, `http` va keng `fs` pluginlari **yoqilmaydi**. Fayl tanlash faqat `dialog` orqali bo'ladi, faylni yozish va o'qish Rust tomonida bajariladi.
- **Qat'iy CSP:** `default-src 'self'`, tashqi manbalar yo'q, `unsafe-eval` yo'q. Shriftlar va rasmlar ilova ichida.
- Tarmoq ishlatilmaydi (updater bundan mustasno). Telemetriya yo'q.
- `window.setContentProtected(true)` — moliyaviy oynalarda skrinshot va ekran yozuvidan himoya (Windows: `WDA_EXCLUDEFROMCAPTURE`, macOS: `sharingType = none`). Linuxda bu imkoniyat yo'qligi «Xavfsizlik» sahifasida ochiq aytiladi.
- Release build'da DevTools o'chirilgan bo'ladi.

## 4. PUL MODELI VA HISOB QOIDALARI (mobil bilan bir xil bo'lishi SHART)
Bu qoidalar `spec/test-vectors` orqali mobil ilova bilan **bitma-bit** mos bo'lishi kerak.

1. **`Money { minor: i64, currency: Currency }`**. Valyutalar: `UZS` (2 xona, tiyin), `USD`, `EUR`, `RUB` (2 xona). Asosiy valyuta — `UZS`.
2. Har xil valyutalarni qo'shish → `Error::CurrencyMismatch`. Konvertatsiya faqat `FxRate { from, to, rate_num: i64, rate_den: i64, date, source }` orqali, natija **half-up** yaxlitlanadi.
3. **`allocate(total, ratios)`** — largest remainder usuli:
   - har bir qismning aniq ulushi `total × r_i / Σr` (rational, butun sonlarda);
   - avval `floor` olinadi, qolgan birliklar **kasr qismi kattaroq** bo'lganlarga bittadan beriladi;
   - kasrlar teng bo'lsa, **kichik indeksli** qismga beriladi;
   - yig'indi har doim `total` ga teng chiqadi.
4. **`percent_of(m, bp)`** — `allocate(m, [bp, 10000 − bp])[0]`. Bu yaxlitlash qoidasini allocate bilan bir xil qiladi.
5. Foiz va ko'rsatkichlar ichki hisobda **basis points (i64)** sifatida saqlanadi. Ko'rsatish uchungina formatlanadi.
6. **Half-up yaxlitlash** (`round_half_up`) — faqat bitta markazlashgan funksiya. Boshqa joyda yaxlitlash taqiqlanadi.
7. Oraliq hisoblarda overflow xavfi bo'lsa, `i128` yoki rational ishlatiladi. Oxirgi natija `i64` ga qaytariladi va overflow tekshiriladi.

## 5. UMUMIY OLTIN TEST VEKTORLARI (`spec/test-vectors/`)

### 5.1. Maqsad
Pul mantig'i ikki tilda yashaydi: mobil (Dart) va desktop (Rust). Ikkalasi bir xil kirishga **bir xil natija** berishini kafolatlash uchun umumiy JSON vektorlar yoziladi. **Har ikkala loyihaning CI'si shu vektorlardan o'tmasa, build qizil bo'ladi.** Vektorlar papkasi ikki repo o'rtasida git submodule yoki alohida `baraka-spec` repo sifatida ulashiladi.

### 5.2. Format
```json
{
  "suite": "allocate",
  "version": 1,
  "description": "Largest remainder taqsimoti, teng kasrda kichik indeks ustun",
  "cases": [
    { "id": "alloc-001", "input": { "total": "100", "currency": "UZS", "ratios": [1, 1, 1] },
      "expected": { "parts": ["34", "33", "33"] } }
  ]
}
```
- Barcha pul qiymatlari **string** (minor birlikda) yoziladi.
- Har bir `case` ning `id` si o'zgarmaydi. Xato topilsa, vektor o'chirilmaydi, yangi `version` chiqariladi.
- Runner har bir suite uchun mos domen funksiyasini chaqiradi va natijani `expected` bilan **to'liq** solishtiradi.

### 5.3. Majburiy suite'lar va boshlang'ich vektorlar
Quyidagi qiymatlar aniq hisoblangan va **o'zgartirilmaydi**. Ular shu bo'limdagi algoritm ta'riflari asosida chiqarilgan.

**`allocate.json`**
| id | total | ratios | expected |
|---|---|---|---|
| alloc-001 | 100 | [1,1,1] | [34, 33, 33] |
| alloc-002 | 800000000 | [70,20,10] | [560000000, 160000000, 80000000] |
| alloc-003 | 12345 | [1000,9000] | [1235, 11110] |
| alloc-004 | 100 | [1,1,1,1,1,1,1] | [15, 15, 14, 14, 14, 14, 14] |
| alloc-005 | 0 | [1,2] | [0, 0] |

**`percent_of.json`**
| id | amount | bp | expected |
|---|---|---|---|
| pct-001 | 800000000 (8 mln so'm) | 1000 (10%) | 80000000 |
| pct-002 | 12345 | 1000 | 1235 |

**`amortization.json`** — annuitet, **muddatni qisqartirish** rejimi (oylik to'lov o'zgarmaydi).
Algoritm:
- `r = annualBp / 10000 / 12` (rational);
- `payment = round_half_up(P·r / (1 − (1+r)^−n))`;
- har oy: `interest = round_half_up(balance·r)`, `principal = payment − interest`;
- agar `principal ≥ balance` yoki bu oxirgi oy bo'lsa, `principal = balance`;
- so'ng `extra = min(extra, balance)` qoldiqdan ayriladi.

| id | Ssenariy | P (tiyin) | annualBp | n | extra/oy | expected payment | expected months | expected totalInterest |
|---|---|---|---|---|---|---|---|---|
| amort-001 | Anvar, odatiy grafik | 3900000000 | 2400 | 14 | 0 | 322147684 | 14 | 610067573 |
| amort-002 | Anvar + 20% (1,6 mln) | 3900000000 | 2400 | 14 | 160000000 | 322147684 | **9** | 397018667 |
| amort-003 | Anvar + 20% + qutqarilgan pul (2,4 mln) | 3900000000 | 2400 | 14 | 240000000 | 322147684 | **8** | 341756885 |

*(Stavka 24% illyustrativ. Bu vektorlar algoritmni tekshiradi, real bank shartlarini emas. Hikoyadagi «14 oy → 8–9 oy» natijasi shu yerda tasdiqlanadi.)*
Har bir case `schedule` massivini ham saqlaydi (`month, interest, principal, extra, balance`). Masalan, amort-002 ning 9-oyi: `interest 8624259, principal 313523425, extra 117689511, balance 0`. Runner jadvalni ham to'liq solishtiradi.

**`profit_distribution.json`**
| id | Tur | Kirish | expected |
|---|---|---|---|
| dist-001 | MUDARABA, foyda | foyda 300000000, ulush [5000, 5000] | [150000000, 150000000] |
| dist-002 | MUDARABA, zarar, beparvolik yo'q | zarar 200000000 | kapital egasi −200000000, ishchi 0 |
| dist-003 | MUSHARAKA, zarar | zarar 300000000, kapital [600000000, 200000000] | [−225000000, −75000000] |
| dist-004 | Kafolatli summa | `fixedReturn` berilgan | `error: GUARANTEED_RETURN_FORBIDDEN` |

**Boshqa majburiy suite'lar** (case'lar dastlabki vazifalarda kengaytiriladi):
- `emergency_target.json`:
  - formula: `round_half_up(Σ(ZARUR+KERAK, oxirgi k oy) × N / k)`;
  - case: oylar [520000000, 500000000, 530000000], N = 6 → **3100000000** (31 mln so'm).
- `personal_inflation.json`:
  - savat: go'sht 8000000 → 13000000 (og'irlik 50%), non 200000 → 300000 (50%);
  - kutilgan natija: go'sht 6250 bp, non 5000 bp, indeks **5625 bp**.
- `unexplained_gap.json`:
  - daromad 800000000, majburiyatlar 535000000, xarajatlar 165000000, jamg'arma 0 → **100000000** (1 mln so'm «izohsiz»).
- `readiness_gate.json`: {qorovul oylari, foizli qarz bormi, qarz rejasi bormi} → `OPEN / LOCKED` + sabablar ro'yxati (to'liq kombinatsiya matritsasi).
- `fx_convert.json`, `money_format.json` (`"8 000 000 so'm"`, manfiy qiymatlar, `ru` lokali).
- `debt_recovery_split.json`: 70/20/10 va jamg'arma ulushi minimal 1% bo'lishi.

### 5.4. Vektorlar bilan ishlash tartibi
1. Yangi pul funksiyasi **avval vektor bilan** yoziladi (TDD), keyin implementatsiya.
2. Desktopda topilgan har qanday hisob xatosi vektorga aylantiriladi va mobil jamoaga xabar beriladi (`docs/OPEN_QUESTIONS.md`).
3. Vektor fayliga o'zgartirish kiritish uchun ikkala platforma egasining ma'qullashi kerak (`CODEOWNERS`).

## 6. MA'LUMOTLAR, SAQLASH VA ALMASHISH

### 6.1. Konvensiyalar (mobil bilan bir xil)
- ID: UUIDv7 (string).
- Har bir jadvalda: `household_id`, `created_at`, `updated_at` (UTC, ISO-8601), `deleted_at` (soft delete), `version` (i64), `origin_device_id`.
- Entity nomlari va maydonlari SPEC 5-bo'limdagi bilan bir xil (snake_case). `Asset` abstraksiyasi ham xuddi o'sha: `CASH | BANK_CARD | VAULT | GOLD | SILVER | FOREIGN_CURRENCY | RECEIVABLE | TRADE_GOODS | BUSINESS_SHARE`.
- Byudjet davrlari lokal sana bo'yicha (`Asia/Tashkent`). Oylik kuni va hafta boshi sozlanadi.

### 6.2. Shifrlash va kalitlar
- Birinchi ishga tushirishda 256-bit DB kaliti `OsRng` dan olinadi va **OS keyring**'ga yoziladi.
- Bundan tashqari, kalit **PIN'dan hosil qilingan kalit (Argon2id) bilan ham wrap qilinadi**. Shunda keyring buzilsa yoki boshqa foydalanuvchi olib qo'ysa ham, PIN'siz ochib bo'lmaydi.
- Xotiradagi kalit va PIN `zeroize` bilan tozalanadi.
- PIN: 6 raqam. Xato kiritilganda o'sib boruvchi kutish. Ilova fonga o'tgandan **5 daqiqa** keyin (sozlanadi) yoki ekran qulflanganda avtomatik qulflanadi. Windows Hello: `windows` crate (`UserConsentVerifier`) orqali ixtiyoriy.
- **Bir kompyuter, bir nechta Windows foydalanuvchisi:** baza `%APPDATA%\BarakaDaftari\` ichida, har bir Windows foydalanuvchisi uchun alohida bo'ladi.

### 6.3. Telefon ↔ desktop almashish (v1: shifrlangan fayl)
- **Format:** `.baraka` fayli = shifrlangan konteyner (Argon2id(parol) → XChaCha20-Poly1305), ichida `export-format.schema.json` ga mos JSON (yoki JSON Lines) bo'ladi. Sxema `spec/interchange/` da, mobil ilova bilan **umumiy**.
- **Eksport:** to'liq yoki faqat oxirgi sinxronlashdan keyingi o'zgarishlar (`updated_at > since`).
- **Import va birlashtirish:**
  - yozuvlar `id` bo'yicha moslashtiriladi;
  - bir xil `id` uchun `version` kattasi yutadi, teng bo'lsa `updated_at` kechrog'i yutadi;
  - `deleted_at` (tombstone) o'chirish sifatida qo'llanadi;
  - ziddiyatlar ro'yxati foydalanuvchiga ko'rsatiladi.
- **Moliyaviy yaxlitlik:** yopilgan davrlar (venture taqsimoti, imzolangan shartnoma versiyasi) import orqali **o'zgartirilmaydi**. Ziddiyat bo'lsa, ogohlantirish chiqadi.
- **QR orqali uzatish:** kichik o'zgarishlar uchun ixtiyoriy, v1.1 da.
- Kelajakda server sinxronlashiga (Ktor + PostgreSQL) shu maydonlar asosida o'tiladi.

## 7. DESKTOPGA XOS FUNKSIYALAR VA UX
- **Oyna tuzilmasi:** chap tomonda navigatsiya (Bosh sahifa, Daromad, Xarajatlar, Kelajagim, Byudjet, Qarzlar, Marosimlar, Sheriklik, Narx daftari, Boblar, Sozlamalar), markazda ish maydoni, o'ng tomonda kontekst paneli (Sobir hoji maslahati yoki tafsilotlar).
- **Klaviatura:**
  - `Ctrl+N` — tez kiritish (daromad yoki xarajat), `Ctrl+K` — buyruq palitrasi, `Ctrl+P` — chop etish, `Ctrl+L` — qulflash;
  - jadvallarda Excel uslubida tahrirlash: `Tab`, `Enter`, strelkalar.
- **Ommaviy kiritish:** «Hafta varag'i» rejimi — jadvalda bir haftaning barcha xarajatlarini ketma-ket kiritish, kategoriya avtomatik to'ldiriladi.
- **Tray va global hotkey** (`tauri-plugin-global-shortcut`): `Ctrl+Alt+B` — kichik «tez xarajat» oynasi (mobildagi vidjetga muqobil). Ilova qulfli bo'lsa, summalar ko'rinmaydi.
- **Oila kengashi rejimi:** to'liq ekran, yirik shrift. Ekrandagi qadamlar: oyni ko'rib chiqish → toifalarni kelishish → havas chegarasini har bir `ADULT` a'zo o'z PIN'i bilan tasdiqlashi → yakuniy PDF bayonnoma.
- **Chop etish:** barcha hisobotlar, tilxat, shartnoma va oylik audit `typst` → PDF → tizim chop etish dialogi orqali.
- **Bildirishnomalar:** `tauri-plugin-notification` — juma eslatmasi va majburiyat muddatlari (faqat ilova yoki tray ishlab turganda). Ishga tushirishda o'tkazib yuborilgan eslatmalar ko'rsatiladi.
- **Ochiq ma'lumotlarni import qilish:** CSV (bank ko'chirmasi) → xaritalash ustasi → xarajatlar. Bu ommaviy kiritish uchun, bank integratsiyasi emas.
- **Accessibility:** to'liq klaviatura navigatsiyasi, focus ko'rinishi, Windows High Contrast, 125–200% DPI masshtablash.

## 8. MAHSULOT CHEKLOVLARI (SPEC 3-bo'limdan, desktopda ham qat'iy)
- Foizli kredit, mikroqarz yoki «tez pul» reklama va integratsiyalari yo'q. Foiz stavkasi hech qachon «muqobil daromad» sifatida ko'rsatilmaydi (i18n matnlarida taqiqlangan iboralar testi bo'ladi).
- `Receivable` da foiz maydoni yo'q. Sheriklikda kafolatli daromad kiritib bo'lmaydi.
- Ohang Sobir hoji uslubida: iliq, ayblamaydigan. Uyaltirish, qo'rqitish va va'dalar yo'q. Sadaqa havas hisobiga kirmaydi va uni kamaytirish «yutuq» deb ko'rsatilmaydi.
- Har bir ta'limiy ekranda disklеymer: «Ta'limiy material. Fatvo yoki moliyaviy maslahat emas».
- Diniy matnlar va shartnoma shablonlari `review_status = APPROVED` bo'lmasa, release'da ko'rsatilmaydi (shablonlar ogohlantirish bilan ko'rsatiladi).
- Qissa matnlari litsenziya hal bo'lguncha **placeholder** bo'lib turadi (kontent egasi — «Asaxiy Invest» × Abdukarim Mirzayev).
- Ilova pulni saqlamaydi va o'tkazmaydi. Sheriklarni bir-biriga tanishtirmaydi va pul yig'maydi (P2P yoki kraudfanding emas).

## 9. ISH REJASI (har bir vazifa alohida sessiyada)

### Umumiy kirish (har bir sessiya boshiga qo'yiladi)
```
Sen «Baraka daftari Desktop» loyihasining senior Rust + TypeScript dasturchisisan.
Avval docs/DESKTOP_PROMPT.md (2–6, 8, 10-bo'limlar) va docs/SPEC.md dagi tegishli bo'limni o'qi.
2-bo'lim (ADR) qat'iy. Pul hisobi faqat Rust `money`/`domain` crate'larida; frontend hisoblamaydi.
Yangi pul funksiyasi — avval spec/test-vectors ga vektor, keyin kod.
Bu sessiyada FAQAT quyidagi vazifani bajar. Avval qisqa reja yoz, keyin bajar.
Oxirida: bajarilgan ishlar, qabul mezonlari holati, ochiq savollar.
Kod va identifikatorlar inglizcha; izohlar, hujjatlar va UI matnlari o'zbekcha.
```

### A. Poydevor
**D1 — Workspace, Tauri skeleti, CI**
- Cargo workspace + pnpm, Tauri 2, React + Vite + TS strict, Tailwind va Radix, i18next (`uz`/`ru`).
- `tauri-specta` bitta namunaviy command bilan.
- Qat'iy CSP va capabilities. Release'da DevTools o'chiq.
- CI matritsasi (Windows asosiy): fmt, clippy, test, frontend lint/test, build.
- **Qabul mezonlari:** Windows'da NSIS installer yig'iladi va ishga tushadi; generatsiya qilingan TS tiplari bilan command chaqiriladi; CI yashil.

**D2 — `money` crate va test vektorlari runner'i**
- `Money`, `Currency`, `allocate`, `percent_of`, `round_half_up`, `FxRate`, formatlash (`uz`, `ru`).
- `spec/test-vectors/` va 5.3 dagi vektorlar (allocate, percent_of, fx, format).
- `vectors` crate: barcha suite'larni yuklaydi va CI'da ishga tushiradi.
- `proptest`: allocate yig'indisi doim teng, manfiy qism yo'q.
- `clippy::float_arithmetic = deny`.
- **Qabul mezonlari:** barcha vektorlar yashil; qamrov ≥ 95%; valyuta aralashuvi xato beradi.

**D3 — Xavfsizlik va shifrlangan baza**
- `security` crate: keyring + PIN bilan qo'shimcha wrap (6.2), Argon2id, `zeroize`, lockout.
- `storage` crate: SQLCipher, migratsiyalar, sxema v1 (households, members, categories, incomes, expenses, assets + snapshots, vault_transactions, allocation_rules, obligations, fx_rates), repository'lar.
- Lock ekrani, avto-qulflash, `setContentProtected`, Windows Hello (ixtiyoriy).
- **Qabul mezonlari:** DB faylini kalitsiz ochib bo'lmaydi (test); keyring'dagi yozuvni o'chirib, faqat PIN bilan ochib bo'lmasligi (hamda PIN + keyring bilan ochilishi) tekshirilgan; migratsiya testlari bor; skrinshot qora chiqadi (qo'lda tekshiruv).

### B. 1-qonun
**D4 — Daromad, «Kelajagim», audit, «Kimning puli?», bosh sahifa**
- SPEC 2.1–2.5. Tez kiritish (`Ctrl+N`), ulush taklifi, progressiv ulush, streak (hafta jumadan boshlanadi), friction bilan pul olish, boshlang'ich balans.
- Oylik audit ustasi va izohsiz summa.
- Majburiyatlar va nasiya.
- Bosh sahifa slot-arxitektura bilan.
- Vektorlar: `unexplained_gap.json`, streak.
- **Qabul mezonlari:** vektorlar yashil; audit oxirgi qadamigacha faqat klaviatura bilan bajariladi; E2E: daromad → ulush → balans.

**D5 — Kontent dvigateli (5 bob)**
- JSON kontent, `review_status`, placeholder matnlar, «Daftar sahifasi», haftalik vazifalar + `TaskTrigger`, odat asosidagi `ChapterUnlockPolicy` (SPEC 2C.6), disklеymer.
- **Qabul mezonlari:** `PENDING` diniy blok release'da ko'rinmaydi (test); unlock policy unit testlari bor.

### C. 2-qonun
**D6 — Uch toifa, havas chegarasi, oila kengashi**
- `Necessity`, kategoriya standart toifalari va o'zgarishlar tarixi, `HavasLimit` + har bir `ADULT` a'zoning PIN bilan roziligi, sadaqa ajratmasi, `is_gift` / `is_ostentation` / `funded_by_debt`, «Juma shirinligi», odatlar statistikasi.
- **Oila kengashi rejimi** (7-bo'lim) va PDF bayonnoma.
- «Hafta varag'i» ommaviy kiritish.
- **Qabul mezonlari:** rozilik to'liq bo'lmaguncha chegara faol emas (test); sadaqa havasga kirmaydi (test); bayonnoma PDF'ida o'zbekcha belgilar to'g'ri chiqadi (snapshot test).

**D7 — Obunalar, konvertlar, «Qutqarilgan pul», tray**
- SPEC 2B.5–2B.7. Unutilgan obuna ogohlantirishi, yillik narx, naqd konvert rejimi, qutqarilgan pul formulasi va «Kelajagim»ga o'tkazish.
- Tray + `Ctrl+Alt+B` tez xarajat oynasi.
- CSV import ustasi.
- **Qabul mezonlari:** qutqarilgan pul vektorlari (manfiy holat → 0) yashil; qulf holatida tray oynasi summa ko'rsatmaydi.

### D. 3-qonun
**D8 — Qorovul/O'sadigan, narx daftari, inflyatsiya, darvoza, ribo filtri**
- SPEC 2C: VAULT → QOROVUL migratsiyasi, 6 oylik maqsad (vektor), «Narx daftari» va shaxsiy indeks (vektor), «Sichqon kemirgani», `ReadinessGate` (vektor matritsasi), ongli chetlab o'tish, `IncomeSourceType`, taqiqlangan iboralar i18n testi.
- **Qabul mezonlari:** `emergency_target`, `personal_inflation` va `readiness_gate` vektorlari yashil; migratsiyada balans yo'qolmaydi.

### E. 4-qonun
**D9 — Qarz inventari, haqiqiy narx, friction, tilxat**
- `Debt` (jadval turlari: `ANNUITY | DIFFERENTIATED | FIXED_MARKUP | MANUAL`), `DebtPayment`, `Receivable` (foizsiz), `Goal`, `BorrowCheck`, haqiqiy narx va imkoniyat narxi.
- **Qarz tilxati PDF:** guvohlar va imzo joylari bo'ladi; desktopda imzo sichqoncha, pero yoki «chop etib qo'lda imzolash» rejimi orqali qo'yiladi.
- **Qabul mezonlari:** `Receivable` da foiz maydoni yo'q (kompilyatsiya darajasida); to'lov rejasisiz qarz saqlanmaydi; tilxat PDF snapshot testi bor.

**D10 — `DEBT_RECOVERY` 70/20/10, payoff planner, «Qarzsiz kun»**
- Amortizatsiya simulyatori (4 xil jadval turi), odatiy va tezlashtirilgan grafik, **katta jadval va grafik** (ECharts), yopish tartibi strategiyasi, muddatidan oldin to'lash shartlari, `DebtContributor`, sotiladigan buyumlar, «Qarzsiz kun», rejimning avtomatik qaytishi.
- **Qabul mezonlari:** `amortization.json` (amort-001…003, to'liq jadvallar bilan) va `debt_recovery_split.json` yashil; jamg'arma ulushini 0 qilib bo'lmaydi.

**D11 — Marosim rejalovchisi**
- SPEC 2D.8: byudjet qatorlari, moliyalash manbalari, `DEBT` manbasi bo'lsa oilaviy muhokama (oila kengashi rejimi bilan), 2–3 stsenariyni yonma-yon solishtirish (to'lash muddati D10 simulyatori bilan), to'yona o'rniga `Goal`, chop etiladigan smeta.
- **Qabul mezonlari:** muhokamasiz `CONFIRMED` holatiga o'tib bo'lmaydi (test).

### F. 5-qonun
**D12 — Sheriklik domeni, shartnoma, buyout**
- SPEC 2E.1, 2E.2, 2E.6: `MUDARABA` / `MUSHARAKA` validatsiyasi (`profit_distribution.json`), shartnoma ustasi, versiyalash, `typst` PDF, imzolar, buyout jadvali, darvozaning faqat kapital kirituvchiga qo'llanishi, kapital qabul qilishda oilaviy rozilik.
- **Qabul mezonlari:** dist-001…004 yashil; kafolatli daromad domen darajasida bloklanadi; versiya o'zgarganda imzolar qayta so'raladi.

**D13 — Venture ledger, taqsimot, «Hunardan ishga», taklif detektori**
- SPEC 2E.3–2E.5: ledger (chek rasmlari shifrlangan holda saqlanadi), davrni yopish va o'zgarmaslik, avtomatik taqsimot va buyout ayirmasi, fors-major, **sherik uchun davr hisoboti PDF**, «Hunardan ishga» (3 stsenariy va payback), `OfferCheck` (yashil / sariq / qizil).
- **Qabul mezonlari:** taqsimot vektorlari yashil; yopilgan davrni o'zgartirib bo'lmaydi; OfferCheck qaror jadvali testlangan.

### G. Almashish va reliz
**D14 — `.baraka` eksport/import (telefon ↔ desktop)**
- 6.3-bo'lim: JSON Schema `spec/interchange/`, shifrlangan konteyner, to'liq va inkremental eksport, birlashtirish qoidalari, ziddiyatlar ekrani, yopilgan davrlar himoyasi.
- **Qabul mezonlari:** eksport → yangi baza → import natijasi 1:1 (round-trip test); ziddiyat ssenariylari testlangan; noto'g'ri parol aniq xato beradi; sxema mobil ilova bilan bir xil fayl.

**D15 — Reliz tayyorgarligi**
- Onboarding (≤ 5 qadam), accessibility tekshiruvi, kod imzolash (Windows), imzolangan updater manifesti, DPI va High Contrast testi.
- **Yakuniy E2E** (Windows, `tauri-driver`): Anvar ssenariysi boshidan oxirigacha (daromad → audit → havas chegarasi → obuna bekor qilish → qarz → 70/20/10 → payoff → qarz yopilishi → darvoza ochilishi → sheriklik → taqsimot → eksport).
- `docs/RELEASE_CHECKLIST.md`.
- **Qabul mezonlari:** E2E yashil; imzolangan installer SmartScreen ogohlantirishisiz o'rnatiladi (sertifikat mavjud bo'lsa); sovuq start < 1,5 s.

## 10. AI-DASTURCHI UCHUN QOIDALAR
- Faqat berilgan vazifa ustida ishla. Keyingi vazifa funksiyalarini «qo'shimcha» sifatida yozma.
- 2-bo'lim (ADR)ni ruxsatsiz o'zgartirma. Yangi dependency uchun sabab yoz.
- Pul uchun `f64` yo'q. Frontendda pul hisobi yo'q. `unwrap()` / `expect()` production kodda yo'q (testlar bundan mustasno).
- `unsafe` faqat Windows API chaqiruvlarida ishlatiladi va izoh bilan asoslanadi.
- Har bir yangi pul funksiyasi uchun avval test vektori yoziladi.
- Har bir yangi command uchun capability ruxsati aniq yoziladi.
- Loglarda shaxsiy yoki moliyaviy ma'lumot yo'q.
- Noaniq joyda taxmin qilmasdan so'ra. Javobsiz qolgan savollarni `docs/OPEN_QUESTIONS.md` ga yoz.
- Har bir vazifa oxirida `docs/CHANGELOG.md` ni yangila.

## 11. DOIRADAN TASHQARIDA (v1 da qilinmaydi)
- Server sinxronlashi, akkauntlar.
- Bank va karta integratsiyalari (CSV importdan tashqari).
- 6–7-qonunlar (keyingi qissalardan keyin qo'shiladi; `Asset` va `asset_snapshots` zakot uchun allaqachon tayyor).
- Real pul o'tkazmalari.
- Sheriklar uchun platforma yoki marketplace.
- Asl qissa matnlari.

## 12. RELIZDAN OLDIN KODDAN TASHQARIDA HAL QILINADIGAN MASALALAR
- Kontent va brend litsenziyasi («Asaxiy Invest» × Abdukarim Mirzayev).
- Diniy matnlar va sheriklik shablonlarining ulamo tekshiruvi; tilxat va shartnoma shablonlarining yurist ko'rigi.
- Windows kod imzolash sertifikati (OV yoki EV) va macOS Developer ID.
- Maxfiylik siyosati (O'zbekistonning shaxsiy ma'lumotlar to'g'risidagi qonuni).
