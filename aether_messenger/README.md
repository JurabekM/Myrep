# AETHER-Q Messenger — Post-Kvant E2E Chat PoC

`aether_q/` Rust kripto-yadrosi (AUTH-AKEM + Compress-KEM ratchet + AEAD record layer)
asosida qurilgan, Signal Protocol'ga o'xshash — lekin post-kvant hybrid — Android
messenger PoC'i. Transport sifatida public MQTT broker (`broker.hivemq.com`) ishlatiladi;
xavfsizlik butunlay client-side E2E shifrlashga tayanadi — broker ishonchsiz hisoblanadi.

## Arxitektura

```
android/app/src/main/java/com/aetherq/messenger/
  crypto/     AetherCrypto.kt (UniFFI fasadi), Identity.kt (identity + EncryptedSharedPreferences),
              ContactCard.kt (QR payload), SelfTest.kt (on-device JNI tekshiruvi)
  data/       MessengerRepository.kt (MQTT+kripto+DB orkestratsiyasi), SessionManager.kt
              (ratchet holati), local/ (Room+SQLCipher: ContactEntity, MessageEntity)
  mqtt/       MqttClient.kt (HiveMQ client), MessageEnvelope.kt (binary wire format)
  ui/         onboarding/QR, contacts/ (ro'yxat + QR skan), chat/ (xabar tarixi)
```

Rust tomoni (`aether_q/crates/aether-ffi`) UniFFI orqali Kotlin'ga eksport qilingan:
`akemEncapsulate`/`akemDecapsulate`, `CompressSenderHandle`/`CompressRecipientHandle`,
`sealRecord`/`openRecord`, `deriveBytes` (ratchet seed uchun).

## Protokol oqimi

1. **Identity**: har bir qurilma birinchi ishga tushishda Ed25519 (imzo) + X25519 (statik
   DH) + ML-KEM-768 (post-kvant KEM) kalitlarini generatsiya qiladi va Android Keystore
   bilan himoyalangan `EncryptedSharedPreferences`da saqlaydi.
2. **Kontakt qo'shish**: QR-kod orqali (`userId` + uchta ochiq kalit) — markazlashgan
   directory yo'q, Signal safety-number uslubida offline almashinuv.
3. **Handshake**: birinchi xabar yuborilganda AUTH-AKEM `encapsulate` bajariladi;
   natijadagi `shared_secret`dan **deterministik** ravishda (`SHAKE-256`) Compress-KEM
   `base_seed`/`session_id` hosil qilinadi — bu qiymatlar alohida uzatilmaydi, ikkala
   tomon mustaqil hisoblab bir xil natijaga keladi.
