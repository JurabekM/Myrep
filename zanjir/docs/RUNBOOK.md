# ZANJIR — Runbook (to'liq oflayn ilova)

> 13-faza (ADR-0017). Server yo'q: barcha ma'lumot laboratoriya telefonlarida. Yo'qolishdan yagona himoya — **shifrlangan
> zaxira fayli**. Parollar, upload kaliti va zaxira fayllari chatga, e-pochtaga, repoga **qo'yilmaydi**; logga yozilmaydi.
> 11-fazadagi server runbook'i git tarixida (`519f1d2`).

## Kundalik / haftalik

| Nima | Qayerda | Kim |
|---|---|---|
| Zaxira yaratish — **har ish kuni oxirida** (va har imzolangan protokoldan keyin) | Sozlamalar → "Zaxira nusxa" → saqlash belgisi | har telefon egasi |
| Zaxira faylini telefondan tashqariga ko'chirish (kompyuter, flesh, tashkilot diski) | tizim fayl oynasi; `.zanjir` fayl | telefon egasi |
| "Zaxira hali yaratilmagan" / eski sana ogohlantirishi yo'qligi | Sozlamalar → "Zaxira nusxa" | LEAD (haftalik ko'rik) |
| Asbob qiyoslash muddatlari | Sozlamalar → Asboblar (muddati o'tgani belgilanadi) | LEAD |

Zaxira parol bilan shifrlangan (Argon2id + ChaCha20-Poly1305): fayl ichini parolsiz o'qib bo'lmaydi, o'zgartirilgan fayl
ochilmaydi. **Parol yo'qolsa — zaxira ham yo'qoladi**; parol tashkilot parol menejerida, fayldan alohida saqlanadi.
Bir nechta oxirgi zaxirani saqlang (masalan, 7 kunlik + har oy bittadan): eski fayl ham to'liq tiklanadi.

## Yangi telefonga ko'chish / telefon almashtirildi

1. Eski telefonda (ishlasa): Sozlamalar → zaxira yaratish → faylni yangi telefonga o'tkazish.
2. Yangi telefonda ilovani o'rnatish → boshlang'ich ekran → **"Zaxiradan tiklash"** → fayl → zaxira sanasini tekshirish →
   parol.
3. Ilova faylni tekshiradi: ZANJIR zaxirasimi, parol, yaxlitlik, barcha audit zanjirlari. Biror tekshiruv o'tmasa — hech
   narsa yozilmaydi (xabar: "parol noto'g'ri yoki fayl o'zgartirilgan", "audit zanjiri buzilgan" va h.k.).
4. Tiklangan telefon **yangi qurilma** sifatida ro'yxatdan o'tadi (yangi imzo kaliti; `BACKUP_RESTORED` audit hodisasi).
   Eski qurilmaning imzolari va protokollari tekshiriladigan holda qoladi. Eski telefondagi ilovani o'chiring.

Tiklash faqat **bo'sh** ilovaga (telefonda allaqachon laboratoriya bo'lsa — rad etiladi: ma'lumotni ustidan yozib
yubormaslik uchun). Bunday holatda avval Android sozlamalari → Ilovalar → ZANJIR → "Ma'lumotni tozalash" — **faqat** shu
telefondagi ma'lumot zaxirada borligiga ishonch hosil qilgandan keyin.

