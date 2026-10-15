//! Har bir command uchun ruxsat (permission) generatsiya qilinadi; ular
//! `capabilities/main.json` da aniq ro'yxat bilan beriladi (BARAKA_OILASI 3.3, 16).
const COMMANDS: &[&str] = &[
    "core_version",
    "session_status",
    "setup",
    "unlock",
    "unlock_with_recovery",
    "lock",
    "household",
    "categories",
    "record_income",
    "allocate_to_vault",
    "record_initial_balance",
    "deposit_to_vault",
    "withdraw_from_vault",
    "vault",
    "set_allocation_rule",
    "record_expense",
    "monthly_summary",
    "simulate_loan",
    "check_agreement",
    "export_loan_receipt",
];

fn main() {
    let attrs = tauri_build::Attributes::new()
        .app_manifest(tauri_build::AppManifest::new().commands(COMMANDS));
    if let Err(e) = tauri_build::try_build(attrs) {
        eprintln!("tauri-build: {e}");
        std::process::exit(1);
    }
}
