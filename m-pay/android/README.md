# M-Pay Android (M6)

Gradle loyihasi: AGP 8.13, Kotlin 2.2, Compose, minSdk 26, targetSdk 36. Arxitektura — ADR-0008.

| Modul | Turi | Vazifasi |
|---|---|---|
| `mpay-core` | Kotlin/JVM | Platformadan mustaqil yadro: `Tlv`, `Emv` (PDOL/CDOL/IAD/Track 2), `MpayScheme` (KDF, ARQC/ARPC), `CardApplet` (HCE applet mantiqi), `TerminalKernel` (PPSE → AID → GPO), `pqlink/*` (PQ Link v1 client), `MpayClient` (HTTP API). |
| `wallet-sdk` | Android library | Bank ilovasi uchun SDK: `MpayWallet` fasadi, `MpayHceService`, `AndroidDeviceKey` (Keystore/StrongBox + attestatsiya), `WalletStore` (shifrlangan profil), `CdcvmState` + `BiometricGate`. |
| `wallet-demo` | ilova | "M-Pay Hamyon" — SDK namoyishi: ulanish, karta qo'shish, OTP, LUK, biometriya, standart to'lov ilovasi, attestatsiya zanjirini eksport qilish. |
| `terminal-app` | ilova | "M-Pay Terminal" — telefon-terminal: NFC reader mode → `TerminalKernel.tap` → `POST /v1/authorizations` → server qarori ekranda. |

## Yig'ish va testlar

JDK 21 kerak (masalan Android Studio JBR):

```bash
JAVA_HOME="C:/Program Files/Android/Android Studio/jbr" ./gradlew assembleDebug
```

```bash
./gradlew :mpay-core:test
```

`mpay-core` testlari Rust bilan umumiy vektorlarni o'qiydi (`../testvectors/`: TLV, EMV KAT).
Haqiqiy `mpay-server` bilan interop: repo ildizidan `bash scripts/android-interop.sh`.
Qurilmada sinash tartibi: `docs/android-testing.md`.

## Xavfsizlik eslatmalari

* Loglarda faqat maskalangan PAN (`maskPan`) va token ID; LUK, kalit, kriptogramma yozilmaydi.
* Qurilma kaliti Android Keystore'dan chiqmaydi; profil (LUK'lar) Keystore AES-GCM kaliti bilan
  shifrlangan, `allowBackup=false`.
* **Terminal (1-faza P1.4):** `mpay-server terminal-bundle` paketi import qilinadi — server TLS
  sertifikati SHA-256 bo'yicha pinlanadi (`TlsConfig`), mTLS mijoz kaliti Android Keystore'ga
  o'tkaziladi (imzo Keystore'da), terminal API kaliti Keystore AES-GCM bilan shifrlangan; paket fayli
  o'chiriladi. "Ulanishni tekshirish" — `GET /v1/terminal/ping`. Paketsiz qo'lda rejim — oddiy HTTP,
  faqat sandbox (kalit saqlanmaydi).
* **Sandbox:** `network_security_config` cleartext HTTP'ga ruxsat beradi (emulyator va qo'lda rejim
  uchun). Hamyon so'rovlari PQ Link bilan muhrlangan; hamyon uchun TLS pinlash — P1.5.
* Release ham debug kaliti bilan imzolanadi (sandbox) — haqiqiy imzo kaliti repoga tushmaydi.
* `TODO(spec):` Play Integrity (`IntegrityProvider` hozircha stub) — 2-faza.
