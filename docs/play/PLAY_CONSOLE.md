# ROSTOR-2 — Google Play Console javoblari

Play Console shakllari uchun tayyor javoblar. Shakllar vaqt o'tib o'zgaradi — yuborishdan oldin Console'dagi joriy
savollarni shu yerdagi faktlar bilan solishtiring. Faktlar manbasi: `app/android/app/src/main/AndroidManifest.xml`,
`tools/check_release.py` natijasi va [PRIVACY_POLICY.md](PRIVACY_POLICY.md).

## 1. Ilova haqida asosiy ma'lumot

| Maydon | Javob |
| --- | --- |
| Paket | `uz.rostor.rostor2` |
| Ilova nomi | ROSTOR-2 firibgarlik qalqoni (uz), [PLAY_LISTING.md](PLAY_LISTING.md) |
| Standart til | O'zbek (uz) |
| Turi / toifa | App → Tools |
| Bepul / pullik | Bepul |
| Reklama | Yo'q |
| Ichki xaridlar | Yo'q |
| Versiya | 1.0.0 (versionCode 1), targetSdk 36, minSdk 26 |

## 2. Maxfiylik siyosati

Ochiq URL kerak. [PRIVACY_POLICY.md](PRIVACY_POLICY.md) dagi `<SANA>`, `<DASTURCHI>`, `<ALOQA_EMAIL>` ni to'ldirib,
ommaviy joyga qo'ying va manzilni "Privacy policy" maydoniga kiriting.

## 3. Data safety (Ma'lumotlar xavfsizligi)

| Savol | Javob | Asos |
| --- | --- | --- |
| Ilova talab qilinadigan foydalanuvchi ma'lumotlarini yig'adimi yoki ulashadimi? | **Yo'q** | Ilovada `INTERNET` yo'q — hech qanday ma'lumot qurilmadan ilova tomonidan uzatilmaydi. Play ta'rifida "yig'ish" = ilovadan qurilma tashqarisiga uzatish |
| Hisobotni "Ulashish" orqali yuborish | yig'ish/ulashish hisoblanmaydi | Foydalanuvchi o'zi boshlagan, kutilgan uzatish: Android Sharesheet'da qabul qiluvchini foydalanuvchi tanlaydi (Play: "user-initiated action ... user reasonably expects") |
| Shifrlash (uzatishda) | Qo'llanilmaydi | Uzatish yo'q |
| O'chirish so'rovi | Ilova ichida: hisobot va qo'ng'iroqlar tarixini o'chirish; ilovani o'chirish hammasini o'chiradi | |

