# 🌾 AgroVision Mobile — Android ilova

[AgricultureDashboard](../AgricultureDashboard) (Python/NiceGUI) desktop platformasining **native Android**
versiyasi. Kotlin + Jetpack Compose + Room asosida yozilgan.

**Ma'lumot siyosati:** fermer/xo'jalik/dala/hosildorlik/sug'orish/moliya/bozor
ma'lumotlarining barchasi foydalanuvchi tomonidan **qo'lda kiritiladi** va
faqat qurilma ichida saqlanadi — hech qanday tashqi serverga yuborilmaydi.
Ilovada **o'ylab topilgan demo biznes-ma'lumot yo'q**. Faqat **Ob-havo**
bo'limi haqiqiy tarixiy va joriy ma'lumot uchun Open-Meteo (bepul, kalitsiz,
ochiq API) internet xizmatiga ulanadi.

## O'rnatish

`AgroVision-Mobile-v1.0.0.apk` faylini telefonga o'tkazing va o'rnating
(noma'lum manbalardan o'rnatishga ruxsat bering). Birinchi ochilishda ilova
faqat ma'lumotnomani (O'zbekiston viloyat/tuman ro'yxati + standart ekin
turlari) va 3 boshlang'ich hisobni yaratadi — boshqa hech narsa.

