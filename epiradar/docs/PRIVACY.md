# EpiRadar — Maxfiylik siyosati

**Kuchga kirgan sana:** 2026-yil 1-noyabr
**Ilova:** EpiRadar (Android, paket nomi `uz.epiradar.app`)
**Ishlab chiquvchi:** JurabekM — aloqa: [GitHub Issues](https://github.com/JurabekM/Myrep/issues)

EpiRadar — rasmiy sog'liqni saqlash tashkilotlarining ochiq ma'lumotlarini tahlil qilib, epidemiya va pandemiya
xavfi haqida ogohlantiradigan ilova. U **shaxsiy ma'lumot yig'maydi, saqlamaydi va hech kimga uzatmaydi.**

## 1. Biz nimani yig'amiz
**Hech narsa.** Ilovada hisob (akkaunt), ro'yxatdan o'tish, reklama, analitika, crash-hisobot yoki boshqa kuzatuv
vositalari yo'q. Ishlab chiquvchining serveri yo'q — ilova ishlab chiquvchiga hech qanday ma'lumot yubormaydi.

## 2. Qurilmangizda nima saqlanadi
Quyidagilar faqat telefoningiz xotirasida, ilovaning yopiq papkasida saqlanadi:
- sozlamalar: tanlangan mamlakat, kuzatuv ro'yxatidagi mamlakatlar, ogohlantirish darajasi, yangilash chastotasi,
  mavzu, tayyorgarlik ro'yxatidagi belgilar;
- rasmiy manbalardan yuklangan ochiq ma'lumotlar (internet bo'lmaganda ko'rsatish uchun);
- qaysi hodisalar haqida bildirishnoma yuborilgani (takror yubormaslik uchun).

Bu ma'lumotlar Google zaxira nusxasiga (backup) kiritilmaydi. Ularni o'chirish uchun: *Sozlamalar → Ilovalar →
EpiRadar → Xotira → Ma'lumotlarni tozalash* yoki ilovani o'chirish.

## 3. Internetga qanday murojaat qilinadi
Ilova ochiq ma'lumotlarni **to'g'ridan-to'g'ri** quyidagi rasmiy serverlardan yuklaydi:

| Server | Nima olinadi |
|---|---|
| `www.who.int` | JSST kasallik avj olishi xabarlari |
| `xmart-api-public.who.int` | JSST FluNet gripp kuzatuvi |
| `www.ecdc.europa.eu` | Yevropa kasalliklarni nazorat qilish markazi xabarlari |
| `wwwnc.cdc.gov` | AQSh CDC sayohat ogohlantirishlari |

Har qanday internet so'rovidagidek, bu serverlar texnik ma'lumotni (IP manzil, so'rov vaqti, `EpiRadar/versiya
(Android)` ko'rinishidagi User-Agent) o'z maxfiylik siyosatlariga ko'ra ko'rishi mumkin. FluNet so'rovida gripp
statistikasi kerak bo'lgan mamlakatlar kodi (masalan, `UZB`) bo'ladi. So'rovlarda ism, telefon raqami,
qurilma identifikatori, aniq joylashuv yoki boshqa shaxsiy ma'lumot **yo'q**.

## 4. Faqat siz bosganda bajariladigan amallar
- **«Manbani ochish»** — rasmiy sahifa brauzeringizda ochiladi.
- **«O'zbekchaga tarjima»** — ochiq xabar matni Google Translate (`translate.google.com`) sahifasida
  brauzeringizda ochiladi; bunda Google maxfiylik siyosati amal qiladi.
- **«Ulashish»** — Android ulashish oynasi; nima va kimga yuborishni o'zingiz tanlaysiz.
- **Tez yordam tugmasi** — telefon raqam teruvchisi ochiladi, qo'ng'iroqni o'zingiz tasdiqlaysiz.

## 5. Ruxsatlar
| Ruxsat | Nima uchun |
|---|---|
| Internet, tarmoq holati | Rasmiy manbalardan ma'lumot yuklash |
| Bildirishnomalar | Xavf haqida ogohlantirish (rad etsangiz, ilova bildirishnomasiz ishlayveradi) |
| Qurilma yoqilganda ishga tushish, uyg'oq tutish | Fon rejimida muntazam yangilash (Android WorkManager) |

Ilova **joylashuv, kontaktlar, kamera, mikrofon yoki fayllarga ruxsat so'ramaydi.** Mamlakatni o'zingiz tanlaysiz.

## 6. Bolalar
Ilova 13 yoshgacha bo'lgan bolalarga mo'ljallanmagan va ulardan hech qanday ma'lumot yig'maydi.

## 7. Tibbiy ogohlantirish
EpiRadar ma'lumot beradi, tashxis qo'ymaydi va shifokor o'rnini bosmaydi. Xavf ballari ochiq manbalar asosida
avtomatik hisoblanadi va xato bo'lishi mumkin. Rasmiy ko'rsatmalar uchun sog'liqni saqlash organlariga murojaat
qiling; shoshilinch holatda tez yordam chaqiring.

## 8. O'zgarishlar
Siyosat o'zgarsa, yangi matn shu sahifada yangi sana bilan e'lon qilinadi. O'zgarishlar tarixi:
[git tarixi](https://github.com/JurabekM/Myrep/commits/master/epiradar/docs/PRIVACY.md).

## 9. Aloqa
Savol va murojaatlar: [GitHub Issues](https://github.com/JurabekM/Myrep/issues).

---

## English summary (for store review)

**EpiRadar does not collect, store on any server, or share any personal data.** There are no accounts,
ads, analytics, crash reporting or tracking SDKs, and no developer-operated server.

- **On-device only:** settings (selected country, watch list, alert level, sync interval, theme, checklist),
  a cache of downloaded public data and the IDs of events already notified. Excluded from cloud backup;
  deleted by clearing app data or uninstalling.
- **Network:** the app fetches public data directly from `www.who.int`, `xmart-api-public.who.int`,
  `www.ecdc.europa.eu` and `wwwnc.cdc.gov`. Those servers see standard request metadata (IP address,
  User-Agent). FluNet queries contain country codes for the requested statistics. No personal identifiers,
  device IDs or location are sent.
- **User-initiated only:** opening a source page or Google Translate in the browser, the Android share
  sheet, the phone dialer.
- **Permissions:** internet/network state, notifications (optional), boot-completed/wake-lock for
  WorkManager background sync. No location, contacts, camera, microphone or storage access.
- Not directed to children under 13. Not a medical device; information only.
- Contact: [GitHub Issues](https://github.com/JurabekM/Myrep/issues).
