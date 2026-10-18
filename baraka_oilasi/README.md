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
| [docs/kasbkor/SPEC.md](docs/kasbkor/SPEC.md) | Kasb-kor makoni spetsifikatsiyasi (K0, qoralama) |
| [CLAUDE.md](CLAUDE.md) | AI-dasturchi uchun sessiya qoidalari |

Mustaqil oracle'ni tekshirish: `python3 -I spec/oracle/oracle.py --selftest`; `.baraka` formati — `python3 -I spec/interchange/oracle.py --check spec/interchange/vectors.json` (`cryptography` kerak).

## Holat (1-sessiya)
| Qism | Holat |
|---|---|
| Rust yadro: `money`, `journal`, `security`, `storage`, `domain-uy`, `agreements`, `app` (sessiya va use-case'lar) | ✅ testlar bilan |
| Oltin vektorlar (28 suite, 191 case) + mustaqil Python oracle | ✅ |
| `cargo xtask`: i18n (uz, uz-Cyrl, ru), taqiqlangan iboralar, dizayn tokenlari | ✅ |
| Desktop: Tauri 2 + React, Claude Code dark theme (sozlash, qulf, bosh sahifa, daromad, Kelajagim, xarajat, audit, qarzlar inventari, «to'xta va o'yla», qarz tilxati → jurnal → PDF, «Qarzdan chiqish», marosimlar, sheriklik, kelishuvlar markazi, sinxronlash, sozlamalar) | ✅ Linux'da yig'ildi va tekshirildi; Windows NSIS — CI'da yashil |
| PDF (typst): qarz tilxati, marosim smetasi, sheriklik shartnomasi (chizilgan imzolar bilan), sheriklik davri hisoboti, ko'rik bayonnomasi, hakam uchun ish papkasi, uz / uz-Cyrl / ru | ✅ |
| U8: qarz inventari, haqiqiy narx, friction, tilxat (jurnal bilan) | ✅ yadro + desktop; Android UI — keyingi sessiya |
| U9: «Qarzdan chiqish» 70/20/10, rejalovchi (grafik), «Qarzsiz kun», buyumlar, to'lovchilar | ✅ yadro + desktop; Android UI — keyingi sessiya |
| U10: marosim rejalovchisi — 2–3 stsenariy, «qarzsiz qanday o'tkazamiz?» muhokamasi, tasdiqlash qulfi, smeta PDF, «To'yona o'rniga» maqsad | ✅ yadro + desktop; Android UI — keyingi sessiya |
| U11: sheriklik (mudoraba / musharaka), 9 savolli shartnoma ustasi, versiyalar va chizilgan imzolar, buyout, darvoza va oilaviy rozilik | ✅ yadro + desktop; Android UI — keyingi sessiya |
| U12: kassa daftari (cheklar bilan, o'zgarmas), davrni yopish va avtomatik taqsimot (zararni tiklash, buyout ayirmasi), sherik uchun hisobot PDF, «Hunardan ishga», «Taklifni tekshirish» | ✅ yadro + desktop; Android UI — keyingi sessiya |
| U13: vazifa hodisalari, oylik ochiq hisob ko'rigi (bayonnoma + zanjir boshi), «katta foyda»da qayta o'qish, nizo va hakam (taqsimot bloki, ish papkasi PDF), yillik yangilash, oilaviy kelishuvlar, kelishuvlar markazi va eslatmalar | ✅ yadro + desktop; Android UI — keyingi sessiya |
| U14: `.baraka` eksport/import (shifrlangan, yagona sxema), uch tomonlama birlashtirish va ziddiyat tanlovi, jurnal ayrilishini aniqlash, zaxira nusxa, QR/kod bilan yangi qurilmani ulash | ✅ yadro + desktop + Python oracle; Android UI — keyingi sessiya |
| U15: 5 qadamli onboarding (daromad ritmi, qarz savoli), sozlamalar (qurilma tili, shrift, mavzu), bosh sahifa eslatmalari, accessibility (WCAG kontrast tekshiruvi, axe, klaviatura, High Contrast), yakuniy E2E (`tauri-driver`), reliz cheklisti | ✅ yadro + desktop + Linux E2E; Windows imzo/E2E va Android UI — keyingi sessiya |
| K0: Kasb-kor makoni spetsifikatsiyasi (`docs/kasbkor/SPEC.md`) | 📝 qoralama v0.1 — mahsulot egasi tasdig'i kutilmoqda |
| K1: Kasb-kor «ikki cho'ntak» — tushum/chiqim, «egasi oldi», kapital, naqd kassa va karta, egasi maoshi va uni Uy'ga atomar o'tkazish | ✅ yadro + desktop + Linux E2E; Android UI — keyingi sessiya |
| K2: Kasb-kor haqiqiy foyda — o'z mehnati, oilaviy mehnat, uskunalar va eskirish, buyurtma kalkulyatori | ✅ yadro + desktop + Linux E2E; Android UI — keyingi sessiya |
| K3: Kasb-kor «Hisob kuni» — soliq zaxirasi, egasi maoshi, taqsimot qoidasi, o'zgarmas bayonnoma va PDF, yopilgan oyni himoyalash | ✅ yadro + desktop + Linux E2E; Android UI — keyingi sessiya |
| K4: Kasb-kor kunlik kassa yopish, nasiya daftari (ustamasiz), yosh guruhlari va haftalik ko'rik | ✅ yadro + desktop + Linux E2E; Android UI — keyingi sessiya |
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

Yakuniy E2E (haqiqiy ilova, `tauri-driver`): `apps/desktop/e2e/README.md`. Reliz oldidan: `docs/RELEASE_CHECKLIST.md`.
