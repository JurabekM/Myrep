# AgroVision — native Android ilova

`AgricultureDashboard/` Python desktop platformasining **to'liq native Android analogi**.
Brauzerda ochiladigan dashboard emas — Jetpack Compose bilan yozilgan haqiqiy ilova.

- **APK:** `AgroVision-v1.1.0.apk` (1.77 MB, imzolangan, R8-minify)
- **Paket:** `com.agrovision.app`
- **minSdk 26 / targetSdk 35** — Android 8.0 va yuqori
- **Internet:** ixtiyoriy — Ob-havo va Sun'iy yo'ldosh bo'limidagi onlayn xarita uchun.
  Qolgan hamma narsa (xarita chegaralari, tumanlar, ML, hisobotlar) qurilma ichida.

## O'rnatish

```bash
adb install AgroVision-v1.1.0.apk
```

Yoki APK faylni telefonga ko'chirib, "Noma'lum manbalardan o'rnatish"ga ruxsat bering.

Birinchi ochilishda ikki tanlov beriladi:

| Tanlov | Nima bo'ladi |
| --- | --- |
| **Namuna ma'lumotlarni yuklash** | 60 fermer, 74 xo'jalik, 140 dala, 23 ekin, 2021–2025 hosildorlik, kunlik ob-havo, haftalik narxlar, moliya, NDVI — jami ~74 000 yozuv. ML modellari darhol o'qitiladi (~10 s). |
| **Bo'sh boshlash** | Faqat ma'lumotnoma (14 hudud, 199 tuman, 23 ekin turi). Barcha biznes-ma'lumot qo'lda yoki import orqali kiritiladi. |

Tanlovni keyin **Administrator** bo'limidan o'zgartirish mumkin.

Boshlang'ich hisoblar: `admin/admin123`, `menejer/manager123`, `kuzatuvchi/viewer123`.

## Ekranlar (18)

| Bo'lim | Ekran | Mazmun |
| --- | --- | --- |
| Umumiy | Bosh sahifa | 6 KPI, hosildorlik trendi + prognoz, ekin taqsimoti (donut), ogohlantirishlar (5 qoida), eng samarali xo'jaliklar |
| | Xarita | O'zbekistonning aniq ma'muriy chegaralari (14 hudud) doimo ko'rinadi — dala bo'lmasa ham. Ustiga dala poligonlari / issiqlik qatlami / klasterlar; +/− va ⟳ tugmalari, ikki barmoq bilan masshtab, poligonga bosib dala kartasi |
| Tahlil | Analitika | Trend + 95% ishonch oralig'i, viloyat reytingi, hudud×ekin issiqlik xaritasi, narx mavsumiyligi, K-Means 3-klaster segmentatsiya |
| | Machine Learning | 4 model: hosil prognozi (RandomForest, R²≈0.97), kasallik xavfi (GradientBoosting, aniqlik≈0.74), suv ehtiyoji, ekin tavsiyasi |
| | AI Yordamchi | 8 intent (nega / prognoz / narx / tavsiya / ob-havo / solishtirish / moliya / statistika), dalil jadvallari bilan |
| Monitoring | Sun'iy yo'ldosh | **Onlayn xarita**: internetdan Esri sun'iy yo'ldosh tasviri yoki OpenStreetMap plitkalari, ustiga dala konturi; keshlanadi va keyin oflayn ochiladi. Shuningdek NDVI/EVI dinamikasi, dalalar salomatligi reytingi, tasvir importi |
| | Ob-havo | Open-Meteo (ERA5 arxiv + 7 kunlik prognoz), NASA POWER zaxira provayder, offlayn keshdan ishlash |
| | Sug'orish | Suv sarfi, tomchilatib sug'orish ulushi, viloyatlar kesimi |
| | Tuproq tahlili | Tuproq turlari bo'yicha maydon/hosildorlik, agronomik moslik baholari |
| Iqtisod | Bozor | So'nggi narxlar + 30 kunlik dinamika, narx prognozi, qo'lda narx kiritish |
| | Moliya | Daromad/xarajat/foyda dinamikasi, ROI trendi |
| Boshqaruv | Ma'lumotlar | 7 ta CRUD forma: fermer, xo'jalik, dala, hosildorlik, sug'orish, moliya, NDVI |
| | Import | CSV/TSV (narx, hosildorlik), GeoJSON, KML — format ustun nomlari bo'yicha avtomatik aniqlanadi, nom bo'yicha idempotent |
| | Hisobotlar | PDF, HTML, CSV, JSON, GeoJSON eksport → `Downloads/AgroVision/` |
| | Administrator | Foydalanuvchi CRUD, parol/faollik, zaxira yaratish-tiklash, baza holati, audit jurnali |
| | Sozlamalar | Tema (tizim/kunduzgi/tungi), til (uz/ru/en), tarmoq rejimi, ob-havo provayderi, zaxira soni |

