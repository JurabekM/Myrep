# ROSTOR-1 — O'zbekiston kiberfiribgarligiga qarshi ishonch protokoli

**[docs/SPEC-ROSTOR-1.1.md](docs/SPEC-ROSTOR-1.1.md)** spetsifikatsiyasining
**to'liq ijro etiladigan implementatsiyasi**: institutsional ishonch (IC/IDC),
shaffoflik jurnali (SMT + append-only log + witness-cosign), tranzaksiya
tasdiqlash (anti-vishing), pul qabul qilish, akkount tiklash, firibgarlik
hisoboti, APK obro'si — va bularning barchasi **6 ta real O'zbekiston
kiberfiribgarlik vektoriga** (T1-T6) qarshi hujum laboratoriyasida sinalgan.
Transport qatlami — post-kvant gibrid `SCUTUM-Q1` (o'zgarishsiz meros).

| Fayl | Nima |
|---|---|
| [`docs/SPEC-ROSTOR-1.1.md`](docs/SPEC-ROSTOR-1.1.md) | **Normativ spetsifikatsiya** — tashqi ko'rikdan keyingi, 11 topilma tuzatilgan |
| [`docs/SPEC-ROSTOR-1.0-pre-review.md`](docs/SPEC-ROSTOR-1.0-pre-review.md) | Tashqi ko'rikdan oldingi versiya (tarixiy) |
| [`kat/rostor-1-kat.json`](kat/rostor-1-kat.json) | ROSTOR-1 normativ test vektorlari (deterministik) |
| `scutum/rostor/` | Ilova qatlami: SMT, transparency, registrar, identity, badge, txn_confirm, payment, account, fraud_report, apk |
| `scutum/sim/rostor_world.py`, `fraud_attacks.py` | Simulyatsiya dunyosi va T1-T6 hujum laboratoriyasi |
| `scutum/gui/panels/institutions.py` va yana 3 ta | ROSTOR GUI panellari |
| [`docs/SPEC-SCUTUM-Q1-v1.1.md`](docs/SPEC-SCUTUM-Q1-v1.1.md) | **Transport qatlami spetsifikatsiyasi** — 16+1 topilma tuzatilgan (K-6 — ROSTOR implementatsiyasi paytida tashqi ko'rikdan topildi) |
| [`docs/SPEC-v1.0-original-Qalqon-Q.md`](docs/SPEC-v1.0-original-Qalqon-Q.md) | Original transport spec (tarixiy) |
| [`kat/scutum-q1-kat.json`](kat/scutum-q1-kat.json) | Transport qatlami test vektorlari |

> ⚠️ Bu **ishlab chiqarish uchun emas**. Maqsad — spetsifikatsiyani sinab
> ko'rish, o'lchash va real hujum ssenariylarini jonli namoyish qilish.
> Chiqarish mezoni (spec §19): mustaqil audit, formal verifikatsiya va
> yon-kanal tahlili hali bajarilmagan.

---

## ROSTOR-1: 6 real tahdid, ikkala holatda ijro etilgan

`python -m scutum.rostor_kat` — KAT generatsiyasi. Testlar: `python run.py --tests`
(51/51, SPEC va HARDENED). Hujum laboratoriyasi `python run.py` GUI'sida
**"Firibgarlik lab (T1-T6)"** panelida, yoki dasturiy: `scutum.sim.fraud_attacks.run_all()`.

```
tahdid  nom                                    UNPROTECTED   PROTECTED
------------------------------------------------------------------------
T1      Telegram Android SMS-stealer/dropper   BROKEN        SAFE
T2      Bank fishing + vishing (OTP aytdirish) BROKEN        SAFE
T3      Davlat/sud nomidan qo'rqitish          BROKEN        SAFE
T4      SIM swap orqali akkount egallash       BROKEN        SAFE
T5      Classiscam bozor firibgarligi          BROKEN        SAFE
T6      Soxta investitsiya/ish e'lonlari       BROKEN        SAFE
------------------------------------------------------------------------
```

`UNPROTECTED` — bugungi ROSTOR-integratsiyasiz oddiy oqim (SMS OTP,
tekshiruvsiz APK, imzosiz "pul olish" sahifasi); `PROTECTED` — ROSTOR-1
mexanizmi (`scutum/rostor/`) haqiqiy kod bilan ijro etilgan. §16 (spec)
da halol qayd etilgan: T6 uchun **birinchi qurbonlar** himoyalanmaydi —
tizim faqat `MIN_K` chegarasidan keyingi qurbonlarni ogohlantiradi.

## Nomlash sxemasi (transport qatlami)

| Daraja | Nom | Qayerda uchraydi |
|---|---|---|
| Protokol oilasi | **SCUTUM** | brend, paket nomi (`scutum`), CLI |
| Kripto profil / suite | **SCUTUM-Q1** | `Envelope.suite` maydoni (AAD ichida) |
| Xabar almashinuvi moduli | **S-MSG** | spec §5–§6 |
| Fayl moduli | **S-FILE** | spec §7 |
| Domen ajratgichlari | `SCUTUM-Q1/...` | KDF `info`/`salt`, imzo prefikslari |
| ROSTOR-1 domen ajratgichlari | `ROSTOR-1/...` | SMT, jurnal, TXN_CONFIRM, va h.k. — `docs/SPEC-ROSTOR-1.1.md` §21.2 |

`SCUTUM` — lotincha rim legioneri qalqoni. `Q1` — post-kvant (quantum-resistant)
birinchi avlod profili; keyingi avlodlar `Q2`, `Q3` bo'ladi va `suite` maydoni
orqali muzokara qilinadi.

> **Buzuvchi o'zgarish.** Domen ajratgich satrlari (`"Qalqon-Q/1/…"` →
> `"SCUTUM-Q1/…"`) KDF kirishiga to'g'ridan-to'g'ri kiradi, shuning uchun
> barcha derivatsiya qilingan kalitlar — `RK0`, `MK`, `chunk_key_i`,
> `device_fingerprint` — oldingi versiyaga nisbatan **butunlay boshqacha**.
> Wire formatidagi `suite` qiymati ham `"QQ-1"` dan `"SCUTUM-Q1"` ga o'zgardi.
> Interop yoki e'lon qilingan test vektorlari hali bo'lmagani uchun bu xavfsiz;
> bundan keyin bunday o'zgarish yangi profil raqamini talab qiladi.

---

## Asosiy g'oya: bitta kod, ikki protokol

| Rejim | Nima |
|---|---|
| `SPEC` | Hujjatda yozilganidek, **aynan** — kamchiliklari bilan birga |
| `HARDENED` | Auditda topilgan 14 ta kamchilik tuzatilgan variant |
| `CUSTOM` | Har bir tuzatishni alohida yoqib/o'chirib tekshirish |

Hujum laboratoriyasi har bir ssenariyni **ikkala rejimda ham haqiqatan ishga
tushiradi**. Natijalar oldindan yozib qo'yilmagan.

```
hujum                                topilma  SPEC         HARDENED
--------------------------------------------------------------------
SPK kompromati -> to'liq sessiya     K-1      BROKEN       SAFE
INIT replay                          K-2      BROKEN       SAFE
Chain key kompromati -> o'tmish      K-3      BROKEN       SAFE
Ratchet sarlavhasini o'zgartirish    K-4      BROKEN       SAFE
KEM transkript bog'lanishi           Y-1      STRUCTURAL   SAFE
AEAD kalit-majburiyati               Y-2      STRUCTURAL   SAFE
Merkle ildiz noaniqligi              Y-3      STRUCTURAL   SAFE
Fayl metama'lumoti: nonce takrori    Y-4      BROKEN       SAFE
Kodlash chalkashligi                 Y-5      STRUCTURAL   SAFE
SPK muddatini almashtirish           Y-6      BROKEN       SAFE
Fingerprint beqarorligi              Y-7      BROKEN       SAFE
Bekor qilish rollback'i              Y-8      BROKEN       SAFE
Skipped-key DoS                      O-3      N/A          SAFE
Metama'lumot oqishi                  O-8      INFO         INFO
Envelope bit-flip (nazorat)          —        SAFE         SAFE
Xabar replay (nazorat)               —        SAFE         SAFE
S-FILE tamper/truncation (nazorat)   —        SAFE         SAFE
--------------------------------------------------------------------
SPEC rejimida buzilgan: 8/17
```

---

## O'rnatish va ishga tushirish

```bash
pip install -r requirements.txt
```

```bash
python run.py
```

```bash
python run.py --tests
```

```bash
python -m scutum.kat
```

```bash
python run.py --attacks
```

---

## GUI panellari

| Panel | Nima ko'rsatadi |
|---|---|
| **Umumiy ko'rinish** | SCUTUM-Q1 profili, rejim tanlash, 14 ta tuzatish bayrog'i |
| **Qurilmalar** | DIK/SPK/OPK, Device Certificate, xavfsizlik raqami, rotatsiya |
| **S-MSG sessiya** | INIT → ACK → MSG jonli oqimi; o'rtada server nimani ko'rishi |
| **Ratchet holati** | RK / CKs / CKr / DH / PN / N, DH va PQ qadamlar hisobi |
| **S-FILE** | Bo'laklash, Merkle barglari, tamper/truncation/duplicate hujumlari |
| **Hujum laboratoriyasi** | 17 ssenariy, SPEC ⇄ HARDENED yonma-yon, dalillar bilan |
| **Paket inspektori** | Har Envelope: AAD maydonlari, ratchet sarlavhasi, hex dump |
| **Testlar** | Spec §10 chiqarish mezoni bo'yicha 33 ta test |

---

## Kriptografiya

Hech qanday algoritm qo'lda yozilmagan (spec §2 talabi):

| Vazifa | Manba |
|---|---|
| X25519, Ed25519, ChaCha20-Poly1305, HKDF-SHA-512, SHA-3-256 | `cryptography` (OpenSSL) |
| **ML-KEM-768** (FIPS 203), **ML-DSA-65** (FIPS 204) | `cryptography` (OpenSSL, constant-time) |
| Argon2id | `argon2-cffi` |
| Kanonik CBOR (RFC 8949 §4.2.1) | `cbor2` |

Tasdiqlangan o'lchamlar: ML-KEM pk 1184 B / ct 1088 B / ss 32 B,
ML-DSA pk 1952 B / sig 3309 B. INIT paketi ≈ 6.7 KiB, MSG ≈ 285 B.

---

## Loyiha tuzilishi

```
scutum/
  config.py            rejim va 14 ta audit bayrog'i
  crypto/
    primitives.py      barcha kripto primitivlar
    canonical.py       kanonik CBOR / JSON
  protocol/
    identity.py        DIK, SPK, OPK, DC, fingerprint       (spec §3)
    envelope.py        Envelope, AAD, nonce, qat'iy parser  (spec §4)
    handshake.py       INIT / ACK, RK0 derivatsiyasi        (spec §5)
    ratchet.py         Double Ratchet + PQ ratchet          (spec §6)
    session.py         S-MSG klient                         (spec §5–6)
    sfile.py           bo'laklash, manifest                 (spec §7)
    merkle.py          Merkle daraxti (2 rejim)             (spec §7.1)
    errors.py          yagona xato modeli                   (spec §10.1)
  sim/
    server.py          ishonchsiz server                    (spec §9)
    world.py           Alisa / Bobur / Mallory sahnasi
    attacks.py         17 hujum ssenariysi
    trace.py           voqealar shinasi
  gui/                 PySide6 dark GUI (8 panel)
  selftest.py          33 test (spec §10)
```

---

## Muhim implementatsiya qarorlari

Spec ba'zi joylarda ijro etib bo'lmaydigan darajada to'liq emas. Quyidagilar
simulyator tomonidan **qo'shilgan** va kodda shunday belgilangan:

1. **Ratchet sarlavhasi** (`dh`, `pn`, `n`) — spec §4 Envelope sxemasida yo'q,
   ularsiz Double Ratchet ishlamaydi (topilma K-4).
2. **`KDF_RK` ning konkret ta'rifi** — spec funksiyani e'lon qiladi, lekin
   ta'riflamaydi. Signal DR bilan mos ta'rif ishlatilgan.
3. **PQ ratchet DH ratchet qadamiga biriktirilgan** — spec §6.1 dagi mustaqil
   `RATCHET_PQ` xabari holat mashinasi jihatidan sinxron bo'la olmaydi
   (yuboruvchi o'z-o'zidan bajargan ratchet qadami qabul qiluvchida
   takrorlanmaydi). Bu — §6.1 ning ta'riflanmagan holat mashinasi
   muammosining amaliy isboti.
4. **`direction` bayti**, **`i` ning kodlanishi**, **INIT replay oynasi** —
   spec'da yo'q, bu yerda aniq belgilangan.
