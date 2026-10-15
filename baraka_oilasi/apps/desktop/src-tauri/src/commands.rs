//! Yupqa adapter: argumentlar → `Session` / `App` → DTO. Bu yerda biznes mantiq yo'q.
use baraka_agreements::{AgreementDraft, Completeness};
use baraka_app::*;
use tauri::{AppHandle, State};
use tauri_plugin_dialog::DialogExt;
use tauri_specta::Event;

use crate::{CoreChanged, Desktop};

type R<T> = Result<T, AppError>;

/// Ochilgan ilovaning o'zgarish hodisalarini frontendga uzatadi.
fn forward_events(handle: &AppHandle, app: &App) {
    let rx = app.subscribe();
    let handle = handle.clone();
    std::thread::spawn(move || {
        for ev in rx {
            let _ = CoreChanged(ev).emit(&handle);
        }
    });
}

#[tauri::command]
#[specta::specta]
pub fn core_version() -> String {
    baraka_app::core_version().to_string()
}

#[tauri::command]
#[specta::specta]
pub async fn session_status(state: State<'_, Desktop>) -> R<SessionStatus> {
    state.session.status()
}

#[tauri::command]
#[specta::specta]
pub async fn setup(
    handle: AppHandle,
    state: State<'_, Desktop>,
    pin: String,
    input: BootstrapInput,
) -> R<SetupResult> {
    let secret = state.secrets.create()?;
    let result = state.session.setup(&secret, &pin, input)?;
    forward_events(&handle, &*state.session.app()?);
    Ok(result)
}

#[tauri::command]
#[specta::specta]
pub async fn unlock(handle: AppHandle, state: State<'_, Desktop>, pin: String) -> R<HouseholdDto> {
    let h = state.session.unlock(&state.secrets.load()?, &pin)?;
    forward_events(&handle, &*state.session.app()?);
    Ok(h)
}

#[tauri::command]
#[specta::specta]
pub async fn unlock_with_recovery(
    handle: AppHandle,
    state: State<'_, Desktop>,
    recovery_code: String,
    new_pin: String,
) -> R<HouseholdDto> {
    let h = state
        .session
        .unlock_with_recovery(&state.secrets.load()?, &recovery_code, &new_pin)?;
    forward_events(&handle, &*state.session.app()?);
    Ok(h)
}

#[tauri::command]
#[specta::specta]
pub async fn lock(state: State<'_, Desktop>) -> R<()> {
    state.session.lock()
}

#[tauri::command]
#[specta::specta]
pub async fn household(state: State<'_, Desktop>) -> R<HouseholdDto> {
    state.session.app()?.household()
}

#[tauri::command]
#[specta::specta]
pub async fn categories(state: State<'_, Desktop>, space_id: String) -> R<Vec<CategoryDto>> {
    state.session.app()?.categories(&space_id)
}

#[tauri::command]
#[specta::specta]
pub async fn record_income(
    state: State<'_, Desktop>,
    space_id: String,
    input: NewIncomeInput,
) -> R<IncomeRecordedDto> {
    state.session.app()?.record_income(&space_id, input)
}

#[tauri::command]
#[specta::specta]
pub async fn allocate_to_vault(
    state: State<'_, Desktop>,
    space_id: String,
    income_id: String,
    amount: String,
) -> R<VaultTxDto> {
    state
        .session
        .app()?
        .allocate_to_vault(&space_id, &income_id, &amount)
}

#[tauri::command]
#[specta::specta]
pub async fn record_initial_balance(
    state: State<'_, Desktop>,
    space_id: String,
    amount: String,
) -> R<VaultTxDto> {
    state
        .session
        .app()?
        .record_initial_balance(&space_id, &amount)
}

#[tauri::command]
#[specta::specta]
pub async fn deposit_to_vault(
    state: State<'_, Desktop>,
    space_id: String,
    amount: String,
    note: Option<String>,
) -> R<VaultTxDto> {
    state
        .session
        .app()?
        .deposit_to_vault(&space_id, &amount, note.as_deref())
}

/// «Kelajagim»dan pul olish: PIN qayta tasdiqlanadi va sabab majburiy (friction).
#[tauri::command]
#[specta::specta]
pub async fn withdraw_from_vault(
    state: State<'_, Desktop>,
    space_id: String,
    pin: String,
    amount: String,
    reason: String,
) -> R<VaultTxDto> {
    state.session.confirm_pin(&state.secrets.load()?, &pin)?;
    state
        .session
        .app()?
        .withdraw_from_vault(&space_id, &amount, &reason)
}

#[tauri::command]
#[specta::specta]
pub async fn vault(state: State<'_, Desktop>, space_id: String) -> R<VaultDto> {
    state.session.app()?.vault(&space_id)
}

#[tauri::command]
#[specta::specta]
pub async fn set_allocation_rule(
    state: State<'_, Desktop>,
    space_id: String,
    input: AllocationRuleInput,
) -> R<AllocationRuleDto> {
    state.session.app()?.set_allocation_rule(&space_id, input)
}

#[tauri::command]
#[specta::specta]
pub async fn record_expense(
    state: State<'_, Desktop>,
    space_id: String,
    input: NewExpenseInput,
) -> R<ExpenseDto> {
    state.session.app()?.record_expense(&space_id, input)
}

#[tauri::command]
#[specta::specta]
pub async fn monthly_summary(
    state: State<'_, Desktop>,
    space_id: String,
    date: Option<String>,
    balance_delta: Option<String>,
) -> R<MonthlySummaryDto> {
    state
        .session
        .app()?
        .monthly_summary(&space_id, date.as_deref(), balance_delta.as_deref())
}

#[tauri::command]
#[specta::specta]
pub async fn simulate_loan(
    state: State<'_, Desktop>,
    input: LoanSimulationInput,
) -> R<LoanSimulationDto> {
    state.session.app()?.simulate_loan(input)
}

#[tauri::command]
#[specta::specta]
pub async fn check_agreement(
    state: State<'_, Desktop>,
    agreement_type: String,
    draft: AgreementDraft,
) -> R<Completeness> {
    state.session.app()?.check_agreement(&agreement_type, draft)
}

/// Tilxat PDF'ini yaratib, tizimning «Saqlash» oynasi orqali saqlaydi. Fayl yo'li frontendga
/// berilmaydi va frontenddan olinmaydi (keng `fs` ruxsati kerak emas). `false` — bekor qilindi.
#[tauri::command]
#[specta::specta]
pub async fn export_loan_receipt(
    handle: AppHandle,
    state: State<'_, Desktop>,
    input: LoanReceiptInput,
) -> R<bool> {
    let pdf = state.session.app()?.render_loan_receipt(input)?;
    let picked = handle
        .dialog()
        .file()
        .add_filter("PDF", &["pdf"])
        .set_file_name("tilxat.pdf")
        .blocking_save_file();
    let Some(file) = picked else {
        return Ok(false);
    };
    let path = file
        .into_path()
        .map_err(|_| AppError::new("SAVE_PATH_INVALID"))?;
    std::fs::write(path, pdf).map_err(|_| AppError::new("IO_ERROR"))?;
    Ok(true)
}
