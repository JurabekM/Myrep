# PQ Link v1 — post-kvant gibrid kalit kanali

> Holat: **v1 yakunlangan (M2, 2026-10-23)**. Implementatsiya: `crates/mpay-pqlink`.
> O'zgartirish faqat yangi versiya (`0x02`) bilan.

## 1. Maqsad

PQ Link — M-Pay serveri va qurilma (Wallet SDK) orasidagi xabar darajasidagi xavfsiz kanal.
U orqali Vault qurilmaga token profili va LUK'larni yetkazadi. Kanal HTTPS ustida ishlaydi
(HTTP `POST`, `Content-Type: application/x-mpay-pqlink`, ADR-0006), lekin xavfsizligi TLS'ga
bog'liq emas.

| Xususiyat | Mexanizm |
|---|---|
| Kalit almashuvi (gibrid) | X25519 + ML-KEM-768 (FIPS 203) — ikkalasidan biri buzilsa ham sir himoyalangan |
| Server autentifikatsiyasi (gibrid) | Ed25519 **va** ML-DSA-65 (FIPS 204), ikkalasi ham to'g'ri bo'lishi shart; server kaliti pinlangan |
| Kalit tasdig'i | `s_finished`, `c_finished` (HMAC-SHA256) |
| Qurilma autentifikatsiyasi | StrongBox P-256 uzoq muddatli kalit + Android Key Attestation zanjiri |
| Transport | ChaCha20-Poly1305, yo'nalish bo'yicha alohida kalit, monoton `seq`, replay himoyasi |
| Identifikator maxfiyligi | qurilma zanjiri va imzosi shifrlangan ClientFinished ichida |

## 2. Kripto to'plami

`0x01` = `PQL1_X25519MLKEM768_ED25519MLDSA65_CHACHA20POLY1305_SHA256` (yagona).

## 3. Kodlash

* Sarlavha (6 bayt): `"MPQL"` ‖ versiya `0x01` ‖ xabar turi.
* Butun sonlar big-endian. O'zgaruvchan maydonlar `u16` uzunlik prefiksi bilan.
* Parser qat'iy: har uzunlik qolgan bufer bilan solishtiriladi, ortiqcha bayt — xato.

