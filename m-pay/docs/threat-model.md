# M-Pay Pay Sandbox — tahdid modeli (STRIDE)

> Holat: **M4**. "Holat" ustunidagi M1–M4 nazoratlari amalga oshirilgan va testlangan
> (`docs/PROGRESS.md`); M6/M7 belgilari — ochiq.

## 1. Qamrov

Qamrovda: `mpay-server` (barcha ichki modullar), PQ Link kanali, Wallet SDK (HCE) va
terminal ilovasi orasidagi APDU almashinuvi, sandbox ma'lumotlar bazasi, KeyStore.

Qamrovdan tashqari (0-faza): real to'lov tarmoqlari, real kartalar, bankning ichki tizimlari,
fizik HSM sertifikatsiyasi.

## 2. Aktivlar

| # | Aktiv | Maxfiylik | Yaxlitlik |
|---|---|---|---|
| A1 | IMK-AC, KEK, PAN-IDX kalitlari (HSM ichida) | kritik | kritik |
| A2 | FPAN (test bo'lsa ham real kabi muomala) | yuqori | yuqori |
| A3 | DPAN, token ↔ FPAN bog'lanishi | yuqori | kritik |
| A4 | LUK'lar (qurilmada va uzatishda) | yuqori | yuqori |
| A5 | Server imzo kalitlari (Ed25519, ML-DSA-65) | kritik | kritik |
| A6 | Qurilma P-256 kaliti (StrongBox) | yuqori | yuqori |
| A7 | Audit log | o'rta | kritik |
| A8 | Test hisob qoldiqlari (emitent emulyatori) | past | yuqori |

## 3. Ishonch chegaralari

```
 [Telefon: HCE ilova] ──NFC──► [Terminal] ──HTTPS──► [mpay-server] ──► [KeyStore/HSM]
        │                                               │
        └──────── PQ Link (HTTPS ichida) ───────────────┘──► [SQLite]
```

TB1: NFC havo interfeysi (ishonchsiz). TB2: Internet/LAN (ishonchsiz). TB3: server ↔ HSM.
TB4: server ↔ DB (DB ishonchsiz deb qaraladi — faqat shifrmatn).

## 4. STRIDE tahlili

| ID | Kategoriya | Tahdid | Nazorat | Holat |
|---|---|---|---|---|
| S1 | Spoofing | Soxta server qurilmaga LUK beradi | Gibrid imzo Ed25519 **va** ML-DSA-65, server kaliti build vaqtida pinlangan (P1.5); kalit almashtirish faqat joriy kalit tasdig'i bilan (P1.6, ADR-0012); oshkor bo'lgan kalit — oflayn ildiz imzolagan bekor qilish ro'yxati (ADR-0014) | M2/P1.5/P1.6 |
| S2 | Spoofing | Emulyator/rootlangan qurilma o'zini haqiqiy deb ko'rsatadi; eski (root'dan oldingi) attestatsiyani qayta ishlatadi | Android Key Attestation zanjiri, xavfsizlik darajasi siyosati; yangi qurilma challenge'i — server nonce'i, qurilmalar reyestri (P1.7, ADR-0013); Play Integrity (stub) | M2/M6/P1.7 |
| S3 | Spoofing | Soxta terminal yoki operator API'ga murojaat (o'g'irlangan kalit) | Rol bo'yicha Bearer kalitlari (SHA-256 xesh, constant-time solishtirish) + mTLS: sertifikat CN'i kalit ID'siga teng (ADR-0011) | M3/P1.3 |
| S4 | Spoofing | Ko'chirilgan token boshqa qurilmada ishlatiladi | Token qurilmaga bog'langan; LUK faqat bog'langan qurilma sessiyasida to'ldiriladi | M3 |
| T1 | Tampering | Summa/valyuta APDU yoki ISO 8583 da o'zgartiriladi | ARQC CDOL ichida summa/valyuta/UN; issuer maydon 4/49 ni 9F02/5F2A bilan solishtiradi | M4 |
| T2 | Tampering | PQ Link yozuvlari o'zgartiriladi | ChaCha20-Poly1305 AEAD, AAD = sessiya ID ‖ seq ‖ yo'nalish | M2 |
| T3 | Tampering | Audit log tahrirlanadi | Append-only trigger'lar + xesh-zanjir, `audit verify` | M3 |
| T4 | Tampering | Parserlarga zararli kirish (TLV, ISO 8583, PQ Link) | Chegaralari tekshirilgan parserlar, proptest + cargo-fuzz | M1/M2/M7 |
| R1 | Repudiation | Operator tokenni to'xtatganini inkor etadi | Audit yozuvi: aktor ID, harakat, vaqt, zanjir xeshi | M3 |
| I1 | Info disclosure | PAN/LUK/kalit logga tushadi | `Pan` tipi faqat maskalangan `Debug`/`Display`; sir tiplarida `Debug` yo'q; e2e log-skaner testi | M1/M4 |
| I2 | Info disclosure | DB o'g'irlanadi | PAN/DPAN AES-256-GCM (DEK), DEK KEK bilan o'ralgan, KEK HSM'da; HMAC indeks | M3 |
| I3 | Info disclosure | "Hozir yig', keyin buz" (kvant) | PQ Link gibrid KEM X25519 + ML-KEM-768 | M2 |
| I4 | Info disclosure | Vaqt bo'yicha yon kanal (kriptogramma/kalit solishtirish) | `subtle` constant-time solishtirish | M1 |
| I5 | Info disclosure | Xotirada qolgan sirlar | `Zeroizing<>`, ML-KEM kalitlari efemer va ishlatilgach tozalanadi | M1/M2 |
| D1 | DoS | Noto'g'ri kriptogramma bilan LUK hisoblagichini "yoqish" | LUK foydalanishi faqat ARQC muvaffaqiyatli tekshirilgandan keyin hisoblanadi | M4 |
| D2 | DoS | Handshake toshqini (ML-KEM/ML-DSA qimmat) | Sessiyalar soni va TTL; bir vaqtdagi handshake'lar semafori (503), IP / API kaliti / qurilma bo'yicha token bucket (429 + Retry-After) | M2/P1.1 |
| E1 | Elevation | Terminal kaliti bilan detokenizatsiya | Detokenizatsiya HTTP'da ochilmagan; faqat issuer moduliga beriladigan port | M3 |
| E2 | Elevation | Muddati o'tgan/to'xtatilgan token bilan to'lov | Issuer token holatini va LUK TTL/limitini har tranzaksiyada tekshiradi | M4 |
| E3 | Elevation | Takroriy (replay) tranzaksiya | ATC token bo'yicha qat'iy o'sishi shart; UN terminal tomonidan tasodifiy | M4 |
| E4 | Tampering | Terminal STAN'ini boshqa tranzaksiya uchun qayta ishlatish; timeout'dan keyingi qayta yuborish noto'g'ri `Q1` beradi | Acquirer `(terminal, STAN, sana)` jadvali: bir xil so'rov — avvalgi javob, boshqa mazmun — `94` (ADR-0010) | P1.2 |

## 5. Qoldiq risklar (sandbox uchun qabul qilingan)

* `memory` KeyStore — dev-urug'dan deterministik kalitlar; faqat sandbox (config'da `sandbox = true`
  bo'lmasa server ishga tushmaydi).
* `MK_tok` HSM'dan tashqarida (dastur xotirasida) hosil qilinadi va darhol tozalanadi.
  Production'da: HSM ichida `CKM_*_DERIVE` yoki to'lov HSM (`TODO(spec):`).
* LUK'lar PQ Link sessiya kaliti bilan shifrlanib uzatiladi, lekin server xotirasida ochiq
  holda paydo bo'ladi.
* OTP-simulyatsiya sandbox endpoint orqali o'qiladi (`sandbox.expose_otp`).
