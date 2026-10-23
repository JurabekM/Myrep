# M-Pay Pay Sandbox — arxitektura

> Holat: **M0 qoralama**, har bosqichda yangilanadi. Oxirgi yangilanish: 2026-10-23.

## 1. Maqsad va chegaralar

Pay Sandbox — M-Pay'ning 0-fazasi: haqiqiy pulsiz, to'liq ishlaydigan demo.
Telefon (yoki dasturiy terminal) tokenni taqdim etadi → token kriptogrammasi (ARQC)
tekshiriladi → Shield risk skorini beradi → emitent emulyatori tasdiqlaydi yoki rad etadi.

Qat'iy chegaralar (qisqacha, to'liq ro'yxat: bosh `README.md`):

* faqat soxta test PAN'lar (`990000`–`990099` BIN, Luhn bo'yicha to'g'ri);
* "M-Pay Test Scheme" — o'zimizning EMV-ga o'xshash profil, real scheme spetsifikatsiyasi emas;
* sirlar faqat `KeyStore` abstraksiyasi orqali; PAN, kalit, LUK, kriptogramma logga yozilmaydi;
* dashboard yo'q — HTTP API va CLI; server tomoni bitta binar `mpay-server`;
* barcha crate'larda `#![forbid(unsafe_code)]`.

## 2. Komponentlar

```
            ┌───────────────────────── mpay-server (bitta binar, axum) ─────────────────────────┐
 telefon/   │                                                                                    │
 terminal ──┼─► /v1/pqlink/*  ──► mpay-pqlink (server) ──► sessiya (device_id, kalitlar)         │
 -sim       │                                                    │                               │
            │   /v1/tokens*   ──► mpay-vault ──► IdvDecider port ─┼─► mpay-shield (M5; hozir stub)│
            │                         │  ▲                        │                               │
            │                         │  └─ Detokenizer port ◄────┼── mpay-issuer               │
            │   /v1/authorizations ──► acquirer shlyuzi ──ISO 8583 0100──► mpay-issuer ──► 0110   │
            │                                                     └─► RiskScorer port ─► shield   │
            │                                                                                    │
            │   mpay-crypto: KeyStore (memory | PKCS#11), kalit ierarxiyasi, ARQC/ARPC, envelope │
            │   mpay-common: TLV, ISO 8583, PAN/Luhn, maskalash, konfiguratsiya, port trait'lari  │
            └────────────────────────────────────────────────────────────────────────────────────┘
                 SQLite (sandbox) / PostgreSQL (keyingi faza): faqat shifrlangan PAN, HMAC indeks
```

### Crate'lar va bog'liqliklar

```
mpay-common   ◄── hamma
mpay-crypto   ◄── pqlink, vault, issuer, terminal-sim, server
mpay-pqlink   ◄── vault, terminal-sim, server
mpay-shield   ◄── server            (faqat common'ga bog'liq)
mpay-vault    ◄── server
mpay-issuer   ◄── server            (vault/shield'ni port trait'lari orqali ko'radi)
mpay-terminal-sim ◄── e2e testlar   (loopback soft-karta + terminal yadrosi + soft-wallet)
mpay-server   ◄── e2e testlar
```

Modullar bir-birini to'g'ridan-to'g'ri chaqirmaydi: `mpay-common::ports` dagi trait'lar
(`IdvDecider`, `RiskScorer`, `Detokenizer`) orqali ulanadi, ularni faqat `mpay-server`
haqiqiy implementatsiyalarga bog'laydi (ADR-0002). Natija: graf siklsiz, M3–M4 da Shield
stub bilan ishlaydi, M5 da haqiqiy Shield boshqa kodga tegmasdan ulanadi.

## 3. Kalit ierarxiyasi

