# deploy — virtual pilot muhiti (docker-compose)

2-faza P2.5 ([ADR-0020](../docs/adr/0020-deployment.md)). Bitta buyruq bilan pilotga yaqin muhit:
PostgreSQL, SoftHSM (PKCS#11), Shield roli, ikkita API instansiyasi, nginx (L4) va Prometheus.
Dashboard yo'q — interfeys HTTP API, CLI va ogohlantirish qoidalari.

```
              127.0.0.1:8443                       ichki tarmoq 10.88.0.0/24
 mijoz ──TLS──▶ nginx (lb, 10.88.0.10) ──TLS + PROXY v1──▶ api-1 ─┐
 (hamyon,       L4: TLS ochilmaydi       least_conn        api-2 ─┼─▶ PostgreSQL
  terminal)                                                       ├─▶ shield (mTLS, ichki API)
                                                                  ├─▶ smsgw (virtual SMS)
                                                                  └─▶ SoftHSM tokeni (hajm)
 Prometheus (127.0.0.1:9090) ◀── /metrics :9464 (api-1, api-2, shield) + alerts.yml
```

## Ishga tushirish

```bash
bash deploy/init-secrets.sh
```

```bash
docker compose -f deploy/docker-compose.yml up -d --build
```

* `init-secrets.sh` — tasodifiy sirlar `deploy/secrets/` ga (git'ga ham, Docker build kontekstiga ham
  tushmaydi): PostgreSQL paroli va URL'i, HSM PIN'i, Shield kaliti, SMS shlyuzi tokeni.
  Konteynerlarga Docker secrets sifatida (`/run/secrets/*`) ulanadi, muhit o'zgaruvchisida emas.
* `bootstrap` (bir martalik) — SoftHSM tokeni, `mpay-server init --tls --keystore pkcs11`,
  konfiguratsiyani moslash va `mpay-server bootstrap` (migratsiyalar va HSM kalitlari bir marta,
  instansiyalar bir vaqtda yuklanganda poyga bo'lmasin). Holat `state` hajmida; qayta ishga
  tushirilganda mavjud konfiguratsiya o'zgartirilmaydi, faqat migratsiyalar.
* API kalitlari va mTLS sertifikatlari (sandbox): `state` hajmidagi `dev-credentials.env`,
  `operator-1.*.pem`, `terminal-1.*.pem`. Server sertifikati SAN: `localhost`, `lb`, `api-1`,
  `api-2`, `shield`.

## Tekshirish

```bash
curl -sk https://127.0.0.1:8443/healthz
```

```bash
curl -s http://127.0.0.1:9090/api/v1/alerts
```

To'liq sinov (yuk nginx orqali, bitta API'ni to'xtatish, ogohlantirish, zaxira → tiklash → audit):

```bash
bash scripts/compose-test.sh
```

## Metrikalar va ogohlantirishlar

`[metrics] listen` — alohida ichki port (`/metrics`, oddiy HTTP, host'ga ochilmaydi). Yorliqlarda
faqat marshrut shabloni, metod, status, javob kodi — PAN, token, qurilma ID, IP hech qachon.

| Metrika | Turi | Ma'nosi |
|---|---|---|
| `mpay_http_requests_total{route,method,status}` | counter | HTTP so'rovlar |
| `mpay_http_request_duration_seconds{route}` | histogram | kechikish (0,3 s — SLA chegarasi) |
| `mpay_authorizations_total{code}` | counter | ISO 8583 javob kodlari |
| `mpay_rate_limited_total{kind}` | counter | `ip`, `api_key`, `device`, `handshake_queue` |
| `mpay_shield_degraded_total` | counter | Shield roli javob bermadi (mahalliy zaxira) |
| `mpay_otp_delivery_failures_total` | counter | SMS yetkazilmadi |
| `mpay_integrity_checks_total{result}` | counter | Play Integrity: `ok`, `missing`, `invalid`, `unavailable`, `absent` (ADR-0021) |
| `mpay_proxy_protocol_rejected_total` | counter | proksidan yaroqsiz PROXY sarlavhasi |
| `mpay_db_up`, `mpay_db_pool_connections{state}`, `mpay_db_pool_max_connections` | gauge | baza |
| `mpay_pqlink_sessions` | gauge | PQ Link sessiyalari (klaster bo'yicha) |
| `mpay_shield_{cards,devices,merchants,graph_nodes}` | gauge | Shield belgilar ombori |
| `mpay_build_info{version,role}`, `mpay_process_start_time_seconds` | gauge | versiya, ishga tushish |

Qoidalar — [`prometheus/alerts.yml`](prometheus/alerts.yml): instansiya yo'q, sig'im kamaydi, DB
yo'q, avtorizatsiya p99 > 300 ms, 5xx > 1 %, `96` javoblari, Shield zaxirada, Play Integrity javob
bermayapti yoki yaroqsiz tokenlar ko'paydi, OTP yetkazilmayapti,
DB hovuzi to'la, chegara portlashi, PROXY sarlavhasi rad etildi. `TODO(spec):` Alertmanager
marshruti (bankning navbatchilik kanali).

## Zaxira va tiklash

```bash
bash deploy/backup.sh
```

```bash
bash deploy/restore.sh deploy/backups/<UTC-vaqt> --verify
```

* `backup.sh` — ishlab turgan muhitdan: `pg_dump -Fc` (bitta izchil snapshot), `state` + SoftHSM
  tokeni arxivi, `SHA256SUMS`. Zaxira papkasi git'ga tushmaydi.
* `restore.sh --verify` — alohida bazaga tiklaydi va audit xesh-zanjirini HSM kaliti bilan
  tekshiradi (ishlayotgan muhitga tegmaydi) — davriy tiklash mashqi.
* `restore.sh --replace` — API'larni to'xtatib `mpay` bazasini almashtiradi, tekshiradi, ishga tushiradi.
* DB'dagi karta ma'lumoti faqat KEK/DEK bilan shifrlangan: HSM kalitlarisiz zaxira foydasiz.
  `TODO(spec):` zaxirani oflayn kalit bilan shifrlash va bank HSM'ining o'z zaxira tartibi.

## To'xtatish va yangilash

* `docker compose stop api-1` — SIGTERM: yangi ulanishlar qabul qilinmaydi, ochiq so'rovlar
  tugatiladi (≤ 8 s), keep-alive ulanishlar yopiladi; nginx qolgan instansiyaga yo'naltiradi.
  Navbatma-navbat yangilash: `api-1` → sog'lom → `api-2`.
* `docker compose down` — hajmlar saqlanadi; `down -v` — **hammasi o'chadi** (DB, HSM tokeni).

## Production'dan farqlari (sandbox)

* `sandbox = true`: `/v1/sandbox/*` va OTP'ni API orqali olish yoqilgan; SoftHSM o'rniga bank HSM'i.
* O'z-o'zini imzolagan TLS va mTLS CA'si (`init`); production'da bankning PKI'si.
* Ichki SMS shlyuzi shifrsiz `http://` (`insecure_http`) — faqat izolyatsiyalangan tarmoq.
* Bitta host: PostgreSQL replikatsiyasi va nginx zaxirasi yo'q (`TODO(spec)`: pilot SLA bo'yicha).
