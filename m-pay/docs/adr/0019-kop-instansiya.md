# ADR-0019: Ko'p instansiya — umumiy sessiyalar, nonce'lar va Shield roli

* Holat: qabul qilingan (2026-10-26, 2-faza P2.4)

## Kontekst

P2.3 dan keyin bir nechta `mpay-server` bitta PostgreSQL'ni bo'lisha oladi, lekin uchta holat hali
jarayon xotirasida edi:

1. **PQ Link sessiyalari:** kalitlar, `seq` hisoblagichlari va yakunlanmagan handshake'lar. Handshake
   bir instansiyada boshlanib boshqasida tugay olmasdi. Qurilmani esa sticky routing'siz bitta
   instansiyaga bog'lab bo'lmaydi, chunki load balancer tanadagi sessiya ID'sini ko'rmaydi.
2. **Ro'yxatdan o'tish nonce'lari:** MAC kaliti jarayon ishga tushganda tasodifiy yaratilardi,
   ishlatilganlari ro'yxati xotirada edi.
3. **Shield belgilari:** karta, qurilma va savdo nuqtasi tezlik oynalari, qurilma–karta grafi.
   N ta instansiyada har biri hodisalarning faqat bir qismini ko'radi, natijada tezlik qoidalari
   N barobar zaiflashadi.

2026-10-25 qarori: umumiy ombor PostgreSQL, sessiya va nonce'lar KEK bilan shifrlanadi.
2026-10-26 qarori (foydalanuvchi): Shield — alohida rol.

## Qaror

1. **Sessiyalar.** `mpay-pqlink` da `SessionStore` (async) trait'i joriy etildi.
   * `MemorySessionStore` — bitta instansiya uchun.
   * `DbSessionStore` (`mpay-server`) — `pqlink_sessions` jadvali. Kalitlar KEK bilan AES-256-GCM'da
     shifrlanadi (HSM'da; AAD = yorliq ‖ holat ‖ sessiya ID).
   * `recv_seq` va `send_seq` atomar `UPDATE` bilan oshiriladi. Yakunlanmagan sessiya
     `DELETE … RETURNING` bilan olinadi: ikki instansiya bir xil ClientFinished'ni ololmaydi.
   * Shifri ochilgan kalitlar instansiya ichida keshlanadi, chunki ular o'zgarmaydi.
   * Handshake ikki bosqichli: kriptografiya `spawn_blocking` da, ombor async.
   * `[pqlink] session_store`: `auto` (PostgreSQL bo'lsa — DB), `memory` yoki `database`.
2. **Nonce'lar.**
   * MAC kaliti — KeyStore'dagi `mpay.enroll-nonce.v1` (HSM'da, barcha instansiyalarda bir xil).
   * Ishlatilganlari `pqlink_used_nonces` jadvalida saqlanadi (`INSERT … ON CONFLICT DO NOTHING`).
   * Nonce o'zi holatsizligicha qoladi (ADR-0013).
3. **Shield roli.** O'sha binar: `mpay-server shield --config …`.
   * Ichki API: `POST /internal/shield/idv` va `/internal/shield/txn`. Kirish uchun `shield` rolidagi
     API kaliti kerak, `require_mtls` bo'lsa mTLS ham. Autentifikatsiya tanani tahlil qilishdan oldin
     tekshiriladi.
   * DTO'larda ochiq PAN yo'q: faqat karta barmoq izi, qurilma ID, savdo nuqtasi, summa va vaqt.
   * API instansiyalarida `[shield] mode = "remote"` va `[shield.remote]` (`url`, `key_env`, ichki CA,
     mTLS identifikatori, `timeout_ms`) beriladi.
   * Shield javob bermasa, mahalliy dvigatel ishlaydi. Qaror chiqadi, lekin sababga `SHIELD_DEGRADED`
     qo'shiladi va ogohlantirish yoziladi.
4. **So'rovlar chegarasi.** Har instansiyada mahalliy qoladi. Handshake semafori CPU'ni himoya qiladi,
   CPU esa instansiya resursi. IP, kalit va qurilma chegaralari amalda `N × qiymat` bo'ladi, shuning
   uchun konfiguratsiyada jami chegara instansiyalar soniga bo'linadi. `TODO(spec):` load balancer
   darajasidagi global chegara (P2.5).

## Oqibatlar

* Istalgan instansiya istalgan so'rovni qabul qiladi: sticky routing kerak emas. Instansiya
  yiqilganda foydalanuvchi uzilmaydi va sessiya boshqa instansiyada davom etadi. Testda A to'xtatildi,
  B davom etdi.
* Muhrlangan so'rovga 4 ta DB amali qo'shiladi (2 ta o'qish, 2 ta atomar yangilash). Avtorizatsiya —
  asosiy yuklama — muhrlanmagan (terminal), shuning uchun unga ta'sir qilmaydi.
* Shield yagona nuqta. Uning yiqilishi to'lovni to'xtatmaydi, faqat aniqlashni zaiflashtiradi.
  `TODO(spec):` Shield holatini davriy saqlash va zaxira instansiya (pilot SLA bo'yicha).
* `max_sessions` va `max_pending` endi butun klaster bo'yicha hisoblanadi (umumiy jadval).
* Tekshirilgan (SQLite va PostgreSQL):
  * e2e `p2_multi_instance`: handshake A'dan B'ga o'tadi, sessiya A/B almashadi, A to'xtasa B'da
    davom etadi, nonce bir marta, takror instansiyalar orasida ham rad etiladi;
  * e2e `p2_shield_role`: qurilma fermasi qoidasi A/B orqali bitta instansiyadagidek ishlaydi,
    Shield'da bitta ombor (6 karta, 1 qurilma), kalitsiz kirish 401, Shield yiqilsa `SHIELD_DEGRADED`;
  * `enroll` unit: nonce A'da berilib B'da bir marta qabul qilinadi;
  * yuk sinovi: `docs/load-report.md` §9.

## Ko'rib chiqilgan muqobillar

* **Sticky routing:** load balancer PQ Link sessiya ID'sini ko'rmaydi (u tanada). Instansiya
  yiqilsa barcha sessiyalari yo'qoladi.
* **Shield belgilari PostgreSQL'da:** to'liq gorizontal masshtab beradi, lekin katta qayta yozish
  talab qiladi va har avtorizatsiyaga qo'shimcha yozuvlar keladi (foydalanuvchi bu variantni
  tanlamadi).
* **Redis:** 2026-10-25 qarori bilan rad etilgan (qo'shimcha infratuzilma).
