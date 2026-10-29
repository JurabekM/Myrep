# ADR-0026: Shield yuqori mavjudligi — yetakchi, zaxira va belgilar ombori snapshot'i

* Holat: qabul qilingan (2026-10-27, production checklist JM-4).
* Bog'liq: ADR-0019 (ko'p instansiya, Shield roli), ADR-0015 (rekey taxalluslari).

## Kontekst

Shield roli — yagona instansiya, belgilar ombori (tezlik oynalari, karta profillari, qurilma–karta
grafi) faqat uning xotirasida.

* Shield yiqilsa to'lov to'xtamaydi: API instansiyalari mahalliy zaxira dvigateliga o'tadi
  (`SHIELD_DEGRADED`). Lekin zaxira faqat shu instansiya ko'rgan hodisalarni biladi — tezlik va
  graf qoidalari zaiflashadi.
* Shield qayta ishga tushsa, butun tarix (qurilma fermalari, kartalar profillari) yo'qoladi.

## Qaror

### 1. Snapshot (`mpay-shield/src/snapshot.rs`, `FeatureStore::snapshot/restore`)

* Belgilar omborining to'liq holati: kartalar, qurilmalar, savdo nuqtalari, P2P oynasi, graf —
  union-find massivlari, qirralar, rekey taxalluslari.
* Format v1: `MPSHSNP1` ‖ versiya ‖ tana ‖ SHA-256. Little-endian, xaritalar saralangan — bir xil holat
  bir xil baytlarni beradi.
