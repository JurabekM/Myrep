# Ochiq savollar

Har bir savol: nima kerak, kim hal qiladi, qachon kerak bo'ladi. Hal bo'lgach, «Hal qilingan» bo'limiga ko'chiriladi va qaror sanasi yoziladi.

## Qaror kutilmoqda

1. **Mobil (Flutter) MVP qayerda davom etadi?** Mobil loyiha alohida worktree'da (`mvp1-fintech-kickoff-56939a`) turibdi, 14A vazifasi boshlanishini kutmoqda. Bu repo — desktop. D2 mobil repo'siz bajarildi. Mobilni shu repo ichiga (`mobile/`) ko'chirish yoki alohida qoldirish kerakmi? _Kerak: D8A oldidan (mobil bilan birgalikda vektorlarni o'zgartirish boshlanganda)._
2. **`spec/test-vectors/` ni sinxron saqlash usuli.** D2 da to'rtta suite (`allocate`, `percent_of`, `fx_convert`, `money_format`) mobil repo'dan bayt-bayt nusxa qilindi (sha256 mos). Mobil repo'da yana 10 ta suite bor; ularni desktop'ga qanday olib kelish kerak? Variantlar: (a) alohida `baraka-spec` repo + git submodule; (b) shu repo `spec/` ichida asosiy nusxa, mobil uni submodule qiladi; (c) qo'lda nusxa + sha256 tekshiruvi. _Kerak: D8 (amortizatsiya) boshlanishidan oldin._
3. **CODEOWNERS.** Vektor o'zgarishi ikki platforma egasining ma'qulligini talab qiladi (DESKTOP_PROMPT.md 5.4). Egalar kim (GitHub username)? _Kerak: birinchi vektor o'zgarishidan oldin._
4. **Formatlash: EUR `€` va RUB `₽` belgilari.** Mobil implementatsiya shu belgilarni ishlatadi, lekin vektorlarda bu tekshirilmagan (faqat `$` va `soʻm`/`сум` bor). Desktop ham shunday qildi. Tasdiq kerak. _Kerak: D4 (pul ko'rsatish) oldidan._
5. **`percent_of` 10 000 bp dan tashqarida.** Desktop spec'da bu holat yo'q; mobil xulqi (`round_half_up(amount × bp / 10 000)`, masalan 120 % ustama) qabul qilindi. Tasdiq kerak. _Kerak: D10 (qarz foizi va ustama) oldidan._
6. **Kiritilgan matnni summaga aylantirish (`MoneyParser`).** Mobilda bor (`8 000 000`, `8000000,5`, `12.50`); desktop'da hali yo'q. Qoidalar mobil bilan bir xil bo'lsin deb taklif qilinadi. _Kerak: D4 (tez kiritish forma) oldidan._
7. **Yorug' («daftar» qog'ozi) tema.** DESKTOP_PROMPT.md «light va dark» deydi. Foydalanuvchi talabi: interfeys to'liq qorong'i, Claude Code desktop uslubida. Yorug' tema hozircha qo'shilmaydi. _Kerak: kelajakda, tasdiq bilan._
8. **`style-src 'unsafe-inline'`.** Radix va popper komponentlari inline uslub qo'yadi. `script-src` qat'iy (`'self'`). Keyinroq nonce yoki hash usuliga o'tish mumkin. _Ko'rib chiqiladi: D15._
9. **Native dialog (fayl tanlash) va Common Controls v6.** Hozir `common-controls-v6` o'chirilgan (sabab: `cargo test` test binary'lari comctl32 v6 manifestsiz yiqiladi). Fayl tanlash (CSV import, `.baraka` eksport) kerak bo'lganda `tauri-plugin-dialog` qo'shiladi va testlar uchun manifest yechimi qayta ko'rib chiqiladi. _Kerak: D7 (CSV import) yoki D14 oldidan._
10. **pnpm «minimal chiqarilish yoshi».** pnpm 12 1 kundan yangi paketlarni vaqtincha bloklaydi. Ikki paket (`lucide-react@1.56.0`, `@testing-library/user-event@14.6.8`) `pnpm-workspace.yaml` dagi istisnolar ro'yxatiga avtomatik qo'shildi. _Kerak: 2026-10-21 atrofida istisnolarni tekshirib, olib tashlash._
11. **Ikonka dizayni.** `scripts/make_icon.py`: qorong'i fonda krem «daftar» va geometrik sakkiz burchakli yulduz. 16–256 px o'lchamlarda tekshirildi. Foydalanuvchi ko'rib tasdiqlashi kerak, aks holda o'zgartiriladi. _Kerak: D15 oldidan._
12. **Sozlamalar saqlanishi.** Til tanlovi hozir brauzer `localStorage` da. D3 da shifrlangan baza tayyor, lekin sozlamalar hali unga ko'chirilmagan (D4 da, birinchi sozlama yozuvi bilan birga). _Kerak: D4._
13. **Repo va remote.** `origin` = `JurabekM/Myrep`. Desktop uchun alohida repo kerakmi va kod push qilinsinmi — foydalanuvchi qarori. Hozircha hech narsa push qilinmagan. _Kerak: CI'ni GitHub'da ishga tushirishdan oldin._
14. **Interaktiv (E2E) sinov.** D1 da ilova o'rnatilib, ishga tushirildi va ekran suratlari bilan ko'zdan kechirildi: bosh sahifa, o'chirilgan bo'lim tooltip'i, sozlamalar sahifasi haqiqiy oynada tasdiqlandi. Lekin sichqoncha avtomatizatsiyasi oyna fokusi sababli ishonchsiz bo'ldi, shuning uchun til almashinuvi va boshqa tugmalar haqiqiy oynada to'liq tasdiqlanmadi (jsdom testlari o'tadi). Keyinroq WebDriver (`tauri-driver` + WebdriverIO) bilan E2E yoziladi. _Kerak: D15 (reliz) yoki har bir UI vazifasi oxirida._ D3 da haqiqiy ilovada sozlash, qulflash tugmasi, `Ctrl+L`, noto'g'ri PIN, 3 urinishdan keyingi kutish va qayta ochish qo'lda tasdiqlandi (ekran suratlari bilan); til almashinuvi va qolgan tugmalar hali shunday tasdiqlanmagan.

