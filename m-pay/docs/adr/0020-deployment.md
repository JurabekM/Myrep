# ADR-0020: Deployment — docker-compose, L4 load balancer, metrikalar, zaxira

* Holat: qabul qilingan (2026-10-26, 2-faza P2.5)

## Kontekst

P2.4 dan keyin `mpay-server` ko'p instansiyada ishlay oladi, lekin uni ishga tushirish qo'lda edi
(skriptlar ichida jarayonlar). Pilotga yaqin muhit uchun kerak:

1. Takrorlanadigan yig'ish va ishga tushirish (image, konfiguratsiya, sirlar, HSM tokeni).
2. Instansiyalar oldida load balancer. Talablar: TLS va mTLS **end-to-end** qolishi kerak (hamyon
   server sertifikatini emas, PQ Link identifikatorini pinlaydi; terminal mTLS sertifikati CN = API
   kaliti), mijozning haqiqiy IP'si esa IP chegarasiga (tahdid modeli D2) yetib borishi kerak.
3. Monitoring — dashboard'siz (loyiha cheklovi): metrikalar va ogohlantirish qoidalari.
4. Zaxira va tiklash, tiklanganini tekshirish bilan.
5. Instansiyani to'xtatganda ochiq so'rovlar uzilmasligi (`docker stop` — SIGTERM).

## Qaror

1. **Image.** Ko'p bosqichli `Dockerfile`: `rust:1.97.1-bookworm` da `--locked --release`
   (`pkcs11` feature), runtime — `debian:bookworm-slim` + SoftHSM2, `mpay` (uid 10001) foydalanuvchisi.
   `loadgen` bosqichi — yuk generatori (faqat sinov). `.dockerignore` — `target/`, `docs/`, sirlar.
