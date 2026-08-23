# DES-1 — DistribOS Event Seal, wire-format v1

**Versiya:** 1 (`0x0001`) · **Sana:** 2026-08-23 · **Holat:** loyiha

> ⚠ **DES-1 AETHER-Q v5.1 spetsifikatsiyasining qismi EMAS.**
> Bu DistribOS konstruksiyasi, AETHER-Q **primitivlari ustiga** qurilgan.
> Yangi kriptografik primitiv o'ylab topilmagan, lekin kompozitsiyaning
> o'zi mustaqil auditdan **o'tmagan**. Sabab va muqobillar: `docs/adr/0001`.

## Nega kerak

AETHER-Q §8 record qatlami sessiyaviy: monotonik `seq`, yo'nalishli kalit,
tartib buzilsa fatal. MQTT pub/sub esa dublikat/tartibsiz/ko'p-qabul
qiluvchi. Hodisa **mustaqil** ochiladigan birlik bo'lishi kerak.

## Wire-format

Barcha butun sonlar **big-endian** (AETHER-Q §1.2).

```
DES1Envelope := header ‖ ciphertext ‖ signature

header (66 bayt, AAD ning bir qismi):
  offset  size  field
  0       2     version        u16   = 0x0001
  2       1     profile_id     u8    = 0x01 | 0x03   (AETHER-Q profili)
  3       1     content_type   u8    (1=EVENT_BATCH, 2=ACK, 3=SYNC_DIGEST,
                                      4=SYNC_REQUEST, 5=SNAPSHOT_MANIFEST,
                                      6=SNAPSHOT_CHUNK, 7=DEVICE_STATUS,
                                      8=REVOCATION, 9=PROTOCOL_CONTROL)
  4       4     epoch          u32   (AETHER-Q §5 epoch)
  8       8     key_id         u64   (epoch kaliti versiyasi)
  16      16    tenant_tag     [16]  = KMAC256(K_ep, "DES1/tenant", tenant_id)[:16]
  32      16    sender_dev     [16]  qurilma ID (tenant ichida opaque)
  48      12    seq            [12]  qurilma-lokal monotonik hisoblagich (LE96)
  60      6     rand           [6]   tasodifiy (nonce ajratish uchun)
  -- jami 66 bayt --

ciphertext := ChaCha20Poly1305(K_ep, nonce, plaintext, aad=header)
  nonce   = seq[0:12] XOR IV_ep      (IV_ep — epoch kalitidan ajratilgan 12B)
  plaintext = CBOR(payload)

signature := ML-DSA-65(sender_sk, "DES1/sig/v1" ‖ header ‖ SHA3-256(ciphertext))
  3309 bayt
```

### Kalit ajratish (AETHER-Q §4 combiner qoidalariga muvofiq)

```
DES1_LABEL = b"DistribOS-DES-1/AETHER-Q-v5.1/v1"

transcript = SHA3-256(profile_id ‖ DES1_LABEL ‖ tenant_id ‖ u32(epoch) ‖ u64(key_id))
PRK        = HKDF-Extract(salt=transcript, ikm=epoch_root_secret)
K_ep       = HKDF-Expand(PRK, DES1_LABEL + b"/aead-key", 32)
IV_ep      = HKDF-Expand(PRK, DES1_LABEL + b"/aead-iv", 12)
K_tag      = HKDF-Expand(PRK, DES1_LABEL + b"/tenant-tag", 32)
```

`epoch_root_secret` — 32 bayt, FAQAT autentifikatsiyalangan AETHER-Q
0x01/0x03 sessiyasi ichida tarqatiladi (ADR-0001, 1-qatlam). U hech qachon
MQTT'ga ochiq chiqmaydi.

`profile_id` va to'liq transcript har KDF'ga bind qilingan — AETHER-Q **N1**
va **S5** (downgrade himoyasi).

## Ochish (open) tartibi — fail-closed

```
1.  len(envelope) chegara tekshiruvi        -> rad
2.  version == 0x0001                       -> rad (noma'lum versiya)
3.  profile_id ∈ {0x01, 0x03}               -> rad
4.  epoch ma'lum va bekor qilinmagan        -> rad
5.  key_id uchun K_ep mavjud                -> rad (kalit yo'q)
6.  tenant_tag == kutilgan qiymat (ct_eq)   -> rad (begona tenant)
7.  sender_dev ma'lum va REVOKED EMAS       -> rad (bekor qilingan qurilma)
8.  ML-DSA-65 imzo tekshiruvi               -> rad
9.  (epoch, sender_dev, seq) replay-cache   -> rad (takror)
10. AEAD ochish                             -> rad (tag xato)
11. CBOR schema validatsiyasi               -> rad
```

**7-qadam 8-qadamdan oldin emas:** revoked qurilma tekshiruvi imzo
tekshiruvidan **oldin** turadi, chunki bekor qilingan qurilmaning imzosi
hali ham matematik jihatdan to'g'ri bo'ladi. Ikkalasi ham SHART.

Har qanday rad etish **jim** bo'ladi (log'da sabab kodi, tarmoqqa batafsil
xato **chiqmaydi** — AETHER-Q N15 oracle himoyasi).

## Replay oynasi

`(epoch, sender_dev)` juftligi bo'yicha sliding-window, kamida `2^20`
(AETHER-Q N5). Oynadan chetdagi eski `seq` — rad. Yangi epoch'da oyna
tozalanadi.

## Batch va imzo narxi

ML-DSA-65 imzosi 3309 bayt. Kichik hodisada bu ustama juda katta, shuning
uchun `EVENT_BATCH` bitta envelope ichida N ta hodisani tashiydi va
**bitta** imzo qo'yiladi. Batch ichidagi har hodisa o'z `event_id` siga ega
va alohida dedup qilinadi — ya'ni batch qisman qo'llanishi mumkin emas
(tranzaksion), lekin dedup hodisa darajasida ishlaydi.

`MQTT_MAX_PAYLOAD_BYTES` (default 256 KiB) batch hajmini cheklaydi.

## Kotlin/Python moslik

Ikkala implementatsiya `tests/interoperability/des1_kat.json` ustida
baytma-bayt bir xil natija berishi SHART. KAT `tools/gen_des1_kat.py`
tomonidan deterministik (fixed seed) generatsiya qilinadi.
