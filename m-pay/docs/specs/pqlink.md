# PQ Link v1 — post-kvant gibrid kalit kanali

> Holat: **M0 qoralama**, M2 da yakunlanadi (test vektorlari va xato kodlari bilan).

## 1. Maqsad

PQ Link — M-Pay serveri va qurilma (Wallet SDK) orasidagi xabar darajasidagi xavfsiz kanal.
U orqali Vault qurilmaga token profili va LUK'larni yetkazadi. Kanal HTTPS ustida ishlaydi
(transport: HTTP `POST`, `Content-Type: application/x-mpay-pqlink`), lekin uning xavfsizligi
TLS'ga bog'liq emas.

Xususiyatlar:

* **gibrid KEM**: X25519 + ML-KEM-768 — ikkalasidan biri buzilsa ham sir himoyalangan;
* **gibrid server imzosi**: Ed25519 **va** ML-DSA-65, ikkalasi ham to'g'ri bo'lishi shart;
* **qurilma autentifikatsiyasi**: StrongBox P-256 uzoq muddatli kalit + Android Key Attestation zanjiri;
* **transport**: ChaCha20-Poly1305, har yo'nalish uchun alohida kalit, monoton nonce, replay himoyasi;
* qurilma identifikatori shifrlangan holda uzatiladi (passiv kuzatuvchidan yashirin).

## 2. Kripto to'plami

`0x01` = `PQL1_X25519MLKEM768_ED25519MLDSA65_CHACHA20POLY1305_SHA256`

## 3. Kodlash

Har xabar sarlavhasi: `"MPQL"` (4 bayt) ‖ versiya `0x01` ‖ xabar turi (1 bayt).
Barcha butun sonlar big-endian. O'zgaruvchan uzunlikdagi maydonlar `u16` uzunlik prefiksi bilan.
Parser har bir uzunlikni qolgan bufer bilan solishtiradi; ortiqcha baytlar — xato.

| Tur | Xabar |
|---|---|
| `0x01` | ClientHello |
| `0x02` | ServerHello |
| `0x03` | ClientFinished |
| `0x04` | ServerAccept |
| `0x10` | Record (ilova ma'lumoti) |
| `0x7F` | Alert (shifrlanmagan xato kodi) |

## 4. Handshake

```
Qurilma (C)                                                  Server (S)
ClientHello { c_random[32], suites, x25519_c[32], mlkem_ek[1184] }
  ──────────────────────── POST /v1/pqlink/hello ───────────────────────►
                        ServerHello { s_random[32], session_id[16], suite,
                                      x25519_s[32], mlkem_ct[1088],
                                      server_fp[32], sig_ed25519[64],
                                      sig_mldsa65[3309], s_finished[32] }
  ◄──────────────────────────────────────────────────────────────────────
ClientFinished { session_id, Record_c2s(seq=0){ cert_chain, device_sig, c_finished } }
  ──────────────────────── POST /v1/pqlink/finish ──────────────────────►
                        ServerAccept { session_id, Record_s2c(seq=0){ device_id[32], expires_at } }
  ◄──────────────────────────────────────────────────────────────────────
```

### 4.1 Kalit jadvali

```
th1 = SHA-256("MPAY-PQLINK-V1 TH1" ‖ ClientHello ‖ ServerHello[imzo va s_finished'gacha])
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
* `sig_ed25519 = Ed25519.Sign(sk_ed, m_s)`
* `sig_mldsa65 = ML-DSA-65.Sign(sk_mldsa, m_s, ctx = "mpay-pqlink-v1")`
* `s_finished = HMAC-SHA256(f_s, th1)`
* `server_fp = SHA-256(ed25519_pk ‖ mldsa65_pk)` — qurilma pinlangan identifikator bilan solishtiradi.

Qurilma **ikkala** imzoni va `s_finished` ni tekshiradi; biror biri noto'g'ri — handshake bekor.

### 4.3 Qurilma autentifikatsiyasi

* `m_c = "MPAY-PQLINK-V1 device-sig" ‖ th2`
* `device_sig = ECDSA-P256-SHA256(device_key, m_c)` (DER)
* `c_finished = HMAC-SHA256(f_c, th2)`
* `cert_chain` — Android Key Attestation zanjiri (leaf birinchi).

Server tekshiradi: zanjir imzolari ishonchli ildizgacha, amal qilish muddatlari, leaf'da
KeyDescription kengaytmasi (`1.3.6.1.4.1.11129.2.1.17`) va `attestationSecurityLevel ≥` siyosat
(production: StrongBox), `device_sig`, `c_finished`.
`device_id = SHA-256(leaf SubjectPublicKeyInfo DER)`.

### 4.4 Efemer kalitlar

ML-KEM va X25519 kalitlari faqat xotirada, bitta handshake uchun; ishlatilgach `zeroize`.
StrongBox ML-KEM'ni qo'llab-quvvatlamaydi — shuning uchun uzoq muddatli qurilma kaliti
faqat P-256 (imzo), kalit almashuvi esa efemer.

## 5. Yozuvlar (Record)

```
Record = header(6) ‖ session_id[16] ‖ seq(u64) ‖ ciphertext
nonce  = 0x00000000 ‖ seq(u64)
AAD    = header ‖ session_id ‖ seq ‖ direction   (0x01 = c2s, 0x02 = s2c)
```

* Har yo'nalishning o'z kaliti va o'z `seq` hisoblagichi bor; `seq = 0` handshake yozuvlari uchun.
* Qabul qiluvchi faqat `seq == kutilgan` ni qabul qiladi: takror yoki tartibsiz yozuv rad etiladi
  (sessiya saqlanadi); AEAD xatosi — sessiya yopiladi.
* Sessiya TTL (standart 15 daqiqa), yozuv hajmi ≤ 64 KiB.

## 6. Ochiq savollar

* `TODO(spec):` KeyDescription `attestationChallenge` — qurilmani ro'yxatdan o'tkazish (enrollment)
  bosqichida server nonce'i bilan bog'lash (M6).
* `TODO(spec):` Google'ning haqiqiy attestatsiya ildizlari (RSA-4096, P-384) — M6 da qo'shiladi;
  M2 da faqat P-256/ECDSA-SHA256 zanjirlari.
* `TODO(spec):` Server kalitini almashtirish (rotation) va bir nechta pinlangan identifikator.
