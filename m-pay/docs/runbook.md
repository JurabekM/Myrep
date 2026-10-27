# M-Pay navbatchi runbook'i

Sana: 2026-10-27 (checklist JM-11). Compose muhiti (`deploy/`) uchun: ogohlantirish → nima bo'ldi → nima
qilish → qanday tekshirish. Arxitektura va qarorlar — ADR'larda (havolalar har bo'limda). Production
infratuzilmasi (alohida host'lar, bank HSM'i, avtomatik almashinuv) tanlanganda buyruqlar o'zgaradi,
tartib esa qoladi.

## 0. Umumiy

```bash
DC="docker compose -f deploy/docker-compose.yml"        # loyiha: mpay (COMPOSE_PROJECT_NAME)
$DC ps                                                   # xizmatlar va sog'lig'i
$DC logs --no-color --since 15m api-1                    # loglar (PAN/sir yo'q — faqat maskalangan)
curl -s http://127.0.0.1:9090/api/v1/alerts              # faol ogohlantirishlar (Prometheus)
```

* **Muhim:** loglarda va chatlarda ochiq PAN, kalit, LUK, kriptogramma hech qachon bo'lmaydi.
  Hodisa yozuvida faqat maskalangan PAN (`990012******3456`), token ID, RRN, STAN.
* **Eskalatsiya:** `critical` — darhol navbatchi va texnik rahbar; mijoz puliga ta'sir qilsa
  (`MpayReversalFailed`, `ISSUER_ONLY_APPROVED`) — bankning operatsion bo'limi ham.
  `TODO(spec):` bankning navbatchilik kanali va eskalatsiya zanjiri (checklist BK-8).
* **Hodisa yozuvi:** vaqt (UTC+5), ogohlantirish, ta'sir (to'lovlar to'xtadimi, nechta mijoz),
  qilingan buyruqlar va natija, keyingi qadamlar. Har critical'dan keyin — tahlil (postmortem).

### O'lchangan tiklash vaqtlari (compose, bitta host)

| Hodisa | Tiklanish | Ma'lumot yo'qotish | Manba |
|---|---|---|---|
| API instansiyasi to'xtadi | darhol (nginx ikkinchisiga) | yo'q | `scripts/compose-test.sh` |
| Shield yetakchisi yiqildi | ≈ 8 s (avtomatik) | oxirgi snapshot'dan keyingi belgilar (≤ 10 s) | ADR-0026 |
| PostgreSQL yetakchisi yiqildi | ≈ 7 s **buyruqdan keyin** (`pg-failover.sh`) | replika kechikishi (sinovda 0) | ADR-0027 |
| nginx (VIP egasi) yiqildi | ≈ 5 s (avtomatik) | yo'q | ADR-0027 |
| Host butunlay yo'qoldi | `docs/dr-report.md` (dr-restore) | oxirgi zaxiradan keyingi hammasi | ADR-0028 |

## 1. Ogohlantirishlar jadvali