**Boshlang'ich hisoblar:** `admin/admin123` (administrator) ·
`menejer/manager123` (menejer) · `kuzatuvchi/viewer123` (kuzatuvchi,
faqat ko'rish). Ishga tushgach parollarni Administrator bo'limidan almashtiring.

## Ishni boshlash

1. **"Ma'lumotlar"** bo'limidan: fermer → xo'jalik → dala qo'shing (har biri
   avvalgisiga bog'liq).
2. Xuddi shu bo'limda: hosildorlik, sug'orish, moliya va NDVI yozuvlarini
   kiriting.
3. Bozor narxlarini **"Bozor"** sahifasida qo'lda kiriting.
4. Ob-havo ma'lumoti **"Ob-havo"** sahifasida "Internetdan yangilash"
   tugmasi bilan avtomatik yuklanadi (internet talab qilinadi).
5. Dashboard, Xarita, Analitika, ML va AI — kiritilgan ma'lumot asosida
   avtomatik hisoblanadi.

## Arxitektura

```
agrovision_mobile/android/app/src/main/java/com/agrovision/mobile/
  core/          — PBKDF2 xavfsizlik, RBAC, on-device chiziqli regressiya,
                   locale-xavfsiz formatlash, tarmoq holati
  data/local/    — Room: 16 Entity, DAO'lar, ma'lumotnoma generatori (SeedData)
  data/remote/   — Open-Meteo HTTP klienti (OkHttp)
  data/repository/ — 13 repository (Geo, KPI, Weather, Market, Irrigation,
                      Finance, Satellite, ML, AI, Records, Backup, Reports,
                      Settings, Alerts)
  ui/            — 15 Compose ekran (Login + Ma'lumotlar + 13 modul)
```

## Desktopdan farqlar (mobil qurilma cheklovlari sababli, ochiq aytilgan)

| Modul | Desktop | Mobil |
|---|---|---|
| Xarita | Folium + jonli plitka | Offlayn sxematik xarita (Canvas, koordinata asosida) |
| Ob-havo | Open-Meteo/NASA POWER | Xuddi shu Open-Meteo (tarixiy archive + joriy prognoz API) |
| ML hosil prognozi | RandomForest/XGBoost ansambl | Qurilmada o'qitiladigan **chiziqli regressiya** (eng kichik kvadratlar) |
| Sun'iy yo'ldosh | GEE/Sentinel-2 provayder zanjiri | Qo'lda NDVI kiritish yoki dron/tasvir yuklash |
| Hisobotlar | PDF/Excel/Word/HTML/PNG | PDF (Android PdfDocument) + CSV, Downloads/AgroVision papkasiga |
| Bozor narxi | CSV/API import + qo'lda | Faqat qo'lda kiritish (ishonchli ochiq API topilmadi) |

## Ruxsatlar

`INTERNET` + `ACCESS_NETWORK_STATE` — **faqat** Ob-havo bo'limida
Open-Meteo'ga ulanish uchun. `WRITE/READ_EXTERNAL_STORAGE` (API ≤28) —
hisobot fayllarini Downloads papkasiga yozish uchun. Boshqa hech qanday
ruxsat yo'q (`aapt2 dump badging` bilan tekshirilgan).

## Build qilish (qayta yig'ish)

```
cd agrovision_mobile/android
JAVA_HOME="C:\Program Files\Android\Android Studio\jbr"
.\gradlew.bat :app:assembleRelease
```

Natija: `app/build/outputs/apk/release/app-release.apk` (imzolangan,
`app/agrovision-release.keystore`, alias `agrovision`).

## To'liq sinovdan o'tgan (haqiqiy Android emulyatorda)

Har bir modul bo'sh baza va real ma'lumot bilan alohida sinovdan o'tkazildi:
Login, Dashboard, Ma'lumotlar (to'liq CRUD zanjiri: Fermer→Xo'jalik→Dala→
Hosildorlik/Sug'orish/Moliya), Xarita, Analitika, ML (prognoz/kasallik
xavfi/suv ehtiyoji/ekin tavsiyasi), Sun'iy yo'ldosh, Ob-havo (internetdan
haqiqiy 366 kunlik tarixiy + 7 kunlik jonli prognoz), Bozor, Sug'orish,
Moliya, AI Yordamchi, Hisobotlar (PDF+CSV — fayllar diskda tasdiqlangan),
Administrator (foydalanuvchi boshqaruvi, audit jurnali, zaxira/tiklash —
to'liq sikl tasdiqlangan), Sozlamalar.

**Ushbu tekshiruv jarayonida topilgan va tuzatilgan xatolar:**
1. `NumberFormatException` — qurilma tili vergulni kasr ajratkichi sifatida
   ishlatganda `String.format().toDouble()` qayta o'qish crash berardi
   (asl xabar qilingan bug). Butun demo-generator olib tashlangani va
   qolgan formatlash `Locale.US`ga o'tkazilgani bilan hal qilindi.
2. Bo'sh ro'yxatda `List(-1){null}` crash — Analitika va Bozor
   ekranlarida (prognoz grafigi hosildorlik/narx tarixi yo'q bo'lganda).
3. Navigation-Compose ViewModel'lari faqat `init{}`da yuklanardi — boshqa
   ekranda ma'lumot qo'shilgach, avval ochilgan ekranga qaytilganda eski
   holat ko'rinardi (Dashboard/Analitika/Moliya/Sug'orish/Xarita/Hisobotlar/
   Sun'iy yo'ldosh) — barchasiga qayta-yuklash (`LaunchedEffect`) qo'shildi.
4. **Zaxira nusxa deyarli bo'sh yaratilardi** (4 KB) — `PRAGMA
   wal_checkpoint` cursor natijasi hech qachon o'qilmagani sababli
   ba'zan haqiqatda bajarilmay qolardi. Tuzatilgach zaxira hajmi real
   ma'lumotga mos (masalan 188 KB) va tiklash to'liq ishlaydi — sikl
   (yaratish→tiklash→qayta ishga tushirish→login→ma'lumot tekshirish)
   ikki marta alohida holatda (bo'sh va to'ldirilgan) tasdiqlandi.
5. Foydalanuvchi qo'lda kiritgan vergulli sonlar (`63,7`) xato bilan rad
   etilishi mumkin edi — `toSafeDouble()` yordamchisi qo'shildi.

Qolgan barcha ekranlar (Xarita, ML, Sun'iy yo'ldosh, Sug'orish, AI) bo'sh
va real ma'lumot bilan crash bermasligi tasdiqlangan.
