# Ochiq savollar

Har bir savol: nima kerak, kim hal qiladi, qachon kerak bo'ladi. Hal bo'lgach, «Hal qilingan» bo'limiga ko'chiriladi va qaror sanasi yoziladi.

## Qaror kutilmoqda

1. **Mobil (Flutter) MVP qayerda davom etadi?** Mobil loyiha alohida worktree'da (`mvp1-fintech-kickoff-56939a`) turibdi, 14A vazifasi boshlanishini kutmoqda. Bu repo — desktop. D2 mobil repo'siz bajarildi. Mobilni shu repo ichiga (`mobile/`) ko'chirish yoki alohida qoldirish kerakmi? _Kerak: D8A oldidan (mobil bilan birgalikda vektorlarni o'zgartirish boshlanganda)._
2. **`spec/test-vectors/` ni sinxron saqlash usuli.** D2 da to'rtta suite (`allocate`, `percent_of`, `fx_convert`, `money_format`) mobil repo'dan bayt-bayt nusxa qilindi (sha256 mos). Mobil repo'da yana 10 ta suite bor; ularni desktop'ga qanday olib kelish kerak? Variantlar: (a) alohida `baraka-spec` repo + git submodule; (b) shu repo `spec/` ichida asosiy nusxa, mobil uni submodule qiladi; (c) qo'lda nusxa + sha256 tekshiruvi. _Kerak: D8 (amortizatsiya) boshlanishidan oldin._
3. **CODEOWNERS.** Vektor o'zgarishi ikki platforma egasining ma'qulligini talab qiladi (DESKTOP_PROMPT.md 5.4). Egalar kim (GitHub username)? _Kerak: birinchi vektor o'zgarishidan oldin._
4. **Formatlash: EUR `€` va RUB `₽` belgilari.** Mobil implementatsiya shu belgilarni ishlatadi, lekin vektorlarda bu tekshirilmagan (faqat `$` va `soʻm`/`сум` bor). Desktop ham shunday qildi. D4 da ko'rsatiladi (`formatted`); tasdiq kutilmoqda._
5. **`percent_of` 10 000 bp dan tashqarida.** Desktop spec'da bu holat yo'q; mobil xulqi (`round_half_up(amount × bp / 10 000)`, masalan 120 % ustama) qabul qilindi. Tasdiq kerak. _Kerak: D10 (qarz foizi va ustama) oldidan._
6. _Hal qilindi (D4) — pastdagi «Hal qilingan» bo'limiga qarang._
7. **Yorug' («daftar» qog'ozi) tema.** DESKTOP_PROMPT.md «light va dark» deydi. Foydalanuvchi talabi: interfeys to'liq qorong'i, Claude Code desktop uslubida. Yorug' tema hozircha qo'shilmaydi. _Kerak: kelajakda, tasdiq bilan._
8. **`style-src 'unsafe-inline'`.** Radix va popper komponentlari inline uslub qo'yadi. `script-src` qat'iy (`'self'`). Keyinroq nonce yoki hash usuliga o'tish mumkin. _Ko'rib chiqiladi: D15._
9. **Native dialog (fayl tanlash) va Common Controls v6.** Hozir `common-controls-v6` o'chirilgan (sabab: `cargo test` test binary'lari comctl32 v6 manifestsiz yiqiladi). Fayl tanlash (CSV import, `.baraka` eksport) kerak bo'lganda `tauri-plugin-dialog` qo'shiladi va testlar uchun manifest yechimi qayta ko'rib chiqiladi. _Kerak: D7 (CSV import) yoki D14 oldidan._
10. **pnpm «minimal chiqarilish yoshi».** pnpm 12 1 kundan yangi paketlarni vaqtincha bloklaydi. Ikki paket (`lucide-react@1.56.0`, `@testing-library/user-event@14.6.8`) `pnpm-workspace.yaml` dagi istisnolar ro'yxatiga avtomatik qo'shildi. _Kerak: 2026-10-21 atrofida istisnolarni tekshirib, olib tashlash._
11. **Ikonka dizayni.** `scripts/make_icon.py`: qorong'i fonda krem «daftar» va geometrik sakkiz burchakli yulduz. 16–256 px o'lchamlarda tekshirildi. Foydalanuvchi ko'rib tasdiqlashi kerak, aks holda o'zgartiriladi. _Kerak: D15 oldidan._
12. **Sozlamalar saqlanishi.** Til tanlovi hozir brauzer `localStorage` da. D3 da shifrlangan baza tayyor, lekin sozlamalar hali unga ko'chirilmagan. D4 da ham ko'chirilmadi (til — brauzer xotirasi, bu «har bir ko'rinish» uchun qulay, lekin ishonchli emas). _Kerak: sozlamalar vazifasi (D15 oldidan)._
13. **Repo va remote.** `origin` = `JurabekM/Myrep`. Desktop uchun alohida repo kerakmi va kod push qilinsinmi — foydalanuvchi qarori. Hozircha hech narsa push qilinmagan. _Kerak: CI'ni GitHub'da ishga tushirishdan oldin._
14. **Interaktiv (E2E) sinov.** D1 da ilova o'rnatilib, ishga tushirildi va ekran suratlari bilan ko'zdan kechirildi: bosh sahifa, o'chirilgan bo'lim tooltip'i, sozlamalar sahifasi haqiqiy oynada tasdiqlandi. Lekin sichqoncha avtomatizatsiyasi oyna fokusi sababli ishonchsiz bo'ldi, shuning uchun til almashinuvi va boshqa tugmalar haqiqiy oynada to'liq tasdiqlanmadi (jsdom testlari o'tadi). Keyinroq WebDriver (`tauri-driver` + WebdriverIO) bilan E2E yoziladi. _Kerak: D15 (reliz) yoki har bir UI vazifasi oxirida._ D3 da haqiqiy ilovada sozlash, qulflash tugmasi, `Ctrl+L`, noto'g'ri PIN, 3 urinishdan keyingi kutish va qayta ochish qo'lda tasdiqlandi (ekran suratlari bilan); til almashinuvi va qolgan tugmalar hali shunday tasdiqlanmagan.

