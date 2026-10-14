//! Baraka Daftari — Tauri ilovasining yadro qatlami.
//!
//! Oyna va commandlar shu yerda yig'iladi. Biznes mantiq bu yerda emas:
//! commandlar yupqa bo'ladi (DESKTOP_PROMPT.md 3.2).

mod commands;
mod dto;
mod finance;
mod finance_commands;
mod session;

use std::sync::Arc;

use security::{KdfParams, KeyringSecretStore};
use session::{AUTO_LOCK_TICK, Paths, Session};
use tauri::{App, Manager, WindowEvent};
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

/// Asosiy oyna nomi (tauri.conf.json → app.windows[0].label).
const MAIN_WINDOW: &str = "main";

/// Barcha commandlar bitta ro'yxatda: ham ilova, ham TypeScript bindinglari shu ro'yxatdan olinadi.
fn specta_builder() -> Builder<tauri::Wry> {
    Builder::<tauri::Wry>::new().commands(collect_commands![
        commands::get_app_info,
        commands::get_security_status,
        commands::setup_pin,
        commands::unlock,
        commands::lock,
        finance_commands::get_home,
        finance_commands::list_incomes_this_month,
        finance_commands::list_recent_incomes,
        finance_commands::create_income,
        finance_commands::accept_share,
        finance_commands::get_vault,
        finance_commands::respond_progression,
        finance_commands::set_share_rule,
        finance_commands::set_initial_balance,
        finance_commands::withdraw,
        finance_commands::get_audit,
        finance_commands::add_audit_expense,
        finance_commands::mark_unexplained_as_daily,
        finance_commands::finish_audit,
        finance_commands::get_whose_money,
        finance_commands::list_categories,
        finance_commands::list_obligations,
        finance_commands::add_obligation,
        finance_commands::set_obligation_active,
        finance_commands::list_debts,
        finance_commands::add_debt,
        finance_commands::pay_debt,
    ])
}

/// Ilovani ishga tushiradi. Ishga tushmasa, xatoni logga yozib, jarayon 1 kod bilan tugaydi.
pub fn run() {
    init_tracing();

    let builder = specta_builder();

    #[cfg(debug_assertions)]
    export_bindings(&builder);

    let result = tauri::Builder::default()
        .invoke_handler(builder.invoke_handler())
        .setup(|app| setup_security(app))
        .run(tauri::generate_context!());

    if let Err(err) = result {
        tracing::error!(error = %err, "ilovani ishga tushirib bo'lmadi");
        std::process::exit(1);
    }
}

/// Seansni yaratadi, oynani himoyalaydi va avto-qulflashni ulaydi.
///
/// - Relizda oyna ekran suratiga va ekran yozuvga tushmaydi (`set_content_protected`).
///   Ishlab chiqishda bu o'chiq: skrinshot bilan tekshirish uchun.
/// - Oyna fokusdan tushsa, `AutoLockPolicy` taymeri boshlanadi; vaqt o'tsa baza qulflanadi.
fn setup_security(app: &mut App) -> Result<(), Box<dyn std::error::Error>> {
    let data_dir = app.path().app_data_dir()?;
    std::fs::create_dir_all(&data_dir)?;

    let session = Arc::new(Session::new(
        Paths::in_dir(&data_dir),
        Arc::new(KeyringSecretStore::new()),
        KdfParams::RECOMMENDED,
    ));
    app.manage(Arc::clone(&session));

    let window = app
        .get_webview_window(MAIN_WINDOW)
        .ok_or("asosiy oyna topilmadi")?;

    if !cfg!(debug_assertions) {
        window.set_content_protected(true)?;
    }

    let focus_session = Arc::clone(&session);
    window.on_window_event(move |event| {
        if let WindowEvent::Focused(focused) = event {
            focus_session.focus_changed(*focused);
        }
    });

    let tick_session = Arc::clone(&session);
    std::thread::Builder::new()
        .name("avto-qulflash".to_owned())
        .spawn(move || {
            loop {
                std::thread::sleep(AUTO_LOCK_TICK);
                tick_session.enforce_auto_lock();
            }
        })?;

    Ok(())
}

/// Log darajasi: ishlab chiqishda batafsil, relizda faqat ogohlantirish va xatolar.
/// Logga summa, ism, izoh, PIN yoki kalit yozilmaydi (SPEC 6-bo'lim).
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
