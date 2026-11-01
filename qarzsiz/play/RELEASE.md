# Qarzsiz — Google Play'ga chiqarish

Bu papkada Play Console uchun hamma narsa bor:

| Nima | Qayerda |
|---|---|
| Do'kon matnlari (uz, ru-RU, en-US): nom, qisqa va to'liq tavsif, yangiliklar | `listing/<til>/*.txt` (chegaralar: `python3 -I play/check_listing.py`) |
| Ikona 512×512, Feature graphic 1024×500 | `graphics/` |
| Telefon skrinshotlari 1080×1920 (8 ta) | `graphics/phone/` |
| Maxfiylik siyosati (uz / ru / en, bitta sahifa) | `privacy-policy.html` |
| Imzolangan AAB yig'ish | `.github/workflows/qarzsiz-release.yml` |

Grafikani qayta yaratish: `cd android && ./gradlew :app:testDebugUnitTest --tests '*StoreScreenshotsTest'`,
keyin `python3 -I play/make_graphics.py`.

---

## 0. Bir marta hal qilinadigan qaror: paket nomi

`applicationId = "uz.qarzsiz.app"` (`android/app/build.gradle.kts`). **Play'ga birinchi yuklangandan keyin
uni o'zgartirib bo'lmaydi.** Boshqa nom kerak bo'lsa — birinchi yuklashdan oldin o'zgartiring.

## 1. Upload kalitini yaratish (o'z kompyuteringizda)

Kalit — sizning imzongiz. U repoga, chatga yoki boshqa joyga yuborilmaydi.

```bash
keytool -genkeypair -v -keystore qarzsiz-upload.jks -alias upload -keyalg RSA -keysize 4096 -validity 10000
```

`keytool` Android Studio bilan keladi (`<Android Studio>/jbr/bin/keytool`). Parolni yozib qo'ying va
`qarzsiz-upload.jks` faylini **ikki joyda** zaxiralang (masalan, parol menejeri + flesh).

Play App Signing (standart) yoqilgan bo'ladi: ilovani Google o'z kaliti bilan imzolaydi, siz faqat
**upload** kaliti bilan yuklaysiz. Upload kaliti yo'qolsa, Play Console orqali yangisini so'rash mumkin.

## 2. GitHub Secrets

Repo → Settings → Secrets and variables → Actions → New repository secret:

| Secret | Qiymati |
|---|---|
| `QARZSIZ_UPLOAD_KEYSTORE_B64` | `base64 -w0 qarzsiz-upload.jks` natijasi (macOS: `base64 -i qarzsiz-upload.jks`) |
| `QARZSIZ_STORE_PASSWORD` | keystore paroli |
| `QARZSIZ_KEY_ALIAS` | `upload` |
| `QARZSIZ_KEY_PASSWORD` | kalit paroli (odatda keystore paroli bilan bir xil) |

## 3. Imzolangan AAB yig'ish

**CI orqali (tavsiya):**
```bash
git tag qarzsiz-v1.0.0
```
```bash
git push origin qarzsiz-v1.0.0
```
Actions → «qarzsiz-release» → artefakt `qarzsiz-1.0.0-play`: `.aab` (Play uchun), `.apk` (sinov uchun),
`mapping-1.0.0.txt`. Workflow testlarni o'tkazadi, imzoni va internet ruxsati yo'qligini tekshiradi.
`versionCode` tegdan hisoblanadi: `1.2.3 → 10203`, har yangi teg kattaroq bo'lishi shart.

**Kompyuterda:** `android/keystore.properties` (commit qilinmaydi):
```properties
storeFile=/to'liq/yo'l/qarzsiz-upload.jks
storePassword=...
keyAlias=upload
keyPassword=...
```
```bash
cd qarzsiz/android && ./gradlew :app:bundleRelease -Pqarzsiz.versionCode=10000 -Pqarzsiz.versionName=1.0.0
```
Kalitsiz `bundleRelease` ataylab to'xtaydi — debug kalitli AAB'ni Play qabul qilmaydi.

## 4. Play Console: ilova yaratish