| Ogohlantirish | Daraja | Ma'nosi | Birinchi qadam |
|---|---|---|---|
| `MpayInstanceDown` | critical | API yoki Shield instansiyasi 30 s javob bermayapti | §2.1 / §2.3 |
| `MpayApiCapacityReduced` | warning | ishlayotgan API'lar < 2 | §2.1 |
| `MpayDatabaseDown` | critical | API bazaga ulana olmayapti | §2.2 |
| `MpayDbReplicaDown` | warning | replika ulanmagan — keyingi yiqilishda almashinuv yo'q | §2.2.3 |
| `MpayDbReplicationLag` | warning | replika 16 MB dan ortiq orqada | §2.2.4 |
| `MpayDbPoolExhausted` | warning | DB ulanishlar hovuzi to'la | §2.2.5 |
| `MpayAuthorizationLatencyHigh` | critical | avtorizatsiya p99 > 300 ms (SLA) | §2.6 |
| `MpayHttp5xxRate` | critical | 5xx > 1 % | §2.6 |
| `MpaySystemErrorResponses` | critical | terminallarga `96` (natija noma'lum) | §2.5 |
| `MpayReversalFailed` | critical | emitent reversal'ni rad etdi — mijoz puli qaytmagan bo'lishi mumkin | §2.5.2 |
| `MpayReversalBacklog` | warning | reversal 15 daqiqadan beri yuborilmayapti | §2.5.3 |
| `MpayShieldDegraded` | warning | API'lar Shield roliga yeta olmayapti — mahalliy zaxira | §2.3 |
| `MpayShieldNoLeader` | warning | Shield yetakchisi yo'q | §2.3 |
| `MpayShieldSplitBrain` | critical | ikki Shield yetakchi | §2.3.2 |
| `MpayShieldSnapshotStale` | warning | Shield snapshot'i 5 daqiqadan eski | §2.3.3 |
| `MpayIntegrityUnavailable` | warning | Play Integrity javob bermayapti — yangi kartalar qo'shilmaydi | §2.7 |
| `MpayIntegrityInvalidSpike` | warning | yaroqsiz yaxlitlik tokenlari — klon ilova yoki hujum | §2.8 |
| `MpayOtpDeliveryFailing` | warning | OTP SMS yetkazilmayapti | §2.7 |
| `MpayRateLimitSpike` | warning | chegaraga tushgan so'rovlar ko'p | §2.8 |
| `MpayRateLimitStoreErrors` | warning | umumiy chegara ombori xatosi (fail-open) | §2.2 |
| `MpayProxyProtocolRejected` | warning | ishonchli proksidan yaroqsiz PROXY sarlavhasi | §2.4 |

## 2. Hodisalar

### 2.1 API instansiyasi ([ADR-0019](adr/0019-kop-instansiya.md), [ADR-0020](adr/0020-deployment.md))

Ta'sir: nginx qolgan instansiyaga yo'naltiradi — to'lovlar davom etadi, sig'im yarmiga tushadi.

1. `$DC ps api-1 api-2`; `$DC logs --no-color --tail 100 api-1`.
2. Konteyner to'xtagan — `$DC start api-1`; ishga tushmayapti — log oxirida sabab:
   * `KeyStore` / PKCS#11 — §2.9 (HSM);
   * `ma'lumotlar bazasi` — §2.2;
   * `konfiguratsiya` — oxirgi o'zgarishni qaytaring.
3. Tekshiruv: `$DC ps` — `healthy`; Prometheus `up{job="mpay-api"}` ikkalasi 1.

### 2.2 PostgreSQL ([ADR-0027](adr/0027-postgres-replika-va-lb-zaxira.md))

#### 2.2.1 Yetakchi yiqildi (`MpayDatabaseDown`)

Ta'sir: avtorizatsiya va boshqa yozuvlar to'xtagan (terminallar xato oladi va qayta urinadi).
Shield ijarani yangilay olmaydi → API'lar mahalliy Shield zaxirasida.

1. Holatni aniqlang (har tugun — `f` yetakchi, `t` replika, bo'sh — javob yo'q):

   ```bash
   for s in postgres postgres-replica; do echo "$s: $($DC exec -T $s psql -U mpay -d mpay -qAtc 'SELECT pg_is_in_recovery()' 2>&1 | tail -1)"; done
   ```
2. Yetakchi tez qaytmasa (konteyner/host yiqilgan, disk buzilgan) — almashinuv:

   ```bash
   bash deploy/pg-failover.sh
   ```

   Skript eski yetakchini to'xtatadi (to'siq), replikani ko'taradi va `pg` proksisi yangi yetakchini
   ko'rguncha kutadi. Ilovalarni qayta ishga tushirmang — o'zi ulanadi.
3. Tekshiruv: `MpayDatabaseDown` yopildi; `$DC logs --since 2m api-1` da DB xatolari to'xtadi.
4. **Ma'lumotlar:** almashinuv asinxron — replikaga yetmagan oxirgi tranzaksiyalar yo'qolishi mumkin.
   Almashinuv vaqtini qamragan kun uchun solishtirish:

   ```bash
   $DC run --rm --no-deps -T --entrypoint mpay-entrypoint bootstrap mpay-server recon --config /var/lib/mpay/state/mpay.toml
   ```

   Tafovutlar — §2.5.4.
5. Eski yetakchini replika qiling (ishlab turgan yetakchi kerak): `bash deploy/pg-rejoin.sh postgres`
   (yoki `postgres-replica` — qaysi biri yiqilgan bo'lsa).

#### 2.2.2 Rejali almashinuv (texnik xizmat)

`bash deploy/pg-failover.sh --planned` — yo'qotishsiz (replika oxirgi WAL'gacha yetib oladi), keyin
`bash deploy/pg-rejoin.sh <eski yetakchi>`.

#### 2.2.3 Replika ulanmagan (`MpayDbReplicaDown`)

Ta'sir: hozir yo'q, lekin yetakchi yiqilsa almashinadigan tugun yo'q.

