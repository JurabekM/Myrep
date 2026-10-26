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
