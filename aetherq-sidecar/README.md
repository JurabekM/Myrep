# AETHER-Q Sidecar

Bitta monolit dasturni post-kvant xavfsiz tarmoq orqali ulaydigan proksi. Ilova kodi o'zgarmaydi:
ilova mahalliy oddiy TCP orqali sidecar bilan gaplashadi, sidecar trafikni tunel orqali yuboradi.

Tarkib:

- **Asosiy rejim:** AETHER-Q (Rust `aq-sidecar`, o'z protokolimiz): ML-KEM-768 + X25519 gibrid, ML-DSA-65 identity,
  session resumption, PoW himoyasi, 0-RTT (kutubxona darajasida).
- **Qo'shimcha rejim:** standart PQ-TLS (Go `aqctl gateway`): TLS 1.3 + X25519MLKEM768 + ML-DSA-65 sertifikat, pinning.
- **Control plane:** Go `aqctl` — identity, muddat va rotatsiya jadvali, allowlist, holat, Prometheus metrikasi.
- **Monolit:** `aether_new/` — sidecar orqasida ishlaydigan REST API (yozuvlar, JSON ombor).
- **Grafik dastur:** AETHER-Q Sidecar Studio (Rust/egui `aq-studio`) — buyruqlarsiz sozlash va boshqarish.

Reja: [PLAN.md](PLAN.md). Bu hujjat — amaldagi holat va ishlatish.

## AETHER-Q Sidecar Studio (grafik dastur)

Buyruq qatorisiz ishlatish uchun. O'rnatish: `dist\AETHER-Q-Studio-Setup-0.1.0.exe` (administrator huquqi
so'ralmaydi, `%LOCALAPPDATA%\Programs` ga o'rnatiladi). Ochilgach — **«Tez sozlash ustasi»**:

| Stsenariy | Nima qiladi |
|---|---|
| Bitta kompyuterda sinash | Kalitlar, ichki sinov serveri, server va klient tunellari — bir bosishda; natija brauzerda |
| Server: ilovamni himoyalash | Kalit + server profili; **taklif fayli** (`.aqinvite`) saqlanadi va klientga yuboriladi |
| Klient: serverga ulanish | Taklifni import qiladi; **ruxsat so'rovi** (`.aqrequest`) serverga qaytariladi |

Kalit almashinuvi fayl bilan: hex, buyruq yoki allowlist fayllarini qo'lda tahrirlash shart emas; barmoq izi
(fingerprint) har ikki tomonda ko'rsatiladi (telefonda solishtirish uchun).

Sahifalar: **Boshqaruv paneli** (jonli KPI, ulanishlar grafigi, hodisalar), **Tunellar** (profillar, ishga
tushirish/to'xtatish, tahrirlash, allowlist, taklif/so'rov, tunel sinovi, CLI ekvivalenti), **Kalitlar** (yaratish,
`.pub` eksport, muddat ogohlantirishi, rotatsiya), **Jurnal** (filtr, qidiruv, eksport, kunlik fayl),
**Diagnostika** (port, manzil, tunel orqali HTTP, ichki sinov serveri, kripto o'z-o'zini tekshirish),
**Sozlamalar**, **Qo'llanma** (xatolar va yechimlar).

Ichki tuzilma:

- AETHER-Q tunellari Studio jarayoni ichida ishlaydi (`aq_sidecar::runtime` — CLI bilan **bitta kod**); har xato
  hodisasida o'zbekcha izoh (masalan, alert 0x2f → «server kaliti pinned kalitga mos emas»).
- Standart rejim — `aqctl gateway` bola jarayoni (Windows Job Object: Studio yopilsa ham o'chadi); server
  statistikasi `/metrics` dan.
- Ma'lumotlar: `%APPDATA%\AETHER-Q\Studio` (`config.json`, `keys\` — `aqctl` bilan bir xil format, `logs\`).
- To'xtatish ochiq tunellarni ham yopadi (Windows'da `shutdown()` bloklangan `recv`'ni uyg'otmagani uchun o'qishlar
  0,5 s timeout bilan to'xtatish bayrog'ini tekshiradi).