1. `$DC ps postgres postgres-replica`; `$DC logs --tail 50 postgres-replica`.
2. Log'da `TO'SIQ` — bu tugun eski yetakchi (almashinuvdan keyin qayta yoqilgan): `bash deploy/pg-rejoin.sh <xizmat>`.
3. Replika ishlayapti, lekin ulanmagan (slot yo'q, WAL `max_slot_wal_keep_size` dan oshgan) — `pg-rejoin.sh` (to'liq qayta nusxa).

#### 2.2.4 Replika kechikmoqda (`MpayDbReplicationLag`)

Disk yoki tarmoq sekin, yoki replikada uzoq so'rov. `SELECT * FROM pg_stat_replication` (yetakchida) —
`write_lag`, `replay_lag`. Kechikish davom etsa — yetakchi yiqilganda shuncha ma'lumot yo'qoladi:
rejali almashinuvlarni kechiktiring.

#### 2.2.5 Hovuz to'la (`MpayDbPoolExhausted`)

Uzoq tranzaksiya yoki yuk oshgan. `SELECT pid, state, now() - xact_start, left(query, 60) FROM
pg_stat_activity ORDER BY 3 DESC NULLS LAST LIMIT 10` (yetakchida). Yuk — `[database] max_connections`
(PostgreSQL `max_connections` 200 — instansiyalar × hovuz undan oshmasin).

#### 2.2.6 Noto'g'ri amal (ma'lumot o'chirildi yoki buzildi)

Replika ham shu amalni oladi — almashinuv yordam bermaydi. Muayyan lahzaga tiklash (PITR), alohida
konteynerga, tekshirib keyin qaror:

```bash
bash deploy/pitr-restore.sh deploy/backups/<B1> deploy/backups/<B2> "2026-10-27 14:05:00+05"
```

### 2.3 Shield ([ADR-0026](adr/0026-shield-yuqori-mavjudlik.md))

Ta'sir (har holatda): to'lovlar to'xtamaydi. API'lar mahalliy zaxirada (`SHIELD_DEGRADED`) —
firibgarlikni aniqlash zaiflashadi.

#### 2.3.1 Yetakchi yo'q (`MpayShieldNoLeader`, `MpayShieldDegraded`)

1. Kim yetakchi: `for s in shield shield-2; do $DC exec -T $s curl -sk https://localhost:8600/healthz; echo; done`
   — `"leader": true` biri bo'lishi kerak.
2. Ikkalasi `false` — ijara bazada: §2.2 (DB ishlayaptimi). Ikkalasi to'xtagan — `$DC start shield shield-2`.
3. Zaxira ijara muddatidan (6 s) keyin o'zi oladi va oxirgi snapshot'ni tiklaydi; `epoch` oshadi.

#### 2.3.2 Ikki yetakchi (`MpayShieldSplitBrain`, critical)

Sabab — soatlar farqi (NTP) yoki ikki instansiyada bir xil `[shield_ha] instance_id`.

1. Darhol bittasini to'xtating: `$DC stop shield-2` (qolgani yetakchi bo'lib qoladi).
2. `date -u` ni host'lar va konteynerlarda solishtiring; `instance_id` ni tekshiring.
3. Tuzatilgach — `$DC start shield-2` (zaxira bo'lib qo'shiladi).

#### 2.3.3 Snapshot eski (`MpayShieldSnapshotStale`)

