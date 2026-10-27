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
    trace_startup();
    state.session.status()
}

/// `BARAKA_STARTUP_TRACE=1`: jarayon boshidan UI'ning birinchi chaqiruvigacha (sahifa yuklangan,
/// React ishga tushgan) vaqt stderr'ga bir marta yoziladi. Faqat raqam — shaxsiy ma'lumot yo'q.
fn trace_startup() {
    static ONCE: std::sync::Once = std::sync::Once::new();
    if std::env::var_os("BARAKA_STARTUP_TRACE").is_some() {
        ONCE.call_once(|| {
            if let Some(t) = crate::STARTED.get() {
                eprintln!("startup_ms={}", t.elapsed().as_millis());
            }
        });
    }
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

/// Faqat debug build'da: `BARAKA_E2E_FILES=<papka>` bo'lsa, «Saqlash» va «Ochish» oynalari
/// ochilmaydi — fayl shu papkaga yoziladi yoki undagi eng yangi `.baraka` tanlanadi. WebDriver
/// tizim oynalarini boshqara olmaydi; release'da bu kod kompilyatsiyaga kirmaydi.
fn e2e_files() -> Option<std::path::PathBuf> {
    #[cfg(debug_assertions)]
    {
        std::env::var_os("BARAKA_E2E_FILES").map(std::path::PathBuf::from)
    }
    #[cfg(not(debug_assertions))]
    {
        None
    }
}

/// Tizimning «Saqlash» oynasi (yoki E2E papkasi). `None` — foydalanuvchi bekor qildi.
fn save_path(
    handle: &AppHandle,
    filter: (&str, &str),
    file_name: &str,
) -> R<Option<std::path::PathBuf>> {
    if let Some(dir) = e2e_files() {
        return Ok(Some(dir.join(file_name)));
    }
    let picked = handle
        .dialog()
        .file()
        .add_filter(filter.0, &[filter.1])
        .set_file_name(file_name)
        .blocking_save_file();
    picked
        .map(|f| {
            f.into_path()
                .map_err(|_| AppError::new("SAVE_PATH_INVALID"))
        })
        .transpose()
}

/// PDF'ni tizimning «Saqlash» oynasi orqali yozadi. `false` — foydalanuvchi bekor qildi.
fn save_pdf(handle: &AppHandle, pdf: Vec<u8>, file_name: &str) -> R<bool> {
    let Some(path) = save_path(handle, ("PDF", "pdf"), file_name)? else {
        return Ok(false);
    };
    std::fs::write(with_extension(path, "pdf"), pdf).map_err(|_| AppError::new("IO_ERROR"))?;
    Ok(true)
}

/// Foydalanuvchi nomni butunlay almashtirsa, GTK kengaytma qo'shmaydi — fayl keyin filtrda
/// ko'rinmay qoladi. Kengaytma boshqacha yoki yo'q bo'lsa, oxiriga qo'shiladi.
fn with_extension(path: std::path::PathBuf, ext: &str) -> std::path::PathBuf {
    let ok = path
        .extension()
        .is_some_and(|e| e.to_string_lossy().eq_ignore_ascii_case(ext));
    if ok {
        return path;
    }
    let mut name = path.into_os_string();
    name.push(".");
    name.push(ext);
    name.into()
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

// ---- U11: sheriklik ----

#[tauri::command]
#[specta::specta]
pub async fn partnerships(
    state: State<'_, Desktop>,
    space_id: String,
) -> R<Vec<PartnershipSummaryDto>> {
    state.session.app()?.partnerships(&space_id)
}

#[tauri::command]
#[specta::specta]
pub async fn partnership(
    state: State<'_, Desktop>,
    space_id: String,
    partnership_id: String,
) -> R<PartnershipDto> {
    state.session.app()?.partnership(&space_id, &partnership_id)
}

#[tauri::command]
#[specta::specta]
pub async fn readiness_gate(state: State<'_, Desktop>, space_id: String) -> R<GateDto> {
    state.session.app()?.readiness_gate(&space_id)
}

#[tauri::command]
#[specta::specta]
pub async fn create_partnership(
    state: State<'_, Desktop>,
    space_id: String,
    input: PartnershipInput,
) -> R<PartnershipDto> {
    state.session.app()?.create_partnership(&space_id, input)
}

#[tauri::command]
#[specta::specta]
pub async fn update_partnership(
    state: State<'_, Desktop>,
    space_id: String,
    partnership_id: String,
    input: PartnershipInput,
) -> R<PartnershipDto> {
    state
        .session
        .app()?
        .update_partnership(&space_id, &partnership_id, input)
}

#[tauri::command]
#[specta::specta]
pub async fn sign_partnership(
    state: State<'_, Desktop>,
    space_id: String,
    partnership_id: String,
    input: SignInput,
) -> R<PartnershipDto> {
    state
        .session
        .app()?
        .sign_partnership(&space_id, &partnership_id, input)
}

#[tauri::command]
#[specta::specta]
pub async fn acknowledge_not_debt(
    state: State<'_, Desktop>,
    space_id: String,
    partnership_id: String,
) -> R<PartnershipDto> {
    state
        .session
        .app()?
        .acknowledge_not_debt(&space_id, &partnership_id)
}

#[tauri::command]
#[specta::specta]
pub async fn consent_partnership(
    state: State<'_, Desktop>,
    space_id: String,
    partnership_id: String,
    member_id: String,
) -> R<PartnershipDto> {
    state
        .session
        .app()?
        .consent_partnership(&space_id, &partnership_id, &member_id)
}

#[tauri::command]
#[specta::specta]
pub async fn activate_partnership(
    state: State<'_, Desktop>,
    space_id: String,
    partnership_id: String,
) -> R<PartnershipDto> {
    state
        .session
        .app()?
        .activate_partnership(&space_id, &partnership_id)
}

#[tauri::command]
#[specta::specta]
pub async fn close_partnership(
    state: State<'_, Desktop>,
    space_id: String,
    partnership_id: String,
) -> R<PartnershipDto> {
    state
        .session
        .app()?
        .close_partnership(&space_id, &partnership_id)
}

#[tauri::command]
#[specta::specta]
pub async fn delete_partnership(
    state: State<'_, Desktop>,
    space_id: String,
    partnership_id: String,
) -> R<()> {
    state
        .session
        .app()?
        .delete_partnership(&space_id, &partnership_id)
}

/// Sheriklik shartnomasi PDF'i (joriy versiya va uning imzolari) — «Saqlash» oynasi orqali.
#[tauri::command]
#[specta::specta]
pub async fn export_partnership_contract(
    handle: AppHandle,
    state: State<'_, Desktop>,
    space_id: String,
    partnership_id: String,
) -> R<bool> {
    let pdf = state
        .session
        .app()?
        .partnership_pdf(&space_id, &partnership_id)?;
    save_pdf(&handle, pdf, "shartnoma.pdf")
}

// ---- U12: kassa daftari, davr taqsimoti, «Hunardan ishga», taklif tekshiruvi ----

#[tauri::command]
#[specta::specta]
pub async fn venture_ledger(
    state: State<'_, Desktop>,
    space_id: String,
    partnership_id: String,
) -> R<VentureLedgerDto> {
    state
        .session
        .app()?
        .venture_ledger(&space_id, &partnership_id)
}

#[tauri::command]
#[specta::specta]
pub async fn add_venture_entry(
    state: State<'_, Desktop>,
    space_id: String,
    partnership_id: String,
    input: VentureEntryInput,
) -> R<VentureLedgerDto> {
    state
        .session
        .app()?
        .add_venture_entry(&space_id, &partnership_id, input)
}

#[tauri::command]
#[specta::specta]
pub async fn venture_attachment(
    state: State<'_, Desktop>,
    space_id: String,
    partnership_id: String,
    attachment_id: String,
) -> R<AttachmentDto> {
    state
        .session
        .app()?
        .venture_attachment(&space_id, &partnership_id, &attachment_id)
}

#[tauri::command]
#[specta::specta]
pub async fn venture_period_preview(
    state: State<'_, Desktop>,
    space_id: String,
    partnership_id: String,
    input: ClosePeriodInput,
) -> R<VenturePeriodDto> {
    state
        .session
        .app()?
        .venture_period_preview(&space_id, &partnership_id, input)
}

#[tauri::command]
#[specta::specta]
pub async fn close_venture_period(
    state: State<'_, Desktop>,
    space_id: String,
    partnership_id: String,
    input: ClosePeriodInput,
) -> R<VentureLedgerDto> {
    state
        .session
        .app()?
        .close_venture_period(&space_id, &partnership_id, input)
}

#[tauri::command]
#[specta::specta]
pub async fn skills(state: State<'_, Desktop>, space_id: String) -> R<Vec<SkillDto>> {
    state.session.app()?.skills(&space_id)
}

#[tauri::command]
#[specta::specta]
pub async fn add_skill(
    state: State<'_, Desktop>,
    space_id: String,
    input: SkillInput,
) -> R<Vec<SkillDto>> {
    state.session.app()?.add_skill(&space_id, input)
}

#[tauri::command]
#[specta::specta]
pub async fn delete_skill(
    state: State<'_, Desktop>,
    space_id: String,
    skill_id: String,
) -> R<Vec<SkillDto>> {
    state.session.app()?.delete_skill(&space_id, &skill_id)
}

#[tauri::command]
#[specta::specta]
pub async fn venture_ideas(state: State<'_, Desktop>, space_id: String) -> R<Vec<VentureIdeaDto>> {
    state.session.app()?.venture_ideas(&space_id)
}

#[tauri::command]
#[specta::specta]
pub async fn create_venture_idea(
    state: State<'_, Desktop>,
    space_id: String,
    input: VentureIdeaInput,
) -> R<VentureIdeaDto> {
    state.session.app()?.create_venture_idea(&space_id, input)
}

#[tauri::command]
#[specta::specta]
pub async fn update_venture_idea(
    state: State<'_, Desktop>,
    space_id: String,
    idea_id: String,
    input: VentureIdeaInput,
) -> R<VentureIdeaDto> {
    state
        .session
        .app()?
        .update_venture_idea(&space_id, &idea_id, input)
}

#[tauri::command]
#[specta::specta]
pub async fn delete_venture_idea(
    state: State<'_, Desktop>,
    space_id: String,
    idea_id: String,
) -> R<()> {
    state
        .session
        .app()?
        .delete_venture_idea(&space_id, &idea_id)
}

#[tauri::command]
#[specta::specta]
pub async fn draft_partnership_from_idea(
    state: State<'_, Desktop>,
    space_id: String,
    idea_id: String,
    input: IdeaDraftInput,
) -> R<PartnershipDto> {
    state
        .session
        .app()?
        .draft_partnership_from_idea(&space_id, &idea_id, input)
}

#[tauri::command]
#[specta::specta]
pub async fn check_offer(state: State<'_, Desktop>, input: OfferAnswersInput) -> R<OfferCheckDto> {
    state.session.app()?.check_offer(input)
}

/// Sherik uchun davr hisoboti PDF'i — «Saqlash» oynasi orqali.
#[tauri::command]
#[specta::specta]
pub async fn export_venture_report(
    handle: AppHandle,
    state: State<'_, Desktop>,
    space_id: String,
    partnership_id: String,
    period_id: String,
) -> R<bool> {
    let pdf = state
        .session
        .app()?
        .venture_period_pdf(&space_id, &partnership_id, &period_id)?;
    save_pdf(&handle, pdf, "davr-hisoboti.pdf")
}

// ---- U13: vazifalar, ochiq hisob ko'rigi, «katta foyda», nizo va hakam, oilaviy kelishuvlar ----

#[tauri::command]
#[specta::specta]
pub async fn governance(
    state: State<'_, Desktop>,
    space_id: String,
    partnership_id: String,
) -> R<GovernanceDto> {
    state.session.app()?.governance(&space_id, &partnership_id)
}

/// «Bajara olmayapman»: hodisa jurnalga yoziladi, «bajarilmasa» bandi darhol ko'rinadi.
#[tauri::command]
#[specta::specta]
pub async fn report_duty_incident(
    state: State<'_, Desktop>,
    space_id: String,
    partnership_id: String,
    input: IncidentInput,
) -> R<GovernanceDto> {
    state
        .session
        .app()?
        .report_duty_incident(&space_id, &partnership_id, input)
}

#[tauri::command]
#[specta::specta]
pub async fn resolve_duty_incident(
    state: State<'_, Desktop>,
    space_id: String,
    partnership_id: String,
    incident_id: String,
    note: String,
) -> R<GovernanceDto> {
    state
        .session
        .app()?
        .resolve_duty_incident(&space_id, &partnership_id, &incident_id, &note)
}

#[tauri::command]
#[specta::specta]
pub async fn review_draft(
    state: State<'_, Desktop>,
    space_id: String,
    partnership_id: String,
    to_on: String,
) -> R<ReviewDraftDto> {
    state
        .session
        .app()?
        .review_draft(&space_id, &partnership_id, &to_on)
}

/// Ochiq hisob ko'rigi: tomonlar belgisi jurnalga, bayonnomada zanjir boshi.
#[tauri::command]
#[specta::specta]
pub async fn hold_review(
    state: State<'_, Desktop>,
    space_id: String,
    partnership_id: String,
    input: HoldReviewInput,
) -> R<GovernanceDto> {
    state
        .session
        .app()?
        .hold_review(&space_id, &partnership_id, input)
}

#[tauri::command]
#[specta::specta]
pub async fn acknowledge_spike_reread(
    state: State<'_, Desktop>,
    space_id: String,
    partnership_id: String,
    party_id: String,
) -> R<VentureLedgerDto> {
    state
        .session
        .app()?
        .acknowledge_spike_reread(&space_id, &partnership_id, &party_id)
}

#[tauri::command]
#[specta::specta]
pub async fn open_partnership_dispute(
    state: State<'_, Desktop>,
    space_id: String,
    partnership_id: String,
    input: OpenDisputeInput,
) -> R<GovernanceDto> {
    state
        .session
        .app()?
        .open_partnership_dispute(&space_id, &partnership_id, input)
}

#[tauri::command]
#[specta::specta]
pub async fn add_dispute_claim(
    state: State<'_, Desktop>,
    space_id: String,
    partnership_id: String,
    dispute_id: String,
    input: DisputeClaimInput,
) -> R<GovernanceDto> {
    state
        .session
        .app()?
        .add_dispute_claim(&space_id, &partnership_id, &dispute_id, input)
}

#[tauri::command]
#[specta::specta]
pub async fn record_arbiter_decision(
    state: State<'_, Desktop>,
    space_id: String,
    partnership_id: String,
    dispute_id: String,
    input: DecisionInput,
) -> R<GovernanceDto> {
    state
        .session
        .app()?
        .record_arbiter_decision(&space_id, &partnership_id, &dispute_id, input)
}

/// Yillik yangilash: reviewDate +1 yil, hamma qayta imzolaydi.
#[tauri::command]
#[specta::specta]
pub async fn renew_partnership(
    state: State<'_, Desktop>,
    space_id: String,
    partnership_id: String,
) -> R<PartnershipDto> {
    state
        .session
        .app()?
        .renew_partnership(&space_id, &partnership_id)
}

#[tauri::command]
#[specta::specta]
pub async fn family_agreements(
    state: State<'_, Desktop>,
    space_id: String,
) -> R<Vec<FamilyAgreementDto>> {
    state.session.app()?.family_agreements(&space_id)
}

#[tauri::command]
#[specta::specta]
pub async fn create_family_agreement(
    state: State<'_, Desktop>,
    space_id: String,
    input: FamilyAgreementInput,
) -> R<FamilyAgreementDto> {
    state
        .session
        .app()?
        .create_family_agreement(&space_id, input)
}

#[tauri::command]
#[specta::specta]
pub async fn update_family_agreement(
    state: State<'_, Desktop>,
    space_id: String,
    id: String,
    input: FamilyAgreementInput,
) -> R<FamilyAgreementDto> {
    state
        .session
        .app()?
        .update_family_agreement(&space_id, &id, input)
}

#[tauri::command]
#[specta::specta]
pub async fn delete_family_agreement(
    state: State<'_, Desktop>,
    space_id: String,
    id: String,
) -> R<()> {
    state.session.app()?.delete_family_agreement(&space_id, &id)
}

#[tauri::command]
#[specta::specta]
pub async fn agreement_reminders(
    state: State<'_, Desktop>,
    space_id: String,
) -> R<Vec<ReminderDto>> {
    state.session.app()?.agreement_reminders(&space_id)
}

#[tauri::command]
#[specta::specta]
pub async fn agreements_center(
    state: State<'_, Desktop>,
    space_id: String,
) -> R<Vec<AgreementSummaryDto>> {
    state.session.app()?.agreements_center(&space_id)
}

/// Katta a'zoning tasdig'i: PIN qayta so'raladi (oilaviy kelishuv 2F.10).
#[tauri::command]
#[specta::specta]
pub async fn confirm_family_agreement(
    state: State<'_, Desktop>,
    space_id: String,
    pin: String,
    id: String,
    member_id: String,
) -> R<FamilyAgreementDto> {
    state.session.confirm_pin(&state.secrets.load()?, &pin)?;
    state
        .session
        .app()?
        .confirm_family_agreement(&space_id, &id, &member_id)
}

/// Ko'rik bayonnomasi PDF'i (zanjir boshi QR bilan).
#[tauri::command]
#[specta::specta]
pub async fn export_review_protocol(
    handle: AppHandle,
    state: State<'_, Desktop>,
    space_id: String,
    partnership_id: String,
    review_id: String,
) -> R<bool> {
    let pdf = state
        .session
        .app()?
        .review_pdf(&space_id, &partnership_id, &review_id)?;
    save_pdf(&handle, pdf, "bayonnoma.pdf")
}

/// «Hakam uchun ish papkasi» — bitta PDF, mundarija va sahifa raqamlari bilan.
#[tauri::command]
#[specta::specta]
pub async fn export_dispute_folder(
    handle: AppHandle,
    state: State<'_, Desktop>,
    space_id: String,
    partnership_id: String,
    dispute_id: String,
) -> R<bool> {
    let pdf = state
        .session
        .app()?
        .dispute_folder_pdf(&space_id, &partnership_id, &dispute_id)?;
    save_pdf(&handle, pdf, "hakam-papkasi.pdf")
}

// ---- U14: `.baraka` eksport/import va qurilmalarni ulash ----

/// `.baraka` fayl hajmi chegarasi (cheklar rasmlari bilan ham yetarli).
const MAX_BARAKA_BYTES: u64 = 512 * 1024 * 1024;

/// Tanlangan fayl: to'liq yo'l (keyingi buyruqlar uchun) va ko'rsatiladigan nomi.
#[derive(Clone, Debug, serde::Serialize, specta::Type)]
#[serde(rename_all = "camelCase")]
pub struct PickedFile {
    pub path: String,
    pub name: String,
}

/// Ulash oynasi uchun: QR, qo'lda kiritiladigan kod va saqlangan fayl nomi.
#[derive(Clone, Debug, serde::Serialize, specta::Type)]
#[serde(rename_all = "camelCase")]
pub struct PairingView {
    pub code: String,
    pub qr_svg: String,
    pub household_name: String,
    pub file_name: String,
}

fn save_baraka(handle: &AppHandle, bytes: &[u8], file_name: &str) -> R<Option<String>> {
    let Some(path) = save_path(handle, ("Baraka Dastur", "baraka"), file_name)? else {
        return Ok(None);
    };
    let path = with_extension(path, "baraka");
    std::fs::write(&path, bytes).map_err(|_| AppError::new("IO_ERROR"))?;
    Ok(Some(
        path.file_name()
            .map(|n| n.to_string_lossy().into_owned())
            .unwrap_or_default(),
    ))
}

/// E2E papkasidagi eng yangi `.baraka` fayl.
fn newest_baraka(dir: &std::path::Path) -> Option<std::path::PathBuf> {
    std::fs::read_dir(dir)
        .ok()?
        .filter_map(Result::ok)
        .filter(|e| e.path().extension().is_some_and(|x| x == "baraka"))
        .max_by_key(|e| e.metadata().and_then(|m| m.modified()).ok())
        .map(|e| e.path())
}

fn read_baraka(path: &str) -> R<Vec<u8>> {
    let meta = std::fs::metadata(path).map_err(|_| AppError::new("IO_ERROR"))?;
    if meta.len() > MAX_BARAKA_BYTES {
        return Err(AppError::new("FILE_TOO_LARGE"));
    }
    std::fs::read(path).map_err(|_| AppError::new("IO_ERROR"))
}

#[tauri::command]
#[specta::specta]
pub async fn kk_overview(
    state: State<'_, Desktop>,
    space_id: String,
    date: Option<String>,
) -> R<KkOverviewDto> {
    state.session.app()?.kk_overview(&space_id, date)
}

#[tauri::command]
#[specta::specta]
pub async fn kk_set_owner_salary(
    state: State<'_, Desktop>,
    space_id: String,
    amount: String,
) -> R<KkOverviewDto> {
    state.session.app()?.kk_set_owner_salary(&space_id, amount)
}

#[tauri::command]
#[specta::specta]
pub async fn kk_record_sale(
    state: State<'_, Desktop>,
    space_id: String,
    input: KkSaleInput,
) -> R<KkOverviewDto> {
    state.session.app()?.kk_record_sale(&space_id, input)
}

#[tauri::command]
#[specta::specta]
pub async fn kk_record_move(
    state: State<'_, Desktop>,
    space_id: String,
    input: KkMoveInput,
) -> R<KkOverviewDto> {
    state.session.app()?.kk_record_move(&space_id, input)
}

#[tauri::command]
#[specta::specta]
pub async fn kk_pay_owner_salary(
    state: State<'_, Desktop>,
    space_id: String,
    input: KkSalaryInput,
) -> R<KkSalaryPaidDto> {
    state.session.app()?.kk_pay_owner_salary(&space_id, input)
}

#[tauri::command]
#[specta::specta]
pub async fn kk_set_owner_labor(
    state: State<'_, Desktop>,
    space_id: String,
    amount: String,
) -> R<KkOverviewDto> {
    state.session.app()?.kk_set_owner_labor(&space_id, amount)
}

#[tauri::command]
#[specta::specta]
pub async fn kk_equipment(state: State<'_, Desktop>, space_id: String) -> R<Vec<KkEquipmentDto>> {
    state.session.app()?.kk_equipment(&space_id)
}

#[tauri::command]
#[specta::specta]
pub async fn kk_add_equipment(
    state: State<'_, Desktop>,
    space_id: String,
    input: KkEquipmentInput,
) -> R<Vec<KkEquipmentDto>> {
    state.session.app()?.kk_add_equipment(&space_id, input)
}

#[tauri::command]
#[specta::specta]
pub async fn kk_dispose_equipment(
    state: State<'_, Desktop>,
    space_id: String,
    id: String,
    input: KkDisposeInput,
) -> R<Vec<KkEquipmentDto>> {
    state
        .session
        .app()?
        .kk_dispose_equipment(&space_id, &id, input)
}

#[tauri::command]
#[specta::specta]
pub async fn kk_delete_equipment(
    state: State<'_, Desktop>,
    space_id: String,
    id: String,
) -> R<Vec<KkEquipmentDto>> {
    state.session.app()?.kk_delete_equipment(&space_id, &id)
}

#[tauri::command]
#[specta::specta]
pub async fn kk_family_labor(
    state: State<'_, Desktop>,
    space_id: String,
    date: Option<String>,
) -> R<Vec<KkFamilyLaborDto>> {
    state.session.app()?.kk_family_labor(&space_id, date)
}

#[tauri::command]
#[specta::specta]
pub async fn kk_add_family_labor(
    state: State<'_, Desktop>,
    space_id: String,
    input: KkFamilyLaborInput,
) -> R<Vec<KkFamilyLaborDto>> {
    state.session.app()?.kk_add_family_labor(&space_id, input)
}

#[tauri::command]
#[specta::specta]
pub async fn kk_delete_family_labor(
    state: State<'_, Desktop>,
    space_id: String,
    id: String,
) -> R<Vec<KkFamilyLaborDto>> {
    state.session.app()?.kk_delete_family_labor(&space_id, &id)
}

#[tauri::command]
#[specta::specta]
pub async fn kk_order_quote(
    state: State<'_, Desktop>,
    space_id: String,
    input: KkQuoteInput,
) -> R<KkQuoteDto> {
    state.session.app()?.kk_order_quote(&space_id, input)
}

#[tauri::command]
#[specta::specta]
pub async fn kk_close_rules(state: State<'_, Desktop>, space_id: String) -> R<KkCloseRulesDto> {
    state.session.app()?.kk_close_rules(&space_id)
}

#[tauri::command]
#[specta::specta]
pub async fn kk_set_close_rules(
    state: State<'_, Desktop>,
    space_id: String,
    input: KkCloseRulesInput,
) -> R<KkCloseRulesDto> {
    state.session.app()?.kk_set_close_rules(&space_id, input)
}

#[tauri::command]
#[specta::specta]
pub async fn kk_close_draft(
    state: State<'_, Desktop>,
    space_id: String,
    period_start: Option<String>,
) -> R<KkCloseDraftDto> {
    state.session.app()?.kk_close_draft(&space_id, period_start)
}

#[tauri::command]
#[specta::specta]
pub async fn kk_close_month(
    state: State<'_, Desktop>,
    space_id: String,
    input: KkCloseInput,
) -> R<KkMonthCloseDto> {
    state.session.app()?.kk_close_month(&space_id, input)
}

#[tauri::command]
#[specta::specta]
pub async fn kk_month_closes(
    state: State<'_, Desktop>,
    space_id: String,
) -> R<Vec<KkMonthCloseDto>> {
    state.session.app()?.kk_month_closes(&space_id)
}

/// «Hisob kuni» bayonnomasi PDF'i — «Saqlash» oynasi orqali.
#[tauri::command]
#[specta::specta]
pub async fn export_kk_month_close(
    handle: AppHandle,
    state: State<'_, Desktop>,
    space_id: String,
    close_id: String,
) -> R<bool> {
    let pdf = state
        .session
        .app()?
        .kk_month_close_pdf(&space_id, &close_id)?;
    save_pdf(&handle, pdf, "hisob-kuni.pdf")
}

#[tauri::command]
#[specta::specta]
pub async fn kk_cash_draft(
    state: State<'_, Desktop>,
    space_id: String,
    day: Option<String>,
    counted: Option<String>,
) -> R<KkCashDraftDto> {
    state.session.app()?.kk_cash_draft(&space_id, day, counted)
}

#[tauri::command]
#[specta::specta]
pub async fn kk_close_cash_day(
    state: State<'_, Desktop>,
    space_id: String,
    input: KkCashCloseInput,
) -> R<KkCashDayDto> {
    state.session.app()?.kk_close_cash_day(&space_id, input)
}

#[tauri::command]
#[specta::specta]
pub async fn kk_cash_days(state: State<'_, Desktop>, space_id: String) -> R<Vec<KkCashDayDto>> {
    state.session.app()?.kk_cash_days(&space_id)
}

#[tauri::command]
#[specta::specta]
pub async fn kk_customers(state: State<'_, Desktop>, space_id: String) -> R<Vec<KkCustomerDto>> {
    state.session.app()?.kk_customers(&space_id)
}

#[tauri::command]
#[specta::specta]
pub async fn kk_add_customer(
    state: State<'_, Desktop>,
    space_id: String,
    input: KkCustomerInput,
) -> R<Vec<KkCustomerDto>> {
    state.session.app()?.kk_add_customer(&space_id, input)
}

#[tauri::command]
#[specta::specta]
pub async fn kk_credit_book(state: State<'_, Desktop>, space_id: String) -> R<KkCreditBookDto> {
    state.session.app()?.kk_credit_book(&space_id)
}

#[tauri::command]
#[specta::specta]
pub async fn kk_add_credit_sale(
    state: State<'_, Desktop>,
    space_id: String,
    input: KkCreditSaleInput,
) -> R<KkCreditBookDto> {
    state.session.app()?.kk_add_credit_sale(&space_id, input)
}

#[tauri::command]
#[specta::specta]
pub async fn kk_credit_payment(
    state: State<'_, Desktop>,
    space_id: String,
    sale_id: String,
    input: KkCreditPaymentInput,
) -> R<KkCreditBookDto> {
    state
        .session
        .app()?
        .kk_credit_payment(&space_id, &sale_id, input)
}

#[tauri::command]
#[specta::specta]
pub async fn kk_credit_forgive(
    state: State<'_, Desktop>,
    space_id: String,
    sale_id: String,
    input: KkCreditForgiveInput,
) -> R<KkCreditBookDto> {
    state
        .session
        .app()?
        .kk_credit_forgive(&space_id, &sale_id, input)
}

#[tauri::command]
#[specta::specta]
pub async fn kk_credit_extend(
    state: State<'_, Desktop>,
    space_id: String,
    sale_id: String,
    input: KkCreditExtendInput,
) -> R<KkCreditBookDto> {
    state
        .session
        .app()?
        .kk_credit_extend(&space_id, &sale_id, input)
}

#[tauri::command]
#[specta::specta]
pub async fn kk_credit_mark(
    state: State<'_, Desktop>,
    space_id: String,
    sale_id: String,
    talk: bool,
) -> R<KkCreditBookDto> {
    state
        .session
        .app()?
        .kk_credit_mark(&space_id, &sale_id, talk)
}

#[tauri::command]
#[specta::specta]
pub async fn kk_delete_credit_sale(
    state: State<'_, Desktop>,
    space_id: String,
    sale_id: String,
) -> R<KkCreditBookDto> {
    state
        .session
        .app()?
        .kk_delete_credit_sale(&space_id, &sale_id)
}

#[tauri::command]
#[specta::specta]
pub async fn kk_stock(state: State<'_, Desktop>, space_id: String) -> R<KkStockDto> {
    state.session.app()?.kk_stock(&space_id)
}

#[tauri::command]
#[specta::specta]
pub async fn kk_add_item(
    state: State<'_, Desktop>,
    space_id: String,
    input: KkItemInput,
) -> R<KkStockDto> {
    state.session.app()?.kk_add_item(&space_id, input)
}

#[tauri::command]
#[specta::specta]
pub async fn kk_update_item(
    state: State<'_, Desktop>,
    space_id: String,
    item_id: String,
    input: KkItemInput,
) -> R<KkStockDto> {
    state
        .session
        .app()?
        .kk_update_item(&space_id, &item_id, input)
}

#[tauri::command]
#[specta::specta]
pub async fn kk_delete_item(
    state: State<'_, Desktop>,
    space_id: String,
    item_id: String,
) -> R<KkStockDto> {
    state.session.app()?.kk_delete_item(&space_id, &item_id)
}

#[tauri::command]
#[specta::specta]
pub async fn kk_stock_move(
    state: State<'_, Desktop>,
    space_id: String,
    item_id: String,
    input: KkStockMoveInput,
) -> R<KkStockDto> {
    state
        .session
        .app()?
        .kk_stock_move(&space_id, &item_id, input)
}

#[tauri::command]
#[specta::specta]
pub async fn kk_staff(state: State<'_, Desktop>, space_id: String) -> R<KkStaffDto> {
    state.session.app()?.kk_staff(&space_id)
}

#[tauri::command]
#[specta::specta]
pub async fn kk_add_employee(
    state: State<'_, Desktop>,
    space_id: String,
    input: KkEmployeeInput,
) -> R<KkStaffDto> {
    state.session.app()?.kk_add_employee(&space_id, input)
}

#[tauri::command]
#[specta::specta]
pub async fn kk_update_employee(
    state: State<'_, Desktop>,
    space_id: String,
    id: String,
    input: KkEmployeeInput,
) -> R<KkStaffDto> {
    state
        .session
        .app()?
        .kk_update_employee(&space_id, &id, input)
}

#[tauri::command]
#[specta::specta]
pub async fn kk_staff_advance(
    state: State<'_, Desktop>,
    space_id: String,
    id: String,
    input: KkAdvanceInput,
) -> R<KkStaffDto> {
    state.session.app()?.kk_staff_advance(&space_id, &id, input)
}

#[tauri::command]
#[specta::specta]
pub async fn kk_staff_pay(
    state: State<'_, Desktop>,
    space_id: String,
    id: String,
    input: KkWageInput,
) -> R<KkStaffDto> {
    state.session.app()?.kk_staff_pay(&space_id, &id, input)
}

#[tauri::command]
#[specta::specta]
pub async fn kk_suppliers(state: State<'_, Desktop>, space_id: String) -> R<KkSuppliersDto> {
    state.session.app()?.kk_suppliers(&space_id)
}

#[tauri::command]
#[specta::specta]
pub async fn kk_add_supplier(
    state: State<'_, Desktop>,
    space_id: String,
    input: KkSupplierInput,
) -> R<KkSuppliersDto> {
    state.session.app()?.kk_add_supplier(&space_id, input)
}

#[tauri::command]
#[specta::specta]
pub async fn kk_update_supplier(
    state: State<'_, Desktop>,
    space_id: String,
    id: String,
    input: KkSupplierInput,
) -> R<KkSuppliersDto> {
    state
        .session
        .app()?
        .kk_update_supplier(&space_id, &id, input)
}

#[tauri::command]
#[specta::specta]
pub async fn kk_supply_delivery(
    state: State<'_, Desktop>,
    space_id: String,
    id: String,
    input: KkDeliveryInput,
) -> R<KkSuppliersDto> {
    state
        .session
        .app()?
        .kk_supply_delivery(&space_id, &id, input)
}

#[tauri::command]
#[specta::specta]
pub async fn kk_supply_payment(
    state: State<'_, Desktop>,
    space_id: String,
    id: String,
    input: KkSupplyPaymentInput,
) -> R<KkSuppliersDto> {
    state
        .session
        .app()?
        .kk_supply_payment(&space_id, &id, input)
}

#[tauri::command]
#[specta::specta]
pub async fn kk_sign_agreement(
    state: State<'_, Desktop>,
    space_id: String,
    id: String,
    input: KkSignInput,
) -> R<()> {
    state
        .session
        .app()?
        .kk_sign_agreement(&space_id, &id, input)
}

#[tauri::command]
#[specta::specta]
pub async fn kk_end_agreement(
    state: State<'_, Desktop>,
    space_id: String,
    id: String,
    ended_on: Option<String>,
) -> R<()> {
    state
        .session
        .app()?
        .kk_end_agreement(&space_id, &id, ended_on)
}

#[tauri::command]
#[specta::specta]
pub async fn kk_delete_agreement(state: State<'_, Desktop>, space_id: String, id: String) -> R<()> {
    state.session.app()?.kk_delete_agreement(&space_id, &id)
}

/// Xodim yoki ta'minotchi kelishuvi PDF'i (imzolangan versiya yoki qoralama) — «Saqlash» oynasi orqali.
#[tauri::command]
#[specta::specta]
pub async fn export_kk_agreement(
    handle: AppHandle,
    state: State<'_, Desktop>,
    space_id: String,
    id: String,
) -> R<bool> {
    let pdf = state.session.app()?.kk_agreement_pdf(&space_id, &id)?;
    save_pdf(&handle, pdf, "kelishuv.pdf")
}

/// Xodim bilan oylik hisob varaqchasi PDF'i; `month` — oy ichidagi istalgan sana.
#[tauri::command]
#[specta::specta]
pub async fn export_kk_payslip(
    handle: AppHandle,
    state: State<'_, Desktop>,
    space_id: String,
    id: String,
    month: String,
) -> R<bool> {
    let pdf = state.session.app()?.kk_payslip_pdf(&space_id, &id, month)?;
    save_pdf(&handle, pdf, "varaqcha.pdf")
}

#[tauri::command]
#[specta::specta]
pub async fn kk_gate(state: State<'_, Desktop>, space_id: String) -> R<KkGateDto> {
    state.session.app()?.kk_gate(&space_id)
}

#[tauri::command]
#[specta::specta]
pub async fn kk_use_fund(
    state: State<'_, Desktop>,
    space_id: String,
    input: KkFundUseInput,
) -> R<KkGateDto> {
    state.session.app()?.kk_use_fund(&space_id, input)
}

#[tauri::command]
#[specta::specta]
pub async fn kk_growth_settings(
    state: State<'_, Desktop>,
    space_id: String,
) -> R<KkGrowthSettingsDto> {
    state.session.app()?.kk_growth_settings(&space_id)
}

#[tauri::command]
#[specta::specta]
pub async fn kk_set_growth_settings(
    state: State<'_, Desktop>,
    space_id: String,
    input: KkGrowthSettingsInput,
) -> R<KkGrowthSettingsDto> {
    state
        .session
        .app()?
        .kk_set_growth_settings(&space_id, input)
}

#[tauri::command]
#[specta::specta]
pub async fn kk_scale(state: State<'_, Desktop>, space_id: String) -> R<KkScaleDto> {
    state.session.app()?.kk_scale(&space_id)
}

#[tauri::command]
#[specta::specta]
pub async fn kk_scale_check(
    state: State<'_, Desktop>,
    space_id: String,
    input: KkScaleCheckInput,
) -> R<KkScaleDto> {
    state.session.app()?.kk_scale_check(&space_id, input)
}

#[tauri::command]
#[specta::specta]
pub async fn kk_zakat_draft(
    state: State<'_, Desktop>,
    space_id: String,
    input: KkZakatInput,
) -> R<KkZakatDto> {
    state.session.app()?.kk_zakat_draft(&space_id, input)
}

#[tauri::command]
#[specta::specta]
pub async fn kk_save_zakat(
    state: State<'_, Desktop>,
    space_id: String,
    input: KkZakatInput,
) -> R<Vec<KkZakatCalcDto>> {
    state.session.app()?.kk_save_zakat(&space_id, input)
}

#[tauri::command]
#[specta::specta]
pub async fn kk_zakat_history(
    state: State<'_, Desktop>,
    space_id: String,
) -> R<Vec<KkZakatCalcDto>> {
    state.session.app()?.kk_zakat_history(&space_id)
}

#[tauri::command]
#[specta::specta]
pub async fn kk_inventory(
    state: State<'_, Desktop>,
    space_id: String,
    input: KkInventoryInput,
) -> R<KkStockDto> {
    state.session.app()?.kk_inventory(&space_id, input)
}

#[tauri::command]
#[specta::specta]
pub async fn kk_stock_counts(
    state: State<'_, Desktop>,
    space_id: String,
) -> R<Vec<KkStockCountDto>> {
    state.session.app()?.kk_stock_counts(&space_id)
}

// ---- K8: ko'p qurilma va rollar (ADR-0003) ----

#[tauri::command]
#[specta::specta]
pub async fn device_role(state: State<'_, Desktop>) -> R<DeviceRoleDto> {
    state.session.app()?.device_role()
}

#[tauri::command]
#[specta::specta]
pub async fn revoke_device(state: State<'_, Desktop>, device_id: String) -> R<Vec<DeviceDto>> {
    state.session.app()?.revoke_device(&device_id)
}

#[tauri::command]
#[specta::specta]
pub async fn kk_catalog(state: State<'_, Desktop>, space_id: String) -> R<Vec<KkCatalogItemDto>> {
    state.session.app()?.kk_catalog(&space_id)
}

#[tauri::command]
#[specta::specta]
pub async fn kk_seller_sale(
    state: State<'_, Desktop>,
    space_id: String,
    input: KkSellerSaleInput,
) -> R<KkSellerDayDto> {
    state.session.app()?.kk_seller_sale(&space_id, input)
}

#[tauri::command]
#[specta::specta]
pub async fn kk_seller_day(state: State<'_, Desktop>, space_id: String) -> R<KkSellerDayDto> {
    state.session.app()?.kk_seller_day(&space_id)
}

#[tauri::command]
#[specta::specta]
pub async fn kk_shift_draft(
    state: State<'_, Desktop>,
    space_id: String,
    input: KkShiftInput,
) -> R<KkShiftDto> {
    state.session.app()?.kk_shift_draft(&space_id, input)
}

#[tauri::command]
#[specta::specta]
pub async fn kk_close_shift(
    state: State<'_, Desktop>,
    space_id: String,
    input: KkShiftInput,
) -> R<KkShiftDto> {
    state.session.app()?.kk_close_shift(&space_id, input)
}

#[tauri::command]
#[specta::specta]
pub async fn kk_shifts(state: State<'_, Desktop>, space_id: String) -> R<Vec<KkShiftRecordDto>> {
    state.session.app()?.kk_shifts(&space_id)
}

// ---- M1: Musofir makoni ----

#[tauri::command]
#[specta::specta]
pub async fn mf_overview(
    state: State<'_, Desktop>,
    space_id: String,
    date: Option<String>,
) -> R<MfOverviewDto> {
    state.session.app()?.mf_overview(&space_id, date)
}

#[tauri::command]
#[specta::specta]
pub async fn mf_set_settings(
    state: State<'_, Desktop>,
    space_id: String,
    input: MfSettingsInput,
) -> R<MfOverviewDto> {
    state.session.app()?.mf_set_settings(&space_id, input)
}

#[tauri::command]
#[specta::specta]
pub async fn mf_set_rate(
    state: State<'_, Desktop>,
    space_id: String,
    input: MfRateInput,
) -> R<MfOverviewDto> {
    state.session.app()?.mf_set_rate(&space_id, input)
}

#[tauri::command]
#[specta::specta]
pub async fn mf_record_income(
    state: State<'_, Desktop>,
    space_id: String,
    input: MfIncomeInput,
) -> R<MfIncomeRecordedDto> {
    state.session.app()?.mf_record_income(&space_id, input)
}

#[tauri::command]
#[specta::specta]
pub async fn mf_record_expense(
    state: State<'_, Desktop>,
    space_id: String,
    input: MfExpenseInput,
) -> R<MfOverviewDto> {
    state.session.app()?.mf_record_expense(&space_id, input)
}

#[tauri::command]
#[specta::specta]
pub async fn mf_record_move(
    state: State<'_, Desktop>,
    space_id: String,
    input: MfMoveInput,
) -> R<MfOverviewDto> {
    state.session.app()?.mf_record_move(&space_id, input)
}

// ---- M2: «Ikki qirg'oq» ----

#[tauri::command]
#[specta::specta]
pub async fn mf_terms(state: State<'_, Desktop>, space_id: String) -> R<MfTermsDto> {
    state.session.app()?.mf_terms(&space_id)
}

#[tauri::command]
#[specta::specta]
pub async fn mf_set_terms(
    state: State<'_, Desktop>,
    space_id: String,
    input: MfTermsInput,
) -> R<MfTermsDto> {
    state.session.app()?.mf_set_terms(&space_id, input)
}

#[tauri::command]
#[specta::specta]
pub async fn mf_two_shores(state: State<'_, Desktop>, space_id: String) -> R<MfTwoShoresDto> {
    state.session.app()?.mf_two_shores(&space_id)
}

#[tauri::command]
#[specta::specta]
pub async fn mf_confirm_receipt(
    state: State<'_, Desktop>,
    space_id: String,
    move_id: String,
    input: MfReceiptInput,
) -> R<MfTwoShoresDto> {
    state
        .session
        .app()?
        .mf_confirm_receipt(&space_id, &move_id, input)
}

#[tauri::command]
#[specta::specta]
pub async fn mf_record_spend(
    state: State<'_, Desktop>,
    space_id: String,
    input: MfSpendInput,
) -> R<MfTwoShoresDto> {
    state.session.app()?.mf_record_spend(&space_id, input)
}

#[tauri::command]
#[specta::specta]
pub async fn mf_travel_debt(
    state: State<'_, Desktop>,
    space_id: String,
) -> R<MfTravelDebtDto> {
    state.session.app()?.mf_travel_debt(&space_id)
}

#[tauri::command]
#[specta::specta]
pub async fn mf_set_travel_debt(
    state: State<'_, Desktop>,
    space_id: String,
    input: MfTravelDebtInput,
) -> R<MfTravelDebtDto> {
    state.session.app()?.mf_set_travel_debt(&space_id, input)
}

#[tauri::command]
#[specta::specta]
pub async fn mf_pay_debt(
    state: State<'_, Desktop>,
    space_id: String,
    input: MfDebtPaymentInput,
) -> R<MfTwoShoresDto> {
    state.session.app()?.mf_pay_debt(&space_id, input)
}

#[tauri::command]
#[specta::specta]
pub async fn mf_set_return(
    state: State<'_, Desktop>,
    space_id: String,
    input: MfReturnInput,
) -> R<MfOverviewDto> {
    state.session.app()?.mf_set_return(&space_id, input)
}

#[tauri::command]
#[specta::specta]
pub async fn mf_check_decision(
    state: State<'_, Desktop>,
    space_id: String,
    input: MfDecisionInput,
) -> R<MfDecisionCheckDto> {
    state.session.app()?.mf_check_decision(&space_id, input)
}

#[tauri::command]
#[specta::specta]
pub async fn mf_record_decision(
    state: State<'_, Desktop>,
    space_id: String,
    input: MfDecisionInput,
) -> R<Vec<MfDecisionDto>> {
    state.session.app()?.mf_record_decision(&space_id, input)
}

#[tauri::command]
#[specta::specta]
pub async fn mf_decisions(
    state: State<'_, Desktop>,
    space_id: String,
) -> R<Vec<MfDecisionDto>> {
    state.session.app()?.mf_decisions(&space_id)
}

#[tauri::command]
#[specta::specta]
pub async fn mf_decision_questions(state: State<'_, Desktop>, kind: String) -> R<Vec<String>> {
    state.session.app()?.mf_decision_questions(&kind)
}

#[tauri::command]
#[specta::specta]
pub async fn mf_set_plan(
    state: State<'_, Desktop>,
    space_id: String,
    input: MfPlanInput,
) -> R<MfOverviewDto> {
    state.session.app()?.mf_set_plan(&space_id, input)
}

#[tauri::command]
#[specta::specta]
pub async fn mf_set_outcome(
    state: State<'_, Desktop>,
    space_id: String,
    decision_id: String,
    input: MfOutcomeInput,
) -> R<Vec<MfDecisionDto>> {
    state.session.app()?.mf_set_outcome(&space_id, &decision_id, input)
}

#[tauri::command]
#[specta::specta]
pub async fn check_course(
    state: State<'_, Desktop>,
    input: CourseAnswersInput,
) -> R<OfferCheckDto> {
    state.session.app()?.check_course(input)
}

#[tauri::command]
#[specta::specta]
pub async fn hour_value_suggest(
    state: State<'_, Desktop>,
    space_id: String,
    member_id: String,
) -> R<HourValueSuggestionDto> {
    state
        .session
        .app()?
        .hour_value_suggest(&space_id, &member_id)
}

#[tauri::command]
#[specta::specta]
pub async fn hour_value_save(
    state: State<'_, Desktop>,
    space_id: String,
    input: HourValueInput,
) -> R<HourValueDto> {
    state.session.app()?.hour_value_save(&space_id, input)
}

#[tauri::command]
#[specta::specta]
pub async fn learning_plan_create(
    state: State<'_, Desktop>,
    space_id: String,
    input: LearningPlanInput,
) -> R<LearningPlanDto> {
    state.session.app()?.learning_plan_create(&space_id, input)
}

#[tauri::command]
#[specta::specta]
pub async fn learning_plan_set_status(
    state: State<'_, Desktop>,
    space_id: String,
    plan_id: String,
    status: String,
) -> R<LearningPlanDto> {
    state
        .session
        .app()?
        .learning_plan_set_status(&space_id, &plan_id, &status)
}

#[tauri::command]
#[specta::specta]
pub async fn learning_plan_result(
    state: State<'_, Desktop>,
    space_id: String,
    plan_id: String,
) -> R<LearningResultDto> {
    state
        .session
        .app()?
        .learning_plan_result(&space_id, &plan_id)
}

#[tauri::command]
#[specta::specta]
pub async fn study_log_add(
    state: State<'_, Desktop>,
    space_id: String,
    plan_id: String,
    input: StudyLogInput,
) -> R<LearningPlanDto> {
    state
        .session
        .app()?
        .study_log_add(&space_id, &plan_id, input)
}

#[tauri::command]
#[specta::specta]
pub async fn teaching_log_add(
    state: State<'_, Desktop>,
    space_id: String,
    input: TeachingLogInput,
) -> R<TeachingLogDto> {
    state.session.app()?.teaching_log_add(&space_id, input)
}

#[tauri::command]
#[specta::specta]
pub async fn learning_overview(
    state: State<'_, Desktop>,
    space_id: String,
    date: Option<String>,
) -> R<LearningOverviewDto> {
    state
        .session
        .app()?
        .learning_overview(&space_id, date.as_deref())
}

#[tauri::command]
#[specta::specta]
pub async fn settings(state: State<'_, Desktop>) -> R<SettingsDto> {
    state.session.app()?.settings()
}

#[tauri::command]
#[specta::specta]
pub async fn update_settings(state: State<'_, Desktop>, input: SettingsInput) -> R<SettingsDto> {
    state.session.app()?.update_settings(input)
}

#[tauri::command]
#[specta::specta]
pub async fn home_nudges(state: State<'_, Desktop>, space_id: String) -> R<Vec<NudgeDto>> {
    state.session.app()?.home_nudges(&space_id)
}

#[tauri::command]
#[specta::specta]
pub async fn devices(state: State<'_, Desktop>) -> R<Vec<DeviceDto>> {
    state.session.app()?.devices()
}

/// Eksport va «Saqlash» oynasi. Bekor qilinsa — `None`; aks holda yozuvlar soni.
#[tauri::command]
#[specta::specta]
pub async fn export_baraka(
    handle: AppHandle,
    state: State<'_, Desktop>,
    input: ExportInput,
) -> R<Option<u32>> {
    let file = state.session.app()?.export_baraka(input)?;
    Ok(save_baraka(&handle, &file.bytes, &file.file_name)?.map(|_| file.rows))
}

#[tauri::command]
#[specta::specta]
pub async fn pick_baraka_file(handle: AppHandle) -> R<Option<PickedFile>> {
    let path = if let Some(dir) = e2e_files() {
        newest_baraka(&dir)
    } else {
        handle
            .dialog()
            .file()
            .add_filter("Baraka Dastur", &["baraka"])
            .blocking_pick_file()
            .map(|f| {
                f.into_path()
                    .map_err(|_| AppError::new("SAVE_PATH_INVALID"))
            })
            .transpose()?
    };
    let Some(path) = path else {
        return Ok(None);
    };
    Ok(Some(PickedFile {
        name: path
            .file_name()
            .map(|n| n.to_string_lossy().into_owned())
            .unwrap_or_default(),
        path: path.to_string_lossy().into_owned(),
    }))
}

#[tauri::command]
#[specta::specta]
pub async fn inspect_baraka(
    state: State<'_, Desktop>,
    path: String,
    password: String,
) -> R<ImportPreviewDto> {
    let bytes = read_baraka(&path)?;
    state.session.app()?.inspect_baraka(&bytes, &password)
}

#[tauri::command]
#[specta::specta]
pub async fn apply_baraka(
    state: State<'_, Desktop>,
    path: String,
    password: String,
    choices: Vec<ConflictChoiceInput>,
) -> R<ImportResultDto> {
    let bytes = read_baraka(&path)?;
    state
        .session
        .app()?
        .apply_baraka(&bytes, &password, choices)
}

/// Yangi qurilmani ulash: kod bilan shifrlangan fayl saqlanadi, QR va kod ko'rsatiladi.
#[tauri::command]
#[specta::specta]
pub async fn pairing_offer(
    handle: AppHandle,
    state: State<'_, Desktop>,
    input: PairingInput,
) -> R<Option<PairingView>> {
    let offer = state.session.app()?.pairing_offer(input)?;
    Ok(
        save_baraka(&handle, &offer.bytes, &offer.file_name)?.map(|file_name| PairingView {
            code: offer.code,
            qr_svg: offer.qr_svg,
            household_name: offer.household_name,
            file_name,
        }),
    )
}

/// O'rnatishda: mavjud xonadonga qo'shilish (ulash kodi) yoki zaxira nusxadan tiklash (parol).
#[tauri::command]
#[specta::specta]
pub async fn join_household(
    handle: AppHandle,
    state: State<'_, Desktop>,
    path: String,
    pin: String,
    input: JoinInput,
) -> R<SetupResult> {
    let bytes = read_baraka(&path)?;
    let secret = state.secrets.create()?;
    let result = state.session.join_household(&secret, &pin, &bytes, input)?;
    forward_events(&handle, &*state.session.app()?);
    Ok(result)
}

#[cfg(test)]
mod tests {
    use super::with_extension;
    use std::path::PathBuf;

    #[test]
    fn save_dialog_name_gets_extension() {
        let p = |s: &str| PathBuf::from(s);
        assert_eq!(
            with_extension(p("/d/noutbuk"), "baraka"),
            p("/d/noutbuk.baraka")
        );
        assert_eq!(with_extension(p("/d/x.BARAKA"), "baraka"), p("/d/x.BARAKA"));
        assert_eq!(
            with_extension(p("/d/x.txt"), "baraka"),
            p("/d/x.txt.baraka")
        );
        assert_eq!(with_extension(p("/d/smeta.pdf"), "pdf"), p("/d/smeta.pdf"));
    }
}
