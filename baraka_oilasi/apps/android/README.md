# Baraka Dastur — Android ilovasi (Flutter)

Desktop bilan **bitta Rust yadro** (`core/`): pul, jurnal, xavfsizlik va barcha qoidalar yadroda;
Flutter faqat ko'rsatadi va yadroni `flutter_rust_bridge` (FRB) orqali chaqiradi
(`docs/BARAKA_OILASI.md` 3.2, 4.2–4.4).

## Tuzilma

| Papka | Mazmuni |
|---|---|
| `lib/bindings/` | **generatsiya** (FRB) — Rust `core/bindings/flutter/src/api` → Dart. Qo'lda tahrirlanmaydi |
| `lib/platform/*.g.dart`, `android/.../PlatformApi.g.kt` | **generatsiya** (Pigeon, `pigeons/platform.dart`) |
| `lib/l10n/*.arb`, `lib/app/theme/tokens.g.dart` | **generatsiya** (`cargo xtask i18n`, `cargo xtask tokens`) |
| `lib/app/` | ilova: mavzu (dark — standart), i18n, yo'nalish (`go_router`), qobiq (yon menyu, makonlar, avto-qulf) |
| `lib/core/` | yadro xizmatlari (Riverpod): sessiya, o'zgarish hodisalari, so'rovlar (`query()`), platforma siri |
| `lib/features/<bo'lim>/` | ekranlar (desktop `features/` bilan bir xil nomlar) |
| `android/` | Kotlin: `PlatformSecretStore` (Keystore), `FLAG_SECURE`, Gradle `buildRustCore` (cargo-ndk) |
| `test/` | widget testlar **haqiqiy yadro bilan** (host `.so`), oltin vektorlar Dart'dan |

## Asboblar (ADR-0002)

Flutter 3.47.6 (`.fvmrc`), Android SDK 36 + NDK 28.2, Rust 1.97 +
`aarch64-linux-android armv7-linux-androideabi`, `cargo install flutter_rust_bridge_codegen@2.13.0 cargo-ndk@4.1.2`.

## Buyruqlar

```sh
cargo xtask codegen                                        # FRB + Pigeon (git diff bo'sh bo'lishi kerak)
cargo build -p baraka-bindings-flutter --features vectors  # testlar uchun host yadro
cd apps/android
flutter analyze
flutter test                                               # widget + oqim testlari, vektorlar
BARAKA_SHOTS=1 flutter test --update-goldens               # docs/screenshots/android-*.png
flutter build apk --release                                # Rust yadro cargo-ndk bilan avtomatik yig'iladi
```

Testlar emulyatorsiz: `flutter test` Dart VM'da haqiqiy Rust yadroni (`target/debug/libbaraka_bindings_flutter.so`,
yoki `BARAKA_CORE_LIB`) yuklaydi — onboarding, qulf, yozuvlar desktop E2E'dagidek to'liq yo'ldan o'tadi.
Platforma siri testda xotirada (`MemorySecret`), qurilmada — Keystore.

## Xavfsizlik (7.2–7.6)

- Platforma siri: 32 bayt, Keystore AES-256-GCM bilan o'ralib `noBackupFilesDir` da; PIN bilan birga KEK.
- `FLAG_SECURE` butun ilovada; `allowBackup="false"`, `dataExtractionRules` — baza bulutga va boshqa qurilmaga ko'chmaydi.
- Avto-qulf: fonga o'tgandan 2 daqiqa keyin. Qulflanganda yadro kalitni `zeroize` qiladi, keshdagi summalar tozalanadi.
