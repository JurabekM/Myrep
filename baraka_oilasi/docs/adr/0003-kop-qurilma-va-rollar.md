# ADR-0003. Kasb-kor: ko'p qurilma va rollar (K8)

- **Holat:** QABUL QILINDI (K8 shu asosda qilindi; mahsulot egasi qayta ko'rib chiqishi mumkin — OQ-K7)
- **Sana:** 2026-10-18
- **Bog'liq:** `docs/kasbkor/SPEC.md` 12, `BARAKA_OILASI.md` 6.6, 7.1, 8.3–8.5, ADR-0001

## Kontekst
- Kasb-kor egasi do'konda sotuvchi ishlatadi. Sotuvchi tushumni yozishi, nasiya to'lovini qabul qilishi va kassani yopishi kerak, lekin foyda, maosh, «egasi oldi», taqsimot va xodimlar haqini ko'rmasligi kerak (SPEC 12).
- U14 da qurilmalar orasida `.baraka` fayl almashish bor (shifrlangan, uch tomonlama birlashtirish, `sync_base`). Unda barcha qurilmalar teng: har biri xonadonning hamma ma'lumotini oladi va hamma narsani yozadi.
- Ilova tarmoq ishlatmaydi (7.6), relay server — R1 bosqichi.
- Rol faqat ekranlarni yashirish bilan cheklansa, himoya bo'lmaydi: ma'lumot sotuvchi telefonida tursa, uni ochib o'qish mumkin (o'z PIN'i bor, baza uning qurilmasida).

## Qaror
1. **Rol — qurilmaga beriladi**, odamga emas. Rollar:
   - `OWNER` — egasi va oila qurilmalari: hamma ma'lumot, hamma amal. Rolsiz qurilma (U14 dagi kabi) — `OWNER`.
   - `SELLER` — bitta Kasb-kor makoniga bog'langan sotuvchi qurilmasi.
   - `ACCOUNTANT` — bitta Kasb-kor makoniga bog'langan hisobchi qurilmasi, faqat o'qish.
2. **Rolni egasining qurilmasi beradi va saqlaydi.** Ulash taklifi (8.5) rol va makon bilan yaratiladi. Yangi qurilma birinchi faylida ulash faylini tasdiqlaydi (`ackExportId`); egasi shu orqali qurilmani rolga bog'laydi (`device_access`). Boshqa qurilmalardan kelgan `device_access` yozuvlari qabul qilinmaydi — rolni faqat `OWNER` qurilmasi yozadi.
3. **Kamaytirilgan ma'lumot (asosiy himoya).** `SELLER`/`ACCOUNTANT` qurilmasiga eksport rol bo'yicha filtrlanadi — kerak bo'lmagan ma'lumot u qurilmaga umuman bormaydi:
   - `SELLER` oladi: xonadon yozuvi, faqat o'z makoni, qurilmalar ro'yxati, o'z roli; tovar katalogi (nomi, birligi, sotuv narxi — **qayta tiklash narxi olib tashlanadi**); nasiya daftari (mijozlar, nasiyalar, hodisalar va nasiya to'lovlari tushumlari); o'zi yozgan tushumlar, sotuv harakatlari va smenalari.
   - `SELLER` olmaydi: chiqimlar, «egasi oldi», maosh, kapital va hamyon harakatlari, tovar xaridlari va tannarx, uskunalar, oilaviy mehnat, «Hisob kuni», kassa kunlari, xodimlar va ta'minotchilar, darvoza, konvertlar, zakot, tarozi, boshqa makonlar (Uy), kelishuvlar va jurnal.
   - `ACCOUNTANT` oladi: o'z makonining hamma yozuvlari (`space_id` bo'yicha), xonadon, qurilmalar va o'z roli; boshqa makonlarni olmaydi.
   - Yozuv xeshi filtrlangan (kamaytirilgan) nusxadan hisoblanadi — `sync_base` barqaror qoladi.
