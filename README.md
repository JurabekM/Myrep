# DistribOS AI

Ulgurji savdo, distribyutsiya va ombor uchun **serversiz, offline-first**
desktop va Android tizimi.

Markaziy backend, markaziy ma'lumotlar bazasi va web-dashboard **yo'q**.
Har bir qurilma to'liq huquqli: o'z lokal bazasi bor, internetsiz ishlaydi
va boshqa qurilmalar bilan to'g'ridan-to'g'ri sinxronlanadi. MQTT broker
faqat shifrlangan baytlarni tashiydi — biznes ma'lumotining manbai yoki
ombori emas.

---

## Holat: nima TEKSHIRILGAN, nima yo'q

Bu bo'lim ataylab birinchi turadi. Quyidagilar **haqiqatan bajarilib**
tasdiqlangan:

| Nima | Qanday tekshirilgan |
|---|---|
| Desktop ishga tushadi | Installer o'rnatildi, `DistribOS.exe` repo tashqarisida **1.1 s** da ishga tushdi |
| Desktop ekranlari | 15 ta ekran GUI testida ochilib, ma'lumot yuklanishi tekshirildi |
| Android ishga tushadi | Release APK emulyatorda o'rnatildi va ochildi, crash yo'q |
| **Jonli sinxronizatsiya** | Haqiqiy `broker.hivemq.com` orqali: telefon ulandi, 4 hodisa kompyuterga yetdi, kompyuterning mahsuloti telefonga yetdi, 0 rad etilgan xabar |
| **Reliz APK jonli sinovi** | Minifikatsiyalangan APK ham xuddi shu yo'l bilan ulandi — R8 aynan shu yerda xato chiqargan edi |
| Android ekranlari | 4 ta ekran emulyatorda qo'lda ochib chiqildi, suratlari `docs/screenshots/` da |
| Kripto mosligi | Python ↔ Kotlin **baytma-bayt**: 32 test (SHA3, HKDF, KMAC, cSHAKE, DES-1, BOOT-1, ML-DSA-65) |
| Domen qoidalari mosligi | Python ↔ Kotlin **159 vektor**, 9 test (yaxlitlash chegaralari bilan) |
| Offline buyurtma | Uzilish → telefonda buyurtma → ulanish → desktopda paydo bo'ldi (avtomatik test) |
| Dublikat va tartib buzilishi | Xaos testlari: 10× dublikat, teskari tartib, yo'qolgan xabar |
| Zaxira nusxa | Shifrlash → tekshirish → tiklash zanjiri testda |
| Installer | O'rnatildi, ishga tushdi, o'chirishda baza tegilmasligi qoidasi yozilgan |
| **Lokal broker integratsiyasi** | Docker'dagi haqiqiy Mosquitto (TLS) orqali: hodisa yetdi, aks-sado behuda yozuv qoldirmadi, ikki yo'nalish ishladi — `broker.hivemq.com`ga bog'liq emas |
| **Alembic migratsiyasi** | Real reliz `.exe` eski (`create_all()`) bazani ochib, ma'lumotni yo'qotmasdan sxemaga stamp qildi |
| Unumdorlik | 100k mahsulot / 1M hodisada o'lchandi (`docs/BENCHMARK.md`) — bitta ochiq savol bor (izohlangan) |
| CI (GitHub Actions) | 4 ish (`python`, `python-integration`, `kotlin-pure`, `kotlin-android`) haqiqiy runnerda yashil |
| `presentation/` mypy strict | 0/47 xato — ikkita haqiqiy xato tuzatildi (tur izohi emas) |
| **Lokalizatsiya (rus)** | `presentation/` qatlami TO'LIQ — 384 kalit, 9 sinov, paketlangan `.exe`da skrinshot bilan tasdiqlandi |

