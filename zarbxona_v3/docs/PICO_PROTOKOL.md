# Pico imzo kaliti — AQP1 USB protokoli (4.x)

Bu hujjat Zarbxona dasturi (xost) bilan Raspberry Pi Pico'dagi imzo kaliti (HSM)
o'rtasidagi protokolni tavsiflaydi. Unga ikki tomon bo'ysunadi:

- **xost:** `core/pico/qurilma.py` (`PicoImzolovchi`);
- **qurilma:** `firmware/pico_hsm/src/aq_hsm.c`.

Qurilma qoidalarining **etaloni** — `core/pico/soxta.py` (`SoxtaPico`). C dagi ichki dastur u
bilan bir xil testlardan va tasodifiy buyruqlar bilan differensial solishtirishdan o'tadi
(`tests/test_pico_ichki.py`).

## 1. Maqsad va ishonch modeli

- ML-DSA-65 maxfiy kaliti **Pico ichida** turadi. Uni o'qib oladigan buyruq **yo'q**.
- Xost ixtiyoriy baytlarni imzolata olmaydi. Har bir imzo turi o'z maydonlari bilan keladi.
  Imzolanadigan xabarni **qurilmaning o'zi** quradi, domen yorlig'ini ham o'zi qo'shadi.
- Partiya imzosi faqat **faol ruxsat** ichida beriladi. Ruxsatni operator Pico **tugmasi**
  bilan beradi va u summa bilan cheklangan. Kompyuterdagi zararli dastur ruxsat etilgan
  summadan ortig'ini zarb qila olmaydi va tugmasiz yangi ruxsat ham ololmaydi.
- Xost qurilma qaytargan har bir imzoni ochiq kalit bilan **o'zi tekshiradi**.
- Pico'da ekran yo'q, shuning uchun tugma bosilganda nimaga rozilik berilayotganini qurilma
  ko'rsatolmaydi. Matnni xost ko'rsatadi (`KUTMOQDA`). Zararli xost boshqa matn ko'rsatishi
  mumkin, lekin summa chegarasini baribir Pico o'zi qo'yadi. 3-bosqichdagi ESP32 panel yoki
  kichik ekran bu bo'shliqni yopadi.

## 2. Transport

- USB CDC (virtual serial port), tezlik ahamiyatsiz.
- USB mahsulot nomi: `AETHER-Q Pico HSM`, VID `0x2E8A` (Raspberry Pi).
- Xost portni `auto` rejimida shu belgilar bo'yicha topadi.
- Bir vaqtda bitta so'rov bajariladi: xost javob kelguncha keyingi so'rovni yubormaydi.

## 3. Ramka

Ramka ikki yo'nalishda ham bir xil:

| Siljish | Uzunlik | Maydon | Qiymat |
|---|---|---|---|
| 0 | 2 | sehr | `41 51` ("AQ") |
| 2 | 1 | versiya | `01` |
| 3 | 1 | kod | buyruq `0x01..0x3F`; javob = `buyruq \| 0x80`; `0x7F` = KUTMOQDA; `0xFF` = buzilgan ramka |
| 4 | 2 | seq | u16 LE. Xost tanlaydi (1..65535), qurilma o'sha qiymatni qaytaradi |
| 6 | 2 | n | u16 LE, yuk uzunligi, n ≤ 8192 |
| 8 | n | yuk | maydonlar |
| 8+n | 4 | crc32 | IEEE (zlib), `[0, 8+n)` baytlar ustidan, LE |

**Maydonlar:** `u16 LE uzunlik ‖ baytlar` ketma-ketligi. Sonlar maydon ichida qat'iy
kenglikda, LE tartibda yoziladi:

| Tur | Bayt |
|---|---|
| u8 | 1 |
| u32 | 4 |
| u64 | 8 |
| u128 | 16 |

**Javob yuki:** `holat (1 bayt) ‖ maydonlar`. Holat `0` bo'lsa — muvaffaqiyat. Aks holda
holat xato kodini bildiradi. Xatoda birinchi maydon — utf-8 matn; ba'zi xatolar qo'shimcha
maydon ham qaytaradi.

**Sinxronlash:**

