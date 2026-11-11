# HavoRadar — Google Play uchun materiallar

Matn uzunliklari Play cheklovlariga mos (nomi ≤ 30, qisqa tavsif ≤ 80, to'liq tavsif ≤ 4000 belgi):
`python3 tool/store/check_listing.py` tekshiradi.

## Do'kon sahifasi — o'zbekcha (uz)

<!-- listing:uz:title -->
HavoRadar — issiqlik va havo
<!-- /listing -->

<!-- listing:uz:short -->
Kuchli issiqlik va havo ifloslanishidan oldindan ogohlantirish
<!-- /listing -->

<!-- listing:uz:full -->
HavoRadar shahringiz uchun ob-havo va havo sifati prognozini tahlil qiladi. Har kuni 0–100 xavf balli hisoblanadi. Bugun yoki ertaga xavf siz tanlagan darajadan oshsa, telefoningiz oldindan xabar beradi.

ISSIQLIK
• Issiqlik ko'rsatkichi AQSh Milliy ob-havo xizmati (NWS) usuli bilan hisoblanadi.
• Kechasi salqinlamaydigan tunlar va ketma-ket issiq kunlar ham hisobga olinadi.
• 7 kunlik prognoz va eng issiq soat ko'rsatiladi.

HAVO SIFATI
• PM2.5, PM10, ozon va azot dioksidi Jahon sog'liqni saqlash tashkilotining (JSST) 2021-yilgi tavsiyalari bilan solishtiriladi.
• Chang ko'tarilishi alohida ko'rsatiladi.
• Keyingi 48 soat uchun grafik bor.

SIZ UCHUN
• Sezgir guruhlarni belgilashingiz mumkin: 65 yoshdan kattalar, yosh bolalar, homiladorlik, yurak va o'pka kasalliklari, qandli diabet, ochiq havoda ishlash. Shunda ogohlantirish ertaroq keladi.
• Ota-ona yoki qarindoshlar yashaydigan, safarga boradigan yana 3 ta shaharni qo'shish mumkin.
• Har bir ball «Nega bu daraja?» bo'limida tushuntiriladi va aniq tavsiyalar beriladi.

BEZOVTA QILMAYDI
• Bitta issiqlik to'lqini haqida bitta xabar keladi. Xavf kuchaysa, yana xabar beriladi.
• Kechasi 22:00 dan 07:00 gacha faqat favqulodda holatda xabar beriladi.

INTERNETSIZ MA'LUMOTNOMA
• Issiq urishi va issiqlikdan holsizlanish belgilari, birinchi yordam (CDC va NIOSH asosida).
• Uyni salqin saqlash, dorilar va issiqlik, havo ifloslanishi, quyosh nurlari (UV indeksi).
• 103 ga bir tugma bilan qo'ng'iroq qilish.

O'zbekistonning 19 shahri va xorijdagi 11 shahar (jumladan Makka va Madina) bor. Bosh ekran vidjeti va qorong'i mavzu.

Maxfiylik: GPS ishlatilmaydi, hisob ochish shart emas, reklama va kuzatuv yo'q. Sog'liq haqidagi belgilaringiz faqat telefoningizda saqlanadi.

Ma'lumot manbalari: Open-Meteo.com (CC BY 4.0) va Copernicus Atmosphere Monitoring Service. Havo sifati — model prognozi, o'lchov emas.

HavoRadar ma'lumot beradi, tashxis qo'ymaydi va shifokor o'rnini bosmaydi. Rasmiy ogohlantirishlarga ham amal qiling.
<!-- /listing -->

<!-- listing:uz:whatsnew -->
Birinchi versiya: issiqlik va havo sifati xavfi, 7 kunlik prognoz, sezgir guruhlar uchun ertaroq ogohlantirish, internetsiz birinchi yordam ma'lumotnomasi va bosh ekran vidjeti.
<!-- /listing -->

## Store listing — English (en-US)

Play Console'da asosiy til inglizcha bo'lsa yoki xalqaro sahifa kerak bo'lsa.

<!-- listing:en:title -->
HavoRadar: Heat & Air Alerts
<!-- /listing -->

<!-- listing:en:short -->
Early warnings for extreme heat and air pollution, based on WHO and NWS criteria
<!-- /listing -->

<!-- listing:en:full -->
HavoRadar analyses the weather and air quality forecast for your city and calculates a daily 0–100 risk score. If today or tomorrow crosses the level you choose, your phone warns you in advance.

HEAT
• Heat index calculated with the US National Weather Service (NWS) method.
• Nights that do not cool down and consecutive hot days are taken into account.
• 7-day forecast with the hottest hour of each day.

AIR QUALITY
• PM2.5, PM10, ozone and nitrogen dioxide compared with the World Health Organization 2021 guidelines.
• Dust episodes are flagged separately.
• Hourly chart for the next 48 hours.

FOR YOU
• Mark sensitive groups (adults over 65, young children, pregnancy, heart or lung disease, diabetes, outdoor work) and warnings arrive earlier.
• Add up to 3 more cities, for example where your parents live or where you travel.
• Every score is explained under "Why this level?" with clear advice.

NO ALERT FATIGUE
• One alert per heatwave; another only if the risk escalates.
• Between 22:00 and 07:00 only emergency alerts are sent.

OFFLINE GUIDE
• Signs of heat stroke and heat exhaustion, and first aid (based on CDC and NIOSH).
• Keeping your home cool, medicines and heat, air pollution, UV index.
• One-tap call to emergency number 103 (Uzbekistan).

Includes 19 cities in Uzbekistan and 11 abroad (including Mecca and Medina), a home-screen widget and a dark theme.

Privacy: no GPS, no account, no ads, no tracking. Your health selections never leave your phone.

Data: Open-Meteo.com (CC BY 4.0) and the Copernicus Atmosphere Monitoring Service. Air quality is a model forecast, not a measurement.

HavoRadar provides information only. It does not diagnose and does not replace a doctor. Follow official warnings as well.

The app interface is in Uzbek.
<!-- /listing -->

<!-- listing:en:whatsnew -->
First release: heat and air quality risk, 7-day forecast, earlier warnings for sensitive groups, offline first-aid guide and a home-screen widget.
<!-- /listing -->

## Grafika

Hammasi `docs/store/` da. Qayta yaratish: `TZ=Asia/Tashkent flutter test tool/store/screenshots_test.dart && python3 tool/store/compose.py`.

| Fayl | Play Console'dagi joyi | O'lcham |
|---|---|---|
| `icon-512.png` | App icon | 512×512, 24-bit PNG |
| `feature-graphic.png` | Feature graphic | 1024×500 |
| `phone/01…07.png` | Phone screenshots (sarlavhali) | 1080×2160 (1:2) |
| `phone-plain/01…07.png` | Phone screenshots (sarlavhasiz variant) | 1080×2160 |

Tartib: 01 Radar → 02 Bugun (issiqlik, havo, UV) → 03 «Nega bu daraja?» → 04 Prognoz → 05 Birinchi yordam →
06 Sezgir guruhlar → 07 Onboarding. Play kamida 2 ta, ko'pi bilan 8 ta telefon skrinshotini qabul qiladi.

Skrinshotlardagi ma'lumot — **namunaviy ssenariy**: Toshkentda iyuldagi issiqlik to'lqini, «65 yoshdan kattalar»
profili (yadro test fixture'i). Ekranlarning o'zi ilovaning haqiqiy UI'si (Flutter render, ilovadagi shriftlar).

## Kategoriya, reyting, auditoriya

- **Kategoriya:** Weather (Ob-havo) — asosiy funksiya prognoz va ogohlantirish. Muqobil: Health & Fitness.
- **Teglar:** weather, air quality, heat.
- **Kontent reytingi so'rovnomasi:** zo'ravonlik, qimor, foydalanuvchi kontenti, joylashuvni ulashish yo'q.
  Tibbiy ma'lumot bor (umumiy, ma'lumot sifatida).
- **Maqsadli auditoriya:** 18+ (bolalarga mo'ljallanmagan).
- **Reklama:** yo'q. **Ilova ichida xarid:** yo'q.
- **Maxfiylik siyosati:** https://github.com/JurabekM/Myrep/blob/master/havoradar/docs/PRIVACY.md

## Data safety (Ma'lumotlar xavfsizligi) — tavsiya etilgan javoblar

Ilova o'zi hech narsa saqlamaydi va ishlab chiquvchi serveri yo'q. Lekin prognoz olish uchun tanlangan
**shahar markazining koordinatasi** Open-Meteo'ga yuboriladi. Google ta'rifida bu «taxminiy joylashuv» deb
qaralishi mumkin, shuning uchun ehtiyotkor javob:

| Savol | Tavsiya etilgan javob | Izoh |
|---|---|---|
| Ma'lumot yig'iladimi yoki ulashiladimi? | **Ha** | Faqat quyidagi bitta tur |
| Ma'lumot turi | **Location → Approximate location** | Ro'yxatdan tanlangan shahar markazi (GPS emas) |
| Yig'iladimi (collected)? | Ha | Prognoz so'rovida Open-Meteo'ga uzatiladi |
| Ulashiladimi (shared)? | Yo'q | Open-Meteo xizmat ko'rsatuvchi sifatida prognoz qaytaradi; reklama yoki boshqa maqsadga berilmaydi |
| Vaqtinchalik qayta ishlanadimi (ephemeral)? | Ha | Ilova ishlab chiquvchiga hech narsa yubormaydi |
| Majburiymi? | Ha | Shaharsiz prognoz olib bo'lmaydi |
| Maqsad | App functionality | |
| Shifrlanadimi? | Ha (faqat HTTPS) | Cleartext o'chirilgan |
| O'chirishni so'rash | Talab qilinmaydi | Hisob yo'q; ilova ma'lumotini tozalash yoki o'chirish kifoya |
| Sog'liq ma'lumoti | **Yig'ilmaydi** | Sezgir guruh belgilari telefondan chiqmaydi |

Agar shahar koordinatasini «joylashuv» deb hisoblamaslikka qaror qilsangiz, «hech narsa yig'ilmaydi» javobi ham
asosli. Lekin keyinchalik Google bu bo'yicha so'rasa, ehtiyotkor javob muammoni oldini oladi. Qaror sizniki.

## Deklaratsiyalar

- **Health apps (sog'liq ilovalari) deklaratsiyasi:** ilova umumiy ma'lumot beradi: ob-havo va havo sifati
  asosida sog'liq xavfi. Tibbiy qurilma emas, tashxis qo'ymaydi, foydalanuvchining sog'liq ma'lumotini
  yig'maydi. Play Console'dagi eng yaqin toifani tanlang.
- **Ruxsatlar:**
  - bor: bildirishnoma (ixtiyoriy), internet, fon sinxronlash (WorkManager);
  - yo'q: joylashuv, kontaktlar, kamera, mikrofon, fayllar;
  - Foreground service ishlatilmaydi.
- **Government apps:** yo'q (rasmiy davlat ilovasi emas, buni tavsifda va'da qilmang).

## Chiqarish tartibi

1. Imzolangan AAB: `havoradar-v1.0.0` tegi → `havoradar-release` workflow'i ([RELEASE.md](RELEASE.md)).
2. Play Console → yangi ilova → yuqoridagi matnlar, grafika, Data safety, kontent reytingi, auditoriya.
3. **Internal testing** — o'zingiz va bir necha kishi, real telefonlarda.
4. **Closed testing.** Yangi shaxsiy dasturchi akkauntlari uchun production'dan oldin yopiq sinov talab qilinadi
   (tester soni va kun miqdori Play Console'da ko'rsatiladi — joriy talabni o'sha yerda tekshiring).
5. **Production.**