**Hali tekshirilmagan** (halol ro'yxat, `docs/HOLAT.md` da batafsil):

* rus tarjimasi hisobot/hujjat/AI matnlarida yo'q (`reports/`, `ai/` — ataylab, eksport tili masalasi hal qilinmagan);
* haqiqiy qurilmada (emulyator emas) sinov;
* uzoq muddatli (soak) sinov;
* DES-1 uchun mustaqil kriptografik ko'rib chiqish.

---

## Xavfsizlik — halol baho

Xabarlar **AETHER-Q v5.1** primitivlari bilan himoyalanadi: ML-KEM-768
(FIPS 203), ML-DSA-65 (FIPS 204), HKDF-SHA3-256, ChaCha20-Poly1305.

Uchta narsani aniq ajratish kerak:

1. **AETHER-Q v5.1** — loyiha egasining protokoli. Uning o'z hujjatlari
   bo'yicha maqomi: *tadqiqot/demo — tayyor; pilot — shartli; production —
   mustaqil audit SHART*. Biz uni o'zgartirmasdan ishlatamiz va
   baytma-bayt nusxaligini SHA-256 manifest bilan qulflaymiz.

2. **DES-1** — hodisa muhri. Bu **AETHER-Q spetsifikatsiyasining qismi
   EMAS**. AETHER-Q §8 record qatlami sessiyaviy (monotonik `seq`, tartib
   buzilsa fatal), MQTT esa dublikat/tartibsiz — ikkisi to'g'ridan-to'g'ri
   ulanmaydi (`docs/adr/0001`). DES-1 AETHER-Q primitivlari ustiga
   qurilgan; yangi kripto o'ylab topilmagan, lekin **kompozitsiyaning
   o'zi mustaqil auditdan o'tmagan**.

3. **Ochiq broker** — `broker.hivemq.com`. HiveMQ o'z shartlarida bu
   brokerni «Production, Dev, Staging or UAT» muhitlarida ishlatishni
   **man qiladi** va maxfiy ma'lumot uzatmaslikni talab qiladi. Shuning
   uchun `PUBLIC_PILOT` profilidagi build **hech qachon**
   «production-secure» deb belgilanmaydi — buni kod majburlaydi.

Batafsil: [docs/SECURITY.md](docs/SECURITY.md)

---

## Tuzilma

```
apps/
  desktop/          PySide6 + SQLAlchemy + SQLite (WAL)
  android/          Kotlin + Compose + Room
contracts/          Python va Kotlin O'QIYDIGAN yagona kontrakt
specs/
  aether-q-v5.1/    protokol hujjatlari xaritasi
  distribos-event-seal/  DES-1 wire-format
tests/
  security/         kripto va vendor yaxlitligi
  sync-chaos/       tarmoq buzilishlari
  interoperability/ Python ↔ Kotlin vektorlari
  end-to-end/       to'liq ssenariy + GUI smoke
packaging/          Windows installer
docs/adr/           arxitektura qarorlari
```

---

## Ishga tushirish

### Desktop (manba kodidan)

```bash
python run.py
```

Holat tekshiruvi (grafik muhitsiz):

```bash
python run.py --check
```

### Desktop (installer)

```bash
python packaging/build_windows.py
```

Natija: `dist/DistribOS-Setup-1.0.0.exe`

### Android

```bash
cd apps/android
./gradlew :app:assembleRelease :app:bundleRelease
```

Reliz build uchun `keystore.properties` **SHART** — kalitsiz build
ataylab yiqiladi (debug kalit bilan imzolangan APK tarqalib ketmasin).
Batafsil: [docs/BUILDING.md](docs/BUILDING.md)

### Testlar

```bash
python -m pytest                              # tezkor (integratsion sinovsiz)
python -m pytest tests/integration -m integration   # Docker talab qiladi
```

```bash
cd apps/android && ./gradlew :crypto:test :domain:test
```

CI: `.github/workflows/ci.yml` — ruff, pytest, lokal broker integratsion
sinovi va Kotlin testlari har push/PR'da.

---

## Asosiy qarorlar

| Qaror | Sabab |
|---|---|
| Broker ma'lumot ombori EMAS | Retained xabar bilan «broker = baza» qilish HiveMQ shartlarini buzadi va broker tozalansa hammasi yo'qoladi ([ADR-0003](docs/adr/0003-broker-ombor-emas.md)) |
| Har hodisaga alohida ML-DSA imzo | Faqat guruh kaliti bo'lsa, kalitni bilgan a'zo boshqa qurilma nomidan yozuv yasay oladi — audit va revocation buziladi |
| Pul — BUTUN son (tiyin) | SQLite'da REAL ustunda `SUM()` aniqlikni yo'qotadi |
| Qoldiq harakatlardan hisoblanadi | Overwrite qilinsa, ikki qurilma bir vaqtda sotganda «yo'qolgan yangilanish» bo'ladi |
| To'lov o'chirilmaydi | Xato bo'lsa teskari yozuv — tarix saqlanadi |
| Kripto BouncyCastle ustida (Android) | Platformada SHA3 faqat API 28 dan, SHAKE256 umuman yo'q; minSdk 26 da qolish uchun |
| Hilt ishlatilmadi | Bog'liqliklar kam va ilova umri davomida bitta nusxada — qo'lda bog'lash soddaroq |

---

## Litsenziya

Mulkiy. Uchinchi tomon komponentlari va ularning litsenziyalari:
[LICENSE](LICENSE).