15. **PIN unutilsa, nima bo'ladi?** Hozir tiklash yo'q: PIN unutilsa yoki `keys.bin` yo'qolsa, ma'lumotlar ochilmaydi. Sozlash ekranida ogohlantirish bor. Variantlar: (a) hech narsa (hozirgi holat); (b) bir marta ko'rsatiladigan tiklash kodi, foydalanuvchi qog'ozga yozadi; (c) shifrlangan zaxira (eksport) fayli. Qaror foydalanuvchida. _Kerak: D15 oldidan; afzal — hozir, chunki u kalit modelini o'zgartiradi._
16. **Windows Hello (ixtiyoriy).** DESKTOP_PROMPT.md 6.2 dagi ixtiyoriy variant D3 da kechiktirildi: hozir faqat PIN. Kerak bo'lsa, keyingi bosqichda qo'shiladi. _Kerak: foydalanuvchi xohlasa._
17. **OS qulflash hodisasi.** Win+L va kompyuter uyqusi aniqlanmaydi. Avto-qulflash hozir faqat oyna fokusining yo'qolishi va vaqtga asoslangan. Windows session/power hodisalarini (`WTSRegisterSessionNotification`, suspend) qo'shish kerakmi? _Kerak: D15 oldidan._
18. _Hal qilindi (D4) — pastdagi «Hal qilingan» bo'limiga qarang._
19. **O'rnatuvchi va o'chirishni tekshirish.** D3 da NSIS o'rnatuvchi qayta qurilmadi va o'rnatilmadi (o'rnatish foydalanuvchi kompyuterini o'zgartiradi; D1 da o'chirgandan keyin begona fayl qolgan edi). Silent o'rnatish, ishga tushirish va o'chirish sinovi foydalanuvchi ruxsati bilan. Reliz exe (`target\release`) bilan tekshiruv D3 da o'tkazildi: oyna ekran suratidan chiqarilgan (`WDA_EXCLUDEFROMCAPTURE`), lekin qora emas — orqadagi oyna ko'rinadi. Eski Windows'da xulq tekshirilmagan. _Kerak: D15._
20. **Windows CI'da Perl.** SQLCipher uchun to'liq Perl kerak (README'ga qarang). GitHub Windows runner'ida bu borligi taxmin qilingan, tekshirilmagan. _Kerak: CI birinchi marta ishga tushirilganda (13-band bilan birga)._
21. **Mobil bilan vektor sinxronlash (D4).** Desktop uchta yangi suite yozdi: `streak.json`, `income_share.json`, `money_parse.json`. Qoidalar mobil Dart testlaridan olingan, lekin mobil ilova bu fayllarni hali ishlatmaydi. Mobil CI ularni ham o'tkazishi kerak (2-band bilan birga hal qilinadi). _Kerak: mobil repo bilan birinchi sinxronlashda._
22. **Audit izohsiz summa bilan yakunlanadi (D4).** Hozir audit izohsiz qoldirilgan holda ham yakunlanadi (faqat «Hozircha izohsiz qoldirish» tanlovi bilan). Majburiy qaror (belgilash yoki sababini yozish) kerakmi? _Kerak: D6 (audit kengayishi) oldidan._
23. **Xarajat kanali (D4).** `expenses.channel` ustuni bazada majburiy, domen modelida kanal yo'q — hozir har doim `CASH`. Kanal (naqd/karta) xarajat formasiga qo'shilishi kerak. _Kerak: D6._
24. **Oilaviy rejim (D4).** SPEC 2.3 dagi «er va xotin birga to'ldiradi» (2+ a'zo, umumiy byudjet) hozir yo'q: xonadonda bitta egasi a'zo («O'zim»). _Kerak: D6._
25. **Pul olish: har safar PIN (D4).** Mobildagi 1 daqiqalik PIN ruxsat tokeni o'rniga, PIN har bir pul olishda qayta so'raladi. Bu soddaroq; ruxsat tokeni kerakmi? _Kerak: D9 oldidan (friction)._
26. **Oylik kun sozlamasi (D4).** `month_start_day` bazada va domenda bor (standart 1), lekin uni o'zgartiradigan UI yo'q. _Kerak: D6 (sozlamalar)._
27. **Nasiya — minimal (D4).** Faqat asl summa, qoldiq va qisman to'lov. Foiz, qarz tilxati va friction — D9 da. _Kerak: D9._
28. **«Oy yakuni» ta'rifi (D4).** Mobil ta'rifi bo'yicha «Oy yakuni» = `daromad − (yozilmagan majburiyat + xarajat + sof jamg'arma)` — bu izohsiz summa bilan bir xil formula. Ikki ko'rsatkich bir xil bo'lishi to'g'rimi yoki «Oy yakuni» boshqacha (masalan, to'liq majburiyat bilan) hisoblansinmi? _Kerak: D4 ni ko'rib chiqish._

29. **Qissa matnlari placeholder (D5).** Barcha 5 bobning qissa va qonun matnlari `[Placeholder]` bilan turibdi. Litsenziya hal bo'lmaguncha asl matn kelmaydi (kontent egasi — «Asaxiy Invest» × Abdukarim Mirzayev). Asl matn kelganda `spec/content/chapters.json` almashtiriladi va mobil bilan birga sinxronlanadi. _Kerak: kontent litsenziyasi tasdiqlanganda._
30. **Diniy matnlar ulamo tekshiruvida (D5).** 5 ta `religiousReviewStatus: PENDING` bloki bor. Release'da yashirin (test bor); debug buildda «ulamo tekshiruvida» belgisi bilan ko'rinadi. Tasdiqlanganda JSON'da `APPROVED` ga o'tkaziladi. _Kerak: ulamo tasdig'i._
31. **Audio (D5).** `audioUrl` hozir hech bir bobda yo'q, pleyer UI ham yo'q. _Kerak: audio tayyor bo'lganda._
32. **Ochilish parametrlari (D5).** Standart — 2 vazifa va 7 kun (mobil bilan bir xil). Foydalanuvchi sozlashi kerakmi, yoki qat'iy qoladimi? _Kerak: D6 (sozlamalar) oldidan._
33. **Hodisasiz vazifalar (D5).** `ch02.t2`, `ch02.t3`, `ch03.*`, `ch04.*`, `ch05.t1` uchun modullar hali yo'q: bu vazifalar faqat qo'lda belgilanadi. Modul tayyor bo'lganda shu hodisa `record_event` orqali yoziladi. `ch05.t2` — hodisasi yo'q, qo'lda. _Kerak: D6–D9 har modulida._
34. **«Daftar sahifasi» uzunligi (D5).** Standart qaror: 5000 belgi (backend va textarea). Mobilda chegara yo'q edi. Chegara to'g'rimi yoki boshqacha bo'lsinmi? _Kerak: tasdiq._

## Hal qilingan

- **MoneyParser (D4, 2026-10-14).** `money::parse_amount` mobil qoidalari bo'yicha: bo'sh joy, `_`, apostroflar, valyuta belgisi va so'zi; `money_parse.json` (16 vektor, shu jumladan xato holatlari). _(6-band)_
- **Kalit fayli yo'q, baza bor (D4, 2026-10-14).** Sozlash bunday holatda rad etiladi (`DATABASE_WITHOUT_KEY`) va aniq xabar chiqadi; ma'lumot jim ustiga yozilmaydi. Eski bazani zaxiraga ko'chirish imkoniyati — keyinroq. _(18-band)_
- **SQLCipher'ni Windows'da yig'ish (D3, 2026-10-14).** Git bilan kelgan MSYS perl'da `Locale::Maketext::Simple` yo'q edi; to'liq perl `OPENSSL_SRC_PERL` bilan ko'rsatildi. Yangi o'rnatish talab qilinmadi. Qarang: README, «Windows: SQLCipher va Perl».

- **Tauri versiyasi.** ADR bo'yicha Tauri 2 (stable 2.12.3). Tauri 3 alpha (3.0.0-alpha.4) ishlatilmaydi. _2026-10-14._
- **TypeScript versiyasi.** TypeScript 7.0 `typescript-eslint` bilan mos emas (peer: `<6.1.0`). TypeScript 6.0.3 tanlandi. _2026-10-14._
- **ESLint a11y plagini.** `eslint-plugin-jsx-a11y` ESLint 10 bilan mos emas (peer: ESLint ≤ 9). Tanlandi: ESLint 10, a11y tekshiruvi Testing Library rol bo'yicha so'rovlari orqali. _2026-10-14._
- **Testlarda Windows manifest.** `cargo test` `STATUS_ENTRYPOINT_NOT_FOUND` bilan yiqilgani sabab `common-controls-v6` o'chirildi (9-savolga qarang). _2026-10-14._
- **Installer tili.** NSIS 3.11 da o'zbekcha til fayli (`Uzbek.nlf`) bor. Konfiguratsiyaga qo'shildi: `Uzbek`, `Russian`, `English` (birinchisi — o'zbekcha). Silent o'rnatish sinalgan; interaktiv til tanlovi oynasi qo'lda sinalmagan. _2026-10-14._
- **Release ogohlantirishlari.** `BINDINGS_PATH` va `BINDINGS_HEADER` konstantalari release'da «ishlatilmagan» deb ogohlantirardi — ular faqat debug va test rejimida kompilyatsiya qilinadi. _2026-10-14._
- **Manfiy yaxlitlash.** Yarmi noldan uzoqqa (`−12 650,5 → −12 651`) — vektor `fx-004` bilan tasdiqlangan. _2026-10-14._
- **Formatlash qoidalari (uz/ru).** Guruhlash — U+00A0, kasr — vergul (faqat tiyin bo'lsa), valyuta — bo'linmas bo'sh joy bilan; `soʻm` (U+02BB). Mobil implementatsiya va vektorlar bilan bir xil. _2026-10-14._
