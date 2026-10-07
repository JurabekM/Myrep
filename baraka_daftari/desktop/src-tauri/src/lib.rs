//! Tauri qobig'i. Commandlar yupqa: validatsiya → domain/storage → DTO.
//! Biznes mantiq va pul hisobi faqat `money`/`domain` crate'larida.

#![cfg_attr(test, allow(clippy::unwrap_used, clippy::expect_used))]

mod commands;
mod debts;
mod dto;
mod family;
mod guard;
mod ledger;
mod saving;
mod session;
mod study;
mod tray;

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

/// Tez xarajat oynasini yashiradi.
#[tauri::command]
#[specta::specta]
fn hide_quick_window(app: tauri::AppHandle) {
    tray::hide_quick(&app);
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
        family::list_members,
        family::add_member,
        family::change_member_pin,
        family::list_categories,
        family::set_necessity,
        family::add_category,
        family::set_habit,
        family::add_expenses,
        family::list_expenses,
        family::remove_expense,
        family::suggest_category,
        family::havas_report,
        family::propose_limit,
        family::consent_limit,
        family::list_treats,
        family::add_treat,
        family::set_treat_active,
        family::remove_treat,
        family::log_treat,
        family::habit_stats,
        family::export_council_pdf,
        saving::list_subscriptions,
        saving::add_subscription,
        saving::mark_subscription_used,
        saving::set_subscription_needed,
        saving::cancel_subscription,
        saving::remove_subscription,
        saving::list_envelopes,
        saving::add_envelope,
        saving::set_envelope_active,
        saving::remove_envelope,
        saving::close_envelope_week,
        saving::rescue_report,
        saving::transfer_rescue,
        saving::transfer_all_rescue,
        saving::csv_open,
        saving::csv_dry_run,
        saving::csv_import,
        guard::guard_overview,
        guard::gate_status,
        guard::set_debt_plan_declaration,
        guard::bypass_gate,
        guard::revoke_gate_bypass,
        guard::list_price_items,
        guard::add_price_item,
        guard::set_price_item,
        guard::remove_price_item,
        guard::add_price,
        guard::price_history,
        guard::remove_price,
        guard::price_book,
        guard::purchasing_power,
        debts::debt_overview,
        debts::list_debts,
        debts::debt_burden_preview,
        debts::add_debt,
        debts::pay_debt,
        debts::set_debt_early_terms,
        debts::remove_debt,
        debts::list_receivables,
        debts::add_receivable,
        debts::return_receivable,
        debts::remove_receivable,
        debts::list_goals,
        debts::add_goal,
        debts::contribute_goal,
        debts::remove_goal,
        debts::receipt_details,
        debts::save_receipt_details,
        debts::export_receipt_pdf,
        hide_quick_window,
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
        .plugin(tauri_plugin_dialog::init())
        .plugin(tray::shortcut_plugin())
        .manage(saving::ImportStore::default())
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
            tray::setup(app)?;
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
