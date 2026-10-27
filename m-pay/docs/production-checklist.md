# M-Pay: production'gacha nazorat ro'yxati

Sana: 2026-10-27. Production'gacha qolgan ishlarning **yagona ro'yxati**. Kod va hujjatlardagi har
`TODO(spec):` belgisi shu yerdagi bandga bog'langan (oxiridagi [belgilar indeksi](#belgilar-indeksi)).
`scripts/check-todo-spec.sh` (CI) indeks bilan kodni solishtiradi: yangi belgi ro'yxatga kiritilmasa
yoki yopilgan belgi indeksda qolsa — xato.

Bosqichlar `docs/roadmap.md` dagi fazalar bilan bir xil: **3-faza — pilot** (bitta bank, yopiq
foydalanuvchilar guruhi, yopiq tizim — faqat M-Pay terminali), **4-faza — production** (to'lov sxemasiga
ulanish, sertifikatsiya, ommaviy ishga tushirish).

**Belgilar**

| Ustun | Qiymatlar |
|---|---|
| Holat | ☐ ochiq · ◐ qisman (virtual muhitda tayyor, real tizim bilan sinalmagan) · ✅ bajarildi |
| Kim | **J** — jamoa (tashqi ma'lumotsiz qilsa bo'ladi) · **B** — pilot bank · **S** — to'lov sxemasi · **R** — regulyator, yurist · **A** — mustaqil auditor · **F** — loyiha egasi |
| Qachon | **P** — pilotdan oldin shart · **X** — production'dan oldin shart |

## 0. Hozirgi holat

Haqiqiy pulsiz sandbox (0-faza), xavfsizlikni kuchaytirish (1-faza) va pilot tayyorgarligi (2-faza)
**virtual muhitda** tugagan: PQ Link, Vault, EMV-ga o'xshash tap-to-pay, Shield, emitent emulyatori,
SoftHSM, PostgreSQL, ko'p instansiya, docker-compose deployment, monitoring, shifrlangan zaxira va PITR,
Play Integrity oqimi, mahsulot siyosatlari. SLA farazi (200 /s, p99 < 300 ms) bitta mashinada bajarilgan.

