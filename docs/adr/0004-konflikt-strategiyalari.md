# ADR 0004 — Konfliktlarni hal qilish strategiyalari

**Holat:** qabul qilingan · **Sana:** 2026-08-23

## Kontekst

Ikki qurilma offline'da bir xil ma'lumotni o'zgartirishi mumkin. Qaysi
o'zgarish yutadi degan savolga **har aggregate uchun alohida** javob
kerak.

«Last write wins» ni hamma joyda ishlatish oson, lekin xavfli: u
moliyaviy yozuvni va ombor qoldig'ini jimgina yo'q qiladi.

## Qaror

| Aggregate | Strategiya | Nega |
|---|---|---|
| Mahsulot, mijoz | **FIELD_VERSION** | Maydon darajasida HLC. Bir xodim narxni, boshqasi telefonni o'zgartirsa — ikkalasi ham saqlanadi |
| Buyurtma holati | **STATE_MACHINE** | Noqonuniy o'tish rad etiladi; zid o'tish konflikt sifatida ko'rsatiladi |
| Ombor harakati | **APPEND_ONLY** | Qoldiq overwrite qilinmaydi — harakatlar qo'shiladi va yig'indi hisoblanadi |
| To'lov | **APPEND_ONLY** | O'chirilmaydi; tuzatish = teskari yozuv |
| Tashrif | **LAST_WRITE_WINS** | Kritik emas; eng kech yozuv yetarli |

Strategiya `contracts/events/registry.json` da har hodisa uchun
yozilgan — kod ham, Kotlin ham shu manbadan o'qiydi.

---

## 1. FIELD_VERSION — maydon darajasidagi versiya

Har maydon uchun oxirgi o'zgartirgan hodisaning **HLC tamg'asi**
saqlanadi (`field_versions` ustuni). Kelgan hodisa tamg'asi mavjuddan
kechroq bo'lsagina qo'llanadi.

Nega HLC, devor soati emas: qurilmalar soati farq qiladi. HLC sabab-oqibat
tartibini saqlaydi va **ikkala qurilmada bir xil natija** beradi.

```
Desktop:  narx = 2 000 000  (HLC: 1787443200000.00003.desktop1)
Telefon:  narx = 3 000 000  (HLC: 1787443200000.00007.androi01)
                             ^ kechroq -> yutadi
```

Natija ikkala qurilmada ham 3 000 000. Bu **konflikt emas** — deterministik
qaror. `tests/sync-chaos/test_chaos.py::test_concurrent_edit_resolves_deterministically`.

## 2. STATE_MACHINE — buyurtma holati

```
DRAFT → CONFIRMED → APPROVED → ALLOCATED → PICKED → SHIPPED → DELIVERED
                                                                  ↓
                                              PARTIALLY_RETURNED → RETURNED
```

Bekor qilish faqat `SHIPPED` gacha. Jo'natilgandan keyin tovar ketgan —
buning o'rniga qaytarish rasmiylashtiriladi.

Noqonuniy o'tish **jimgina qabul qilinmaydi**: u `sync_conflict` ga
yoziladi va «Tekshiruv navbati» da ko'rinadi. Sabab: bu ko'pincha ikki
xodimning zid amali (biri bekor qildi, ikkinchisi jo'natdi) va buni
faqat odam hal qila oladi.

## 3. APPEND_ONLY — ombor va moliya

Qoldiq **hech qachon** yozilmaydi. U harakatlardan hisoblanadi:

```
RECEIPT +100
SALE     -30   ← desktop
SALE     -40   ← telefon (offline edi)
------------
qoldiq    30
```

Ikkala sotuv ham saqlanadi. Agar qoldiq overwrite qilinganda edi, biri
ikkinchisini o'chirib yuborardi («yo'qolgan yangilanish»).

To'lovda ham xuddi shunday: bekor qilish teskari yozuv yaratadi, asl
yozuv joyida qoladi. Buni SQLite trigger majburlaydi — ORM qoidasi emas.

## 4. LAST_WRITE_WINS — faqat kritik bo'lmagan ma'lumot

Tashrif izohi yoki natijasi. Yo'qolsa biznes zarari yo'q.

---

## Bog'liqlik tartibi (ota-ona hali kelmagan bo'lsa)

Hodisa o'z ota-onasidan **oldin** kelishi mumkin (tartib buzilishi):
buyurtma mijozdan oldin. Bunday hodisa **yo'qotilmaydi** —
`Outcome.DEFERRED` bo'lib qoladi va keyingi urinishda qayta ko'riladi.

12 marta urinilgandan keyin ham ota-ona kelmasa, bu konflikt sifatida
ko'rsatiladi. Cheksiz kutish ham, jimgina yo'qotish ham qabul qilinmaydi.

---

## Baza cheklovi buzilganda

Ikki qurilma offline'da bir xil buyurtma raqamini berishi mumkin.
Proyektor har hodisani **SAVEPOINT** ichida qo'llaydi: bittasi cheklovni
buzsa, butun batch yiqilmaydi — qolgan hodisalar qo'llanaveradi, buzuq
bittasi konflikt bo'ladi.

Yumshatish: buyurtma raqamiga **qurilma prefiksi** qo'shiladi
(`A3F1-00042`), shuning uchun to'qnashuv amalda deyarli bo'lmaydi.
