# ADR-0027: PostgreSQL replikatsiyasi va almashinuvi, nginx zaxirasi (VRRP)

* Holat: qabul qilingan (2026-10-27, production checklist JM-5).
* Bog'liq: ADR-0018 (PostgreSQL), ADR-0020 (deployment), ADR-0023 (zaxira, PITR), ADR-0026 (Shield HA).

## Kontekst

Compose muhitida PostgreSQL va nginx bittadan edi:

* baza yiqilsa hamma narsa to'xtaydi (avtorizatsiya, Shield ijarasi, kliring), tiklash faqat
  zaxiradan — soatlab;
* nginx yiqilsa API'ga kirish yo'q, garchi ikki API instansiyasi ishlab tursa ham.

## Qaror

### 1. PostgreSQL: yetakchi + streaming replika

* Ikki tugun (`postgres`, `postgres-replica`) bir xil `deploy/postgres/pg-node.sh` bilan.
  * Bo'sh papka:
    * birinchi ishga tushishda (`PG_BOOTSTRAP=primary`, boshqa yetakchi yo'q) — initdb;
    * aks holda — joriy yetakchidan `pg_basebackup -R` (replika, `standby.signal`, o'z replikatsiya
      sloti).
  * Replikatsiya roli `replicator` — faqat `REPLICATION LOGIN`, ma'lumotlarga huquqi yo'q. Paroli —
    alohida sir (`pg_repl_password`).
* **Asinxron** replikatsiya:
  * yetakchi replikani kutmaydi — replika yiqilsa ham to'lovlar to'xtamaydi;
  * yetakchi yiqilsa replikaga yetmagan oxirgi tranzaksiyalar yo'qolishi mumkin;
  * kechikish kuzatiladi: `mpay_db_replication_lag_bytes`, `MpayDbReplicationLag`;
  * `TODO(spec):` pilot RPO — sinxron replikatsiya (ikki replika bilan, bittasi kechiksa ham yozuv
    davom etadi) yoki shu kelishuv.
* WAL arxivi (PITR) umumiy hajmda: almashinuvdan keyin yangi yetakchi ham shu yerga arxivlaydi, PITR
  yangi timeline bo'ylab tiklaydi.
* Slotlar WAL'ni replika uchun saqlaydi, lekin `max_slot_wal_keep_size = 2GB` — uzoq ishlamagan
  replika disk to'ldirmaydi (keyin `pg-rejoin.sh`).

### 2. `pg` proksisi — ilovalar har doim yetakchiga

* HAProxy (L4) + tashqi tekshiruv `pg-primary-check`: har tugunga `SELECT pg_is_in_recovery()`
  (`replicator` roli bilan), har 1 s.
* Faqat `false` qaytargan tugun xizmatda. Tugun tushsa, unga ochiq ulanishlar uziladi
  (`on-marked-down shutdown-sessions`).
* Ilovalar `database_url` → `pg:5432`. Almashinuvda ilovalar qayta ishga tushirilmaydi: sqlx hovuzi
  uzilgan ulanishlarni tashlaydi va yangilarini proksi orqali yangi yetakchiga ochadi.
* `balance first`: ikki tugun yetakchi ko'rinsa ham faqat birinchisiga.

### 3. Almashinuv qo'lda, skript bilan

`deploy/pg-failover.sh`:

* **Yiqilish:** to'siq — eski yetakchi konteyneri to'xtatiladi; keyin `pg_promote()`; keyin proksi
  yangi yetakchini ko'rganini kutish.
* **`--planned`:** yetakchi to'xtatiladi (fast shutdown: walsender oxirgi WAL'ni yuboradi), replika
  shu LSN'gacha yetib olgach ko'tariladi — yo'qotishsiz.
