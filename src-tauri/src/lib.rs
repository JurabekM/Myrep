//! Baraka Daftari — Tauri ilovasining yadro qatlami.
//!
//! Oyna va commandlar shu yerda yig'iladi. Biznes mantiq bu yerda emas:
//! commandlar yupqa bo'ladi (DESKTOP_PROMPT.md 3.2).

mod commands;

use tauri_specta::{Builder, collect_commands};

/// TypeScript bindinglari yoziladigan fayl (frontend tomonida, git'da saqlanadi).
#[cfg(any(debug_assertions, test))]
const BINDINGS_PATH: &str = concat!(
    env!("CARGO_MANIFEST_DIR"),
    "/../ui/src/bindings/bindings.ts"
);

/// Bindings fayli boshiga qo'yiladigan izoh.
#[cfg(any(debug_assertions, test))]
const BINDINGS_HEADER: &str =
    "// Bu fayl avtomatik yaratiladi (tauri-specta). Qo'lda tahrirlamang.";

/// Barcha commandlar bitta ro'yxatda: ham ilova, ham TypeScript bindinglari shu ro'yxatdan olinadi.
fn specta_builder() -> Builder<tauri::Wry> {
    Builder::<tauri::Wry>::new().commands(collect_commands![commands::get_app_info])
}

/// Ilovani ishga tushiradi. Ishga tushmasa, xatoni logga yozib, jarayon 1 kod bilan tugaydi.
pub fn run() {
    init_tracing();

    let builder = specta_builder();

    #[cfg(debug_assertions)]
    export_bindings(&builder);

    let result = tauri::Builder::default()
        .invoke_handler(builder.invoke_handler())
        .run(tauri::generate_context!());

    if let Err(err) = result {
        tracing::error!(error = %err, "ilovani ishga tushirib bo'lmadi");
        std::process::exit(1);
    }
}

/// Log darajasi: ishlab chiqishda batafsil, relizda faqat ogohlantirish va xatolar.
/// Logga summa, ism yoki izoh yozilmaydi (SPEC 6-bo'lim).
fn init_tracing() {
    let default_level = if cfg!(debug_assertions) {
        "info"
    } else {
        "warn"
    };
    let filter = tracing_subscriber::EnvFilter::try_from_default_env()
        .unwrap_or_else(|_| tracing_subscriber::EnvFilter::new(default_level));

    // Qayta chaqirilsa (masalan, testlarda) xato bo'lmasligi uchun natija e'tiborsiz qoldiriladi.
    let _ = tracing_subscriber::fmt()
        .with_env_filter(filter)
        .with_target(false)
        .try_init();
}

/// Ishlab chiqish rejimida bindinglarni yangilab turadi. Xato dasturni to'xtatmaydi.
#[cfg(debug_assertions)]
fn export_bindings(builder: &Builder<tauri::Wry>) {
    let language = specta_typescript::Typescript::new().header(BINDINGS_HEADER);
    if let Err(err) = builder.export(language, BINDINGS_PATH) {
        tracing::warn!(error = %err, "TypeScript bindinglarini yozib bo'lmadi");
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    /// CI shu testni yurgizadi: bindinglar commandlar bilan sinxron bo'lishi shart.
    /// Agar fayl o'zgarsa, `git diff --exit-code ui/src/bindings` xato beradi.
    #[test]
    fn typescript_bindinglari_yaratiladi() {
        let language = specta_typescript::Typescript::new().header(BINDINGS_HEADER);
        specta_builder()
            .export(language, BINDINGS_PATH)
            .expect("TypeScript bindinglari yozilishi kerak");
    }
}