Zaxira yaratilgandan keyin kiritilgan yozuvlar (o'lchov, protokol) tiklangan telefonda **yo'q** — shuning uchun har kuni
zaxira. Imzolangan protokolning PDF nusxasi buyurtmachida va ulashilgan joyda qoladi (QR havola tekshiruvi — ilova ichida).

## Telefon yo'qoldi / o'g'irlandi

1. Darhol: oxirgi zaxiradan boshqa telefonda tiklash (yuqoridagi tartib). Zaxiradan keyingi ma'lumot yo'qolgan — qog'oz
   qaydlar bo'yicha qayta kiritiladi (o'lchovlar qayta o'tkazilishi mumkin).
2. Yo'qolgan telefondagi ma'lumot: Android qulfi va disk shifrlash (FBE) himoya qiladi; ilovada lokal PIN yo'q (R-05).
   Telefon qulfsiz bo'lgan bo'lsa — shaxsiy ma'lumot sizishi ehtimoli: tashkilot rahbari va huquqshunos xabardor qilinadi.
3. Yo'qolgan qurilmaning imzo kaliti boshqa telefonlarga faqat almashish fayli orqali ta'sir qilishi mumkin; qurilmani
   bekor qilish almashish bosqichida (13-faza 3-bosqich) qo'shiladi — ungacha begona manbadan kelgan fayllar qabul
   qilinmaydi.
4. Hodisa sanasi, qurilma va oxirgi zaxira sanasi laboratoriya jurnaliga yoziladi.

## Ilovani yangilash

- Play internal testing orqali (`RELEASE.md`). Yangilash lokal bazani o'chirmaydi (migratsiyalar faqat oldinga, testlar
  bilan).
- Yangilashdan **oldin** zaxira yarating: yangi versiyada muammo chiqsa, oldingi versiyani o'rnatib (Play'da eski release)
  shu zaxiradan tiklash mumkin. Yangi versiyada yaratilgan zaxira eski versiyada tiklanmaydi ("yangiroq versiya" xabari) —
  bu ataylab.
- Turli versiyadagi telefonlar o'rtasida almashish — 13-faza 3-bosqichda shu yerga qo'shiladi.

## Kalitlar va parollar

| Nima | Qayerda | Yo'qolsa |
|---|---|---|
| Qurilma imzo kaliti (Ed25519) | Android Keystore (telefondan chiqmaydi, zaxirada ham yo'q) | zaxiradan tiklash — yangi kalit; eski imzolar amalda |
| Zaxira paroli | tashkilot parol menejeri | o'sha parol bilan yaratilgan zaxiralar ochilmaydi — darhol yangi parol bilan yangi zaxira |
| Upload kaliti (`zanjir-upload.jks`) va paroli | foydalanuvchida: parol menejeri + shifrlangan nusxa, ikki joyda (`RELEASE.md`) | Play Console orqali upload kalitini almashtirish (Play App Signing) |
| Dart simbollari, `mapping.txt` | maxfiy arxiv (`RELEASE.md`) | xato izlarini o'qib bo'lmaydi — keyingi release'dan yangisi |

Parol almashtirilsa: yangi parol bilan zaxira yarating; eski parolni eski zaxiralar saqlanadigan muddat tugaguncha
saqlang (aks holda ular ochilmaydi).

## Hodisalar

- **Tiklashda "audit zanjiri buzilgan":** fayl yoki manba telefondagi baza o'zgartirilgan bo'lishi mumkin. Faylni dalil
  sifatida saqlang, oldingi zaxirani sinab ko'ring; manba telefonni ishlatishni to'xtatib LEAD ga xabar bering.
- **"Bu ZANJIR zaxira fayli emas yoki buzilgan":** fayl to'liq ko'chirilmagan (hajmini solishtiring) yoki boshqa fayl.
- **Protokol shubhali:** ilovada QR havola (`zanjir://app/v/<token>`) imzo va hash'larni tekshiradi; bekor qilish —
  LEAD/ADMIN ilovada (sabab bilan, audit hodisasi).
- **Ilova ishga tushmaydi:** ma'lumotni tozalamang — avval yangi versiyani o'rnating; baza fayli telefonda qoladi.
  Tozalash faqat zaxira borligida.

## Mashqlar jurnali

Zaxira → boshqa (bo'sh) telefonda tiklash mashqi: pilotning birinchi haftasida va har chorakda. Tekshiriladi: obyektlar,
sessiyalar, protokollar soni bir xil; protokol QR havolasi tiklangan telefonda "imzo to'g'ri".

| Sana | Nima | Natija |
|---|---|---|
| 2026-10-30 | Avtomatik test: zaxira yaratish (UI) → bo'sh ilovada tiklash, noto'g'ri parol, buzilgan/begona fayl, audit buzilgan, eski sxema | ✅ `app/test/backup_test.dart`, `packages/zanjir_data/test/backup_test.dart` |
