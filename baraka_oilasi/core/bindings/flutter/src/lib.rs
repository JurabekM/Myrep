//! Android adapteri (`docs/BARAKA_OILASI.md` 3.2, 4.2).
//!
//! `flutter_rust_bridge` v2 codegen `src/api/` dagi ochiq funksiya va metodlardan Dart API
//! yaratadi (`cargo xtask` emas, Android vazifasida `flutter_rust_bridge_codegen generate`).
//! Bu yerda biznes mantiq yo'q: hamma chaqiruv `baraka_app::Session` / `App` ga uzatiladi —
//! desktop (`src-tauri`) bilan aynan bir xil use-case'lar.
pub mod api;
