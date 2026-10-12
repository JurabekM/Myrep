//! TS bindinglarni (`ui/src/bindings/index.ts`) qayta yozadi.
//! CI va mahalliy: `cargo run -p baraka-desktop --bin export-bindings` (testsiz, har OS'da).
#![allow(clippy::expect_used)]

use specta_typescript::Typescript;

fn main() {
    baraka_desktop::specta_builder()
        .export(
            Typescript::default(),
            concat!(env!("CARGO_MANIFEST_DIR"), "/../ui/src/bindings/index.ts"),
        )
        .expect("TS bindinglarni yozib bo'lmadi");
}