Yig'ish (testlar o'tmasa o'rnatuvchi yig'ilmaydi):

```powershell
powershell -ExecutionPolicy Bypass -File scripts\package-studio.ps1   # → dist\AETHER-Q-Studio-Setup-0.1.0.exe, dist\studio\
```

## Tez ishga tushirish (Windows)

```powershell
python run.py        # to'liq demo: monolit + tunel + standart gateway + HTTP testlar + latency + metrika
```

`run.py` `dist\` papkasidagi `aq-sidecar.exe`, `aqctl.exe`, `aether_new.exe` ni ishlatadi (Python 3.8+, faqat stdlib).
Natijada `run-demo\` papkasi yaratiladi: kalitlar, ma'lumot fayli, har bir jarayonning logi.

```powershell
python loadtest.py           # yuk sinovi (≈2,5 daqiqa): avval hammasini qayta yig'adi, natija loadtest-out\report.md
python loadtest.py --quick   # tez tekshiruv (≈20 s)
```

## Tuzilma

| Yo'l | Til | Vazifa |
|---|---|---|
| `crates/aq-core` | Rust | AETHER-Q yadrosi: KDF/KMAC, KEM combiner, ML-KEM-768, ML-DSA-65, handshake (resumption, PoW, 0-RTT), transport |
| `crates/aq-sidecar` | Rust | Sidecar CLI: `keygen`, `serve`, `connect` (+ `examples/bench.rs`) |
| `control/cmd/aqctl` | Go | Control plane: `identity`, `allowlist`, `schedule`, `status`, `gateway` |
| `control/internal/identity` | Go | ML-DSA identity, allowlist, muddat (meta), barmoq izi (Rust bilan bir xil fayl formati) |
| `control/internal/gateway` | Go | Standart PQ-TLS gateway va `/metrics` hisoblagichlari |
| `aether_new/` | Go | Monolit: REST API (`/api/v1/records`), JSON fayl ombori |
| `dist/` | — | Tayyor ikkilik fayllar: `aq-sidecar.exe`, `aqctl.exe`, `aether_new.exe` |
| `crates/aq-studio` | Rust (egui) | AETHER-Q Sidecar Studio — grafik dastur |
| `installer/`, `scripts/package-studio.ps1`, `scripts/make_icon.py` | Inno Setup, PowerShell, Python | Studio o'rnatuvchisi (o'zbekcha), paketlash, ikonka |
| `run.py` | Python | Yagona ishga tushirish demosi (34 tekshiruv) |
| `loadtest/` + `loadtest.py` | Go + Python | Yuk sinovi (`aqload`): bayt yaxlitligi, 10 000 so'rov, 1000 ulanish, parallellik, oqish tekshiruvi |
| `kat/gen_wire_kat.py` | Python | Python referensidan KAT vektorlari (ticket, PoW, early data, frame'lar ham) |
| `scripts/interop_py.py` | Python | Python referens ↔ Rust sidecar (4 stsenariy) |
| `scripts/interop_resume.py` | Python | Resumption va PoW cross-check (8 tekshiruv) |
| `scripts/interop_std.py` | Python | Python `ssl` (OpenSSL 3.5.7) ↔ Go gateway (5 tekshiruv) |
| `scripts/cargo-msvc.ps1` | PowerShell | cargo'ni MSVC muhitida (vcvars64) ishga tushiradi |
| `backup/` | — | Python referens fayllarining o'zgartirishdan oldingi nusxalari (git'da emas) |

## Build va test

Rust: MSVC (VS 2022 Build Tools). GNU toolchain bu mashinada bog'liqliklar bilan ishlamadi.

```powershell
powershell -ExecutionPolicy Bypass -File scripts\cargo-msvc.ps1 test --workspace
powershell -ExecutionPolicy Bypass -File scripts\cargo-msvc.ps1 build --release --workspace
# uzun fuzz (1M parser, 30k handshake):
powershell -ExecutionPolicy Bypass -File scripts\cargo-msvc.ps1 test --release -p aq-core --test fuzz --test fuzz_long -- --ignored --nocapture
```

Go (Go 1.27.2, `~/tools/go`, PATH'ga qo'shilmagan — to'liq yo'l bilan):

```powershell
$go = "$env:USERPROFILE\tools\go\bin\go.exe"
cd control;    & $go test -count=1 ./...
cd ..\aether_new; & $go test -count=1 ./...
& $go test -run=^$ -fuzz=FuzzLoadAllowlist -fuzztime=60s ./internal\identity   # native fuzz
```

Python referens (`aether_q_v3\`, git'da emas): `python C:\Users\comp_2.1\Downloads\aether_q_v3\tests\test_v51.py` → 65/65.

Interop (release binary va `bin\aqctl.exe` kerak):

```powershell
$env:PYTHONIOENCODING = "utf-8"
python scripts\interop_py.py       # Python referens ↔ Rust sidecar
python scripts\interop_resume.py   # resumption + PoW
python scripts\interop_std.py      # Python ssl (OpenSSL 3.5.7) ↔ Go gateway
python run.py                      # end-to-end demo
```

## Foydalanish

AETHER-Q rejimi (Rust):

```powershell
# 1) Identity (aqctl bilan — muddat ham yoziladi)
aqctl identity new --out server --days 90      # server.key, server.key.pub, server.meta.json
aqctl identity new --out client --days 90

