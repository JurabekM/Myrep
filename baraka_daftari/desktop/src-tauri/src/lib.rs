//! Tauri qobig'i. Commandlar yupqa: validatsiya → domain/storage → DTO.
//! Biznes mantiq va pul hisobi faqat `money`/`domain` crate'larida.

#![cfg_attr(test, allow(clippy::unwrap_used, clippy::expect_used))]

mod commands;
mod dto;

use specta_typescript::Typescript;
use tauri_specta::{collect_commands, Builder};

fn specta_builder() -> Builder<tauri::Wry> {
    Builder::<tauri::Wry>::new().commands(collect_commands![commands::allocate_demo])
}

/// Ilovani ishga tushiradi.
///
/// # Panics
/// Tauri ishga tushmasa (qo'lda tuzatib bo'lmaydigan xato).
#[allow(clippy::expect_used)]
pub fn run() {
    let builder = specta_builder();

    // Debug build'da TS tiplari ui/src/bindings ga avtomatik yoziladi.
    #[cfg(debug_assertions)]
    builder
        .export(Typescript::default(), "../ui/src/bindings/index.ts")
        .expect("TS bindinglarni yozib bo'lmadi");

    tauri::Builder::default()
        .invoke_handler(builder.invoke_handler())
        .setup(move |app| {
            builder.mount_events(app);
            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("Tauri ishga tushmadi");
}

#[cfg(test)]
mod tests {
    use super::*;

    /// CI: bindinglar har doim yangilanganini tekshirish uchun faylni qayta yozadi.
    #[test]
    fn exports_typescript_bindings() {
        specta_builder()
            .export(Typescript::default(), "../ui/src/bindings/index.ts")
            .unwrap();
    }
}
