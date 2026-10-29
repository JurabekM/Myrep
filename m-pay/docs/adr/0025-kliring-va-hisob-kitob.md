# ADR-0025: Kunlik kliring va hisob-kitob (settlement)

* Holat: qabul qilingan (2026-10-27, production checklist JM-1).
* Bog'liq: ADR-0024 (reversal va solishtirish, acquirer jurnali), ADR-0022 (sxema vaqti UTC+5).

## Kontekst

Avtorizatsiya pulni faqat **ruxsat etadi**. Savdo nuqtasiga pul tushishi uchun quyidagilar kerak:

* kun oxirida tasdiqlangan tranzaksiyalarni emitentga taqdim etish — kliring;
* kim kimga qancha to'lashini hisoblash — hisob-kitob (settlement).

M-Pay'da bularning hech biri yo'q edi. Acquirer jurnali esa 3 kun saqlanadi (ADR-0024).

## Qaror

### 1. Kliring fayli formati (`mpay-common/src/clearing.rs`)

O'zimizning M-Pay Test Scheme formati v1 — haqiqiy sxema formati emas, kodek almashtiriladi.
`TODO(spec):` sxemaning kliring formati.

* Qat'iy uzunlikli ASCII qatorlar:
  * `H` — sarlavha;
  * `D` — har tranzaksiya: terminal, merchant, STAN, RRN, summa, valyuta, vaqt, **maskalangan** DPAN;
  * `S` — valyuta bo'yicha soni va jami;
  * `T` — yozuvlar soni va oldingi baytlarning SHA-256 xeshi.
* Emitent tasdig'i (ack): `A` sarlavha, har yozuvga `R` (kod va sabab), `Z` (soni va xesh).
* Tahlil qat'iy: uzunliklar, tartib raqamlari, nazorat yig'indilari va xesh tekshiriladi. Ochiq PAN
  faylga tushmaydi (`*` siz DPAN — xato).
* Emitent yozuvni reversal kabi `(terminal, STAN, RRN, merchant)` bo'yicha topadi.

### 2. Emitent (`mpay-issuer/src/clearing.rs`)

| Holat | Kod | Sabab |
|---|---|---|
| tasdiqlangan, qaytarilmagan, kliringga kirmagan | `00` | `ACCEPTED` |
| topilmadi / bir nechta mos | `25` | `ORIGINAL_NOT_FOUND` / `AMBIGUOUS_ORIGINAL` |
| summa yoki valyuta farqli | `13` | `AMOUNT_MISMATCH` |
| asl rad etilgan / qaytarilgan | `12` | `NOT_APPROVED` / `REVERSED` |
| boshqa paketda kliringdan o'tgan | `94` | `ALREADY_CLEARED` |

* Qabul qilingan avtorizatsiyaga paket ID'si yoziladi (`cleared_batch`). Shartli `UPDATE` — bitta
  tranzaksiya ikki paketda o'tmaydi.
* Bir paket ID — bitta natija: o'sha fayl qayta kelsa saqlangan tasdiq qaytadi; o'sha ID boshqa
  mazmun bilan — butun paket rad etiladi.
* Kliringdan o'tgan tranzaksiyaga reversal kelsa — `12 ALREADY_CLEARED`. U endi yakuniy, faqat
  qaytarish (refund) bilan qaytariladi.
* Emulyator pulni avtorizatsiyada yechadi (bitta xabarli model), shuning uchun kliring balansni
  o'zgartirmaydi. `TODO(spec):` sxemaga qarab — avtorizatsiyada blok (hold), kliringda yechim (post).

### 3. Acquirer (`mpay-server/src/clearing.rs`)

Bir kun (sxema vaqti, UTC+5) — bitta paket (`MPAY` + `YYYYMMDD`), uch bosqich. Har bosqich shartli
`UPDATE` bilan o'tadi, shuning uchun to'xtagan joydan xavfsiz davom ettiriladi.

1. **`BUILT`** — paket yaratiladi:
   * kun ichida acquirer `00` bergan (terminal tovar bergan) yozuvlar paketga nusxalanadi;
   * `clearing_items` doimiy saqlanadi — acquirer jurnalidan farqli;
   * `96` va rad etilganlar paketga kirmaydi;
   * shartlar: kun tugagach `[clearing] cutoff_grace_secs` (standart 900 s) o'tgan, kun ichida javobi
     noma'lum (`PENDING`) yozuv yo'q, kun jurnal saqlanish muddati (3 kun) ichida;
   * aks holda `409 CLEARING_NOT_READY` yoki `400`.
2. **`ACKED`** — fayl emitentga yuboriladi. Tasdiq o'z formatida qayta tekshiriladi va har yozuv
   holati saqlanadi: `ACCEPTED` yoki `REJECTED` + sabab.
