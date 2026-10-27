# ZANJIR — Deploy

> 11-faza (ADR-0015). Server, ilova roli, TLS, zaxira — `deploy/` to'plami. Kundalik amallar va hodisalar — `RUNBOOK.md`.
> Maxfiy ma'lumotlar faqat `deploy/environments/<muhit>.env` da (0600, commit qilinmaydi); chatga yoki issue'ga yozilmaydi.

## Tarkib

| Fayl | Vazifa |
|---|---|
| `deploy/zanjir` | Boshqaruv: `init`, `up`, `down`, `ps`, `logs`, `migrate`, `backup`, `restore`, `psql`, `keygen` |
| `deploy/compose.yaml` | Xizmatlar: `db` (PostgreSQL 16), `migrate` (Alembic, bir martalik), `api` (FastAPI/uvicorn), `caddy` (TLS), `backup` |
| `deploy/server/Dockerfile` | Server image: `uv sync --locked --no-dev`, root emas (uid 10001), faqat o'qiladigan FS, HEALTHCHECK `/readyz` |
| `deploy/backup/` | `pg_dump` → `age` (ochiq kalit) shifrlangan kunlik zaxira, `restore.sh` |
| `deploy/db/init/10-roles.sh` | Bo'sh bazada rollar: `zanjir_owner`, `zanjir_app`, `zanjir_api` |
| `deploy/caddy/Caddyfile` | HTTPS (ACME yoki ichki CA), HSTS, `/metrics` yopiq, kirish logi o'chiq |
| `deploy/environments/*.env.example` | Staging va prod muhit namunalari |
| `deploy/check-staging.sh` | Staging qabul sinovi (CI `zanjir-deploy`) |

Staging va prod — bitta `compose.yaml`; farq faqat muhit faylida (domen, TLS, portlar, ro'yxatdan o'tish, chegaralar,
zaxira muddati). Har muhit — alohida Compose loyihasi (`zanjir-staging`, `zanjir-prod`): volume'lar ham alohida.

## Staging (lokal yoki sinov serveri)

```
deploy/zanjir up staging        # birinchi marta: environments/staging.env yaratiladi (tasodifiy parollar, age kalit)
deploy/check-staging.sh         # smoke + E2E (TLS orqali) + zaxira + tiklash mashqi
```

Lokal staging: `https://localhost:8443/` (Caddy ichki CA; ildiz sertifikati —
`docker compose ... exec caddy cat /data/caddy/pki/authorities/local/root.crt`). Ochiq ro'yxatdan o'tish va yuqoriroq auth
chegarasi faqat staging'da (E2E uchun).

## Prod (🛑 2-inson darvozasi)

Operator tayyorlaydi: O'zbekistondagi server (Ubuntu 24.04 LTS, ≥ 2 vCPU, 4 GB RAM, 40 GB SSD), domen (A yozuvi →
server IP), ACME uchun e-pochta. Qadamlar:

1. Server: `apt install docker.io docker-compose-v2 git`, `timedatectl set-ntp true` (soat — `clock_skew` uchun muhim),
   faervol: faqat 22 (SSH, kalit bilan), 80, 443 (`ufw allow 22,80,443/tcp`). Root SSH va parol bilan kirish o'chiq.
2. Zaxira kaliti — **operator kompyuterida**: `deploy/zanjir keygen ~/zanjir-backup.key`. Maxfiy kalit serverga
   qo'yilmaydi (ikki nusxa: shifrlangan USB + seyf); ochiq kalit `age1...` env'ga yoziladi.
3. Serverda: `git clone` → `deploy/zanjir init prod` → `deploy/environments/prod.env` da `<...>` qiymatlarni to'ldirish
   (domen, ACME e-pochta, `age1...`). Parollar va JWT kaliti avtomatik tasodifiy.
4. `deploy/zanjir up prod` — build, migratsiya, api, Caddy (sertifikat avtomatik), kunlik zaxira (21:30 UTC = 02:30 Toshkent).
5. Tekshiruv: `curl -I https://<domen>/healthz` (HSTS, `no-store`), `deploy/zanjir ps prod` (hammasi healthy).
6. Birinchi laboratoriya: RUNBOOK "Yangi laboratoriya". Ilova build'i: `--dart-define=ZANJIR_SERVER_URL=https://<domen>/`
   va `--dart-define=ZANJIR_VERIFY_BASE_URL=https://<domen>/v/` (12-faza).
7. Zaxiradan tiklash mashqi — birinchi hafta ichida va keyin har chorakda (RUNBOOK).

