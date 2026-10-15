//! «Baraka oilasi» desktop ilovasi (Tauri 2). Biznes mantiq yo'q: commandlar `baraka-app` ni chaqiradi.
use std::sync::Arc;
use std::time::Duration as StdDuration;

use baraka_app::{ChangeEvent, KdfParams, Session, SystemClock, UuidV7Gen};
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

pub fn run() {
    let builder = specta_builder();
    let result = tauri::Builder::default()
        .invoke_handler(builder.invoke_handler())
        .setup(move |app| {
            builder.mount_events(app);
            let dir = app.path().app_data_dir()?;
            std::fs::create_dir_all(&dir)?;
            let session = Session::new(
                &dir,
                KdfParams::DESKTOP,
                chrono::Duration::minutes(IDLE_LOCK_MINUTES),
                Arc::new(SystemClock),
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
}
