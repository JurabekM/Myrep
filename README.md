# Baraka Daftari — Desktop

Ribosiz (islom moliyasi tamoyillari asosidagi) shaxsiy va oilaviy moliya daftari. Windows 10/11 uchun
**Tauri 2 + Rust + React (TypeScript)** ilovasi. Ma'lumotlar faqat shu kompyuterda saqlanadi: server, akkaunt
va telemetriya yo'q.

> Ta'limiy material. Fatvo yoki moliyaviy maslahat emas.

## Talablar

| Nima                            | Qanday                                                              |
| ------------------------------- | ------------------------------------------------------------------- |
| Windows 10/11 (x64)             | Asosiy platforma                                                    |
| Visual Studio Build Tools 2022  | «Desktop development with C++» (MSVC va Windows SDK)                |
| Microsoft Edge WebView2 Runtime | Windows 10/11 da odatda o'rnatilgan                                 |
| Node.js 24 LTS                  | nodejs.org                                                          |
| pnpm 12.11.2                    | `npm i -g pnpm@12.11.2` (versiya `package.json` da qotirilgan)      |
| Rust 1.97.1                     | rustup o'rnatilgan bo'lsa, `rust-toolchain.toml` uni o'zi oladi     |
| Python 3 + Pillow               | Faqat ikonkani qayta yaratish uchun: `python -m pip install pillow` |

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

## Tekshiruvlar

```bash
pnpm format:check
pnpm lint
pnpm typecheck
pnpm test
cargo fmt --all -- --check
cargo clippy --workspace --all-targets -- -D warnings
cargo test --workspace
```

`cargo test` TypeScript bindinglarini (`ui/src/bindings/bindings.ts`) qayta yaratadi. Agar fayl o'zgarsa, bu Rust
commandlari bilan frontend o'rtasida nomuvofiqlik bor degani — `git diff ui/src/bindings` bilan tekshiring.

## O'rnatish fayli (NSIS)

```bash
pnpm build
```

Natija: `target/release/bundle/nsis/` papkasida `Baraka Daftari_<versiya>_x64-setup.exe` (yoki
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

Keyingi bosqichlar uchun Cargo workspace'ga `crates/` (money, domain, storage va boshqalar) qo'shiladi
(DESKTOP_PROMPT.md 3.1).

## Xavfsizlik

- **CSP:** `script-src 'self'` — tashqi skript yo'q, `unsafe-eval` yo'q. Shriftlar va rasmlar ilova ichida.
  `style-src 'unsafe-inline'` — Radix va popper komponentlari inline uslub qo'yadi.
- **Ruxsatlar:** faqat `get_app_info` command va yadro standarti. `shell`, `http`, `fs` pluginlari yoqilmagan.
- **Release:** DevTools yoqilmagan (`devtools` xususiyati kiritilmagan).

## Hujjatlar

- [`docs/SPEC.md`](docs/SPEC.md) — mahsulot spetsifikatsiyasi (FINTECH_PROMPT v0.8)
- [`docs/DESKTOP_PROMPT.md`](docs/DESKTOP_PROMPT.md) — desktop stek, arxitektura va ish rejasi
- [`docs/MVP_PLAN.md`](docs/MVP_PLAN.md) — mobil (Flutter) MVP rejasi
- [`docs/CHANGELOG.md`](docs/CHANGELOG.md) — o'zgarishlar tarixi
- [`docs/OPEN_QUESTIONS.md`](docs/OPEN_QUESTIONS.md) — javobsiz savollar
