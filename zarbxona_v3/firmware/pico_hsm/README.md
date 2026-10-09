# Zarbxona Pico HSM — Raspberry Pi Pico imzo kaliti (4.x)

Oddiy Raspberry Pi Pico (RP2040) zarbxonaning ML-DSA-65 imzo kalitiga aylanadi.

- Kalit Pico ichida turadi va kompyuterga **hech qachon chiqmaydi**.
- Har bir buyurtma Pico **tugmasi** bilan tasdiqlanadi.
- Pico operator tasdiqlagan summadan ortig'ini **imzolamaydi**.

Protokol: [`docs/PICO_PROTOKOL.md`](../../docs/PICO_PROTOKOL.md).

> **Holat:**
> - C yadro kompyuterda Python etaloni bilan bir xil testlardan o'tadi; kalit va imzolar
>   `cryptography` bilan mos.
> - Yig'ilgan **`.uf2` RP2040 emulyatorida (rp2040js) ishlaydi**: USB, tugma, imzolar va
>   qayta yoqishdan keyingi flash yozuvi sinalgan (`tests/test_pico_emulyator.py`, CI'da).
> - **Haqiqiy Pico'da hali ishga tushirib ko'rilmagan.** Flash yozish (ROM funksiyalari)
>   va haqiqiy tezlik faqat Pico'ning o'zida tekshiriladi. Birinchi sinov — quyidagi
>   "Tekshirish" bo'limi.

**Kutiladigan vaqtlar** (emulyator, 125 MHz, taxminiy):

| Amal | Vaqt |
|---|---|
| PIN bilan ochish | ~2 s |
| Kalit yaratish yoki import | ~2,5 s (tugmadan keyin) |
| Bitta partiya imzosi | 0,8–2,4 s (ML-DSA tasodifiy) |
| Jurnal boshi imzosi | 0,7–1,7 s |

## 1. Kerakli narsalar

- Raspberry Pi Pico (RP2040; chip yozuvi `RP2-B2`). Pico W ham bo'ladi, lekin unda
  platadagi LED ishlamaydi — tashqi LED kerak.
- Ma'lumot o'tkazadigan micro-USB kabel (faqat zaryad beradigan kabel ishlamaydi).
- 1 ta tugma (har qanday 2 oyoqli yoki 4 oyoqli "tact" tugma).
- 1 ta LED va 220–330 Ω rezistor (ixtiyoriy, lekin tavsiya etiladi).
- Kavsharsiz maket plata (breadboard) va simlar yoki kavsharlash.

## 2. Ulanish

Pico'ni USB porti yuqoriga qaragan holda tutsangiz, chap tomondagi pastki oyoqlar:

```
   Pico oyog'i   GPIO     ulanadi
   ───────────   ──────   ─────────────────────────────────────────────
   18            GND  ──┬── tugmaning bir oyog'i
   19            GP14 ──┘── tugmaning ikkinchi oyog'i  (pull-up ichida)
   20            GP15 ───── 330 Ω ───── LED (+, uzun oyoq)
                                         LED (−, qisqa oyoq) ──── GND (18 yoki 23)
```

- Tugmaga rezistor kerak emas: ichki pull-up yoqilgan.
- Platadagi LED (GP25) tashqi LED bilan bir xil yonadi.

**LED nimani bildiradi:**

| LED | Ma'nosi |
|---|---|
| o'chiq | qulflangan (PIN kiritilmagan) |
| yonib turadi | PIN bilan ochilgan |
| sekin miltillaydi (1 s) | buyurtma ruxsati faol — zarb ketmoqda |
| **tez miltillaydi** | **TUGMANI BOSING**: qisqa — tasdiq, 2 s bosib turish — rad, 30 s — bekor |

## 3. Ichki dasturni yuklash (.uf2)

1. Tayyor faylni oling: GitHub → Actions → `zarbxona-v3` → oxirgi muvaffaqiyatli yugurish
   → **Artifacts** → `zarbxona-pico-hsm-uf2` → `zarbxona_pico_hsm.uf2`. Yonidagi `.sha256`
   bilan solishtiring.
2. Pico'dagi **BOOTSEL** tugmasini bosib turib, USB kabelni kompyuterga ulang, keyin
   tugmani qo'yib yuboring. `RPI-RP2` nomli disk paydo bo'ladi.
3. `zarbxona_pico_hsm.uf2` faylini shu diskka nusxalang. Pico o'zi qayta yuklanadi. Windows'da
   endi yangi COM port paydo bo'ladi ("AETHER-Q Pico HSM").

> **Yangilash:** yangi `.uf2` versiyasi xuddi shu yo'l bilan yuklanadi. Kalit yozuvi
> flash'ning oxirgi 4 KB sektorida turadi va UF2 uni o'zgartirmaydi.
>
> Boshqa dastur (masalan, MicroPython) yuklansa, kalit yozuvi o'chib ketishi mumkin.
> Shuning uchun kalitli Pico'ga boshqa dastur yuklamang.

## 4. Zarbxona bilan ishlatish

**GUI:**

1. "Kalit va sertifikat" sahifasiga o'ting va **"Pico'ni sozlash…"** ni bosing.
2. Port tanlang (`auto` odatda yetadi) va rejimni belgilang:
   - **"Mavjud kalitni ko'chirish"** — `kalit.json` dagi kalit Pico'ga import qilinadi.
     Sertifikat o'zgarmaydi. Keyin `kalit.json` ni faqat zaxira sifatida seyfda saqlang.
   - **"Pico ichida yangi kalit"** — eng xavfsiz yo'l, lekin bankdan **yangi sertifikat** kerak
     ("Ochiq kalitni eksport qilish").
3. PIN'ni ikki marta kiriting. LED tez miltillaganda Pico tugmasini bosing.
4. Dasturni yoping va qayta oching: kirish oynasida endi **Pico PIN'i** so'raladi.
5. Har buyurtma boshida oynada sariq banner chiqadi ("PICO TUGMASINI BOSING") — tugmani
   bosing.

**CLI:**

```
python run.py pico portlar
python run.py pico sozla --import            # yoki --yangi; PIN: ZARBXONA_PICO_PIN
python run.py pico holat
python run.py zarb --summa 100000 --qulf AQ-RES-1   # PIN so'raladi, keyin tugma
python run.py pico qaytish                    # yana kalit.json (agar bor bo'lsa)
```

**Apparatsiz sinash:** port o'rniga `soxta:yo'l/flash.json` yozsangiz, kompyuterdagi soxta
Pico ishlaydi (tugma avtomatik bosiladi). Bu faqat sinash uchun — haqiqiy himoya emas.

## 5. Tekshirish (birinchi ulanishda)

1. `.uf2` ni yuklang. LED o'chiq turishi kerak (kalit yo'q yoki qulflangan).
2. `python run.py pico portlar` — "AETHER-Q Pico HSM" ko'rinsin.
3. `python run.py pico holat` — `kalit: yo'q`, seriya raqami chiqsin.
4. Sinov profilida `pico sozla --yangi`. LED tez miltillaganda **tugmani bosing**. Javob
   kelishi bir necha soniya olishi mumkin (PIN KDF va ML-DSA kalit yaratish RP2040'da sekin).
5. `--demo` profilida zarb qiling. Tugmani bosgach LED sekin miltillasin va partiyalar
   yozilsin. "Tekshiruv" sahifasi TOZA bo'lishi kerak.
6. Rad etishni sinang: buyurtma boshida tugmani 2 s bosib turing — buyurtma pauzaga o'tishi kerak.
7. USB'ni zarb paytida sug'urib oling — partiya yozilmasligi va buyurtma pauzaga o'tishi
   kerak. Qayta ulang: "Kalit" sahifasi → "Qayta ulash (PIN)…" → davom ettiring.
8. Har bir imzo qancha vaqt olganini yozib qo'ying va yuqoridagi emulyator jadvali bilan
   solishtiring.

## 6. Manbadan yig'ish

Kerak:

- `gcc-arm-none-eabi`;
- CMake ≥ 3.18;
- [pico-sdk](https://github.com/raspberrypi/pico-sdk) 2.1.1 va uning `lib/tinyusb` submodule'i.

Windows'da eng osoni — VS Code'ning "Raspberry Pi Pico" kengaytmasi: u hammasini o'rnatadi.

```
cmake -S . -B build -DPICO_SDK_PATH=/yo'l/pico-sdk
cmake --build build          # → build/zarbxona_pico_hsm.uf2
```

**ML-DSA kutubxonasi:**

- ML-DSA-65 — [mldsa-native](https://github.com/pq-code-package/mldsa-native) v2.0.0
  (Apache-2.0 / ISC / MIT).
- CMake uni aniq commit bo'yicha yuklaydi.
- Internetsiz yig'ish: `-DMLDSA_NATIVE_PATH=/yo'l/mldsa-native`.

**Kompyuter uchun (test) varianti:** SDK kerak emas.

```
cmake -S . -B build-host -DAQ_HOST=ON && cmake --build build-host
AQ_PICO_HOST=$PWD/build-host/pico_hsm_host python -m pytest ../../tests/test_pico_ichki.py
```

## 7. Tuzilishi

| Fayl | Vazifasi |
|---|---|
| `src/aq_hsm.c` | protokol va qurilma qoidalari (SDK'siz; etalon — `core/pico/soxta.py`) |
| `src/aq_keccak.c` | SHA3-256 / SHAKE256 (PIN KDF, flash yozuvi, tagged_hash) |
| `src/aq_arena.c` | ML-DSA buferlari uchun statik arena va `randombytes` |
| `src/aq_mldsa.c` | mldsa-native (bitta kompilyatsiya birligi, `aq_mldsa_config.h`) |
| `src/main_pico.c` | RP2040: USB CDC, flash (oxirgi 4 KB sektor), tugma/LED, tasodif, 32 KB stek |
| `src/main_host.c` | kompyuter: stdin/stdout, flash fayli, `AQ_TUGMA` navbati, stek o'lchovi |
| `../../tools/pico_emulyator/` | `.uf2` ni rp2040js emulyatorida ishga tushirish (tugma, flash, vaqtlar) |

**Xotira:**

- Kod ≈ 64 KB.
- RAM ≈ 80 KB, shundan:
  - 32 KB — asosiy stek;
  - ~19 KB — ML-DSA arenasi;
  - ~12 KB — kirish/chiqish buferlari;
  - qolgani — kalitlar va boshqalar.

## 8. Xavfsizlik — RP2040 cheklovlari (MUHIM)

- **Flash himoyalanmagan.** Pico'ni qo'lga olgan odam BOOTSEL orqali flash'ni o'qib olishi
  mumkin. Kalit flash'da PIN'dan olingan kalit bilan shifrlangan (1024 marta SHA3), lekin
  qisqa PIN oflayn tez topiladi. **Uzun PIN** (12+ belgi yoki ibora) ishlating va Pico'ni
  seyfda saqlang. 5 ta xato urinishdan keyin kalit o'chirilishi faqat qurilmaning o'zi
  orqali qilinadigan taxminlarga qarshi ishlaydi.
- **TRNG yo'q.** Tasodif ROSC shovqini, `pico_rand` va vaqtdan SHA3 bilan yig'iladi. Kalit
  yaratishda kompyuter entropiyasi ham aralashtiriladi.
- **Secure boot yo'q.** Pico'ga boshqa (zararli) ichki dastur yozish mumkin. Xost buni qisman
  sezadi: har imzo ochiq kalit bilan tekshiriladi, seriya raqami esa profil bilan
  solishtiriladi.
- **Ekran yo'q.** Tugma nimani tasdiqlayotganini qurilma ko'rsatmaydi (3-bosqichda ESP32 panel).

**Haqiqiy pul uchun** Pico 2 (RP2350) kerak: OTP'da kalit, secure boot va debug portni
yopish. Ichki dastur shunga ko'chiriladigan qilib yozilgan: o'zgaradigan qism — faqat
`main_pico.c` (HAL).