## Nima uchun native

Desktop versiya brauzer texnologiyalariga tayanadigan uch joyni Android'da to'liq native almashtirildi:

| Desktop | Android |
| --- | --- |
| folium (Leaflet iframe) — offlayn | Compose `Canvas` + geoBoundaries ADM1 vektor chegaralari (`assets/`) + ray-casting `pointInPolygon` |
| folium tile qatlami — onlayn | `TileRepository` (OkHttp + LRU/disk kesh) + Web Mercator XYZ plitkalari `Canvas`da |
| ECharts grafiklar | Compose `Canvas` grafiklari: chiziq (ishonch oralig'i bilan), ustun, gorizontal ustun, donut, issiqlik xaritasi, scatter, gauge |
| scikit-learn | Kotlin CART: variance/Gini bo'linish, bagging RandomForest (regressor + multiklass), GradientBoosting (Newton-step yaproq kalibratsiyasi), JSON serializatsiya |
| fpdf2 | Android `PdfDocument` |

Domen mantiqi desktop'dan aynan ko'chirildi: SQL so'rovlar, seed formulalari, ML xususiyat to'plamlari, AI intent kalit so'zlari, ogohlantirish qoidalari.

## Loyiha tuzilishi

```
agrovision_app/
├─ AgroVision-v1.1.0.apk
└─ android/
   └─ app/src/main/java/com/agrovision/app/
      ├─ core/          Fmt (Locale.US), Security/Rbac/Session, Stats+KMeans, ml/Trees.kt
      ├─ assets/        uz_basemap.json (14 hudud konturi), uz_districts.json (199 tuman)
      ├─ config/        Constants
      ├─ data/
      │  ├─ local/      17 Room entity, ~60 DAO so'rov, DemoSeeder
      │  └─ repo/       18 repozitoriy
      └─ ui/
         ├─ chart/      Charts.kt, FieldMap.kt (offlayn vektor), TileMap.kt (onlayn tile)
         ├─ common/     Components.kt
         ├─ nav/        AppScaffold, Navigation, AppNavHost
         └─ screens/    18 ekran
```

## Build

```bash
cd android && ./gradlew assembleRelease
```

JDK 21 kerak (JDK 25 bilan AGP 8.7.2 ishlamaydi):

```bash
export JAVA_HOME="/c/Program Files/Android/Android Studio/jbr"
```

## Sinovdan o'tgan qismlar

Emulyatorda (Medium_Phone_API_36.0, 1080×2400) release APK bilan tekshirilgan:

- Bootstrap ikki yo'li, kirish, RBAC (kuzatuvchi menyusidan Moliya/Ma'lumotlar/Import/Hisobot/Admin/Sozlama yashiriladi)
- Dashboard KPI'lari, ogohlantirishlar, qidiruv
- Analitika: prognoz + ishonch oralig'i, K-Means A/B/C segmentatsiya
- 4 ML modeli: 12.78 t/ga, 24.4% xavf, 214 800 m³, Pomidor 66.2%
- 8 AI intent — har biri dalil jadvali bilan
- Ob-havo: Open-Meteo'dan real 7 kunlik prognoz
- Bozor: qo'lda narx kiritish → ro'yxatda darhol ko'rinadi
- Foydalanuvchi qo'shish (3→4)
- Eksport: PDF (`%PDF-1.4`, 61 KB), CSV (UTF-8 BOM), GeoJSON (yopiq poligon ringlari) — fayllar diskda tekshirilgan
- Import: CSV narxlar (3 qator), GeoJSON (140 poligon), takroriy import 0 qo'shdi / 140 o'tkazib yubordi
- Zaxira: 7 MB (WAL checkpoint to'g'ri), tiklash → ma'lumot butun
- Sozlamalar: tungi tema, uz/en til almashinuvi
- Bo'sh baza: 12 ekran ham xatosiz, tushunarli bo'sh-holat xabarlari bilan
- Xarita: bo'sh bazada ham 14 hudud konturi aniq chizildi; viloyat filtri o'sha hududga yaqinlashtiradi; +/− tugmalari ×2.6 gacha sinaldi
- Onlayn xarita: Esri sun'iy yo'ldosh tasviri va OpenStreetMap plitkalari yuklandi, dala konturi ustiga to'g'ri joylashdi
- Tumanlar: 199 ta tuman ro'yxatda; Zomin tumani uchun Open-Meteo'dan prognoz olindi
- CRUD: 7 forma ham sinaldi — fermer (60→61), xo'jalik (74→75), dala, hosildorlik (700→701), sug'orish (3500→3501), moliya (851→852), NDVI (9100→9101)

