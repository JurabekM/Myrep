# Loyiha holati — halol hisobot

Bu hujjat «nima tayyor» degan savolga **o'zini maqtamasdan** javob
beradi. «Test o'tdi» va «ishlaydi» — ikki xil narsa, shuning uchun har
qator uchun **qanday tekshirilgani** ko'rsatilgan.

Sana: 2026-08-23

---

## 1. Tekshiruv darajalari

| Belgi | Ma'nosi |
|---|---|
| **A** | Haqiqiy build o'rnatilib/ishga tushirilib, natija ko'z bilan ko'rilgan |
| **B** | Avtomatik test bor va o'tadi |
| **C** | Kod yozilgan, lekin alohida test yo'q |
| **—** | Bajarilmagan |

---

## 2. Desktop

| Nima | Daraja | Izoh |
|---|---|---|
| Installer yig'iladi | **A** | 61.9 MB, Inno Setup, ogohlantirishsiz |
| O'rnatiladi va ishga tushadi | **A** | Repo tashqarisida, 1.1 s |
| 15 ta ekran ochiladi | **A+B** | GUI smoke test + ekran suratlari |
| Uch xil kirish nuqtasi | **B** | `run.py`, `-m distribos.main`, to'g'ridan-to'g'ri fayl |
| Lokal baza (WAL, FK) | **B** | PRAGMA'lar test bilan tasdiqlangan |
| Append-only trigger'lar | **B** | audit, hodisa, ombor, to'lov |
| Outbox tranzaksiyasi | **B** | §7.1 oqimi |
| 14 hisobot | **B** | Har biri GUI testida shakllantiriladi |
| PDF hujjatlar | **C** | Kod bor, GUI testida chaqirilmagan |
| Zaxira nusxa / tiklash | **B** | Shifrlash → tekshirish → tiklash |
| AI tavsiyalar | **A+B** | Ekranda 6 ta tavsiya ko'rindi |
| Kalitlar DPAPI ostida | **B** | O'rash/ochish + kontekst bog'lanishi |

## 3. Android

| Nima | Daraja | Izoh |
|---|---|---|
| Release APK / AAB yig'iladi | **A** | 26 MB / 18 MB, R8 bilan |
| DistribOS sertifikati bilan imzolangan | **A** | v2 + v3 sxema tasdiqlandi |
| Emulyatorda o'rnatiladi va ochiladi | **A** | Crash yo'q |
| 4 ta ekran | **A** | Qo'lda ochib chiqildi, suratlari bor |
| Room bazasi + trigger'lar | **C** | Kod bor, Robolectric testi yozilmagan |
| Rolga mos ekranlar | **C** | Kod bor, faqat `agent` roli sinaldi |
| Keystore | **C** | Emulyatorda ishladi, alohida test yo'q |
| Shtrix-kod skaneri | **—** | Bog'liqlik qo'shilgan, ekran yozilmagan |
| Kamera / foto | **—** | Bajarilmagan |
| WorkManager fon sinxronizatsiyasi | **—** | Hozircha faqat ekran ochiq bo'lganda |

## 4. Sinxronizatsiya va kripto

| Nima | Daraja | Izoh |
|---|---|---|
| Python ↔ Kotlin kripto mosligi | **B** | 22 test, baytma-bayt |
| Python ↔ Kotlin domen qoidalari | **B** | 159 vektor, 9 test |
| Offline buyurtma → desktop | **B** | To'liq zanjir (Python tomonida) |
| Dublikat (10×) | **B** | Replay oynasi + inbox dedup alohida |
| Tartib buzilishi | **B** | Teskari tartib + kechiktirilgan proyeksiya |
| Yo'qolgan xabar tiklanishi | **B** | Anti-entropy digest, brokersiz |
| Bir vaqtda tahrirlash | **B** | HLC, ikki qurilmada bir xil natija |
| Bekor qilingan qurilma | **B** | Hodisalari rad etiladi |
| Buzilgan/kesilgan/katta paket | **B** | Uchalasi ham rad etiladi |
| Begona tenant | **B** | Rad etiladi |
| Clock skew | **B** | 10 yillik chetlanish qabul qilinmaydi |
| Snapshot (chunk, resume, yaxlitlik) | **B** | Uzilib qolsa davom ettiriladi |
| Snapshot role-scoped | **B** | Omborchiga moliyaviy jadval tushmaydi |
| Kalit rotatsiyasi | **C** | Kod bor, offline qurilma ssenariysi sinalmagan |

---

## 5. BAJARILMAGAN yoki tekshirilmagan

Bular ochiq va ular haqida da'vo qilinmaydi.

### 5.1. Desktop ↔ Android jonli sinxronizatsiya

Protokol **baytma-bayt tasdiqlangan** (KAT testlari), lekin ikki qurilma
bir-birini avtomatik topmaydi: QR provisioning oqimi desktopda yaratiladi,
ammo Android tomonida skanerlash ekrani yozilmagan va epoch kalitini
uzatuvchi AETHER-Q sessiyasi UI'ga ulanmagan.

Ya'ni: **transport ishlaydi, kripto ishlaydi, ulash oqimi tugallanmagan.**

### 5.2. Unumdorlik

Topshiriqdagi mezonlar (100 000 mahsulot, 1 million hodisa, 50 000
mahsulotli mobil katalog) **o'lchanmagan**. Indekslar qo'yilgan, lekin
benchmark yo'q. Desktop ishga tushishi o'lchandi: 1.1 s.

### 5.3. Haqiqiy qurilma

Faqat emulyator (Medium_Phone_API_36) sinaldi. Haqiqiy telefonda —
xususan zaif qurilmada va yomon tarmoqda — sinalmagan.

### 5.4. Lokal konteynerli MQTT broker

Integratsion testlar uchun Mosquitto/HiveMQ CE konteyneri **sozlanmagan**.
Hozircha sinxronizatsiya mantiqi soxta transport ustida sinaladi.

### 5.5. Boshqalar

* Alembic migratsiyalari yozilmagan (hozircha `create_all`);
* ovozli buyurtma (speech-to-text) — yo'q;
* tashqi AI provayder abstraksiyasi — faqat lokal maslahatchi bor;
* uz-Kirill va rus tillari — kalitlar tayyor, tarjimalar yo'q;
* CI (GitHub Actions) — sozlanmagan;
* soak test — bajarilmagan.

---

## 6. Ma'lum xatarlar

| Xatar | Ta'siri | Yumshatish |
|---|---|---|
| DES-1 auditdan o'tmagan | Noma'lum zaiflik bo'lishi mumkin | Mustaqil ko'rib chiqish kerak |
| Ochiq broker | Uzilish, ban, metama'lumot | `PRIVATE_PRODUCTION` profiliga o'tish |
| ML-DSA imzosi 3309 bayt | Trafik va batareya | Batch (50 hodisagacha) |
| Qoldiq to'liq qayta hisoblanadi | Ko'p harakatda sekinlashadi | Hozircha o'lchanmagan |
| Android `agent` rolидан boshqasi sinalmagan | Ekranlar noto'g'ri bo'lishi mumkin | Qo'lda sinash kerak |

---

## 7. Keyingi qadam uchun tavsiya

Ustuvorlik tartibida:

1. QR provisioning oqimini ikkala tomonda tugatish — hozir bu yagona
   uzilgan halqa.
2. Lokal konteynerli broker bilan integratsion test.
3. Unumdorlik o'lchovi (100k mahsulot, 1M hodisa).
4. Alembic migratsiyalari — sxema o'zgarishi ma'lumotni yo'qotmasin.
5. DES-1 uchun mustaqil kriptografik ko'rib chiqish.