```
                         ┌──────────── HSM (KeyStore) ────────────┐
                         │                                         │
                         │  KEK (AES-256)     IMK-AC (AES-128)     │
                         │  PAN-IDX (HMAC)    SRV-ED25519          │
                         └────┬──────────────────┬─────────────────┘
                              │ AES-256-GCM wrap │ CMAC (SP 800-108 KDF)
                              ▼                  ▼
          DB: DEK_n (o'ralgan)          MK_tok = KDF(IMK, "MPAY-TOKEN-MK", DPAN‖PSN)
                │ AES-256-GCM                    │
                ▼                                ▼
          PAN shifrmatni               LUK_i = KDF(MK_tok, "MPAY-LUK", i)   ──► qurilmaga (PQ Link)
          (+ HMAC-SHA256 indeks                  │
           PAN-IDX kaliti bilan)                 ▼
                                       SK = KDF(LUK_i, "MPAY-SK-AC", ATC)
                                                 │
                                                 ▼
                                       ARQC = CMAC(SK, CDOL)[0..8]
                                       ARPC = CMAC(SK, ARQC ‖ ARC)[0..4]

          ML-DSA-65 server kaliti: urug' (32 bayt) KEK bilan o'ralgan blob sifatida saqlanadi,
          faqat imzolash paytida xotirada ochiladi (SoftHSM2 ML-DSA'ni qo'llamaydi, ADR-0003).
```

Qurilma hech qachon `MK_tok` yoki `IMK` ni ko'rmaydi: unda faqat LUK'lar bor, har biri
tranzaksiyalar soni (standart 10) va TTL (standart 24 soat) bilan cheklangan.
Batafsil KDF ta'rifi va KAT vektorlari: `docs/specs/emv-profile.md`.

## 4. Asosiy oqimlar

### 4.1 Provisioning

1. Qurilma `POST /v1/pqlink/hello` → `POST /v1/pqlink/finish`: gibrid handshake, server
   Ed25519 + ML-DSA-65 bilan imzolaydi, qurilma P-256 attestatsiya zanjiri bilan o'zini tanitadi.
2. Qurilma `POST /v1/tokens` — PQ Link bilan muhrlangan (sealed) PAN va amal muddati.
3. Vault `IdvDecider` (Shield) dan qaror oladi: GREEN → token + LUK'lar; YELLOW → OTP-simulyatsiya;
   RED → rad.
4. Javob ham muhrlangan: token profili (DPAN, PSN, muddat) va LUK'lar.

### 4.2 Tap (tranzaksiya)

1. Terminal: SELECT PPSE → SELECT AID `F04D50415901` → GET PROCESSING OPTIONS (PDOL bilan).
2. Karta (HCE / soft-karta): ATC++, LUK tanlaydi, ARQC hisoblaydi, javob qaytaradi.
3. Terminal `POST /v1/authorizations` ga EMV ma'lumotlarini yuboradi.
4. Server (acquirer shlyuzi roli) ISO 8583 `0100` yig'adi → `mpay-issuer`.
5. Issuer: `Detokenizer::lookup` → ARQC tekshiruvi → `Detokenizer::consume` (LUK hisoblagichi,
   ATC monotonligi, atomar) → `RiskScorer` → qoldiq → ARPC → `0110`.

## 5. Ma'lumotlar saqlash

* Sandbox: bitta SQLite fayl, modul jadvallari prefiks bilan (`vault_*`, `issuer_*`).
* PAN va DPAN faqat AES-256-GCM shifrmatn sifatida; qidiruv HMAC-SHA256 indeks orqali.
* Audit log: append-only (SQLite trigger'lari UPDATE/DELETE ni taqiqlaydi), har yozuv
  `hash = SHA-256(prev_hash ‖ yozuv)` bilan zanjirlangan.

## 6. Interfeyslar

* HTTP API: `docs/specs/api.md`.
* CLI: `mpay-server` (serve, init, audit verify), `mpay-tsim` (dasturiy terminal va soft-wallet).

## 7. Ochiq savollar

* `TODO(spec):` PostgreSQL'ga o'tish fazasi va migratsiya strategiyasi.
* `TODO(spec):` Ichki API uchun mTLS (operator/terminal kalitlari hozircha Bearer).
