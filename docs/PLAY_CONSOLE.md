# Google Play Console: yuklash yo'riqnomasi

Holat: 2026-10-28. Ilova `uz.barakadastur.app`, versiya `1.0.0+6`, `targetSdk 36` (Android 16).
Play qoidalari tez-tez o'zgaradi — har bosqichdan oldin Console'dagi ogohlantirishlarni o'qing.

Tayyor fayllar:

| Narsa | Joyi |
|---|---|
| Play uchun AAB | `release/1.0.0+6-signed/app-release.aab` (upload kaliti bilan imzolangan, ilova ichidagi imzo xeshi bo'sh) |
| To'g'ridan-to'g'ri APK'lar | `release/1.0.0+6-signed/app-*-release.apk` (imzo xeshi = upload kaliti) |
| Ikonka 512×512 | `tools/store/play_icon_512.png` |
| Banner 1024×500 | `tools/store/feature_graphic_1024x500.png` |
| Telefon skrinshotlari | `tools/store/screenshots/uz/` (7) va `ru/` (5), 1080×1920 |
| Do'kon matnlari | `docs/PLAY_LISTING.md` (uz, ru, en; `python tools/store/check_listing.py`) |
| Maxfiylik siyosati | `docs/PRIVACY_POLICY.md` (ochiq URL kerak) + ilova ichida: Sozlamalar → Ilova haqida → Maxfiylik siyosati |

Egasi o'zi qiladigan ishlar: akkaunt va to'lov, shaxs tasdig'i, aloqa emaili, siyosat URL'i, testerlar,
deklaratsiyalarni tasdiqlash. Kalit paroli va `key.properties` hech kimga berilmaydi.

---

## 0. Talablar (2026-yil oktabr)

- **Target API.** 2026-08-31 dan yangi ilovalar va yangilanishlar **API 36** ni nishonlashi shart
  (uzaytirish 2026-11-01 gacha edi). `1.0.0+6` — `targetSdk 36` (RELEASE_CHECKLIST 18). Talab har yili
  avgustda bir pog'ona ko'tariladi: 2027-08 da API 37 kutiladi.
- **16 KB sahifa.** Native kutubxonalar (`libflutter.so`, `libapp.so`, `libsqlcipher.so`) 16 KB va undan
  katta tekislangan, APK `zipalign -P 16` dan o'tadi.
- **Shaxsiy akkaunt** (2023-11-13 dan keyin ochilgan): production'dan oldin kamida 12 tester bilan
  14 kun uzluksiz yopiq test (6-bo'lim). Tashkilot akkauntiga (D-U-N-S) bu talab qo'yilmaydi.

## 1. Dasturchi akkaunti

1. <https://play.google.com/console/signup> — Google hisobi bilan kiring (ilova uchun alohida hisob tavsiya etiladi).
2. Turi: **Shaxsiy** (pasport) yoki **Tashkilot** (D-U-N-S raqami, yuridik shaxs).
3. Bir martalik to'lov 25 $ — kartadan egasining o'zi to'laydi.
4. Shaxs tasdig'i (hujjat), telefon va email tasdig'i. Console Android telefonda Play Console ilovasi
   orqali qurilma tasdig'ini so'rashi mumkin.
5. Ochiq ma'lumot: dasturchi nomi (masalan, «JurabekM») va aloqa emaili — do'kon sahifasida ko'rinadi.

## 2. Ilova yaratish

**Home → Create app**:

| Maydon | Qiymat |
|---|---|
| App name | `Baraka Dastur` |
| Default language | o'zbekcha (ro'yxatda bo'lsa), aks holda `Russian – ru-RU` |
| App or game | App |
| Free or paid | Free (keyin pullikka o'tkazib bo'lmaydi) |
| Declarations | Developer Program Policies va US export laws — o'qib, egasi belgilaydi |

Paket nomi birinchi AAB yuklanganda qotadi: `uz.barakadastur.app` (o'zgartirib bo'lmaydi).

## 3. App content (Policy → App content)

| Bo'lim | Javob | Asos |
|---|---|---|
| **Privacy policy** | `docs/PRIVACY_POLICY.md` ning ochiq URL'i | Ma'lumot yig'masa ham majburiy. `<ALOQA_EMAIL>` o'rniga haqiqiy email qo'yiladi |
| **App access** | All functionality is available without special access | Login yo'q; birinchi ishga tushishda foydalanuvchi o'z 6 xonali PIN'ini yaratadi |
| **Ads** | No, my app does not contain ads | Reklama SDK yo'q |
| **Content rating** | IARC so'rovnomasi: toifa *All Other App Types*; zo'ravonlik, jinsiy, so'kinish, giyohvand, qimor, foydalanuvchilar o'zaro aloqasi, joylashuv ulashish, raqamli xarid, cheklovsiz internet — hammasi **No** | Taklif tekshiruvi qimorni faqat xavf belgisi sifatida tilga oladi, qimor o'yini yo'q |
| **Target audience** | Faqat **18 and over** | Moliya mavzusi; bolalarga mo'ljallanmagan (Families siyosatiga tushmaydi) |
| **News app** | No | |
| **Health apps** | Hech biri | |
| **Government apps** | No | |
| **Financial features** | *Support services → Other* yoki *My app doesn't provide any financial features* (4-band) | |
| **Data safety** | 5-band | |
| **Advertising ID** | No | `AD_ID` ruxsati yo'q |

**Financial features (4-band).** Ro'yxatdagi turlar: bank va kreditlar, to'lov va o'tkazmalar, xarid
shartnomalari, savdo va fondlar, yordamchi xizmatlar (kredit monitoringi, moliyaviy maslahat, sug'urta,
boshqa). Ilova pul o'tkazmaydi, kredit bermaydi, hisobga ulanmaydi va shaxsiy maslahat bermaydi
(«Fatvo yoki moliyaviy maslahat emas»). Tavsiya: *Other* va izoh — «Offline personal budgeting and
financial literacy notebook. No money movement, no loans, no account connections, no personalised
advice.» **Financial advice ni tanlamang.** Ikkilansangiz, Play Console Help orqali so'rang — tanlov egasining
qarori.

**Data safety (5-band).**

| Savol | Javob |
|---|---|
| Does your app collect or share any of the required user data types? | **No** |
| Natija (do'konda) | «No data collected», «No data shared with third parties» |

Asos: ilovada `INTERNET` ruxsati yo'q, tarmoq kodi yo'q. Google ta'rifi bo'yicha qurilmadan
chiqmaydigan ma'lumot «yig'ilgan» hisoblanmaydi. Foydalanuvchi o'zi tanlab ulashgan fayl (PDF, zaxira) ham
«sharing» emas (*user-initiated action*). Ruxsatlar ro'yxati (birlashgan manifest): `USE_BIOMETRIC`,
`USE_FINGERPRINT`, `POST_NOTIFICATIONS`, `RECEIVE_BOOT_COMPLETED`, `WAKE_LOCK`, `ACCESS_NETWORK_STATE` va
`FOREGROUND_SERVICE` (ikkalasi WorkManager kutubxonasidan, ilova tarmoqqa chiqmaydi va foreground service
ishga tushirmaydi). Kamera/galereya — tizim tanlagichi orqali, ruxsatsiz.

**Foreground service deklaratsiyasi** faqat `FOREGROUND_SERVICE_<TUR>` ruxsatlari uchun so'raladi — bizda
yo'q. Agar Console baribir so'rasa: ilova foreground service ishlatmaydi, ruxsat WorkManager'dan keladi.

## 4. Do'kon sahifasi (Grow users → Store presence)

- **Main store listing:** matnlar `docs/PLAY_LISTING.md` dan, grafika va skrinshotlar yuqoridagi jadvaldan.
  Boshqa tillar — **Translations → Add translation**.
- **Store settings:** Category — **Finance**; Tags — budgeting, personal finance (Console ro'yxatidan);
  Contact details — email majburiy, sayt ixtiyoriy.
- Skrinshotlar: telefon uchun 2–8 ta, tomonlar nisbati 2:1 dan oshmasin (bizda 1080×1920 = 16:9).

## 5. Birinchi yuklash: ichki test va Play App Signing

1. **Test and release → Testing → Internal testing → Create new release.**
2. **App integrity:** *Use Google-generated key* (Play App Signing). `C:\keys\baraka` dagi kalit shundan
   keyin **upload kaliti** bo'ladi; Play foydalanuvchilarga Google saqlaydigan app signing kaliti bilan
   imzolangan ilovani yetkazadi.
3. `release/1.0.0+6-signed/app-release.aab` ni yuklang. R8 mapping va native belgilar AAB ichida
   (`BUNDLE-METADATA`) — alohida yuklash shart emas. Release notes — `docs/PLAY_LISTING.md`, «What's new».
4. Testerlar: email ro'yxati (100 tagacha), havola orqali qo'shiladi. Ichki test deyarli ko'riksiz.
5. **Test and release → App integrity → App signing** sahifasidan **App signing key certificate →
   SHA-256** ni ko'chiring.
6. Keyingi Play yig'ishi shu xesh bilan (ilova ichidagi imzo tekshiruvi Play nusxasida ham ishlashi uchun):
   versiyani oshiring (`pubspec.yaml` `1.0.0+7`, `AppInfo.build`), keyin
   ```
   powershell -File tools/build_release.ps1 -SigningProperties C:\keys\baraka\key.properties -ExpectedSignatureSha256 <Play SHA-256> -NoApk
   ```
   To'g'ridan-to'g'ri tarqatiladigan APK'lar avvalgidek upload xeshi bilan (`-NoBundle`).
   Agar App signing sahifasi xeshni birinchi yuklashdan **oldin** ko'rsatsa, `1.0.0+6` AAB'ni shu xesh
   bilan qayta yig'ib yuklang.
7. Har yuklashda `versionCode` oshadi (6 → 7 → 8…). Bir xil kod bilan qayta yuklab bo'lmaydi.

## 6. Yopiq test (shaxsiy akkaunt uchun majburiy)

1. **Testing → Closed testing → Create track** (masalan, «Oila sinovi»), mamlakatlar va testerlar
   (email ro'yxati yoki Google Group).
2. Ichki testdan relizni **Promote** qiling yoki yangi AAB yuklang. Yopiq test **Google ko'rigidan o'tadi**
   (bir necha soatdan bir necha kungacha).
3. Kamida **12 tester** opt-in qilib, **14 kun uzluksiz** qatnashishi kerak (Console hisoblagichi ko'rsatadi).
   Testerlarga: havola orqali qo'shilish, ilovani o'rnatish, haftasiga bir necha marta ochish, fikr yozish.
4. 14 kundan keyin **Dashboard → Apply for production**: test qanday o'tgani, testerlar fikri, nima
   tuzatilgani, ilova kimga mo'ljallangani haqida savollar. Javob — odatda 7 kungacha.

## 7. Production

1. **Production → Countries/regions:** boshlash uchun O'zbekiston (keyin qo'shimcha mamlakatlar).
2. **Create new release** → AAB → **Staged rollout** (masalan, 20 %) → ko'rik.
3. Ko'rikdan keyin rollout'ni bosqichma-bosqich 100 % gacha ko'taring; **Android vitals** (crash, ANR)
   ni kuzating. Stack'lar Play'da avtomatik deobfuskatsiya qilinadi (mapping AAB ichida).

## 8. Keyin ham esda tuting

- **Upload kaliti** — `C:\keys\baraka` ni ikki joyga zaxiralang (RELEASE_CHECKLIST 2). Yo'qolsa, Play
  Console orqali upload kalitini almashtirish so'raladi (app signing kaliti Google'da qoladi).
- **Android developer verification.** Google Play'dan tashqarida o'rnatiladigan APK'lar uchun ham
  dasturchi tasdig'i joriy qilinmoqda (2026-09-30 dan Braziliya, Indoneziya, Singapur va Tailandda,
  2027 da hamma joyda). Play akkaunti bo'lsa, paket nomi va kalitni Console'da ro'yxatdan o'tkazing —
  aks holda to'g'ridan-to'g'ri APK va demo o'sha davlatlarda o'rnatilmaydi.
- **«Baraka» savdo belgisi** — OPEN_QUESTIONS («Nom va mustaqil kontent»): Play'ga chiqishdan oldin
  yurist ko'rigi tavsiya etiladi.
- **Siyosat sanasi.** Ilova ma'lumot bilan ishlash tartibi o'zgarsa (masalan, internet qo'shilsa),
  `docs/PRIVACY_POLICY.md`, ilova ichidagi matn va Data safety bir vaqtda yangilanadi.

Manbalar (2026-10-28 da tekshirilgan):
[Target API level requirements](https://developer.android.com/google/play/requirements/target-sdk),
[App testing requirements for new personal developer accounts](https://support.google.com/googleplay/android-developer/answer/14151465),
[Financial features declaration](https://support.google.com/googleplay/android-developer/answer/13849271),
[Data safety section](https://support.google.com/googleplay/android-developer/answer/10787469),
[Android 16 behavior changes](https://developer.android.com/about/versions/16/behavior-changes-16),
[Sideloading / developer verification timeline](https://www.androidauthority.com/android-sideloading-changes-timeline-3679204/).
