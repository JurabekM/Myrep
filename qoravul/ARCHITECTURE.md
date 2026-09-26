# QORAVUL v0.1 — Arxitektura

> **Ogohlantirish (sintetik ma'lumot).** Ushbu hujjatdagi barcha ML natijalari
> (FPR, TPR, simulyatsiya) **sintetik** yuklama modeli va **qo'lda yozilgan**
> hujum signaturalari asosida o'lchangan. Haqiqiy hisoblagichlardan olingan
> ma'lumot ishlatilmagan. Real tarmoqda FPR/TPR boshqacha bo'ladi; pilot
> bosqichida qayta o'lchash shart. Barcha raqamlar `x86_64`, Python 3.11,
> pure-Python PQ backend'da o'lchangan (manba buyruqlari har bo'limda).
> Taxminiy qiymatlar **TAXMIN** deb belgilangan va formulasi berilgan.

## 1. Muammo

Aqlli elektr hisoblagichlar (230 V / 50 Hz, bir fazali) ikki muammoga duch keladi:

1. **Elektr o'g'irligi**: neytral orqali aylanib o'tish (bypass), magnit bilan tok
   transformatorini to'yintirish, kuchlanish kanalini buzish, chastota
   referensini soxtalashtirish, tunda noqonuniy katta yuklama (masalan, kripto-mayning).
2. **Aloqa xavfsizligi va hajmi**: hisoblagich 10–20 yil xizmat qiladi. Bugun
   yozib olingan trafik ertaga kvant kompyuter bilan ochilishi mumkin
   ("harvest now, decrypt later"). Har daqiqalik xom oqim esa NB-IoT/LTE-M
   kanalida qimmat.

QORAVUL yechimi: har daqiqalik o'lchov oynasi **qurilmaning o'zida** int8
autoenkoder + envelope bilan tahlil qilinadi; serverga faqat 15 daqiqalik
xulosa va **ML-DSA-65 bilan imzolangan dalil** yuboriladi; kanal gibrid
X25519 + ML-KEM-768 bilan himoyalangan.

## 2. Qatlamlar

```
 ┌──────────────────────── EDGE (hisoblagich MCU) ─────────────────────────┐
 │  ADC/metrologiya (ADE9153A)  →  1 daqiqalik oyna: V, I, I_n, PF, THD, f │
 │            │                                                            │
 │            ▼                                                            │
 │  8 xususiyat → qv_quantize (float32→int8, s_in = 8/127)                 │
 │            │                                                            │
 │            ▼                                                            │
 │  A: Envelope (per-feature [lo, hi])   B: AE 8-16-4-16-8 int8 → score     │
 │            └──────────── anomaly = A OR score > thr ─────┘              │
 │                                   │                                     │
 │  Incident FSM (4/6 ochadi, 30 toza oyna yopadi) ── ALERT (ML-DSA-65)    │
 │  Har 15 oyna: DATA SUMMARY                                              │
 │            │                                                            │
 │  QVL/1 record layer (ChaCha20-Poly1305, replay oynasi)                  │
 └────────────┼────────────────────────────────────────────────────────────┘
              │ TCP (NB-IoT / LTE-M)   1-RTT gibrid handshake
 ┌────────────▼──────────────── GATEWAY (server) ──────────────────────────┐
 │  asyncio Gateway: registry (node_id → ML-DSA pk), siyosat {HYBRID}       │
 │  ALERT → imzo + ev.node == session node tekshiruvi → EvidenceLedger      │
 │  EvidenceLedger: JSONL, hash_i = SHA256(prev ‖ canonical(record))        │
 └─────────────────────────────────────────────────────────────────────────┘
```

| Modul | Fayl |
|---|---|
| PQ abstraksiya (RLock bilan) | `qoravul/crypto/backend.py` |
| Framing, TLV-lite | `qoravul/protocol/wire.py` |
| Handshake | `qoravul/protocol/handshake.py` |
| Record layer, replay | `qoravul/protocol/session.py` |
| Sintetik hisoblagich + hujumlar | `qoravul/tinyml/meter.py` |
| AE, kvantlash, kalibrlash | `qoravul/tinyml/model.py` |
| C eksport | `qoravul/tinyml/export_c.py` |
| Edge node + FSM | `qoravul/edge/node.py` |
| Gateway + ledger | `qoravul/gateway/server.py` |
| Firmware (C99) | `firmware/qv_infer.[ch]`, `firmware/test_parity.c` |

## 3. QVL/1 protokoli

**Framing:** `u32 BE length ‖ frame`, `frame = ver(1)=1 ‖ type(1) ‖ body`;
body maydonlari `u16 len ‖ bytes`. `MAX_FRAME = 64 KiB`.
FrameType: HELLO=1, ACCEPT=2, DATA=3, ALERT=4, REJECT=5, CLOSE=6.
Suite: CLASSIC=1 (X25519), PQ_ONLY=2 (ML-KEM-768), HYBRID=3.

**Handshake (1-RTT, node boshlaydi):**

```
Node                                                        Gateway
HELLO [suite, node_id, Nn, X25519_pub, ML-KEM ek]
      + SIG_node("QVL1-HELLO" ‖ fields)          ───────►  registry → pk,
                                                           imzo → siyosat
          ◄───────  ACCEPT [Ng, X25519_pub, ML-KEM ct]
                    + SIG_gw("QVL1-ACCEPT" ‖ SHA384(HELLO) ‖ fields)
TH  = SHA384(HELLO ‖ ACCEPT)
OKM = HKDF-SHA384(ss_x ‖ ss_kem, salt=TH, info="QVL/1 traffic keys", L=72)
k_up = OKM[0:32], k_down = OKM[32:64], session_id = OKM[64:72]
```

* Gateway avval **imzoni** tekshiradi, keyin siyosatni: yo'lda suite baytini
  o'zgartirish `"bad signature"` bo'ladi, to'g'ri imzolangan past suite esa
  `"suite below policy"`.
* Node gateway ochiq kalitini **pin** qiladi (`"gateway signature invalid"`).
* Default siyosat: faqat `{HYBRID}` — X25519 yoki ML-KEM'dan biri buzilsa ham
  kalit xavfsiz qoladi.

**Record layer:** `body = sid(8) ‖ seq(u64 BE) ‖ ChaCha20-Poly1305 ct`,
`AAD = ver ‖ type ‖ sid ‖ seq`, `nonce = dir(4) ‖ seq(8)`, dir = `UP\0\0` / `DN\0\0`.
Replay: 64-bitli RFC 4303 bitmap; `seq = 0` rad etiladi; oyna faqat AEAD
tekshiruvidan **keyin** yangilanadi (soxta paket oynani siljita olmaydi).
`REKEY_AFTER = 2^20` yozuv.

**O'lchangan hajmlar** (`python -m bench.bench --runs 30`, 30 ta ishga tushirish
medianasi, 4 baytli uzunlik prefiksi bilan; host vaqtlari yugurishdan yugurishga ±20% o'zgaradi):

| Suite | HELLO, B | ACCEPT, B | Jami, B | Node, ms | Gateway, ms | Jami, ms |
|---|---|---|---|---|---|---|
| CLASSIC | 3408 | 3387 | 6795 | 43.2 | 42.2 | 85.5 |
| PQ_ONLY | 4560 | 4443 | 9003 | 53.5 | 51.7 | 105.2 |
| HYBRID | 4592 | 4475 | 9067 | 49.7 | 40.0 | 89.6 |
| RESUME (PSK, 3.1) | 126 | 108 | **234** | 0.07 | 0.10 | 0.16 |

**liboqs backend** (kengaytma 9.3; liboqs 0.16.0 faqat ML-KEM-768 + ML-DSA-65 bilan
manbadan build qilingan, `QORAVUL_PQ_BACKEND=liboqs python -m bench.bench --runs 30`):
HYBRID handshake jami **0.63 ms** (pure-Python'da 89.6 ms), CLASSIC 0.69 ms, PQ_ONLY 0.58 ms;
hajmlar bir xil. Interop: bir tomon liboqs, ikkinchisi pure-Python — ML-KEM, ML-DSA
(kontekst bilan) va to'liq HYBRID handshake ikki yo'nalishda ishlaydi
(`QORAVUL_TEST_LIBOQS=1 pytest tests/test_liboqs_interop.py` → 6/6). Butun test to'plami
liboqs backend bilan ham yashil. liboqs'ning "constant-time" xususiyatlari uchun liboqs
hujjatiga qarang; pure-Python backend constant-time **emas**.

* Record overhead: **34 B** (ver 1 + type 1 + sid 8 + seq 8 + tag 16) + 4 B uzunlik.
* MAC soni: har yozuvda **1** Poly1305 teg (16 B); handshake'da **2** ML-DSA-65
  imzo (node + gateway) va **2** tekshiruv.
* seal+open (100 B): 10.1 µs; ML-DSA-65 sign 28.0 ms, verify 6.9 ms (host, pure-Python).
* ALERT yozuvi: **3554 B** (dalil 205 B + xom imzo 3309 B). Imzo hex ko'rinishida
  JSON ichida bo'lsa ~6873 B bo'lardi (**TAXMIN**: `len(ev) + 2·3309 + 12 + 38`) — shuning
  uchun binary payload (saboq 7).

Handshake hajmining asosiy qismi — ML-DSA-65 imzolari (2 × 3309 B), ML-KEM-768
qo'shimchasi atigi +2272 B (ek 1184 + ct 1088).

### 3.1 PSK resumption (kengaytma 9.4)

To'liq handshake'dan keyin ikkala tomon qo'shimcha xabarsiz ticket chiqaradi:
`rms = HKDF(ikm, salt=TH, "QVL/1 resumption", 32)`, `ticket_id = HKDF(..., "QVL/1 ticket id", 16)`.
Keyingi ulanishda:

```
RESUME  = [ticket_id, Nn, X25519_pub] + HMAC-SHA384(rms, "QVL1-RESUME" ‖ fields)[:32]
RESUMED = [Ng, X25519_pub]            + HMAC-SHA384(rms, "QVL1-RESUMED" ‖ SHA384(RESUME) ‖ fields)[:32]
OKM     = HKDF-SHA384(rms ‖ ss_x, salt=SHA384(RESUME ‖ RESUMED), "QVL/1 resumed traffic keys", 72)
```

* Ticket **bir martalik**: MAC tekshirilgandan keyin o'chiriladi → qayta yuborilgan
  RESUME `"unknown ticket"`; soxta RESUME esa haqiqiy ticketni "yoqib" yubora olmaydi.
* Ticket o'zini chiqargan sessiya suite'ini eslaydi; u joriy siyosatda bo'lmasa
  `"suite below policy"` — resumption orqali siyosatdan pastga tushib bo'lmaydi.
* Yangi X25519 almashinuvi ticket keyinchalik oshkor bo'lsa ham o'tgan sessiyalarni
  himoya qiladi (forward secrecy); PQ mustahkamlik `rms` dan (gibrid handshake'dan) keladi.
* Muddati: 7 kun. Har resumed sessiya keyingi ticketni o'z transkriptidan chiqaradi.
* Hajm: **9067 B → 234 B** (−97.4%), vaqt ~0.16 ms (ML-DSA yo'q).

Sim, har node 4 soatda qayta ulanadi (30 node, 24 soat, 180 sessiya):

| Rejim | Handshake trafigi | Jami QORAVUL trafigi | Tejam (xom oqimga nisbatan) |
|---|---|---|---|
| Faqat to'liq handshake | 1 632 060 B | 2 026 748 B | 69.1% |
| PSK resumption (150/180 resumed) | 307 110 B | 701 798 B | 86.6% |

## 4. Xususiyatlar

| # | Nomi | Formula | Nimani ushlaydi |
|---|---|---|---|
| 0 | `v_dev` | V/230 − 1 | kuchlanish kanali buzilishi (sag) |
| 1 | `i_norm` | I/60 | yuklama darajasi (night_load) |
| 2 | `pf` | quvvat koeffitsiyenti | magnit, noodatiy yuklama |
| 3 | `thd` | harmonik buzilish | magnit (CT to'yinishi) |
| 4 | `f_dev` | f − 50 | chastota soxtalashtirish |
| 5 | `n_imb` | \|I − I_n\| / max(I, I_n, 0.1) | bypass (neytral orqali) |
| 6 | `h_sin` | sin(2π·soat/24) | kun vaqti |
| 7 | `h_cos` | cos(2π·soat/24) | kun vaqti |

**Normal model** (`meter.py`): tungi baza 1.2 A + ertalab 07:30 (3.0 A) +
kechqurun 20:00 (5.0 A) + kunduzgi cho'qqi 13:30 (1.8 A); `scale ~ U(0.6, 1.8)`,
`phase ~ N(0, 0.7)` soat; lognormal(0, 0.25) shovqin; 5% ehtimol bilan 4–9 A burst;
V = 231 + N(0, 1.8) − 0.15·I; PF va THD yuklamaga bog'liq; f ~ N(50, 0.03);
I_n = I·(1 + N(0, 0.008)).

**Hujumlar:** `bypass` (I_faza = I·U(0.2, 0.8)), `magnet` (I·U(0.3, 0.7),
THD U(0.28, 0.5), PF U(0.45, 0.65)), `sag` (V·U(0.70, 0.85)), `freq` (±U(0.6, 1.5) Hz),
`night_load` (01:00–05:00 da 25–45 A, PF U(0.95, 0.99)).

## 5. Model va kvantlash

**Autoenkoder** 8-16-4-16-8, ReLU yashirin, chiziqli chiqish, **428 parametr**.
Numpy Adam (lr 3e-3, kosinus pasayish, 40 epoch, batch 256), MSE,
standartlashtirilgan kirish (±8σ da kesilgan). Dataset: `meters=4096`,
`n_train=120000`, validatsiya 60 000 (saboq 3).

**Denoising (v0.1 da topilgan muhim tuzatish).** Oddiy AE night_load'ni
faqat seed omadiga ko'ra aniqlardi: 6 ta (ma'lumot + init) seed bo'yicha TPR
**16%…100%** (o'lchangan). Sabab: katta tok kechqurun normal; AE tungi katta
tokni "soat xususiyatlarini siljitib" tushuntirishi mumkin, soat
xususiyatlarining diapazoni esa atigi ±22 x_q — xato kichik chiqadi.
Barcha xususiyatlarga shovqin qo'shish ham yordam bermadi (16…100%).
Yechim: o'rgatishda **o'lchov xususiyatlariga σ = 1.5 shovqin, soatga esa
shovqin yo'q** (soat — toza takt). AE tokni "shu soat uchun ehtimolli"
qiymatga tortishga majbur bo'ladi. σ tanlov seedlari (0–7, alohida hujum
to'plami) bo'yicha barqaror bo'lgan eng kichik qiymat sifatida tanlandi;
yakuniy baho **boshqa** seedlarda:

| Seed | threshold | FPR, % | bypass | magnet | sag | freq | night_load |
|---|---|---|---|---|---|---|---|
| 0 | 3850 | 0.064 | 100 | 100 | 100 | 100 | 100 |
| 1 | 3727 | 0.112 | 100 | 100 | 100 | 100 | 100 |
| 2 | 3781 | 0.090 | 100 | 100 | 100 | 100 | 100 |
| 3 | 3644 | 0.071 | 100 | 100 | 100 | 100 | 100 |
| 4 | 5215 | 0.097 | 100 | 100 | 100 | 100 | 100 |
| 5 | 3471 | 0.090 | 100 | 100 | 100 | 100 | 100 |

**night_load sezgirligi** (seed 0 modeli, 01:00–05:00, har bin'da 4000 oyna):

| Tungi tok | 8–12 A | 12–16 A | 16–20 A | 20–25 A | 25–30 A | 30–45 A |
|---|---|---|---|---|---|---|
| TPR | 57.8% | 86.6% | 98.7% | 100% | 100% | 100% |

Ya'ni ~16 A dan past noqonuniy tungi yuklama ishonchli ushlanmaydi (normal
tungi burst 4–9 A bilan ustma-ust tushadi).

**Kvantlash** (simmetrik, zero-point 0):

* kirish: `x_q = clip(rint((x − mean)/std/s_in), −127, 127)`, `s_in = 8/127`
  (4/127 gauss dumlarini kesadi — saboq 2);
* og'irliklar: per-tensor int8, `s_w = max|W|/127`; bias int32 = `b/(s_x·s_w)`;
* requant: `M = s_x·s_w/s_y = M0·2^−sh`, `M0 ∈ [2^30, 2^31)`,
  `y = (acc·M0 + 2^(sh−1)) >> sh` (int64); `quantize_multiplier` nisbiy xatosi < 2^−30 (test);
* clamp: yashirin [0, 127], chiqish [−127, 127], chiqish shkalasi = `s_in`;
* faollashuv shkalasi: **har bir neyronning 99.9-persentilidan eng kattasi**.
  Birlashtirilgan (pooled) 99.9-persentil keng neyronlarni >0.1% oynada
  to'yintirdi va kvant threshold float'dagi 2485 o'rniga 28 836 ga chiqdi
  (o'lchangan) — bu tuzatildi.

**Detektor:** `score = Σ(x_q − y_q)²`; `threshold` = validatsiya ballarining
99.9-persentili; `feat_thresh[k]` = per-feature xatoning 99.9-persentili + 1;
envelope = per-feature x_q ning 0.002 / 99.998 persentili ± 12.
`anomaly = envelope buzildi OR score > threshold`. Culprit: birinchi buzilgan
envelope, aks holda `argmax(err/feat_thresh)` (C da uint64 kesishgan
ko'paytirish, teng bo'lsa birinchi indeks).

**Joriy model** (`python -m qoravul.tinyml.train`, seed 0): threshold 3850,
FPR **0.064%** (100 000 ta ko'rilmagan normal oyna; envelope 0.001%, score 0.064%),
barcha 5 hujum TPR **100%** (har biri 5000 oyna). O'rgatish 4.9 s.

**Firmware:**

| O'lchov | Qiymat | Manba |
|---|---|---|
| Host parity | **500/500 bit-exact** (`-Wall -Wextra -Werror -pedantic`) | `make -C firmware test` |
| Cortex-M33 parity (QEMU mps2-an505, FPv5 hard-float) | **500/500 bit-exact** | `make -C firmware qemu-m33` |
| Kod + konstantalar (M33, `-Os`) | **1444 B** `.text`, 0 B `.data/.bss` | `make -C firmware size-m33` |
| int8 MAC / oyna | 384 | `bench.bench` |
| Host vaqti | 323 ns/oyna | `make -C firmware bench` |
| M33 instruksiyalar (QEMU icount proxy) | ~4305 instr/oyna (`-O2`) | `make -C firmware qemu-bench-m33` |
| STM32U5 @160 MHz da vaqt | **TAXMIN** 27–40 µs: `4305 · CPI / 160e6`, CPI ∈ [1.0, 1.5] | — |

**PQ on-MCU** (kengaytma 9.2, batafsil: [`firmware/BENCHMARKS.md`](firmware/BENCHMARKS.md)):
mlkem-native / mldsa-native Cortex-M33 (QEMU) da, KAT Python referensi bilan
bayt-ma-bayt mos. Instruksiyalar (stack peak): ML-KEM-768 keypair 0.99 M (13.8 KB),
encaps 1.10 M (16.9 KB), decaps 1.34 M (18.1 KB); ML-DSA-65 keypair 3.64 M (49.4 KB),
sign 4.61 M (72.9 KB), verify 3.57 M (45.0 KB). Node HYBRID handshake ≈ 10.5 M
instruksiya → **TAXMIN** 66–98 ms @160 MHz (`10.5e6 · CPI / 160e6`, CPI 1.0–1.5).

QEMU DWT_CYCCNT ni modellamaydi, shuning uchun haqiqiy cycle soni faqat
apparatda o'lchanadi (yo'l xaritasi, 11-bo'lim). Heap yo'q; ma'lumot buferlari stekda ~72 B (**TAXMIN**: `2·16 + 8 + 8·4` bayt, registr saqlashlarisiz; aniq stack peak apparatda stack painting bilan o'lchanadi).

## 6. Incident FSM

```
            ≥4 of last 6 windows anomalous
  NORMAL ─────────────────────────────────────► INCIDENT  (bitta ALERT)
     ▲                                              │
     └──────────── 30 ketma-ket toza oyna ◄─────────┘
```

* 4/6 debounce + 99.9-persentil (saboq 4). O'lchangan: **2000 ta halol
  hisoblagich × 24 soat = 2 880 000 oyna → oyna FPR 0.070%, soxta incident 0**
  (`python -m bench.bench --fleet-meters 2000`).
* Har 15 oynada `DATA SUMMARY {w, kwh, vmin, vmax, pf, smax, nflag, inc}` (90 B JSON, 128 B simda).
* ALERT payload: `u16 len ‖ kanonik JSON dalil ‖ xom ML-DSA-65 imzo`;
  dalil = `{node, window, hour, score, culprit, features[8], model_thr}`,
  imzo konteksti `"QVL1-EVIDENCE"`, JSON `sort_keys` + `(",", ":")`.

## 7. Evidence ledger

Gateway ALERT'ni qabul qilganda: (1) node pk bilan imzo, kontekst
`QVL1-EVIDENCE`; (2) `evidence.node == session node` (boshqa node nomidan
dalil yuborib bo'lmaydi); (3) `EvidenceLedger` ga yoziladi:

```
record = {node, evidence (aynan qabul qilingan JSON), sig (hex)}
hash_i = SHA256(prev_hash ‖ canonical(record)),  genesis = "0"×64
```

JSONL fayl; `verify_chain()` har qanday o'zgartirish yoki o'chirishni aniqlaydi.
Ledger yozuvi **rad etib bo'lmaydigan** (non-repudiation): node ochiq kalitiga
ega har qanday uchinchi tomon (sud, regulyator) dalilni mustaqil tekshira oladi
(`verify_evidence`). Eslatma: ledger faylini to'liq qayta yozgan admin zanjirni
qaytadan hisoblay oladi — bunga qarshi `head` xeshini tashqi joyga (masalan,
regulyatorga) davriy e'lon qilish kerak (keyingi qadamlar).

## 8. Tahdid modeli

| Hujum | Himoya | Test |
|---|---|---|
| Kvant hujumchi trafikni yozib oladi (HNDL) | ML-KEM-768 + X25519 gibrid, HKDF-SHA384 | `test_hybrid_roundtrip_both_directions` |
| Suite'ni CLASSIC'ga tushirish (downgrade) | Siyosat `{HYBRID}` | `test_classic_downgrade_rejected`, `test_pq_only_rejected_by_default_policy` |
| Yo'lda suite baytini o'zgartirish | HELLO imzosi, imzo siyosatdan oldin tekshiriladi | `test_suite_byte_tamper_is_bad_signature` |
| Ro'yxatda yo'q qurilma | Registry | `test_unknown_node_rejected` |
| Soxta gateway (MITM) | Gateway kalitini pin qilish, ACCEPT imzosi HELLO xeshiga bog'langan | `test_rogue_gateway_detected` |
| Yozuvni qayta yuborish (replay) | 64-bit oyna, AEAD dan keyin yangilanadi | `test_replay_rejected`, `test_replay_window_unit` |
| Tarmoqdagi tartib buzilishi | Oyna ichida out-of-order qabul | `test_out_of_order_within_window_ok` |
| Yozuvni o'zgartirish | Poly1305; soxta yozuv oynani siljitmaydi | `test_tamper_rejected` |
| DATA → ALERT tur almashtirish | type AAD ichida | `test_type_confusion_data_to_alert` |
| Yozuvni yuboruvchiga qaytarish (reflection) | Yo'nalishga xos kalit + nonce | `test_reflection_rejected` |
| Boshqa sessiya yozuvini qo'yish | session_id AAD da | `test_wrong_session_id_rejected` |
| RESUME'ni qayta yuborish | Bir martalik ticket | `test_resume_replay_rejected` |
| RESUME'ni o'zgartirish | HMAC; soxta xabar ticketni yoqmaydi | `test_resume_tamper_rejected` |
| Eski (CLASSIC) ticket orqali downgrade | Ticket suite'i joriy siyosat bilan tekshiriladi | `test_resume_cannot_downgrade_policy` |
| Eskirgan ticket | 7 kunlik muddat | `test_resume_expired_ticket` |
| Soxta gateway resumption'da | RESUMED MAC `rms` bilan, RESUME xeshiga bog'langan | `test_resume_rogue_gateway` |
| Nonce tugashi | `REKEY_AFTER = 2^20` | `test_rekey_limit` |
| Buzilgan freymlar / DoS | Uzunlik, versiya, tur tekshiruvlari; REJECT, crash yo'q | `test_malformed_frames`, `test_garbage_hello_is_reject_not_crash` |
| Neytral orqali aylanib o'tish | Envelope (`n_imb`) | `test_attack_tpr[bypass]`, `test_culprit_points_at_tampered_feature[bypass-n_imb]` |
| Magnit bilan CT to'yintirish | Envelope (`thd`, `pf`) + AE | `test_attack_tpr[magnet]` |
| Kuchlanish kanalini buzish | Envelope (`v_dev`) | `test_attack_tpr[sag]` |
| Chastota soxtalashtirish | Envelope (`f_dev`) | `test_attack_tpr[freq]` |
| Tungi noqonuniy yuklama | Soat-toza denoising AE | `test_attack_tpr[night_load]`, `test_night_load_robust_to_training_seed` |
| Soxta alertlar bilan operatorni charchatish | 99.9-pers. + 4/6 debounce | `test_fpr_on_unseen_households`, `test_incident_fsm_debounce` |
| Node dalildan tonishi | ML-DSA-65 imzo ledger'da | `test_evidence_non_repudiation` |
| Node boshqa node nomidan dalil yuborishi | `ev.node == session node` | `test_gateway_rejects_bad_or_foreign_evidence` |
| Ledger'ni o'zgartirish / yozuvni o'chirish | Xesh zanjiri | `test_ledger_chain_and_tamper` |
| Firmware va Python modelining farqlanishi | 500 golden vektor, bit-exact | `test_c_parity_bit_exact`, `test_c_parity_on_cortex_m33_qemu` |

**Qamrovdan tashqarida (v0.1):** yon kanal hujumlari (pure-Python PQ
**constant-time emas**), MCU'dan kalitni jismoniy o'g'irlash (secure element /
TrustZone kerak), hisoblagichga soxta o'lchov oqimini to'liq sintez qilib
berish (mimicry), gateway'ning o'zi buzilishi.

## 9. Simulyatsiya natijalari

Haqiqiy localhost TCP ulanishlari, har node alohida ML-DSA kaliti va to'liq
HYBRID handshake bilan.

`python -m qoravul.sim.run --nodes 30 --thieves 6 --hours 24`:

| Ko'rsatkich | Qiymat |
|---|---|
| Oynalar | 43 200 |
| Aniqlangan o'g'rilar | **6/6** (bypass ×2, freq, magnet, night_load, sag) |
| Aniqlash vaqti | har biri 3 daqiqa (4-anomal oyna) |
| Soxta alertlar | **0** |
| Ledger | 6 yozuv, zanjir **butun** |
| Trafik: QORAVUL | 660 998 B (≈22.0 KB/node/kun) |
| Trafik: xom oqim | 5 183 179 B (≈172.8 KB/node/kun) |
| Ikkalasida handshake | 272 010 B (9067 B/node) |
| **Tejam** | **87.2%** |
| Devor vaqti | 15.6 s |

Seed 1–5 da ham 6/6, 0 soxta, tejam 87.3%.

`test_e2e_fleet` (8 node / 3 o'g'ri / 6 soat): **3/3**, 0 soxta, tejam **72.9%**.
Qisqa sessiyada tejam past, chunki 9 KB handshake ikkala tomonda ham bor va
umumiy hajmda katta ulush egallaydi (saboq 8).

**Xom oqim bazasi ta'rifi:** har daqiqada bitta QVL/1 DATA yozuvi, payload —
kanonik JSON `{t, v, i, in, pf, thd, f}` (~76 B) + 38 B overhead, **plyus** o'sha
HYBRID handshake. Ya'ni solishtirish bir xil kriptografik kanal ustida.

Qayta ulanish bilan (PSK resumption): `test_e2e_fleet_with_resumption`
(4 node, 3 soat, har soatda qayta ulanish → 12 sessiya, 8 tasi resumed) va 3.1-bo'limdagi jadval.

Oylik trafik (**TAXMIN**, chiziqli ekstrapolyatsiya): `22 033 B × 30 ≈ 0.66 MB/node/oy`
(QORAVUL) va `172 773 B × 30 ≈ 5.2 MB/node/oy` (xom). Har kuni qayta ulanish
bo'lsa handshake har kun qo'shiladi: to'liq 9067 B yoki PSK resumption bilan 234 B (3.1-bo'lim).

> **Ogohlantirish.** Hujum signaturalari model yaratuvchisi tomonidan
> yozilgan; detektor ularni osonlikcha ajratadigan joylarga (envelope)
> tushadi. Haqiqiy o'g'rilar kichik va sekin (masalan, 10% under-reading)
> hujum qiladi — bular v0.1 da o'lchanmagan va ehtimol ushlanmaydi.

## 10. Apparat yo'l xaritasi

1. **Renode STM32U5** — `nucleo_u575zi_q` Zephyr ilovasi 500 vektorni UART'ga
   chiqaradi, `.resc` + `.robot` bilan `parity: 500/500` avtomatik test.
   *v0.1 holati:* Renode o'rnatilmagan; o'rniga eng yaqin Cortex-M33 platforma —
   QEMU `mps2-an505` da detektor parity 500/500, ML-KEM-768/ML-DSA-65 KAT,
   instruksiya soni va stack peak o'lchandi (`firmware/BENCHMARKS.md`).
2. **NUCLEO-U575ZI-Q + ADE9153A** — haqiqiy metrologiya (V, I, I_n, PF, THD, f),
   DWT_CYCCNT bilan cycle o'lchovi, stack painting, energiya iste'moli;
   ML-KEM-768 / ML-DSA-65 on-MCU (mlkem-native / mldsa-native yoki PQClean M4).
   Kalitlar TrustZone secure tomonida.
3. **nRF9151 yoki Quectel BG95** — NB-IoT/LTE-M uplink; handshake hajmi
   (9 KB) va PSK resumption'ning haqiqiy efir vaqti va energiyasi.
4. **Pilot** — 50–100 ta hisoblagich, haqiqiy yuklama profillari bilan qayta
   o'rgatish, FPR/TPR ni real ma'lumotda o'lchash, energetika kompaniyasi bilan
   dalil formatini huquqiy jihatdan kelishish.

## 11. Keyingi qadamlar

* Haqiqiy cycle soni: NUCLEO-U575 da DWT_CYCCNT; pqm4 (M4 assembler) bilan solishtirish.
* Ledger `head` xeshini tashqi joyga davriy e'lon qilish (anchoring).
* Real ma'lumotda qayta o'rgatish; sekin/kichik o'g'irlik hujumlarini modellash;
  per-meter kalibrlash (uy xo'jaligi profili drift'i).
* Model yangilanishi uchun imzolangan OTA (model versiyasi dalilga kiritiladi).
* PyQt6 dashboard (ledger, incidentlar, kWh grafigi, uz/en).