4. **Xabar yuborish**: har bir xabar — yangi Compress-KEM ratchet qadami (yangi X25519
   ephemeral DH) + shu qadam sirridan AEAD (ChaCha20-Poly1305) shifrlash. 77-baytli
   compress-frame + record-frame bitta MQTT payload'ga qadaladi
   (`aetherq/msgr/<recipientUserId>` topic'iga).
5. **Qabul qilish**: `acceptFrame` (delta_tag + replay-himoya) → `openRecord`.

## Qurish

```sh
# 1. Rust .so fayllarini yangilash (kripto o'zgarganda)
cd aether_q
export ANDROID_NDK_HOME=".../Sdk/ndk/28.2.13676358"
cargo ndk -t arm64-v8a -t x86_64 -o ../aether_messenger/android/app/src/main/jniLibs \
  build --release -p aether-ffi
cargo build -p aether-ffi --release
./target/release/uniffi-bindgen.exe generate --library ./target/release/aether_ffi.dll \
  --language kotlin --out-dir bindings/kotlin
cp bindings/kotlin/uniffi/aether_ffi/aether_ffi.kt \
  ../aether_messenger/android/app/src/main/java/uniffi/aether_ffi/aether_ffi.kt

# 2. Android APK
cd ../aether_messenger/android
JAVA_HOME=".../jdk-17" ./gradlew assembleDebug     # -> app/build/outputs/apk/debug/app-debug.apk
JAVA_HOME=".../jdk-17" ./gradlew assembleRelease   # -> app/build/outputs/apk/release/app-release.apk
```

**Muhim**: qurish uchun **JDK 17** kerak (JDK 25'da Kotlin kompilyatori
`JavaVersion.parse("25.0.2")`da ishlamaydi — Gradle 8.9/Kotlin 2.0.21 hali JDK 25'ni
to'liq qo'llab-quvvatlamaydi). Gradle'ning o'zi JDK 25'da ishga tushadi, lekin
`compileDebugKotlin` xato beradi.

### Release signing

`app/build.gradle.kts`dagi `signingConfigs.release` — repo ildizidagi
`aetherq-release.keystore`ga ishora qiladi (`uzerp_mobile` konventsiyasiga mos, alias
`aetherq`, parol `aetherq2026` — **faqat PoC/demo uchun**, real tarqatishda alohida,
maxfiy saqlanadigan keystore va parollar bilan almashtirilishi SHART). `isMinifyEnabled
= false` — R8/JNA reflection to'qnashuvlarini oldini olish uchun ataylab o'chirilgan.

## Tekshirilgan (ushbu sessiyada, x86_64 emulyator, API 36)

- ✅ `cargo ndk` orqali `arm64-v8a` va `x86_64` uchun `.so` muvaffaqiyatli qurildi.
- ✅ `gradlew assembleDebug` — 27.5 MB debug APK muvaffaqiyatli qurildi.
- ✅ APK emulyatorga o'rnatildi va ishga tushdi — JNA/sqlcipher/aether_ffi native
  kutubxonalar muvaffaqiyatli yuklandi, ilova ishga tushishda ML-KEM-768/X25519/Ed25519
  identity kalitlarini JNI orqali generatsiya qildi (crash yo'q).
- ✅ **Self-test** (ilova ichidagi tugma): Alice/Bob identity'larini simulyatsiya qilib,
  to'liq AUTH-AKEM handshake + Compress-KEM ratchet qadami + AEAD record round-trip —
  **"MUVAFFAQIYATLI"** natija bilan JNI orqali tasdiqlandi.
- ✅ Own-QR ekrani — ZXing orqali QR-kod muvaffaqiyatli generatsiya qilindi (identity
  ochiq kalitlari bilan).
- ✅ Emulyatordan `broker.hivemq.com:8883`ga TCP ulanish ochiq (tarmoq yo'li tasdiqlangan).
- ✅ `gradlew assembleRelease` — 23.6 MB imzolangan release APK muvaffaqiyatli qurildi
  (`apksigner verify` orqali imzo tasdiqlandi), emulyatorga o'rnatildi va debug build
  bilan bir xil natijada (crashsiz) ishga tushdi.

## Ma'lum cheklovlar (PoC chegaralari)

- **Faqat matnli xabarlar** — media/fayl uzatish qo'llab-quvvatlanmaydi.
- **Ratchet holati faqat jarayon-ichida saqlanadi** — ilova qayta ishga tushganda har bir
  kontakt uchun AUTH-AKEM handshake avtomatik qayta bajariladi. Identity kalitlar
  doimiy saqlanadi, faqat hosila ratchet-seansi emas.
- **Ikki haqiqiy qurilma o'rtasidagi to'liq P2P almashinuv** ushbu sessiyada avtomatik
  tekshirilmadi (ikkinchi fizik qurilma/emulyator hisobi yo'q edi) — protokol mantig'i
  on-device self-test orqali JNI darajasida to'liq tasdiqlangan, MQTT transport qatlami
  esa tarmoq darajasida (TCP reachability) tekshirilgan.
- QR-skanerlash (kamera) oqimi kod darajasida yozilgan (ZXing `IntentIntegrator`), lekin
  emulyator kamerasi orqali interaktiv tekshirilmadi.
- Kontakt qo'shishda displey nomi avtomatik (`Kontakt-<userId prefiksi>`) beriladi —
  qo'lda nomlash UI hali yo'q.
