# ADR-0008: Android — umumiy Kotlin yadrosi va BouncyCastle

* Holat: qabul qilingan (2026-10-24)

## Kontekst

M6 da uchta Android artefakti kerak: bank ilovasiga ulanadigan `wallet-sdk`, uning namoyish
ilovasi `wallet-demo` va telefon-terminal `terminal-app`. Ular bir xil protokollarni ishlatadi:
TLV, M-Pay Test Scheme applet'i, terminal yadrosi, PQ Link client va `mpay-server` HTTP API.
Rust tomonida bu mantiq allaqachon bor (`mpay-common`, `mpay-pqlink`, `mpay-terminal-sim`).

## Qaror

1. **`android/mpay-core`** — sof Kotlin/JVM moduli (Android'ga bog'liq emas): `Tlv`, `Emv`,
   `MpayScheme` (KDF/CMAC), `CardApplet`, `TerminalKernel`, `pqlink/*`, `MpayClient`.
   JVM testlari Rust bilan bir xil test vektorlarini (`testvectors/*.json`) o'qiydi va
   `scripts/android-interop.sh` haqiqiy `mpay-server` ga qarshi interop sinovini o'tkazadi.
2. **Kriptografiya — BouncyCastle 1.86** (`bcprov`): ML-KEM-768, ML-DSA-65 (kontekst bilan),
   X25519, Ed25519, ChaCha20-Poly1305, HKDF, AES-CMAC. Android platformasida bu algoritmlarning
   hammasi mavjud emas (ML-KEM/ML-DSA umuman yo'q), shuning uchun provayder ilova ichida.
3. **Qurilma kaliti — Android Keystore**: P-256, `setAttestationChallenge`, StrongBox
   mavjud bo'lsa StrongBox. Shaxsiy kalit hech qachon ilovaga chiqmaydi; imzo Keystore'da.
4. **HCE applet bitta nusxa** (`MpayWallet.applet`): `MpayHceService` va UI bir xil holatni
   (ATC, LUK, CDCVM oynasi) ko'radi. Profil Keystore AES-GCM kaliti bilan shifrlangan faylda.
5. **CDCVM**: `BiometricPrompt` (`BIOMETRIC_STRONG`) → 60 s oyna, ekran yoniq bo'lishi shart,
   bir martalik (muvaffaqiyatli GPO'dan keyin tushadi).
6. **Server ishonchi — TOFU pinlash**: birinchi ulanishda PQ Link server barmoq izi saqlanadi;
   keyin o'zgarsa ulanish rad etiladi. `TODO(spec):` bank ilovasida barmoq izi build vaqtida
   joylanishi kerak (TOFU — faqat sandbox).

## Oqibatlar

* Protokol mantiqi ikki tilda (Rust va Kotlin) — farq xavfi umumiy test vektorlari va interop
  skripti bilan yopiladi; har protokol o'zgarishida ikkala tomon ham yangilanishi shart.
* BouncyCastle APK hajmini sezilarli oshiradi (debug APK 13–15 MB; release'da R8 qisqartiradi).
* Emulyator NFC/HCE ni qo'llamaydi va uning attestatsiyasi `SOFTWARE` darajali, ildizi
  "Droid Unregistered Device CA" (Google Test LLC). Emulyator sinovi uchun alohida konfiguratsiya
  kerak (`docs/android-testing.md` §2); standart `init` siyosati — `STRONG_BOX`.

## Ko'rib chiqilgan muqobillar

* **Rust yadroni JNI orqali** (`cargo-ndk`): bitta implementatsiya, lekin NDK yig'ish zanjiri,
  ABI'lar bo'yicha `.so` va FFI chegarasida `unsafe` kerak bo'lardi (`unsafe` faqat HSM FFI
  crate'ida ruxsat — qat'iy chegara 6). Phase 0 uchun rad etildi; Phase 1 da qayta ko'riladi.
* **Conscrypt / platforma provayderi**: PQ algoritmlari yo'q.
