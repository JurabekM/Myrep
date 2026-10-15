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

#[tauri::command]
#[specta::specta]
pub async fn debts_overview(state: State<'_, Desktop>, space_id: String) -> R<DebtsOverviewDto> {
    state.session.app()?.debts_overview(&space_id)
}

#[tauri::command]
#[specta::specta]
pub async fn preview_borrow_check(
    state: State<'_, Desktop>,
    space_id: String,
    input: NewDebtInput,
) -> R<BorrowCheckDto> {
    state.session.app()?.preview_borrow_check(&space_id, input)
}

#[tauri::command]
#[specta::specta]
pub async fn add_debt(
    state: State<'_, Desktop>,
    space_id: String,
    input: NewDebtInput,
) -> R<DebtDto> {
    state.session.app()?.add_debt(&space_id, input)
}

#[tauri::command]
#[specta::specta]
pub async fn add_receivable(
    state: State<'_, Desktop>,
    space_id: String,
    input: NewReceivableInput,
) -> R<ReceivableDto> {
    state.session.app()?.add_receivable(&space_id, input)
}

#[tauri::command]
#[specta::specta]
pub async fn record_repayment(
    state: State<'_, Desktop>,
    space_id: String,
    owner_type: String,
    id: String,
    input: RepaymentInput,
) -> R<RepaymentResultDto> {
    state
        .session
        .app()?
        .record_repayment(&space_id, &owner_type, &id, input)
}

#[tauri::command]
#[specta::specta]
pub async fn add_goal(
    state: State<'_, Desktop>,
    space_id: String,
    input: NewGoalInput,
) -> R<GoalDto> {
    state.session.app()?.add_goal(&space_id, input)
}

#[tauri::command]
#[specta::specta]
pub async fn delete_goal(state: State<'_, Desktop>, space_id: String, goal_id: String) -> R<()> {
    state.session.app()?.delete_goal(&space_id, &goal_id)
}

#[tauri::command]
#[specta::specta]
pub async fn issue_loan_receipt(
    state: State<'_, Desktop>,
    space_id: String,
    input: IssueLoanReceiptInput,
) -> R<IssuedReceiptDto> {
    state.session.app()?.issue_loan_receipt(&space_id, input)
}

#[tauri::command]
#[specta::specta]
pub async fn budget_mode(state: State<'_, Desktop>, space_id: String) -> R<BudgetModeDto> {
    state.session.app()?.budget_mode(&space_id)
}

#[tauri::command]
#[specta::specta]
pub async fn set_budget_mode(
    state: State<'_, Desktop>,
    space_id: String,
    input: BudgetModeInput,
) -> R<BudgetModeDto> {
    state.session.app()?.set_budget_mode(&space_id, input)
}

#[tauri::command]
#[specta::specta]
pub async fn payoff_planner(
    state: State<'_, Desktop>,
    space_id: String,
    input: PlannerInput,
) -> R<PlannerDto> {
    state.session.app()?.payoff_planner(&space_id, input)
}

#[tauri::command]
#[specta::specta]
pub async fn set_debt_order(
    state: State<'_, Desktop>,
    space_id: String,
    debt_ids: Vec<String>,
) -> R<()> {
    state.session.app()?.set_debt_order(&space_id, debt_ids)
}

#[tauri::command]
#[specta::specta]
pub async fn reset_debt_order(state: State<'_, Desktop>, space_id: String) -> R<()> {
    state.session.app()?.reset_debt_order(&space_id)
}

#[tauri::command]
#[specta::specta]
pub async fn add_contributor(
    state: State<'_, Desktop>,
    space_id: String,
    debt_id: String,
    input: NewContributorInput,
) -> R<ContributorDto> {
    state
        .session
        .app()?
        .add_contributor(&space_id, &debt_id, input)
}

#[tauri::command]
#[specta::specta]
pub async fn sellable_items(
    state: State<'_, Desktop>,
    space_id: String,
) -> R<Vec<SellableItemDto>> {
    state.session.app()?.sellable_items(&space_id)
}

#[tauri::command]
#[specta::specta]
pub async fn add_sellable_item(
    state: State<'_, Desktop>,
    space_id: String,
    input: NewSellableItemInput,
) -> R<SellableItemDto> {
    state.session.app()?.add_sellable_item(&space_id, input)
}

#[tauri::command]
#[specta::specta]
pub async fn sell_item(
    state: State<'_, Desktop>,
    space_id: String,
    item_id: String,
    input: SellItemInput,
) -> R<SellResultDto> {
    state.session.app()?.sell_item(&space_id, &item_id, input)
}

#[tauri::command]
#[specta::specta]
pub async fn ceremonies(state: State<'_, Desktop>, space_id: String) -> R<Vec<CeremonySummaryDto>> {
    state.session.app()?.ceremonies(&space_id)
}

#[tauri::command]
#[specta::specta]
pub async fn ceremony(
    state: State<'_, Desktop>,
    space_id: String,
    ceremony_id: String,
) -> R<CeremonyDto> {
    state.session.app()?.ceremony(&space_id, &ceremony_id)
}

#[tauri::command]
#[specta::specta]
pub async fn create_ceremony(
    state: State<'_, Desktop>,
    space_id: String,
    input: NewCeremonyInput,
) -> R<CeremonyDto> {
    state.session.app()?.create_ceremony(&space_id, input)
}

#[tauri::command]
#[specta::specta]
pub async fn update_ceremony(
    state: State<'_, Desktop>,
    space_id: String,
    ceremony_id: String,
    input: CeremonyUpdateInput,
) -> R<CeremonyDto> {
    state
        .session
        .app()?
        .update_ceremony(&space_id, &ceremony_id, input)
}

