# ADR-0002. Asboblar va bog'liqliklar versiyalari

- **Holat:** QABUL QILINDI
- **Sana:** 2026-10-15
- **Bog'liq:** BARAKA_OILASI.md 3.5, OQ-T2, OQ-T3

## Qotirilgan versiyalar (Y1)
| Qism | Versiya | Qayerda qotirilgan |
|---|---|---|
| Rust | 1.97.0 (+ `thumbv8m.main-none-eabihf`) | `rust-toolchain.toml` |
| Node.js | 22 LTS | `.nvmrc`, CI |
| pnpm | 10 | `package.json#packageManager`, CI |
| Tauri | 2.12.x (`tauri-build` 2.7.x, `@tauri-apps/api` 2.12.4, CLI 2.12.3) | `Cargo.toml`, `package.json` |
| tauri-specta / specta | `=2.0.0-rc.25` (barqaror versiya hali yo'q — OQ-T2 shu ADR bilan yopiladi) | `src-tauri/Cargo.toml` |
| specta-typescript | 0.0.12 | `src-tauri/Cargo.toml` |
| React | 19.3.1 | `ui/package.json` |
| TypeScript | **6.0.3** (7.0 emas: `typescript-eslint` faqat `<6.1` ni qo'llaydi, ADR esa qat'iy ESLint talab qiladi) | `ui/package.json` |
| Vite / Vitest | 8.3.4 / 5.0.4 | `ui/package.json` |
| Tailwind CSS | 4.3.3 (`@tailwindcss/vite`) | `ui/package.json` |
| rusqlite | 0.40 (`bundled-sqlcipher-vendored-openssl`), `rusqlite_migration` 2.6 | `Cargo.toml` |
| Kripto | `argon2` 0.6, `chacha20poly1305` 0.11, `hkdf` 0.13, `sha2` 0.11, `getrandom` 0.4, `zeroize` 1.9 | `Cargo.toml` |
| Sana-vaqt | `chrono` 0.4 + `chrono-tz` 0.10 (OQ-T3 yopildi) | `Cargo.toml` |
| Flutter / Dart | **3.47.6** / 3.13 (A0) | `.fvmrc`, `apps/android/pubspec.yaml` |
| flutter_rust_bridge | **=2.13.0** (Rust crate, Dart paket va `flutter_rust_bridge_codegen` bir xil) | `core/bindings/flutter/Cargo.toml`, `pubspec.yaml` |
| Android | compileSdk / targetSdk 36, minSdk 26, NDK 28.2, AGP 9.1, Kotlin 2.4, Gradle 9.3 | `apps/android/android/` |
| cargo-ndk | 4.1.2 (Gradle `buildRustCore` vazifasi) | `apps/android/README.md`, CI |
| Riverpod / go_router / Pigeon | `flutter_riverpod` 2.6 (generatorsiz — OQ-T9), `go_router` 18, `pigeon` 26 | `pubspec.yaml` |

## Yangi bog'liqliklar va sabablari
| Bog'liqlik | Nima uchun | Muqobil | Litsenziya |
|---|---|---|---|
| `num-bigint`, `num-traits` | Amortizatsiyada `(1 + r)^n` ni aniq rational hisoblash: 14 oyda ham `i128` dan oshadi | o'z bigint implementatsiyasi (ortiqcha kod) | MIT/Apache-2.0 |
| `getrandom` | OS RNG to'g'ridan-to'g'ri (kalitlar); `rand` bu yerda ortiqcha qatlam | `rand::rngs::SysRng` | MIT/Apache-2.0 |
| `data-encoding` | Tiklash kodi uchun base32 | qo'lda base32 | MIT |
| `keyring` 4.2 | Desktop platforma siri: Credential Manager / Keychain / Secret Service | `windows` crate bilan to'g'ridan-to'g'ri DPAPI | MIT/Apache-2.0 |
| `@fontsource/noto-sans` | Shrift ilova ichida (CSP `font-src 'self'`), `unicode-range` bilan, U+02BB/U+02BC ni qamraydi | qo'lda woff2 fayllari | OFL-1.1 |

## Android (A0) — qo'shimcha
- **FRB tashqi crate'larni o'qiydi:** `rust_input: crate::api, baraka-app::dto, baraka-app::error, baraka-app::events` — DTO'lar Dart'da oddiy klass bo'ladi (opaque emas), qo'lda «mirror» yozilmaydi.
- **Generik `Answer<T>` va imzo chiziqlari** (`[u16; 2]`) FRB'da tarjima qilinmaydi: sheriklik shartnomasi (`PartnershipInput/Dto`, `SignInput`) va kelishuv tekshiruvi adapterda **JSON** (serde, desktop TS bilan bir xil shakl) orqali o'tadi. Adapterda faqat (de)serializatsiya.
- **`hash_code` maydoni** Dart'dagi `Object.hashCode` bilan to'qnashadi: Rust'da `chain_code`, serde nomi `hashCode` (desktop TS o'zgarmaydi).
- **`unsafe`:** FRB generatsiya qilgan `frb_generated.rs` uchun bindings crate'ida `unsafe_code = "deny"` va faqat shu modulga `allow`; qolgan workspace'da `forbid` saqlanadi.
- **Oltin vektorlar Dart'dan (12.1):** `run_vector` — faqat `vectors` feature bilan (host testlari), release APK'da yo'q.

## Qo'shimcha qarorlar
- **Desktop alohida Cargo workspace** (`apps/desktop/src-tauri`): Linux'da webkit tizim kutubxonalarini talab qiladi; yadro CI'si unga bog'liq bo'lmasligi kerak.
- **specta va BigInt:** `specta-typescript` `i64`/`usize` ni JS'ga eksport qilishni taqiqlaydi (aniqlik yo'qolishi). DTO'larda bp va tartib raqamlari `i32`/`u32`, pul esa doim string — bu qoida bilan mos.
- **Dev profil:** `argon2` va `blake2` debug build'da ham `opt-level = 3` — aks holda desktop KDF (64 MiB × 3) bilan PIN tekshiruvi o'nlab soniya davom etadi.
- **CI:** workflow Myrep ildizida (`.github/workflows/baraka-oilasi.yml`), `paths: baraka_oilasi/**` filtri bilan.
