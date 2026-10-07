//! Tauri qobig'i. Commandlar yupqa: validatsiya → domain/storage → DTO.
//! Biznes mantiq va pul hisobi faqat `money`/`domain` crate'larida.

#![cfg_attr(test, allow(clippy::unwrap_used, clippy::expect_used))]

mod commands;
mod dto;
mod ledger;
mod session;
mod study;

use std::{sync::Mutex, time::Duration};

use security::{KdfParams, KeyringStore};
use session::Session;
use specta_typescript::Typescript;
use tauri::Manager;
use tauri_specta::{collect_commands, Builder};

/// Har 5 soniyada harakatsizlikni tekshiradi; muddat o'tsa bazani yopadi.
fn spawn_autolock(app: tauri::AppHandle) {
    std::thread::spawn(move || loop {
        std::thread::sleep(Duration::from_secs(5));
        let state = app.state::<commands::AppSession>();
        let mut guard = state
            .lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner);
        guard.tick(commands::unix_now());
    });
}

fn specta_builder() -> Builder<tauri::Wry> {
    Builder::<tauri::Wry>::new().commands(collect_commands![
        commands::allocate_demo,
        commands::vault_state,
        commands::setup_pin,
        commands::unlock,
        commands::lock,
        commands::activity,
        ledger::home_summary,
        ledger::suggest_share,
        ledger::record_income,
        ledger::list_incomes,
        ledger::set_rule,
        ledger::set_opening_balance,
        ledger::request_withdrawal,
        ledger::confirm_withdrawal,
        ledger::cancel_withdrawal,
        ledger::list_withdrawals,
        ledger::audit_overview,
        ledger::audit_set_category,
        ledger::list_obligations,
        ledger::add_obligation,
        ledger::add_nasiya,
        ledger::pay_nasiya,
        ledger::remove_obligation,
        study::journey,
        study::chapter_detail,
        study::set_task_done,
        study::save_page,
        study::set_unlock_policy,
    ])
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
            // Har bir Windows foydalanuvchisi uchun alohida: %APPDATA%\BarakaDaftari.
            let data_dir = app.path().data_dir()?.join("BarakaDaftari");
            let store = KeyringStore::new("uz.baraka.daftari.desktop", "db-device-secret")?;
            let session = Session::new(
                &data_dir,
                store,
                KdfParams::production(),
                commands::unix_now(),
            );
            app.manage(Mutex::new(session));
            spawn_autolock(app.handle().clone());
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