# 2) Server: monolit 127.0.0.1:8080 da; tunel 0.0.0.0:9443; mutual auth; PoW D=8; resumption (default)
aq-sidecar serve --listen 0.0.0.0:9443 --upstream 127.0.0.1:8080 --identity server.key `
  --require-client-auth --allow allow.txt --pow 8

# 3) Klient: mahalliy 127.0.0.1:7000 → tunel → server; --resume bilan ikkinchi ulanish resumption'da
aq-sidecar connect --listen 127.0.0.1:7000 --peer server-host:9443 --server-pub server.key.pub `
  --identity client.key --resume
```

Standart rejim (Go):

```powershell
aqctl gateway serve --listen 0.0.0.0:9444 --upstream 127.0.0.1:8080 --identity std-server.key --metrics 127.0.0.1:9100
aqctl gateway connect --listen 127.0.0.1:7001 --peer server-host:9444 --server-pub std-server.key.pub
```

Control plane:

```powershell
aqctl schedule --dir . --warn-days 14                # rotatsiya jadvali (JSON)
aqctl status --dir . --allow allow.txt               # identity, barmoq izi, allowlist, muddat, holat
aqctl identity rotate --name server --out server2 --allow allow.txt   # overlap: eski+yangi kalit
aqctl allowlist retire --allow allow.txt --pub server.key.pub         # eskisini olib tashlash
```

Monolit:

```powershell
aether_new.exe -listen 127.0.0.1:8080 -data aether_new_data.json
# GET /healthz, GET/POST /api/v1/records, GET/DELETE /api/v1/records/{id}
```

Eslatma: `connect --resume` va `serve` ning resumption'i birgalikda ishlaydi. Server resumption'ni o'chirsa
(`--no-resume`), klient ham `--resume` bilan ishlatilmasligi kerak (NST kutish). Python referens serverlari
ticket authority bilan ishga tushirilganda resumption'ni qo'llaydi.

## Holat

### AETHER-Q (Rust)

| Qism | Holat | Izoh |
|---|---|---|
| Hash/KDF/KMAC | ✅ | Python referensi bilan bayt-mos (KAT) |
| ML-KEM-768 / ML-DSA-65 | ✅ | Python ↔ Rust ikki yo'nalishda |
| KEM combiner (0x01, 0x03) | ✅ | KAT |
| Handshake (CH/SH/CKX/CA/CF/SF) | ✅ | Rust↔Rust, Python↔Rust TCP |
| Server autentifikatsiyasi + pinning | ✅ | Noto'g'ri kalit → `BAD_SIGNATURE` |
| Mutual auth + allowlist | ✅ | Ruxsatsiz klient → `BAD_CLIENT_AUTH` |
| Session resumption (ticket, NST) | ✅ | Kontekst bog'lash (AQ-05); Python bilan ikki yo'nalishda |
| PoW (HELLO_RETRY / CH_RETRY) | ✅ | Klient byudjeti (AQ-L05); Python server bilan |
| 0-RTT early data | ✅ (kutubxona) | Anti-replay, mutual auth bilan rad (S3.3c). Sidecar oqimida ishlatilmaydi (N17: faqat idempotent) |
| Transport record (ChaCha20-Poly1305) | ✅ | KAT, rekey, buzilgan/ortiqcha record → rad |
| Nol X25519 nuqta (S4/F1) | ✅ | Implicit rejection → `BAD_FINISHED`; Python referens ham tuzatilgan |
| Fuzz | ✅ | Parser 1 000 000 holat (panic 0); handshake 30 000 holat (panic 0) |

### Standart PQ-TLS (Go)

| Qism | Holat | Izoh |
|---|---|---|
| TLS 1.3 + X25519MLKEM768 | ✅ | Go 1.27.2; Python OpenSSL 3.5.7 bilan tasdiqlangan |
| ML-DSA-65 sertifikat + pinning | ✅ | CA yo'q, pinning |
| Mutual TLS + allowlist | ✅ | Go testi |
| Metrika `/metrics` | ✅ | `aqgw_connections_total`, `aqgw_bytes_total`, handshake summary, faol tunellar |

### Control plane va monolit

| Qism | Holat |
|---|---|
| `aqctl identity new / show / rotate` | ✅ (muddat meta bilan) |
| `aqctl schedule` (rotatsiya jadvali, JSON) | ✅ |
| `aqctl status` | ✅ |
| `aqctl allowlist build / retire` | ✅ |
| Aether_new monolit (REST, JSON ombor) | ✅ 4 test |
| Avtomatik rotatsiya (cron) | ❌ — buyruq bilan qo'lda; tashqi scheduler kerak |

### Ma'lum farqlar va cheklovlar

- **KMAC256 nostandart** (Python referensidagi kabi, `KNOWN_LIMITATIONS` C1). Foydalanuvchi qarori: o'zgartirilmaydi.
- **Standart rejim CA'siz.** Har bir tomon o'z-o'zidan imzolangan ML-DSA sertifikat ishlatadi, ishonch pinning orqali.
- **Avtomatik rejim tanlash yo'q** (foydalanuvchi qarori bilan shart emas): AETHER-Q va standart rejim alohida portlarda.
- **Thread per connection (Rust) / goroutine (Go).** Yuk sinovida 128 parallel ulanishgacha xatosiz; sig'im bu
  mashinada ≈700–880 yangi ulanish/s da to'yinadi (pastda). Juda ko'p parallel ulanish uchun async (tokio) kerak bo'ladi.
- **Monolit ombori — ehtimoliy tor joy.** `Aether_new` har POST/DELETE'da butun JSON faylni mutex ostida qayta yozadi.
  Yuk sinovida to'g'ridan-to'g'ri yo'l ≈2400 so'rov/s (16 parallel, keep-alive p50 7.8 ms, holbuki bitta `/healthz`
  0.5 ms). Sabab alohida o'lchanmagan, lekin yozuvlar soni oshgani sari fayl o'sadi va har yozish sekinlashadi.
- **Mustaqil audit yo'q.** Kriptografik komponentlar KAT va interop bilan tekshirildi, lekin ishlab chiqarishdan oldin tashqi audit shart.

## O'lchovlar (MEASURED, bu mashina)

Protokol (Rust release, `cargo run --release -p aq-sidecar --example bench`, oxirgi yugurish):

```
handshake, faqat protokol (in-memory)     n=300  mean=1.648 ms  p50=1.467 ms  p99=3.546 ms
handshake, TCP loopback (sidecar serve)   n=200  mean=2.349 ms  p50=2.201 ms  p99=4.240 ms
bazaviy TCP connect (handshake'siz)       n=200  mean=0.189 ms  p50=0.173 ms  p99=0.268 ms
throughput: bazaviy TCP                   693.7 MiB/s
throughput: AETHER tunel (sidecar)        286.8 MiB/s
AEAD record seal+open, 16 KiB             478.2 MiB/s
```

`run.py` (HTTP, har so'rov yangi ulanish, n=30, oxirgi yugurish; bir yugurish — p95 shovqinli):

```
to'g'ridan-to'g'ri (monolit)   p50 = 0.43 ms   p95 = 15.24 ms
AETHER-Q tunel                 p50 = 3.62 ms   p95 = 17.90 ms
standart PQ-TLS gateway        p50 = 2.64 ms   p95 =  6.11 ms
```

Fuzz (MEASURED, bu sessiya): Rust parser 1 000 000 holat (panic 0, 12 s release); handshake state 30 000 holat
(panic 0); Go native fuzz, identity parserlari (3 funksiya × 30 s) ≈ 92 000 ijro, xato yo'q.

### Yuk sinovi (MEASURED, 2026-10-17, `python loadtest.py`)

i5-10300H, 8 mantiqiy CPU, Windows 10, loopback. Generator, sidecar'lar, gateway va monolit bitta mashinada — bu
tarmoq kechikishi emas, CPU va dasturiy yo'l narxi. Hamma zanjirda mutual auth + allowlist yoqilgan. To'liq hisobot:
`loadtest-out\report.md` (har yugurishda qayta yoziladi; sinalgan binarlarning SHA-256 si bilan).

**Natija: 8/8 mezon o'tdi**, 2 daq 24 s. Jami ≈ 13 800 yangi ulanish (B 4 000 + C 4 500 + D 5 136 + A 150) va
≈ 49 600 HTTP so'rov — xato 0, bayt farqi 0.

| Bosqich | Natija |
|---|---|
| A. Bayt yaxlitligi | 3 zanjir × 50 oqim (0 B, 16 KiB chegaralari, 1 MiB, 8 MiB, tasodifiy), half-close bilan — hammasi aynan bir xil |
| B. 10 000 so'rov / zanjir | direct, AETHER-Q, AETHER-Q resumption, gateway: har biri 10 000/10 000, mazmun mos (o'zbek lotin/kirill, emoji, JSON maxsus belgilari, 0…10 000 B) |
| C. 1000 ketma-ket ulanish | hammasi xatosiz (pastdagi jadval) |
| D. Parallellik 1/8/32/128 | 5 136 ulanish, 0 xato |
| E. Oqish | sidecar thread'lari oxirida 1 ta (bo'sh holat); ≈ 13 800 ulanishdan keyin bitta ham thread qolmadi |
| F–H. Loglar, resumption, gateway | xato qatori 0; resumption zanjirida 3712/3712 tunel resumption bilan; gateway faol tunel 0 |

Ketma-ket yangi ulanish (tunel + `GET /healthz`, n=1000; PoW n=500):

| Zanjir | p50 | p99 | qo'shimcha p50 | CPU ms/ulanish (connect; serve) |
|---|---|---|---|---|
| to'g'ridan-to'g'ri | 0.51 ms | 0.59 ms | — | — |
| AETHER-Q, to'liq handshake | 4.34 ms | 7.16 ms | +3.83 ms | 2.58; 2.44 |
| AETHER-Q, resumption | 3.17 ms | 5.46 ms | +2.66 ms | 2.14; 1.31 |
| AETHER-Q, PoW D=8 | 4.56 ms | 8.06 ms | +4.05 ms | 2.81; 2.34 |
| standart PQ-TLS (gateway) | 3.64 ms | 7.24 ms | +3.12 ms | 1.98; 1.98 |

Parallellik (har ulanish yangi tunel — eng og'ir holat), ulanish/s va p99:

| Zanjir | ×1 | ×8 | ×32 | ×128 |
|---|---|---|---|---|
| AETHER-Q, to'liq | 218 (7 ms) | 694 (19 ms) | 685 (74 ms) | 702 (293 ms) |
| AETHER-Q, resumption | 309 (6 ms) | 883 (14 ms) | 881 (60 ms) | 746 (326 ms) |
| standart PQ-TLS | 232 (10 ms) | 725 (22 ms) | 860 (64 ms) | 844 (325 ms) |

Kuzatuvlar:

- **Sig'im ≈ 700–880 yangi ulanish/s** da to'yinadi (8 CPU'ni generator va monolit bilan bo'lishgan holda); undan keyin
  parallellik faqat kutishni oshiradi. Keep-alive ulanishda so'rovlar handshake'siz o'tadi (B bosqichi).
- **Resumption server CPU'sini ≈ 2 marta kamaytiradi** (2.44 → 1.31 ms), klientniki kam o'zgaradi: resumption'da server
  ML-DSA imzosini o'tkazib yuboradi, lekin mutual auth yoqilgan bo'lsa klient o'z imzosini har safar qo'yadi.
- **Windows porti cheklovi:** o'lchangan — har yopilgan ulanish ≈ 1 vaqtinchalik portni TIME_WAIT'da qoldiradi
  (diapazon 16 384 port, Windows standart TIME_WAIT ≈ 2 daqiqa). Hisoblangan (MODELED): har so'rovga yangi ulanish
  ochiladigan uzoq yuklamada barqaror chegara ≈ 16 384 / 120 s ≈ 135 ulanish/s — shuning uchun keep-alive yoki ulanishlar
  hovuzi kerak. Generator portlarni o'lchab, kerak bo'lganda kutadi (bu yugurishda jami 65 s).
- Boshlang'ich holatda Rust sidecar 4 thread ko'rsatadi: bular Windows yuklovchisining vaqtinchalik ishchi thread'lari,
  ≈30 s da chiqib ketadi (bo'sh sidecar'da tekshirildi: 1 s da 4, 35 s da 1).

## Testlar (yakuniy)

| To'plam | Soni | Holat |
|---|---|---|
| Rust birlik (`aq-core`) | 12 | ✅ |
| Rust KAT (`kat.rs` + `kat_features.rs`) | 15 | ✅ Python vektorlari bilan bayt-mos |
| Rust handshake (TCP, salbiy stsenariylar) | 8 | ✅ |
| Rust features (resumption, PoW, 0-RTT) | 8 | ✅ |
| Rust fuzz (mutatsion) | 4 | ✅ (+2 uzun, `--ignored`) |
| Go `identity` / `gateway` | 13 | ✅ |
| Go `aether_new` (monolit) | 4 | ✅ |
| Python referens (`aether_q_v3`) | 65 | ✅ |
| Interop: Python↔Rust / resumption+PoW / Python ssl↔Go | 4 + 8 + 5 | ✅ |
| `run.py` end-to-end | 34 | ✅ |
| Go `loadtest` (yuk generatori birlik testlari) | 6 | ✅ |
| Rust `aq-sidecar` runtime (to'xtatish, xato hodisalari, port band) | 6 | ✅ |
| Rust `aq-studio` (model, kalitlar, dvigatel, standart rejim `aqctl` bilan, oynasiz UI, glif qamrovi) | 27 | ✅ |
| `loadtest.py` yuk sinovi (mezonlar) | 8 | ✅ |
