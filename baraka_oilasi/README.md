# Baraka oilasi

Halol (ribosiz) moliyaviy odatlar uchun bitta ilova, uchta makon:

- **Uy** («Baraka daftari») — oila moliyasi;
- **Kasb-kor** — o'zini o'zi band qilganlar va kichik biznes;
- **Musofir** — chet elda ishlaydiganlar va ularning oilasi.

Hamma makon bitta Rust yadroga tayanadi. Android ilovasi Flutter va Kotlin'da, desktop ilovasi Tauri 2 va React'da yoziladi.

| Hujjat | Mazmuni |
|---|---|
| [docs/BARAKA_OILASI.md](docs/BARAKA_OILASI.md) | Bosh loyiha prompti: stek, arxitektura, pul algoritmlari, xavfsizlik, ish rejasi |
| [docs/adr/0001-umumiy-rust-yadro.md](docs/adr/0001-umumiy-rust-yadro.md) | Asosiy arxitektura qarori |
| [docs/OPEN_QUESTIONS.md](docs/OPEN_QUESTIONS.md) | Mahsulot egasi, ulamo va yurist uchun ochiq savollar |
| [docs/uy/](docs/uy/) | «Baraka daftari» spetsifikatsiyasi va dastlabki rejalar |
| [CLAUDE.md](CLAUDE.md) | AI-dasturchi uchun sessiya qoidalari |

Mustaqil oracle'ni tekshirish: `python3 -I spec/oracle/oracle.py --selftest`

## Holat (1-sessiya)
| Qism | Holat |
|---|---|
| Rust yadro: `money`, `journal`, `security`, `storage`, `domain-uy`, `agreements`, `app` (sessiya va use-case'lar) | ✅ testlar bilan |
| Oltin vektorlar (16 suite, 81 case) + mustaqil Python oracle | ✅ |
| `cargo xtask`: i18n (uz, uz-Cyrl, ru), taqiqlangan iboralar, dizayn tokenlari | ✅ |
| Desktop: Tauri 2 + React, Claude Code dark theme (sozlash, qulf, bosh sahifa, daromad, Kelajagim, xarajat, audit, qarz, qarz tilxati PDF) | ✅ Linux'da yig'ildi va tekshirildi; Windows NSIS — CI'da yashil |
| PDF (typst): qarz tilxati, uz / uz-Cyrl / ru | ✅ |
| Android: FRB API sirti (`core/bindings/flutter`) | ✅; Flutter ilovasi — keyingi sessiya |

## Ishga tushirish
```bash
# Yadro
cargo test --workspace
cargo clippy --workspace --all-targets --all-features -- -D warnings
python3 -I spec/oracle/oracle.py --check spec/test-vectors
cargo xtask all                      # i18n, tokenlar, lint

# Desktop (Windows'da: Visual Studio Build Tools + WebView2; Linux'da: libwebkit2gtk-4.1-dev)
cd apps/desktop
pnpm --dir ui install
(cd src-tauri && cargo test)         # ui/src/bindings.ts ni yangilaydi
ui/node_modules/.bin/tauri dev       # ishlab chiqish
ui/node_modules/.bin/tauri build --bundles nsis   # Windows o'rnatuvchi → ../../target/release/bundle/nsis/
```
Headless Linux'da OS keyring bo'lmasa, faqat debug build uchun: `BARAKA_INSECURE_DEV_SECRET=1`.
