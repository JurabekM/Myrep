# Zarbxona v3 — davom ettirish uchun eslatma

*Yozilgan: 2026-10-09. Keyingi sessiya shu fayldan boshlasin.*

## 1. Loyiha qayerda to'xtagan

**Dasturiy qism tugagan, 4.x apparat qismi hali BOSHLANMAGAN.** 4.x faqat reja holida.

- **Git holati:**
  - tarmoq `claude/focused-galileo-1pmwcp`, oxirgi kommit `6a2b208`;
  - PR: https://github.com/JurabekM/Myrep/pull/4 — ochiq, CI yashil, konfliktsiz, `master` ga hali merge qilinmagan;
  - PR kuzatuvi foydalanuvchi so'rovi bilan to'xtatilgan.
- **Testlar:** lokal 165 o'tdi, 1 skip (A1 — haqiqiy AETHER-Q yo'q).
- **CI:**
  - ubuntu va windows, Python 3.12 va 3.13;
  - Windows `.exe` yig'ilib, `--version` va `--selftest` dan o'tdi (artifact `Zarbxona-windows`).
- **Bajarilgan takliflar tartibi:**
  - 1.1 buzish demosi (nusxada);
  - 2.1 CI;
  - 1.4 parol, zaxira va ogohlantirishlar;
  - 1.2 jurnal xesh-zanjiri;
  - 3.1 demo bank;
  - 3.2 jonli grafiklar;
  - 3.3 ikki kishilik tasdiq;
  - 3.4 PDF hisobot va 3.5 isbot/QR;
  - CLI, `.exe` paketi, soat himoyasi, sirlarni tozalash.
- **Hali sinalmagan** (batafsil: `README.md`, «Holat» bo'limi):
  - A1–A6 va haqiqiy `aetherq_core`;
  - haqiqiy MQTT broker;
  - `run.bat` va GUI haqiqiy Windows ekranida;
  - kod imzolash.

## 2. Keyingi ish: 4.x — Pico asosidagi imzo kaliti (HSM)

**Maqsad:** ML-DSA-65 maxfiy kaliti hech qachon kompyuter xotirasiga tushmasin. Kompyuter faqat imzolanadigan xabarni yuboradi va tayyor imzoni oladi. Har bir imzo jismoniy tugma bilan tasdiqlanadi.

**Foydalanuvchidagi jihoz:**
- Raspberry Pi **Pico (RP2040)** — chip yozuvi `RP2-B2`, ya'ni Pico 2 emas.
- Cheklovlar:
  - RP2040 da secure boot va OTP yo'q;
  - flash'ni BOOTSEL orqali o'qib olish mumkin.
- Shuning uchun:
  - kalit flash'da PIN'dan olingan kalit bilan shifrlanib saqlanadi;
  - bu prototip/demo darajasi; haqiqiy pul uchun keyin Pico 2 (RP2350) ga o'tiladi.
- Dastur ikkala platani ham qo'llaydigan qilib yoziladi.

**Kerakli qo'shimcha jihozlar:** tugma, 1–2 LED, 220–330 Ω rezistorlar, ma'lumot o'tkazadigan micro-USB kabel.

### 1-bosqich — apparatsiz (keyingi sessiya SHUNDAN boshlaydi)
1. **`core/imzolovchi.py` — `Imzolovchi` interfeysi.**
   - Metodlar: `ochiq_kalit()` va `imzola(xabar) -> imzo`.
   - Ikki turi bo'ladi:
     - `FaylImzolovchi` — hozirgi `kalit.json`, xatti-harakati o'zgarmaydi;
     - `PicoImzolovchi` — USB orqali.
   - `Zarbxona._imzo`, jurnal zanjir boshi imzosi va `partiya.zarb_qil` ichidagi imzo shu interfeysdan o'tadi.
2. **`docs/PICO_PROTOKOL.md` — USB CDC protokoli.**
   - Ramka: sehrli bayt, versiya, buyruq, uzunlik, ma'lumot, CRC.
   - Buyruqlar: `SALOM`/versiya, `OCHIQ_KALIT`, `KALIT_YARAT`, `PIN_OCH`, `IMZOLA`, `HOLAT`.
   - Xato kodlari; tugmani kutish uchun vaqt chegarasi.
   - `IMZOLA` uchun qurilma qo'shimcha ravishda imzo hisoblagichini (counter) qaytaradi.
3. **`core/soxta_pico.py` — kompyuterda ishlaydigan soxta Pico.**
   - Protokolni to'liq bajaradi.
   - «Tugma bosildi/bosilmadi» va «uzildi» holatlarini simulyatsiya qiladi.
4. **Testlar:**
   - protokol ramkalari (hypothesis bilan fuzz);
   - soxta Pico bilan to'liq zarb sikli;
   - tugma bosilmasa zarb to'xtashi;
   - qurilma uzilsa buyurtma pauzaga o'tib, keyin davom etishi.
5. **GUI:**
   - Kalit sahifasida «Imzolovchi: fayl / Pico» tanlovi va Pico holati.
   - Zarb paytida «tugmani bosing» ko'rsatkichi.

### 2-bosqich — Pico ichki dasturi (Pico qo'lda)
- **Til:** C (pico-sdk). MicroPython ML-DSA uchun juda sekin va xotirasi kam.
- **ML-DSA-65:** tekshirilgan ochiq implementatsiya (masalan, PQClean yoki mldsa-native) ishlatiladi.
  - KAT orqali kompyuterdagi `cryptography` imzolari bilan tekshiriladi.
  - Tezlik Pico'da o'lchanadi; oldindan taxmin qilinmaydi.
- **Xavfsizlik:**
  - kalit qurilma ichida yaratiladi va eksport buyrug'i yo'q;
  - flash'da PIN bilan shifrlanadi;
  - har imzoda tugma bosilishi shart, LED holatni ko'rsatadi.

### 3-bosqich — ESP32 panel (ixtiyoriy)
Zarb holatini alohida ekranda ko'rsatadi.

## 3. Ish qoidalari (o'zgarmaydi)
- `tools/kat_tekshir.py` ni **bulutda ishga tushirmaslik** — bu foydalanuvchining fayli, uni o'zi ishga tushiradi.
- Push faqat `claude/focused-galileo-1pmwcp` ga qilinadi.
  - Agar PR #4 merge bo'lgan bo'lsa: tarmoqni `master` dan qayta boshlab, yangi PR ochiladi.
  - Yangi PR faqat foydalanuvchi so'rasa ochiladi.
- **Testlarni ishga tushirish:**
  ```
  QT_QPA_PLATFORM=offscreen python -m pytest -q
  ```
  Python 3.12+ va `cryptography>=47` kerak.
