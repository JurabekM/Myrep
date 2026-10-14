# Ochiq savollar

Har bir savol: nima kerak, kim hal qiladi, qachon kerak bo'ladi. Hal bo'lgach, «Hal qilingan» bo'limiga ko'chiriladi va qaror sanasi yoziladi.

## Qaror kutilmoqda

1. **Mobil (Flutter) MVP qayerda davom etadi?** Mobil loyiha alohida worktree'da (`mvp1-fintech-kickoff-56939a`) turibdi, 14A vazifasi boshlanishini kutmoqda. Bu repo — desktop. Mobilni shu repo ichiga (`mobile/`) ko'chirish yoki alohida qoldirish kerakmi? _Kerak: D2 boshlanishidan oldin._
2. **`spec/test-vectors/` ni ulashish usuli.** Mobil va desktop bir xil oltin vektorlardan o'tishi shart (DESKTOP_PROMPT.md 5.1). Variantlar: (a) alohida `baraka-spec` repo + git submodule; (b) vektorlar shu repo'da `spec/` ichida, mobil uni submodule qilib oladi. _Kerak: D2 boshlanishidan oldin._
3. **WebView2 o'rnatish rejimi.** Hozir `downloadBootstrapper`: WebView2 yo'q kompyuterda o'rnatish paytida internet kerak. Mahsulot «to'liq offline» bo'lgani uchun `offlineInstaller` (~+180 MB) variant. _Kerak: D15 (reliz)._
4. **Kod imzolash sertifikati (OV yoki EV).** Imzolanmagan installer Windows SmartScreen ogohlantirishini chiqaradi. Sertifikat sotib olish — foydalanuvchi qarori; CI'da secret sifatida saqlanadi. _Kerak: D15._
5. **Yorug' («daftar» qog'ozi) tema.** DESKTOP_PROMPT.md «light va dark» deydi. Foydalanuvchi talabi: interfeys to'liq qorong'i, Claude Code desktop uslubida. Yorug' tema hozircha qo'shilmaydi. _Kerak: kelajakda, tasdiq bilan._
6. **`style-src 'unsafe-inline'`.** Radix va popper komponentlari inline uslub qo'yadi. `script-src` qat'iy (`'self'`). Keyinroq nonce yoki hash usuliga o'tish mumkin. _Ko'rib chiqiladi: D15._
7. **Native dialog (fayl tanlash) va Common Controls v6.** Hozir `common-controls-v6` o'chirilgan (sabab: `cargo test` test binary'lari comctl32 v6 manifestsiz yiqiladi). Fayl tanlash (CSV import, `.baraka` eksport) kerak bo'lganda `tauri-plugin-dialog` qo'shiladi va testlar uchun manifest yechimi qayta ko'rib chiqiladi. _Kerak: D7 (CSV import) yoki D14 oldidan._
8. **pnpm «minimal chiqarilish yoshi».** pnpm 12 1 kundan yangi paketlarni vaqtincha bloklaydi. Ikki paket (`lucide-react@1.56.0`, `@testing-library/user-event@14.6.8`) `pnpm-workspace.yaml` dagi istisnolar ro'yxatiga avtomatik qo'shildi. _Kerak: 2026-10-21 atrofida istisnolarni tekshirib, olib tashlash._
9. **Ikonka dizayni.** `scripts/make_icon.py`: qorong'i fonda krem «daftar» va geometrik sakkiz burchakli yulduz. 16–256 px o'lchamlarda tekshirildi. Foydalanuvchi ko'rib tasdiqlashi kerak, aks holda o'zgartiriladi. _Kerak: D15 oldidan._
10. **Sozlamalar saqlanishi.** Til tanlovi hozir brauzer `localStorage` da. D3 (shifrlangan baza) dan keyin sozlamalar shifrlangan bazaga ko'chiriladi. _Kerak: D3._
11. **Repo va remote.** `origin` = `JurabekM/Myrep`. Desktop uchun alohida repo kerakmi va kod push qilinsinmi — foydalanuvchi qarori. Hozircha hech narsa push qilinmagan. _Kerak: CI'ni GitHub'da ishga tushirishdan oldin._
12. **Interaktiv (E2E) sinov.** D1 da ilova o'rnatilib, ishga tushirildi va ekran suratlari bilan ko'zdan kechirildi: bosh sahifa, o'chirilgan bo'lim tooltip'i, sozlamalar sahifasi haqiqiy oynada tasdiqlandi. Lekin sichqoncha avtomatizatsiyasi oyna fokusi sababli ishonchsiz bo'ldi, shuning uchun til almashinuvi va boshqa tugmalar haqiqiy oynada to'liq tasdiqlanmadi (jsdom testlari o'tadi). Keyinroq WebDriver (`tauri-driver` + WebdriverIO) bilan E2E yoziladi. _Kerak: D15 (reliz) yoki har bir UI vazifasi oxirida._

## Hal qilingan

- **Tauri versiyasi.** ADR bo'yicha Tauri 2 (stable 2.12.3). Tauri 3 alpha (3.0.0-alpha.4) ishlatilmaydi. _2026-10-14._
- **TypeScript versiyasi.** TypeScript 7.0 `typescript-eslint` bilan mos emas (peer: `<6.1.0`). TypeScript 6.0.3 tanlandi. _2026-10-14._
- **ESLint a11y plagini.** `eslint-plugin-jsx-a11y` ESLint 10 bilan mos emas (peer: ESLint ≤ 9). Tanlandi: ESLint 10, a11y tekshiruvi Testing Library rol bo'yicha so'rovlari orqali. _2026-10-14._
- **Testlarda Windows manifest.** `cargo test` `STATUS_ENTRYPOINT_NOT_FOUND` bilan yiqilgani sabab `common-controls-v6` o'chirildi (7-savolga qarang). _2026-10-14._
- **Installer tili.** NSIS 3.11 da o'zbekcha til fayli (`Uzbek.nlf`) bor. Konfiguratsiyaga qo'shildi: `Uzbek`, `Russian`, `English` (birinchisi — o'zbekcha). Silent o'rnatish sinalgan; interaktiv til tanlovi oynasi qo'lda sinalmagan. _2026-10-14._
- **Release ogohlantirishlari.** `BINDINGS_PATH` va `BINDINGS_HEADER` konstantalari release'da «ishlatilmagan» deb ogohlantirardi — ular faqat debug va test rejimida kompilyatsiya qilinadi. _2026-10-14._
