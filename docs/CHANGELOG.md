# O'zgarishlar tarixi

Format: [Keep a Changelog](https://keepachangelog.com/uz/1.1.0/) ruhida. Versiya: [SemVer](https://semver.org/lang/uz/).

## [Unreleased]

### D6 — Uch toifa, havas chegarasi, oila kengashi (2026-10-15)

**Qo'shildi**

- **`crates/security`:** a'zo PIN verifier (`member_pin`): tuz va Argon2id, solishtirish doimiy vaqtda. PIN saqlanmaydi.
- **`crates/domain`:**
  - `necessity` — `ZARUR | KERAK | HAVAS` va `NecessityChange` (kim, qachon, qaysidan qaysiga). Standart toifalar `CategoryKey::default_necessity` da: ZARUR — ijara, kredit, oziq-ovqat, kommunal, yoqilg'i, yo'lkira; HAVAS — gazak, kafe; KERAK — qolganlari, shu jumladan bola ta'limi va sadaqa.
  - `Category::change_necessity` — o'zgartirish tarix yozuvi bilan birga qaytadi.
  - `Expense` — `necessity`, `is_gift`, `is_ostentation`, `funded_by_debt`.
  - `limit` — `HavasLimit`, `LimitConsent`; `is_active` (barcha kattalar rozi); `counts_as_havas` (`HAVAS`, sovg'a emas, sadaqa emas); `level` (80% va 100% — yumshoq darajalar).
  - `treat` — `ScheduledTreat` (haftalik, hafta kuni bo'yicha).
  - `DomainError`: `NECESSITY_UNCHANGED`, `PIN_NOT_SET`.
- **`crates/storage`:** sxema v4. Toifa standart qiymatlari v1 dagi mavjud ustunlarni (`categories.default_necessity`, `expenses.necessity`) to'ldiradi; migratsiya testi bor. Yangi jadvallar: `necessity_changes`, `havas_limits`, `limit_consents` (`UNIQUE`), `scheduled_treats`; `members` ga `pin_failed_attempts`, `pin_failed_at`. Repo'lar: `PinRepo`, `LimitRepo`, `TreatRepo`; `CategoryRepo` — tarix; `ExpenseRepo` — yangi maydonlar.
- **`src-tauri`:** `family` servisi va 12 command: `get_month_summary`, `list_month_expenses`, `add_expense`, `set_category_necessity`, `get_havas_limit`, `set_havas_limit`, `consent_havas_limit`, `list_members`, `add_member`, `set_member_pin`, `list_treats`, `add_treat`. Xarajat qo'shilganda `EXPENSE_RECORDED` hodisasi yoziladi.
- **UI:** «Xarajatlar» sahifasi (oy xulosasi, xarajat qo'shish: sovg'a, obro' va qarz bayroqlari, ro'yxat), «Juma shirinligi» kartasi, «Oila kengashi» (to'liq ekran, 4 qadam: oyni ko'rib chiqish, toifalarni kelishish, havas chegarasi va kattalar roziligi — har biri o'z PIN'i bilan, yakun). i18n: uz va ru.

**Qarorlar va sabablar**

- **Toifa xarajat yozilganda kategoriyadan olinadi va xarajatda saqlanadi.** Keyingi o'zgarish eski yozuvlarni o'zgartirmaydi.
- **Sovg'a va sadaqa havas hisobiga kirmaydi** (testlar bilan). Obro' xarajati havas ichida qoladi, lekin alohida ko'rsatiladi.
- **Chegara faol emas**, agar bitta katta ham rozi bo'lmasa (test). Yumshoq ogohlantirish faqat faol chegarada ko'rsatiladi; bloklash yo'q.
- **Chegara o'zgarsa, rozilik qayta olinadi** — yangi chegara, yangi rozilik.
- **A'zo PIN'i** ilova PIN'i bilan bir xil himoyada: uchta noto'g'ri urinishdan keyin kutish (`retry_after_secs`).
- **Juma shirinligi** faqat haftalik. Bildirishnoma yo'q (OPEN_QUESTIONS, 38-band).

**Tekshiruv**

- `cargo test --workspace`: yashil (domen 81, storage oila oqimlari 5 va v4 migratsiyasi, security PIN 5, src-tauri oila 6).
- `cargo clippy --workspace --all-targets -- -D warnings`: toza. `cargo fmt --all -- --check`: toza.
- Frontend: `pnpm test` (41, shu jumladan 7 ta yangi oila testi), `pnpm lint`, `pnpm typecheck`, `pnpm format:check`: yashil.
- GUI: dev build ochilmadi (native oyna avtomatizatsiyaga ulanmadi). React UI in-app brauzerda IPC soxtasi bilan tekshirildi: xarajat qo'shish (sovg'a bayrog'i), toifani o'zgartirish, PIN o'rnatish, noto'g'ri PIN xatosi, ikki katta roziligi («Chegara faol»), Escape bilan yopish.

**Hali bajarilmagan (keyingi bosqich)**

- Bayonnoma PDF (`typst`) va uning snapshot testi: `typst` hali qo'shilmagan (OPEN_QUESTIONS, 35-band).
- «Hafta varag'i» ommaviy kiritish (36-band).
- Odat statistikasi, SPEC 2B.9 (37-band).
- Juma shirinligi bildirishnomalari va a'zo tahriri/o'chirish (38–39-bandlar).

### D5 — Kontent dvigateli: boblar, odat asosidagi ochilish, haftalik vazifalar, «Daftar sahifasi» (2026-10-14)

**Qo'shildi**

- **Kontent (`spec/content/`):** `chapters.json` va `content_schema.json` mobil repo bilan bayt-bayt bir xil (sha256 tekshirilgan). 5 bob, har bobda aniq 3 ta haftalik vazifa, qonun va diniy bloklar. Qissa matnlari hozircha placeholder.
- **`crates/domain`:**
  - `content` — `LocalizedText` (`uz` majburiy, `ru` ixtiyoriy), `ContentBlock` (paragraph, quote, religious + `ReligiousReviewStatus`), `Chapter`, `Law`, `WeeklyTask`, `TaskTrigger` (17 hodisa kodi; noma'lum kod bobni yaroqsiz qiladi).
  - `content_parser` — mobil `ContentParser` qoidalari va xato xabarlari; buzuq bob o'tkazib yuboriladi, butun fayl buzuq bo'lsa — bo'sh natija.
  - `unlock` — `ChapterUnlockPolicy`; `HabitUnlockPolicy` (standart: 2 vazifa, 7 kun — SPEC 2C.6) va `TimeBasedUnlockPolicy` (mobil bilan paritet).
  - `progress` — `TaskCompletion` (hafta boshi bo'yicha), `DaftarPage` (bob uchun bitta, 5000 belgigacha).
  - `DomainError`: `CHAPTER_LOCKED`, `TASK_NOT_CURRENT`, `BODY_REQUIRED`, `BODY_TOO_LONG`.
- **`crates/storage`:** sxema v3 (faqat yangi jadvallar: `task_completions`, `daftar_pages`; v1 va v2 o'zgarmagan). Repo'lar: `TaskCompletionRepo` (hafta bo'yicha; birinchi bajarilish tarixi mantiqiy o'chirilganlarni ham hisobga oladi), `DaftarPageRepo`.
- **`src-tauri`:**
  - `content` servisi: kontent bir marta yuklanadi (kompilyatsiyada `include_str!`); ochilish, joriy bob va bajarilishlar har chaqiriqda hisoblanadi.
  - Command'lar: `list_chapters`, `get_chapter`, `get_weekly_tasks`, `set_task_done`, `save_daftar_page`.
  - Avtomatik hodisalar: `VAULT_OPENED` («Kelajagim» ochilganda), `INCOME_SHARED` va `VAULT_FIRST_DEPOSIT` (ulush qabul qilinganda), `EXPENSE_RECORDED` (audit xarajati), `AUDIT_COMPLETED` (audit yakunida), `DAFTAR_PAGE_WRITTEN` (sahifa saqlanganda).
  - Tasdiqlanmagan diniy blok DTO'ga release'da kirmaydi (`SHOW_PENDING_RELIGIOUS = cfg!(debug_assertions)`).
  - `ApiError`'ga yangi variant qo'shilmadi: yangi xatolar mavjud `Rule { rule }` orqali yuboriladi.
- **UI:** «Boblar» (ro'yxat: ochiq/yopiq holat, ochilish sharti), bob sahifasi (qissa bloklari, qonun, haftalik vazifalar, «Daftar sahifasi»), bosh sahifada «Shu haftaning vazifalari» kartasi. Har kontent ekranida disklеymer. i18n: uz va ru (kalitlar parite).
- **Bog'liqlik:** `crates/domain` ga `serde_json` qo'shildi (kontent JSON'ini domen qatlamida tekshirish uchun). `serde_json` workspace'da allaqachon bor (`vectors`, `src-tauri`); yangi crate emas, ADR o'zgarmadi.

**Qarorlar va sabablar**

- **Ochilish mobil bilan bir xil.** Keyingi bob: oldingi bobning 2 ta vazifasi bajarilgan va kamida 7 kun o'tgan bo'lsa ochiladi. Ochilgan bob qayta yopilmaydi: birinchi bajarilish sanasi mantiqiy o'chirilganda ham saqlanadi.
- **Joriy bob — eng so'nggi ochilgan bob.** Haftalik vazifalar faqat shu bob uchun shu hafta belgilanadi. Oldingi boblarda vazifalar faqat ko'rsatiladi (bir marta bajarilgan bo'lsa belgisi bilan).
- **Hafta juma kunidan boshlanadi** (`week_of`, mobil bilan bir xil).
- **Tasdiqlanmagan diniy blok.** Release'da yashirin: `cargo test --release` da `release_buildda_get_chapter_pending_blokni_chiqarmaydi` shuni tekshiradi. Debug buildda ulamo tekshiruvi uchun ko'rinadi va «ulamo tekshiruvida» belgisi bilan chiqadi.
- **Avtomatik belgilash idempotent.** Bir hafta ichida bir vazifa ikki marta yozilmaydi; hodisa faqat joriy bobning vazifalariga tegishli.
- **`VAULT_OPENED`** — «Kelajagim» ma'lumoti yuklanganda yoziladi. Ma'lumot qayta yuklanganda ham chaqiriladi, lekin haftada bir marta yoziladi.
- **«Daftar sahifasi» — 5000 belgi chegarasi** (standart qaror; mobilda chegara yo'q edi). OPEN_QUESTIONS, 34-band.

**Tekshiruv**

- `cargo test --workspace`: domen (unlock, parser, progress, content), storage (progress oqimlari, migratsiya v3), src-tauri (content servisi: ochilish, hodisa, DTO, Daftar sahifasi), vektorlar — yashil.
- `cargo test --release -p baraka-daftari release_buildda`: release buildda tasdiqlanmagan diniy blok `get_chapter` javobida yo'q — yashil.
- `cargo clippy --workspace --all-targets -- -D warnings`: toza. `cargo fmt --all -- --check`: toza.
- Frontend: `pnpm test` (7 fayl, 34 test), `pnpm lint`, `pnpm typecheck`, `pnpm format:check` — yashil.
- GUI: dev build (`pnpm dev`) ochilmadi — native oyna avtomatizatsiyaga ulanmadi. Shu sababli React UI in-app brauzerda, IPC soxtasi bilan tekshirildi: ro'yxat, ochiq/yopiq bob, bob sahifasi, vazifa belgilash va olib tashlash, «Daftar sahifasi» saqlash, RU/UZ almashinuvi, «Barcha boblar» va «Boblar roʻyxatiga qaytish» tugmalari, bosh sahifa kartasi. Haqiqiy Tauri IPC bilan E2E hali o'tkazilmagan (OPEN_QUESTIONS, 14-band).

### D4 — Daromad, «Kelajagim», audit, «Kimning puli?», majburiyat va nasiya, bosh sahifa (2026-10-14)

**Qo'shildi**

- **Vektorlar (`spec/test-vectors/`):**
  - `unexplained_gap.json` — mobil ilovadagi fayl bilan bayt-bayt bir xil (sha256 tekshirilgan).
  - `streak.json`, `income_share.json`, `money_parse.json` — yangi. Qoidalar mobil `habit.dart`, `vault_service.dart`, `money_format.dart` va ularning testlaridan olingan. Mobil ilova bu fayllarni hali ishlatmaydi (OPEN_QUESTIONS, 21-band).
  - `vectors` runner'lari: 8 ta suite, har bir fayl uchun runner bor (qamrov testi buni tekshiradi).
- `crates/money`: `parse_amount` (MoneyParser qoidalari: bo'sh joy, `_`, apostrof, `so'm`/`soʻm`/`сум`/`$`/`€`/`₽`, kasr aniqligi), `ceil_to_step` (yuqoriga yaxlitlash — yaxlitlashning ikkinchi yagona joyi), `MoneyError::ParseError` (`PARSE_ERROR`).
- `crates/domain`:
  - `calendar` — Toshkent sanasi (UTC+5), haftalar jumadan, oylar oylik kunidan (31 → oyning oxirgi kuni).
  - `habit` — streak (joriy hafta tugamaguncha uzilmaydi), `streak_since` (progressiv taklif uchun).
  - `share` — `ShareRule` (foiz yoki oylik summa, progressiv), `suggest_share`, `progression_offer` (4 hafta → +1 %, maks 10 %).
  - `income`, `expense`, `obligation` (tur → standart kategoriya), `category` (13 tizim kalitli kategoriya), `debt` (nasiya qoldig'i), `vault` (balans, ulush, pul olish va boshlang'ich balans qoidalari).
  - `ledger` — oy hisobi: majburiyat kategoriyadagi yozilgan xarajat bilan qoplanadi (ikki marta hisoblamaslik), izohsiz summa, «Kimning puli?» egalari.
  - `report` — oylik audit surati (o'zgarmas).
  - `DomainError` kengaytirildi: har xato barqaror kodga ega (`INSUFFICIENT_BALANCE`, `REASON_REQUIRED`, `INCOME_ALREADY_SHARED` va boshqalar).
- `crates/storage`:
  - Sxema v2 (faqat `ALTER TABLE ... ADD COLUMN` va yangi jadvallar; v1 ma'lumotlari saqlanadi — migratsiya testi bor): `households.month_start_day`, `categories.system_key` (xonadonda bir marta), `obligations.kind` va `category_id`, `vault_transactions.income_id`, `allocation_rules.progression_offered_on`. Yangi: `debts`, `debt_payments`, `monthly_reports` (davr uchun bir marta, `UNIQUE`).
  - Repo'lar: `CategoryRepo`, `IncomeRepo`, `ExpenseRepo`, `ObligationRepo`, `VaultRepo` (aktiv va yozuvlar), `RuleRepo`, `DebtRepo`, `ReportRepo`.
- `src-tauri`:
  - `session`: `verify_pin` (pul olish tasdig'i), `with_database` (faqat ochiq bazada ishlaydi), `SessionError::Locked`, `DatabaseWithoutKey` (kalit fayli yo'q, baza bor bo'lsa sozlash rad etiladi — ma'lumot jim ustiga yozilmaydi).
  - `finance` servisi va 22 ta command (`get_home`, `create_income`, `accept_share`, `withdraw`, `get_audit`, `finish_audit`, `get_whose_money`, `add_obligation`, `pay_debt` va boshqalar). Har command yupqa; biznes mantiq `finance` da.
  - DTO: pul — `minor` (satr) va tayyor `formatted`; «Kimning puli?» bo'laklari `shareBp` bilan (kenglikni backend hisoblaydi).
  - `ApiError`: `Locked`, `DatabaseWithoutKey`, `Rule { rule }` (domen kodi).
- UI:
  - Tez daromad (`Ctrl+N`): summa → Enter → «Shundan X so'm — kelajagingiz uchun» → Enter bilan ajratish. Taklif matni (`formatted`) qayta kiritiladi.
  - «Daromad» sahifasi (shu oy), bosh sahifa KPI kartalari («O'zingizga to'langan», «Kelajagim» balansi, «Oy yakuni», odat, audit holati).
  - «Kelajagim»: balans, odat, progressiv taklif, ulush qoidasi (5 % / 10 % / oylik summa), boshlang'ich balans (bir marta), pul olish (sabab majburiy, 5 soniya o'ylash pauzasi, PIN har safar), tarix.
  - Oylik audit ustasi (4 qadam): daromad va majburiyatlar, xarajat yozish, izohsiz summani «mayda kundalik» deb belgilash, yakunlash (hisobot o'zgarmas saqlanadi). Klaviatura bilan bajariladi: birinchi boshqaruv fokusda, Enter tasdiqlaydi, Esc orqaga.
  - «Kimning puli?»: oy bo'yicha o'tish, egalar bo'yicha bo'laklar.
  - «Majburiyatlar va nasiya»: doimiy to'lovlar (qo'shish, o'chirish), nasiya (qo'shish, qisman to'lash, qoldiq).
  - i18n: uz va ru; xato kodlari `errors.*` orqali matnga aylanadi.

**Qarorlar va sabablar**

- **Yozuvlarda kalendar sanasi, vaqt emas.** Odat va audit kun darajasida hisoblanadi; Toshkent vaqti (UTC+5) konvertatsiyasi unit testda. Mobil ilova instant saqlaydi — natija bir xil, chunki hafta chegarasi kun darajasida.
- **Ulush taklifi:** foiz bo'yicha `percent_of`, so'ng 1 000 so'mgacha (kichik summada — butun so'mgacha) yuqoriga, daromaddan oshmaydi. Mobil `suggestShare` bilan bir xil; `income_share.json` bilan tasdiqlangan.
- **Pul olish: har safar PIN.** Mobildagi 1 daqiqalik PIN ruxsat tokeni o'rniga, PIN buyruqning o'zida qayta tekshiriladi (noto'g'ri urinish `security` da hisoblanadi). Soddaroq va xavfsizroq; tasdiq kerak (OPEN_QUESTIONS, 25-band).
- **Oy yakuni** = `daromad − (yozilmagan majburiyat + xarajat + sof jamg'arma)`. Mobil ta'rifi bilan bir xil, izohsiz summa bilan bir xil formula (OPEN_QUESTIONS, 28-band).
- **Xarajat kanali:** `expenses.channel` ustuni majburiy, domen modelida kanal yo'q — hozircha `CASH`. D6 da qo'shiladi (OPEN_QUESTIONS, 23-band).
- **Bitta xonadon, bitta egasi a'zo («O'zim»).** Oilaviy rejim (2+ a'zo) D6 da (OPEN_QUESTIONS, 24-band).
- **ID — UUIDv7** (`uuid` crate, ADR: `uuid` v7; `fast-rng` tasodifiy qism uchun). `time` (formatting, parsing, macros) va `thiserror` src-tauri'ga qo'shildi — ikkalasi ham ish joyida allaqachon bor.
- **`zeroize`** storage crate'ga to'g'ridan-to'g'ri bog'landi (`PRAGMA key` satrini tozalash); versiya `security` bilan bir xil.
- **Sxema v2 — faqat qo'shish.** Eski v1 migratsiyasi o'zgartirilmadi; yangi ustunlar `DEFAULT` yoki `NULL` bilan.
- Testlar uchun `security` temp papkalari endi tugagach o'chiriladi (D3 da qolib ketgan).

**Natijalar**

- `cargo test --workspace`: 148 ta test — yashil. D4 ga oid: `baraka-money` (parse, ceil), `baraka-domain` (calendar, habit, share, vault, ledger, debt va boshqalar), `baraka-vectors` (8 suite), `baraka-storage` (v1→v2 migratsiya, daromad → ulush bog'liqligi, cheklovlar, hisobot bir marta), `baraka-daftari` (oqimlar: daromad → ulush → balans, pul olish, ro'molcha, audit).
- `cargo clippy --workspace --all-targets -D warnings`, `cargo fmt --check` — toza.
- Frontend: `pnpm test` 22 ta — yashil (ilova qobig'i, xavfsizlik, tez daromad, pul olish pauzasi va PIN, audit klaviatura oqimi, «Kimning puli?» bo'laklari, bosh sahifa). `lint`, `typecheck`, `format:check` — toza.
- Haqiqiy ilovada qo'lda sinov (ishlab chiqish rejimi, ekran suratlari bilan):
  - sozlash → bosh sahifa;
  - `Ctrl+N`: 150 000 → taklif 8 000 → Enter bilan ajratish → bosh sahifada «O'zingizga to'langan» 8 000, «Kelajagim» 8 000, «Oy yakuni» 142 000, odat 1 hafta;
  - «Kelajagim»: ro'molcha 100 000 (kartochka yo'qoladi, bir marta); pul olish — noto'g'ri PIN xabari va maydon tozalanishi, so'ng to'g'ri PIN bilan 30 000 «Dori» tarixda;
  - audit: klaviatura bilan 4 qadam (Enter, Enter, Tab-Enter, Enter), «Ijara» 5 000 yozildi, yakunlandi — «Audit yakunlangan» holati;
  - «Kimning puli?» — izohsiz bo'lak; «Majburiyatlar va nasiya»: nasiya 200 000 qo'shildi, 50 000 to'landi — qoldiq 150 000;
  - ruscha til: bosh sahifa va yon panel to'g'ri ko'rinadi.

**Ma'lum cheklovlar**

- Audit izohsiz summa bilan yakunlanishi mumkin (majburiy tanlov yo'q) — OPEN_QUESTIONS, 22-band.
- Pul olish va boshqa yozuvlarning qayta ishga tushirishdan keyingi saqlanishi D4 da alohida tekshirilmadi (baza D3 da sinalgan).
- Oylik kun (`month_start_day`) sozlamasi UI'da yo'q; standart — 1.
- Nasiya minimal: foiz, tilxat va friction D9 da.
- Daromad `source_type` (TER/MOL/TAVAKKAL/RIBO) ustuni ishlatilmaydi — ribo filtri D8 da.

### D3 — Xavfsizlik va shifrlangan baza (2026-10-14)

**Qo'shildi**

- `crates/domain` (paket `baraka-domain`): `Household`, `Member`, `MemberRole` (ADULT/CHILD), `Meta` (yaratilgan/yangilangan/o'chirilgan vaqt, `version`, `origin_device_id`), `validate_name`, `validate_uuid_v7`, `Clock` va `IdGen` traitlari.
- `crates/security` (paket `baraka-security`):
  - 6 raqamli PIN. Baza kaliti tasodifiy 256 bit; u ikki qatlamda o'raladi: ichki qatlam PIN'dan Argon2id bilan (19 MiB, t=2, p=1), tashqi qatlam OS keyring'idagi qurilma kaliti bilan. Ikkala qatlam XChaCha20-Poly1305.
  - Kalit fayli `keys.bin` (208 bayt, `BDKEY001`), atomik yoziladi.
  - Lockout: 3-urinishdan keyin 30 s, 4 — 60 s, 5 — 5 daqiqa, 6 — 15 daqiqa, 7 va undan keyin 1 soat. Keyring kaliti yo'q bo'lsa, urinish hisoblanmaydi.
  - `AutoLockPolicy`: oyna fokusdan tushib 5 daqiqa o'tsa, qulflash.
- `crates/storage` (paket `baraka-storage`): SQLCipher bilan shifrlangan baza (`PRAGMA key` 256 bit hex). Sxema v1 — `rusqlite_migration` bilan (`user_version`), 11 ta `STRICT` jadval, CHECK cheklovlari (masalan, `WITHDRAWAL` uchun sabab majburiy). `HouseholdRepo`, `MemberRepo` — mantiqiy o'chirish va optimistik versiya nazorati. Vaqt — RFC 3339, UTC.
- `src-tauri`:
  - `session` moduli: qulflangan/ochiq holat, PIN bilan ochish, qulflash, avto-qulflash. Tauri'dan mustaqil.
  - Commandlar: `get_security_status`, `setup_pin`, `unlock`, `lock`. Xato — `ApiError` (`code`, `retryAfterSeconds`); PIN yoki kalit qiymati hech qachon xatoda yoki logda bo'lmaydi.
  - Relizda oyna ekran suratidan chiqariladi (`set_content_protected`). Ishlab chiqish rejimida o'chiq.
  - Ma'lumotlar papkasi: `%APPDATA%\uz.barakadaftari.desktop` (`keys.bin`, `daftar.db`).
- UI: `SecurityGate` (avval PIN sozlash, keyin qulflash, keyin ilova), `SetupScreen` (PIN ikki marta kiritiladi), `LockScreen` (Enter bilan yuboriladi, noto'g'ri PIN xabari, lockout sanog'i), yon paneldagi «Qulflash» tugmasi va `Ctrl+L`. Tarjimalar uz va ru'da. Yangi rang tokeni `--color-danger`.

**Qarorlar va sabablar**

- **Ikki qatlamli o'rash** (DESKTOP_PROMPT.md 6.2): faqat PIN ham, faqat keyring ham yetarli emas. Keyring yozuvi o'chirilsa, PIN to'g'ri bo'lsa ham baza ochilmaydi.
- **Tartib:** format → lockout → keyring → PIN. Keyring kaliti yo'q bo'lsa, bu tizim xatosi: PIN tekshirilmaydi va urinish hisoblanmaydi.
- **Keyring nomi:** xizmat `BarakaDaftari`, hisob `db-device-key-v1` (Windows'da `db-device-key-v1.BarakaDaftari`).
- **`retryAfterSeconds` — `u32`:** specta TypeScript'da 64-bitli butun sonlarni (`bigint`) taqiqlaydi. Kutish bir soatgacha bo'lgani uchun u sig'adi.
- **Commandlar `async`:** Argon2id (bir necha yuz millisekund) UI oqimini bloklamasligi uchun `spawn_blocking` ichida bajariladi.
- **Sozlash bazani ochadi:** PIN kiritilgach yangi o'rnatishda ilova darhol ochiladi.
- **Ekran surati:** Windows bu oynani ekran suratidan chiqarib tashlaydi (`WDA_EXCLUDEFROMCAPTURE`, affinity `0x11`). Qora to'rtburchak chiqmaydi — oyna ortidagi oyna ko'rinadi. Eski Windows'da xulq boshqacha bo'lishi mumkin (tekshirilmagan).
- **Windows'da SQLCipher'ni yig'ish** to'liq Perl'ni talab qiladi (OpenSSL Configure). Git bilan kelgan perl yetmaydi; `OPENSSL_SRC_PERL` bilan ko'rsatiladi (README).

**Bog'liqliklar va sabablari** (ADR bo'yicha, DESKTOP_PROMPT.md 2-bo'lim)

- `argon2` 0.6 — PIN'dan kalit (Argon2id).
- `chacha20poly1305` 0.11 — AEAD (XChaCha20-Poly1305), `zeroize` xususiyati bilan.
- `keyring` 4.2 — OS xavfsiz saqlash (Windows Credential Manager).
- `rand` 0.10 — tasodifiy sonlar (OS manbai).
- `zeroize` 1.9 — kalit xotirasini tozalash (`security` va `storage`).
- `rusqlite` 0.40, `bundled-sqlcipher-vendored-openssl` — SQLCipher; `rusqlite_migration` 2.6 — migratsiyalar.
- `time` 0.3, `thiserror` 2 — vaqt va xatolar (`src-tauri` ham `thiserror` ishlatadi).
- Ichki bog'liqliklar: `src-tauri` → `baraka-security`, `baraka-storage`.

**Natijalar**

- `cargo test --workspace`: yashil. D3 testlari: `baraka-domain` 5; `baraka-security` 15 (unit) + 9 (integratsiya: PIN+keyring ikki qatlam, keyring yo'qolganda PIN yetmasligi, lockout, avto-qulflash); `baraka-storage` 8 (shifrlangan fayl kalitsiz o'qilmaydi, noto'g'ri kalit rad etiladi, migratsiya v1, versiya nomuvofiqligi, tashqi kalit, CHECK); `baraka-daftari` 12 (seans 7, commandlar 4, bindinglar 1).
- `cargo clippy --workspace --all-targets -D warnings`, `cargo fmt --check` — toza.
- Frontend: `pnpm test` 17 ta — yashil (App 5, xavfsizlik oqimlari 6, ikonka siyosati, tarjima kalitlari); `lint`, `typecheck`, `format:check` — toza.
- Haqiqiy ilovada qo'lda sinov (ishlab chiqish rejimi, sichqoncha va klaviatura, har bir ekran suratga olingan):
  - sozlash: PIN ikki marta, «Saqlash va boshlash» — bosh sahifa ochildi;
  - «Qulflash» tugmasi va `Ctrl+L` — qulflash ekrani;
  - noto'g'ri PIN — xabar, maydon tozalanadi, ilova qulflangan qoladi;
  - uchinchi noto'g'ri urinish — 30 soniyalik kutish, sanoq, maydon va tugma o'chiq; sanoq tugagach maydon qayta yoqildi;
  - to'g'ri PIN — ilova ochildi;
  - oyna 5 daqiqa fokusdan tashqarida (minimallashtirilgan) — qayta ochilganda qulflash ekrani;
  - ilova qayta ishga tushirildi — qulflash ekrani (kalit fayli va keyring saqlangan), to'g'ri PIN bilan ochildi;
  - keyring yozuvi Windows Credential Manager'dan o'chirildi — to'g'ri PIN ham ochmadi: «Qurilma kaliti topilmadi» xabari.
- Reliz exe (`target\release`, o'rnatilmagan): ekran surati oyna mazmunini chiqarmadi (yuqoridagi qaror).

**Ma'lum cheklovlar**

- PIN unutilsa, ma'lumotlarni tiklash yo'q (docs/OPEN_QUESTIONS.md, 15-band).
- Windows Hello yo'q (kechiktirildi, 16-band). OS qulflash hodisasi (Win+L, uyqu) aniqlanmaydi, faqat oyna fokusi va vaqt (17-band).
- PIN JS tomonida qisqa vaqt matn sifatida turadi; Rust tomonda `zeroize` qilinmaydi (Tauri deserializatsiyasi `String` beradi).
- Kalit fayli o'chirilib, `daftar.db` qolsa, sozlash eski bazani ochishga urinadi va `INTERNAL` xato beradi (18-band).
- O'rnatuvchi (NSIS) bu vazifada qayta qurilmadi va o'rnatilmadi; silent o'rnatish va o'chirish sinalmagan (19-band).

### D2 — `money` crate va test vektorlari runner'i (2026-10-14)

**Qo'shildi**

- `crates/money` (paket `baraka-money`, kodda `money`):
  - `Money` — butun minor birliklar (tiyin, sent) va valyuta; `checked_add`/`checked_sub` valyuta aralashuvini va chegaradan oshishni xato bilan qaytaradi.
  - `Currency` — UZS, USD, EUR, RUB; minor birlik ikki xonali.
  - `round_half_up_div` — loyihadagi yagona yaxlitlash joyi (yarmi noldan uzoqqa).
  - `allocate` — largest remainder usuli: qismlar yig'indisi aniq teng, teng kasrda kichik indeks ustun, manfiy summa simmetrik.
  - `percent_of` — basis points (1 % = 100 bp) bo'yicha foiz.
  - `FxRate` + `convert` — kurs kasr sifatida (`rate_num / rate_den`), yarmi noldan uzoqqa yaxlitlanadi.
  - `format_money` — `uz` va `ru` lokallari: guruhlash bo'linmas bo'sh joy bilan, kasr faqat tiyin nolga teng bo'lmasa, `soʻm` (U+02BB) / `сум`, `$`, `€`, `₽`.
  - `MoneyError::code()` — barqaror kodlar (`CURRENCY_MISMATCH`, `OVERFLOW` va hokazo).
- `crates/vectors` (paket `baraka-vectors`, kodda `vectors`):
  - suite yuklovchi: `spec/test-vectors/*.json` ni o'qiydi;
  - pul runner'lari: `allocate` (5 ta), `percent_of` (2 ta), `fx_convert` (5 ta), `money_format` (8 ta) — jami 20 ta vektor. Har bir natija `expected` bilan TO'LIQ solishtiriladi;
  - qoplanmagan vektor fayli bo'lsa, `har_bir_vektor_fayli_runner_bilan_qoplangan` testi qizil bo'ladi.
- `spec/test-vectors/` — to'rtta D2 suite (`allocate`, `percent_of`, `fx_convert`, `money_format`) mobil repo'dagi fayllarning bayt-bayt nusxasi (sha256 mos).
- Xususiyat testlari (proptest, har biri 256 ta tasodifiy holat): taqsimot yig'indisi aniq teng; ishora saqlanadi; har bir qism aniq ulushdan bir minor birlikdan ko'p og'maydi; nisbati nol bo'lgan qism nolga teng; `percent_of` = `allocate([bp, 10000 − bp])[0]`; yaxlitlash simmetrik.
- CI: alohida «Pul vektorlari» qadami va `coverage` job (`baraka-money` qamrovi ≥ 95 %).
- README: tekshiruv buyruqlari va qamrov o'lchash.

**Natijalar**

- Testlar: 32 ta unit, 6 ta xususiyat, 5 ta runner — hammasi o'tdi.
- Qamrov: `baraka-money` satrlari 99,80 % (talab ≥ 95 %).
- Mutatsiya sinovi: tie-break qoidasi ataylab buzildi — `alloc-001`, `alloc-003`, `alloc-004` qizil bo'ldi. Qoida qaytarilgach, hammasi yana yashil.
- `cargo fmt --check`, `clippy -D warnings`, Prettier — toza.

**Qarorlar va sabablar**

- **Yaxlitlash — yarmi noldan uzoqqa, manfiy uchun ham.** Vektor `fx-004` talab qiladi: −12 650,5 → −12 651. Mobil `MoneyRounding.defaultMode` bilan bir xil.
- **Manfiy summa.** `allocate` modulni taqsimlaydi va ishorani qo'yadi (`dist-003`: −300 000 000 kapital bo'yicha → −225 000 000 / −75 000 000).
- **`percent_of` oraliqdan tashqarida** (masalan, 120 % ustama): `round_half_up(amount × bp / 10 000)`. Desktop spec'da bu holat yo'q; mobil ilova xuddi shunday qiladi. 0..=10 000 oralig'ida ikkala ta'rif teng — xususiyat testi buni tasdiqlaydi.
- **Vektorlar nusxasi.** Ikki repo bitta vektor to'plamini ishlatadi (DESKTOP_PROMPT.md 5.1). Hozircha nusxa; sinxronlash usuli ochiq (docs/OPEN_QUESTIONS.md, 2-band).
- **Bog'liqlik yo'nalishi.** `money` vektorlarga bog'lanmaydi; runner `vectors` da. Shu sababli tsikl va ikki nusxadagi tiplar yo'q.
- **Yangi crate'lar** (ADR bo'yicha sabablari): `thiserror` — xatolar (ADR: xatolar); `time` — `FxRate.date` kurs sanasi (ADR: sana); `proptest` — xususiyat testlari (ADR: testlar); `serde`, `serde_json` — vektor JSON'ini o'qish (faqat `vectors`).
- **Vositalar.** `cargo-llvm-cov` — qamrov o'lchash (bog'liqlik emas, CI'da o'rnatiladi).

**Hali yo'q (keyingi bosqichlar)**

- Kiritilgan matnni summaga aylantirish (`MoneyParser`) — D4 (forma kiritish) da.
- `Money` DTO (`{ minor: string, currency, formatted }`) — `src-tauri` commandlarida, D4 da.
- Qolgan 10 ta vektor suite'i (`amortization`, `personal_inflation`, `emergency_target`, `readiness_gate`, `journal_chain`, `profit_spike`, `profit_distribution`, `agreement_completeness`, `debt_recovery_split`, `unexplained_gap`) — mos vazifalarda runner bilan birga qo'shiladi.
- CODEOWNERS — vektor o'zgarishi ikki platforma egasining ma'qulligini talab qiladi (DESKTOP_PROMPT.md 5.4); egalar aniqlangach.

### D1 — Workspace, Tauri skeleti, CI (2026-10-14)

**Qo'shildi**

- Cargo workspace (Rust 1.97.1, `rust-toolchain.toml`) va pnpm workspace (pnpm 12.11.2, Node 24).
- Tauri 2.12 ilova skeleti (`src-tauri/`): asosiy oyna, `get_app_info` command, NSIS o'rnatuvchisi (`currentUser` — administrator huquqi shart emas).
- TypeScript bindinglari tauri-specta orqali (`ui/src/bindings/bindings.ts`). `cargo test` va debug ishga tushirish ularni yangilaydi; CI farqni tekshiradi.
- React 19 + TypeScript (strict) + Vite 8 + Tailwind CSS 4 + Radix UI (ToggleGroup, Tooltip) + i18next (`uz` asosiy, `ru`).
- Qorong'i tema (Claude Code desktop uslubi). Noto Sans shrifti ilova ichida — `ʻ` (U+02BB) va `ʼ` (U+02BC) belgilari to'g'ri chiqadi.
- Navigatsiya: 11 ta bo'lim. Tayyori ikkita — «Bosh sahifa» va «Sozlamalar». Qolganlari o'chirilgan, sababi (keyingi bosqichda qo'shiladi) tooltip'da ko'rsatiladi.
- Ilova ikonkasi: `scripts/make_icon.py` (Pillow) — krem «daftar» va geometrik sakkiz burchakli yulduz. 16–256 px uchun alohida chiziladi.
- Xavfsizlik: qat'iy CSP (`script-src 'self'`, tashqi manba yo'q), minimal capabilities (`core:default` va faqat `allow-get-app-info`), release'da DevTools yo'q.
- Testlar: Rust — 3 ta (JSON kontrakt, yig'ish profili, bindinglar). Frontend — 11 ta (ilova qobig'i, tooltip, til almashinuvi, xato holati, tarjima kalitlari bir xilligi, ikonka siyosati).
- CI (`.github/workflows/ci.yml`): frontend (format, lint, typecheck, test); Rust — Windows, macOS, Ubuntu (fmt, clippy `-D warnings`, test, bindinglar farqi); Windows NSIS build (artifact).
- Hujjatlar: `docs/SPEC.md`, `docs/DESKTOP_PROMPT.md`, `docs/MVP_PLAN.md`, `CLAUDE.md`, `README.md`, `docs/CHANGELOG.md`, `docs/OPEN_QUESTIONS.md`.

**Qarorlar va sabablar**

- **Tauri 2.12** (ADR). Tauri 3 alpha ishlatilmaydi.
- **TypeScript 6.0.3**, 7.0 emas: TypeScript 7 `typescript-eslint` bilan mos emas.
- **ESLint 10**, `eslint-plugin-jsx-a11y`siz: a11y plagini ESLint 10 bilan mos emas. A11y tekshiruvi Testing Library'ning rol bo'yicha so'rovlari orqali.
- **`common-controls-v6` o'chirildi** (`default-features = false`): test binary'lari `STATUS_ENTRYPOINT_NOT_FOUND` bilan yiqilardi. Ilova binary'si manifestni baribir oladi.
- **`style-src 'unsafe-inline'`**: Radix va popper komponentlari inline uslub qo'yadi. `script-src` qat'iy.
- **NSIS tillari**: `Uzbek`, `Russian`, `English`. NSIS 3.11 da `Uzbek.nlf` bor.
- **pnpm 12 minimal chiqarilish yoshi**: yangi chiqqan ikki paket (`lucide-react@1.56.0`, `@testing-library/user-event@14.6.8`) istisnoga qo'shildi (`pnpm-workspace.yaml`). Keyinroq tekshiriladi (docs/OPEN_QUESTIONS.md, 8-band).
- **Ikonkalarda** odam, hayvon, cho'chqa, qimor, alkogol, bank binosi va foiz belgisi ishlatilmaydi. Taqiq `icon-policy.test.ts` da tekshiriladi.

**Bog'liqliklar va sabablari**

- Rust: `tauri` 2.12, `tauri-build` (ilova build skripti), `tauri-specta` + `specta` (`=2.0.0-rc.25`, TS bindinglari — ADR), `specta-typescript` 0.0.12 (bindinglarni yozish), `serde` (DTO), `tracing` + `tracing-subscriber` (log — ADR), `serde_json` (faqat testlar).
- npm: `react`, `react-dom` 19 (ADR: React 18+); `vite` 8, `@vitejs/plugin-react`; `typescript` 6.0 (strict); `tailwindcss` 4 + `@tailwindcss/vite`; `@radix-ui/react-toggle-group`, `@radix-ui/react-tooltip` (ADR: Radix primitivlari); `i18next`, `react-i18next` (ADR); `@tanstack/react-query` (ADR); `zustand` (ADR: faqat UI holati); `@tauri-apps/api` (bindinglar uchun) va `@tauri-apps/cli` (ADR: Tauri); `lucide-react` (ikonkalar — ADR'da yo'q, qo'shildi, ikonka siyosati bilan); `@fontsource-variable/noto-sans` (shrift ilova ichida); `vitest`, `jsdom`, `@testing-library/*`; `eslint`, `typescript-eslint`, `eslint-plugin-react-hooks`, `globals`, `@eslint/js`; `prettier` (ADR).
- Python (faqat ikonka uchun): `Pillow`.

**Ma'lum cheklovlar**

- GitHub Actions CI hali GitHub'da ishga tushirilmagan: repo'da push qilinmagan. Uning qadamlari mahalliy Windows muhitida qo'lda takrorlangan.
- O'rnatuvchi kod imzolanmagan — SmartScreen ogohlantirishi chiqishi mumkin.
- Silent o'rnatish sinalgan (`/S`). Interaktiv o'rnatish va til tanlovi oynasi qo'lda sinalmagan.
- Haqiqiy oynada til almashinuvi tugmasi sichqoncha avtomatizatsiyasi bilan to'liq tasdiqlanmadi. Bu jsdom testlari bilan qoplangan; E2E (WebDriver) keyingi bosqichda.
- Mobil (Flutter) loyiha bu repo'da yo'q; `spec/test-vectors/` faqat to'rtta D2 suite'iga ega (docs/OPEN_QUESTIONS.md, 1–2-bandlar).
