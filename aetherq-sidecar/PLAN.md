# AETHER-Q Sidecar — reja (v0.1) va yakuniy holat (2026-10-12)

Bitta monolit dasturni post-kvant xavfsiz tarmoq orqali ulash. Ilova kodi o'zgarmaydi: u localhost'ga oddiy
ulanadi, sidecar trafikni AETHER-Q orqali yuboradi.

## 1. Qaror qilingan talablar (foydalanuvchi tasdiqlagan)

- **Asosiy rejim:** AETHER-Q (o'zimizning protokol). Standart PQ-TLS rejimi — qo'shimcha.
- **Til:** Rust (data plane, protokol) + Go (control plane va mustaqil interop).
- **Muhit:** bitta aniq monolit dastur — **`Aether_new`** (foydalanuvchi nomini berdi; yangi yoziladi, `aether_new/`).
- **MVP:** 2 bosqich.
- **Avtomatik rejim tanlash (AETHER-Q ↔ standart) shart emas** — foydalanuvchi qarori.
- **KMAC nostandart qoladi** — foydalanuvchi qarori (standart SP 800-185 ga o'tish shart emas).

## 2. Qamrov

**Kiradi:** AETHER-Q tunel, standart rejim, control plane, o'lchov, salbiy testlar, interop testlar,
monolit integratsiyasi, resumption, PoW, 0-RTT (kutubxona), rotatsiya jadvali, metrika, fuzzing.

**Kirmaydi:** Kubernetes, 0x06/0x07/0x08 profillar (o'chirilgan, AQ-L01/L02), HSM/KMS, ommaviy reliz.
Mustaqil audit kirmaydi, lekin ishlab chiqarishdan oldin shart deb hujjatga yoziladi.

## 3. Arxitektura

```
 [Monolit A] <── localhost, oddiy TCP ──> [aq-sidecar A] ══ AETHER-Q (asosiy) ══> [aq-sidecar B] <── localhost ──> [Monolit B]
                                              ║                                          ║
                                              ╚══════ standart PQ-TLS (qo'shimcha) ══════╝
                                              ▲
                                              │ allowlist, identity fayllari, status
                                       [aqctl (Go) — control plane]
```

| Komponent | Til | Vazifa |
|---|---|---|
| `aq-core` | Rust | AETHER-Q protokoli: handshake, transport, kalit jadvali, identity, resumption, PoW, 0-RTT. Referens: `aether_q_v3/aether_q_v51` (Python) |
| `aq-sidecar` | Rust | Proxy: localhost ↔ tarmoq. Ikki yo'nalish, allowlist, resumption, PoW |
| `aqctl` | Go | Control plane: identity (muddat bilan), allowlist, rotatsiya jadvali, status, standart PQ-TLS gateway va `/metrics` |
| `aether_new` | Go | Monolit (REST API, JSON ombor) — sidecar orqasida |

**Rejim tanlash:** avtomatik emas. AETHER-Q — `aq-sidecar serve/connect` (alohida port); standart — `aqctl gateway`
(alohida port). Foydalanuvchi qaysi portdan ulanishni o'zi tanlaydi.

**Monolit integratsiyasi:** monolit TCP (HTTP) xizmat sifatida olinadi. Sidecar unga manzil orqali ulanadi —
ilova kodiga tegilmaydi. Konfiguratsiya: `--upstream 127.0.0.1:<port>`, `--listen <tarmoq>:<port>`.

## 4. Bosqichlar (reja)

### Bosqich 1 — AETHER-Q tunel (asosiy rejim)

| Pakit | Ish | Chiqish |
|---|---|---|
| **P0 Poydevor** | Toolchain. Kutubxona tekshiruvi (ml-kem, ml-dsa, KMAC). Referens nuqsonlari: F1 (S4 — X25519 nol nuqta), F4 (spec ↔ kod yorliqlari) | Ishlaydigan workspace, spec tuzatmasi, KAT manbasi |
| **P1 aq-core** | Transport record, kalit jadvali, handshake, resumption, identity | Python referens bilan bayt-mos KAT; Python↔Rust ikki tomonlama ulanish |
| **P2 aq-sidecar** | Proxy (ikki yo'nalish), allowlist, konfiguratsiya, toza yopish | Monolit trafigi tunel orqali o'tadi |
| **P3 Sinov va o'lchov** | Salbiy testlar, fuzzing, handshake va overhead o'lchovi | 1-bosqich hisoboti |

### Bosqich 2 — boshqaruv va standart rejim

| Pakit | Ish | Chiqish |
|---|---|---|
| **P4 aqctl (Go)** | Identity paketlari, allowlist, rotatsiya jadvali, status/metrika | Control plane ishlaydi |
| **P5 Standart rejim** | X25519MLKEM768 TLS, ML-DSA-65 sertifikat, pinning | Go gateway |
| **P6 Interop** | Python `ssl` (OpenSSL 3.5.7) va Go crypto/tls bilan ulanish | Tashqi klientlar bilan ishlaydi |
| **P7 Hisobot** | O'lchovlar, xavf reestri, ochiq masalalar, audit talablari | README.md, shu hujjat |

## 5. Qabul mezonlari va natija

O'lchov belgilari: **MEASURED** (o'lchangan), **MODELED** (hisoblangan), **ASSUMED** (taxmin).

| Mezon | Reja | Natija (2026-10-12) |
|---|---|---|
| Bayt-to'g'rilik | 10 000 so'rov echo orqali monolitga: 0 xato | ⚠️ Qisman: `run.py` da 8 CRUD tekshiruvi × 3 yo'l (to'g'ridan-to'g'ri, AETHER-Q, standart) — 0 xato. 10 000 so'rov yuklama sinovi **bajarilmadi** |
| Handshake vaqti | 1000 ulanish: p50/p99, klassik TCP bilan solishtirish | ⚠️ Qisman: TCP loopback n=200 (p50 2.20 ms, p99 4.24 ms); plain TCP connect p50 0.17 ms. 1000 ulanish o'lchanmadi |
| Overhead | Kichik va katta xabarlar uchun latency va throughput | ✅ MEASURED: throughput plain 693.7 vs tunel 286.8 MiB/s; AEAD 478 MiB/s |
| Salbiy testlar | Downgrade, replay, noto'g'ri identity, oversize, kesilgan xabar: 100% rad | ⚠️ Qisman: replay (0-RTT), noto'g'ri pin, ruxsatsiz klient, buzilgan record, kesilgan/ortiqcha bayt — testlar bor. Downgrade uchun alohida test yo'q |
| Cross-impl | Python↔Rust handshake 100%; KAT bayt-mos | ✅ interop_py 4/4, interop_resume 8/8; KAT 15/15 |
| Standart rejim | Go crypto/tls va OpenSSL 3.5 bilan ulanish | ✅ Go crypto/tls (testlar), Python `ssl` (OpenSSL 3.5.7) 5/5. `openssl s_client` ishlatilmadi |

## 6. Xavflar va cheklovlar

- **Sof Rust PQ kutubxonalari:** `ml-kem` 0.3.2 va `ml-dsa` 0.1.1 (RustCrypto) audit qilinmagan. Yechim: KAT
  bilan Python (OpenSSL) natijasiga qarshi tekshirish — o'tdi.
- **Protokol audit qilinmagan.** Sidecar AETHER-Q v5.1 pilot doirasida qoladi.
- **Standart rejimda autentifikatsiya CA'siz** — pinning orqali (ML-DSA-65 o'z-o'zidan imzolangan sertifikat).
- **Sertifikat hajmi:** ML-DSA-65 pk 1952 B, imzo 3309 B. Handshake kattalashadi (bench'da ko'rinadi).
- **Go o'rnatildi** (`~/tools/go`, PATH'ga qo'shilmagan — to'liq yo'l bilan ishlatiladi).
- **Windows:** `rust-toolchain.toml` MSVC'ni pin qiladi (GNU'da `getrandom` 0.4 va `-lgcc_eh` muammosi).
- **Scope creep:** Kubernetes, qo'shimcha profillar, UI — bu rejaga kirmaydi.

## 7. Savollar — javoblar

1. **Monolit dastur:** `Aether_new` (yangi yoziladi, `aether_new/`, REST, `127.0.0.1:8080`). ✅ Javob berilgan.
2. **Go o'rnatish ruxsati:** ✅ berilgan; go.dev zip, `~/tools/go`, PATH o'zgarmadi.
3. **Standart rejim autentifikatsiyasi:** foydalanuvchi aniq javob bermadi. Men **ML-DSA-65** sertifikatni
   tanladim (Go stdlib ML-DSA x509'ni qo'llaydi, pinning bilan). Klassik ECDSA variant qo'shilmagan.
   Agar kerak bo'lsa, alohida qaror bilan qo'shiladi.

## 8. Ish tartibi

- Har bosqich oxirida hisobot (o'lchovlar belgilar bilan).
- Kod inglizcha, izohlar va hujjat o'zbekcha (loyiha konvensiyasi).
- Commit faqat so'ralganda. Loyiha shu worktree ichida.
- Referens (`aether_q_v3`) git emas — o'zgartirishdan oldin nusxa olinadi (`backup/`).

## 9. Yakuniy holat (2026-10-12)

**Reja paketlari: P0–P7 va monolit bajarildi.** Qabul mezonlarining bir qismi qisman (§5: 10 000 so'rov va 1000
ulanish yuk sinovi bajarilmadi). Ishlab chiqarishga tayyor emas: audit yo'q. Batafsil va o'lchovlar: [README.md](README.md).

| Paket | Holat |
|---|---|
| P0 Poydevor | ✅ MSVC toolchain, kutubxona tekshiruvi, KAT manbasi. F1 (Python + Rust, ruxsat berilgan), F2 (runner), F4 (spec), F5 (preferens) |
| P1 aq-core | ✅ handshake, transport, identity, **resumption** (ticket, kontekst bog'lash), **PoW** (HELLO_RETRY, byudjet), **0-RTT** (kutubxona). Testlar: birlik 12, KAT 15, handshake 8, features 8, fuzz 4 (+2 uzun) |
| P2 aq-sidecar | ✅ `keygen`/`serve`/`connect`, mutual auth + allowlist, `--resume`, `--pow`, `--no-resume`, ikki yo'nalishli pump. ✅ Monolit integratsiyasi (`Aether_new`, `dist/aether_new.exe`) |
| P3 Sinov va o'lchov | ✅ Rust 47 (+2 uzun fuzz: 1 000 000 parser, 30 000 handshake — panic 0). Go 13 (+ monolit 4). Python referens 65/65. Interop 4 + 8 + 5. `run.py` 34/34. Go native fuzz ≈ 92 000 ijro — xato yo'q. Bench |
| P4 aqctl (Go) | ✅ `identity new/show/rotate`, `allowlist build/retire`, `schedule` (rotatsiya jadvali, JSON), `status`, metrika (gateway `/metrics`) |
| P5 Standart rejim | ✅ Go gateway: TLS 1.3, X25519MLKEM768, ML-DSA-65, pinning, mutual TLS + allowlist. ❌ Rust tomonida (qarang §10) |
| P6 Interop | ✅ Python `ssl` (OpenSSL 3.5.7) ↔ Go gateway, 5/5. Python ↔ Rust, 4/4 + 8/8 |
| P7 Hisobot | ✅ README.md (holat, o'lchovlar, testlar, ishlatish), shu hujjat |
| Monolit `Aether_new` | ✅ REST: `GET /healthz`, `GET/POST /api/v1/records`, `GET/DELETE /api/v1/records/{id}`; JSON ombor (atomik yozish); 4 test |
| Demo | ✅ `run.py`: monolit + AETHER-Q tunel + standart gateway + CRUD + resumption + latency + metrika + control plane — 34/34 |

## 10. Ochiq masalalar va cheklovlar (yakuniy)

1. **0-RTT** sidecar oqimida ishlatilmaydi (faqat kutubxona). Replay xavfi bor — faqat idempotent so'rovlar uchun.
2. **Resumption `connect`da opt-in** (`--resume`). Ticket authority'siz server (Python referens) NST yubormaydi —
   shunda `--resume` bilan klient kutib qoladi.
3. **Avtomatik rejim tanlash yo'q** — foydalanuvchi talab qilmadi. AETHER-Q va standart alohida portlarda.
4. **Rust tomonida standart rejim yo'q** — faqat Go gateway.
5. **Rotatsiya CLI darajasida.** `aqctl schedule` jadval beradi, lekin avtomatik yangilash (cron) yo'q.
6. **Metrika faqat Go gateway'da** (`aqgw_*`). Rust sidecar'da hisoblagich yo'q.
7. **KMAC256 nostandart** (C1) — foydalanuvchi qarori.
8. **Python referens:** F3 (0x07 K_reject) va F6–F8 hali ochiq.
9. **Yuk sinovi yo'q** (10 000 so'rov, 1000 ulanish). Har bir ulanish uchun thread/goroutine.
10. **Mustaqil audit yo'q.** Ishlab chiqarishdan oldin shart.
11. **Sinovlar faqat Windows'da** (Rust MSVC, Go 1.27.2, Python 3.14). Boshqa OS'da tekshirilmagan.
12. **Standart rejim:** ML-DSA-65 o'z-o'zidan imzolangan sertifikat, CA yo'q (pinning).
