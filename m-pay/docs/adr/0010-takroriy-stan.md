# ADR-0010: Takroriy avtorizatsiya so'rovlari (STAN) — idempotentlik va `94`

* Holat: qabul qilingan (2026-10-24, 1-faza P1.2)

## Kontekst

Terminal javobni ololmasa (tarmoq uzilishi, timeout) xuddi shu so'rovni qayta yuboradi. 0-fazada
emitent bunday qayta yuborishni ATC replay sifatida `Q1` bilan rad etardi: pul birinchi so'rovda
yechilgan, terminal esa "rad etildi" ko'rsatadi — mijoz qayta to'laydi. Bundan tashqari bir terminal
STAN'ini boshqa tranzaksiya uchun qayta ishlatish aniqlanmasdi.

## Qaror

1. Acquirer `acquirer_requests` jadvalida `(terminal_id, stan, UTC sana)` kaliti bilan so'rov
   mazmuni xeshini (terminal, merchant, STAN, `icc_data`) va javobni saqlaydi (3 kun).
2. Aynan bir xil so'rov — saqlangan javob qaytariladi, emitentga ikkinchi marta yuborilmaydi.
3. Shu kalit boshqa mazmun bilan — ISO `94` (takroriy uzatish), emitentga yuborilmaydi.
4. Birinchi so'rov hali ishlanayotgan bo'lsa — `409 REQUEST_IN_PROGRESS` + `Retry-After: 1`.
5. Emitentga yetib bo'lmasa (`502`) — yozuv o'chiriladi, terminal shu STAN bilan qayta urinishi mumkin.
6. `mpay-tsim` STAN hisoblagichi hamyondan terminalga ko'chirildi (`<sandbox>/tsim-terminal-<id>.stan`).

## Oqibatlar

* Timeout'dan keyingi qayta yuborish xavfsiz: bir xil javob, bitta yechim (`tests/e2e/tests/p1_duplicate_stan.rs`).
* Har avtorizatsiyaga 2 ta qo'shimcha commit (PENDING va DONE): yuk sinovida 238 → ~172 so'rov/s
  (bitta SQLite yozuvchisi, har commit fsync). 2-fazada PostgreSQL va avtorizatsiyani bitta
  tranzaksiyada yozish bilan qaytariladi (ADR-0009).
* Sana UTC bo'yicha: yarim tunda kesishgan qayta yuborish yangi so'rov hisoblanadi — emitent uni ATC
  replay sifatida `Q1` bilan rad etadi (ikki marta yechilmaydi, xavfsiz tomonga xato).

## Ko'rib chiqilgan muqobillar

* **Xotirada kesh** — tezroq, lekin server qayta ishga tushsa yo'qoladi va ko'p instansiyada ishlamaydi.
* **Faqat emitentdagi ATC himoyasi** — pulni himoya qiladi, lekin terminalga noto'g'ri `Q1` beradi.
* **Takroriy STAN'ni 409 xato bilan rad etish** — terminal kernel'lari avtorizatsiya javobini kutadi;
  ISO `94` standart ma'noga ega.
