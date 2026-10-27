# ADR-0024: Avtomatik reversal (`0400`) va solishtirish (reconciliation)

* Holat: qabul qilingan (2026-10-27, production checklist JM-2, JM-3).
* Bog'liq: ADR-0007 (javob kodlari), ADR-0010 (takroriy so'rovlar), ADR-0018 (PostgreSQL),
  ADR-0019 (ko'p instansiya).

## Kontekst

Avtorizatsiya ikki joyda yoziladi: acquirer (terminal ko'rgan javob) va emitent (pul yechilgani).
Ular uch holatda ajralib qolardi — emitent pul yechgan, terminal esa `96` ko'rsatgan:

1. emitent javobni kechiktirdi yoki javob yo'qoldi (tarmoq);
2. `0110` ni o'qib bo'lmadi;
3. jarayon emitent ishlaganidan keyin, javobni saqlashdan oldin to'xtadi (yozuv `PENDING` da qotadi).

ADR-0010 bunday so'rovni qayta yubormaydi (ATC replay bo'lardi) va `96` saqlaydi, lekin pul
qaytmasdi. Mijoz to'lovni takrorlasa — ikki marta to'laydi. Ikki tomonni taqqoslaydigan vosita ham
yo'q edi.

## Qaror

### 1. ISO 8583 profili (M-Pay Test Scheme)

* MTI `0400` — reversal, `0401` — takror (birinchisiga javob kelmagan), `0410` — javob.
* Maydonlar: 3, 4, 7 (reversal vaqti), 11 (asl STAN), 37 (asl RRN), 41, 42, 49 va **90** — asl ma'lumot
  (`0100` ‖ STAN(6) ‖ asl maydon 7(10) ‖ acquirer ID(11) ‖ forwarding ID(11), sandbox'da nollar;
  ikkilamchi bitmap).
* **Maydon 2 (PAN) yo'q:** acquirer karta raqamini saqlamaydi. Emitent asl yozuvni
  `(terminal, STAN, RRN, merchant)` bo'yicha topadi, summa va valyuta mos kelishi shart.
  `TODO(spec):` haqiqiy sxemaning reversal formati va muassasa identifikatorlari.

### 2. Emitent (`mpay-issuer/src/reversal.rs`)

| Holat | `0410` maydon 39 | Sabab |
|---|---|---|
| tasdiqlangan, qaytarilmagan | `00` | `REVERSED` — summa o'sha hisobga qaytadi |
| avval qaytarilgan | `00` | `ALREADY_REVERSED` |
| asl rad etilgan | `00` | `NOTHING_TO_REVERSE` |
| topilmadi | `25` | `ORIGINAL_NOT_FOUND` — emitent `0100` ni ko'rmagan |
| bir nechta mos yozuv | `25` | `AMBIGUOUS_ORIGINAL` — avtomatik qaytarilmaydi |
| summa/valyuta farqli | `13` | `AMOUNT_MISMATCH` |
| yechilgan hisob yozilmagan (eski yozuv) | `96` | `ACCOUNT_UNKNOWN` |
| maydon yo'q, maydon 90 noto'g'ri | `30` | `FORMAT_ERROR` |

* Avtorizatsiya qatoriga endi yechilgan hisob (`account_id`) yoziladi — qaytarish shu hisobga.
* Qaytarish va belgi bitta tranzaksiyada: `UPDATE … SET reversed_at WHERE reversed_at IS NULL`
  faqat bitta xabarda o'tadi. Parallel `0400`/`0401` pulni ikki marta qaytarmaydi.
* Har reversal xabari `issuer_reversals` ga yoziladi (migratsiya `2003`).
* Sandbox: `[issuer] response_delay_ms` — `0110` ni commit'dan keyin kechiktiradi (timeout yo'lini
  sinash uchun).

### 3. Acquirer (`mpay-server/src/reversal.rs`)

* Emitent chaqiruvi `[acquirer] issuer_timeout_ms` (standart 10 s) bilan cheklangan.
* Natija noma'lum bo'lsa — `ISSUER_TIMEOUT`, `ISSUER_RESPONSE_UNREADABLE` yoki `OUTCOME_UNKNOWN`.
  **Bitta tranzaksiyada** takroriy so'rov yozuvi `96` bilan yopiladi va `acquirer_reversals` ga navbat
  yozuvi qo'shiladi. Kalit takroriy so'rov kaliti bilan bir xil, shuning uchun ikkinchi marta
  qo'shilmaydi. Terminal qayta yuborsa — o'sha `96`.
* `acquirer_requests` acquirer jurnali ham bo'ldi (migratsiya `3005`): RRN, terminal, merchant,
  summa, valyuta, maskalangan DPAN, uzatish vaqti va yakuniy javob kodi. PAN yo'q.
* Fon ishchisi har instansiyada (`[acquirer] reversal_interval_ms`, standart 5 s) ikki ish qiladi:
  * qotgan `PENDING` larni (`> 120 s`, terminal qayta yubormagan) topib yopadi;
  * vaqti kelgan reversal'larni yuboradi.
* Yozuv shartli `UPDATE` (`attempts` versiya sifatida) bilan band qilinadi, shuning uchun bitta
  reversal'ni bir vaqtda ikki instansiya yubormaydi. Baribir yuborilsa, emitent tomoni idempotent.
* Birinchi xabar `0400`, keyingilari `0401`.
  * `00`/`25` → `DONE`.
  * Boshqa kod → `FAILED` (qo'lda ko'rib chiqish).
  * Emitentga yetib bo'lmasa → 5 s, 10 s, 20 s … `reversal_max_backoff_secs` (600 s) oralig'ida
    muddatsiz qayta urinish.
