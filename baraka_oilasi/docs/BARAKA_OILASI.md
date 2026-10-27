# «BARAKA OILASI» — BOSH LOYIHA PROMPTI
### Uy · Musofir · Kasb-kor — bitta Rust yadro · Android (Flutter + Kotlin) · Desktop (Tauri 2 + React)

> Versiya: v1.0 · AI-dasturchi (Claude Code va h.k.) uchun asosiy hujjat.
> Bu hujjat uchta mahsulotni bitta texnik platformada birlashtiradi va **barcha texnik masalalarda ustun** turadi.
> Arxitektura qarori: `docs/adr/0001-umumiy-rust-yadro.md`.

---

## 0. HUJJAT HAQIDA

### 0.1. Hujjatlar xaritasi
| Fayl | Nima uchun | Holat |
|---|---|---|
| `docs/BARAKA_OILASI.md` | **Shu fayl.** Stek, arxitektura, pul algoritmlari, xavfsizlik, ish rejasi | asosiy |
| `docs/uy/SPEC.md` | Uy makoni mahsulot spetsifikatsiyasi, 1–6-tamoyillar (= `FINTECH_PROMPT.md` v0.8) | amalda, 4-bo'limdan tashqari |
| `docs/uy/MVP_PLAN.md` | Uy makoni vazifalarining **funksional** mazmuni va qabul mezonlari | amalda, texnik qismlaridan tashqari |
| `docs/uy/DESKTOP_PROMPT.md` | Desktop UX (7-bo'lim), test vektorlari (5-bo'lim), desktop vazifalari | qisman amalda (Ilova A) |
| `docs/kasbkor/SPEC.md` | Kasb-kor makoni spetsifikatsiyasi | **K0 vazifasida yoziladi** |
| `docs/musofir/SPEC.md` | Musofir makoni spetsifikatsiyasi | v1.0 — tasdiqlangan (2026-10-19); M1–M4 amalga oshirilgan |
| `docs/OPEN_QUESTIONS.md` | Ochiq savollar: mahsulot egasi, ulamo, yurist | jonli hujjat |
| `docs/adr/` | Arxitektura qarorlari | jonli |
| `docs/CHANGELOG.md` | Har vazifadan keyin yangilanadi | jonli |

### 0.2. Ustunlik tartibi (zid kelganda)
1. **Texnik masalalar** (stek, arxitektura, pul algoritmlari, jurnal, xavfsizlik, saqlash, almashish) → **shu fayl**, keyin ADR'lar.
2. **Mahsulot, diniy-moliyaviy qoidalar va ohang** → tegishli makonning `SPEC.md` fayli.
3. **Vazifaning funksional mazmuni** → `docs/uy/MVP_PLAN.md` va `docs/uy/DESKTOP_PROMPT.md` dagi tegishli vazifa. Ulardagi texnik ko'rsatmalar (Drift, Dart `core/money`, `pdf` paketi, alohida `crates/` papkasi) **bekor** va shu fayl bilan almashtiriladi (Ilova A).
4. Hal qilinmagan masala → `docs/OPEN_QUESTIONS.md`. **Taxmin qilinmaydi.**

---

## 1. ROL
Sen — senior Rust dasturchisan, Flutter (Dart) va React (TypeScript) bilan ham chuqur ishlaysan, Android (Kotlin) platformasini bilasan. Amaliy kriptografiya va moliyaviy dasturiy ta'minot bo'yicha tajribang bor. Kodni production-sifatda, testlar bilan yozasan. **Pul hisobining aniqligi, foydalanuvchi ma'lumotlarining maxfiyligi va ishonch** birinchi o'rinda turadi.

---

## 2. LOYIHA MOHIYATI VA MAHSULOT OILASI

### 2.1. Bitta g'oya
> **Odamni pulini, qarzini va kelishuvlarini yozishga o'rgatib, halol (ribosiz) moliyaviy odatlar orqali o'z hayotini o'zi boshqaradigan qilish.**

Yadro so'z — **«yoz»**: yozilgan narsa ko'rinadi, ko'ringan narsa boshqariladi, yozilgan kelishuv ishonchni asraydi. Tamoyil: «Ilm o'qiganniki emas, amal qilganniki». Yo'l ko'rsatuvchi ovoz — **Moliyaviy maslahatchi** (ismsiz, personaj emas): iliq, ayblamaydi, savol beradi.

Har bir funksiya ikki savol bilan tekshiriladi: **(1) odamni amalga undayaptimi? (2) ishonchni asrayaptimi?**

#### Ilova nomi, ilhom manbasi va mustaqillik (mahsulot egasi qarori, 2026-10-23)
- Android va desktop ilovalarining nomi — **«Baraka Dastur»**. Google Play'da «Baraka» nomli boshqa ilova bor; «Baraka daftari» nomi ham ishlatilmaydi. Loyiha va repozitoriy ichki nomi — «Baraka oilasi».
- G'oya halol boylik haqidagi «qonunlar» suhbatlari turkumining **ma'no-mazmunidan ilhomlangan**. Ilova ularning moslashuvi yoki rasmiy davomi **emas**: boshqa mualliflarning matnlari, personajlari va brendi ishlatilmaydi; ilovadagi barcha matnlar — o'zimiz yozganlari.
- Ilova o'sha suhbatlar mualliflari va ularning tashkiloti bilan **bog'liq emas**, ular tomonidan tasdiqlanmagan va ularning nomidan gapirmaydi; litsenziyaga tayanilmaydi.
- **Nomlar repoda yo'q** (mahsulot egasi qarori, 2026-10-27): suhbatlar mualliflari, ularning tashkiloti va qissa personajlarining nomlari kodda, hujjatlarda, testlarda, vektorlarda va commit xabarlarida yozilmaydi. Yangi qonun kelganda faqat uning ma'no-mazmuni o'z so'zlarimiz bilan tamoyil sifatida qo'shiladi.
- Hujjatlarda «qonun» o'rniga **«tamoyil»** ishlatiladi: 8 tamoyil — ribosiz moliyaning keng ma'lum asoslari (o'zingizga avval to'lash, xarajatni yozish, qarzdan reja bilan chiqish, halol sheriklik, kelishuvni yozish, o'zingizga — bilim va malakaga sarmoya qilish va h.k.).
- Ilova ichidagi yo'l ko'rsatuvchi ovoz — **«Moliyaviy maslahatchi»**: ismsiz, personaj emas. Segment personalari (taksichi, tikuvchi, migrant va h.k.) — o'zimizning mahsulot tahlilimiz.

### 2.2. Uchta makon (bitta ilova ichida)
Android va desktopda **bitta «Baraka Dastur» ilovasi** bo'ladi. Ilova ichida uchta **makon** (`SpaceKind`) bor. Foydalanuvchi onboarding'da o'ziga keraklisini yoqadi. Makonlar orasidagi chegara — 1-tamoyilning («ikki cho'ntak») o'zi.

| Makon | `SpaceKind` | Kim uchun | Asosiy tashxis | Spetsifikatsiya |
|---|---|---|---|---|
| **Uy** | `UY` | O'rta qatlam oila | «Ko'p ishlaydi, oy oxirida pul qolmaydi» | `docs/uy/SPEC.md` ✅ |
| **Kasb-kor** | `KASBKOR` | O'zini o'zi band qilganlar, kichik va o'rta biznes | «Aylanma bor, egasi boyimaydi»: cho'ntak bitta, foyda aslida maosh, kapitalni inflyatsiya yeydi, nasiya yig'ilmaydi | `docs/kasbkor/SPEC.md` (K0) |
| **Musofir** | `MUSOFIR` | Chet elda ishlaydigan migrant va uning uydagi oilasi | «Yillar ishlaydi, qaytganda qo'lida hech narsa yo'q»: hammasi uyga ketadi, kelishuv og'zaki, qaytishda «kalxatlar» | `docs/musofir/SPEC.md` (M0) |

#### Kasb-kor — qisqa karta (K0 uchun manba)
- **8 tamoyil:** (1) Ikki cho'ntak — biznes puli omonat, egasiga qat'iy maosh; (2) Haqiqiy foydani bil — o'z mehnati, eskirish va oilaviy mehnat tannarxda; (3) Tovar ham pul, u ham yotadi — taqsimot qoidasi, qayta tiklash narxi, muzlagan tovar; (4) Nasiyani adolat bilan yurit — narx kelishuvda qotiriladi, kechikish uchun ustama yo'q; (5) Kengayishga reja bilan chiq — kengayish darvozasi, foizli kreditga halol muqobil; (6) Kelishuvni yozing — sherik, xodim, yetkazib beruvchi, mijoz; (7) Tarozingni to'g'ri tut — halol o'lchov, soliq zaxirasi, savdo mollari zakoti; (8) O'zingizga sarmoya qiling — egasining soat qiymati, «o'zim qilaymi yoki o'rgatib topshiraymi?» (K9).
- **Odat ritmi:** har kuni kassa yopish (5 daqiqa) → har hafta nasiya ko'rigi → har oy «Hisob kuni» → har yil inventarizatsiya va zakot.
- **Bosh ekrandagi 1-raqam:** «Haqiqiy foyda (shu oy)», 2-raqam: «Egasiga to'langan maosh».
- **Personajlar:** Feruza (atelye), Bahodir aka (mahalla do'koni), Jasur (usta), Malika (Instagram do'kon), aka-uka choyxonasi. Maslahat ovozi — moliyaviy maslahatchi.
- **EMAS:** ERP, buxgalteriya yoki 1C o'rnini bosuvchi, onlayn kassa (fiskal), soliq hisobotini topshiruvchi, «ikkinchi daftar» (daromadni yashirish vositasi), kredit yoki investor bozori.

#### Musofir — qisqa karta (M0 uchun manba)
- **Tamoyillar:** o'z ulushi (uyga yuborilmaydigan «qaytish jamg'armasi»); chet eldagi xarajatlar; valyutada saqlanish va zaxira pul; yo'l qarzidan chiqish; qaytgandan keyingi ish rejasi; **oila bilan pul kelishuvi** («Ikki qirg'oq»: har bir o'tkazmaning maqsadi, uyda shu maqsad bo'yicha xarajat yoziladi); **sovutish davri** (katta pul bilan qaytgandan keyin 90 kun katta qarorlar uchun tekshiruv) — bu `docs/uy/SPEC.md` 10-bo'limdagi 7-tamoyil ishorasining amaliy ko'rinishi; **o'zingizga sarmoya** (soat qiymati ish valyutasida, til va hunar rejasi — M6).
- **EMAS:** pul o'tkazish xizmati, valyuta ayirboshlash, ish topib beruvchi agentlik, o'tkazma kompaniyalari reklamasi.

