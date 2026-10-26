# ADR-0003: KeyStore, ML-DSA o'ralgan blob va dev-urug'

* Holat: qabul qilingan (2026-10-23)

## Kontekst

Kalitlar faqat HSM abstraksiyasi orqali ishlatilishi kerak. Sandbox HSM — SoftHSM2 (PKCS#11).
SoftHSM2 AES, CMAC, AES-GCM, HMAC va EdDSA'ni qo'llaydi, lekin ML-KEM/ML-DSA'ni qo'llamaydi.
Windows dev muhitida SoftHSM2 yo'q.

## Qaror

* `KeyStore` trait kalit materialini qaytarmaydi, faqat operatsiyalarni bajaradi (CMAC,
  AES-GCM seal/open, HMAC-SHA256, Ed25519 sign/public) — yorliq (label) bo'yicha.
* Backend'lar:
  * `MemoryKeyStore` — dev-urug'dan HKDF bilan deterministik kalitlar (server qayta ishga
    tushganda shifrlangan ma'lumot o'qiladi). Faqat `sandbox = true` konfiguratsiyada.
  * `Pkcs11KeyStore` — `pkcs11` feature, `cryptoki`. Kalitlar `CKA_SENSITIVE=true`,
    `CKA_EXTRACTABLE=false`, `CKA_TOKEN=true`.
* Ed25519 server kaliti HSM ichida.
* ML-DSA-65 server kaliti: 32 baytli urug' KEK bilan AES-256-GCM o'ralgan blob sifatida saqlanadi,
  faqat imzolash paytida xotirada ochiladi (`Zeroizing`).
* SoftHSM integratsion testlari: `#[ignore]` + `MPAY_PKCS11_LIB`; CI (Ubuntu) da majburiy,
  lokalda Docker konteynerida (`scripts/softhsm-test.sh`).

## Oqibatlar

* ML-DSA kaliti HSM chegarasidan tashqarida ochiladi — qoldiq risk (threat-model §5).
  PKCS#11 3.2 ML-DSA'ni qo'llaydigan HSM ulanganda `KeyStore::mldsa_sign` qo'shiladi.
* `MK_tok` dastur xotirasida hosil qilinadi va darhol tozalanadi (ADR-0004).
