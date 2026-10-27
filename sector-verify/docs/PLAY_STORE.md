# Google Play talablari (agar Play orqali tarqatilsa)

> **targetSdk 36** (ADR-017): Google Play 2026-08-31 dan talab qiladigan daraja bajarilgan. Native kutubxonalar 16 KB sahifaga tekislangan.

## 1. Foreground service (location) deklaratsiyasi
Play Console → App content → **Foreground service permissions** → `FOREGROUND_SERVICE_LOCATION`.

**Tavsif (uz):** Ilova baza stansiyasi muhandisiga sayt atrofida piyoda aylanib, sektorlar RF rejaga mos nurlanayotganini
tekshirishga yordam beradi. Foydalanuvchi «Boshlash» tugmasini bosgandan «Tugatish» gacha 15–25 daqiqa davomida har soniyada
GPS joylashuvi va uyali tarmoq o'lchovlari (CellInfo) yig'iladi. Ekran o'chganda ham o'lchov uzilmasligi uchun foreground
service kerak; doimiy bildirishnoma namunalar soni va qamrovni ko'rsatadi. Fon rejimidagi joylashuv so'ralmaydi.

**Description (en):** Field engineers walk around a cell site; between “Start” and “Finish” (15–25 min) the app records GPS
position and CellInfo once per second to verify antenna sector directions against the RF plan. A location foreground service
keeps the survey running with the screen off and shows an ongoing notification with sample count and coverage.
Background location is not requested.

**Video (30–60 s) ssenariysi:** Saytlar → sayt → Oldindan tekshiruv → Boshlash → bildirishnoma ko'rinadi → ekranni o'chirish →
yoqish (namunalar o'sgan) → Tugatish → Natija.

## 2. Data safety javoblari
| Savol | Javob |
|---|---|
| Ilova foydalanuvchi ma'lumotini to'playdimi yoki ulashadimi? | **Yo'q** (ma'lumot qurilmadan chiqmaydi) |
| Joylashuv | To'planmaydi (faqat qurilmada qayta ishlanadi) |
| Ma'lumot shifrlanadimi? | Ha (qurilmada SQLCipher); uzatish yo'q |
| Ma'lumotni o'chirish so'rovi | Ilova ma'lumotlarini tozalash / o'chirish |
| Uchinchi tomon SDK'lari | Yo'q (Firebase/analitika yo'q) |

## 3. Maxfiylik siyosati
`docs/privacy/privacy_{uz,ru,en}.md` — ommaviy URL sifatida joylashtiring va Play Console'ga kiriting.

## 4. Boshqalar
- Kategoriya: Tools / Business. Kontent reytingi: barcha yoshlar.
- `READ_PHONE_STATE` — faqat SIM tanlash (dual-SIM) uchun; Permissions declaration talab qilinmaydi.