Yetakchi bazaga yoza olmayapti (`mpay_shield_snapshot_errors_total` o'smoqda) — §2.2. Snapshot'lar
`shield_snapshots` jadvalida (oxirgi 3 tasi).

#### 2.3.4 Yangilash

Avval zaxirani, keyin yetakchini `$DC stop` (SIGTERM — yakuniy snapshot va ijara bo'shatiladi, zaxira
darhol oladi, hech narsa yo'qolmaydi).

### 2.4 nginx va VIP ([ADR-0027](adr/0027-postgres-replika-va-lb-zaxira.md))

* VIP egasi tushsa, keepalived ≈ 3–5 s da ikkinchisiga o'tkazadi. Kimda:
  `$DC exec lb ip -4 addr show dev eth0` (10.88.0.100).
* nginx qayta yaratilsa — yonidagi keepalived ham: `$DC restart lb-vrrp` (yoki `lb-2-vrrp`).
* `MpayProxyProtocolRejected` — API ishonchli proksidan yaroqsiz sarlavha oldi: nginx konfiguratsiyasi
  (`proxy_protocol on`) va API `[http] trusted_proxies` (ikkala nginx IP'si) ni solishtiring.

### 2.5 To'lovlar: `96`, reversal, solishtirish ([ADR-0024](adr/0024-reversal-va-solishtirish.md))

#### 2.5.1 `96` javoblari (`MpaySystemErrorResponses`)

Emitent javob bermadi (`ISSUER_TIMEOUT`), javob o'qilmadi yoki ishlov to'xtadi. Har biri avtomatik
reversal navbatiga tushadi — mijozning puli qaytariladi. Ko'p bo'lsa — emitent bilan aloqa yoki
yuklama (§2.6). Kassirga: mijoz qayta tap qilsin (yangi to'lov).

#### 2.5.2 Reversal rad etildi (`MpayReversalFailed`, critical)

Mijozdan pul yechilgan, qaytmagan bo'lishi mumkin.

1. Ro'yxat: `$DC exec -T <yetakchi PostgreSQL> psql -U mpay -d mpay -c "SELECT terminal_ref, stan, rrn, dpan_masked, amount_minor, response_code, result, updated_at FROM acquirer_reversals WHERE state = 'FAILED'"`.
2. Har yozuv bo'yicha emitent bilan (RRN, STAN, terminal) qo'lda qaytarish yoki tasdiq.
3. `FAILED` yozuvlar o'chirilmaydi — hal qilinganini hodisa yozuvida qayd eting.

#### 2.5.3 Reversal navbati tiqilgan (`MpayReversalBacklog`)

Emitent reversal'larga javob bermayapti; navbat saqlanadi va emitent tiklangach o'zi yuboriladi
(kutish ≤ 10 daqiqa). Emitent bilan aloqani tekshiring.

#### 2.5.4 Kunlik solishtirish tafovutlari

`mpay-server recon --date <kun>` chiqish kodi 1:

| Tur | Harakat |
|---|---|
| `ISSUER_ONLY_APPROVED` | mijozdan pul ketgan, terminal tasdiq olmagan — emitent bilan qaytarish (critical) |
| `ACQUIRER_ONLY_APPROVED` | terminal tasdiqlagan, emitentda yechim yo'q — savdo nuqtasi bilan hisob-kitob |
| `AMOUNT_MISMATCH` | emitent qaydnomasini tekshirish |
| `REVERSAL_FAILED` | §2.5.2 |
| `CLEARING_REJECTED` | §2.10 |

### 2.6 Kechikish va 5xx (`MpayAuthorizationLatencyHigh`, `MpayHttp5xxRate`)

1. Qaysi qism: `mpay_http_request_duration_seconds` marshrut bo'yicha; `mpay_db_pool_connections`;
   `mpay_shield_degraded_total` (Shield sekin bo'lsa timeout → mahalliy).
2. DB — §2.2.5; bitta instansiya — §2.1; HSM sekin — §2.9.
3. Yuk hujum bo'lsa — §2.8.

### 2.7 Karta qo'shish to'xtadi (`MpayIntegrityUnavailable`, `MpayOtpDeliveryFailing`)

Mavjud kartalar bilan to'lovlar ishlaydi; yangi kartalar qo'shilmaydi yoki OTP kelmaydi.

* Integrity: Google API (`[integrity.google]`), xizmat akkaunti kaliti muddati, tarmoq. Fail-closed —
  provisioning to'xtaydi (ADR-0021).
* OTP: SMS shlyuzi (`[otp.webhook]`), `MPAY_SMS_TOKEN`. Mijozga: `POST /v1/tokens/{id}/idv/resend`
  (3 marta).

### 2.8 Xavfsizlik (`MpayRateLimitSpike`, `MpayIntegrityInvalidSpike`)

* Qaysi chegara: `mpay_rate_limited_total{kind}` — `ip` (bitta manzildan), `device`, `api_key`
  (terminal kaliti o'g'irlangan bo'lishi mumkin), `handshake_queue`.
* nginx log'ida manzillar (`$DC logs lb lb-2`). Kerak bo'lsa — nginx'da manzilni bloklash.
* **Kalit oshkor bo'lishi:**
  * terminal mTLS sertifikati — `mpay-server cert-fingerprint --cert <pem>` → `[auth] revoked_client_certs`
    ([ADR-0011](adr/0011-mtls.md));
  * PQ Link server kaliti — `identity-next` → o'tish ([ADR-0012](adr/0012-kalit-almashtirish.md)),
    eskisini bekor qilish ro'yxatiga (`revoke`, oflayn ildiz kaliti, [ADR-0014](adr/0014-bekor-qilish-royxati.md)).

### 2.9 HSM (PKCS#11, [ADR-0017](adr/0017-hsm-sessiyalar.md))

Belgilar: `mpay-server` ishga tushmaydi (`KeyStore` xatosi), ishlayotgan serverda avtorizatsiya `91`
(`ISSUER_OFFLINE`), provisioning 500.

1. Ishlayotgan server sessiya/login yo'qolsa o'zi qayta ochadi — qisqa uzilish o'zi o'tadi.
2. Ishga tushmayapti: PIN (`secrets/hsm_pin`), token (`hsm` hajmi, sandbox — SoftHSM), kutubxona
   (`MPAY_PKCS11_LIB`).
3. Token yo'qolgan yoki buzilgan — zaxiradagi `state-hsm.tar.gz.age` dan (§2.11). **Kalitlarsiz DB
   ma'lumotlari o'qilmaydi** — HSM zaxirasi DB zaxirasidek muhim.
   `TODO(spec):` bank HSM'ining o'z klasteri va zaxira tartibi (checklist BK-3, BK-4).

### 2.10 Kliring ([ADR-0025](adr/0025-kliring-va-hisob-kitob.md))

* Kunlik cron — `deploy/README.md`. `409 CLEARING_NOT_READY` — kun ichida javobi noma'lum
  avtorizatsiya qolgan (reversal ishchisi yopadi), keyinroq qayta ishga tushiring.
* Chiqish kodi 1 — emitent yozuvlarni rad etgan (`rejected_items`): savdo nuqtasiga ular uchun
  to'lanmaydi, emitent bilan tekshiring.
* 3 kundan kechiksa acquirer jurnali yo'q — `400`, qo'lda (bank bilan).

### 2.11 Host butunlay yo'qoldi ([ADR-0028](adr/0028-falokatdan-tiklash.md))

Kerak:

* oxirgi shifrlangan zaxira (`deploy/backup.sh` natijasi, boshqa joyda);
* maxfiy zaxira kaliti (oflayn, `MPAY_BACKUP_IDENTITY`);
* sirlar nusxasi (`deploy/secrets/`: HSM PIN'i, DB, Shield, SMS) — zaxira bilan birga emas, alohida.

Tartib:

1. Yangi host: Docker, repo, sirlar → `deploy/secrets/`.
2. Image'lar: `docker build --target runtime -t mpay-server:local .`,
   `docker build -t mpay-pgproxy:local deploy/pgproxy`, `docker build -t mpay-keepalived:local deploy/keepalived`.
3. `bash deploy/dr-restore.sh <zaxira papkasi>` — holat va HSM, PostgreSQL, xizmatlar, audit zanjiri.
   Har bosqich vaqti chiqariladi.
4. Tekshiruv: `curl -sk https://127.0.0.1:8443/healthz`; `mpay-server recon`; sinov kartasi bilan to'lov.
5. Yo'qolgan davr (zaxiradan keyingi) — emitent qaydnomasi bilan solishtirish; terminallar u davrdagi
   to'lovlar uchun `96`/qayta urinish ko'rgan bo'lishi mumkin.
6. Yangi zaxira (`backup.sh`) — WAL arxivi yangi host'da noldan boshlanadi.

`TODO(spec):` zaxirani boshqa joyga uzluksiz yuborish (WAL ham) — RPO'ni daqiqalarga tushiradi (BK-13).

## 3. Muntazam ishlar

| Qachon | Ish | Buyruq |
|---|---|---|
| har kuni, kun tugagach | kliring va hisob-kitob | `mpay-server clearing --out-dir …` (cron) |
| har kuni | solishtirish (kecha) | `mpay-server recon --date …` |
| har kuni | shifrlangan zaxira | `bash deploy/backup.sh` → boshqa joyga |
| har hafta | zaxiradan tiklash mashqi (ishlayotgan muhitga tegmaydi) | `bash deploy/restore.sh <zaxira> --verify` |
| har chorak | falokatdan tiklash mashqi (alohida muhit) | `bash scripts/dr-drill.sh` |
| har chorak | almashinuv mashqi | `bash scripts/compose-test.sh` (Shield, PostgreSQL, nginx) |
| yangilashda | API navbatma-navbat; Shield — avval zaxira; PostgreSQL — `pg-failover.sh --planned` | §2.1, §2.3.4, §2.2.2 |
