# HavoRadar — issiqlik va havo ifloslanishidan oldindan ogohlantirish

EpiRadar uslubidagi mobil ilova. U ob-havo va havo sifati prognozini fonda muntazam tahlil qiladi va siz tanlagan
shaharlar uchun har kuni **0–100 xavf balli** hisoblaydi. Bugun yoki ertaga xavf siz tanlagan darajadan oshsa,
push-bildirishnoma keladi: «Xavfli issiqlik — Toshkent, ertaga».

**Texnologiya:** Flutter (UI) + Kotlin (yadro, fon sinxronlash, bildirishnomalar, vidjet). Tashqi Dart paketlari yo'q.
Barcha tahlil telefonda bajariladi. GPS ishlatilmaydi, shaxsiy ma'lumot yig'ilmaydi.

## Ma'lumot manbalari

| Manba | Nima beradi |
|---|---|
| [Open-Meteo Forecast API](https://open-meteo.com/en/docs) | Soatlik harorat, nisbiy namlik, UV indeksi: o'tgan 2 kun + 7 kun oldinga. Manba — milliy meteorologiya xizmatlari modellari |
| [Open-Meteo Air Quality API](https://open-meteo.com/en/docs/air-quality-api) | PM2.5, PM10, ozon, NO₂, chang: o'tgan 1 kun + 5 kun oldinga. Manba — Copernicus CAMS modeli |

API kaliti kerak emas. Ma'lumotlar litsenziyasi CC BY 4.0, manba ilovada ko'rsatiladi. Open-Meteo'ning bepul
tarifi faqat **notijorat** foydalanish uchun: ilovaga reklama yoki pullik funksiya qo'shilsa, tijoriy tarif kerak bo'ladi.
Bitta manba ishlamasa, oldingi prognoz «eskirgan» belgisi bilan ishlatiladi (3 kungacha).

## Qanday hisoblanadi

```
Open-Meteo ──► soatlik qatorlar ──► kunlik ko'rsatkichlar ──► issiqlik va havo bali ──► ogohlantirish siyosati ──► push / vidjet
 (har bir joy)   (mahalliy vaqt)     (max, min, 24 soat o'rtacha,   (sabablar va tavsiyalar    (bir to'lqin — bir xabar,
                                       8 soatlik ozon)               o'zbekcha)                 tunda faqat favqulodda)
```

### Issiqlik (`engine/.../risk/Heat.kt`)

- **Issiqlik ko'rsatkichi** = max(NWS issiqlik indeksi, havo harorati). [NWS formulasi](https://www.wpc.ncep.noaa.gov/html/heatindex_equation.shtml):
  Rothfusz regressiyasi va tuzatishlar. O'zbekistonning quruq issig'ida indeks havo haroratidan past chiqadi.
  Shuning uchun xavf kamaytirib ko'rsatilmasligi uchun harorat olinadi.
- Ball [NWS toifalariga](https://www.weather.gov/safety/heat-index) bog'langan (oraliqda chiziqli):

  | Issiqlik ko'rsatkichi | NWS toifasi | Ball |
  |---|---|---|
  | 26,7°C | Caution | 20 |
  | 32,2°C | Extreme caution | 40 |
  | 39,4°C | Danger | 60 |
  | 51,7°C | Extreme danger | 80 |

- Qo'shimchalar (kunning bali ≥ 20 bo'lsa):
  - **+5** — tropik tun: issiq kundan keyingi tunda (18:00–09:00) harorat 20°C dan pastga tushmaydi (chegara — WMO ETCCDI
    «TR» ko'rsatkichi). Prognozda keyingi tun bo'lmasa, kunning eng past harorati olinadi;
  - **+7** — ketma-ket 3-kun va undan ortiq «Danger» toifasi.

### Havo sifati (`engine/.../risk/Air.kt`)

[JSST 2021 havo sifati tavsiyalari](https://www.who.int/publications/i/item/9789240034228) (AQG) va oraliq maqsadlari (IT),
juda yuqori qiymatlar uchun AQSh EPA AQI chegaralari. Kunning bali — eng yomon ifloslantiruvchining bali:

| Ko'rsatkich | 20 | 40 | 60 | 80 | 100 |
|---|---|---|---|---|---|
| PM2.5, 24 soat, µg/m³ | 15 (AQG) | 37,5 (IT-3) | 75 (IT-1) | 125,5 (EPA Very unhealthy) | 225,5 (EPA Hazardous) |
| PM10, 24 soat | 45 (AQG) | 75 (IT-3) | 150 (IT-1) | 355 (EPA) | 425 (EPA) |
| Ozon, 8 soatlik eng yuqori | 100 (AQG) | 160 (IT-1) | 240 (JSST 2005 «yuqori») → 60, undan oshmaydi | | |
| NO₂, 24 soat | 25 (AQG) | 50 (IT-2) → 30; 120 (IT-1) → 45 | | | |

NO₂ uchun soatlik qiymat ≥ 200 µg/m³ bo'lsa (JSST 1 soatlik tavsiyasi) ball 50 ga ko'tariladi. Chang PM10 ning yarmidan
ko'pini tashkil qilsa, sabablar ro'yxatiga «chang bo'roni» qo'shiladi.

### Profil va umumiy daraja

- **Sezgir guruhlar** (JSST, CDC, EPA ro'yxatlari): 65 yoshdan kattalar, yosh bolalar, homiladorlik, yurak-qon tomir
  kasalliklari, astma yoki o'pka kasalliklari, qandli diabet (faqat issiqlik), ochiq havoda ishlash. Ulardan birortasi
  belgilansa, shu xavf bali **×1,25**: ogohlantirish ertaroq keladi.
- **UV indeksi** [JSST toifalari](https://www.who.int/news-room/questions-and-answers/item/radiation-the-ultraviolet-(uv)-index)
  bilan alohida ko'rsatiladi, lekin push yubormaydi: O'zbekiston yozida u har kuni «juda yuqori» bo'ladi.
- Kunning umumiy darajasi — issiqlik va havoning yomonrog'i. Har bir ball «Nega bu daraja?» sabablari bilan ko'rsatiladi.

| Ball | Daraja |
|---|---|
| 0–19 | Xavfsiz |
| 20–39 | Kuzatuv |
| 40–59 | Ehtiyot |
| 60–79 | Xavfli |
| 80–100 | Favqulodda |

### Ogohlantirish (`engine/.../alert/AlertPolicy.kt`)

- Faqat **bugun va ertaga** uchun ogohlantiradi. Bugungi issiqlik cho'qqisi o'tib bo'lgan bo'lsa, kechikkan «bugun»
  xabari yuborilmaydi (faqat «Favqulodda» bundan mustasno), ertangi kun esa odatdagidek xabar qilinadi. Daraja siz tanlagan chegaradan past bo'lmasligi kerak (standart — «Xavfli»,
  chunki yozda «Ehtiyot» darajasi deyarli har kuni bo'ladi).
- **Bir to'lqin — bir xabar.** Oldingi kun xabar qilingan bo'lsa, davomi jim qoladi. Daraja oshsa, «Xavf darajasi
  oshdi» deb yana xabar beriladi. Xabarda to'lqin necha kun davom etishi ham aytiladi.
- **Sokin soatlar** (22:00–07:00): faqat «Favqulodda» xabar beriladi, qolganlari ertalabgi sinxronlashda yuboriladi.
- Bitta sinxronlashda ko'pi bilan 3 ta xabar + jamlovchi xabar. Birinchi ishga tushishda faqat «Favqulodda» xabar beriladi.

## Ilova imkoniyatlari

- **Radar** — bugungi xavf shkalasi, hozirgi harorat, issiqlik ko'rsatkichi, PM2.5 va UV. Issiqlik va havo kartalari,
  UV tavsiyasi, «Ertaga» bo'limi, 103 ga qo'ng'iroq, manbalar holati. Asosiy va qo'shimcha joylar o'rtasida almashish mumkin.
- **Prognoz** — keyingi 48 soat grafigi (issiqlik ko'rsatkichi va JSST chizig'i bilan PM2.5) va 7 kun. Kun tafsilotida
  «Nega bu daraja?», «Nima qilish kerak» va yaqinlarga ulashish bor.
- **Ma'lumotnoma** (oflayn, CDC/NIOSH/JSST asosida) — issiq urishi va birinchi yordam, issiqlikdan holsizlanish,
  mushak tortishishi, uyni salqin saqlash, dori-darmonlar, sezgir guruhlar, havo ifloslanishi, UV.
- **Sozlamalar** — asosiy shahar (O'zbekistonning 19 shahri va xorijdagi 11 shahar, jumladan Makka va Madina),
  qo'shimcha 3 ta joy (ota-ona, safar), sezgir guruhlar, chegara, sokin soatlar, yangilash chastotasi (1–12 soat),
  yorug' mavzu (standart — dark).
- **Bosh ekran vidjeti** va bildirishnomani bosib to'g'ridan-to'g'ri o'sha joyni ochish.

## Cheklovlar

- Havo sifati — **CAMS model prognozi, o'lchov emas**. U shahar ichidagi ko'cha darajasidagi farqni ko'rsatmaydi.
- Shaharlar ro'yxati oflayn. Yangi shahar qo'shish uchun `engine/src/main/resources/havoradar/places.tsv` ga bitta qator yoziladi.
- Ilova tashxis qo'ymaydi va shifokor o'rnini bosmaydi. Rasmiy (O'zgidromet, SSV) ogohlantirishlariga ham amal qiling.

## Tuzilma

```
havoradar/
├── engine/            # Sof Kotlin/JVM yadro (Android importi yo'q) — mustaqil Gradle build
│   ├── src/main/kotlin/uz/havoradar/engine/
│   │   ├── sources/   # Open-Meteo URL'lari va parserlari
│   │   ├── risk/      # NWS issiqlik indeksi, issiqlik va havo bali, kunlik hisobot
│   │   ├── alert/     # bildirishnoma siyosati
│   │   ├── json/      # holat, snapshot, sozlamalar ↔ JSON
│   │   ├── geo/       # oflayn shaharlar ro'yxati
│   │   └── knowledge/ # ma'lumotnoma (guide.json) yuklovchi
│   ├── src/main/resources/havoradar/  # places.tsv, guide.json
│   └── src/test/      # testlar; fixtures/ — haqiqiy va namunaviy Open-Meteo javoblari
├── android/           # Kotlin: MainActivity (MethodChannel), SyncWorker, Notifier, vidjet, Repository
├── lib/               # Flutter UI (Dart): faqat ko'rsatadi, hech narsa hisoblamaydi
├── test/              # Flutter vidjet testlari; fixtures/ — yadroning haqiqiy JSON chiqishi
├── integration_test/  # qurilmada to'liq oqim: UI → MethodChannel → Kotlin → jonli Open-Meteo
└── tool/synth_fixtures.py  # namunaviy ob-havo javoblari (iyul issiqlik to'lqini)
```

## Buyruqlar

```bash
cd havoradar/engine && ./gradlew test
```

```bash
cd havoradar && flutter analyze && TZ=Asia/Tashkent flutter test
```

```bash
cd havoradar && flutter build apk --release --split-per-abi
```

Jonli Open-Meteo'ga qarshi tekshiruv (internet kerak):

```bash
cd havoradar/engine && HAVORADAR_LIVE=1 ./gradlew test --tests '*LiveSmokeTest*' -i
```

Emulyatorda to'liq tekshiruv (Kotlin instrumental testlar, Flutter integration_test, ilovani ishga tushirib skrinshot):

```bash
cd havoradar && ./tool/emulator_test.sh
```

Imzolangan reliz — teg orqali CI'da: [docs/RELEASE.md](docs/RELEASE.md). Google Play matnlari va grafikasi:
[docs/PLAY_STORE.md](docs/PLAY_STORE.md).

Yadro JSON formati o'zgarganda Flutter test fixture'larini qayta yaratish:

```bash
cd havoradar/engine && HAVORADAR_EXPORT=../test/fixtures ./gradlew test --tests '*CodecTest*' --rerun-tasks
```