Qolgan ishning asosiy qismi kodda emas — **tashqi tomonlarning qarori va infratuzilmasida** (1, 2, 5,
6-bo'limlar). Jamoa hozir qila oladigan ishlar — 3-bo'lim.

## 1. To'lov sxemasi va EMV

| ID | Ish | Holat | Kim | Qachon | Manba |
|---|---|---|---|---|---|
| SX-1 | Sxema tanlovi: pilot yopiq tizimda (faqat M-Pay terminali) yoki darhol milliy/xalqaro sxemaga ulanish; shartnoma | ☐ | F, S | X | `docs/roadmap.md` 4-faza |
| SX-2 | Sxema spetsifikatsiyasi: haqiqiy BIN'lar, AID, TLV profili, IAD formati, ARPC usuli. Hozirgi "M-Pay Test Scheme" — fiktiv profil, oddiy POS uni tanimaydi | ☐ | S | X | `docs/specs/emv-profile.md` §10 |
| SX-3 | Token muddati qoidasi: hozir `min(hozir + 36 oy, karta muddati)`, UTC+5 bo'yicha, yangilash bilan (ADR-0022) — sxema qoidasi bilan solishtirish | ◐ | S | X | `crates/mpay-common/src/pan.rs`, ADR-0022 §4 |
| SX-4 | Emitentdan karta qayta chiqarilganligi xabari (token qayta qo'shishsiz yangilanadi) | ☐ | S, B | X | ADR-0022 §4 |
| SX-5 | EMV/HCE sertifikatsiyasi, sxema test kartalari va test muhiti | ☐ | S | X | `docs/roadmap.md` 4-faza |
| SX-6 | Ketma-ket CVM'siz to'lovlar chegarasi (soni/summasi), boshqa valyutalar | ☐ | S, B | X | ADR-0022 |

## 2. Bank integratsiyasi va infratuzilmasi

| ID | Ish | Holat | Kim | Qachon | Manba |
|---|---|---|---|---|---|
| BK-1 | Emitent protsessingiga ulanish (ISO 8583, bankning haqiqiy formati). Hozir avtorizatsiyani emitent emulyatori beradi | ☐ | B, J | P | `crates/mpay-issuer` |
| BK-2 | Provisioning'da karta egaligini bank tasdiqlashi (hozir emulyatordagi telefon raqami + OTP) | ◐ | B | P | ADR-0016 |
| BK-3 | HSM: modeli, PKCS#11 kutubxonasi, sessiyalar soni, uzilish xatolari; `MK_tok` HSM ichida hosil qilinishi (`CKM_*_DERIVE` yoki to'lov HSM) | ◐ | B | P | ADR-0017, `docs/threat-model.md` §5, `docs/load-report.md` §7 |
| BK-4 | Kalit marosimi: ildiz va server kalitlari, zaxira shifrlash kalitining oflayn saqlanishi | ☐ | B | P | ADR-0014, ADR-0023 |
| BK-5 | PKI: TLS va mTLS sertifikatlari bankniki, sertifikatni bekor qilish (CRL/OCSP) | ☐ | B | P | ADR-0011 |
| BK-6 | SMS shlyuzi: SMPP yoki HTTP, matn, yuboruvchi nomi, qayta yuborish chegarasi; muqobil kanal (push, call-center) | ◐ | B | P | ADR-0016, `crates/mpay-vault/src/vault.rs` |
| BK-7 | SIM-swap belgisi (operator yoki emitentdan) Shield'ga | ☐ | B | X | ADR-0016 |
| BK-8 | Navbatchilik kanali va eskalatsiya (hozir virtual `mpay-smsgw`) | ◐ | B | P | `deploy/alertmanager/alertmanager.yml` |
| BK-9 | Mahsulot siyosati qiymatlari: CVM limiti, REVIEW siyosati, karta–qurilma chegarasi, token muddati, OTP qayta yuborish (hozir faraz) | ◐ | B | P | ADR-0022, `crates/mpay-server/src/init.rs` |
| BK-10 | SLA va TPS talablari (faraz: 200 /s, p99 < 300 ms); pilot muhitida (alohida DB serveri, tarmoq HSM, alohida host'lar) yuk sinovini qayta o'lchash | ◐ | B, J | P | `docs/roadmap.md`, `docs/load-report.md` |
| BK-11 | Play Integrity: Play Console, Google Cloud loyihasi, xizmat akkaunti; Android'da `com.google.android.play:integrity`. Oqim tayyor, faqat emulyatorga qarshi sinalgan | ◐ | B, J | P | ADR-0021, `crates/mpay-integrity` |
| BK-12 | Qurilma siyosati: maxsus proshivka (`SelfSigned` + `verifiedBootKey` ro'yxati), `MEETS_VIRTUAL_INTEGRITY` | ☐ | B | P | `docs/specs/pqlink.md` §9, ADR-0021 |
| BK-13 | Zaxira: offsite joy (WAL uzluksiz), saqlash muddati, bank HSM'ining zaxira tartibi | ◐ | B, J | P | ADR-0023, `deploy/backup.sh` |
| BK-14 | Shield uchun MCC va terminal geo-koordinatalari (bankning ISO 8583 maydonlari) | ☐ | B, J | X | `docs/shield-report.md` |

## 3. Kodda yo'q — jamoa hozir qila oladi

| ID | Ish | Holat | Kim | Qachon | Manba |
|---|---|---|---|---|---|
| JM-1 | **Kliring va hisob-kitob (settlement):** kunlik yopilish, kliring fayli (sandbox formati, almashtiriladigan) | ☐ | J | P | — |
| JM-2 | **Solishtirish (reconciliation)** va tafovut hisoboti: M-Pay jurnali ↔ emitent ↔ kliring | ☐ | J | P | `crates/mpay-server/src/dedup.rs` |
| JM-3 | **Avtomatik reversal (`0400`):** `96` va javobi noma'lum (`PENDING` > 120 s) avtorizatsiyalar uchun | ☐ | J | P | `crates/mpay-server/src/dedup.rs`, ADR-0010 |
| JM-4 | **Shield yuqori mavjudligi:** holatni davriy saqlash (snapshot) va zaxira instansiya. Hozir bitta Shield roli, holat xotirada; yiqilsa to'lov to'xtamaydi, aniqlash zaiflashadi | ☐ | J | P | ADR-0019, `crates/mpay-shield/src/graph.rs` |
| JM-5 | PostgreSQL replikatsiyasi va failover, nginx zaxirasi (keepalived/VIP) — compose'da namuna | ☐ | J, B | P | ADR-0020, ADR-0023, `deploy/README.md` |
| JM-6 | Bekor qilingan server identifikatorlari ro'yxatini ilova build'iga joylash, boshqa kanal (CDN/push) | ☐ | J | P | ADR-0014 |
| JM-7 | Kotlin klienti uchun deterministik handshake test vektori (hozir faqat jonli interop) | ☐ | J | X | `docs/specs/pqlink.md` §9 |
| JM-8 | Uzoq ulanishli terminal shlyuzlari uchun ulanish umri chegarasi (L4 balanslash) | ☐ | J | X | `docs/load-report.md` §10 |
| JM-9 | Audit zanjirini bo'laklash yoki davriy muhrlash (auditor talabi bo'yicha) | ☐ | A, J | X | ADR-0018 |
| JM-10 | Nizolar (chargeback) va qo'llab-quvvatlash operatori vositalari (CLI/API) | ☐ | J | X | — |
| JM-11 | Runbook'lar va DR mashqi: instansiya, DB, HSM, Shield yiqilishi; zaxiradan tiklash vaqtini o'lchash | ◐ | J, B | P | `deploy/README.md` |
| JM-12 | Telefon raqamini maskalashda boshqa mamlakat kodlari (roaming) | ☐ | J | X | `crates/mpay-common/src/phone.rs` |

## 4. Mobil ilovalar

| ID | Ish | Holat | Kim | Qachon | Manba |
|---|---|---|---|---|---|
| MB-1 | **Ikki haqiqiy telefonda NFC tap** (P1.8). Emulyatorda virtual NFC bilan to'liq tap ✅ | ◐ | F | P | `docs/android-testing.md` §3 |
| MB-2 | Haqiqiy qurilmalar matritsasi: Android versiyalari, ishlab chiqaruvchilar, HCE ustuvorligi, biometriya | ☐ | F, J | P | — |
| MB-3 | Release imzo kaliti (repoga tushmaydi), Play Store yopiq sinov treki | ☐ | F, B | P | `android/README.md` |
| MB-4 | Haqiqiy Play Integrity Android'da (`StandardIntegrityManager`) — BK-11 dan keyin | ☐ | J | P | `android/wallet-sdk`, `docs/android-testing.md` §7 |

## 5. Xavfsizlik va audit

| ID | Ish | Holat | Kim | Qachon | Manba |
|---|---|---|---|---|---|
| AU-1 | Mustaqil pentest: HTTP API, mobil ilovalar, infratuzilma | ☐ | A | P | `docs/roadmap.md` 3-faza |
| AU-2 | PQ Link protokoli va kalit ierarxiyasining kriptografik auditi (o'zimizning protokol) | ☐ | A | P | `docs/specs/pqlink.md` |
| AU-3 | Shield'ni real ma'lumotda qayta o'qitish va chegaralarni kalibrlash (sintetik natijalar optimistik) | ☐ | B, J | X | `docs/shield-report.md` §3 |
| AU-4 | PCI DSS (token ombori, karta ma'lumoti) | ☐ | A, R | X | `docs/roadmap.md` 4-faza |
| AU-5 | Tahdid modelining qoldiq risklari: LUK server xotirasida ochiq, `memory` KeyStore faqat sandbox | ◐ | J, A | P | `docs/threat-model.md` §5 |

## 6. Regulyator va tashkiliy

| ID | Ish | Holat | Kim | Qachon | Manba |
|---|---|---|---|---|---|
| RG-1 | Markaziy bank ruxsati: to'lov tashkiloti yoki to'lov tizimi operatori — qaysi tur kerakligi va pilotga ham kerakmi (yurist aniqlaydi) | ☐ | R | P | — |
| RG-2 | Shaxsga doir ma'lumotlarni mahalliy saqlash talabi (serverlar, zaxiralar, loglar joylashuvi) | ☐ | R | P | — |
| RG-3 | Foydalanuvchi ofertasi, maxfiylik siyosati, bank bilan shartnoma (javobgarlik taqsimoti) | ☐ | R, B | P | — |
| RG-4 | PR zanjirini `main` ga birlashtirish (JurabekM/Myrep#16 → #17 → #19) | ☐ | F | P | — |

## 7. Yopilgan belgilar (2026-10-27 tozalashida)

Avvalgi bosqichlarda ochiq deb belgilangan, keyin bajarilgan ishlar. Belgilar o'chirildi yoki
`PROGRESS.md` da yopilgan deb belgilandi.

| Ish | Qayerda bajarildi |
|---|---|
| Ko'p instansiyada PQ Link sessiyalari umumiy | ADR-0019 (P2.4) |
| Production DB — PostgreSQL | ADR-0018 (P2.3) |
| Global so'rovlar chegarasi (instansiyalar bo'yicha) | ADR-0019 §4 (2026-10-26) |
| Takroriy STAN/RRN ni rad etish | ADR-0010 (P1.2) |
| `X-Forwarded-For` uchun ishonchli proksilar | 1-faza qo'shimcha ishlari |
| `terminal-app`: TLS, pinlash, kalit Keystore'da | P1.4 |
| Hamyonda server barmoq izi build vaqtida (TOFU o'rniga) | P1.5 |
| Emitent tomonidagi CVM siyosati, REVIEW siyosati, karta–qurilma chegarasi | ADR-0022 (P2.7) |
| OTP kanali (virtual SMS shlyuzi) | ADR-0016 (P2.1); haqiqiy shlyuz — BK-6 |
| HSM bilan yuk sinovi | ADR-0017 (P2.2); pilot HSM'da — BK-10 |
| Play Integrity: server tekshiruvi va SDK interfeysi | ADR-0021 (P2.6); eski `IntegrityProvider` stub'i o'chirildi |
| HTTP API fuzzing, Kotlin Jazzer | `docs/fuzz-report.md` §5 |
| LUK/ATC iste'moli va emitent bitta tranzaksiyada | ADR-0018 da ataylab rad etildi: emitent alohida tizim |
| Kalit almashtirilganda Shield tarixi | ADR-0015 (2026-10-26) |
| Token muddati UTC+5 va yangilash | ADR-0022 §4 (2026-10-26) |

## 8. Pilotga chiqish mezoni

Pilot **yopiq tizimda** (SX-1 — sxemasiz, faqat M-Pay terminali, bitta bank) boshlanishi uchun
**P** belgili barcha bandlar bajarilgan bo'lishi kerak. Qisqasi:

1. Bank tomoni: BK-1 … BK-6, BK-8 … BK-13.
2. Jamoa tomoni: JM-1 … JM-6, JM-11, MB-4.
3. Telefonlar: MB-1 … MB-3.
4. Audit: AU-1, AU-2, AU-5.
5. Huquqiy: RG-1 … RG-4.

Production (4-faza) uchun — qolgan **X** bandlar: sxema (SX-*), sertifikatsiya, PCI DSS, Shield'ni
real ma'lumotda o'qitish.

## Belgilar indeksi

`TODO(spec):` belgisi bor har fayl va u bog'langan bandlar. `scripts/check-todo-spec.sh` shu ro'yxatni
`git grep` natijasi bilan ikki tomonlama solishtiradi.

<!-- todo-index:start -->
* `android/README.md` — BK-11
* `android/wallet-sdk/src/main/kotlin/uz/mpay/wallet/sdk/IntegrityTokenProvider.kt` — BK-11, MB-4
* `crates/mpay-common/src/pan.rs` — SX-3
* `crates/mpay-common/src/phone.rs` — JM-12
* `crates/mpay-integrity/README.md` — BK-11
* `crates/mpay-integrity/src/google.rs` — BK-11
* `crates/mpay-integrity/src/lib.rs` — BK-11
* `crates/mpay-integrity/src/service_account.rs` — BK-11
* `crates/mpay-issuer/src/issuer.rs` — BK-9
* `crates/mpay-pqlink/src/attestation.rs` — BK-12
* `crates/mpay-server/src/dedup.rs` — JM-2, JM-3
* `crates/mpay-server/src/init.rs` — BK-9
* `crates/mpay-shield/src/graph.rs` — JM-4
* `crates/mpay-vault/src/model.rs` — BK-9
* `crates/mpay-vault/src/vault.rs` — BK-6
* `deploy/README.md` — BK-8, BK-13, JM-5
* `deploy/alertmanager/alertmanager.yml` — BK-8
* `deploy/backup.sh` — BK-13
* `deploy/docker-compose.yml` — BK-8
* `docs/PROGRESS.md` — tarixiy jurnal; ochiq qolganlari: SX-3, BK-5, BK-6, BK-10, BK-11, BK-14, JM-3, AU-3
* `docs/adr/0011-mtls.md` — BK-5
* `docs/adr/0014-bekor-qilish-royxati.md` — JM-6
* `docs/adr/0016-otp-kanali.md` — BK-6, BK-7
* `docs/adr/0017-hsm-sessiyalar.md` — BK-3
* `docs/adr/0018-postgresql.md` — JM-9
* `docs/adr/0019-kop-instansiya.md` — JM-4
* `docs/adr/0020-deployment.md` — JM-5, BK-8
* `docs/adr/0021-play-integrity.md` — BK-11, BK-12
* `docs/adr/0022-mahsulot-siyosatlari.md` — BK-9, SX-3, SX-4, SX-6
* `docs/adr/0023-zaxira-pitr-ogohlantirish.md` — BK-4, BK-13, JM-5
* `docs/android-testing.md` — BK-11, MB-4
* `docs/architecture.md` — BK-5
* `docs/load-report.md` — BK-3, BK-10, JM-8
* `docs/roadmap.md` — BK-9, BK-10, BK-11
* `docs/shield-report.md` — JM-4
* `docs/specs/emv-profile.md` — SX-2
* `docs/specs/pqlink.md` — BK-12, JM-7
* `docs/threat-model.md` — BK-3
<!-- todo-index:end -->
