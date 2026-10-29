# Arxitektura qarorlari (ADR)

| # | Sarlavha | Holat |
|---|---|---|
| [0001](0001-crate-tanlovi.md) | Asosiy crate'lar va versiyalar | qabul qilingan |
| [0002](0002-monolit-va-portlar.md) | Monolit binar va port trait'lari | qabul qilingan |
| [0003](0003-kalit-saqlash.md) | KeyStore: HSM, ML-DSA o'ralgan blob, dev-urug' | qabul qilingan |
| [0004](0004-kdf-va-luk.md) | Kalit hosil qilish zanjiri va LUK | qabul qilingan |
| [0005](0005-onnx-runtime.md) | ONNX runtime: tract default, ort feature | qabul qilingan |
| [0006](0006-pqlink-http.md) | PQ Link HTTP ustida xabar darajasida | qabul qilingan |
| [0007](0007-javob-kodlari.md) | Javob kodlari xaritasi | qabul qilingan |
| [0008](0008-android-kotlin-yadro.md) | Android: umumiy Kotlin yadrosi va BouncyCastle | qabul qilingan |
| [0009](0009-sqlite-yozuvchi.md) | SQLite: `BEGIN IMMEDIATE` va bitta ulanishli hovuz | qabul qilingan |
| [0010](0010-takroriy-stan.md) | Takroriy avtorizatsiya so'rovlari: idempotentlik va `94` | qabul qilingan |
| [0011](0011-mtls.md) | Ichki API uchun mTLS: sertifikat API kalitiga bog'langan | qabul qilingan |
| [0012](0012-kalit-almashtirish.md) | PQ Link server kalitini almashtirish (rotation) | qabul qilingan |
| [0013](0013-qurilma-royxati.md) | Qurilmani ro'yxatdan o'tkazish: challenge = server nonce'i | qabul qilingan |
| [0014](0014-bekor-qilish-royxati.md) | Bekor qilingan server identifikatorlari: oflayn ildiz imzosi | qabul qilingan |
| [0015](0015-qayta-attestatsiya.md) | Davriy qayta attestatsiya: qurilma kalitini almashtirish | qabul qilingan |
| [0016](0016-otp-kanali.md) | OTP kanali: emitentdagi telefonga SMS (webhook) | qabul qilingan |
| [0017](0017-hsm-sessiyalar.md) | PKCS#11 sessiyalar pool'i va uzilishdan tiklanish | qabul qilingan |
| [0018](0018-postgresql.md) | PostgreSQL: umumiy ombor, `sqlx::Any`, parallel tranzaksiyalar | qabul qilingan |
| [0019](0019-kop-instansiya.md) | Ko'p instansiya: umumiy sessiyalar, nonce'lar, Shield roli | qabul qilingan |
| [0020](0020-deployment.md) | Deployment: docker-compose, L4 balancer + PROXY protocol, metrikalar, zaxira | qabul qilingan |
| [0021](0021-play-integrity.md) | Play Integrity: provisioning'da ilova/qurilma yaxlitligi, sessiyaga bog'langan token | qabul qilingan |
| [0022](0022-mahsulot-siyosatlari.md) | Mahsulot siyosatlari: REVIEW `step_up`, CVM chegarasi (`Q2`), token muddati (`54`), karta–qurilma | qabul qilingan |
| [0023](0023-zaxira-pitr-ogohlantirish.md) | Shifrlangan zaxira (age), PITR (WAL arxivi), Alertmanager | qabul qilingan |
| [0024](0024-reversal-va-solishtirish.md) | Avtomatik reversal (`0400`/`0401`) va solishtirish: acquirer jurnali ↔ emitent | qabul qilingan |
| [0025](0025-kliring-va-hisob-kitob.md) | Kunlik kliring (fayl, emitent tasdig'i) va hisob-kitob (MDR, interchange, pozitsiyalar) | qabul qilingan |
| [0026](0026-shield-yuqori-mavjudlik.md) | Shield: DB ijarasi bilan yetakchi + zaxira, belgilar ombori snapshot'i | qabul qilingan |
| [0027](0027-postgres-replika-va-lb-zaxira.md) | PostgreSQL streaming replika, `pg` proksisi, almashinuv skriptlari; nginx zaxirasi (VRRP VIP) | qabul qilingan |
| [0028](0028-falokatdan-tiklash.md) | Falokatdan tiklash (`dr-restore.sh`, CI'dagi mashq) va navbatchi runbook'i | qabul qilingan |
| [0029](0029-bekor-qilish-royxati-manbalari.md) | Bekor qilish ro'yxati: ilova build'i + mustaqil kanal (CDN) + server, eng katta versiya | qabul qilingan |
| [0030](0030-hamyon-api.md) | Mijoz hamyoni API'si: kartalar ro'yxati, o'zim to'xtatish/yoqish/o'chirish (bank bloki ustun), tarix | qabul qilingan |

Shablon: Kontekst → Qaror → Oqibatlar → Ko'rib chiqilgan muqobillar.