- Qabul qiluvchi `AQ` gacha bo'lgan axlatni tashlab yuboradi.
- Versiya yoki uzunlik noto'g'ri bo'lsa, yoki CRC mos kelmasa, 2 bayt tashlanadi va qidiruv
  davom etadi.
- Bunday holatda qurilma `kod=0xFF, seq=0` ramkasini yuboradi. Uning yuki: `02 ‖ matn`.

**Misol** — `SALOM`, seq=1:

```
41 51 01 01 01 00 00 00 69 62 37 4b
```

**Misol** — `PIN_OCH("123456")`, seq=2, va noto'g'ri PIN javobi (qolgan urinish: 4):

```
→ 41 51 01 04 02 00 08 00 06 00 31 32 33 34 35 36 2a 3d 4a 87
← 41 51 01 84 02 00 13 00 05 0d 00 50 49 4e 20 6e 6f 74 6f 27 67 27 72 69 01 00 04 88 f0 9a 99
```

## 4. KUTMOQDA (tugma)

Tugma kerak bo'lganda qurilma javobdan **oldin** `kod=0x7F` ramkasini yuboradi. Ramka
so'rovning `seq` qiymatini oladi, yukida bitta maydon bo'ladi — operatorga ko'rsatiladigan
matn. Keyin qurilma 30 s gacha tugmani kutadi:

| Harakat | Natija |
|---|---|
| Qisqa bosish | tasdiq |
| ≥ 2 s bosib turish | rad (`X_RAD`) |
| 30 s ichida bosilmasa | `X_TUGMA_YOQ` |
| So'rov paytida tugma allaqachon bosilgan bo'lsa | avval qo'yib yuborilishi kerak (tiqilib qolgan tugma tasdiq emas) |

Xost KUTMOQDA'ni olgach javob kutish vaqtini uzaytiradi.

## 5. Buyruqlar

Maydonlar tartibi aynan shunday. Maydonlar soni yoki kengligi noto'g'ri bo'lsa — `X_FORMAT`.

| Kod | Buyruq | Maydonlar | Javob maydonlari | Shart / tugma |
|---|---|---|---|---|
| 01 | SALOM | — | versiya (utf-8), imkoniyatlar u32, holat u8, pk (ochiq bo'lsa 1952 B, aks holda bo'sh), seriya (8 B), qolgan PIN urinishi u8 | — |
| 02 | KALIT_YARAT | pin (6..64 B), xost entropiyasi (32 B) | pk | kalit yo'q bo'lishi kerak; **tugma** |
| 03 | KALIT_IMPORT | pin, urug' (32 B) | pk | kalit yo'q bo'lishi kerak; **tugma** |
| 04 | PIN_OCH | pin | — | kalit bor |
| 05 | QULFLA | — | — | RAM tozalanadi, ruxsat bekor |
| 06 | RUXSAT | buyurtma id (1..64 B), summa u128 (> 0), muddat u32 s (1..86400) | — | ochiq; **tugma** |
| 07 | HOLAT | — | holat u8, qolgan byudjet u128, ruxsatning qolgan vaqti u32 s, imzolar soni u32 | — |
| 08 | KALIT_OCHIR | pin | — | PIN to'g'ri; **tugma** |
| 10 | IMZO_PARTIYA | ildiz (32 B), partiya id (16 B), soni u64 (≥ 1), jami u128 (≥ 1), zaxira qulfi (1..256 B, utf-8, chetida bo'sh joy yo'q), zarb_ms u64 | imzo (3309 B) | ochiq, **faol ruxsat**, jami ≤ byudjet → byudjet −= jami |
| 11 | IMZO_BOSH | tartib u64, xesh (32 B) | imzo | ochiq; tartib ≥ oxirgi; ruxsat bo'lmasa **tugma** |
| 12 | IMZO_MINT_AUTH | bank pk (1952 B), chaqiriq (1..128 B), cert_id (16 B) | imzo | ochiq |

**Imzolanadigan xabarlarni qurilma o'zi quradi:**

