# QORAVUL firmware benchmarklari (Cortex-M33, QEMU)

> **Muhim cheklov.** Barcha o'lchovlar **QEMU `mps2-an505`** (Cortex-M33,
> FPv5 hard-float) emulyatorida olingan. QEMU pipeline, kesh va wait-state'larni
> modellamaydi va DWT_CYCCNT ni qo'llab-quvvatlamaydi. Shuning uchun quyidagi
> "instr" — **bajarilgan instruksiyalar soni** (`-icount shift=0` + SysTick,
> 2·10⁶ instruksiyali sikl bilan kalibrlangan: 50 instr/tick), **cycle emas**.
> Haqiqiy cycle soni NUCLEO-U575ZI-Q da DWT_CYCCNT bilan o'lchanadi (yo'l xaritasi).

## 1. TinyML detektor (`qv_infer.c`)

| O'lchov | Qiymat | Buyruq |
|---|---|---|
| Parity (500 golden vektor) | **500/500 bit-exact** | `make qemu-m33` |
| Kod + konstantalar (`-Os`) | 1444 B `.text`, 0 B `.data/.bss` | `make size-m33` |
| Instruksiyalar / oyna (`-O2`) | ~4305 | `make qemu-bench-m33` |
| int8 MAC / oyna | 384 | `python -m bench.bench` |

## 2. PQ primitivlar on-MCU (kengaytma 9.2)

Manba: [mlkem-native](https://github.com/pq-code-package/mlkem-native) `b87425bd`,
[mldsa-native](https://github.com/pq-code-package/mldsa-native) `14d195a8` —
portable C backend (Armv8-M uchun maxsus assembler backend yo'q), monolit build,
deterministik API (`MLK/MLD_CONFIG_NO_RANDOMIZED_API`), `-O2 -mcpu=cortex-m33`.
Manbalar repo'ga kiritilmaydi — `make pq-fetch` pinned commit'larni yuklaydi.

**KAT:** MCU chiqishi Python referensi bilan bayt-ma-bayt solishtiriladi
(`QORAVUL_TEST_PQ_M33=1 pytest tests/test_pq_m33.py` → 3/3):
ML-KEM-768 `ek`, `ct`, `ss` = kyber-py `_keygen_internal(d, z)` / `_encaps_internal(ek, m)`;
ML-DSA-65 `pk` va deterministik imzo (`ctx = "QVL1-EVIDENCE"`) = dilithium-py.
MCU imzosi pure-Python backend'da `verify()` dan ham o'tadi.

`make pq-m33` natijasi:

| Amal | Instruksiyalar | Stack peak, B |
|---|---|---|
| ML-KEM-768 keypair | 988 250 | 13 784 |
| ML-KEM-768 encaps | 1 103 550 | 16 944 |
| ML-KEM-768 decaps | 1 342 850 | 18 080 |
| ML-DSA-65 keypair | 3 641 750 | 49 416 |
| ML-DSA-65 sign (1 ta xabar, rnd = 0) | 4 614 050 | 72 872 |
| ML-DSA-65 verify | 3 569 250 | 44 960 |

Stack peak — stack painting (0xA5 naqsh bilan 128 KiB bo'yalgan, keyin
birinchi o'zgargan so'z qidiriladi). Natija har yugurishda bir xil.
ML-DSA sign rejection sampling ishlatadi: instruksiya soni xabarga qarab
o'zgaradi, jadvalda **bitta** test xabar uchun qiymat.

Kod hajmi (`.text`, `arm-none-eabi-gcc 13.2`):

| Fayl | `-O2` | `-Os` |
|---|---|---|
| `mlkem_native.c` (ML-KEM-768 + FIPS 202) | 12 652 B | 9 688 B |
| `mldsa_native.c` (ML-DSA-65 + FIPS 202) | 19 812 B | 13 800 B |

## 3. Handshake narxi node'da (TAXMIN)

Node HYBRID handshake'da: ML-KEM keypair + decaps, ML-DSA sign (HELLO) +
verify (ACCEPT), X25519 (o'lchanmagan).

* Instruksiyalar: `988 250 + 1 342 850 + 4 614 050 + 3 569 250 ≈ 10.5·10⁶` (+ X25519).
* **TAXMIN** vaqt STM32U585 @160 MHz: `10.5·10⁶ · CPI / 160·10⁶`, CPI ∈ [1.0, 1.5] → **66–98 ms**.
* PSK resumption'da PQ amal yo'q (faqat HMAC-SHA384 + X25519).
* Har ALERT uchun bitta ML-DSA sign: **TAXMIN** `4.61·10⁶ · CPI / 160·10⁶` → 29–43 ms.
* RAM: eng og'ir amal ML-DSA-65 sign, ~73 KB stack. STM32U585 da 786 KB SRAM bor,
  lekin kichikroq MCU (masalan, 64 KB RAM) uchun mldsa-native'ning
  kam-xotirali rejimi yoki pqm4 `m4stack` varianti kerak bo'ladi.

## 4. Qayta ishlab chiqarish

```bash
sudo apt-get install gcc-arm-none-eabi libnewlib-arm-none-eabi qemu-system-arm
make -C firmware qemu-m33 qemu-bench-m33 pq-m33
QORAVUL_TEST_PQ_M33=1 pytest -q tests/test_pq_m33.py
```
