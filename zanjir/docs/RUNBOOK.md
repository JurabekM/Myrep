# ZANJIR — Runbook

> 11-faza (ADR-0015). Barcha buyruqlar repo ildizidan, serverda: `deploy/zanjir <buyruq> prod`.
> O'rnatish — `DEPLOY.md`. Maxfiy qiymatlar faqat `deploy/environments/prod.env` da; logga, chatga, tiketga yozilmaydi.

## Kundalik holat

| Nima | Buyruq / belgi |
|---|---|
| Xizmatlar | `deploy/zanjir ps prod` — `db`, `api`, `caddy` — `healthy`; `migrate` — `exited (0)`; `backup` — `running` |
| Tirikligi | `curl -s https://<domen>/healthz` → `{"status":"ok"}`; baza bilan — `/readyz` → `ready` |
| Loglar | `deploy/zanjir logs prod api` — JSON (`zanjir.access`, `zanjir.sync`); sir va token yozilmaydi |
| Zaxira | `ls -l <ZANJIR_BACKUP_DIR>` — har kuni yangi `zanjir-*.dump.age` (+ `.sha256`); `deploy/zanjir logs prod backup` |
| Disk | `df -h` (baza volume'i, zaxiralar); Docker loglari aylanadi (5 × 10 MB) |
| Soat | `timedatectl` — `System clock synchronized: yes` (aks holda qurilmalar `clock_skew` bilan rad etiladi) |

Ogohlantiruvchi belgilar (metrikalar, `/metrics` token bilan): `zanjir_sync_push_rejected_total` keskin o'ssa — qurilmada
qotgan yozuv yoki soxtalashtirish urinishi (`reason` bo'yicha: `audit_chain:*`, `missing_audit_event`, `plan_immutable`,
`protocol_rule:*`); 5xx ulushi; `/readyz` 503.

## Yangilash

1. `deploy/zanjir backup prod` — yangilashdan oldingi zaxira (fayl nomini yozib qo'ying).
2. `git fetch && git checkout <yangi teg>` (faqat ko'rib chiqilgan teg; `main` ga to'g'ridan-to'g'ri emas).
3. `deploy/zanjir up prod` — image'lar qayta build, `migrate` (Alembic) avval, keyin `api` (eski konteyner sog'lom
   yangisi kelguncha ishlaydi; qisqa uzilish ≤ 30 s — ilova oflayn ishlaydi, navbat keyin yuboriladi).
4. Tekshiruv: `ps`, `/readyz`, bitta qurilmada qo'lda sinxronlash.

**Orqaga qaytish:** migratsiyalar faqat oldinga. Sxema o'zgarmagan bo'lsa — `git checkout <eski teg> && deploy/zanjir up prod`.
O'zgargan bo'lsa — eski teg + 1-qadamdagi zaxiradan tiklash (quyida); yangilashdan keyingi sinxronlangan o'zgarishlar
qurilmalar navbatidan qayta yuboriladi (idempotent), serverdan olinganlari qurilmalarda qoladi.

## Zaxiradan tiklash

> Bazani **o'chiradi**. Avval sabab va tiklanadigan fayl LEAD/rahbar bilan kelishiladi; hodisa yozib boriladi.

1. Maxfiy kalitni (operator nusxasi) serverga vaqtincha olib keling: `/root/zanjir-backup.key` (0600).
2. Fayl butunligi: `cd <ZANJIR_BACKUP_DIR> && sha256sum -c zanjir-<UTC>.dump.age.sha256`.
3. `deploy/zanjir restore prod <ZANJIR_BACKUP_DIR>/zanjir-<UTC>.dump.age /root/zanjir-backup.key --confirm prod` —
   `caddy`, `api`, `backup` to'xtaydi, `zanjir` bazasi qayta yaratiladi, zaxira bitta tranzaksiyada tiklanadi, xizmatlar
   qaytadi.
4. `shred -u /root/zanjir-backup.key`.
5. Tekshiruv: `/readyz`; `deploy/zanjir psql prod` → `SELECT count(*) FROM protocol;`; bitta qurilmada sinxronlash.
   Zaxiradan keyin yaratilgan yozuvlar qurilmalar navbatidan qayta keladi (push idempotent; audit zanjiri davom etadi).

**Mashq** (birinchi hafta va har chorak): zaxira faylini sinov serveriga (yoki lokal staging'ga) ko'chirib
`deploy/check-staging.sh` dagi 5a-qadam kabi bo'sh bazaga tiklash, jadval sonlarini prod bilan solishtirish. Natija sanasi
shu faylning oxiriga yoziladi.

## Yangi laboratoriya (prod'da ro'yxatdan o'tish yopiq)

1. `prod.env`: `ZANJIR_REGISTRATION_OPEN=true` → `deploy/zanjir up prod`.
2. Laboratoriya LEAD'i ilovada "Laboratoriyani serverda ro'yxatdan o'tkazish" ni bajaradi (operator telefonda kuzatadi).
3. Darhol `ZANJIR_REGISTRATION_OPEN=false` → `deploy/zanjir up prod`. Qolgan xodimlar — taklif kodi orqali.

## Kalitlar va kirish

| Holat | Amal |
|---|---|
| Telefon yo'qoldi / o'g'irlandi | ADMIN `POST /devices/{id}/revoke` bilan qurilmani bekor qiladi (ilovada bu ekran hali yo'q, F-25); tashkilotda ADMIN bo'lmasa — operator: `deploy/zanjir psql prod` → `UPDATE device SET revoked_at = now(), updated_at = now(), rev = rev + 1 WHERE id = '<id>';`. Bekor qilingan qurilmaning keyingi push'lari rad etiladi; foydalanuvchi parolini almashtiradi |
| Xodim ketdi | `DELETE /users/{id}` (ADMIN) — refresh tokenlar va qurilmalar bekor qilinadi; imzolagan protokollari amalda qoladi |
| JWT kaliti sizib chiqdi yoki rejali almashtirish (yiliga) | `prod.env` da `ZANJIR_JWT_SECRET` ni yangilash (`od -An -tx1 -N32 /dev/urandom \| tr -d ' \n'`) → `deploy/zanjir up prod`. Access tokenlar (15 daq) bekor bo'ladi, ilovalar refresh orqali avtomatik yangilaydi |
| Baza parollari | `deploy/zanjir psql prod` → `ALTER ROLE zanjir_api PASSWORD '...'` (yoki `zanjir_owner`) → `prod.env` ni yangilash → `up` |
| Metrika tokeni | `ZANJIR_METRICS_TOKEN` ni yangilash → `up`; Prometheus konfiguratsiyasida ham |
| Zaxira kaliti | Yangi juftlik (`keygen`) → `ZANJIR_BACKUP_AGE_RECIPIENT` → `up`. Eski maxfiy kalit eski zaxiralar muddati tugaguncha saqlanadi |

## Hodisalar

- **`api` unhealthy / 5xx:** `logs prod api` (so'nggi xato), `/readyz` (baza). Baza ishlamasa — `logs prod db`, disk.
  Qayta ishga tushirish: `deploy/zanjir up prod`. Ilovalar oflayn ishlashda davom etadi — ma'lumot yo'qolmaydi.
- **Disk to'ldi:** eski zaxiralar (`KEEP_DAYS`), `docker system prune` (volume'larsiz!). Baza volume'iga tegilmaydi.
- **Sertifikat yangilanmadi:** `logs prod caddy` (ACME xatosi: DNS A yozuvi, 80-port ochiqligi). Caddy o'zi qayta urinadi.
- **Ko'p `push_rejected`:** `reason` bo'yicha. `clock_skew` — qurilma (yoki server) soati; `audit_chain:*`,
  `missing_audit_event`, `plan_immutable`, `qr_token_invalid` — mumkin bo'lgan soxtalashtirish: qurilma egasi bilan
  bog'lanish, kerak bo'lsa qurilmani bekor qilish; dalil sifatida loglarni saqlash.
- **Buzib kirish gumoni:** tarmoqni cheklash (faqat SSH), barcha kalitlarni almashtirish (yuqoridagi jadval), barcha
  refresh tokenlarni bekor qilish (`deploy/zanjir psql prod` → `UPDATE refresh_token SET revoked_at = now() WHERE revoked_at IS NULL;`),
  `audit_event` jadvalini dalil sifatida saqlash (zanjir har push'da serverda tekshiriladi), toza serverga zaxiradan tiklash. Shaxsga doir ma'lumotlar sizgan bo'lsa —
  qonun bo'yicha xabardor qilish tartibi (huquqshunos).
- **Protokol shubhali:** `/v/<token>` sahifasi imzo va hash'larni tekshiradi; bekor qilish — LEAD/ADMIN ilovada (sabab bilan).

## Mashqlar jurnali

| Sana | Nima | Natija |
|---|---|---|
| 2026-10-27 | Staging: zaxira → yangi PostgreSQL ga tiklash va `zanjir restore staging` (`check-staging.sh`) | ✅ 20 jadval + sxema nazorat yig'indilari bir xil |
