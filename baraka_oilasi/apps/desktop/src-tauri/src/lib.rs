//! «Baraka oilasi» desktop ilovasi (Tauri 2). Biznes mantiq yo'q: commandlar `baraka-app` ni chaqiradi.
use std::sync::Arc;
use std::time::Duration as StdDuration;

use baraka_app::{ChangeEvent, Clock, KdfParams, Session, SystemClock, UuidV7Gen};
use serde::Serialize;
use specta_typescript::Typescript;
use tauri::Manager;
use tauri_specta::{collect_commands, collect_events, Builder, Event};

mod commands;
mod secret;

/// Desktop avto-qulf vaqti (7.4).
const IDLE_LOCK_MINUTES: i64 = 5;

pub struct Desktop {
    pub session: Session,
    pub secrets: secret::SecretStore,
}

/// Yadrodagi o'zgarish — UI tegishli so'rovlarni qayta o'qiydi.
#[derive(Clone, Debug, Serialize, specta::Type, tauri_specta::Event)]
pub struct CoreChanged(pub ChangeEvent);

/// Avto-qulf ishladi — UI qulf ekraniga o'tadi, summalar ko'rinmaydi.
#[derive(Clone, Debug, Serialize, specta::Type, tauri_specta::Event)]
pub struct SessionLocked;

pub fn specta_builder() -> Builder<tauri::Wry> {
    Builder::<tauri::Wry>::new()
        .commands(collect_commands![
            commands::core_version,
            commands::session_status,
            commands::setup,
            commands::unlock,
            commands::unlock_with_recovery,
            commands::lock,
            commands::household,
            commands::categories,
            commands::record_income,
            commands::allocate_to_vault,
            commands::record_initial_balance,
            commands::deposit_to_vault,
            commands::withdraw_from_vault,
            commands::vault,
            commands::set_allocation_rule,
            commands::record_expense,
            commands::monthly_summary,
            commands::simulate_loan,
            commands::check_agreement,
            commands::export_loan_receipt,
            commands::debts_overview,
            commands::preview_borrow_check,
            commands::add_debt,
            commands::add_receivable,
            commands::record_repayment,
            commands::add_goal,
            commands::delete_goal,
            commands::issue_loan_receipt,
            commands::export_agreement_receipt,
            commands::budget_mode,
            commands::set_budget_mode,
            commands::payoff_planner,
            commands::set_debt_order,
            commands::reset_debt_order,
            commands::add_contributor,
            commands::sellable_items,
            commands::add_sellable_item,
            commands::sell_item,
            commands::ceremonies,
            commands::ceremony,
            commands::create_ceremony,
            commands::update_ceremony,
            commands::add_scenario,
            commands::update_scenario,
            commands::delete_scenario,
            commands::select_scenario,
            commands::add_ceremony_line,
            commands::delete_ceremony_line,
            commands::save_discussion,
            commands::agree_discussion,
            commands::confirm_ceremony,
            commands::reopen_ceremony,
            commands::delete_ceremony,
            commands::add_goal_contribution,
            commands::export_ceremony_estimate,
            commands::partnerships,
            commands::partnership,
            commands::readiness_gate,
            commands::create_partnership,
            commands::update_partnership,
            commands::sign_partnership,
            commands::acknowledge_not_debt,
            commands::consent_partnership,
            commands::activate_partnership,
            commands::close_partnership,
            commands::delete_partnership,
            commands::export_partnership_contract,
            commands::venture_ledger,
            commands::add_venture_entry,
            commands::venture_attachment,
            commands::venture_period_preview,
            commands::close_venture_period,
            commands::skills,
            commands::add_skill,
            commands::delete_skill,
            commands::venture_ideas,
            commands::create_venture_idea,
            commands::update_venture_idea,
            commands::delete_venture_idea,
            commands::draft_partnership_from_idea,
            commands::check_offer,
            commands::export_venture_report,
            commands::governance,
            commands::report_duty_incident,
            commands::resolve_duty_incident,
            commands::review_draft,
            commands::hold_review,
            commands::acknowledge_spike_reread,
            commands::open_partnership_dispute,
            commands::add_dispute_claim,
            commands::record_arbiter_decision,
            commands::renew_partnership,
            commands::family_agreements,
            commands::create_family_agreement,
            commands::update_family_agreement,
            commands::delete_family_agreement,
            commands::agreement_reminders,
            commands::agreements_center,
            commands::confirm_family_agreement,
            commands::export_review_protocol,
            commands::export_dispute_folder,
            commands::devices,
            commands::export_baraka,
            commands::pick_baraka_file,
            commands::inspect_baraka,
            commands::apply_baraka,
            commands::pairing_offer,
            commands::join_household,
        ])
        .events(collect_events![CoreChanged, SessionLocked])
}