1. **Create app**: nom `Qarzsiz: qarzdan chiqish`, standart til — o'zbek (ro'yxatda bo'lsa), aks holda
   rus; App; Free.
2. **Store listing**: `listing/<til>/` dagi matnlar, `graphics/` dagi ikona, feature graphic va
   skrinshotlar. Kategoriya: **Finance**. Aloqa e-pochtasi — o'zingizniki.
3. **Privacy policy**: `privacy-policy.html` ni ochiq manzilga joylang (GitHub Pages, Google Sites yoki
   istalgan statik hosting) va URL'ni kiriting. Repo yopiq bo'lsa, `raw.githubusercontent` havolasi
   ishlamaydi — alohida ochiq joy kerak.

## 5. App content (so'rovnomalar) — javoblar

| Bo'lim | Javob |
|---|---|
| **Ads** | No, my app does not contain ads |
| **App access** | All functionality is available without special access (PIN ixtiyoriy va standart o'chiq) |
| **Content rating** | Kategoriya: barcha boshqa ilovalar (All Other App Types). Zo'ravonlik, jinsiy, so'kinish, giyohvand, qimor, foydalanuvchilar o'zaro aloqasi, joylashuv, raqamli xaridlar — hammasiga **No**. Kutilgan reyting: 3+ / Everyone |
| **Target audience** | 18 and over (moliyaviy mavzu). Bolalarni jalb qilmaydi |
| **News app** | No |
| **Data safety** | «Does your app collect or share any of the required user data types?» → **No**. Sabab: ilovada internet ruxsati yo'q, ma'lumot qurilmadan chiqmaydi (Play ta'rifida faqat qurilmada qayta ishlanadigan ma'lumot «to'plash» hisoblanmaydi). Foydalanuvchi o'zi bosadigan «Yuborish» — foydalanuvchi boshlagan ulashish |
| **Financial features** | Ilova kredit bermaydi, to'lov o'tkazmaydi, investitsiya yoki qarzni hal qilish xizmati ko'rsatmaydi — bu shaxsiy qarz va byudjetni kuzatish vositasi. Deklaratsiyada moliyaviy mahsulot taklif qilinmasligini belgilang |
| **Government apps / Health** | No |
| **Permissions** | Maxsus deklaratsiya kerak emas: `POST_NOTIFICATIONS` (oddiy runtime ruxsat), `RECEIVE_BOOT_COMPLETED` (oddiy). Aniq vaqt (`SCHEDULE_EXACT_ALARM`), joylashuv, kontaktlar, SMS — yo'q |

## 6. Test va production

1. **Internal testing** → Create release → AAB yuklang, yangiliklar: `listing/<til>/release_notes.txt`.
   O'z telefoningizga o'rnatib, asosiy oqimni tekshiring (qarz qo'shish, reja, eslatma, PIN).
2. **Shaxsiy dasturchi akkaunti** (2023-yil noyabridan keyin ochilgan) uchun production'dan oldin
   **yopiq test majburiy: kamida 12 tester, 14 kun uzluksiz**. Testerlar Google akkaunt e-pochtalari
   bilan qo'shiladi va test havolasi orqali o'rnatadi. Talablarni Play Console'ning o'zida tekshiring —
   ular o'zgarib turadi.
3. 14 kundan keyin **Apply for production** → savollarga javob → ko'rib chiqish (odatda bir necha kun).

## 7. Keyingi relizlar

- Yangi teg: `qarzsiz-v1.0.1` (versionCode avtomatik oshadi).
- `listing/*/release_notes.txt` ni yangilang.
- Ekranlar o'zgarsa — skrinshotlarni qayta yarating (yuqoridagi buyruqlar).

## Texnik ma'lumot

- `targetSdk = 36` (Android 16), `minSdk = 26` (Android 8.0), AGP 8.11.1.
- Native kutubxona (`libandroidx.graphics.path.so`) 16 KB sahifaga tekislangan (Play talabi).
- R8 yoqilgan; `mapping.txt` AAB ichida ham bor (Play o'zi oladi) va artefaktda alohida.
- Hajm: AAB ≈ 3.6 MB, foydalanuvchiga yuklanadigan APK ≈ 1.8 MB.