* O'qish qat'iy:
  * uzunliklar qolgan baytlar bilan cheklangan (katta ajratish yo'q);
  * indekslar tekshiriladi, union-find daraxtida aylana — xato (aks holda `find` tugamas edi);
  * NaN taqiqlangan, ortiqcha bayt — xato.
* Tiklangan ombor keyingi hodisalarda asl ombor bilan **aynan bir xil** belgilarni beradi (testda
  taxallus orqali ham).
* PAN yo'q: kartalar — `PanFingerprint` (HMAC), qurilmalar — `DeviceId`, savdo nuqtalari — FNV xeshi.

### 2. Yetakchilik (`mpay-server/src/shield_ha.rs`, `[shield_ha]`)

* Bir nechta Shield instansiyasi bitta bazani ko'radi.
* `shield_leader` — bitta qatorli ijara: `holder`, `epoch`, `expires_at`.
  * Har instansiya `renew_interval_ms` (standart 1 s) da olishga yoki yangilashga urinadi: o'zi egasi
    bo'lsa yoki muddat (`lease_ttl_ms`, standart 6 s) o'tgan bo'lsa.
  * Ega almashganda `epoch` oshadi. Bitta atomar `UPDATE … RETURNING`.
* **Faqat yetakchi xizmat qiladi.**
  * Zaxira ichki API'ga `503 SHIELD_STANDBY` qaytaradi.
  * Yetakchi o'zini ijara muddatidan bir yangilash oralig'i **oldin** to'xtatadi. DB'ga yeta olmasa,
    boshqasi olishidan oldin xizmatni to'xtatadi — ikki yetakchi bo'lmaydi.
  * Shart: instansiyalar soatlari farqi shu zaxiradan (1 s) kichik bo'lsin (NTP).
  * `instance_id` noyob bo'lishi shart (standart — `HOSTNAME`).
* **Snapshot.**
  * Yetakchi har `snapshot_interval_secs` (standart 30 s, compose'da 10 s) da `shield_snapshots` ga
    yozadi. Oxirgi `snapshots_keep` (3) tasi saqlanadi.
  * Yozuv `epoch` va ijara muddati bilan to'silgan: ijarani yo'qotgan eski yetakchining kechikkan
    snapshot'i yozilmaydi (`INSERT … SELECT … WHERE EXISTS`).
* **O'tish.**
  * Yangi `epoch` bilan yetakchi bo'lgan instansiya avval oxirgi butun snapshot'ni tiklaydi, keyin
    xizmat qiladi. Xeshi yoki tuzilmasi buzilgani o'tkazib yuboriladi va oldingisi olinadi.
  * Yangi jarayon (`epoch` 0) o'z nomidagi ijarani qayta olganda ham tiklaydi.
  * Yiqilishda oxirgi snapshot'dan keyingi hodisalar yo'qoladi: RPO ≤ `snapshot_interval_secs`,
    o'tish vaqti ≈ `lease_ttl_ms`.
* **To'g'ri to'xtatish** (`SIGTERM` → `step_down`): yakuniy snapshot va ijarani bo'shatish — zaxira
  bir yangilash oralig'ida oladi va hech narsa yo'qolmaydi.

### 3. Mijoz (`shield_client`)

* `[shield.remote] standby_urls` — so'rov avval oxirgi javob bergan instansiyaga, xato yoki `503` bo'lsa
  navbatdagisiga ketadi. Hammasi javob bermasa — mahalliy zaxira (avvalgidek).
* O'tish paytida (`lease_ttl_ms` gacha) so'rovlar mahalliy zaxirada — `SHIELD_DEGRADED`.

### 4. Kuzatuv

* Metrikalar:
  * `mpay_shield_leader` (HA o'chiq — doim 1);
  * `mpay_shield_epoch`, `mpay_shield_snapshot_age_seconds`, `mpay_shield_snapshot_bytes`;
  * `mpay_shield_takeovers_total`, `mpay_shield_snapshot_errors_total`.
* Ogohlantirishlar:
  * `MpayShieldNoLeader` (1 daqiqa yetakchisiz);
  * `MpayShieldSplitBrain` (critical, ikki yetakchi);
  * `MpayShieldSnapshotStale` (5 daqiqadan eski).
* `/healthz`: `leader`, `ha.epoch`, `ha.snapshot_age_secs`. Zaxira ham `200` qaytaradi (konteyner sog'),
  `leader` bilan ajratiladi.

## Oqibatlar

* Shield yiqilsa yoki yangilansa, tarix saqlanadi: zaxira oxirgi snapshot bilan davom etadi.
* `docker-compose`: `shield` va `shield-2`; API'lar ikkalasini biladi.
* Snapshot butun omborni ombor qulfi ostida yozadi (O(n)). Sandbox va pilot hajmida millisekundlar.
  Katta hajmda so'rovlar shu vaqtga kutadi: o'shanda inkremental jurnal (hodisalar WAL'i) yoki nusxa
  ustida yozish kerak bo'ladi.
* Snapshot bazada (`BYTEA`/`BLOB`) — PostgreSQL zaxirasi va PITR bilan birga saqlanadi (ADR-0023).
* Yiqilishda yo'qolgan oxirgi soniyalar hodisalari faqat tezlik oynalariga ta'sir qiladi. Karta va
  qurilma tarixining asosiy qismi (graf, profil) saqlanadi.
* Tekshirilgan:
  * snapshot: aynan tiklash, buzilgan va qisqa baytlar, union-find aylanasi, proptest;
  * HA unit:
    * yiqilgan yetakchi o'rniga oxirgi snapshot bilan;
    * eski yetakchi qaytganda zaxira, eski `epoch` bilan snapshot yozilmaydi;
    * `step_down` yo'qotishsiz, `snapshots_keep`;
    * buzilgan oxirgi snapshot → oldingisi;
  * e2e `p3_shield_ha` (SQLite va PostgreSQL), ikki haqiqiy Shield roli va API:
    * zaxira `503`;
    * yetakchi yiqildi → zaxira 3 kartani tiklab oldi;
    * 4-karta YELLOW (qurilma fermasi qoidasi tarix bilan), `SHIELD_DEGRADED` yo'q;
    * qayta ishga tushgan instansiya zaxira; `step_down` bilan qaytarildi, 4 karta saqlandi.
  * Tiklash o'chirilganda e2e yiqildi.
  * `scripts/compose-test.sh`: yetakchi `SIGKILL` → zaxira oladi, kartalar soni teng, keyingi yukda
    `SHIELD_DEGRADED` o'smaydi; qaytgan instansiya zaxira.

## Ko'rib chiqilgan muqobillar

* **Belgilarni to'g'ridan-to'g'ri bazada (taqsimlangan feature store):** har tranzaksiyada bir necha
  DB amali va oynalar bo'yicha so'rovlar. Shield kechikishi va baza yuklamasi oshadi. Hozirgi hajmda
  xotiradagi ombor va snapshot yetarli.
* **Ikkala instansiya faol, hodisalar ikkalasiga (replikatsiya):** tartib va izchillik muammosi, ikki
  xil qaror. Yetakchi + zaxira oddiyroq va bir xil belgilarni kafolatlaydi.
* **Snapshot fayl tizimida:** ikkinchi host'dan ko'rinmaydi. Baza allaqachon umumiy va zaxiralanadi.
* **Tashqi koordinator (etcd, Consul):** yangi komponent. PostgreSQL ijarasi shu vazifani bajaradi.
