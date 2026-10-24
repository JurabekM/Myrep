# ADR-0009: SQLite — `BEGIN IMMEDIATE` va bitta ulanishli hovuz

* Holat: qabul qilingan (2026-10-24)

## Kontekst

M7 yuk sinovida (`docs/load-report.md`) parallel avtorizatsiyalarda Vault tranzaksiyalari
`SQLITE_BUSY` bilan yiqildi va emitent buni `91 ISSUER_OFFLINE` deb qaytardi (7 % so'rov).
WAL rejimida deferred tranzaksiya o'qishdan yozishga o'tganda boshqa yozuvchi bo'lsa SQLite
`busy_timeout` ni kutmaydi. `BEGIN IMMEDIATE` xatoni yo'qotdi, lekin 8 ulanish yozish qulfi uchun
SQLite busy-handler'ida uxlab kutdi: p99 ~1 s, 83 so'rov/s.

## Qaror

1. Vault'dagi barcha yozuvchi tranzaksiyalar — `mpay_vault::db::begin_write` (`BEGIN IMMEDIATE`).
2. Hovuz standarti — **1 ulanish** (`[database] max_connections`, standart 1): SQLite'da baribir bitta
   yozuvchi; navbat jarayon ichida (tokio) adolatli va uyg'onish kechikishisiz.
3. Qoida: tranzaksiya ochiq turganda hovuzdan boshqa so'rov qilinmaydi (bitta ulanishda o'z-o'zini
   kutish). Tayyorgarlik (DEK, DPAN generatsiya, shifrlash) tranzaksiyadan oldin, ichida faqat `&mut tx`.
4. `[database] synchronous = "full"` (standart) | `"normal"` — faqat o'lchov/sandbox uchun.

## Oqibatlar

* Yuk sinovi: p99 155 ms (32 parallel, navbat), 46 ms (8 parallel), 238 so'rov/s, xato 0.
* O'qishlar ham ketma-ket — sandbox hajmida sezilmaydi; o'tkazuvchanlik shifti ~240 so'rov/s.
* 3-qoida buzilsa deadlock (pool acquire timeout) — kod ko'rib chiqishda tekshiriladi.

## Ko'rib chiqilgan muqobillar

* **Alohida yozuvchi (1) va o'quvchi (N) hovuzlari** — yaxshiroq, lekin Vault/emitent kodida har
  so'rovni ajratish kerak; production DB tanlovi (`TODO(spec):` PostgreSQL) bilan birga qayta ko'riladi.
* **`synchronous = NORMAL`** — o'lchovda atigi +30 %, elektr uzilishida oxirgi commit'lar yo'qolishi
  mumkin; to'lov ma'lumoti uchun rad etildi.
