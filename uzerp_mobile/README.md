# UzERP Mobile — to'liq avtonom Android ERP ilovasi

`erp_platform/` (Python) loyihasining **to'liq avtonom Android versiyasi**.
Ilova hech qanday serverga yoki internetga ulanmaydi — barcha ma'lumotlar
qurilmaning o'zidagi SQLite bazasida saqlanadi. Buni Android'ning o'zi
kafolatlaydi: `AndroidManifest.xml`da `INTERNET` ruxsati umuman yo'q.

## Tayyor APK

| Fayl | Tavsif |
|---|---|
| `UzERP-v1.0.0.apk` | Imzolangan release APK (~1.9 MB, minify qilingan), zamonaviy Material 3 dizayn |

## Dizayn

Ilova zamonaviy, professional UI'ga ega: gradientli login ekrani va Dashboard
sarlavhasi, har bir modul/hisobot uchun o'ziga xos rangli doiraviy ikonka
(Material Icons), 2 ustunli modul grid, rangli KPI kartochkalar. Barcha
vizual elementlar sof Jetpack Compose kodida chizilgan — tashqi rasm/SVG
fayllari yo'q, shu bilan APK hajmi kichik qoladi.

**O'rnatish**: APK faylni telefonga ko'chiring va oching ("Noma'lum
manbalardan o'rnatish"ga ruxsat bering). Talab: Android 8.0+ (API 26+).

**Birinchi kirish**: ilova birinchi ochilganda `admin` foydalanuvchisi va
tasodifiy parol yaratiladi hamda ekranda BIR MARTA ko'rsatiladi — uni
albatta saqlab qo'ying (Nusxalash tugmasi bor).

## Modullar (RBAC — 9 rol bo'yicha ko'rinadi)

- **Savdo**: hisob-faktura, POS kassa, qaytarish, to'lovlar (naqd/karta/Click/Payme/bank)
- **Ombor**: mahsulotlar (avto-SKU, shtrix-kod), qoldiqlar, kam zaxira nazorati
- **Xaridlar**: ta'minotchidan qabul qilish, o'rtacha tannarx yangilanishi
- **Mijozlar / Ta'minotchilar / CRM** (leadlar)
- **Buxgalteriya**: NAS-21 hisoblar rejasi, dvoyna zapis, avto-provodkalar
  (savdo/xarid tasdiqlanganda), Balans, Foyda-zarar, QQS hisoboti
- **Kassa/Bank**: kirim-chiqim, kassa kitobi
- **HR / Ish haqi**: xodimlar, vedomost (12% daromad solig'i + 0.1% INPS),
  tasdiqlash va to'lash — jurnal provodkalari bilan
- **Hisobotlar**: savdo/xarid, TOP mahsulotlar, qarzdorlik — CSV eksport
- **Analitika**: oylik savdo dinamikasi, TOP-5 grafiklar
- **Zaxira nusxa**: butun bazani bitta faylga saqlash va undan tiklash

## Loyihani qayta build qilish

```bash
cd uzerp_mobile/android
# JDK 21 kerak (Android Studio bilan birga keladi):
export JAVA_HOME="C:\Program Files\Android\Android Studio\jbr"
./gradlew assembleRelease
# Natija: app/build/outputs/apk/release/app-release.apk
```

Imzo kaliti: `android/uzerp-release.keystore` (alias `uzerp`). Bu o'z-o'zini
imzolagan mahalliy kalit — Play Store'ga chiqarishda YANGI maxfiy kalit
yaratib, parollarni xavfsiz joyda saqlang.

## Texnik stek

Kotlin · Jetpack Compose (Material 3, dark theme) · Room (SQLite) · Hilt ·
Navigation-Compose · Coroutines/StateFlow. Pul hisob-kitoblari faqat
`BigDecimal` (HALF_UP, 2 xona) — Python `Decimal` bilan bir xil natija.