## Test paytida topilgan va tuzatilgan xatolar

| # | Muammo | Tuzatish |
| --- | --- | --- |
| 1 | Ekin taqsimoti buzilgan (29% Anor) — `cropDao.all()` `ORDER BY name` bo'lgani uchun strategik ekin indeks bo'yicha tanlangan | Strategik ekin **nom** bo'yicha tanlanadi |
| 2 | Xarita yorliqlari xarita chegarasidan tashqariga chizilgan | `Modifier.clipToBounds()` |
| 3 | Viloyat filtri qo'llanganda dala poligonlari ko'rinmagan | `computeBounds` dalalarni ustun qo'yadi |
| 4 | Poligonni barmoq bilan bosish deyarli imkonsiz (16 px tolerantlik) | Material tegish zonasi — 44 px |
| 5 | Grafik X o'qi yorliqlari pastdan kesilgan (qat'iy 24 px) | Yorliq balandligi o'lchanadi, joy shunga qarab ajratiladi |
| 6 | Uzun formada tugma "ishlamayotgandek" — validatsiya xabari ekranning tepasida, ko'rinmaydi | `ScreenColumn(scrollToTopKey=…)` xabar chiqqanda tepaga qaytaradi (xabari tugma yonida bo'lgan ekranlarda o'zgarmaydi) |
| 7 | Til almashtirilganda menyu eski tilda qolgan — `I18n.language` oddiy `var` | Compose `mutableStateOf` |
| 8 | Menyu guruh sarlavhalari tarjima qilinmagan | `I18n.t(group)` + ru/en kalitlari |
| 9 | Qo'lda kiritilgan narx ro'yxatda ko'rinmagan — bir kunda bir nechta narx bo'lsa `GROUP BY` tasodifiy qator olardi | `WHERE m.id = (… ORDER BY epochDay DESC, id DESC LIMIT 1)` |
| 10 | Bir xil GeoJSON'ni ikki marta import qilish dala dublikatlari yaratgan | Nom bo'yicha idempotent + o'tkazib yuborilganlar soni hisobotda |
| 11 | Zaxiradan tiklashda ilova ogohlantirishsiz yopilgan | Avval aniq xabar (2.5 s), keyin jarayon tugatiladi |
| 12 | Dala qo'shilmagan bo'lsa Xarita ekrani umuman chizilmagan (faqat matn) | Xarita doimo chiziladi, xabar banner sifatida ko'rsatiladi |
| 13 | Xarita bir barmoqli surishni o'ziga olib, sahifa aylanmay qolgan | Surish/masshtab faqat ikki barmoq bilan; bir barmoq sahifaga o'tadi |
| 14 | Proyeksiya cho'zilgan — mamlakat shakli buzilgan | `cos(lat)` tuzatishi + bir xil masshtab koeffitsienti |
| 15 | Ma'lumotnomada atigi 26 tuman bo'lgan | 199 tuman + Toshkent shahri qo'shildi; mavjud o'rnatishlarda ham idempotent yangilanadi |
| 16 | 199 tuman uchun 5 yillik kunlik ob-havo ~406 ming qator (seed 35 s) | Namuna ob-havo faqat ishlatiladigan tumanlar uchun — 108 ming qator, seed 26 s |
