# Baraka Dastur — Desktop

Ribosiz (islom moliyasi tamoyillari asosidagi) shaxsiy va oilaviy moliya daftari. Windows 10/11 uchun
**Tauri 2 + Rust + React (TypeScript)** ilovasi. Ma'lumotlar faqat shu kompyuterda saqlanadi: server, akkaunt
va telemetriya yo'q.

> Ta'limiy material. Fatvo yoki moliyaviy maslahat emas.

## Talablar

| Nima                            | Qanday                                                                     |
| ------------------------------- | -------------------------------------------------------------------------- |
| Windows 10/11 (x64)             | Asosiy platforma                                                           |
| Visual Studio Build Tools 2022  | «Desktop development with C++» (MSVC va Windows SDK)                       |
| Microsoft Edge WebView2 Runtime | Windows 10/11 da odatda o'rnatilgan                                        |
| Node.js 24 LTS                  | nodejs.org                                                                 |
| pnpm 12.11.2                    | `npm i -g pnpm@12.11.2` (versiya `package.json` da qotirilgan)             |
| Rust 1.97.1                     | rustup o'rnatilgan bo'lsa, `rust-toolchain.toml` uni o'zi oladi            |
| Python 3 + Pillow               | Faqat ikonkani qayta yaratish uchun: `python -m pip install pillow`        |
| Perl (to'liq, Windows)          | SQLCipher ni yig'ish uchun. Git bilan kelgan perl yetmaydi (pastga qarang) |

## Ishga tushirish

```bash
pnpm install
pnpm dev
```

`pnpm dev` ilovani ishlab chiqish rejimida ochadi. Frontend o'zgarishlari darhol ko'rinadi.

**Windows: uzun yo'l muammosi.** Repo papkasi uzun bo'lsa, Rust chiqish fayllari `MAX_PATH` (260 belgi) chegarasiga
urilishi mumkin. Buning oldini olish uchun chiqish papkasini qisqa yo'lga qo'ying (PowerShell, bir marta):

```powershell
$env:CARGO_TARGET_DIR = "C:\cargo-targets\baraka-daftari"
```

**Windows: SQLCipher va Perl.** Shifrlangan baza OpenSSL'ni manba kodidan yig'adi, buning uchun to'liq Perl kerak
(`Locale::Maketext::Simple` moduli bilan). Git bilan kelgan perl (`C:\Program Files\Git\usr\bin\perl.exe`) bunga yetmaydi
va build `Can't locate Locale/Maketext/Simple.pm` deb yiqiladi. Bunday holda to'liq perl.exe yo'lini ko'rsating:

```powershell
$env:OPENSSL_SRC_PERL = "C:\path\to\perl\bin\perl.exe"
```

CI (GitHub Actions) Windows runner'ida to'liq perl bor deb taxmin qilinadi; buni birinchi CI yurgizishda tekshirish kerak
(docs/OPEN_QUESTIONS.md).

## Tekshiruvlar

```bash
pnpm format:check
pnpm lint
pnpm typecheck
pnpm test
cargo fmt --all -- --check
cargo clippy --workspace --all-targets -- -D warnings
cargo test --workspace
cargo test -p baraka-vectors
```

Pul hisobi (`crates/money`) qamrovi kamida 95 % bo'lishi shart. Qamrovni o'lchash uchun bir martalik o'rnatish:
`cargo install cargo-llvm-cov --locked` va `rustup component add llvm-tools-preview`. Keyin:

```bash
cargo llvm-cov -p baraka-money -p baraka-vectors --ignore-filename-regex '(tests|vectors)[\\/]' --summary-only
```

`cargo test` TypeScript bindinglarini (`ui/src/bindings/bindings.ts`) qayta yaratadi. Agar fayl o'zgarsa, bu Rust
commandlari bilan frontend o'rtasida nomuvofiqlik bor degani — `git diff ui/src/bindings` bilan tekshiring.

## O'rnatish fayli (NSIS)

```bash
pnpm build
```

Natija: `target/release/bundle/nsis/` papkasida `Baraka Dastur_<versiya>_x64-setup.exe` (yoki
`CARGO_TARGET_DIR` ichida). O'rnatish joriy foydalanuvchi uchun bo'ladi, administrator huquqi shart emas.
Kod imzolash hali sozlanmagan (docs/OPEN_QUESTIONS.md).

## Loyiha tuzilmasi

```
src-tauri/     Tauri ilovasi: oyna, commandlar (yupqa qatlam), ruxsatlar (capabilities)
ui/            React ilovasi: sahifalar, komponentlar, i18n (uz, ru), testlar
ui/src/bindings/  Rust commandlaridan avtomatik yaratilgan TypeScript tiplari (qo'lda tahrirlamang)
scripts/       make_icon.py — ilova ikonkasini yaratadi
docs/          SPEC.md, DESKTOP_PROMPT.md, MVP_PLAN.md, CHANGELOG.md, OPEN_QUESTIONS.md
```

Pul hisobi `crates/money` da (Money, allocate, percent_of, FxRate, formatlash). Umumiy test vektorlari
`spec/test-vectors/` da, ularni yurgizuvchi runner `crates/vectors` da. Qolgan crate'lar: `crates/domain`
(domen modeli), `crates/security` (PIN, kalit, lockout, keyring, avto-qulflash), `crates/storage` (SQLCipher baza,
migratsiyalar, repo'lar). Keyingi crate'lar keyingi bosqichlarda qo'shiladi (DESKTOP_PROMPT.md 3.1).

## Xavfsizlik

- **Shifrlash:** ma'lumotlar bazasi SQLCipher bilan shifrlangan. Fayl kalitsiz ochilmaydi.
- **Kalit modeli (DESKTOP_PROMPT.md 6.2):** baza kaliti tasodifiy 256 bit. U ikki qatlamda o'raladi: PIN (6 raqam)
  dan Argon2id bilan hosil qilingan kalit va OS keyring'idagi qurilma kaliti (Windows Credential Manager). Faqat PIN
  ham, faqat keyring ham yetarli emas.
- **Noto'g'ri PIN:** 3-urinishdan keyin kutish qo'yiladi (30 s, 60 s, 5 daqiqa, 15 daqiqa, keyin 1 soat).
- **Avto-qulflash:** oyna fokusdan tushib 5 daqiqa o'tsa, baza qulflanadi. Qo'lda qulflash: yon paneldagi «Qulflash» yoki `Ctrl+L`.
- **Ekran surati:** relizda oyna ekran suratiga va ekran yozuvga tushmaydi (`set_content_protected`). Ishlab chiqish
  rejimida bu o'chiq.
- **Kalit fayli:** `%APPDATA%\uz.barakadaftari.desktop\keys.bin`. PIN unutilsa, ma'lumotlarni tiklab bo'lmaydi.
- **CSP:** `script-src 'self'` — tashqi skript yo'q, `unsafe-eval` yo'q. Shriftlar va rasmlar ilova ichida.
  `style-src 'unsafe-inline'` — Radix va popper komponentlari inline uslub qo'yadi.
- **Ruxsatlar:** faqat ilova commandlari (`get_app_info`, `get_security_status`, `setup_pin`, `unlock`, `lock`) va yadro
  standarti. `shell`, `http`, `fs` pluginlari yoqilmagan.
- **Release:** DevTools yoqilmagan (`devtools` xususiyati kiritilmagan).

## Hujjatlar

- [`docs/SPEC.md`](docs/SPEC.md) — mahsulot spetsifikatsiyasi (FINTECH_PROMPT v0.8)
- [`docs/DESKTOP_PROMPT.md`](docs/DESKTOP_PROMPT.md) — desktop stek, arxitektura va ish rejasi
- [`docs/MVP_PLAN.md`](docs/MVP_PLAN.md) — mobil (Flutter) MVP rejasi
- [`docs/CHANGELOG.md`](docs/CHANGELOG.md) — o'zgarishlar tarixi
- [`docs/OPEN_QUESTIONS.md`](docs/OPEN_QUESTIONS.md) — javobsiz savollar
