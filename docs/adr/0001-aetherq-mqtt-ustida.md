# ADR 0001 — AETHER-Q sessiyasi boshqaruvda, hodisalar esa alohida muhrlanadi

**Holat:** qabul qilingan · **Sana:** 2026-08-23

## Kontekst

AETHER-Q v5.1 §8 record qatlami — bu **sessiya** protokoli:

* yo'nalishli kalitlar (`K_c2s`, `K_s2c`);
* `nonce(seq) = IV_dir XOR LE96(seq)` — **qat'iy monotonik** hisoblagich (N12);
* AEAD tag xatosi **fatal**, ulanish yopiladi (N15).

MQTT esa pub/sub va **store-and-forward**: xabar dublikat bo'ladi, tartibi
almashadi, kechikadi, va bir xabarni **bir nechta** qurilma o'qishi kerak.

## Muammo

§8 record qatlamini to'g'ridan-to'g'ri MQTT ustiga qo'yib bo'lmaydi:

1. Bir record'ni faqat bitta peer, faqat bitta marta, faqat to'g'ri
   tartibda ocha oladi. Uch qurilmali mesh'da bu ishlamaydi.
2. Tartib buzilsa AEAD ochilmaydi → N15 bo'yicha sessiya yopiladi.
   Ya'ni MQTT ning normal xulqi protokolni **fatal** holatga olib keladi.
3. Har juft qurilma uchun alohida nusxa → N² trafik.
4. Bir necha kun offline qurilma qaytganda `seq` oynasi allaqachon o'tib
   ketgan bo'ladi.

## Qaror — ikki qatlam

### 1-qatlam: boshqaruv (AETHER-Q sessiyasi, o'zgartirilmagan)

Ikki qurilma o'rtasidagi **jonli** AETHER-Q 0x01/0x03 handshake +
§8 record sessiyasi. Faqat quyidagilar uchun:

* qurilmani juftlash va provisioning (QR onboarding);
* o'zaro autentifikatsiya (ML-DSA-65);
* **epoch kalitini** uzatish;
* kalit rotatsiyasi;
* qurilmani chiqarish (revocation);
* snapshot uzatish (katta, nuqta-nuqta oqim).

Bu yerda AETHER-Q spetsifikatsiyasidan **chetlanmaymiz**: MQTT shunchaki
ikkita tomon o'rtasida bayt tashiydi (`sync-requests`/`sync-responses`
kanallari, MQTT 5 Correlation Data bilan juftlanadi).

### 2-qatlam: hodisa muhri (DistribOS Event Seal, DES-1)

Har bir biznes hodisasi **mustaqil** muhrlanadi — tartibdan, sessiyadan va
boshqa hodisalardan qat'i nazar ochiladi.

```
DES-1 envelope:
  version      u16   = 0x0001
  epoch        u32          -- kalit/revocation epoch'i (AETHER-Q §5)
  tenant_tag   [16]         -- KMAC256(epoch_key, tenant_id) — opaque
  sender_dev   [16]         -- qurilma ID (tenant ichida)
  key_id       [8]          -- epoch kaliti versiyasi
  nonce        [24]         -- 12B monotonik ‖ 12B random (AETHER-Q N5)
  ciphertext   []           -- ChaCha20-Poly1305(K_ep, nonce[0:12], payload, aad)
  signature    [3309]       -- ML-DSA-65(sender_sk, H(aad ‖ ciphertext))
```

* **Maxfiylik** — epoch kaliti `K_ep` bilan AEAD. Kalit faqat 1-qatlamdagi
  autentifikatsiyalangan AETHER-Q sessiyasi ichida tarqatiladi.
* **Jo'natuvchi autentifikatsiyasi** — har hodisa **alohida** ML-DSA-65
  bilan imzolanadi. Bu guruh kalitidan kuchliroq: kalitni bilgan a'zo ham
  boshqa qurilma nomidan hodisa yasay olmaydi. Audit va
  «revoked device rad etiladi» talabi shuni majbur qiladi.
* **Replay** — `(epoch, nonce)` sliding-window cache (AETHER-Q N5/S6).
* **Tenant izolyatsiyasi** — `tenant_tag` epoch kalitiga bog'langan, ochiq
  matnda tenant nomi yo'q.
* **Downgrade** — `version`, `epoch`, `profile_id` AAD ichida, imzo ostida (S5).

`nonce` ning monotonik qismi qurilma-lokal `device_sequence` dan keladi, ya'ni
§8 dagi `seq` invarianti hodisa oqimida ham saqlanadi, lekin **qurilma
bo'yicha**, sessiya bo'yicha emas.

## HALOL OGOHLANTIRISH

DES-1 — bu **AETHER-Q v5.1 spetsifikatsiyasining qismi EMAS**. Bu DistribOS
tomonidan AETHER-Q **primitivlari ustiga** qurilgan konstruksiya
(`kdf.kmac256`, `kem`, `sig.MLDSA65`, ChaCha20-Poly1305 — hammasi
o'zgartirilmagan modullardan). Yangi kriptografik primitiv **o'ylab
topilmagan**, lekin kompozitsiya mustaqil auditdan o'tmagan.

Shu sababli:

* `docs/SECURITY.md` da alohida bo'lim sifatida yoziladi;
* README'da «AETHER-Q bilan himoyalangan» deyilganda DES-1 alohida tilga olinadi;
* DES-1 wire-format `specs/distribos-event-seal/DES-1.md` da versiyalanadi;
* Python va Kotlin implementatsiyalari umumiy KAT bilan qulflanadi.

## Muqobillar

| Variant | Nega tanlanmadi |
|---|---|
| §8 record'ni to'g'ridan MQTT'ga | Yuqoridagi 1-4 sabab — ishlamaydi |
| Faqat guruh kaliti, imzosiz (DistribOS Mesh yondashuvi) | Jo'natuvchi autentifikatsiyasi yo'q → audit va revocation buziladi |
| Har juft uchun alohida sessiya | N² trafik, snapshot/retained imkonsiz, offline qurilma tiklanmaydi |
| MQTT TLS'ga tayanish | Broker ochiq matnni ko'radi — public broker'da qabul qilib bo'lmaydi |

## Narx

ML-DSA-65 imzosi **3309 bayt** — har hodisaga. Kichik hodisa uchun bu katta
qo'shimcha. Yumshatish:

* hodisalar **batch** qilinadi: bitta DES-1 envelope ichida N ta hodisa,
  bitta imzo (`events` kanali batch'ni qo'llaydi);
* `device-status` kabi kritik bo'lmagan kanallarda imzo o'rniga KMAC256 teg
  (`ADR-0004` da hal qilinadi).