/// `ui/src/bindings.ts` ni generatsiya qiladi (`cargo test export_bindings`). Qo'lda tahrirlanmaydi.
pub fn export_bindings(path: &std::path::Path) -> Result<(), String> {
    specta_builder()
        .export(
            Typescript::default().header(
                "// @generated tauri-specta tomonidan. Qo'lda tahrirlamang.\n// eslint-disable\n",
            ),
            path,
        )
        .map_err(|e| e.to_string())
}

/// Faqat debug build'da: `BARAKA_DEV_SHIFT_DAYS=N` yadro soatini N kunga siljitadi — E2E da davr
/// yopish va muddatlarni real vaqtni kutmasdan sinash uchun. Release'da e'tiborga olinmaydi.
struct ShiftedClock(chrono::Duration);

impl Clock for ShiftedClock {
    fn now(&self) -> chrono::DateTime<chrono::Utc> {
        SystemClock.now() + self.0
    }
}

fn core_clock() -> Arc<dyn Clock> {
    let days = cfg!(debug_assertions)
        .then(|| std::env::var("BARAKA_DEV_SHIFT_DAYS").ok())
        .flatten()
        .and_then(|v| v.parse::<i64>().ok());
    match days {
        Some(d) => Arc::new(ShiftedClock(chrono::Duration::days(d))),
        None => Arc::new(SystemClock),
    }
}

pub fn run() {
    let builder = specta_builder();
    let result = tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init())
        .invoke_handler(builder.invoke_handler())
        .setup(move |app| {
            builder.mount_events(app);
            let dir = app.path().app_data_dir()?;
            std::fs::create_dir_all(&dir)?;
            let session = Session::new(
                &dir,
                KdfParams::DESKTOP,
                chrono::Duration::minutes(IDLE_LOCK_MINUTES),
                core_clock(),
                Arc::new(UuidV7Gen),
            );
            app.manage(Desktop {
                secrets: secret::SecretStore::new(&dir),
                session,
            });

            let handle = app.handle().clone();
            std::thread::spawn(move || loop {
                std::thread::sleep(StdDuration::from_secs(15));
                let locked = handle.state::<Desktop>().session.lock_if_idle();
                if matches!(locked, Ok(true)) {
                    let _ = SessionLocked.emit(&handle);
                }
            });
            Ok(())
        })
        .run(tauri::generate_context!());
    if let Err(e) = result {
        eprintln!("Baraka ishga tushmadi: {e}");
        std::process::exit(1);
    }
}

#[cfg(test)]
mod tests {
    #[test]
    fn export_bindings() {
        let path = std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("../ui/src/bindings.ts");
        assert_eq!(super::export_bindings(&path), Ok(()));
    }

    /// Frontend chaqira oladigan har bir command `build.rs` ro'yxatida va `capabilities/main.json`
    /// ruxsatlarida bo'lishi shart — aks holda ilova ichida «ruxsat yo'q» xatosi chiqadi.
    #[test]
    fn every_command_is_permitted() {
        let dir = std::path::Path::new(env!("CARGO_MANIFEST_DIR"));
        let read = |p: &str| std::fs::read_to_string(dir.join(p)).unwrap_or_default();
        let bindings = read("../ui/src/bindings.ts");
        let invoked: std::collections::BTreeSet<String> = bindings
            .split("__TAURI_INVOKE(\"")
            .skip(1)
            .filter_map(|s| s.split('"').next().map(str::to_string))
            .collect();
        assert!(!invoked.is_empty());
        let build = read("build.rs");
        let caps = read("capabilities/main.json");
        for c in &invoked {
            assert!(build.contains(&format!("\"{c}\"")), "build.rs: {c}");
            let perm = format!("\"allow-{}\"", c.replace('_', "-"));
            assert!(caps.contains(&perm), "capabilities/main.json: {c}");
        }
    }
}
