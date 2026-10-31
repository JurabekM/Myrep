# EpiRadar — epidemiya va pandemiyalardan oldindan ogohlantirish

Google'ning zilzila ogohlantirishi kabi ishlaydigan mobil ilova: rasmiy sog'liqni saqlash manbalarini
fon rejimida muntazam tahlil qiladi, sizning mamlakatingiz uchun **0–100 xavf balli** hisoblaydi va
xavf siz tanlagan darajadan oshsa — darhol push-bildirishnoma yuboradi.

**Texnologiya:** Flutter (UI) + Kotlin (yadro, fon sinxronlash, bildirishnomalar, vidjet).
Tashqi Dart paketlari yo'q; tahlil to'liq qurilmada bajariladi, shaxsiy ma'lumot yig'ilmaydi.

## Ma'lumot manbalari (faqat rasmiy va ochiq)

| Manba | Nima beradi | Ishonchlilik |
|---|---|---|
| [JSST Disease Outbreak News](https://www.who.int/emergencies/disease-outbreak-news) (OData API) | Tasdiqlangan avj olishlar, PHEIC | 1.0 |
| [ECDC](https://www.ecdc.europa.eu/en/threats-and-outbreaks) (RSS) | Epidemiologik yangilanishlar, yangiliklar | 0.95 |
| [CDC Travelers' Health](https://wwwnc.cdc.gov/travel/notices) (RSS) | Sayohat darajalari 1–4 | 0.9 |
| [JSST FluNet](https://www.who.int/tools/flunet) (xMart OData) | Haftalik gripp laboratoriya kuzatuvi, odamda A(H5)/A(H7N9) | 1.0 |

Bitta manba ishlamasa, oldingi muvaffaqiyatli ma'lumot «eskirgan» belgisi bilan ishlatiladi.

## Qanday ishlaydi

```
manbalar ──► tasniflash ──► hodisalarga birlashtirish ──► xavf bahosi ──► ogohlantirish siyosati ──► push / vidjet
  (WHO, ECDC,   (kasallik, mamlakat,   (bir kasallik + kesishgan     (tushuntiriladigan     (yangi yoki kuchaygan,
   CDC, FluNet)  epid. belgilar)        mamlakatlar, 60 kun)          0–100 ball)            chegaradan yuqori)
```

1. **Tasniflash** (`engine/.../text/SignalClassifier.kt`) — qoidaga asoslangan, tekshiriladigan:
   33 ta kasallik (eng aniq ibora yutadi: «avian influenza A(H5N1)» → qush grippi, «influenza» emas),
   210+ mamlakat (uzun nom avval: «Papua New Guinea» ≠ «Guinea»), 11 ta epidemiologik belgi
   (noma'lum sabab, odamdan odamga, PHEIC, olib kirilgan holat...) — inkor hisobga olinadi
   («no evidence of human-to-human transmission» → belgi qo'yilmaydi).
2. **Birlashtirish** — WHO, ECDC va CDC bitta voqea haqida yozsa, bu bitta hodisa va «3 ta mustaqil manba tasdiqlagan».
3. **Xavf bahosi** (`engine/.../risk/Risk.kt`):
   - `intensivlik = min(1, 0.6·qo'zg'atuvchi xavfi + 0.6·Σbelgilar + CDC sayohat darajasi)`
   - `global = 100 · intensivlik · ishonchlilik · tasdiq · 0.5^(kun/30)`
   - `shaxsiy = global · yaqinlik'`, yaqinlik — bir mamlakat 1, chegaradosh 0.9, qo'shnining qo'shnisi 0.75,
     keyin masofa bo'yicha; havo orqali yuqadigan pandemik qo'zg'atuvchilar uchun yaqinlashtiriladi.
   - Har bir ball o'zbekcha «Nega bu daraja?» sabablari bilan ko'rsatiladi.
4. **Trendlar** (`engine/.../trend/`) — CDC'ning **EARS C2** algoritmi (keskin o'sish) va
   **tarixiy chegaralar** usuli (o'tgan 3 yilning shu davri bilan solishtirish) — odatiy qishki gripp
   mavsumi yolg'on signal bermaydi, mavsumdan tashqari o'sish esa ushlanadi.
5. **Ogohlantirish** (`engine/.../alert/AlertPolicy.kt`) — faqat yangi yoki darajasi oshgan hodisalar,
   so'nggi 7 kunda yangilanganlar, bir sinxronlashda ≤ 3 ta (+ jamlovchi); birinchi ishga tushishda
   eski hodisalar bilan bezovta qilinmaydi. Xavf/Favqulodda — alohida yuqori ustuvorlikdagi kanal.

## Xavf darajalari

| Ball | Daraja | Tavsiya |
|---|---|---|
| 0–19 | Tinch | Umumiy gigiyena |
| 20–39 | Kuzatuv | Rasmiy yangilanishlarni kuzating |
| 40–59 | Ogohlik | Ehtiyot choralarini kuchaytiring, safar rejalarini qayta ko'ring |
| 60–79 | Xavf | Rasmiy tavsiyalarga qat'iy amal qiling |
| 80–100 | Favqulodda | Faqat rasmiy ko'rsatmalar, tayyorgarlik ro'yxati |

## Ilova imkoniyatlari

- **Radar** — mamlakatingiz uchun xavf shkalasi, dunyo darajasi, eng muhim 3 hodisa, gripp kuzatuvi,
  shoshilinch qo'ng'iroq (103), manbalar holati.
- **Signallar** — barcha hodisalar: qidiruv, filtrlar (yaqin hududlar, kuzatuv ro'yxati), saralash;
  tafsilot sahifasida asl manba xabarlari, «O'zbekchaga tarjima», ulashish.
- **Trendlar** — mamlakatingiz va qo'shnilar bo'yicha gripp musbatligi grafigi, anomaliya nuqtalari.
- **Kasalliklar** — 32 ta kasallik bo'yicha oflayn ma'lumotnoma (JSST asosida): yuqish yo'li,
  yashirin davr, alomatlar, oldini olish, **qachon darhol shifokorga**, vaksina.
- **Tayyorgarlik** — oila uchun 21 bandli ro'yxat (zaxira, sog'liq, hujjatlar, odatlar).
- **Sozlamalar** — mamlakat, kuzatuv ro'yxati (sayohat/qarindoshlar), ogohlantirish chegarasi,
  yangilash chastotasi (1–24 soat), yorug' mavzu (standart — dark).
- **Bosh ekran vidjeti** va bildirishnomadan to'g'ridan-to'g'ri hodisaga o'tish.

## Tuzilma

```
epiradar/
├── engine/            # Sof Kotlin/JVM yadro (Android importi yo'q) — mustaqil Gradle build
│   ├── src/main/kotlin/uz/epiradar/engine/
│   │   ├── sources/   # WHO DON, ECDC, CDC parserlari
│   │   ├── text/      # kasallik/mamlakat/belgi tasniflagich
│   │   ├── risk/      # hodisalarga birlashtirish va xavf bahosi
│   │   ├── trend/     # FluNet, EARS C2, tarixiy chegaralar
│   │   ├── alert/     # bildirishnoma siyosati
│   │   └── json/      # Snapshot ↔ JSON (disk va Flutter uchun yagona format)
│   ├── src/main/resources/epiradar/  # diseases.json (tibbiy ma'lumotnoma), countries.tsv
│   └── src/test/      # 28 test; fixtures/ — haqiqiy manbalardan olingan javoblar
├── android/           # Kotlin: MainActivity (MethodChannel), SyncWorker (WorkManager),
│                      # Notifier, RiskWidgetProvider, Repository. includeBuild("../engine")
├── lib/               # Flutter UI (Dart): faqat ko'rsatadi, hech narsa hisoblamaydi
├── test/              # Flutter widget testlari; fixtures/ — yadroning haqiqiy chiqishi
└── tool/gen_countries.py
```

## Buyruqlar

```bash
cd epiradar/engine && gradle test
```

```bash
cd epiradar && flutter analyze && TZ=Asia/Tashkent flutter test
```

```bash
cd epiradar && flutter build apk --release --split-per-abi
```

Jonli manbalarga qarshi tekshiruv (internet kerak):

```bash
cd epiradar/engine && EPIRADAR_LIVE=1 gradle test --tests '*LiveSmokeTest*' -i
```

Flutter test fixture'larini yadrodan qayta yaratish (yadro JSON formati o'zgarganda):

```bash
cd epiradar/engine && EPIRADAR_EXPORT=../test/fixtures gradle test --rerun-tasks
```

## Cheklovlar va keyingi qadamlar

- Rasmiy manbalar inglizcha: sarlavha va tahlil o'zbekcha, asl matn esa tarjima tugmasi orqali.
- Mahalliy (O'zbekiston SSV) ma'lumotlari uchun ochiq API yo'q — paydo bo'lsa, `SignalSource` sifatida qo'shiladi.
- Reliz imzosi hali sozlanmagan (`android/app/build.gradle.kts`): Play'ga chiqarishdan oldin o'z kalitingizni ulang.
- iOS hozircha yo'q (Kotlin yadro Android uchun; Kotlin Multiplatform orqali ko'chirish mumkin).

## Litsenziyalar va manbalar

- Mamlakatlar ma'lumoti: [mledoze/countries](https://github.com/mledoze/countries) — ODbL 1.0.
- Shrift: Noto Sans — SIL Open Font License 1.1 (`assets/fonts/OFL.txt`).
- Tibbiy matnlar JSST va CDC axborot varaqalari asosida qisqartirib yozilgan.

> EpiRadar ma'lumot beradi, tashxis qo'ymaydi va shifokor o'rnini bosmaydi.