Agar Console baribir "Ulashish"ni belgilashni talab qilsa: "Personal info → Phone number" (firibgar raqami) va
"Messages → Other in-app messages" (foydalanuvchi qo'shgan SMS matni), maqsad — "App functionality", ixtiyoriy,
foydalanuvchi boshlaydi.

## 4. Ruxsatlar deklaratsiyasi

### QUERY_ALL_PACKAGES (majburiy shakl)

- **Asosiy maqsad:** Antivirus va xavfsizlik ilovasi (*"Device search / Antivirus / Security apps"* — ruxsat etilgan toifa).
- **Tavsif (inglizcha, Console uchun):**

  > ROSTOR-2 is an offline anti-fraud security app. Its core feature "Device audit" lists every installed app that holds
  > high-risk capabilities (enabled Accessibility service, notification listener, device admin, default SMS app,
  > overlay and "install unknown apps" permissions) and flags look-alike or sideloaded banking-trojan apps. The
  > "APK Shield" compares the signing certificate of an APK file with the installed official app. Both require
  > visibility of all installed packages; a narrower `<queries>` set cannot know in advance which malicious package
  > names will appear. The app has no INTERNET permission, so the package list never leaves the device.

- **Video (agar so'ralsa):** Bosh ekran → "Qurilmani tekshirish" → topilgan ilova → "Sozlamani ochish". Emulyatorda
  `tools/testapks` dagi zararsiz "fakeclick" sinov APK'si bilan ko'rsatish mumkin.

### Qo'ng'iroqlarni aniqlash roli

`CallScreeningService` + `ROLE_CALL_SCREENING`. `READ_CALL_LOG`, `READ_PHONE_STATE`, `READ_CONTACTS` so'ralmaydi —
SMS/Call Log deklaratsiyasi talab qilinmaydi. Rol foydalanuvchi tomonidan tizim oynasida beriladi.

### Boshqalar

| Ruxsat | Holat |
| --- | --- |
| `POST_NOTIFICATIONS` | Qo'ng'iroq ogohlantirishi. Oddiy ruxsat, deklaratsiya yo'q |
| Accessibility | Ishlatilmaydi |
| `MANAGE_EXTERNAL_STORAGE`, SMS, joylashuv, kamera | Ishlatilmaydi |
| Foreground service | Yo'q |

## 5. Boshqa deklaratsiyalar

| Shakl | Javob |
| --- | --- |
| Government apps | Yo'q — davlat idorasini ifodalamaydi va u bilan bog'liq emas |
| Financial features | "My app doesn't provide any financial features" |
| Health | Yo'q |
| News | Yo'q |
| Ads ID | Ishlatilmaydi (`AD_ID` yo'q) |
| App access | Hamma funksiya kirishsiz ochiq; qo'ng'iroq funksiyasi rolni yoqishni talab qiladi — ko'rib chiquvchi uchun izoh: "Call Shield: Qo'ng'iroq Qalqoni → Qalqonni yoqish" |

## 6. Kontent reytingi (IARC)

Toifa: **Utility, Productivity, Communication or Other**. Zo'ravonlik, jinsiy, qo'pol so'z, giyohvandlik, qimor — yo'q.
Foydalanuvchilar o'zaro muloqot qilmaydi, joylashuv ulashilmaydi, raqamli xaridlar yo'q. Kutilgan natija: 3+/Everyone.
Eslatma: ta'lim matnlarida firibgarlik usullari (soxta qo'ng'iroq, qo'rqitish) tasvirlanadi — bu "crude humor" yoki
"violence" emas.

## 7. Maqsadli auditoriya

**18 va undan katta.** Sabab: bolalarga mo'ljallangan ilovalar uchun Families siyosati qo'shimcha talablar qo'yadi;
ilova kattalar moliyaviy firibgarligiga qaratilgan. "Ilova bolalarni jalb qiladimi?" — Yo'q.

## 8. Imzo va kalitlar

1. **Play App Signing** yoqiladi (yangi ilovalar uchun majburiy). Siz AAB'ni **upload kaliti** bilan imzolaysiz
   (`tools/create_upload_key.ps1`), Google esa foydalanuvchiga **app signing key** bilan imzolab beradi.
2. Shuning uchun Play'dan o'rnatilgan ROSTOR-2 ning "haqiqiymi?" ekranidagi izi = Console → *Test and release →
   App integrity → App signing key certificate → SHA-256*. Upload kaliti xeshi boshqa.
3. Birinchi yuklashdan keyin:
   - shu SHA-256 ni README va reliz eslatmasida e'lon qiling (foydalanuvchi solishtiradigan "rasmiy iz");
   - AAB'ni `-ExpectedSignatureSha256 <app signing SHA-256>` bilan qayta yig'ing — ekrandagi ichki tekshiruv yoqiladi.
4. Bitta tarqatish kanali: Play. Upload kaliti bilan imzolangan APK'ni ommaga tarqatmang — uning izi Play'dagidan
   farq qiladi va foydalanuvchini chalg'itadi (Play nusxasi ustiga o'rnatilmaydi ham).
5. Upload kaliti yo'qolsa Console orqali almashtirsa bo'ladi; **baza kaliti** (`C:\keys\rostor2\db`) yo'qolsa —
   o'rnatilgan ilovalar yangi bazani qabul qilmaydi. Ikkalasini alohida zaxiralang.

## 9. Ko'rib chiquvchi uchun eslatma (Release notes for review)

> ROSTOR-2 is a fully offline anti-fraud app for Uzbekistan (UI in Uzbek). It has no INTERNET permission. Organization
> names (banks, payment systems, police) appear only as data for verifying official domains, app signatures and phone
> numbers; the app is not affiliated with them and does not use their logos. QUERY_ALL_PACKAGES powers the device audit
> and APK signature check. Call screening uses the system caller-ID role without call-log or contacts permissions.