#[tauri::command]
#[specta::specta]
pub async fn add_scenario(
    state: State<'_, Desktop>,
    space_id: String,
    ceremony_id: String,
    input: ScenarioInput,
) -> R<CeremonyDto> {
    state
        .session
        .app()?
        .add_scenario(&space_id, &ceremony_id, input)
}

#[tauri::command]
#[specta::specta]
pub async fn update_scenario(
    state: State<'_, Desktop>,
    space_id: String,
    ceremony_id: String,
    scenario_id: String,
    input: ScenarioInput,
) -> R<CeremonyDto> {
    state
        .session
        .app()?
        .update_scenario(&space_id, &ceremony_id, &scenario_id, input)
}

#[tauri::command]
#[specta::specta]
pub async fn delete_scenario(
    state: State<'_, Desktop>,
    space_id: String,
    ceremony_id: String,
    scenario_id: String,
) -> R<CeremonyDto> {
    state
        .session
        .app()?
        .delete_scenario(&space_id, &ceremony_id, &scenario_id)
}

#[tauri::command]
#[specta::specta]
pub async fn select_scenario(
    state: State<'_, Desktop>,
    space_id: String,
    ceremony_id: String,
    scenario_id: String,
) -> R<CeremonyDto> {
    state
        .session
        .app()?
        .select_scenario(&space_id, &ceremony_id, &scenario_id)
}

#[tauri::command]
#[specta::specta]
pub async fn add_ceremony_line(
    state: State<'_, Desktop>,
    space_id: String,
    ceremony_id: String,
    scenario_id: String,
    input: NewCeremonyLineInput,
) -> R<CeremonyDto> {
    state
        .session
        .app()?
        .add_ceremony_line(&space_id, &ceremony_id, &scenario_id, input)
}

#[tauri::command]
#[specta::specta]
pub async fn delete_ceremony_line(
    state: State<'_, Desktop>,
    space_id: String,
    ceremony_id: String,
    line_id: String,
) -> R<CeremonyDto> {
    state
        .session
        .app()?
        .delete_ceremony_line(&space_id, &ceremony_id, &line_id)
}

#[tauri::command]
#[specta::specta]
pub async fn save_discussion(
    state: State<'_, Desktop>,
    space_id: String,
    ceremony_id: String,
    answers: Vec<DiscussionAnswerDto>,
) -> R<CeremonyDto> {
    state
        .session
        .app()?
        .save_discussion(&space_id, &ceremony_id, answers)
}

#[tauri::command]
#[specta::specta]
pub async fn agree_discussion(
    state: State<'_, Desktop>,
    space_id: String,
    ceremony_id: String,
    member_id: String,
) -> R<CeremonyDto> {
    state
        .session
        .app()?
        .agree_discussion(&space_id, &ceremony_id, &member_id)
}

#[tauri::command]
#[specta::specta]
pub async fn confirm_ceremony(
    state: State<'_, Desktop>,
    space_id: String,
    ceremony_id: String,
) -> R<CeremonyDto> {
    state
        .session
        .app()?
        .confirm_ceremony(&space_id, &ceremony_id)
}

#[tauri::command]
#[specta::specta]
pub async fn reopen_ceremony(
    state: State<'_, Desktop>,
    space_id: String,
    ceremony_id: String,
) -> R<CeremonyDto> {
    state
        .session
        .app()?
        .reopen_ceremony(&space_id, &ceremony_id)
}

#[tauri::command]
#[specta::specta]
pub async fn delete_ceremony(
    state: State<'_, Desktop>,
    space_id: String,
    ceremony_id: String,
) -> R<()> {
    state
        .session
        .app()?
        .delete_ceremony(&space_id, &ceremony_id)
}

#[tauri::command]
#[specta::specta]
pub async fn add_goal_contribution(
    state: State<'_, Desktop>,
    space_id: String,
    goal_id: String,
    input: NewGoalContributionInput,
) -> R<GoalDto> {
    state
        .session
        .app()?
        .add_goal_contribution(&space_id, &goal_id, input)
}

/// Marosim smetasini PDF qilib «Saqlash» oynasi orqali yozadi.
#[tauri::command]
#[specta::specta]
pub async fn export_ceremony_estimate(
    handle: AppHandle,
    state: State<'_, Desktop>,
    space_id: String,
    ceremony_id: String,
) -> R<bool> {
    let pdf = state
        .session
        .app()?
        .ceremony_estimate_pdf(&space_id, &ceremony_id)?;
    save_pdf(&handle, pdf, "smeta.pdf")
}

/// PDF'ni tizimning «Saqlash» oynasi orqali yozadi. `false` — foydalanuvchi bekor qildi.
fn save_pdf(handle: &AppHandle, pdf: Vec<u8>, file_name: &str) -> R<bool> {
    let picked = handle
        .dialog()
        .file()
        .add_filter("PDF", &["pdf"])
        .set_file_name(file_name)
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

/// Saqlangan tilxatni joriy tekshirish kodi bilan PDF qilib saqlaydi.
#[tauri::command]
#[specta::specta]
pub async fn export_agreement_receipt(
    handle: AppHandle,
    state: State<'_, Desktop>,
    space_id: String,
    agreement_id: String,
) -> R<bool> {
    let pdf = state
        .session
        .app()?
        .loan_receipt_pdf(&space_id, &agreement_id)?;
    save_pdf(&handle, pdf, "tilxat.pdf")
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
    save_pdf(&handle, pdf, "tilxat.pdf")
}