4. **Yozish filtri — egasining qurilmasida.** `SELLER` dan kelgan faylda faqat shu qurilma yaratgan (`origin_device_id`) va ruxsat etilgan yozuvlar qabul qilinadi: shu makondagi tushum, sotuv harakati (`SALE`), nasiya to'lovi (`PAYMENT`), smena va o'z qurilma yozuvi. Qolganlari — e'tiborsiz yoki rad etilgan (sababi bilan). `ACCOUNTANT` dan faqat o'z qurilma yozuvi qabul qilinadi. Sotuvchi ilovasini o'zgartirgan taqdirda ham egasining bazasi himoyalangan.
5. **Import tekshiruvi.** Sotuvchi yozuvlari egasining qoidalari bilan qayta tekshiriladi: yopilgan oy yoki yopilgan kassa kuniga tushgan yozuv (8.4) va qoldiqdan ko'p sotuv rad etiladi. Rad etilganlar import hisobotida ko'rsatiladi, qolganlari qabul qilinadi. Egasi kerak bo'lsa ularni qo'lda kiritadi.
6. **Sotuvchi kassasi — smena.** Sotuvchi egasining kunlik kassa yopishini (K4) qila olmaydi — buning uchun barcha naqd harakatlar kerak. Uning o'rniga **smena**: ochilish (oldingi smenada qolgani), o'z naqd tushumi va naqd nasiya to'lovlari → kutilgan; sanalgan → farq va sabab; egasiga topshirilgan → keyingi smenaga qolgan (`kk_shift_close`). Smenalar o'zgarmas; egasi ularni «Kassa» bo'limida ko'radi. Egasining kunlik yopishi o'zgarmaydi.
7. **Sotuvchi qurilmasida yadro qoidalari.**
   - Foyda, maosh va boshqa egasi bo'limlari use-case'lari `SELLER` qurilmasida `ROLE_FORBIDDEN` qaytaradi — ma'lumot bo'lmasa ham noto'g'ri «foyda» ko'rsatilmasin.
   - Qoldiqni sotuvchi qurilmasi bilmaydi, shuning uchun u yerda sotuv qoldiqqa tekshirilmaydi (egasining importida tekshiriladi).
   - Sotuv sanasi — faqat bugun.
   - `ACCOUNTANT` qurilmasida barcha yozuvlar `ROLE_READ_ONLY` (sinxronlash importidan tashqari).
   - Rolli qurilma yangi qurilma ulay olmaydi.
8. **Rolni bekor qilish.** Egasi qurilmani bekor qiladi: unga eksport qilinmaydi va undan import qilinmaydi (`DEVICE_REVOKED`). Qurilmadagi mavjud ma'lumotni masofadan o'chirib bo'lmaydi — bu ochiq aytiladi.
9. **Transport** — o'zgarmaydi: U14 dagi shifrlangan `.baraka` fayl (USB, messenjer, LAN papka). Relay server — R1, alohida ADR bilan. Jurnal va hisob yurituvchi qurilma qoidasi (6.6) saqlanadi: sotuvchiga jurnal yuborilmaydi, hisobchi uni faqat o'qiydi (rolli qurilmadan jurnal yozuvi qabul qilinmaydi).

## Ko'rib chiqilgan muqobillar
| Variant | Nega tanlanmadi |
|---|---|
| Faqat UI'da yashirish, ma'lumot to'liq yuboriladi | Sotuvchi qurilmasida foyda ma'lumoti bo'ladi — SPEC talabiga zid; qabul mezoni buni taqiqlaydi |
| Ustunlarni shifrlab yuborish (sotuvchi ocholmaydi) | Kalit boshqaruvi murakkab; baribir kerak bo'lmagan ma'lumotni tashish; minimal ma'lumot tamoyiliga zid |
| Rol — odamga (`members`), PIN bilan almashinadigan profillar | Bitta qurilmada maxfiylik cheklangan (7.1); sotuvchi o'z telefonida ishlaydi |
| Sotuvchi ham K4 kunlik yopishni qiladi | «Egasi oldi», chiqim va o'tkazmalarsiz kutilgan qoldiq noto'g'ri; ikki qurilmada bir kunni yopish ziddiyati (`UNIQUE(space_id, day)`) |
| Sotuvchiga tovar harakatlarini xarid summasini yashirib yuborish (qoldiqni tekshirish uchun) | Soxta summalar bazada saqlanadi; sotuv harakatlari egasining tushumlariga bog'langan — ularni ham yuborish kerak bo'ladi |
| Relay server orqali jonli sinxronlash | Tarmoq va server — R1; avval fayl almashish modeli barqaror bo'lishi kerak |

## Oqibatlar
**Ijobiy**
- Sotuvchi qurilmasida foyda ma'lumoti fizik jihatdan yo'q (test: eksport tarkibi va sotuvchi bazasi tekshiriladi).
- Egasining bazasi rolli qurilmadan faqat ruxsat etilgan yozuvlarni oladi.
- U14 formati va birlashtirish dvigateli o'zgarmaydi; filtr — eksport va import bosqichida.

**Salbiy va cheklovlar**
- Sotuv qoldiqqa faqat egasining importida tekshiriladi; rad etilgan sotuvlar sotuvchi qurilmasida qoladi, egasiga qo'lda kiritish kerak bo'ladi.
- Sotuvchi nasiya bera olmaydi va mijoz qo'sha olmaydi (SPEC 12 dagi ro'yxat bo'yicha; OQ-K7).
- Bekor qilingan qurilmadagi ma'lumot o'chirilmaydi.
- Sotuvchi tushum summalarini (o'z savdosi va nasiya to'lovlari) ko'radi — bu ish uchun zarur.