| Tur | Xabar | Yo'nalish | HTTP |
|---|---|---|---|
| `0x01` | ClientHello | C → S | `POST /v1/pqlink/hello` so'rovi |
| `0x02` | ServerHello | S → C | o'sha javob |
| `0x03` | ClientFinished (muhrlangan) | C → S | `POST /v1/pqlink/finish` so'rovi |
| `0x04` | ServerAccept (muhrlangan) | S → C | o'sha javob |
| `0x10` | Record (muhrlangan ilova ma'lumoti) | ikki tomonga | qurilma endpointlari |

Xatolar HTTP status + JSON (`docs/specs/api.md`) bilan qaytariladi; protokolda alohida Alert xabari yo'q.

### 3.1 Maydonlar

```
ClientHello    = hdr ‖ c_random[32] ‖ n_suites(u8, 1..16) ‖ suites[n] ‖ x25519_c[32] ‖ mlkem_ek[1184]
ServerHello    = hdr ‖ s_random[32] ‖ session_id[16] ‖ suite(u8) ‖ x25519_s[32] ‖ mlkem_ct[1088]
                 ‖ server_fp[32]                                    ← "imzosiz qism" shu yergacha
                 ‖ sig_ed25519[64] ‖ sig_mldsa65[3309] ‖ s_finished[32]
Sealed         = hdr ‖ session_id[16] ‖ seq(u64) ‖ ciphertext(16..65552)   (turlar 0x03, 0x04, 0x10)

ClientFinished ichki = n_certs(u8, 1..6) ‖ { u16 len ‖ cert_der (≤ 8 KiB) }* ‖ u16 len ‖ device_sig_der (≤ 80)
                       ‖ c_finished[32]
ServerAccept ichki   = device_id[32] ‖ expires_at(i64, unix sekund)
```

Hajmlar: ClientHello 1256 bayt, ServerHello 4612 bayt.

## 4. Handshake

```
Qurilma (C)                                                  Server (S)
ClientHello ──────────────────────────────────────────────────────────►
                                  encaps(ML-KEM ek), X25519, imzo, s_finished
◄────────────────────────────────────────────────────────── ServerHello
pinlangan fp, ikkala imzo, s_finished tekshiriladi; decaps
ClientFinished(seq 0, c2s) ───────────────────────────────────────────►
                              c_finished, attestatsiya zanjiri, device_sig
◄────────────────────────────────────────────── ServerAccept(seq 0, s2c)
```

### 4.1 Kalit jadvali

```
th1 = SHA-256("MPAY-PQLINK-V1 TH1" ‖ ClientHello ‖ ServerHello[imzosiz qism])
ss  = ss_x25519 ‖ ss_mlkem                      (32 + 32 bayt)
PRK = HKDF-Extract(salt = th1, IKM = ss)         (SHA-256)
k_c2s = HKDF-Expand(PRK, "mpay pqlink v1 c2s", 32)
k_s2c = HKDF-Expand(PRK, "mpay pqlink v1 s2c", 32)
f_c   = HKDF-Expand(PRK, "mpay pqlink v1 c fin", 32)
f_s   = HKDF-Expand(PRK, "mpay pqlink v1 s fin", 32)
th2 = SHA-256("MPAY-PQLINK-V1 TH2" ‖ ClientHello ‖ ServerHello[to'liq])
```

### 4.2 Server autentifikatsiyasi

* `m_s = "MPAY-PQLINK-V1 server-sig" ‖ th1`
* `sig_ed25519 = Ed25519.Sign(sk_ed, m_s)` — kalit HSM ichida (`mpay.srv-ed25519.v1`).
* `sig_mldsa65 = ML-DSA-65.Sign(sk_mldsa, m_s, ctx = "mpay-pqlink-v1")` — hedged (tasodifiy `rnd`);
  urug' KEK bilan o'ralgan (ADR-0003).
* `s_finished = HMAC-SHA256(f_s, th1)`
* `server_fp = SHA-256(ed25519_pk ‖ mldsa65_pk)`.

Qurilma tekshirish tartibi (birinchi xatoda to'xtaydi):

1. `suite == 0x01`;
2. `server_fp` pinlangan identifikator barmoq iziga teng (constant-time) — aks holda `ServerNotPinned`;
3. Ed25519 (`verify_strict`) va ML-DSA-65 imzolari — **dekapsulyatsiyadan oldin**;
4. X25519 natijasi kontributiv (kichik tartibli nuqta emas); ML-KEM dekapsulyatsiyasi;
5. `s_finished`.

### 4.3 Qurilma autentifikatsiyasi

* `m_c = "MPAY-PQLINK-V1 device-sig" ‖ th2`
* `device_sig = ECDSA-P256-SHA256(device_key, m_c)` (DER)
* `c_finished = HMAC-SHA256(f_c, th2)`

Server tekshirish tartibi:

1. sessiya `pending` va muddati o'tmagan (60 s); `seq == 0`;
2. AEAD ochiladi (`k_c2s`); `c_finished`;
3. zanjir: har sertifikat muddati, `issuer == keyingi.subject`, ECDSA-P256-SHA256 imzolari;
   oxirgisi ishonchli ildizning o'zi yoki u imzolagan;
   **leaf'dan boshqa har bir sertifikat `basicConstraints cA = true` va KeyDescription'siz** —
   aks holda haqiqiy attestatsiya qilingan kalit (u istalgan baytni imzolay oladi) o'z ostida soxta
   leaf (soxta daraja, soxta challenge) chiqarib, zanjirni "uzaytirardi";
4. leaf'da KeyDescription (`1.3.6.1.4.1.11129.2.1.17`): `min(attestationSecurityLevel,
   keyMintSecurityLevel) ≥ siyosat` (production: StrongBox; sandbox sozlanadi);
   `hardwareEnforced.rootOfTrust` (`[704]`): `verifiedBootState = Verified` va `deviceLocked = true`
   (`[pqlink] require_verified_boot`, standart `true`; faqat emulyator sinovida `false`);
5. `device_sig` leaf ochiq kaliti bilan.

`device_id = SHA-256(leaf SubjectPublicKeyInfo DER)`. Har qanday xatoda pending sessiya o'chiriladi.

### 4.4 Efemer kalitlar

ML-KEM dekapsulyatsiya kaliti va X25519 sirlari faqat xotirada, bitta handshake uchun; ishlatilgach
`ZeroizeOnDrop` bilan tozalanadi. StrongBox ML-KEM'ni qo'llab-quvvatlamaydi — uzoq muddatli qurilma
kaliti faqat P-256 (imzo), kalit almashuvi esa efemer.

## 5. Yozuvlar

```
nonce = 0x00000000 ‖ seq(u64)
AAD   = hdr(tur bilan) ‖ session_id ‖ seq ‖ direction   (0x01 = c2s, 0x02 = s2c)
```

* Har yo'nalishning o'z kaliti va o'z `seq` hisoblagichi; `seq = 0` — handshake yozuvlari,
  ilova yozuvlari `seq = 1` dan.
* Qabul qiluvchi faqat `seq == kutilgan` ni qabul qiladi. Takror yoki tartibsiz yozuv —
  `Replay` xatosi, sessiya holati o'zgarmaydi.
* AEAD xatosi — yozuv rad etiladi, sessiya **yopilmaydi** va `seq` oshmaydi: `session_id` va `seq`
  ochiq sarlavhada, ularni ko'rgan begona tomon soxta yozuv bilan sessiyani yopib qo'ymasin.
* Bir sessiyada so'rovlar ketma-ket (HTTP so'rov → javob).

## 6. Cheklovlar (server standartlari)

| Parametr | Qiymat |
|---|---|
| O'rnatilgan sessiya umri | 15 daqiqa |
| Yakunlanmagan handshake umri | 60 soniya |
| Sessiyalar soni chegarasi | 10 000 (to'lganda muddati o'tganlar tozalanadi) |
| Yakunlanmagan handshake'lar | 2 500 — joy yo'q bo'lsa `hello` ML-KEM/ML-DSA hisoblashdan **oldin** rad |
| Yozuv shifrmatni | ≤ 64 KiB + 16 |
| Zanjir | ≤ 6 sertifikat, har biri ≤ 8 KiB |

## 7. Xatolar

| Kod (`PqLinkError`) | Vaziyat |
|---|---|
| `Malformed`, `UnexpectedMessage`, `UnsupportedSuite` | kodlash/versiya/to'plam |
| `ServerNotPinned`, `BadServerSignature`, `BadFinished`, `KeyExchange` | qurilma tomonida server rad |
| `Attestation`, `BadDeviceSignature` | server tomonida qurilma rad |
| `UnknownSession`, `Replay`, `Decrypt`, `TooManySessions` | sessiya/yozuv |

## 8. Tekshiruv

* NIST ACVP (`testvectors/acvp/`, `crates/mpay-pqlink/tests/acvp.rs`): ML-KEM-768 keyGen (10),
  encaps (10), decaps (10), ek/dk tekshiruvi (20); ML-DSA-65 keyGen (10), sigGen (20: tashqi/ichki ×
  deterministik/hedged), sigVer (30).
* `tests/handshake.rs`: to'liq handshake, replay va tartibsizlik, buzilgan yozuv, buzilgan Ed25519 /
  ML-DSA imzo / `s_finished`, pinlanmagan server, faqat bitta kalit to'g'ri bo'lgan identifikator,
  begona CA, past xavfsizlik darajasi, ko'chirilgan zanjir, ClientFinished takrori, muddatlar, limit.
* `fuzz/fuzz_targets/pqlink_decode.rs` — dekoderlar va KeyDescription.

## 9. Ochiq savollar

* `TODO(spec):` KeyDescription `attestationChallenge` ni qurilmani ro'yxatdan o'tkazish (enrollment)
  bosqichida server nonce'i bilan bog'lash (M6).
* `TODO(spec):` `verifiedBootState = SelfSigned` (foydalanuvchi kaliti bilan qulflangan maxsus
  proshivka) — pilot bank siyosati bo'yicha `verifiedBootKey` ruxsat ro'yxati bilan.
* `TODO(spec):` Server kalitini almashtirish (rotation) va bir nechta pinlangan identifikator.
* `TODO(spec):` Kotlin client uchun deterministik handshake test vektori (M6 da, tasodifiylikni
  in'ektsiya qiladigan test rejimi bilan).
