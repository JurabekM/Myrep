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
* **Sandbox:** `network_security_config` barcha manzillarga cleartext HTTP'ga ruxsat beradi
  (LAN/emulyator uchun). Hamyon so'rovlari PQ Link bilan muhrlangan, lekin `terminal-app`
  `/v1/authorizations` ni **ochiq** yuboradi: terminal kaliti (Bearer) va ICC teglari (DPAN,
  ARQC) tarmoqda ko'rinadi. Ishonchsiz tarmoqda sinamang. `TODO(spec):` production — faqat
  TLS (sandbox CA ni ilovaga joylash) va build vaqtida pinlangan server barmoq izi.
* Release ham debug kaliti bilan imzolanadi (sandbox) — haqiqiy imzo kaliti repoga tushmaydi.
* `TODO(spec):` Play Integrity (`IntegrityProvider` hozircha stub), terminal kalitini
  Keystore bilan shifrlash (hozir `SharedPreferences`, sandbox).