3. **`SETTLED`** — faqat qabul qilinganlar bo'yicha pozitsiyalar (`settlement_positions`):
   * `MERCHANT` (savdo nuqtasi × valyuta): yalpi, MDR (`merchant_fee_bps`, standart 1,5 %),
     to'lanadigan;
   * `ISSUER`: yalpi − interchange (`interchange_bps`, standart 1,0 %) — emitent acquirer'ga to'laydi;
   * `ACQUIRER` (M-Pay): MDR − interchange;
   * har valyutada tekshiriladi: `ISSUER.net = Σ MERCHANT.net + ACQUIRER.net`;
   * komissiya savdo nuqtasi/valyuta jamisidan olinadi, butun tiyingacha yarmidan yuqoriga
     yaxlitlanadi;
   * paketda ishlatilgan tariflar saqlanadi.
   * `TODO(spec):` haqiqiy tariflar (savdo nuqtasi toifasi, karta turi), emitentlar BIN/bank
     bo'yicha, savdo nuqtasi reyestri va bank rekvizitlari.

Kirish (faqat operator):

* `POST /v1/clearing/run {"date"}` (standart — kecha);
* `GET /v1/clearing/{date}`;
* `GET /v1/clearing/{date}/clearing.txt | ack.txt | payouts.csv`;
* CLI `mpay-server clearing [--date] [--out-dir]` — rad etilgan yozuv bo'lsa chiqish kodi 1 (cron).

### 4. Solishtirish (ADR-0024 ga qo'shimcha)

* Har qatorda `clearing` maydoni: `ACCEPTED`, `REJECTED:<sabab>` yoki `PENDING`.
* Yangi tafovut — `CLEARING_REJECTED`: ikki tomon tasdiqlagan, lekin emitent kliringda rad etgan,
  ya'ni savdo nuqtasiga to'lanmaydi.
* Hisobotda `cleared` — kliringda qabul qilinganlar soni.

## Oqibatlar

* Kunning to'lovlari bitta buyruq bilan emitentga taqdim etiladi. Pozitsiyalar va to'lovlar ro'yxati
  tayyorlanadi; ularni bankka o'tkazish — bank jarayoni.
* Kliring yozuvlari doimiy saqlanadi: kunlar o'tgach ham hisobot va fayl qayta olinadi.
* Kliringni kun tugagach 3 kun ichida o'tkazish shart (acquirer jurnali). Kechiksa — `400`, qo'lda.
* Qaytarish (refund), nizolar (chargeback) va qayta taqdim etish hali yo'q (JM-10). Rad etilgan
  yozuvlar hisobotda qoladi va qo'lda hal qilinadi.
* Fayl bazada saqlanadi (sandbox hajmi uchun). `TODO(spec):` production'da fayl almashinuvi kanali
  (SFTP/API) va arxiv.
* Tekshirilgan:
  * kodek: format, tartib, xesh, nazorat yig'indilari, ochiq PAN rad, proptest;
  * emitent: barcha natija turlari, takroriy paket, boshqa mazmunli o'sha ID, `94`, kliringdan
    keyingi reversal;
  * server unit: komissiya yaxlitlash, pozitsiyalar muvozanati, bir nechta valyuta;
  * e2e `p3_clearing` (SQLite va PostgreSQL):
    * kun tugamaguncha `409`;
    * 3 yozuv → 2 qabul, 1 rad (`NOT_APPROVED`), pozitsiyalar aniq raqamlar bilan;
    * qayta ishga tushirish o'sha natijani beradi;
    * fayllar o'z formatida o'qiladi, PAN yo'q, CSV mazmuni tekshirildi;
    * solishtirish `ACQUIRER_ONLY_APPROVED` → `CLEARING_REJECTED`;
    * kirish huquqi va kiritish xatolari.
  * Paketga rad etilganlar ham tushadigan qilib kod ataylab buzilganda e2e yiqildi.
  * Haqiqiy binar: `init` → `clearing --out-dir` (bo'sh kun), takror, bugungi kun rad.

## Ko'rib chiqilgan muqobillar

* **Kliringni har tranzaksiyada (real vaqtda):** bitta xabarli tizimlarda shunday. Lekin kunlik
  paket bank amaliyotiga yaqin va hisob-kitobni bitta nuqtada beradi.
* **Pozitsiyalarni har tranzaksiya komissiyasidan yig'ish:** yaxlitlash qoldiqlari tranzaksiyalar
  soniga qarab o'sadi. Savdo nuqtasi jamisidan bitta yaxlitlash oddiyroq va tekshiriladi.
* **Paketni avtomatik fon ishchisi bilan yaratish:** ko'p instansiyada yetakchi tanlash kerak bo'ladi.
  Cron bilan bitta buyruq, idempotent bosqichlar va chiqish kodi oddiyroq.
* **Faylni JSON'da:** o'qish oson, lekin real sxema fayllari qat'iy uzunlikli. Kodek almashinuvini
  shu yo'l bilan oldindan sinaymiz.