### 2.3. Butun oila uchun qat'iy mahsulot cheklovlari
`docs/uy/SPEC.md` 3-bo'limidagi barcha cheklovlar **uchala makonga** ham tegishli. Qo'shimcha:
- Ilova **pulni saqlamaydi va o'tkazmaydi**. Tomonlarni bir-biriga tanishtirmaydi, pul yig'maydi (P2P, kraudfanding, marketplace emas).
- Foiz stavkasi hech qayerda «muqobil daromad» sifatida ko'rsatilmaydi (taqiqlangan iboralar linteri — 10.3).
- Ayblash, uyaltirish, qo'rqitish va va'dalar yo'q. Har bir «ogohlantiruvchi» ekran keyingi qadam bilan tugaydi.
- Diniy matnlar va shartnoma shablonlari `reviewStatus = APPROVED` bo'lmasa, release'da ko'rsatilmaydi (shablonlar ogohlantirish bilan ko'rsatiladi).
- Kasb-kor makoni soliq to'lashni halollikning bir qismi sifatida ko'rsatadi va yashirishga undamaydi. «Soliq maslahati emas» disklеymeri bor.
- Har bir ta'limiy ekranda: «Ta'limiy material. Fatvo, moliyaviy, soliq yoki yuridik maslahat emas».

---

## 3. TEXNOLOGIK STEK — QAT'IY QARORLAR (ADR)
> Bu qarorlar o'zgarmaydi. O'zgartirish kerak bo'lsa, avval `docs/adr/` ga yangi ADR loyihasini yozib, ruxsat so'raysan. Yangi crate, Dart paket yoki npm paket qo'shishdan oldin uning nima uchun kerakligini, muqobillarini va litsenziyasini yozasan.

### 3.1. Umumiy yadro — `core/` (Cargo workspace)
| Qatlam | Tanlov |
|---|---|
| Til | **Rust** stable, `rust-toolchain.toml` bilan qotiriladi, edition 2021+ |
| Baza | **SQLite + SQLCipher**: `rusqlite` (`bundled-sqlcipher-vendored-openssl`). Migratsiyalar: `rusqlite_migration` |
| Kripto | `argon2` (Argon2id), `chacha20poly1305` (XChaCha20-Poly1305), `hkdf` + `sha2`, `rand` (`OsRng`), `zeroize` |
| Pul | O'zimizning `money` crate: `i64` minor birlik, oraliq hisob `i128`. `f32`/`f64` pul crate'larida **taqiqlanadi** (`clippy::float_arithmetic = deny`) |
| Sana/vaqt | `time` + `time-tz` (yoki `chrono` + `chrono-tz`, T0 da bittasi tanlanadi): `Asia/Tashkent`, `weekAnchor = FRIDAY` |
| ID | `uuid` v7 |
| Unicode | `unicode-normalization` (kiritishda NFC — 6.4) |
| PDF | **`typst`** + `typst-pdf` (+ snapshot uchun `typst-render`), kutubxona sifatida, shriftlar o'rnatilgan |
| Serializatsiya | `serde`, `serde_json`; JSON Schema — `schemars` |
| Xatolar/log | `thiserror`, `tracing`. Loglarda summa, ism, izoh, telefon raqami **bo'lmaydi** |
| Testlar | `cargo test`, `proptest`, `insta` |
| Codegen va vositalar | **`cargo xtask`** (alohida Rust binari): FRB/specta generatsiyasi, i18n, dizayn tokenlari, vektorlar |

