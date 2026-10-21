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
| [docs/adr/0003-kop-qurilma-va-rollar.md](docs/adr/0003-kop-qurilma-va-rollar.md) | Kasb-kor: ko'p qurilma va rollar (K8) |
| [docs/adr/0004-musofir-uy-qurilmasi.md](docs/adr/0004-musofir-uy-qurilmasi.md) | Musofir: uydagi oila qurilmasi (M2) |
| [docs/OPEN_QUESTIONS.md](docs/OPEN_QUESTIONS.md) | Mahsulot egasi, ulamo va yurist uchun ochiq savollar |
| [docs/uy/](docs/uy/) | «Baraka daftari» spetsifikatsiyasi va dastlabki rejalar |
| [docs/kasbkor/SPEC.md](docs/kasbkor/SPEC.md) | Kasb-kor makoni spetsifikatsiyasi (K0, qoralama) |
| [docs/musofir/SPEC.md](docs/musofir/SPEC.md) | Musofir makoni spetsifikatsiyasi (v1.0, tasdiqlangan) |
| [CLAUDE.md](CLAUDE.md) | AI-dasturchi uchun sessiya qoidalari |

Mustaqil oracle'ni tekshirish: `python3 -I spec/oracle/oracle.py --selftest`; `.baraka` formati — `python3 -I spec/interchange/oracle.py --check spec/interchange/vectors.json` (`cryptography` kerak).

