# Xavfsizlik

Bu hujjat nima **kafolatlanadi**, nima **kafolatlanmaydi** va nima
**tekshirilmagan** — uchalasini ham aniq ajratadi.

---

## 1. Uch qatlam, uch xil ishonch darajasi

### 1.1. AETHER-Q v5.1 — o'zgartirilmagan

Primitivlar `apps/desktop/src/distribos/aether_q/vendor/` da yotadi va
**baytma-bayt** nusxa. Har o'zgarish `tests/security/test_aetherq_vendor.py`
dagi SHA-256 manifest bilan aniqlanadi.

Nega bu muhim: `ruff --fix` yoki formatter auditdan o'tgan kripto kodini
«tozalab» qo'yishi mumkin. Kod ishlashda davom etadi, hech qanday test
yiqilmaydi — o'zgarish jimgina o'tib ketadi. Kriptografiyada auditor
tekshirgan bayt bilan ishlatilayotgan bayt bir xil bo'lishi SHART.

Ishlatiladigan profillar: **0x01** (X25519 + ML-KEM-768) va **0x03**
(ML-KEM-768 standalone).

**Ishlatilmaydi:** 0x06 (ZKP), 0x07 (threshold), 0x08 (PUF). Bular
AETHER-Q ning 5-audit raundida ikkita KRITIK topilma (AQ-L01 soundness,
AQ-L02 kvant modelida yaroqsiz yumshatuv) sababli deployable build'dan
chiqarilgan. Ular repositoryga **umuman olib kelinmagan** va buni test
qulflaydi.

**AETHER-Q maqomi (uning o'z hujjatlaridan):** tadqiqot/demo — tayyor;
pilot — shartli; **production — mustaqil audit SHART**. DistribOS AI
uni kuchli, sinovdan o'tgan qatlam sifatida ishlatadi, lekin
**sertifikatlangan deb da'vo qilmaydi**.

### 1.2. DES-1 — bizning konstruksiya

⚠ **DES-1 AETHER-Q spetsifikatsiyasining qismi EMAS.**

AETHER-Q §8 record qatlami sessiyaviy: yo'nalishli kalitlar, monotonik
`seq`, AEAD tag xatosi fatal. MQTT esa pub/sub va store-and-forward:
xabar dublikat bo'ladi, tartibi almashadi, va bir xabarni bir nechta
qurilma o'qishi kerak. Ikkisi to'g'ridan-to'g'ri ulanmaydi
([ADR-0001](adr/0001-aetherq-mqtt-ustida.md)).

DES-1 — AETHER-Q **primitivlari ustiga** qurilgan envelope:

* maxfiylik — epoch kaliti bilan ChaCha20-Poly1305;
* jo'natuvchi autentifikatsiyasi — har hodisaga **alohida ML-DSA-65 imzo**;
* tenant izolyatsiyasi — KMAC256 teg, ochiq matnda tenant nomi yo'q;
* replay — `(epoch, device, seq)` sliding-window;
* downgrade himoyasi — `profile_id` har KDF'ga bind (AETHER-Q N1/S5).

**Yangi kriptografik primitiv o'ylab topilmagan.** Lekin kompozitsiyaning
o'zi mustaqil auditdan **o'tmagan**. Wire-format:
[specs/distribos-event-seal/DES-1.md](../specs/distribos-event-seal/DES-1.md).

Python va Kotlin implementatsiyalari 22 ta test bilan baytma-bayt
solishtiriladi (`tests/interoperability/des1_kat.json`).

### 1.3. Ochiq broker — pilot uchun

`broker.hivemq.com`, TLS porti **8883** (rasmiy manbadan tekshirilgan).

HiveMQ o'z shartlarida so'zma-so'z aytadi:

* broker «Production, Dev, Staging or UAT» muhitlarida ishlatilmasin;
* **maxfiy va shaxsiy ma'lumot uzatilmasin**;
* uptime kafolati yo'q, yangilanishda **xabar yo'qoladi**;
* foydalanuvchi **ban** qilinishi mumkin.

Bu bizning qoidalarimizdan **qattiqroq**. Shuning uchun:

* `PUBLIC_PILOT` profilida `production_secure` **hech qachon** true emas;
* `broker.hivemq.com` + `PRIVATE_PRODUCTION` kombinatsiyasi ishga tushishni
  **rad etadi** (jim tuzatilmaydi);
* ilova ishga tushganda ogohlantirish ko'rsatiladi va tasdiq so'raladi.

---

## 2. Nima kafolatlanadi

| Xususiyat | Qanday ta'minlanadi |
|---|---|
| Xabar mazmuni brokerdan yashirin | ChaCha20-Poly1305, kalit faqat qurilmalarda |
| Jo'natuvchi haqiqiyligi | Har hodisaga ML-DSA-65 imzo |
| Bekor qilingan qurilma rad etiladi | Revocation tekshiruvi **imzodan oldin** (bekor qilingan qurilma imzosi hali ham matematik to'g'ri) |
| Takroriy xabar bir marta qo'llanadi | Ikki qatlam: replay oynasi (kripto) + inbox dedup (biznes) |
| Begona tenant rad etiladi | KMAC256 tenant tegi, constant-time solishtirish |
| Downgrade himoyasi | `profile_id` har KDF'ga bind |
| Topikda maxfiy ma'lumot yo'q | Tenant/qurilma ID — domain-ajratilgan hash |
| Kalitlar diskda ochiq emas | Windows DPAPI / Android Keystore |
| Audit o'chirilmaydi | SQLite TRIGGER (ORM emas — xom SQL ham to'xtatiladi) |
| Qoldiq qayta yozilmaydi | `inv_movement` append-only, trigger bilan |
| To'lov o'chirilmaydi | Trigger; bekor qilish = teskari yozuv |