### 3.2. Android — `apps/android/`
| Qatlam | Tanlov |
|---|---|
| UI | **Flutter** stable (`.fvmrc` bilan qotiriladi), Dart 3 |
| State | **Riverpod 2** (`riverpod_generator`). Server-holat = yadrodan keladigan ma'lumot; UI-holat alohida provider'larda |
| Navigatsiya | **go_router** |
| Modellar | `freezed` (faqat UI-holat uchun; domen DTO'lari FRB'dan generatsiya qilinadi) |
| Rust ↔ Dart | **`flutter_rust_bridge` v2**. Qo'lda `dart:ffi` yoki `MethodChannel` taqiqlanadi. Yig'ish: `cargo-ndk` Gradle orqali |
| Kotlin ↔ Dart | **Pigeon** (faqat platforma xizmatlari uchun: Keystore, biometriya, WorkManager, vidjet, `FLAG_SECURE`) |
| Native | **Kotlin**: Android Keystore (StrongBox mavjud bo'lsa), `androidx.biometric` + **`CryptoObject`**, WorkManager, bildirishnomalar, **Jetpack Glance** vidjeti |
| PDF ko'rish/ulashish | `pdfrx` (preview), `share_plus`, `printing` (Android print) — PDF baytlari yadrodan keladi |
| Lint | `very_good_analysis`, `strict-casts`, `strict-raw-types` |
| Testlar | `flutter_test`, `mocktail`, `integration_test`; Kotlin — JUnit |
| Platforma | **minSdk 26**, targetSdk eng so'nggi barqaror. ABI: `arm64-v8a` (asosiy), `armeabi-v7a`. Tarqatish — App Bundle |
| Hajm byudjeti | Play'dan yuklanadigan hajm (arm64) **≤ 40 MB**. CI'da tekshiriladi, oshsa build qizil |

### 3.3. Desktop — `apps/desktop/`
| Qatlam | Tanlov |
|---|---|
| Shell | **Tauri 2** stable. Windows 10/11 x64 — 1-navbat, macOS — 2-navbat, Linux — 3-navbat |
| Frontend | **React 18+**, **TypeScript (strict)**, **Vite**, pnpm |
| UI | Tailwind CSS + Radix UI (yoki shadcn/ui). Standart — dark (Claude Code uslubi), light ixtiyoriy (10.4) |
| State | **TanStack Query** (yadro ma'lumoti), **Zustand** (faqat UI holati) |
| Jadval/grafik | **TanStack Table** (virtualizatsiya), **ECharts** |
| Formalar | `react-hook-form` + `zod` (faqat shakl validatsiyasi; biznes validatsiya — yadroda) |
| i18n | `i18next` (resurslar `shared/i18n` dan generatsiya qilinadi) |
| Rust ↔ TS | **`tauri-specta`**. Qo'lda `invoke('...')` taqiqlanadi |
| Kalit | `keyring` (Windows Credential Manager / macOS Keychain / Secret Service); Windows Hello — `windows` crate, **`KeyCredentialManager`** (7.3) |
| Pluginlar | faqat: `dialog`, `notification`, `global-shortcut`, `updater` (keyinroq). `shell`, `http`, keng `fs` **yoqilmaydi** |
| Testlar | `vitest`, `@testing-library/react`; E2E — `tauri-driver` + WebdriverIO (Windows) |
| Lint | ESLint (strict) + Prettier |
| Paketlash | Windows: **NSIS** (WebView2 bootstrapper ichida), kod imzolash; macOS: DMG (notarization); Linux: AppImage + deb |

### 3.4. Keyingi bosqichlar (oldindan belgilangan, hozir qurilmaydi)
| Qism | Tanlov | Qachon |
|---|---|---|
| Relay server (Musofir «Ikki qirg'oq», Kasb-kor ko'p qurilma) | Rust **axum** + PostgreSQL, **uchdan-uchgacha shifrlangan** bloblar, server O'zbekiston hududida | M0/K8 dagi ADR'dan keyin |
| «Guvoh» qurilmasi | **RP2350 (Pico 2 W)**, `embassy-rp` + `cyw43` (BLE), `money` va `journal` crate'lari `no_std` holida | G0 dan keyin |

### 3.5. Versiya va bog'liqlik siyosati
- Y1 vazifasida har bir asosiy vositaning **eng so'nggi barqaror** versiyasi tanlanadi va qotiriladi: `rust-toolchain.toml`, `.fvmrc`, `Cargo.lock`, `pubspec.lock`, `pnpm-lock.yaml`, `.nvmrc`, Android NDK versiyasi (`apps/android/android/gradle.properties`). Tanlangan versiyalar `docs/adr/0002-versiyalar.md` ga yoziladi.
- RC yoki beta versiya faqat ADR bilan ishlatiladi (masalan, `tauri-specta` barqaror chiqmagan bo'lsa).
- Har bir yangi bog'liqlik uchun: nima uchun kerak, muqobillari, litsenziya (GPL/AGPL taqiqlanadi), oxirgi chiqarilgan sanasi.

---

## 4. ARXITEKTURA

### 4.1. Monorepo tuzilmasi
```
baraka-oilasi/
  rust-toolchain.toml  Cargo.toml (workspace)  .fvmrc  .nvmrc  CLAUDE.md
  core/
    crates/
      money/            no_std: Money, Currency, allocate, percent_of, round, FxRate, format
      journal/          no_std + alloc: JCS, SHA-256, chain, verify
      agreements/       9 savol dvigateli, turlar, validatsiyalar
      domain-uy/        Uy makoni: 1–6-tamoyillar (sof funksiyalar)
      domain-kasbkor/   Kasb-kor makoni (K-vazifalarda)
      domain-musofir/   Musofir makoni (M-vazifalarda)
      domain-common/    Household, Member, Space, Category, Asset, Clock, IdGen traitlari
      storage/          SQLCipher, migratsiyalar, repository'lar, o'zgarish hodisalari
      security/         kalit iyerarxiyasi, slotlar, PIN, lockout, KeyProvider trait
      pdf/              typst World, shablon renderer
      interchange/      .baraka konteyneri, JSON Schema, birlashtirish
      app/              USE-CASE qatlami: domen + storage'ni boshqaradi, DTO qaytaradi
      vectors/          test vektorlari runner'i (dev-dependency)
    bindings/
      flutter/          flutter_rust_bridge API (yupqa adapter → app)
  apps/
    android/            Flutter ilova; android/ — Kotlin (Pigeon xizmatlari)
      lib/ app/ features/<makon>/<feature>/ shared/ bindings/(generatsiya)
    desktop/
      src-tauri/        Tauri: commandlar (yupqa adapter → app), oyna, tray, hotkey
      ui/               React ilova: src/ app/ features/<makon>/<feature>/ components/ bindings/(generatsiya)
  shared/
    i18n/               uz.json uz-Cyrl.overrides.json ru.json (ICU MessageFormat) — yagona manba
    design-tokens/      tokens.json — yagona manba
    pdf/                *.typ shablonlar
    fonts/              Noto Sans / Noto Serif (+ litsenziyalar)
    content/            boblar JSON, reviewStatus bilan
  spec/
    test-vectors/       *.json — oltin vektorlar
    oracle/             oracle.py — mustaqil ma'lumotnoma implementatsiya (12.2)
    interchange/        export-format.schema.json
  xtask/                cargo xtask: codegen, i18n, tokens, vectors, size-check
  firmware/guvoh/       (keyinroq)
  server/relay/         (keyinroq)
  docs/                 (0.1)
  .github/workflows/    (13)
```

### 4.2. Qatlamlar va bog'liqlik qoidalari
```
money, journal            ← hech narsaga bog'liq emas (no_std)
domain-common             ← money
agreements                ← domain-common, money, journal
domain-uy|kasbkor|musofir ← domain-common, agreements, money, journal
storage                   ← domain-* (faqat tiplar), rusqlite
security                  ← kripto crate'lar
pdf, interchange          ← domain-*, money, journal
app                       ← hammasi (yagona orkestrator)
bindings/flutter, src-tauri ← FAQAT app
```
- `money`, `journal`, `agreements`, `domain-*` **sof**: IO, tizim vaqti, tasodifiylik yo'q. `Clock` va `IdGen` trait orqali beriladi. **Barcha biznes qoidalari shu yerda.**
- `app` — use-case'lar (`record_income`, `close_cash_day`, `sign_agreement` …). Tranzaksiya chegarasi, hodisa chiqarish, avtorizatsiya (makon, rol) shu yerda.
- **Adapterlar yupqa:** `bindings/flutter` va `src-tauri` faqat argumentni DTO'dan o'qiydi → `app` ni chaqiradi → DTO qaytaradi. Ularning ichida biznes mantiq bo'lsa — bu xato (review'da rad etiladi). Ikkala adapter bir xil use-case'ni chaqiradi, shuning uchun Android va desktop xulqi bir xil bo'ladi.
- Domen crate'lari bir-birini import qilmaydi. Makonlararo aloqa faqat `app` dagi use-case orqali (4.6).

### 4.3. Frontend qoidalari (Flutter va React uchun bir xil)
- **UI pul hisoblamaydi.** Foiz, ulush, jami, qoldiq — hammasi yadroda. Formadagi summa **string** sifatida yuboriladi va yadroda parse qilinadi.
- DTO'da pul: `{ minor: string, currency: string, formatted: string, plain: string }`. `minor` — JS `number` va Dart `int`ning platformaga bog'liq chegaralaridan himoya uchun string; `plain` — kirish maydoniga o'zgarishsiz qaytariladigan ko'rinish (`40000`, `123,45`): UI taklif qilingan summani hisoblamasdan qayta yuboradi. Foizlar ham yadroda formatlanadi (`format_percent_bp`).
- UI biznes validatsiyani takrorlamaydi: yadro `ValidationError { code, field?, params }` qaytaradi, UI uni i18n kaliti orqali ko'rsatadi.
- Vaqt, sana va hafta chegaralari yadroda hisoblanadi; UI faqat tayyor `LocalDate`/formatlangan qatorni ko'rsatadi.

### 4.4. Oqim, bazaga kirish va hodisalar
- `storage` ichida bitta **yozuvchi ulanish** (writer actor, alohida thread) va o'qish uchun kichik ulanishlar puli. Barcha yozuvlar tranzaksiyada.
- FRB funksiyalari `async` (FRB thread pool'ida), Tauri commandlari `async` (`spawn_blocking`). UI thread hech qachon bloklanmaydi.
- Har bir muvaffaqiyatli yozuvdan keyin `app` **`ChangeEvent { space_id, topics: [..] }`** chiqaradi (broadcast kanal).
  - Android: FRB `StreamSink` → Dart `Stream` → Riverpod provider'lari invalidatsiya qilinadi.
  - Desktop: Tauri event → TanStack Query `invalidateQueries`.
- Xatolar: `thiserror` enum → adapterda **barqaror kod** (`"CURRENCY_MISMATCH"`, `"JOURNAL_IMMUTABLE"` …) + parametrlar. Xato matnida shaxsiy ma'lumot bo'lmaydi.

### 4.5. Makonlar modeli
- `spaces` jadvali: `id`, `kind (UY|KASBKOR|MUSOFIR)`, `name`, `household_id`, `created_at`, … Har bir makon o'z kategoriyalari, aktivlari va jurnallariga ega.
- **Har bir domen jadvalida `space_id`** bor. Repository'lar makon bo'yicha filtrlamasdan so'rov qila olmaydi (API darajasida majburiy parametr).
- Bitta `household_id` ostida bir nechta makon bo'lishi mumkin. Oila a'zolari (`members`) xonadon darajasida, ularning makondagi rollari `space_members` da.
- Shaxsiy (boshqa a'zolarga ko'rinmaydigan) jamg'arma imkoniyati — `docs/OPEN_QUESTIONS.md` (OQ-M2). Qaror chiqmaguncha sxemada `visibility` maydoni (`SHARED | PRIVATE`, standart `SHARED`) **hozirdan** bo'ladi.

### 4.5a. Sessiya yadroda
- O'rnatish, PIN bilan ochish, tiklash kodi, PIN'ni qayta tasdiqlash, qulflash va harakatsizlikda avto-qulf — `baraka_app::Session` (Android va desktop uchun **bitta** implementatsiya).
- Adapter faqat platforma sirini beradi: desktop — `keyring`, Android — Kotlin `PlatformSecretApi` (Keystore). Debug build'da `BARAKA_INSECURE_DEV_SECRET=1` bo'lsa desktop faylga yozadi (headless Linux uchun); release'da bu yo'l yo'q.

### 4.6. Makonlararo o'tkazma
- Masalan, Kasb-kor → Uy: «egasi maoshi» Uy makonida `Income(sourceType = MOL | TAVAKKAL)` bo'lib tushadi.
- `app::transfer_between_spaces` bitta DB tranzaksiyasida ikkita yozuv yaratadi, ular umumiy `transfer_id` bilan bog'lanadi. Biri yozilib, ikkinchisi yozilmay qolishi mumkin emas (test).
- Agar manba yoki qabul qiluvchi yozuv jurnalga bog'langan bo'lsa (kelishuv bo'yicha), jurnal yozuvi ham shu tranzaksiyada qo'shiladi.

---

## 5. PUL MODELI VA ALGORITMLAR (BITMA-BIT ANIQ)
> Bu bo'lim `docs/uy/DESKTOP_PROMPT.md` 4-bo'limini **o'rnini bosadi** va uni aniqlashtiradi. Barcha formulalar butun sonlarda yoki rational sonlarda hisoblanadi.

### 5.1. Valyutalar
| Kod | Kasr xonasi (`exponent`) | Izoh |
|---|---|---|
| `UZS` | 2 | asosiy valyuta, minor = tiyin |
| `USD`, `EUR`, `RUB`, `KZT`, `TRY`, `GBP` | 2 | |
| `KRW` | **0** | Koreya voni — kasr xonasi yo'q |

- `Currency` har bir valyutaning `exponent`ini biladi. «Hamma valyuta 2 xonali» degan taxmin **taqiqlanadi**.
- Yangi valyuta qo'shish — `money` crate'idagi jadval + `fx_convert` va `money_format` vektorlari bilan.

### 5.2. `Money`
- `Money { minor: i64, currency: Currency }` — immutable.
- Har xil valyutani qo'shish yoki solishtirish → `Error::CurrencyMismatch`.
- Arifmetika `checked_*` bilan; overflow → `Error::Overflow` (hech qachon wrap yoki panic emas).
- Oraliq hisoblar `i128` da, natija `i64` ga `try_from` bilan qaytariladi.

### 5.3. Yaxlitlash — `round_half_up`
- Yagona markazlashgan funksiya. Boshqa joyda yaxlitlash taqiqlanadi (review'da `/` bilan bo'lish va `as` konvertatsiyasi qidiriladi).
- Ta'rif: **yarimni noldan uzoqqa** (half away from zero), ishoraga nisbatan simmetrik:
  - `round_half_up(2.5) = 3`, `round_half_up(-2.5) = -3`, `round_half_up(-2.4) = -2`.
- Kirish — rational `num / den` (`den > 0`), `i128` da.

### 5.4. `allocate(total, ratios)` — largest remainder
1. `ratios`: `i64`, har biri `≥ 0`, yig'indisi `> 0`. Aks holda `Error::InvalidRatios`.
2. Agar `total < 0`: natija = `allocate(−total, ratios)` ning har bir elementi manfiy ishora bilan. (**Simmetriya qoidasi** — dist-002, dist-003 va barcha zarar taqsimotlari shu orqali.)
3. `total ≥ 0` uchun:
   - har bir qismning aniq ulushi `q_i = total × r_i / Σr` (`i128`, rational);
   - `base_i = floor(q_i)`;
   - qolgan birliklar `total − Σbase_i` ta. Ular **kasr qismi kattaroq** bo'lgan qismlarga bittadan beriladi;
   - kasrlar teng bo'lsa — **kichik indeksli** qismga.
4. Invariantlar (proptest): `Σparts = total`; `total ≥ 0` bo'lsa barcha qismlar `≥ 0`; `r_i = 0` bo'lsa `part_i = 0`.

### 5.5. `percent_of(m, bp)`
- `percent_of(m, bp) = allocate(m, [bp, 10000 − bp])[0]`, `0 ≤ bp ≤ 10000`.
- Foiz va ko'rsatkichlar ichki hisobda **basis points (`i64`)**; faqat ko'rsatishda formatlanadi.

### 5.6. Valyuta konvertatsiyasi — `FxRate`
- `FxRate { from, to, rate_num: i64, rate_den: i64, date, source }`. Ma'nosi: **1 major `from` = `rate_num / rate_den` major `to`**.
- `convert(m, fx)`: `minor_to = round_half_up( m.minor × rate_num × 10^exp(to) / (rate_den × 10^exp(from)) )`.
- Misollar: 100 USD (`10000`) @ `12650/1` → `126500000` tiyin; 1 000 000 KRW (`1000000`) @ `91/10` → `910000000` tiyin.
- MVP'da kursni foydalanuvchi kiritadi. Har bir konvertatsiya qaysi `FxRate` bilan qilinganini saqlaydi.

### 5.7. Formatlash — yadroda, ICU/intl ishlatilmaydi
| Qoida | Qiymat |
|---|---|
| Minglik ajratuvchi | **U+00A0** (NBSP), 3 xonadan |
| Kasr ajratuvchi | `,` (vergul) |
| Kasr qismi | nol bo'lsa ko'rsatilmaydi (`8 000 000 soʻm`); nol bo'lmasa `exponent` xonagacha (`123,45 soʻm`) |
| Manfiy | `-` (U+002D) boshida: `-8 000 000 soʻm` |
| Birlik oldidagi bo'shliq | U+00A0 |
| UZS birligi | `uz`: **`soʻm`** (`ʻ` = U+02BB); `uz-Cyrl`: `сўм`; `ru`: `сум` |
| Boshqa valyutalar | kod bilan: `100 USD`, `1 000 000 KRW` |

`money_format.json` vektorlari aniq **kod nuqtalarini** (UTF-8 hex) ham saqlaydi.

### 5.8. Amortizatsiya
`docs/uy/DESKTOP_PROMPT.md` 5.3 dagi algoritm o'zgarishsiz amalda (`r = annualBp / 10000 / 12` rational, `round_half_up`, «muddatni qisqartirish» rejimi, `extra = min(extra, balance)`). Vektorlar amort-001…003 mustaqil oracle bilan tasdiqlangan (12.2).

### 5.9. «Izohsiz summa» (tuzatilgan formula)
```
gap = income − obligations_paid − expenses − vault_net − Δ(CASH + BANK_CARD)
```
- `vault_net` = davr ichida jamg'armaga kirgan − chiqqan.
- `Δ(CASH + BANK_CARD)` = davr oxiri va boshi qoldiqlari farqi. **Cho'ntakda qolgan pul «oqib ketgan» deb ko'rsatilmaydi.**
- Majburiyat to'lovi xarajat sifatida ham yozilgan bo'lsa, faqat bir marta hisoblanadi (`expense.obligation_id` bo'yicha).
- Qoldiqlar kiritilmagan bo'lsa, UI ayblamaydigan matn bilan «qoldiqni kiriting» deb so'raydi.
- Mavjud `unexplained_gap` vektori (`Δ = 0`) o'zgarmaydi; yangi case'lar qo'shiladi (12.3).

---

## 6. APPEND-ONLY JURNAL VA XESH-ZANJIR
> `docs/uy/SPEC.md` 2F.6 va `DESKTOP_PROMPT.md` 5.3 (`journal_chain.json`) amalda. Bu bo'lim ularni aniqlashtiradi.

### 6.1. Algoritm
- `canonical` = RFC 8785 (JCS) JSON: kalitlar UTF-16 kod birliklari bo'yicha tartiblangan, bo'sh joy yo'q, UTF-8.
- `hash_n = hex_lower(SHA256(prevHash + "\n" + canonical(entry_n)))`; genesis `prevHash` = 64 ta `0`.
- Har bir kelishuvning o'z zanjiri. Tartib — kelishuv ichidagi `seq` (1, 2, 3 …, saqlanadi, lekin xeshlanmaydi: tartib zanjirning o'zida).

### 6.2. Xeshlanadigan maydonlar (whitelist) — v1
| Maydon | Turi | Majburiy |
|---|---|---|
| `id` | UUIDv7 string | ha |
| `agreementId` | UUIDv7 string | ha |
| `kind` | enum string (`CONTRIBUTION`, `EXPENSE`, `REVENUE`, `PROFIT_DISTRIBUTION`, `LOSS_ALLOCATION`, `REPAYMENT`, `OPENING_BALANCE`, `DUTY_INCIDENT`, `REVIEW_ACK`, `CORRECTION`, …) | ha |
| `partyId` | string | yo'q |
| `amount` | `{ "minor": string, "currency": string }` | yo'q |
| `date` | `YYYY-MM-DD` (lokal sana) | ha |
| `note` | string | yo'q |
| `correctsEntryId` | UUIDv7 string | faqat `CORRECTION` da majburiy |
| `refs` | string massivi (masalan, chek rasmi xeshi `sha256:<hex>`) | yo'q |

- **Barcha sonlar string.** JSON `number` tipi jurnalda ishlatilmaydi.
- **Qiymati yo'q ixtiyoriy maydon kalit sifatida umuman yozilmaydi.** `null` taqiqlanadi.
- Ro'yxatda yo'q maydonlar (`householdId`, `spaceId`, `createdAt`, `version`, `originDeviceId`, `prevHash`, `hash`, `seq`) **xeshlanmaydi**.
- Whitelist'ni o'zgartirish = `schemaVersion` oshiriladi + yangi vektor + ADR. Eski yozuvlar o'z versiyasining qoidasi bilan tekshiriladi.

### 6.3. O'zgarmaslik
- DB darajasida `journal_entries` uchun `BEFORE UPDATE` va `BEFORE DELETE` triggerlar `RAISE(ABORT)`. Repository'da `update`/`delete` metodlari umuman yo'q.
- Tuzatish faqat `CORRECTION` yozuvi bilan (`correctsEntryId` bilan).
- `verify_chain(agreement_id)` → `Ok(head)` yoki `Err(FirstBroken { seq, id })`.

### 6.4. Matn normalizatsiyasi
- UI'dan kelgan har bir matn yadroda **bir marta, saqlashdan oldin NFC** ga keltiriladi.
- Saqlangan matn import/eksport va qayta tekshirishda **hech qachon qayta normalizatsiya qilinmaydi** — baytlar o'zgarishsiz uzatiladi.

### 6.5. chainHead — dalil faqat tashqarida saqlansa ishlaydi
- Jurnalni bitta qurilma (keeper) yuritadi va u nazariy jihatdan butun zanjirni qayta hisoblay oladi. Shu sababli zanjirning dalil kuchi **chainHead ikkinchi tomonda saqlanganida** paydo bo'ladi.
- Har bir ko'rik bayonnomasi, tilxat va shartnoma PDF'ida:
  - chainHead **qisqa kodi** — birinchi 16 hex belgi, 4 ta guruhda: `F8B2-EF8C-8E72-218F`;
  - to'liq chainHead QR-kod sifatida;
  - matn: «Bu kodni o'zingizda saqlang. Keyinchalik yozuvlar o'zgartirilmaganini shu kod bilan tekshirish mumkin».
- Ilovada «Kodni tekshirish» funksiyasi: kiritilgan qisqa kod yoki skanerlangan QR joriy zanjirdagi tegishli joy bilan solishtiriladi.
- UI va hujjatlar «sezdirmasdan o'zgartirib bo'lmaydi» deb **mutlaq va'da bermaydi**; «saqlangan kod bilan solishtirib tekshirish mumkin» deydi.

### 6.6. Hisob yurituvchi qurilma va fork
- `custody.keeper_device_id` — faqat shu qurilma jurnalga yozadi; boshqa qurilmalarda jurnal faqat o'qish uchun.
- Import paytida zanjir `verify_chain` bilan tekshiriladi. Mahalliy nusxadan ayrilib ketgan bo'lsa (fork) — import to'xtaydi, aniq hisobot ko'rsatiladi, **avtomatik birlashtirilmaydi**.
- Keeper'ni almashtirish faqat kelishuvning yangi versiyasi orqali.

---

## 7. XAVFSIZLIK

### 7.1. Tahdid modeli (halol)
| Tahdid | Himoya | Cheklov (ochiq aytiladi) |
|---|---|---|
| Telefon yoki noutbuk yo'qolgan/o'g'irlangan | SQLCipher + platforma siri + PIN | — |
| Qurilmani boshqa oila a'zosi ochgan | PIN, avto-qulf, makon/a'zo darajasidagi ko'rinish | Bitta qurilmada a'zolar o'rtasidagi maxfiylik cheklangan |
| Skrinshot, ekran yozuvi, «so'nggi ilovalar» oynasi | `FLAG_SECURE`, `setContentProtected` | Linuxda imkoniyat yo'q — «Xavfsizlik» sahifasida aytiladi |
| Shu foydalanuvchi nomidan ishlayotgan zararli dastur (desktop) | platforma siri + PIN birlashmasi | 6 xonali PIN = 10⁶ variant. Fayl va keyring sirini olgan hujumchi uni soatlar yoki kunlar ichida terib topishi mumkin. Uzunroq parol ixtiyoriy |
| Eksport fayli tarqalib ketishi | Argon2id(parol) + XChaCha20-Poly1305 | Parol kuchsiz bo'lsa — himoya kuchsiz (parol kuchi ko'rsatkichi) |
| Ulashilgan PDF | — | PDF shifrlanmagan. Ulashishdan oldin ogohlantirish |

### 7.2. Kalit iyerarxiyasi (Android va desktop uchun bir xil)
```
DB_KEY (32 bayt, OsRng)          ← SQLCipher kaliti; faqat xotirada, zeroize
  └─ slotlar: DB_KEY har bir slotda alohida XChaCha20-Poly1305 bilan wrap qilinadi
      slot PIN      : KEK = HKDF-SHA256(ikm = PLATFORM_SECRET ‖ Argon2id(PIN, salt_pin), info = "baraka/kek/pin/v1")
      slot RECOVERY : KEK = HKDF-SHA256(ikm = PLATFORM_SECRET ‖ Argon2id(RECOVERY_CODE, salt_rc), info = "baraka/kek/recovery/v1")
      slot BIO      : KEK = biometriya bilan ochiladigan platforma kaliti (7.3)

PLATFORM_SECRET (32 bayt):
  Android — tasodifiy, Keystore'dagi AES-GCM kalit bilan wrap qilinib, ilovaning private storage'ida (StrongBox bo'lsa — StrongBox)
  Desktop — OS keyring (Windows Credential Manager / Keychain / Secret Service)
```
- `keys.bin` fayli: versiya, KDF parametrlari, saltlar, slotlar. PIN o'zgarganda faqat PIN sloti qayta wrap qilinadi.
- **Ikkala omil ham kerak:** faqat keyring yoki faqat PIN bilan bazani ochib bo'lmaydi (test).
- Argon2id parametrlari `keys.bin` da saqlanadi va qurilmada kalibrlanadi (maqsad ~0,5 s): Android uchun boshlang'ich `m = 19 MiB, t = 2, p = 1`; desktop uchun `m = 64 MiB, t = 3, p = 1`.
- **Tiklash kodi:** onboarding'da 24 belgili kod (base32, 4 tadan guruhlangan, ~120 bit) ko'rsatiladi va chop etish/yozib olish taklif qilinadi. PIN unutilsa — shu kod bilan ochiladi va yangi PIN o'rnatiladi. Qurilmaning o'zi yo'qolsa — faqat `.baraka` eksport fayli yordam beradi (onboarding'da va har oy eslatiladi).

### 7.3. Biometriya
- **Android:** `BiometricPrompt` + **`CryptoObject`**. BIO sloti Keystore'dagi `setUserAuthenticationRequired(true)` (BIOMETRIC_STRONG) kaliti bilan himoyalangan; biometriya muvaffaqiyatli bo'lgandagina u DB_KEY'ni ochadi. Faqat «ha/yo'q» javobiga tayanish **taqiqlanadi**.
- **Windows Hello:** `KeyCredentialManager` orqali RSA kalit yaratiladi, `keys.bin` dagi tasodifiy `challenge` imzolanadi (PKCS#1 v1.5 — deterministik), imzo HKDF orqali KEK'ga aylanadi. `UserConsentVerifier` faqat UI tasdig'i, **kalit omili emas**.
- Biometriya ixtiyoriy; PIN har doim bor.

### 7.4. Qulflash
- 6 xonali PIN. Xato kiritilganda o'sib boruvchi kutish: 5 xatodan keyin 30 s, keyin 1, 5, 15, 60 daqiqa. Hisoblagich `keys.bin` da.
- Avto-qulf: Android — fonga o'tgandan **2 daqiqa** keyin; desktop — **5 daqiqa** harakatsizlik yoki ekran qulflanganda (`WTSRegisterSessionNotification`). Sozlanadi.
- `Ctrl+L` (desktop) — darhol qulflash. Qulflanganda DB_KEY xotiradan `zeroize` qilinadi va ulanishlar yopiladi.
- Moliyaviy ekranlar: Android — `FLAG_SECURE`; desktop — `setContentProtected(true)`.

### 7.5. Vidjet va tray: «yoza oladi, o'qiy olmaydi»
- Ilova qulflangan paytda vidjet (Android Glance) yoki tray «tez xarajat» oynasi (desktop) **bazani ocha olmaydi**.
- Ular yozuvni **navbatga** qo'yadi: yozuv ilovaning ochiq kaliti (X25519) bilan shifrlanadi (sealed box). Yopiq kalit DB ichida turadi va faqat ilova ochilganda navbatni o'qib, yozuvlarni bazaga qo'shadi.
- Qulflangan holatda vidjet va tray **hech qanday summa ko'rsatmaydi** (test).

### 7.6. Boshqa qoidalar
- Android: `allowBackup="false"`, `dataExtractionRules`; release'da `debugPrint` o'chiq; integrity signallari (root, emulyator, debugger, imzo) — faqat ogohlantirish.
- Desktop: qat'iy CSP (`default-src 'self'`, `unsafe-eval` yo'q), release'da DevTools o'chiq, tarmoq ishlatilmaydi (updater bundan mustasno), telemetriya yo'q.
- Baza joyi: Android — ilova private storage; Windows — `%APPDATA%\BarakaOilasi\` (har Windows foydalanuvchisi uchun alohida).

---

## 8. MA'LUMOTLAR, SAQLASH VA ALMASHISH

### 8.1. Konvensiyalar
- ID: UUIDv7 (string). Autoincrement yo'q.
- **Har bir jadvalda:** `household_id`, `space_id` (makon jadvallaridan tashqari), `created_at`, `updated_at` (UTC, ISO-8601), `deleted_at` (soft delete), `version` (i64), `origin_device_id`, `updated_by_device_id`.
- `devices` jadvali: shu xonadonga ulangan qurilmalar (`id`, `name`, `platform`, `paired_at`).
- Entity va maydon nomlari tegishli SPEC 5-bo'limidagi bilan bir xil (DB'da snake_case, DTO'da camelCase).
- `Asset` abstraksiyasi `docs/uy/SPEC.md` 4.3 dagi kabi: `CASH | BANK_CARD | VAULT | GOLD | SILVER | FOREIGN_CURRENCY | RECEIVABLE | TRADE_GOODS | BUSINESS_SHARE`; miqdor butun sonda (oltin — milligramm).
- Byudjet davrlari lokal sana bo'yicha (`Asia/Tashkent`); oylik kuni va hafta boshi sozlanadi.
- Kelajak bosqichlardagi maydonlar jadvalga hozirdan nullable qilib qo'shiladi.

### 8.2. Migratsiyalar
- Har bir migratsiya — alohida SQL fayl va test: «eski sxemadagi namunaviy baza → migratsiya → ma'lumot yo'qolmagan».
- Moliyaviy ma'lumot ko'chiriladigan migratsiyalarda (masalan, VAULT → QOROVUL) balans yig'indisi oldin va keyin teng ekani tekshiriladi.

### 8.3. `.baraka` almashish formati
- Konteyner: sarlavha (`magic`, `formatVersion`, KDF parametrlari, salt, nonce) + XChaCha20-Poly1305 bilan shifrlangan JSON Lines. Kalit — Argon2id(foydalanuvchi paroli).
- Sxema: `spec/interchange/export-format.schema.json` — **yagona fayl**, Android va desktop bir xil `interchange` crate'idan foydalanadi.
- Eksport: to'liq yoki inkremental (`updated_at > since` yoki qurilma bo'yicha sinxronlash holati).
- Noto'g'ri parol → aniq xato kodi `INTERCHANGE_BAD_PASSWORD`.

### 8.4. Birlashtirish qoidalari
- Yozuvlar `id` bo'yicha moslashtiriladi. `sync_peers` jadvali har bir juft qurilma uchun oxirgi sinxronlash holatini saqlaydi.
- **Oxirgi sinxronlashdan keyin faqat bir tomonda o'zgargan yozuv** — avtomatik qabul qilinadi.
- **Ikkala tomonda o'zgargan yozuv — ZIDDIYAT.** U foydalanuvchiga ko'rsatiladi va u tanlaydi. Pul yoki sana maydonlarida «oxirgi yozgan yutadi» (LWW) qoidasi **taqiqlanadi**. LWW faqat moliyaviy bo'lmagan maydonlarda (sozlamalar, ko'rinish) ruxsat etiladi.
- `deleted_at` (tombstone) o'chirish sifatida qo'llanadi; o'chirilgan yozuv boshqa tomonda o'zgargan bo'lsa — ziddiyat.
- Yopilgan davrlar (venture taqsimoti, kassa kuni, imzolangan versiya, ko'rik bayonnomasi) import orqali **o'zgartirilmaydi**; urinish — ogohlantirish.
- Jurnal — 6.6 qoidalari bo'yicha.

### 8.5. Qurilmalarni ulash (pairing)
- Birinchi qurilma xonadonni yaratadi. Ikkinchi qurilma onboarding'da **«Mavjud xonadonga qo'shilish»** ni tanlaydi.
- Birinchi qurilma QR ko'rsatadi: `household_id`, bir martalik ulash siri, qurilma nomi. Ikkinchi qurilma QR'ni skanerlaydi, `household_id` ni qabul qiladi, birinchi `.baraka` faylini shu sirdan hosil qilingan kalit bilan oladi.
- Ikkita alohida xonadonni keyinchalik birlashtirish MVP'da **yo'q** (ogohlantirish bilan rad etiladi).

---

## 9. PDF (typst)
- `pdf` crate'i typst'ni kutubxona sifatida ishlatadi: o'zimizning `World` implementatsiyasi, shablonlar `shared/pdf/*.typ`, shriftlar `shared/fonts/` (Noto Sans va Noto Serif — `ʻ` U+02BB, `ʼ` U+02BC, o'zbek kirill `ў қ ғ ҳ` va rus harflarini qamrab oladi; litsenziya fayllari bilan).
- **Determinizm:** sana va vaqt `Clock` dan, PDF metadata'dagi vaqt va identifikator qotiriladi. Bir xil kirish → bir xil baytlar.
- Snapshot testlari: `typst-render` orqali har bir sahifa PNG'ga aylantiriladi va `insta` bilan solishtiriladi; qo'shimcha ravishda PDF baytlarining SHA-256 xeshi.
- Umumiy bloklar: sarlavha, jadval, imzo bloki (tomon, guvoh, hakam), chainHead bloki (6.5), disklеymer, sahifa raqami, mundarija (hakam papkasi uchun).
- Shablonlarda `reviewStatus`; `PENDING` shablon release'da «Tekshiruvdan o'tmagan namuna» suv belgisi bilan chiqadi.
- Android: PDF baytlari yadrodan keladi → `pdfrx` bilan ko'rsatiladi → `share_plus`/`printing`. Desktop: jonli preview + tizim chop etish dialogi.
- Hajm: shriftlar subset qilinadi; APK hajm byudjeti (3.2) buzilsa, shrift to'plami qisqartiriladi.

---

## 10. I18N, DIZAYN TOKENLARI VA KONTENT

### 10.1. Yagona manba
- `shared/i18n/uz.json` (asosiy, lotin), `shared/i18n/ru.json` — ICU MessageFormat.
- `uz-Cyrl` — `cargo xtask i18n` orqali lotindan **avtomatik transliteratsiya** qilinadi (`ts`, `yo`, `ye`, so'z boshidagi `e` → `э` kabi qoidalar bilan) va `uz-Cyrl.overrides.json` dagi qo'lda tuzatishlar ustiga qo'yiladi.
- `cargo xtask i18n` generatsiya qiladi: Flutter uchun ARB (`apps/android/lib/l10n/`), React uchun i18next JSON (`apps/desktop/ui/src/i18n/`). **Generatsiya qilingan fayllar qo'lda tahrirlanmaydi**; CI generatsiyadan keyin `git diff` bo'sh ekanini tekshiradi.
- UI matnlari faqat i18n'da; hardcode taqiqlanadi (lint).

### 10.2. Lokallar
`uz` (asosiy), **`uz-Cyrl`** (50 yoshdan katta foydalanuvchilar uchun), `ru`. Til onboarding'da va sozlamalarda tanlanadi.

### 10.3. Taqiqlangan iboralar linteri
- `cargo xtask i18n --lint` barcha lokallardagi matnlarni `shared/i18n/forbidden.json` ro'yxati bilan tekshiradi: foizni «muqobil daromad» sifatida ko'rsatish («bankda tursa X% …»), va'dalar («X oyda mashina»), uyaltiruvchi so'zlar va h.k.
- Linter CI'da majburiy.

### 10.4. Dizayn tokenlari
- `shared/design-tokens/tokens.json` — ranglar, shriftlar, oraliqlar, radiuslar, light/dark. `cargo xtask tokens` → CSS (Tailwind v4 `@theme`) va Dart.
- **Standart mavzu — dark, Claude Code dark theme uslubida** (foydalanuvchi qarori, 2026-10-15; `defaultTheme: "dark"`): fon `#262624`, sidebar `#1F1E1D`, surface `#30302E`, matn `#FAF9F5`, aksent `#D97757` (ustida `#1F1E1D`). Light — ixtiyoriy (`data-theme="light"`). Oldingi «qog'oz daftar» palitrasi bekor; «daftar» metaforasi matn va tuzilmada qoladi.
- `HAVAS` rangi neytral (qizil emas). Kontrast WCAG AA (generatsiyadan oldin hisoblanadi).

### 10.5. Kontent
- Boblar JSON shaklida `shared/content/<makon>/` da: `Chapter`, `Law`, `WeeklyTask[3]`, `religiousReviewStatus`.
- `PENDING` diniy bloklar release build'da ko'rsatilmaydi (test). Ta'limiy matnlar — faqat o'zimiz yozganlari (boshqa mualliflarning qissa matnlari ishlatilmaydi, 2.1).

---

## 11. PLATFORMA XUSUSIYATLARI

### 11.1. Android
- Pigeon API'lari (`apps/android/pigeons/`):
  - `PlatformSecretApi` — `getOrCreatePlatformSecret()`, `unwrapBioSlot(cryptoObject…)`;
  - `SecureWindowApi` — `setSecure(bool)`;
  - `ReminderApi` — WorkManager orqali eslatmalar (qurilma qayta yoqilgandan keyin ham);
  - `WidgetApi` — vidjet uchun xavfsiz snapshot (summasiz) va navbat (7.5).
- Platforma siri Kotlin'dan Dart orqali Rust'ga `ZeroizingBytes` sifatida uzatiladi va ishlatilgandan keyin tozalanadi.
- Bir qo'l bilan kiritish, 48dp+ tugmalar, TalkBack yorliqlari, katta shrift.
- Sovuq start < 2 s (o'rta segment telefon); ro'yxatlar paginatsiya bilan.

### 11.2. Desktop
`docs/uy/DESKTOP_PROMPT.md` **7-bo'limi to'liq amalda** (oyna tuzilmasi, klaviatura, «Hafta varag'i», tray va `Ctrl+Alt+B`, oila kengashi rejimi, chop etish, bildirishnomalar, CSV import, accessibility). Qo'shimcha:
- Navigatsiyada makon tanlovchi (Uy / Kasb-kor / Musofir).
- Kasb-kor makoni uchun desktop — asosiy ish stoli: kunlik kassa jadvali, nasiya jadvali, tovar qoldig'i, oylik «Hisob kuni».
- Sovuq start < 1,5 s.

---

## 12. TEST STRATEGIYASI VA OLTIN VEKTORLAR

### 12.1. Piramida
| Daraja | Vosita | Nima |
|---|---|---|
| Domen | `cargo test`, `proptest`, `insta` | barcha qoidalar, invariantlar |
| Vektorlar | `core/crates/vectors` | barcha `spec/test-vectors/*.json` |
| FFI | Dart test (FRB orqali) | **barcha vektorlar Dart'dan ham ishga tushiriladi** — DTO va string-pul konvertatsiyasidagi xatolarni ushlaydi |
| Storage | `cargo test` (vaqtinchalik shifrlangan baza) | CRUD, soft delete, triggerlar, migratsiyalar |
| UI | Flutter widget testlar; `vitest` + Testing Library | ekran xulqi |
| E2E | Flutter `integration_test` (emulator, tungi); `tauri-driver` (Windows, tungi) | Bekzod ssenariysi |

### 12.2. Mustaqil oracle
- `spec/oracle/oracle.py` — algoritmlarning **Python'dagi mustaqil** implementatsiyasi (`fractions.Fraction`, standart kutubxona, tashqi paketlarsiz).
- Har bir yangi vektor avval oracle bilan hisoblanadi, keyin Rust bilan. Rust natijasi oracle'dan farq qilsa — xato Rust'da deb hisoblanmaydi, **ikkalasi ham** tekshiriladi.
- CI: `python3 -I spec/oracle/oracle.py --check spec/test-vectors` — vektor fayllari oracle bilan mos.
- Mavjud vektorlar (allocate, percent_of, amortization 001–003, journal_chain 001–003, emergency_target, personal_inflation, unexplained_gap, profit_spike, profit_distribution) oracle bilan **tasdiqlangan**.

### 12.3. Vektor suite'lari
**Mavjudlari** — `docs/uy/DESKTOP_PROMPT.md` 5.3 (qiymatlari o'zgarmaydi).

**Yangi majburiy case'lar:**
| Suite | id | Kirish | Kutilgan |
|---|---|---|---|
| `allocate` | alloc-neg-001 | total −100, [1,1,1] | [−34, −33, −33] |
| `allocate` | alloc-neg-002 | total −200000000, [1,0] | [−200000000, 0] |
| `allocate` | alloc-err-001 | total 100, [0,0] | `error: INVALID_RATIOS` |
| `round` | round-001…004 | 5/2, −5/2, −12/5, 7/2 | 3, −3, −2, 4 |
| `fx_convert` | fx-001 | 10000 USD, 12650/1 → UZS | 126500000 |
| `fx_convert` | fx-002 | 1000000 KRW, 91/10 → UZS | 910000000 |
| `fx_convert` | fx-err-001 | 10000 USD, kurs EUR→UZS (valyuta mos emas) | `error: CURRENCY_MISMATCH` |
| `money_format` | fmt-001 | 800000000 UZS, `uz` | `8 000 000 soʻm` (NBSP, U+02BB) |
| `money_format` | fmt-002 | 12345 UZS, `uz` | `123,45 soʻm` |
| `money_format` | fmt-003 | −800000000 UZS, `uz` | `-8 000 000 soʻm` |
| `money_format` | fmt-004 | 800000000 UZS, `ru` | `8 000 000 сум` |
| `money_format` | fmt-005 | 800000000 UZS, `uz-Cyrl` | `8 000 000 сўм` |
| `money_format` | fmt-006 | 1000000 KRW, `uz` | `1 000 000 KRW` |
| `unexplained_gap` | gap-002 | daromad 800000000, majb. 535000000, xarajat 165000000, jamg'arma 0, Δqoldiq +60000000 | 40000000 |
| `journal_chain` | chain-utf8-001 | `note` da `oʻ`, `gʻ`, `ʼ`, kirill | oracle bilan |
| `journal_chain` | chain-opt-001 | `amount` siz yozuv (kalit yozilmaydi) | oracle bilan |
| `journal_chain` | chain-corr-001 | `CORRECTION` + `correctsEntryId` | oracle bilan |

Makonlarning o'z suite'lari (tannarx, kassa farqi, nasiya muddatlari, zakot, sovutish davri …) K0 va M0 da belgilanadi.

### 12.4. Vektorlar bilan ishlash tartibi
1. Yangi pul funksiyasi — **avval vektor (oracle bilan)**, keyin Rust implementatsiyasi (TDD).
2. Case `id` si o'zgarmaydi. Xato topilsa, case o'chirilmaydi — suite'ning yangi `version` i chiqariladi.
3. `spec/test-vectors/` va `spec/oracle/` dagi o'zgarishlar `CODEOWNERS` orqali mahsulot egasining ma'qullashini talab qiladi.

---

## 13. CI/CD (GitHub Actions)
> Workflow'lar repo ildizidagi `.github/workflows/` da bo'lishi shart. Shu sababli loyiha **alohida `baraka-oilasi` repo**sida yashaydi.

| Workflow | Runner | Bosqichlar |
|---|---|---|
| `core.yml` | ubuntu, windows | `fmt --check` → `clippy -D warnings` → `test` → vektorlar → `no_std` tekshiruvi (`money`, `journal` uchun `thumbv8m.main-none-eabihf` build) |
| `oracle.yml` | ubuntu | `oracle.py --check` |
| `codegen.yml` | ubuntu | `cargo xtask codegen && cargo xtask i18n && cargo xtask tokens` → `git diff --exit-code`; `cargo xtask i18n --lint` |
| `android.yml` | ubuntu (NDK) | `cargo-ndk` build → `flutter analyze` → `flutter test` (FFI vektorlari bilan) → `build appbundle` → hajm byudjeti |
| `desktop.yml` | **windows** (asosiy), macos, ubuntu | `pnpm lint` → `pnpm test` → `tauri build` (NSIS) |
| `nightly-e2e.yml` | ubuntu (emulator), windows | Flutter `integration_test`, `tauri-driver` |

- Release imzolash kalitlari faqat CI secret'larida; repoga hech qachon yozilmaydi.
- Har bir PR: barcha workflow'lar yashil bo'lmaguncha merge qilinmaydi.

---

## 14. ISH REJASI
> Har bir vazifa **alohida sessiyada** bajariladi. Katta vazifalar uchta sessiyaga bo'linadi: **(a) yadro** (`core/`), **(b) Android UI**, **(c) Desktop UI**. Har sessiya oxirida qabul mezonlari tekshiriladi va commit qilinadi.

### Tartib
```
Y1 → Y2 → Y3 → Y4 → Y5 → Y6                     (poydevor)
U1 → … → U15                                     (Uy makoni — 1-reliz)
U16 → K9 → M6                                    (8-tamoyil — uchala makon; 1.2.0)
K0 (U-vazifalar bilan parallel, faqat hujjat) → K1 → … → K5   (Kasb-kor MVP — 2-reliz)
M0 (parallel, faqat hujjat) → M1 → M2 → M3       (Musofir MVP — 3-reliz)
K6 → K7 → K8, R1, G0 → G1                        (kengaytmalar)
```

### Y. POYDEVOR

**Y1 — Monorepo, skelet va CI**
- 4.1 dagi tuzilma; bo'sh crate'lar; `app` va `bindings/flutter`.
- Flutter Android ilova: FRB orqali `core_version()` chaqiriladi va ekranda ko'rsatiladi.
- Tauri ilova: `tauri-specta` orqali o'sha `app::core_version()` chaqiriladi.
- `cargo xtask codegen | i18n | tokens` (i18n va tokens — minimal namuna bilan).
- 13-bo'limdagi workflow'lar (e2e'dan tashqari). `docs/adr/0002-versiyalar.md`.
- **Qabul mezonlari:** CI yashil; Android debug APK va Windows NSIS o'rnatuvchisi bir xil Rust funksiyasidan bir xil javob oladi; codegen idempotent (`git diff` bo'sh); `uz` ↔ `uz-Cyrl` ↔ `ru` almashadi.

**Y2 — `money` crate va vektorlar**
- 5-bo'lim to'liq: `Currency` (exponent), `Money`, `round_half_up`, `allocate` (manfiy simmetriya), `percent_of`, `FxRate`, `convert`, formatlash.
- `spec/test-vectors/`: mavjud va 12.3 dagi barcha pul case'lari; `spec/oracle/oracle.py` kengaytiriladi.
- `vectors` runner (Rust) va FFI vektor runner (Dart).
- `proptest`: 5.4 invariantlari; `clippy::float_arithmetic = deny`; `no_std` build.
- **Qabul mezonlari:** barcha vektorlar Rust'da ham, Dart'da ham yashil; oracle tekshiruvi yashil; qamrov ≥ 95%; valyuta aralashuvi xato beradi; KRW formatlash to'g'ri.

**Y3 — `journal` crate**
- 6-bo'lim: JCS (o'zimizniki yoki `serde_jcs` — vektorlar bo'yicha tanlanadi, ADR bilan), whitelist, `null` taqiqi, NFC qoidasi, `verify_chain`, chainHead qisqa kodi.
- `journal_chain.json` (mavjud + 12.3 dagi yangi case'lar), salbiy case.
- **Qabul mezonlari:** 3 ta asl xesh bitma-bit mos; salbiy case 2-yozuvni topadi; `thumbv8m.main-none-eabihf` uchun build o'tadi; whitelist'dan tashqari maydon qo'shish xeshni o'zgartirmaydi (test).

**Y4 — Xavfsizlik va qulf**
- `security`: 7.2 kalit iyerarxiyasi va slotlar, Argon2id kalibrlash, tiklash kodi, lockout, `zeroize`.
- Android: Keystore `PlatformSecretApi`, BIO sloti (`CryptoObject`), `FLAG_SECURE`, avto-qulf 2 daqiqa.
- Desktop: keyring, Windows Hello (`KeyCredentialManager`, ixtiyoriy), `setContentProtected`, avto-qulf 5 daqiqa, `Ctrl+L`.
- Lock ekranlari (ikkala platforma), onboarding'dagi tiklash kodi qadami.
- **Qabul mezonlari:** faqat platforma siri bilan ham, faqat PIN bilan ham ochib bo'lmaydi, ikkalasi bilan ochiladi (test); tiklash kodi bilan ochilib, PIN almashtiriladi (test); lockout vaqtlari testlangan; qulflanganda kalit xotirada qolmaydi (test); skrinshot qora (qo'lda tekshiruv).

**Y5 — Storage, makonlar va `app` qatlami**
- `storage`: SQLCipher, `rusqlite_migration`, writer actor, sxema v1: `households`, `devices`, `spaces`, `members`, `space_members`, `categories`, `incomes`, `expenses`, `assets` + `asset_snapshots`, `vault_transactions`, `allocation_rules`, `obligations`, `fx_rates`, `journal_entries` (triggerlar bilan), `sync_peers`, `quick_entry_queue`. Barcha 8.1 maydonlari.
- `app`: birinchi use-case'lar (makon yaratish, kategoriya CRUD), `ChangeEvent` oqimi.
- Android: FRB `Stream` → Riverpod invalidatsiyasi; Desktop: Tauri event → TanStack Query invalidatsiyasi.
- Standart kategoriyalar seed qilinadi (makon turiga qarab).
- **Qabul mezonlari:** DB faylini kalitsiz ochib bo'lmaydi; migratsiya test infratuzilmasi bor; soft delete testlangan; `journal_entries` ni UPDATE/DELETE qilish DB darajasida rad etiladi; makon parametrisiz so'rov kompilyatsiya bo'lmaydi; ikkala UI'da yozuv qo'shilganda ro'yxat avtomatik yangilanadi.

**Y6 — PDF**
- 9-bo'lim: `World`, shriftlar, determinizm, umumiy bloklar (sarlavha, jadval, imzo, chainHead + QR, disklеymer).
- Android: preview va ulashish; Desktop: preview va chop etish.
- **Qabul mezonlari:** namunaviy hujjatning PNG snapshot va bayt-xesh testlari yashil; `oʻ gʻ ʼ` va `ўқғҳ` to'g'ri chiqadi; APK hajm byudjeti saqlanadi.

### U. UY MAKONI
Har bir U-vazifaning **funksional mazmuni va qabul mezonlari** — ko'rsatilgan MVP vazifasi **va** desktop vazifasining birlashmasi. Qo'shimcha talablar oxirgi ustunda.

| # | MVP_PLAN | DESKTOP | Mavzu | Qo'shimcha talablar (shu hujjatdan) |
|---|---|---|---|---|
| U1 | V4 | D4 (qism) | Daromad, «Kelajagim», ulush, streak, pul olish friction'i | streak'da «dam haftasi» — OQ-P4 qaroriga ko'ra |
| U2 | V5 | D4 (qism) | Xarajat, majburiyatlar, oylik audit, «Kimning puli?», bosh ekran slotlari, oilaviy rejim | **5.9 formula**; `gap-002` vektori |
| U3 | V6 | D5 | Kontent dvigateli, `TaskTrigger`, unlock policy | unlock qoidasi — OQ-P6 qaroriga ko'ra |
| U4 | V7 | D6 | Zarur/Kerak/Havas, havas chegarasi, vidjet, oila kengashi, «Hafta varag'i» | **7.5** (vidjet yoza oladi, o'qiy olmaydi) |
| U5 | V8 | D7 | Obunalar, konvertlar, «Qutqarilgan pul», tray, CSV import | bazaviy davr — OQ-P3 qaroriga ko'ra; tray — 7.5 |
| U6 | V9 | D8 | Zaxira/O'sadigan, narx daftari, inflyatsiya, darvoza, ribo filtri | darvoza sharti — OQ-D4 qaroriga ko'ra |
| U7 | V9A | D8A | Kelishuv dvigateli, jurnal integratsiyasi, imzolar, og'zaki kelishuv | **6.5** (chainHead kodi va QR); `agreement_completeness.json` |
| U8 | V10 | D9 | Qarz inventari, haqiqiy narx, friction, tilxat | tilxatda «foizsiz» bandi va qaytarish valyutasi = qarz valyutasi (OQ-D3, OQ-Y1) |
| U9 | V11 | D10 | `DEBT_RECOVERY` 70/20/10, payoff planner, «Qarzsiz kun» | amort vektorlari Dart'dan ham |
| U10 | V12 | D11 | Marosim rejalovchisi, stsenariylar, maqsadlar | «To'yona daftari» — OQ-P1 qaroriga ko'ra |
| U11 | V13 | D12 | Sheriklik domeni, shartnoma, buyout | zararni keyingi foydadan qoplash — OQ-D1; Hanafiy cheklovi — OQ-D2 |
| U12 | V14 | D13 | Venture ledger, taqsimot, «Hunardan ishga», taklif detektori | |
| U13 | V14A | D13A | Vazifalar, oylik ko'rik, «katta foyda», nizo va hakam, oilaviy kelishuvlar | bayonnomada 6.5 bloki |
| U14 | V15 (eksport) | D14 | `.baraka` eksport/import, pairing | **8.3–8.5**; telefon ↔ desktop round-trip testi |
| U15 | V15 | D15 | Onboarding, accessibility, reliz | onboarding'da makon tanlash va tiklash kodi; yakuniy E2E ikkala platformada |
| U16 | V16 | D16 | 8-tamoyil: «Bir soatim qancha?», bilim rejasi, «Sarmoya» belgisi, kurs tekshiruvi, natija, «Ilm zakoti» | `docs/uy/SPEC.md` 2G; vektorlar `hour_value`, `hour_value_change`, `self_invest_share`, `offer_check` (`COURSE`) |

### K. KASB-KOR MAKONI
**K0 — `docs/kasbkor/SPEC.md` yozish (kod yo'q).** 2.2 dagi karta asosida, `docs/uy/SPEC.md` formatida: personajlar, 7 tamoyilning funksional talablari, domen modeli, vektor suite'lari (tannarx — FIFO yoki o'rtacha tortilgan, kassa farqi, nasiya muddatlari, qayta tiklash narxi, zakot), cheklovlar, mijozlarning shaxsiy ma'lumotlari (operator sifatida rozilik). **Qabul:** mahsulot egasi tasdiqlagan; ulamo va yurist savollari `OPEN_QUESTIONS.md` da.

| # | Mavzu |
|---|---|
| K1 | Ikki cho'ntak: Kasb-kor makoni, tushum/chiqim, «egasi oldi», egasi maoshi, makonlararo o'tkazma (4.6) |
| K2 | Haqiqiy foyda: tannarx kalkulyatori (o'z mehnati, eskirish, oilaviy mehnat) |
| K3 | Taqsimot qoidasi (soliq zaxirasi, maosh, zaxira, aylanma, kengayish) va oylik «Hisob kuni» |
| K4 | Kunlik kassa yopish (kassa farqi — egasi olgan pul va qoldiq hisobga olinadi) va nasiya daftari |
| K5 | Tovar qoldig'i, qayta tiklash narxi, muzlagan tovar |
| K6 | Xodimlar va avans; `EMPLOYMENT`, `SUPPLY` kelishuvlari |
| K7 | Kengayish darvozasi va savdo mollari zakoti |
| K8 | Ko'p qurilma va rollar (sotuvchi foydani ko'rmaydi) — avval ADR (LAN/fayl yoki relay) |
| K9 | 8-tamoyil: egasining soat qiymati, «o'zim qilaymi yoki o'rgatib topshiraymi?» (`kasbkor/SPEC.md` 8A; ✅ — vektorlar `kk_owner_hour`, `kk_delegate`, farqlar 8A.4) |

### M. MUSOFIR MAKONI
**M0 — `docs/musofir/SPEC.md` + relay ADR loyihasi (kod yo'q).** **Qabul:** mahsulot egasi tasdiqlagan.

| # | Mavzu |
|---|---|
| M1 | Ko'p valyuta (KRW va b.), chet eldagi maosh va xarajatlar, o'z ulushi, qaytish jamg'armasi |
| M2 | «Ikki qirg'oq»: o'tkazma maqsadlari, `REMITTANCE` kelishuvi, uydagi xarajatni maqsad bo'yicha yozish (`.baraka` fayl orqali) |
| M3 | Yo'l qarzi, sovutish davri, kengaytirilgan taklif detektori |
| M6 | 8-tamoyil: soat qiymati ish valyutasida, ikki maqsadli bilim rejasi (`musofir/SPEC.md` 6A; ✅ — vektor `mf_hour_value`, farqlar 6A.1) |
| R1 | E2E shifrlangan relay server (axum) — ADR tasdiqlangandan keyin |

### G. «GUVOH» QURILMASI (keyinroq)
| # | Mavzu |
|---|---|
| G0 | Qurilma spetsifikatsiyasi va tahdid modeli (Kasb-kor tarozisi yoki Musofir/dala qurilmasi) |
| G1 | RP2350 proshivkasi: `money` + `journal` `no_std`, OTP'dagi kalit, BLE sinxronlash, ilova bilan bir xil xesh |

---

## 15. SESSIYA SHABLONI (har sessiya boshiga qo'yiladi)
```
Sen «Baraka oilasi» loyihasining senior Rust + Flutter + React dasturchisisan.
Avval o'qi: CLAUDE.md, docs/BARAKA_OILASI.md (0, 3–7 va 14-bo'limlar),
docs/OPEN_QUESTIONS.md va vazifaga tegishli SPEC/MVP_PLAN/DESKTOP_PROMPT bo'limlari.
3-bo'lim (ADR) qat'iy. Pul va biznes mantiq faqat core/ da; UI hisoblamaydi.
Yangi pul funksiyasi — avval spec/test-vectors ga vektor (oracle bilan), keyin kod.
Bu sessiyada FAQAT quyidagi vazifani (va ko'rsatilgan qismini: a/b/c) bajar.
Avval qisqa reja yoz (fayllar + qadamlar), keyin bajar.
Oxirida: bajarilgan ishlar, qabul mezonlari holati (har biri alohida), ochiq savollar.
docs/CHANGELOG.md ni yangila. Kod, identifikatorlar va commit xabarlari inglizcha;
izohlar, hujjatlar va UI matnlari o'zbekcha.

VAZIFA: <masalan, Y2 — money crate va vektorlar>
```

---

## 16. AI-DASTURCHI UCHUN QOIDALAR
- Faqat berilgan vazifa (va qism) ustida ishla. Keyingi vazifa funksiyalarini «qo'shimcha» sifatida yozma.
- 3-bo'limni ruxsatsiz o'zgartirma. Yangi bog'liqlik uchun sabab, muqobil va litsenziyani yoz.
- Pul uchun `f32`/`f64`/`double`/`num`/JS `number` yo'q. UI'da pul hisobi yo'q. Yaxlitlash faqat `round_half_up`.
- Production Rust kodida `unwrap()`, `expect()`, `panic!` yo'q (testlar bundan mustasno). `unsafe` faqat FFI va Windows API chaqiruvlarida, izoh bilan asoslanadi.
- Adapterlarda (`bindings/flutter`, `src-tauri`) biznes mantiq yo'q.
- Generatsiya qilingan fayllar (FRB, specta, i18n, tokens) qo'lda tahrirlanmaydi.
- Har bir yangi Tauri command uchun capability ruxsati aniq yoziladi.
- Loglarda shaxsiy yoki moliyaviy ma'lumot yo'q.
- Jurnal yozuvlari hech qachon tahrirlanmaydi yoki o'chirilmaydi.
- Noaniq joyda taxmin qilmasdan so'ra. Javobsiz savollarni `docs/OPEN_QUESTIONS.md` ga yoz (kimga: mahsulot egasi / ulamo / yurist).
- Har vazifa oxirida `docs/CHANGELOG.md` ni yangila.

### «Tayyor» ta'rifi (har vazifa uchun)
- Barcha CI workflow'lari yashil; `clippy`, `flutter analyze`, ESLint — 0 ogohlantirish.
- Yangi domen mantiqi testlar bilan qoplangan; pul funksiyalari vektor bilan.
- UI matnlari `shared/i18n` da (`uz`, `uz-Cyrl`, `ru`); taqiqlangan iboralar linteri yashil.
- Maxfiy ma'lumot loglarda yo'q.
- `CHANGELOG.md` va `OPEN_QUESTIONS.md` yangilangan.

---

## 17. DOIRADAN TASHQARIDA (1-relizda qilinmaydi)
- Server sinxronlashi va akkauntlar (R1 gacha).
- Bank va karta integratsiyalari (CSV importdan tashqari), fiskal kassa va soliq portali integratsiyasi.
- Ikkinchi tomon, hakam yoki sherikning o'z qurilmasidan masofadan tasdiqlashi.
- Real pul o'tkazmalari, sheriklar yoki investorlar uchun platforma/marketplace.
- iOS (arxitektura to'sqinlik qilmaydi, lekin rejada yo'q).
- Boshqa mualliflarning qissa matnlari — ishlatilmaydi (2.1).

## 18. RELIZDAN OLDIN KODDAN TASHQARIDA HAL QILINADIGAN MASALALAR
- ~~Kontent va brend litsenziyasi~~ — kerak emas: ilova boshqa mualliflarning matni, personajlari va brendini ishlatmaydi (2.1, 2026-10-23).
- Diniy matnlar, sheriklik, nasiya va zakot qoidalarining ulamo tekshiruvi.
- Tilxat, shartnoma va xodim kelishuvi shablonlarining yurist ko'rigi.
- Windows kod imzolash sertifikati (OV/EV), keyinroq macOS Developer ID; Play Console hisobi.
- Maxfiylik siyosati (shaxsga doir ma'lumotlar to'g'risidagi qonun); Kasb-kor uchun mijoz ma'lumotlari bo'yicha yo'riqnoma.

---

## ILOVA A. LEGACY HUJJATLARDAGI O'ZGARISHLAR
| Hujjat va joy | Eski ko'rsatma | Yangi qoida |
|---|---|---|
| `uy/SPEC.md` 4.1 | Drift + SQLCipher (Dart) | Rust `storage` (rusqlite + SQLCipher) FRB orqali |
| `uy/SPEC.md` 4.1 | Backend: Ktor + PostgreSQL | Relay: axum + PostgreSQL (3.4, ADR bilan) |
| `uy/SPEC.md` 4.2, `MVP_PLAN` V3 | Dart `core/money` | Rust `money` crate (5-bo'lim) |
| `uy/SPEC.md` 4.4 | Umumiy maydonlar | + `space_id`, `origin_device_id`, `updated_by_device_id` (8.1) |
| `uy/SPEC.md` 4.5, `MVP_PLAN` V2 | PIN — faqat tekshiruv uchun hosila; Keystore DB kalitini wrap qiladi | 7.2 kalit iyerarxiyasi (platforma siri + PIN, tiklash kodi, BIO slot) |
| `uy/SPEC.md` 6 | TLS va certificate pinning | Offline relizda tarmoq yo'q; R1 bilan birga qayta ko'riladi |
| `MVP_PLAN` V1 | Faqat Flutter skeleti | Y1 (monorepo, FRB, Tauri, xtask, CI) |
| `MVP_PLAN` V3 | `core/pdf` (`pdf` paketi) | Rust `pdf` crate (typst), 9-bo'lim |
| `MVP_PLAN` V5, `DESKTOP` 5.3 | «Izohsiz summa» formulasi | 5.9 (qoldiq o'zgarishi bilan) |
| `MVP_PLAN` V15 | «Butun baza shifrlangan fayl» | `.baraka` formati (8.3), desktop bilan bir xil |
| `DESKTOP` 3.1 | `crates/` desktop ichida | `core/crates/` — umumiy (4.1) |
| `DESKTOP` 4 | Pul qoidalari | 5-bo'lim (manfiy allocate, yaxlitlash simmetriyasi, valyuta exponent'i, formatlash kod nuqtalari) |
| `DESKTOP` 5.1 | Vektorlar git submodule yoki alohida repo | Monorepo ichida `spec/` |
| `DESKTOP` 6.2 | Keyring + PIN bilan qo'shimcha wrap | 7.2 (ikkala omil HKDF orqali birlashtiriladi) |
| `DESKTOP` 6.2 | Windows Hello — `UserConsentVerifier` | `KeyCredentialManager` (7.3) |
| `DESKTOP` 6.3 | `version` kattasi yutadi | 8.4 (ikki tomonda o'zgargan = ziddiyat) |
| `DESKTOP` 9 (D1–D15) | Alohida desktop vazifalari | U1–U15 ning (c) qismlari |
| `DESKTOP` «D2. 6-tamoyil poydevori» sarlavhasi | D2 vazifasi bilan nomi to'qnashadi | ahamiyatsiz — U7 ga birlashtirildi |
