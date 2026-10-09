# Zarbxona v3 — davom ettirish uchun eslatma

*Yangilangan: 2026-10-09. Keyingi sessiya shu fayldan boshlasin.*

## 1. Loyiha qayerda to'xtagan

**Dasturiy qism tugagan.** 4.x (Pico imzo kaliti) ning 1- va 2-bosqichlari kodda tayyor va
kompyuterda sinalgan. **Haqiqiy Pico'da hali sinalmagan.**

**Git:**
- tarmoq: `claude/focused-galileo-1pmwcp`;
- PR: https://github.com/JurabekM/Myrep/pull/4 — ochiq, `master` ga merge qilinmagan;
- PR kuzatuvi foydalanuvchi so'rovi bilan to'xtatilgan.

**Testlar:**
- lokal 223 o'tdi, 1 skip (A1);
- Pico ichki dasturi testlari faqat `AQ_PICO_HOST` berilganda ishlaydi.

**CI:**
- ubuntu va windows, Python 3.12 va 3.13;
- Windows `.exe`;
- Pico `.uf2` (artifact `zarbxona-pico-hsm-uf2`);
- Linux'da ichki dasturning kompyuter varianti bilan testlar.

**Bajarilganlar:**
- takliflar 1.1, 2.1, 1.4, 1.2, 3.1, 3.2, 3.3, 3.4, 3.5;
- CLI, `.exe`, soat himoyasi;
- 4.x (1–2-bosqich).

**Hali sinalmagan** (batafsil: `README.md`, «Holat» bo'limi):
- A1–A6 va haqiqiy `aetherq_core`;
- haqiqiy MQTT broker;
- GUI va `run.bat` haqiqiy Windows'da;
- **Pico ichki dasturi haqiqiy RP2040'da**.

## 2. 4.x — nima qilindi

**Foydalanuvchidagi jihoz:** Raspberry Pi Pico (RP2040, chip `RP2-B2`).

**Xost tomoni:**

| Fayl | Nima |
|---|---|
| `core/imzolovchi.py` | `Imzolovchi` interfeysi: fayl yoki Pico. Imzo turlari: partiya, jurnal boshi, mint_auth |
| `core/pico/` | AQP1 protokoli, `PicoImzolovchi`, soxta Pico (etalon), flash yozuvi (PIN), port va `imzolovchi.json` |

Zarbxona bilan bog'lanishi:

- Buyurtma boshida `ruxsat` — tugma; Pico faqat shu summagacha imzolaydi.
- Imzo olinmasa (rad, uzilish, ruxsat tugadi) — buyurtma pauzaga o'tadi.

Interfeyslar:

- **GUI:** kirishda Pico PIN; "Kalit" sahifasida Pico kartasi; tugma banneri; chiqishda QULFLA.
- **CLI:** `pico portlar | holat | sozla --import|--yangi | qaytish`, `ZARBXONA_PICO_PIN`.

**Ichki dastur:** `firmware/pico_hsm/` (C, pico-sdk 2.1.1, mldsa-native v2.0.0).

- `aq_hsm.c` — SDK'siz yadro; `main_pico.c` — RP2040 HAL.
- RP2040 HAL: USB CDC, flash'ning oxirgi sektori, GP14 tugma, GP15 LED, ROSC tasodifi,
  32 KB stek.
- `main_host.c` — kompyuter varianti (testlar uchun).

**Hujjatlar:** `docs/PICO_PROTOKOL.md` (protokol), `firmware/pico_hsm/README.md` (ulanish,
yuklash, xavfsizlik).

## 3. Keyingi qadamlar

1. **Foydalanuvchi Pico'da sinaydi** — `firmware/pico_hsm/README.md`, 5-bo'lim. Natijalarni
   yozib qo'yish kerak:
   - port ko'rindimi;
   - `pico holat` ishladimi;
   - kalit yaratish va imzo qancha soniya oldi;
   - tugma, LED va USB uzilishi to'g'ri ishladimi.

   Muammo bo'lsa, eng ehtimoliy joylar:
   - `main_pico.c` (stdio_usb, flash_safe_execute);
   - xostdagi `ODDIY_KUTISH_S` (imzo sekin bo'lsa).
2. **Pico 2 (RP2350) ga ko'chirish** — haqiqiy pul uchun:
   - kalit OTP'da yoki OTP kalit bilan shifrlangan;
   - secure boot, debug portni yopish, TRNG.

   Faqat HAL (`main_pico.c`) va CMake'dagi `PICO_BOARD` o'zgaradi.
3. **3-bosqich — ESP32 panel (yoki Pico'ga kichik OLED):** tugma nimani tasdiqlayotganini
   (buyurtma id, summa) qurilmaning o'zi ko'rsatsin. Hozir matnni faqat kompyuter ko'rsatadi.

## 4. Ish qoidalari (o'zgarmaydi)

- `tools/kat_tekshir.py` ni **bulutda ishga tushirmaslik** — bu foydalanuvchining fayli.
- Push faqat `claude/focused-galileo-1pmwcp` ga qilinadi.
  - PR #4 merge bo'lgan bo'lsa: tarmoqni `master` dan qayta boshlash kerak.
  - Yangi PR faqat foydalanuvchi so'rasa ochiladi.
- **Testlar:**

  ```
  QT_QPA_PLATFORM=offscreen python -m pytest -q
  ```

  Python 3.12+ va `cryptography>=47` kerak.

- **Pico ichki dasturi testlari:**

  ```
  cmake -S firmware/pico_hsm -B /tmp/ph -DAQ_HOST=ON && cmake --build /tmp/ph
  AQ_PICO_HOST=/tmp/ph/pico_hsm_host python -m pytest -q tests/test_pico_ichki.py
  ```
