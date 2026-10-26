# Yuk sinovi hisoboti (M7)

Sana: 2026-10-24. Qayta yugurish: `bash scripts/load-test.sh [KARTA] [PARALLEL] [SONIYA] [engine|stub] [full|normal]`.

## 1. Usul

* **Server**: release `mpay-server` alohida jarayonda, oddiy HTTP (keep-alive), `RUST_LOG=warn`,
  KeyStore `memory` (HSM kechikishi kirmaydi — §5), SQLite WAL, `synchronous = FULL`.
* **Generator** (`mpay-load`, `tests/e2e/src/bin/mpay_load.rs`):
  1. `prepare` — `mpay.toml` ga 200 ta fiktiv hisob (`99001277…`, Luhn) va LUK limiti 1 000 000
     (faqat yuk konfiguratsiyasi; bir kartada uzoq yuklama uchun).
  2. Provisioning — har karta alohida soft-qurilma (sandbox CA attestatsiyasi), to'liq PQ Link
     handshake + `POST /v1/tokens` (YELLOW bo'lsa sandbox OTP).
  3. Avtorizatsiya — C ta ishchi, har biri o'z kartalari to'plami: soft-karta haqiqiy GPO/ARQC
     hisoblaydi → `POST /v1/authorizations` (terminal kaliti). Kechikish — HTTP so'rov boshidan javobgacha.
* **Mashina**: Intel i5-10300H (4 yadro / 8 oqim), 24 GB RAM, NVMe SSD, Windows 10; generator va
  server bir mashinada (CPU ni bo'lishadi).

## 2. Natijalar (yakuniy, 60 s, 200 karta)

| Stsenariy | So'rovlar | O'tkazuvchanlik | p50 | p95 | p99 | max | Xato | Javob kodlari |
|---|---|---|---|---|---|---|---|---|
| Shield dvigateli, 32 parallel | 14 313 | **238 /s** | 131 ms | 146 ms | **155 ms** | 377 ms | 0 | `00` 1 200, `59` 13 113 |
| Shield stub, 32 parallel | 12 868 | 214 /s | 148 ms | 157 ms | 160 ms | 174 ms | 0 | `00` 12 868 |
| Shield dvigateli, 8 parallel | 13 106 | 218 /s | 36 ms | 43 ms | **46 ms** | 51 ms | 0 | `00` 1 200, `59` 11 906 |

Provisioning (200 karta, PQ Link handshake + ID&V + Vault): 630–670 karta/s, p99 25 ms (8 parallel)
— 100 ms (32 parallel), hammasi GREEN, xato 0. Server logida ochiq PAN yo'q (skript tekshiradi).

**`59` ko'pligi — kutilgan xatti-harakat**: har karta sekundiga ~1 marta tap qilinadi; Shield
tezlik qoidalari har kartada 6 ta tasdiqdan keyin karta testlash/tezlik namunasi sifatida rad etadi.
Rad etilgan so'rov ham to'liq yo'ldan o'tadi (ISO 8583, ARQC tekshiruvi, Shield, audit) — o'lchov
uchun teng og'irlikda. Faqat tasdiq yo'li (balans yechish bilan) — stub qatori.

## 3. Topilgan va tuzatilgan muammolar

1. **DB xatosi `91 ISSUER_OFFLINE` sifatida** (birinchi yugurish: 14 708 so'rovdan 1 036 tasi `91`,
   loglarda `DB_ERROR`). Sabab: WAL rejimida oddiy (deferred) tranzaksiya avval o'qib, keyin yozishga
   o'tganda boshqa yozuvchi bo'lsa SQLite `busy_timeout` ni kutmasdan `SQLITE_BUSY` qaytaradi.
   Tuzatish: barcha Vault yozuvchi tranzaksiyalari `BEGIN IMMEDIATE` (`mpay_vault::db::begin_write`).
2. **Yozish qulfi uchun "uxlab kutish"**: tuzatishdan keyin xato yo'qoldi, lekin 8 ulanishli hovuzda
   p99 1 046 ms, 83 so'rov/s. SQLite busy-handler qulfni uxlab-uyg'onib kutadi (Windows'da taymer
   donadorligi ~15 ms). Hovuz 1 ulanishga tushirilganda navbat jarayon ichida (tokio) bo'ladi:
   **p99 1 046 → 155 ms, 83 → 238 so'rov/s**, xato 0. ADR-0009.
3. `synchronous = NORMAL` (8 ulanish bilan) faqat 83 → 111 so'rov/s berdi — fsync asosiy cheklov emas;
   standart `FULL` qoldirildi (`[database] synchronous` sozlamasi o'lchov uchun bor).

| O'zgarish | O'tkazuvchanlik | p99 | Xato |
|---|---|---|---|
| Boshlang'ich (deferred, 8 ulanish) | 244 /s | 938 ms | 1 036 × `91` (7 %) |
| `BEGIN IMMEDIATE`, 8 ulanish | 83 /s | 1 046 ms | 0 |
| `BEGIN IMMEDIATE`, 8 ulanish, `NORMAL` | 111 /s | 778 ms | 0 |
| `BEGIN IMMEDIATE`, **1 ulanish** (yakuniy) | **238 /s** | **155 ms** | 0 |

(Boshlang'ich qatorning yuqori o'tkazuvchanligi xatolar tez qaytgani hisobiga.)

## 4. Tahlil

* O'tkazuvchanlik ~220–240 so'rov/s da to'xtaydi va parallellikka bog'liq emas (8 va 32 bir xil):
  bitta SQLite yozuvchisi, bir avtorizatsiyaga ~4,2 ms ketma-ket ish (bir nechta commit: LUK
  qaydi, detokenizatsiya/ATC, emitent jurnali, balans, audit). 32 parallelda kechikish deyarli
  butunlay navbat: 32 / 238 ≈ 134 ms ≈ p50 (Little qonuni).
* Shield dvigateli stub'ga nisbatan sezilarli qo'shimcha bermaydi (M5: p99 1,94 ms).
* Sandbox maqsadi (bank demo, pilot) uchun yetarli; production hajmi uchun quyidagi ishlar kerak.

## 5. Cheklovlar va keyingi qadamlar

* `TODO(spec):` production DB (PostgreSQL yoki bir avtorizatsiyani bitta tranzaksiyada yozish);
  bank kutayotgan TPS va kechikish SLA talablari.
* HSM (PKCS#11) kechikishi o'lchanmagan — `memory` KeyStore. SoftHSM bilan alohida o'lchash kerak
  (har avtorizatsiyada KDF/CMAC chaqiruvlari).
* TLS o'chiq (sandbox HTTP); TLS handshake keep-alive tufayli faqat ulanish boshida.
* Generator server bilan bir mashinada — natija pastki chegara sifatida qaralsin.

## 6. 1-faza ta'siri (2026-10-24)

P1.1 (rate-limit) va P1.2 (takroriy STAN jadvali, ADR-0010) qo'shilgandan keyin, o'sha usul
(200 karta, 60 s, Shield dvigateli, `synchronous = FULL`):

| Stsenariy | O'tkazuvchanlik | p50 | p99 | Xato |
|---|---|---|---|---|
| 32 parallel | 171–175 /s | 183–191 ms | 201–212 ms | 0 |
| 8 parallel | 171 /s | 45 ms | 58 ms | 0 |

Pasayish (238 → ~172, −27 %) — har avtorizatsiyaga ikkita qo'shimcha commit (PENDING va DONE).
Yuk generatori bitta IP'dan ishlagani uchun IP chegarasini ko'taradi va handshake `503 BUSY` da
`Retry-After` bilan qayta urinadi (provisioning xatosiz). 2-fazada qaytariladi (ADR-0009, ADR-0010).

## 7. HSM bilan yuk sinovi — 2-faza P2.2 (2026-10-26)

Qayta yugurish: `bash scripts/softhsm-load.sh [KARTA] [PARALLEL] [SONIYA] [SESSIYALAR]`
(`MPAY_LOAD_ONLY=memory|hsm`, `MPAY_LOAD_SYNC=full|normal`). Natijalar `docs/load/p2.2-*.json`.

**Usul.** Hammasi bitta Docker konteynerida (Linux, 8 yadro, `rust:1.97.1-bookworm`), server va
generator birga; release `mpay-server --features pkcs11`, SoftHSM 2.6.1, token har yugurishda yangi.
KeyStore `pkcs11` da barcha kalit operatsiyalari HSM ichida: LUK hosil qilish (CMAC), ARQC, envelope
(GCM), PAN indeksi (HMAC), PQ Link handshake imzosi (Ed25519). So'rovlar chegarasi o'chirilgan
(generator bitta terminal kaliti bilan ishlaydi — 500/s kalit chegarasi production'dagi ko'p
terminallarni aks ettirmaydi). 200 karta, 32 parallel, 60 s, Shield dvigateli.

| Stsenariy | SQLite | Avtorizatsiya | p50 | p95 | p99 | Provisioning | Xato |
|---|---|---|---|---|---|---|---|
| memory | FULL | 105 /s | 304 ms | 324 ms | 351 ms | 161 /s | 0 |
| SoftHSM, 1 sessiya | FULL | 102 /s | 313 ms | 333 ms | 364 ms | 136 /s | 0 |
| SoftHSM, 4 sessiya | FULL | 101 /s | 315 ms | 335 ms | 368 ms | 135 /s | 0 |
| memory | NORMAL | **524 /s** | 57 ms | 72 ms | **88 ms** | 391 /s | 0 |
| SoftHSM, 1 sessiya | NORMAL | 483 /s | 61 ms | 80 ms | 87 ms | 355 /s | 0 |
| SoftHSM, 4 sessiya | NORMAL | **492 /s** | 60 ms | 77 ms | **89 ms** | 368 /s | 0 |

Server loglarida ochiq PAN yo'q (skript tekshiradi).

**Topilgan va tuzatilgan (ADR-0017).**

1. **Har HSM operatsiyasida kalit qidiruvi.** Bitta CMAC = 5 ta PKCS#11 chaqiruvi (`C_FindObjects` ×3,
   `C_GetAttributeValue`, `C_Sign`). Kalit handle'lari keshlandi: SoftHSM'da 8 oqim CMAC **1 264 →
   17 941 op/s** (1 sessiya), yuk sinovida HSM qo'shimcha xarajati −21% → −3% (FULL).
2. **Bitta sessiya.** Pool (4 sessiya) kesh bilan CMAC'ni **32 591 op/s** ga yetkazdi (×1,8). Keshsiz
   pool SoftHSM'da hatto sekinroq edi (862 op/s) — SoftHSM ichida ketma-ket, sessiyalar raqobat
   qo'shadi. Tarmoq HSM'ida (round-trip) foyda kattaroq bo'lishi kutiladi — `TODO(spec):` pilot HSM'da.
3. **Uzilishdan tiklanmaslik.** Sessiya/login yo'qolsa qayta ochiladi va operatsiya takrorlanadi
   (`pkcs11_recovers_after_logout`).

**Tahlil — SLA (200 TPS, p99 < 300 ms).** HSM bilan SLA **hozir bajarilmaydi** (101 /s, p99 368 ms),
lekin to'siq HSM emas: `synchronous = NORMAL` (fsync'siz) da o'sha HSM yo'li 492 /s, p99 89 ms. Har
avtorizatsiya SQLite'ning yagona yozuvchisida bir nechta fsync'li commit qiladi (takroriy so'rov yozuvi,
LUK/ATC iste'moli, emitent yechimi + yozuvi, takroriy so'rov javobi). Bu 2-faza **P2.3** ning vazifasi:
PostgreSQL va avtorizatsiya bitta tranzaksiyada (bitta commit). Docker'dagi FULL raqamlari Windows'dagi
mahalliy o'lchovdan (§2, §6) past — konteyner fayl tizimida fsync qimmatroq; solishtirish faqat jadval
ichida.

## 8. PostgreSQL bilan yuk sinovi — 2-faza P2.3 (2026-10-26)

Qayta yugurish: `bash scripts/pg-load.sh [KARTA] [PARALLEL] [SONIYA] ["memory pkcs11"]`.
Natijalar `docs/load/p2.3-pg-*.json`.

**Usul.** §7 dagidek (Docker, 8 yadro, 200 karta, 32 parallel, 60 s, Shield dvigateli, so'rovlar
chegarasi o'chiq). Qo'shimchasi: alohida PostgreSQL 17 konteyneri o'sha Docker tarmog'ida, standart
sozlamada (fsync, `synchronous_commit = on` — to'liq chidamlilik). Server hovuzi 32 ulanish (ADR-0018).

| Ombor | KeyStore | Avtorizatsiya | p50 | p95 | p99 | max | Provisioning | Xato |
|---|---|---|---|---|---|---|---|---|
| SQLite (FULL, §7) | SoftHSM, 4 sessiya | 101 /s | 315 ms | 335 ms | 368 ms | 410 ms | 135 /s | 0 |
| **PostgreSQL** | memory | **377 /s** | 84 ms | 91 ms | **111 ms** | 139 ms | 234 /s | 0 |
| **PostgreSQL** | SoftHSM, 4 sessiya | **368 /s** | 85 ms | 109 ms | **118 ms** | 444 ms | 228 /s | 0 |

Server loglarida ochiq PAN va DB paroli yo'q (skript tekshiradi).

**Xulosa — SLA (200 /s, p99 < 300 ms) HSM bilan va to'liq chidamlilik bilan bajarildi**: 368 /s
(×1,8 zaxira), p99 118 ms. SQLite'ga nisbatan ×3,6: takroriy so'rov va emitent commit'lari endi
parallel va PostgreSQL ularning fsync'ini guruhlaydi. Yagona ketma-ket qism — audit zanjiri qulfi
ostidagi Vault commit'i (ADR-0018). Bu raqamlar bitta mashinadagi Docker'da (server, generator va
PostgreSQL bir xil 8 yadroni bo'lishadi); `TODO(spec):` pilot muhitida (alohida DB serveri, tarmoq HSM)
qayta o'lchash.

## 9. Ko'p instansiya — 2-faza P2.4 (2026-10-26)

Qayta yugurish: `bash scripts/multi-load.sh [KARTA] [PARALLEL] [SONIYA] [INSTANSIYALAR]`.
Natijalar `docs/load/p2.4-*.json`.

**Usul.** §8 dagidek (Docker, 8 yadro, PostgreSQL 17 standart sozlamada, 200 karta, 32 parallel, 60 s,
memory KeyStore, so'rovlar chegarasi o'chiq). Ikki stsenariy bitta konteynerda:

* **1 instansiya** — mahalliy Shield (taqqoslash).
* **2 instansiya + Shield roli** — `mpay-server shield` (yagona belgilar ombori) va ikkita
  `mpay-server serve` (`[shield] mode = "remote"`), bitta PostgreSQL va umumiy PQ Link sessiyalari.
  Generator har so'rovni navbatdagi instansiyaga yuboradi (round-robin). Har kartada nonce, hello va
  finish turli instansiyada, provisioning esa uchinchisida — sticky routing'dan qattiqroq sinov.

| Stsenariy | Avtorizatsiya | p50 | p95 | p99 | Provisioning (p99) | Xato | Zaxira (`SHIELD_DEGRADED`) |
|---|---|---|---|---|---|---|---|
| 1 instansiya | 421 /s | 76 ms | 87 ms | 94 ms | 220 /s (262 ms) | 0 | — |
| 2 instansiya + Shield roli | 384 /s | 82 ms | 93 ms | **113 ms** | 187 /s (283 ms) | 0 | **0** |

Shield roli oxirida: 200 karta, 200 qurilma, 32 savdo nuqtasi, 400 graf tuguni. Ikkala instansiya
hodisalari bitta omborda, qaror taqsimoti esa bitta instansiyadagidek: `00` 1 200, qolgani `59`
(tezlik qoidasi). Loglarda ochiq PAN, DB paroli va Shield kaliti yo'q (skript tekshiradi).

**Xulosa.** Ko'p instansiya to'g'ri ishlaydi: xato yo'q, sessiyalar instansiyalar orasida o'tadi,
Shield belgilari umumiy. SLA (200 /s, p99 < 300 ms) zaxira bilan bajariladi. Bitta mashinada ikki
instansiya bittadan biroz sekin: Shield'ga qo'shimcha ichki HTTP so'rov (~5 ms p50) bor va 8 yadroni
5 jarayon bo'lishadi. Gorizontal masshtabni (instansiyalar alohida mashinalarda) bu sinov o'lchamaydi —
`TODO(spec):` pilot muhitida.

## 10. docker-compose muhiti — 2-faza P2.5 (2026-10-26)

Qayta yugurish: `bash scripts/compose-test.sh [SONIYA] [PARALLEL]` (ADR-0020). Natija
`docs/load/p2.5-compose.json` (oxirgi yugurish).

**Usul.** Docker Desktop (Windows, 8 yadro), compose loyihasi `mpay-test`: PostgreSQL 17, SoftHSM
(PKCS#11, 8 sessiya), Shield roli (TLS + mTLS), `api-1` va `api-2`, nginx `stream` (L4, `least_conn`,
PROXY protocol), Prometheus. Yuk generatori alohida konteynerda va **faqat nginx orqali** ishlaydi:
TLS (server sertifikati pinlangan) va terminal mTLS — §9 dagi oddiy HTTP emas. 200 karta, 32 ishchi,
90 s, so'rovlar chegarasi o'chiq. 25-soniyada `docker compose stop api-1` (SIGTERM), keyin
`MpayInstanceDown` kutiladi va `api-1` qayta ishga tushiriladi.

| Yugurish | Avtorizatsiya | p50 | p95 | p99 | max | Provisioning (p99) | Xato |
|---|---|---|---|---|---|---|---|
| 1 | 275 /s | 105 ms | 174 ms | 282 ms | 1 641 ms | 65 /s (946 ms) | 0 |
| 2 | 355 /s | 87 ms | 111 ms | 136 ms | 260 ms | 123 /s (532 ms) | 0 |
| 3 | 332 /s | 91 ms | 127 ms | **164 ms** | 419 ms | 106 /s (741 ms) | **0** |

Barcha yugurishlarda:

* `api-1` to'xtatilganda **birorta so'rov yo'qolmadi** (xato 0): ochiq ulanishlar joriy so'rovni
  tugatib yopildi, generator qayta ulandi va nginx qolgan instansiyaga yo'naltirdi. To'xtash < 1 s.
* `MpayInstanceDown` 30 s dan keyin `firing`, `MpayApiCapacityReduced` `pending` holatiga o'tdi.
* nginx orqali kelgan sertifikat barmoq izi = API sertifikati (TLS end-to-end).
* `mpay_proxy_protocol_rejected_total` = 0, `mpay_shield_degraded_total` = 0, `mpay_db_up` = 1,
  Shield omborida 200 karta.
* Zaxira (`pg_dump` ~6 MB) → alohida bazaga tiklash → audit xesh-zanjiri to'g'ri (~30 000 yozuv).
* ~120 000 qator logda ochiq PAN va sirlar (DB paroli, HSM PIN'i, Shield kaliti, SMS tokeni) yo'q.

**Kuzatuvlar.**

* 1-yugurish sekinroq va dumi uzunroq (max 1,6 s): to'xtatish paytida 32 ulanish birdan qayta
  o'rnatildi (TLS + mTLS handshake). 2- va 3-yugurishlarda max 260–419 ms. Yugurishlar orasidagi farq
  Docker Desktop VM'idagi shovqin; SLA (200 /s, p99 < 300 ms) uchala yugurishda bajarildi.
* L4 balanslash **ulanish** bo'yicha: qayta ishga tushgan `api-1` keep-alive ulanishlar uzilmaguncha
  yangi yuk olmaydi (to'xtatishdan keyin 25 684 / 1 620 taqsimot). Real mijozlar (ko'p qisqa
  ulanishlar) uchun bu muammo emas; uzoq ulanishli terminal shlyuzlari uchun `TODO(spec):` ulanish
  umri chegarasi (`max_requests` yoki vaqt bo'yicha).
* Yuk ostida bitta instansiyada `MpayDbPoolExhausted` `pending` bo'ldi (32 ishchi, hovuz 32) — qoida
  to'g'ri ishlaydi; pilotda hovuz hajmi instansiya va ishchilar soniga qarab sozlanadi.
* §9 (384 /s, oddiy HTTP, bitta konteyner) bilan to'g'ridan-to'g'ri solishtirib bo'lmaydi: bu yerda
  TLS, nginx, Docker tarmog'i va SoftHSM qo'shilgan.