15. **PIN unutilsa, nima bo'ladi?** Hozir tiklash yo'q: PIN unutilsa yoki `keys.bin` yo'qolsa, ma'lumotlar ochilmaydi. Sozlash ekranida ogohlantirish bor. Variantlar: (a) hech narsa (hozirgi holat); (b) bir marta ko'rsatiladigan tiklash kodi, foydalanuvchi qog'ozga yozadi; (c) shifrlangan zaxira (eksport) fayli. Qaror foydalanuvchida. _Kerak: D15 oldidan; afzal — hozir, chunki u kalit modelini o'zgartiradi._
16. **Windows Hello (ixtiyoriy).** DESKTOP_PROMPT.md 6.2 dagi ixtiyoriy variant D3 da kechiktirildi: hozir faqat PIN. Kerak bo'lsa, keyingi bosqichda qo'shiladi. _Kerak: foydalanuvchi xohlasa._
17. **OS qulflash hodisasi.** Win+L va kompyuter uyqusi aniqlanmaydi. Avto-qulflash hozir faqat oyna fokusining yo'qolishi va vaqtga asoslangan. Windows session/power hodisalarini (`WTSRegisterSessionNotification`, suspend) qo'shish kerakmi? _Kerak: D15 oldidan._
18. **Kalit fayli yo'q, baza bor.** `keys.bin` o'chirilib, `daftar.db` qolsa, sozlash yangi kalit bilan eski bazani ochishga urinadi va `INTERNAL` xato beradi. Bunday holatni aniq xabar bilan rad etish kerak (yoki eski bazani zaxiraga ko'chirish). _Kerak: D4 oldidan._
19. **O'rnatuvchi va o'chirishni tekshirish.** D3 da NSIS o'rnatuvchi qayta qurilmadi va o'rnatilmadi (o'rnatish foydalanuvchi kompyuterini o'zgartiradi; D1 da o'chirgandan keyin begona fayl qolgan edi). Silent o'rnatish, ishga tushirish va o'chirish sinovi foydalanuvchi ruxsati bilan. Reliz exe (`target\release`) bilan tekshiruv D3 da o'tkazildi: oyna ekran suratidan chiqarilgan (`WDA_EXCLUDEFROMCAPTURE`), lekin qora emas — orqadagi oyna ko'rinadi. Eski Windows'da xulq tekshirilmagan. _Kerak: D15._
20. **Windows CI'da Perl.** SQLCipher uchun to'liq Perl kerak (README'ga qarang). GitHub Windows runner'ida bu borligi taxmin qilingan, tekshirilmagan. _Kerak: CI birinchi marta ishga tushirilganda (13-band bilan birga)._

## Hal qilingan

- **SQLCipher'ni Windows'da yig'ish (D3, 2026-10-14).** Git bilan kelgan MSYS perl'da `Locale::Maketext::Simple` yo'q edi; to'liq perl `OPENSSL_SRC_PERL` bilan ko'rsatildi. Yangi o'rnatish talab qilinmadi. Qarang: README, «Windows: SQLCipher va Perl».

- **Tauri versiyasi.** ADR bo'yicha Tauri 2 (stable 2.12.3). Tauri 3 alpha (3.0.0-alpha.4) ishlatilmaydi. _2026-10-14._
- **TypeScript versiyasi.** TypeScript 7.0 `typescript-eslint` bilan mos emas (peer: `<6.1.0`). TypeScript 6.0.3 tanlandi. _2026-10-14._
- **ESLint a11y plagini.** `eslint-plugin-jsx-a11y` ESLint 10 bilan mos emas (peer: ESLint ≤ 9). Tanlandi: ESLint 10, a11y tekshiruvi Testing Library rol bo'yicha so'rovlari orqali. _2026-10-14._
- **Testlarda Windows manifest.** `cargo test` `STATUS_ENTRYPOINT_NOT_FOUND` bilan yiqilgani sabab `common-controls-v6` o'chirildi (9-savolga qarang). _2026-10-14._
- **Installer tili.** NSIS 3.11 da o'zbekcha til fayli (`Uzbek.nlf`) bor. Konfiguratsiyaga qo'shildi: `Uzbek`, `Russian`, `English` (birinchisi — o'zbekcha). Silent o'rnatish sinalgan; interaktiv til tanlovi oynasi qo'lda sinalmagan. _2026-10-14._
- **Release ogohlantirishlari.** `BINDINGS_PATH` va `BINDINGS_HEADER` konstantalari release'da «ishlatilmagan» deb ogohlantirardi — ular faqat debug va test rejimida kompilyatsiya qilinadi. _2026-10-14._
- **Manfiy yaxlitlash.** Yarmi noldan uzoqqa (`−12 650,5 → −12 651`) — vektor `fx-004` bilan tasdiqlangan. _2026-10-14._
- **Formatlash qoidalari (uz/ru).** Guruhlash — U+00A0, kasr — vergul (faqat tiyin bo'lsa), valyuta — bo'linmas bo'sh joy bilan; `soʻm` (U+02BB). Mobil implementatsiya va vektorlar bilan bir xil. _2026-10-14._