* Birinchi `0400` `reversal_delay_secs` (standart 10 s) dan keyin yuboriladi. Tarmoqda kechikkan asl
  `0100` emitentga reversal'dan oldin yetsin: aks holda reversal `25` oladi, keyin kelgan asl esa
  tasdiqlanadi. Bu qoldiq holatni solishtirish `ISSUER_ONLY_APPROVED` sifatida ko'rsatadi.
  `TODO(spec):` sxema qoidasi — emitent kechikkan aslni reversal'dan keyin rad etadimi.
* `DONE` yozuvlar 35 kun saqlanadi, `FAILED` — o'chirilmaydi.
* Metrikalar:
  * `mpay_reversals_enqueued_total{cause}`, `mpay_reversals_total{result}`;
  * `mpay_reversals{state="pending"|"failed"}`, `mpay_reversal_oldest_pending_seconds` — DB'dan,
    klaster bo'yicha.
* Ogohlantirishlar: `MpayReversalFailed` (critical), `MpayReversalBacklog` (15 daqiqadan eski).

### 4. Solishtirish (`mpay-server/src/recon.rs`)

* Acquirer jurnali ↔ emitent qaydnomasi, kalit `(terminal, STAN, RRN)`. Ikki tomon davr chetida
  `MARGIN_SECS` (300 s) kengroq o'qiladi.
* Tafovutlar:
  * `ISSUER_ONLY_APPROVED` — mijozdan pul ketgan, tovar berilmagan;
  * `ACQUIRER_ONLY_APPROVED` — savdo nuqtasiga pul tushmaydi;
  * `AMOUNT_MISMATCH`;
  * `REVERSAL_FAILED`.
* Izohlar (vaqtinchalik): `REVERSAL_PENDING`, `IN_FLIGHT`.
* Mos kelganlar valyuta bo'yicha jami beriladi.
* Davr — sxema vaqti bo'yicha kun (UTC+5, ADR-0022) yoki `from`/`to`. Eng ko'pi 7 kun.
  Acquirer jurnali saqlanish muddatidan (3 kun) eski davr rad etiladi.
* Kirish:
  * `GET /v1/recon?date=YYYY-MM-DD` (operator);
  * `mpay-server recon --date … [--out report.json]` — tafovut bo'lsa chiqish kodi 1, cron va
    navbatchi uchun.
* Hisobotda PAN yo'q, faqat maskalangan DPAN.
* Emitent tomoni hozir jarayon ichidagi emulyatordan (`Issuer::report`) olinadi.
  `TODO(spec):` real bankda — bankning kunlik fayli; `reconcile()` sof funksiya, manbadan mustaqil.

## Oqibatlar

* Natijasi noma'lum avtorizatsiyada mijozning puli avtomatik qaytadi. Sinovda: timeout, emitent
  vaqtincha ishlamaganda qayta urinishlar va jarayon to'xtagan holat.
* Terminal uchun hech narsa o'zgarmaydi: `96` → kassir mijozdan qayta tap so'raydi (yangi ATC, yangi
  STAN).
* Avtorizatsiyaga bitta qo'shimcha DB amali yo'q: jurnal ustunlari takroriy so'rov yozuviga mavjud
  `INSERT`/`UPDATE` bilan yoziladi.
* Kliring/settlement hali yo'q (JM-1): solishtirish avtorizatsiya darajasida, pul o'tkazmasi bilan emas.
* Uzoq muddatli jurnal yo'q: acquirer jurnali 3 kun. Kunlik solishtirish shu oyna ichida o'tkaziladi;
  kliring bilan birga doimiy jurnal kerak bo'ladi.
* Tekshirilgan:
  * `mpay-common`: maydon 90 va ikkilamchi bitmap.
  * Emitent (`iso_flow`): qaytarish bir marta, `25`/`13`/`30`, `0401` takror, rad etilgan asl,
    parallel ikki reversal.
  * Server unit: `settle_unknown` bitta navbat yozuvi bilan; `0400` → `0401`; kutish oralig'i;
    solishtirishning barcha turlari; UTC+5 kun.
  * E2e `p3_reversal`, SQLite va PostgreSQL:
    * timeout → `96` → emitent ishlamaguncha qayta urinishlar (`REVERSAL_PENDING` izohi) → `0401`
      bilan qaytarish, balans tiklandi, terminal qayta yuborsa o'sha `96`;
    * qotgan yozuv → ishchi yopadi va qaytaradi;
    * solishtirish uchala tafovutni topadi;
    * API'ga kirish huquqi va davr xatolari tekshirildi.
  * Ishchi o'chirilganda ikkala reversal e2e testi yiqildi.

## Ko'rib chiqilgan muqobillar

* **Javob kelmasa `0100` ni qayta yuborish:** ATC replay (`Q1`) va ikki marta yechish xavfi —
  ADR-0010 da rad etilgan.
* **Reversal'ni darhol, so'rov ichida yuborish:** emitent ishlamayotgan bo'lsa ham terminal kutib
  qoladi. Qayta urinish va instansiya yiqilishiga chidamlilik baribir fon navbatini talab qiladi.
* **Maydon 2 bilan reversal (DPAN'ni navbatda saqlash):** karta raqami yana bir jadvalda (shifrlash,
  PCI doirasi kengayadi). RRN/STAN/terminal aniqlash uchun yetarli.
* **Emitent "topilmadi" (`25`) javobini qayta urinish:** kechikkan asl uchun foydali bo'lishi mumkin,
  lekin cheksiz navbat hosil qiladi. O'rniga — birinchi yuborishdan oldin kutish va solishtirish.