* **To'siq `pg-node.sh` ichida ham bor:** papkasi bor va yetakchi bo'lib ishga tushmoqchi tugun,
  boshqa tugun allaqachon yetakchi bo'lsa, ishga tushmaydi (`TO'SIQ` logi). Qaytgan eski yetakchi
  ikkinchi yetakchi bo'lolmaydi.
* `deploy/pg-rejoin.sh <xizmat>` — eski yetakchining papkasini o'chirib, yangi yetakchidan nusxa bilan
  replika qiladi.
* Zaxira va tiklash skriptlari (`backup.sh`, `restore.sh`) xizmat nomini qattiq yozmaydi — joriy
  yetakchini topadi (`deploy/lib-pg.sh`).
* Avtomatik almashinuv yo'q — konsensussiz avtomat split-brain xavfini oshiradi.
  `TODO(spec):` bank infratuzilmasida Patroni + etcd (yoki bankning standarti); unda shu proksi
  sxemasi o'zgarmaydi.

### 4. nginx zaxirasi — VRRP virtual IP

* Ikki nginx (`lb` 10.88.0.10, `lb-2` 10.88.0.11), har birining yonida keepalived — o'sha tarmoq nomlar
  fazosida, `NET_ADMIN`.
* VRRP unicast (Docker ko'prigida multicast'ga tayanmaslik uchun). VIP 10.88.0.100. nginx 8443 portda
  javob bermasa, VIP boshqasiga o'tadi.
* `nopreempt` — qaytgan nginx VIP'ni tortib olmaydi (keraksiz almashinuv yo'q).
* API'lar ikkala nginx'dan PROXY protocol sarlavhasini qabul qiladi (`trusted_proxies`).
* Dinamik IP'lar `.128–.255` oralig'ida — statik manzillar va VIP bilan to'qnashmaydi.
* Sandbox cheklovi:
  * host porti (`127.0.0.1:8443`) — faqat `lb`;
  * VIP ichki tarmoqda (ichki mijozlar, sinov);
  * `TODO(spec):` production'da VIP bankning tashqi tarmog'ida yoki bulut/apparat balansiri.

### 5. Kuzatuv

* Metrikalar (`[database] expected_replicas`):
  * `mpay_db_replicas`, `mpay_db_replicas_expected`;
  * `mpay_db_replication_lag_bytes` — yetakchining `pg_stat_replication` dan.
* Ogohlantirishlar (jami 21 qoida):
  * `MpayDbReplicaDown` — replika ulanmagan, 2 daqiqa;
  * `MpayDbReplicationLag` — 16 MB dan ortiq, 2 daqiqa.
* `MpayDbDown` (avvaldan bor) — yetakchi yo'q.

## Oqibatlar

* Baza yiqilsa, operator bitta buyruq bilan bir necha soniyada yangi yetakchiga o'tadi, ilovalar
  o'zi ulanadi. Avval esa zaxiradan tiklash soatlab davom etardi.
* RTO operator reaksiyasiga bog'liq (ogohlantirish → `pg-failover.sh`). RPO — replika kechikishi
  (odatda 0 yoki millisekundlar).
* Replika `hot_standby` — o'qish so'rovlari uchun ishlatilishi mumkin (hozir ishlatilmaydi).
* Yangi xizmatlar: `postgres-replica`, `pg` (o'z image'i: HAProxy + psql), `lb-2`, ikki keepalived.
* Mavjud o'rnatishlar:
  * `init-secrets.sh` `pg_repl_password` ni yaratadi va `database_url` xostini `pg` ga ko'chiradi;
  * replikatsiya roli faqat birinchi initdb'da yaratiladi — mavjud bazada qo'lda yaratish yoki
    `bootstrap`'dan oldin yangi hajm kerak.
* Ikkala tugun bir vaqtda o'chib, eski yetakchi papkasi bilan birga yoqilsa — to'siq ikkinchi tugunni
  ko'rmaydi (u ham o'chiq). Tartib: avval oxirgi yetakchini yoqish. Bu holatni faqat konsensusli
  tizim (Patroni) to'liq hal qiladi.
* Tekshirilgan:
  * PostgreSQL qismi alohida loyihada:
    * replikatsiya `streaming`;
    * yetakchi `SIGKILL` → `pg-failover.sh`: 1000/1000 qator, timeline 2, proksi yangi yetakchiga;
    * eski yetakchi qayta ishga tushirilganda `TO'SIQ`;
    * `pg-rejoin.sh` → replika, yangi yozuv yetib bordi;
    * `--planned` teskari almashinuv yo'qotishsiz (2001/2001, timeline 3).
  * VRRP alohida loyihada: VIP `lb` da; `lb` `SIGKILL` → 5 s da `lb-2`, VIP orqali TCP ulanish;
    qaytgan `lb` — BACKUP, VIP `lb-2` da qoldi.
  * To'liq `scripts/compose-test.sh` — natija `docs/PROGRESS.md` da.

## Ko'rib chiqilgan muqobillar

* **Patroni + etcd (avtomatik almashinuv):** production standarti, lekin uchta yangi komponent va
  konsensus kerak. Bank infratuzilmasi tanlanganda. Proksi va ilova sxemasi shunga mos.
* **Ilovada bir nechta xost (`target_session_attrs=read-write`):** sqlx'da bir nechta xostli
  ulanish yo'q, hovuzni qayta qurish esa har komponentga tegadi. Proksi ilovani o'zgartirmaydi.
* **Sinxron replikatsiya (bitta replika bilan):** replika yiqilsa yetakchi yozishni to'xtatadi —
  to'lovlar to'xtaydi. Ikki replika va RPO talabi bilan qayta ko'riladi.
* **Ikkinchi nginx DNS round-robin bilan:** mijoz o'lik manzilni keshlab qoladi. VIP darhol o'tadi.