## Holat (1.0.0)
| Qism | Holat |
|---|---|
| Rust yadro: `money`, `journal`, `security`, `storage`, `domain-uy`, `agreements`, `app` (sessiya va use-case'lar) | ✅ testlar bilan |
| Oltin vektorlar (28 suite, 191 case) + mustaqil Python oracle | ✅ |
| `cargo xtask`: i18n (uz, uz-Cyrl, ru), taqiqlangan iboralar, dizayn tokenlari | ✅ |
| Desktop: Tauri 2 + React, Claude Code dark theme (sozlash, qulf, bosh sahifa, daromad, Kelajagim, xarajat, audit, qarzlar inventari, «to'xta va o'yla», qarz tilxati → jurnal → PDF, «Qarzdan chiqish», marosimlar, sheriklik, kelishuvlar markazi, sinxronlash, sozlamalar) | ✅ Linux'da yig'ildi va tekshirildi; Windows NSIS — CI'da yashil |
| PDF (typst): qarz tilxati, marosim smetasi, sheriklik shartnomasi (chizilgan imzolar bilan), sheriklik davri hisoboti, ko'rik bayonnomasi, hakam uchun ish papkasi, uz / uz-Cyrl / ru | ✅ |
| U8: qarz inventari, haqiqiy narx, friction, tilxat (jurnal bilan) | ✅ yadro + desktop + Android |
| U9: «Qarzdan chiqish» 70/20/10, rejalovchi (grafik), «Qarzsiz kun», buyumlar, to'lovchilar | ✅ yadro + desktop + Android |
| U10: marosim rejalovchisi — 2–3 stsenariy, «qarzsiz qanday o'tkazamiz?» muhokamasi, tasdiqlash qulfi, smeta PDF, «To'yona o'rniga» maqsad | ✅ yadro + desktop + Android |
| U11: sheriklik (mudoraba / musharaka), 9 savolli shartnoma ustasi, versiyalar va chizilgan imzolar, buyout, darvoza va oilaviy rozilik | ✅ yadro + desktop + Android |
| U12: kassa daftari (cheklar bilan, o'zgarmas), davrni yopish va avtomatik taqsimot (zararni tiklash, buyout ayirmasi), sherik uchun hisobot PDF, «Hunardan ishga», «Taklifni tekshirish» | ✅ yadro + desktop + Android |
| U13: vazifa hodisalari, oylik ochiq hisob ko'rigi (bayonnoma + zanjir boshi), «katta foyda»da qayta o'qish, nizo va hakam (taqsimot bloki, ish papkasi PDF), yillik yangilash, oilaviy kelishuvlar, kelishuvlar markazi va eslatmalar | ✅ yadro + desktop + Android |
| U14: `.baraka` eksport/import (shifrlangan, yagona sxema), uch tomonlama birlashtirish va ziddiyat tanlovi, jurnal ayrilishini aniqlash, zaxira nusxa, QR/kod bilan yangi qurilmani ulash | ✅ yadro + desktop + Python oracle + Android |
| U15: 5 qadamli onboarding (daromad ritmi, qarz savoli), sozlamalar (qurilma tili, shrift, mavzu), bosh sahifa eslatmalari, accessibility (WCAG kontrast tekshiruvi, axe, klaviatura, High Contrast), yakuniy E2E (`tauri-driver`), reliz cheklisti | ✅ yadro + desktop + Linux E2E + Android; Windows kod imzosi — sertifikat kelgach |
| K0: Kasb-kor makoni spetsifikatsiyasi (`docs/kasbkor/SPEC.md`) | 📝 qoralama v0.1 — mahsulot egasi tasdig'i kutilmoqda |
| K1: Kasb-kor «ikki cho'ntak» — tushum/chiqim, «egasi oldi», kapital, naqd kassa va karta, egasi maoshi va uni Uy'ga atomar o'tkazish | ✅ yadro + desktop + Linux E2E + Android |
| K2: Kasb-kor haqiqiy foyda — o'z mehnati, oilaviy mehnat, uskunalar va eskirish, buyurtma kalkulyatori | ✅ yadro + desktop + Linux E2E + Android |
| K3: Kasb-kor «Hisob kuni» — soliq zaxirasi, egasi maoshi, taqsimot qoidasi, o'zgarmas bayonnoma va PDF, yopilgan oyni himoyalash | ✅ yadro + desktop + Linux E2E + Android |
| K4: Kasb-kor kunlik kassa yopish, nasiya daftari (ustamasiz), yosh guruhlari va haftalik ko'rik | ✅ yadro + desktop + Linux E2E + Android |
| K5: Kasb-kor tovar qoldig'i — o'rtacha/FIFO tannarx, qayta tiklash narxi («inflyatsiya yegan kapital»), muzlagan tovar | ✅ yadro + desktop + Linux E2E + Android |
| K6: Kasb-kor xodim va ta'minotchi kelishuvlari (`reviewStatus` li shablonlar), foizsiz va jarimasiz avans, oylik varaqcha, ta'minotchiga qarz | ✅ yadro + desktop + Linux E2E + Android |
| K7: Kasb-kor kengayish darvozasi (5 shart va keyingi qadamlar), «Hisob kuni» konvertlari va soliq zaxirasi, halol muqobillar, zakot hisobi (hijriy «Zakot kuni», hisob — fatvo emas), tarozi tekshiruvi, yillik inventarizatsiya | ✅ yadro + desktop + Linux E2E + Android |
| K8: Kasb-kor ko'p qurilma va rollar (ADR-0003) — sotuvchi qurilmasi (sotuv, nasiya to'lovi, smena; foyda ma'lumoti unga yuborilmaydi), hisobchi (faqat o'qish), egasida yozish filtri va bekor qilish | ✅ yadro + desktop + Linux E2E + Android |
| M0: Musofir makoni spetsifikatsiyasi (`docs/musofir/SPEC.md`) | ✅ v1.0 — mahsulot egasi tasdiqladi (2026-10-19) |
| M1: Musofir — ish valyutasi va kurs (taxminsiz), chet eldagi maosh va xarajat, uyga yuborilgan (komissiya bilan), o'z ulushi va qaytish jamg'armasi, qaytish sanasigacha prognoz | ✅ yadro + desktop + Linux E2E + Android |
| M2: Musofir «Ikki qirg'oq» — yuborishning maqsadlari, oila bilan kelishuv (kattalar tasdig'i), uyda qabul va maqsad bo'yicha xarajat; uydagi oila qurilmasi (ADR-0004) — musofirning shaxsiy hisobi unga yuborilmaydi | ✅ yadro + desktop + Linux E2E + Android |
| M3: Musofir — yo'l qarzidan chiqish («Qarz to'lovi» maqsadidan uyda to'lanadi, necha oyda yopilishi), «Qaytdim» va 90 kunlik sovutish davri, katta qaror oldidan tekshiruv va qarorlar jurnali | ✅ yadro + desktop + Linux E2E + Android |
| M4: Musofir — qorovul pul (o'z ulushi avval qorovulga, keyin jamg'armaga), ish boshlash summasi («Hunardan ishga» g'oyasi bilan), qaror natijasi | ✅ yadro + desktop + Linux E2E + Android |
| M5: Musofir — 7-qonun qissasidan: «besh xavf belgisi» (3 yangi savol, «ikki belgi — qoching»), qal'a devori (6 oylik ro'zg'or, erkin pul), valyutada olib kelingan summa, va'daning yillik hisobi | ✅ yadro + desktop + Linux E2E + Android |
| Android (A0–A4): Flutter ilova — FRB (DTO'lar yadrodan), Keystore platforma siri, `FLAG_SECURE`, onboarding, qulf va avto-qulf; uchala makonning barcha ekranlari desktop bilan bir xil (Uy, Kasb-kor va sotuvchi qurilmasi, Musofir va «Ikki qirg'oq»); oqim testlari haqiqiy yadro bilan, vektorlar Dart'dan; release APK arm64 ≈ 31 MB yuklab olish | ✅ |

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
```bash
# Android (Flutter 3.47.6, Android SDK 36, NDK 28.2, cargo-ndk; ADR-0002)
cargo xtask codegen                  # FRB + Pigeon (generatsiya, qo'lda tahrirlanmaydi)
cargo build -p baraka-bindings-flutter --features vectors   # testlar uchun host yadro
cd apps/android
flutter analyze && flutter test      # haqiqiy yadro bilan oqim testlari
flutter build apk --release --split-per-abi --target-platform android-arm64,android-arm
```
Headless Linux'da OS keyring bo'lmasa, faqat debug build uchun: `BARAKA_INSECURE_DEV_SECRET=1`.

Yakuniy E2E (haqiqiy ilova, `tauri-driver`): `apps/desktop/e2e/README.md`. Reliz oldidan: `docs/RELEASE_CHECKLIST.md`.
