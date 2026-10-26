# Sector Verify — foydalanuvchi qo'llanmasi

Sector Verify baza stansiyasi sektorlari RF rejaga mos nurlanayotganini **oddiy telefon bilan** tekshiradi:
sektor almashinuvi, yo'q PCI va antenna burilishini brigada saytdan ketmasidan oldin topadi. Ilova to'liq
offline ishlaydi — ma'lumot telefondan chiqmaydi.

## 1. Tayyorgarlik (bir marta)
1. Ilovani o'rnating (APK yoki Google Play).
2. **Sozlamalar** (yuqori o'ng burchakdagi tishli g'ildirak):
   - **Muhandis ismi** — hisobotga yoziladi.
   - **Tahlil preseti:** *Shahar* (zich bino, 600 m gacha), *Shahar atrofi* (standart), *Qishloq*.
   - **Trafik URL** (ixtiyoriy, faqat `https://`): telefon tarmoqqa ulangan holatda qolishi va TA (timing advance)
     kelishi uchun har 2 s da HEAD so'rov yuboriladi. Bo'sh qoldirsangiz, oldindan tekshiruv ogohlantiradi.
   - **Qurilma probe (60 s)** — telefon haqiqatda nimalarni beradi (chastota, qo'shni RSRP, TA). Har telefonda bir marta.
   - **Ilova tili** va **hisobot tili** (o'zbek, rus, ingliz) — alohida tanlanadi.
   - **Mavzu:** qorong'i (standart), yorug', **quyosh** (to'g'ri quyosh nurida yuqori kontrast).

## 2. RF rejani import qilish
**Saytlar → CSV reja import**. Fayl formati (UTF-8, sarlavha majburiy; ajratuvchi `,` yoki `;`):
```
site_code,site_name,lat,lon,mcc_mnc,sector,rat,band,arfcn,pci,azimuth_deg,hpbw_deg,mech_tilt_deg,elec_tilt_deg,height_m
NAV-0123,Navoiy Markaz,40.1032,65.3685,43405,S1,LTE,B3,1300,141,0,65,2,4,30
```
Xatolar qator raqami bilan ko'rsatiladi; fayl to'liq to'g'ri bo'lmaguncha hech narsa saqlanmaydi.
Mavjud sayt qayta import qilinsa, sektorlari yangilanadi (eski natijalar saqlanadi).

## 3. Saytda o'lchov
1. **Saytlar** → saytni tanlang → **Oldindan tekshiruv**.
2. Barcha qatorlar yashil yoki sariq bo'lishi kerak. **Qizil** (to'sqinlik) bo'lsa, «Boshlash» o'chiq:
   - *Ruxsatlar* → «Ruxsatlarni berish» (aniq joylashuv, telefon holati, bildirishnomalar). Rad etgan bo'lsangiz —
     «Ilova sozlamalarini ochish».
   - *Operator/SIM* — rejadagi MCC/MNC ga mos SIM kerak (dual-SIM telefonda o'zi tanlanadi).
   - *GPS* — yoqilgan bo'lishi kerak.
3. **Boshlash** → sayt atrofida **150–400 m** radiusda, iloji boricha **to'liq halqa** bo'ylab piyoda yuring
   (taxminan 15–20 daqiqa). Telefonni qo'lda, ekran o'chiq bo'lsa ham yig'ish davom etadi.
4. **Jonli o'lchov** ekranida: xarita (iz rangi = serving PCI), **qamrov radari** (36 ta 10° li yo'nalish),
   har bir PCI kartasi (RSRP, taxminiy va rejadagi azimut, holat rangi).
5. **«Natija tayyor»** bildirishnomasi chiqsa — yetarli qamrov yig'ilgan. **Tugatish** ni bosing.

> Maslahat: radarda kulrang/sariq yo'nalishlar — yetishmayotgan qamrov. Iloji bo'lsa o'sha tomonga yuring.

## 4. Natija
- Har bir ARFCN uchun **polar diagramma**: reja — shtrix chiziq, o'lchov — qalin chiziq va 95% ishonch yoyi.
- **Verdiktlar:** PASS (mos), WARN (20–45° og'ish yoki noaniqlik katta), FAIL (xato: almashinuv, PCI yo'q, > 45°),
  INCONCLUSIVE (qamrov yetarli emas yoki baho ishonchsiz).
- **Topilmalar va tavsiyalar** — nima tekshirish kerakligi (konfiguratsiya/CPRI, band portlari, antenna azimuti...).
- **Qayta tekshiruv** — tuzatishdan keyin yangi o'lchov.

## 5. Hisobot
**Hisobot (PDF, ZIP)** → **Hisobotni yaratish**:
- **PDF** — sarlavha, umumiy verdikt, sektorlar jadvali, polar diagrammalar, marshrut va qamrov, tavsiyalar,
  ilova (config, chastota, SHA-256, imzo). Tanlangan hisobot tilida.
- **report.json** — telefonning himoyalangan kaliti (Android Keystore, EC P-256) bilan **imzolangan**.
- **ZIP** — to'liq sessiya (xom o'lchovlar, reja, hisobot). Ofisda `sv-replay verify sessiya.zip` bilan imzoni tekshirish
  va `sv-replay analyze` bilan qayta tahlil qilish mumkin.

## 6. Muammolar
| Belgi | Sabab va yechim |
|---|---|
| «Mos SIM yo'q» | SIM operatori rejadagi MCC/MNC dan farq qiladi — to'g'ri SIM qo'ying |
| Chastota < 0.5 Hz | Ba'zi telefonlar CellInfo'ni kam yangilaydi — `docs/DEVICES.md` dagi tavsiya etilgan telefonlardan foydalaning |
| Hamma sektor INCONCLUSIVE | Halqa to'liq emas — radardagi bo'sh yo'nalishlarda yuring |
| Ilova to'xtab qoldi | Qayta oching: «Tugallanmagan o'lchov» oynasida **Davom ettirish** — yig'ilgan ma'lumot saqlangan |
| Xato haqida xabar berish | Sozlamalar → **Crash loglarini eksport** — ZIP'ni dasturchiga yuboring (joylashuv yo'q) |