Korporativ (TLS'ni tekshiruvchi) proksi ortida build: proksi CA faylini `deploy/environments/build-ca.pem` ga qo'yib
`ZANJIR_BUILD_CA=./environments/build-ca.pem` (faqat build vaqtida, image'ga kirmaydi). Docker Hub cheklovi bo'lsa —
`ZANJIR_REGISTRY=mirror.gcr.io/library` (image'lar digest bilan qotirilgan — ko'zgu boshqa image bera olmaydi).

## Ma'lumotlarni lokalizatsiya qilish

> ⚠️ **Huquqshunos bilan tekshirilsin.** O'zbekiston fuqarolarining shaxsiy ma'lumotlari O'zbekiston hududidagi
> serverlarda saqlanishi talab qilinadi ("Shaxsga doir ma'lumotlar to'g'risida"gi qonun). Talabning joriy tahriri,
> zaxira nusxalar va CDN/log xizmatlariga tatbiqi huquqshunos tomonidan tasdiqlanmagan.

Reja: PostgreSQL, ilova serveri va shifrlangan zaxiralar — O'zbekistondagi serverda; tashqi xizmatlarga
(xato hisobotlari, metrikalar) shaxsiy ma'lumot yuborilmaydi.

## Server (7-faza, ADR-0011; 11-faza, ADR-0015)

`deploy/` da hammasi avtomatik: `migrate` xizmati `alembic upgrade head` ni `zanjir_owner` bilan bajaradi, `api`
`uvicorn --factory zanjir_server.main:app --workers 1 --proxy-headers` (faqat Caddy orqali, port tashqariga ochilmaydi).

**Baza rollari** (RLS chetlab o'tilmasligi uchun; `deploy/db/init/10-roles.sh` yaratadi):
- `postgres` — superuser, faqat konteyner ichidagi lokal socket (`peer`), tarmoqdan kirib bo'lmaydi.
- `zanjir_owner` — jadvallar egasi, faqat migratsiya va zaxira (`NOSUPERUSER`, `NOCREATEROLE`). Migratsiya RLS siyosatlari,
  triggerlar va `SECURITY DEFINER` qidiruv funksiyalarini yaratadi.
- `zanjir_app` — `NOLOGIN NOBYPASSRLS`; `zanjir_api` — ilova ulanadigan login roli, **faqat** `zanjir_app` a'zosi.
  Ilova har so'rovda `SET LOCAL ROLE zanjir_app` + `app.org_id` qiladi; tashkilot noma'lum yo'llar (kirish, refresh, taklif,
  `/v/{qr_token}`) faqat `zanjir_org_of_*` funksiyalari orqali `org_id` ni topadi. Testlar aynan shunday rol bilan ishlaydi.
- Ilovani superuser yoki jadval egasi bilan ishga tushirmang.

**Muhit o'zgaruvchilari** — `deploy/environments/*.env.example` (compose ularni `ZANJIR_*` ga uzatadi); serverni
`deploy/` siz ishga tushirish uchun — `server/.env.example`.
- `ZANJIR_REGISTRATION_OPEN=false` (prod): yangi laboratoriyani faqat operator ochadi (vaqtincha true qilib).
- `/metrics` standart o'chiq; yoqish — `ZANJIR_METRICS_TOKEN` (Prometheus `Authorization: Bearer`), Caddy tashqariga ochmaydi
  (404). Prometheus `zanjir-prod_frontend` tarmog'iga ulanib `http://api:8000/metrics` ni token bilan o'qiydi.
- Hisob bo'yicha kirish cheklovi: `ZANJIR_LOGIN_FAILURES_MAX` (10), `ZANJIR_LOGIN_FAILURES_WINDOW_SECONDS` (900);
  qurilma soati chegarasi: `ZANJIR_MAX_CLOCK_SKEW_SECONDS` (600) — server soati NTP bilan sinxron bo'lishi shart. Rate limiting bitta jarayon xotirasida — bir nechta nusxa bo'lsa
  Redis'ga o'tkaziladi.

## Mobil ilova build (ADR-0016)

To'liq tartib — `docs/RELEASE.md`: upload kaliti (foydalanuvchi, 3-darvoza), `ZANJIR_SERVER_URL=https://<domen>/
app/tool/build_release.sh` (normalar release darvozasi, testlar, obfuskatsiya, AAB tekshiruvi), Play internal testing.
Server manzili faqat `https://` (ilova `http` ni rad etadi; Android cleartext taqiqlangan).

## Zaxira (ADR-0015)

- Har kuni 21:30 UTC (`ZANJIR_BACKUP_AT`): `pg_dump --format=custom` → `age -r <ochiq kalit>` →
  `ZANJIR_BACKUP_DIR/zanjir-<UTC>.dump.age` + `.sha256`; `ZANJIR_BACKUP_KEEP_DAYS` dan eskilari o'chiriladi.
- Serverda faqat ochiq kalit: server buzib kirilsa ham zaxiralarni ochib bo'lmaydi. Maxfiy kalit yo'qolsa — zaxiralar
  ham yo'qoladi (ikki nusxa, alohida joyda).
- Server tashqarisiga nusxa (disk nosoz bo'lsa): shifrlangan fayllar boshqa O'zbekistondagi saqlash joyiga (`rsync`/`rclone`,
  faqat yozish huquqli kalit bilan). ⚠️ Lokalizatsiya talabi zaxiralarga ham tatbiq etilishi — huquqshunos bilan.
- Tiklash: `deploy/zanjir restore <muhit> <fayl> <maxfiy-kalit> --confirm <muhit>` (RUNBOOK). `restore.sh` faqat bo'sh
  bazaga tiklaydi; `check-staging.sh` har ishga tushishda zaxira → yangi PostgreSQL → nazorat yig'indilarini solishtiradi.
