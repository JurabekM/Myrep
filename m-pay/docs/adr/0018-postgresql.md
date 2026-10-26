# ADR-0018: PostgreSQL — umumiy ombor, `sqlx::Any` va parallel tranzaksiyalar

* Holat: qabul qilingan (2026-10-26, 2-faza P2.3)

## Kontekst

P2.2 yuk sinovi to'siqni ko'rsatdi: avtorizatsiya SQLite'ning yagona yozuvchisida bir nechta
fsync'li commit qiladi. Bular takroriy so'rov yozuvi, LUK/ATC iste'moli, emitent yechimi va yozuvi,
takroriy so'rov javobi. HSM bilan natija 101 /s, p99 368 ms; fsync'siz esa 492 /s. Ko'p instansiya
(P2.4) uchun umumiy ombor ham kerak. 2026-10-25 qarori: PostgreSQL (Redis yo'q).

## Qaror

1. **`mpay-db` crate'i** — `sqlx::Any`. Dialekt URL bo'yicha tanlanadi: `sqlite:…` (sandbox, bitta
   instansiya) yoki `postgres://…`. Vault, emitent emulyatori va server bitta `Db` ni bo'lishadi.
2. **Bitta SQL ikkala dialekt uchun**:
   * parametrlar `$1, $2, …` birinchi uchrash tartibida — SQLite ularni nomli parametr deb o'qiydi;
   * butun sonlar `BIGINT` (Rust `i64`);
   * yig'indilar `CAST(… AS BIGINT)` bilan.

   Har crate'da ikkita migratsiya to'plami bor: `migrations/sqlite` (mavjudlari ko'chirildi,
   kontrolsummalar o'zgarmagan) va `migrations/postgres` (`BIGINT`, `BYTEA`, PL/pgSQL append-only
   trigger).
3. **Yozish semantikasi.**
   * **SQLite:** avvalgidek — jarayon qulfi + `BEGIN IMMEDIATE`, hovuz 1 ulanish.
   * **PostgreSQL:** parallel tranzaksiyalar (`READ COMMITTED`), hovuz 32 ulanish. Poyga xavfi bor
     joylarda qulflar qo'yilgan:

     | Qayer | Qulf |
     |---|---|
     | LUK/ATC iste'moli | token qatori `FOR UPDATE` — bir xil kriptogramma parallel ikki marta o'tmasin |
     | LUK to'ldirish, holat o'tishlari | token qatori `FOR UPDATE` |
     | OTP tekshiruvi | challenge qatori `FOR UPDATE` |
     | Provisioning | karta va qurilma bo'yicha `pg_advisory_xact_lock` (doimiy tartibda), qulf ostida hisoblar qayta tekshiriladi (ID&V qoidalari va limitlar) |
     | DEK yaratish | advisory qulf (bir vaqtda ishga tushgan instansiyalar) |
     | Audit xesh-zanjiri | global advisory qulf, tranzaksiyadagi **oxirgi** qulf (deadlock bo'lmasin) |

     Emitent yechimi (`balance >= summa` sharti bilan `UPDATE`) va takroriy so'rov yozuvi
     (`INSERT … ON CONFLICT DO NOTHING`) o'zi atomar.
4. **Sirlar.** PostgreSQL URL'ida parol bor, shuning uchun faylga yozilmaydi: `[database] url_env`
   faqat muhit o'zgaruvchisining nomini saqlaydi. Testlar URL'ni dasturiy beradi (`url`, serializatsiya
   qilinmaydi). `Debug` da URL yashiriladi.
5. **Sinov.** `MPAY_TEST_PG_URL` (admin URL) o'rnatilsa, Vault testlari va butun e2e to'plami
   PostgreSQL'da yuguradi: har test uchun alohida baza yaratiladi (`mpay_db::fresh_test_database`).

## Oqibatlar

* Bir nechta instansiya bitta bazani bo'lisha oladi (P2.4). PQ Link sessiyalari, ro'yxatdan o'tish
  nonce'lari va rate-limit hali xotirada — P2.4 ishi.
* Audit zanjiri global bo'lgani uchun Vault yozuvlari audit qulfida ketma-ket commit qilinadi: bitta
  avtorizatsiyada bitta shunday commit bor. Takroriy so'rov va emitent commit'lari esa parallel va
  PostgreSQL ularni guruhlab fsync qiladi. `TODO(spec):` auditor talabi bo'yicha zanjirni bo'laklash
  (masalan token bo'yicha) yoki davriy muhrlash.
* SQLite yo'li o'zgarmadi: sandbox, demo va mavjud testlar ishlayveradi.
* Tekshirilgan:
  * `concurrent_same_atc_consumed_once` — `FOR UPDATE` olib tashlansa, PostgreSQL'da yiqiladi;
  * `concurrent_provisioning_respects_device_limit`;
  * Vault testlari 13/13 va e2e to'plami ikkala dialektda;
  * yuk sinovi: `docs/load-report.md` §8.

## Ko'rib chiqilgan muqobillar

* **Ikkita alohida implementatsiya (trait + SqliteVault/PgVault)** — har so'rov ikki marta yoziladi va
  vaqt o'tib bir-biridan ajralib ketadi.
* **`SERIALIZABLE` va qayta urinish** — qulflarsiz to'g'rilik, lekin har tranzaksiyani qayta
  urinadigan qilib yozish kerak bo'ladi va yuk ostida bekor qilishlar ko'payadi.
* **Avtorizatsiyaning hammasi (takroriy so'rov + Vault + emitent) bitta tranzaksiyada** — haqiqiy
  tizimda emitent alohida tizim (bank, ISO 8583 tarmog'i), shuning uchun umumiy tranzaksiya faqat
  sandbox artefakti bo'lardi. M-Pay tomonidagi commit'lar parallel bo'lishi yetarli.
