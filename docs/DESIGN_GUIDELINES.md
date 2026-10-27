# Dizayn qoidalari

## Grafika va ikonkalar — islom tamoyillariga muvofiqlik (majburiy)

Ilova ribosiz moliya g'oyasiga qurilgan, shuning uchun uning ko'rinishi ham shu qadriyatlarga mos bo'ladi.

**Ishlatilmaydi:**
- jonzot tasvirlari: odam yuzi yoki qiyofasi, hayvon, qush (shu jumladan Material'ning `person`, `face`, `emoji`, `pets` ikonkalari);
- cho'chqa yoki «piggy bank» (`Icons.savings` aynan shu shaklda chiziladi);
- qimor (karta, zar, kazino) va alkogol (vino, bar) belgilari;
- boshqa din ramzlari (xoch, cherkov va hokazo), burj va folbinlik belgilari;
- foizni daromad sifatida ko'rsatuvchi grafikalar (`%` belgisi bilan «o'sish» va hokazo). Foizli bankni eslatuvchi bank binosi (`account_balance`) ham ishlatilmaydi.

**Afzal ko'riladi:** daftar, qopcha va hamyon, geometrik (girih uslubidagi) naqshlar, o'simlik naqshlari, xattotlik uslubidagi bezaklar. Oila a'zolari rasm bilan emas, ism bosh harflari bilan ko'rsatiladi.

**Diniy matnlar** faqat `religiousReviewStatus = APPROVED` bo'lganda ko'rsatiladi (SPEC 3).

**Nazorat:** `test/design/icon_policy_test.dart` testi `lib/` dagi har bir `Icons.*` va `CupertinoIcons.*` havolasini taqiqlar ro'yxati bilan solishtiradi. Ilova ikonkasi (`tools/make_icon.py`) — yashil fonda «B» harfi va bug'doy boshog'i (to'kinlik ramzi). Yangi rasm yoki ikonka qo'shilsa, u shu bo'lim bo'yicha ko'zdan kechiriladi.