| Buyruq | Xabar | Manba |
|---|---|---|
| IMZO_PARTIYA | `BATCH-ROOT/v1`: LE u64 uzunlik prefiksli `L_ROOT, ildiz, id, u64le(soni), u128le(jami), qulf, u64le(zarb_ms)` | SPEC §6.2, `core/partiya.py` |
| IMZO_BOSH | `tagged_hash(L_ZANJIR_BOSH, u64be(tartib), xesh)` | `core/zanjir.py` |
| IMZO_MINT_AUTH | `tagged_hash(L_MINT_AUTH, bank_pk, chaqiriq, cert_id)` | `core/protokol.py` |

Imzo turi — sof ML-DSA-65 (FIPS 204), bo'sh kontekst, randomlashtirilgan (hedged).

**Holat bitlari:**

| Bit | Ma'nosi |
|---|---|
| 0x01 | kalit bor |
| 0x02 | ochiq (PIN kiritilgan) |
| 0x04 | kalit import qilingan |
| 0x08 | ruxsat faol |

## 6. Xato kodlari

| Kod | Nomi | Izoh |
|---|---|---|
| 1 | X_NOMALUM | noma'lum buyruq |
| 2 | X_FORMAT | ramka yoki maydonlar noto'g'ri |
| 3 | X_KALIT_YOQ | qurilmada kalit yo'q |
| 4 | X_QULFLANGAN | avval PIN_OCH |
| 5 | X_PIN | qo'shimcha maydon: qolgan urinish (u8) |
| 6 | X_TUGMA_YOQ | 30 s ichida bosilmadi |
| 7 | X_RUXSAT_YOQ | ruxsat yo'q yoki muddati tugagan |
| 8 | X_BYUDJET | qo'shimcha maydon: qolgan byudjet (u128) |
| 9 | X_TARTIB | jurnal boshi tartibi orqaga ketdi |
| 10 | X_KALIT_BOR | kalit allaqachon bor |
| 11 | X_OCHIRILDI | PIN 5 marta ketma-ket xato — kalit o'chirildi |
| 12 | X_ICHKI | ichki xato |
| 13 | X_RAD | operator rad etdi |
| 100 | X_ALOQA | faqat xostda: port yo'q, javob kelmadi, buzilgan javob |

## 7. Qoidalar (qurilma bajaradi)

**PIN:**

- PIN 6..64 bayt.
- Urinishlar hisobi tekshiruvdan **oldin** flash'ga yoziladi: quvvatni uzib hisobni chetlab
  o'tib bo'lmaydi.
- 5 ta ketma-ket xato → kalit o'chiriladi. To'g'ri PIN hisobni nolga tushiradi.

**Ruxsat:**

- Yangi RUXSAT eskisini almashtiradi (summalar qo'shilmaydi).
- Ruxsat QULFLA, qayta PIN_OCH yoki quvvat uzilishi bilan yo'qoladi.
- Muddati qurilma soati bo'yicha hisoblanadi.

**Jurnal boshi:** tartib kamayishi mumkin emas (bir xil tartib — qayta urinish uchun ruxsat).
Ruxsatsiz holatda (masalan, ishga tushishdagi tiklash) har bir jurnal boshi imzosi uchun
tugma so'raladi.

**Kalit:**

- Kalit urug'i flash'da PIN'dan olingan kalit bilan shifrlanib saqlanadi:
  `core/pico/saqlash.py`, `PIN_ITER = 1024`.
- Yangi kalit urug'i = `SHA3-256(L_KEYGEN ‖ qurilma tasodifi ‖ xost entropiyasi)`.

## 8. Xost qanday ishlatadi

| Bosqich | Nima bo'ladi |
|---|---|
| Kirish | `ulan` → `SALOM` (seriya va ochiq kalit profildagi `imzolovchi.json` bilan solishtiriladi) → `PIN_OCH` |
| Buyurtma boshi | `RUXSAT(buyurtma_id, qolgan summa, 12 soat)` — operator tugmani bosadi |
| Har partiya | `IMZO_PARTIYA`, keyin `IMZO_BOSH` (jurnal zanjiri) |
| Onlayn topshirish | `IMZO_MINT_AUTH` |
| Chiqish | `QULFLA` |

**Pico uzilsa yoki ruxsat tugasa:** joriy partiya yozilmaydi va buyurtma pauzaga o'tadi.
Davom etish uchun "Kalit" sahifasida qayta ulang (PIN), keyin buyurtmani davom ettiring —
tugma yana so'raladi.