2. **Compose** (`deploy/docker-compose.yml`): PostgreSQL 17, `bootstrap`, Shield roli, `api-1`,
   `api-2`, `smsgw`, nginx, Prometheus. Host'ga faqat `127.0.0.1:8443` va `127.0.0.1:9090`.
   * Sirlar — Docker secrets fayllari (`deploy/init-secrets.sh`, tasodifiy, git'ga tushmaydi);
     `mpay-entrypoint` `MPAY_X_FILE` dan `MPAY_X` ni eksport qiladi. Konfiguratsiyada sir yo'q.
   * `mpay-server bootstrap` — yangi buyruq: migratsiyalar va barcha `ensure_key` bir marta, API'lar
     ishga tushishidan oldin. Aks holda bir vaqtda yuklangan instansiyalar HSM'da bir xil yorliqli
     ikki kalit yaratishi mumkin edi.
   * Shield roli — TLS + mTLS (`init` endi `api-shield` mijoz sertifikatini ham chiqaradi),
     `init --tls-san` — sertifikatga konteyner nomlari.
3. **Load balancer — nginx `stream` (L4) + PROXY protocol v1.** TLS nginx'da ochilmaydi.
   `[http] proxy_protocol = true`: ulanish `trusted_proxies` dan kelsa, birinchi qator
   `PROXY TCP4 …\r\n` bo'lishi shart (≤ 107 bayt, 5 s), aks holda ulanish yopiladi va
   `mpay_proxy_protocol_rejected_total` oshadi. Boshqa manzillardan to'g'ridan-to'g'ri ulanish
   (ichki sog'liq tekshiruvi) sarlavhasiz qabul qilinadi. nginx statik IP'da (`10.88.0.10/32`) —
   faqat u ishonchli. Docker DNS `resolve` bilan qayta yaratilgan instansiya manzili yangilanadi.
4. **Metrikalar.** O'zimizning kichik Prometheus matn eksportchisi (`metrics.rs`, yangi bog'liqlik
   yo'q): HTTP so'rovlar va kechikish gistogrammasi (marshrut **shabloni**), avtorizatsiya javob
   kodlari, chegara turlari, Shield zaxirasi, OTP xatolari, PROXY rad etishlari, DB hovuzi va
   `SELECT 1`, PQ Link sessiyalari, Shield ombori hajmi. Yorliq qiymatlari cheklangan
   (`[A-Za-z0-9_]`, ≤ 16 belgi, aks holda `other`) — PAN yoki ID tushib qolishi mumkin emas.
   Alohida port (`[metrics] listen`, kalitsiz, faqat ichki tarmoq). Qoidalar — `alerts.yml`
   (SLA: avtorizatsiya p99 > 300 ms; mavjudlik; 5xx; `96`; bog'liqliklar; xavfsizlik).
5. **Graceful to'xtatish.** SIGTERM (va Ctrl+C) → yangi ulanishlar qabul qilinmaydi; ochiq
   ulanishlarga hyper `graceful_shutdown` (joriy so'rov tugaydi, keep-alive yopiladi), 8 s gacha
   kutiladi (`stop_grace_period: 15s`). Qo'shimcha: TLS handshake 10 s timeout, `accept` xatosida
   server to'xtamaydi (avval `?` bilan butun tsikl tugardi).
6. **Zaxira.** `deploy/backup.sh`: `pg_dump -Fc` + `state`/SoftHSM arxivi + `SHA256SUMS`.
   `deploy/restore.sh --verify` alohida bazaga tiklaydi va `mpay-server audit-verify` bilan audit
   xesh-zanjirini HSM kaliti orqali tekshiradi; `--replace` — ishlayotgan bazani almashtiradi.

## Oqibatlar

* Bitta buyruq: `init-secrets.sh` + `docker compose up -d --build`. `scripts/compose-test.sh` —
  to'liq sinov: yuk nginx orqali (TLS + mTLS), o'rtada `api-1` to'xtatiladi, `MpayInstanceDown`
  kutiladi, zaxira → tiklash → audit, loglarda PAN/sir yo'qligi. Natija: `docs/load-report.md` §10.
* IP chegarasi load balancer ortida ishlaydi (e2e `p2_deploy`: bitta proksi ortidagi ikki mijozning
  chegarasi alohida). Global chegara — umumiy DB token bucket (ADR-0019 §4, 2026-10-26).
* Metrikalar jarayon bo'yicha global (Prometheus odati); bir jarayondagi bir nechta server
  (testlar) hisoblagichlari qo'shiladi.
* SoftHSM tokeni hajm orqali instansiyalar orasida bo'linadi — faqat sandbox; production'da
  tarmoq HSM'i (PKCS#11 kutubxonasi, `MPAY_PKCS11_*`).
* Zaxirani shifrlash (oflayn kalit), PITR (WAL arxivi) va Alertmanager — ADR-0023 (2026-10-26).
  `TODO(spec):` PostgreSQL replikatsiyasi, nginx zaxirasi (keepalived/VIP), bankning navbatchilik
  kanali — pilot SLA va bank infratuzilmasi bo'yicha.

## Ko'rib chiqilgan muqobillar

* **L7 proksi (TLS nginx'da ochiladi, `X-Forwarded-For`):** terminal mTLS'i proksida tugaydi —
  CN'ni sarlavhada uzatish kerak bo'lardi (soxtalashtirish xavfi), server sertifikati va kaliti
  proksiga ko'chadi. Rad etildi.
* **PROXY protocol v2 (binar):** nginx ikkalasini ham yuboradi; v1 matnli, tahlili sodda va
  bayt-bayt o'qiladi (TLS baytlari iste'mol qilinmaydi). Kerak bo'lsa v2 keyin qo'shiladi.
* **`prometheus`/`metrics` crate'lari:** keragidan katta API va bog'liqliklar; bizga bir nechta
  hisoblagich va bitta gistogramma yetadi.
* **Kubernetes:** pilot uchun ortiqcha; compose fayli Helm/k8s manifestlariga ko'chirish uchun asos.
