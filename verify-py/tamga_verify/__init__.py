"""TAMGA Record 0.1 mustaqil verifikatori.

Faqat Python standart kutubxonasi: SHA-256/SHA-512/SHAKE `hashlib` dan, Ed25519 (RFC 8032) va
ML-DSA-65 (FIPS 204) tekshiruvi shu paket ichida noldan yozilgan. Rust implementatsiyasi
(`tamga-core`) bilan umumiy kodi yo'q — bu ikkinchi, mustaqil hukm.

Spetsifikatsiya: `spec/TAMGA-RECORD-0.1.md`.
"""

FORMAT_VERSION = "0.1"