---

## 3. Nima KAFOLATLANMAYDI

* **Metama'lumot maxfiyligi.** Broker kim, qachon, qancha bayt
  yuborganini ko'radi. Topik nomi opaque, lekin trafik naqshi ko'rinadi.
* **Ochiq brokerning mavjudligi.** U istalgan vaqtda uzilishi, xabarni
  yo'qotishi yoki bizni ban qilishi mumkin.
* **Ma'lumotni tiklash.** Agar barcha qurilmalar yo'qolsa va tashqi zaxira
  nusxa bo'lmasa — broker tiklash manbai **EMAS**.
* **Qurilma o'g'irlanganda oldingi ma'lumot.** Revocation keyingi
  hodisalarni to'xtatadi, lekin qurilmadagi mavjud nusxa uning qo'lida
  qoladi. Shu sababli telefonga **rolga mos** ma'lumotgina beriladi.
* **Kriptografik audit.** Na AETHER-Q kompozitsiyasi, na DES-1 mustaqil
  auditdan o'tgan.

---

## 4. Loglarda nima bo'lmaydi

Quyidagilar jurnalga **yozilmaydi**:

* ochiq biznes payload;
* kalitlar va maxfiy material (`EpochKeys.__repr__` ataylab qayta yozilgan);
* AETHER-Q ichki holati;
* mijozlarning keraksiz shaxsiy ma'lumotlari;
* AI provider secretlari.

Rad etish sabablari (`RejectReason`) **faqat lokal** yoziladi va tarmoqqa
qaytarilmaydi — AETHER-Q N15 (oracle himoyasi).

Yordam to'plami (`Sozlamalar > Yordam to'plami`) faqat texnik holatni
o'z ichiga oladi; foydalanuvchi uni yuborishdan oldin ko'radi.

---

## 5. Zaxira nusxa

Server yo'q — nusxa **majburiy biznes funksiyasi**.

* ChaCha20-Poly1305 + scrypt (parol asosida, DPAPI'ga bog'lanmagan:
  kompyuter buzilsa nusxa boshqa mashinada ochilishi kerak);
* SQLite `backup` API — ilova ishlab turganda ham **izchil** nusxa;
* `verify_backup()` alohida funksiya: «nusxa bor» ≠ «nusxa ishlaydi»;
* tiklashda eski baza o'chirilmaydi, `.replaced-<vaqt>` nomi bilan chetga
  olinadi.

---

## 6. Zaiflik haqida xabar berish

Zaiflik topsangiz uni ommaga e'lon qilishdan oldin loyiha egasiga
xabar bering. Aloqa ma'lumotlari alohida shartnomada.

DES-1 kompozitsiyasi bo'yicha mustaqil ko'rib chiqish alohida
**kutilmoqda** — bu ochiq vazifa.
