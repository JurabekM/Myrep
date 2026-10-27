use std::path::Path;
use std::sync::Arc;

use baraka_agreements::AgreementDraft;
use baraka_app::*;
use serde::{de::DeserializeOwned, Serialize};
use zeroize::Zeroize;

use crate::frb_generated::StreamSink;

/// Android avto-qulf vaqti (7.4): fonga o'tgandan 2 daqiqa.
const IDLE_LOCK_MINUTES: i64 = 2;

pub fn core_version() -> String {
    baraka_app::core_version().to_string()
}

/// Oltin vektor case'i (12.1: vektorlar Dart'dan ham — DTO va string-pul o'tkazishdagi xatolarni
/// ushlaydi). `input_json` → yadro natijasi (JSON). Faqat `vectors` feature bilan (host testlari);
/// aks holda `VECTORS_DISABLED`.
pub fn run_vector(suite: String, input_json: String) -> Result<String, AppError> {
    #[cfg(feature = "vectors")]
    {
        let input: serde_json::Value = from_json(&input_json)?;
        to_json(&baraka_vectors::run_case(&suite, &input))
    }
    #[cfg(not(feature = "vectors"))]
    {
        let _ = (suite, input_json);
        Err(AppError::new("VECTORS_DISABLED"))
    }
}

/// Dart tomonida opaque obyekt. Platforma siri Kotlin `PlatformSecretApi` (Keystore) dan keladi.
pub struct BarakaCore {
    session: Session,
}

/// Kotlin'dan kelgan baytlar ishlatilgandan keyin xotirada qoldirilmaydi.
fn take_secret(mut bytes: Vec<u8>) -> Result<PlatformSecret, AppError> {
    let secret = PlatformSecret::from_slice(&bytes).map_err(AppError::from);
    bytes.zeroize();
    secret
}

/// `Answer<T>` (generik) va imzo chiziqlarini FRB Dart'ga tarjima qila olmaydi: sheriklik
/// shartnomasi va kelishuv tekshiruvi JSON orqali o'tadi. Shakl — serde (camelCase), desktop TS
/// turlari bilan aynan bir xil. Bu yerda faqat (de)serializatsiya — mantiq yo'q.
fn from_json<T: DeserializeOwned>(json: &str) -> Result<T, AppError> {
    serde_json::from_str(json).map_err(|_| AppError::new("INVALID_INPUT"))
}

fn to_json<T: Serialize>(value: &T) -> Result<String, AppError> {
    serde_json::to_string(value).map_err(|_| AppError::new("GENERIC"))
}

impl BarakaCore {
    /// `data_dir` — ilovaning private storage papkasi (`Context.filesDir`).
    pub fn new(data_dir: String) -> BarakaCore {
        BarakaCore {
            session: Session::new(
                Path::new(&data_dir),
                KdfParams::ANDROID,
                chrono::Duration::minutes(IDLE_LOCK_MINUTES),
                Arc::new(SystemClock),
                Arc::new(UuidV7Gen),
            ),
        }
    }

    pub fn status(&self) -> Result<SessionStatus, AppError> {
        self.session.status()
    }

    pub fn setup(
        &self,
        platform_secret: Vec<u8>,
        pin: String,
        input: BootstrapInput,
    ) -> Result<SetupResult, AppError> {
        self.session
            .setup(&take_secret(platform_secret)?, &pin, input)
    }

    pub fn unlock(&self, platform_secret: Vec<u8>, pin: String) -> Result<HouseholdDto, AppError> {
        self.session.unlock(&take_secret(platform_secret)?, &pin)
    }

    pub fn unlock_with_recovery(
        &self,
        platform_secret: Vec<u8>,
        recovery_code: String,
        new_pin: String,
    ) -> Result<HouseholdDto, AppError> {
        self.session
            .unlock_with_recovery(&take_secret(platform_secret)?, &recovery_code, &new_pin)
    }

    pub fn lock(&self) -> Result<(), AppError> {
        self.session.lock()
    }

    /// Ilova fonga o'tganda va qaytganda chaqiriladi.
    pub fn lock_if_idle(&self) -> Result<bool, AppError> {
        self.session.lock_if_idle()
    }

    pub fn household(&self) -> Result<HouseholdDto, AppError> {
        self.session.app()?.household()
    }

    pub fn categories(&self, space_id: String) -> Result<Vec<CategoryDto>, AppError> {
        self.session.app()?.categories(&space_id)
    }

    pub fn record_income(
        &self,
        space_id: String,
        input: NewIncomeInput,
    ) -> Result<IncomeRecordedDto, AppError> {
        self.session.app()?.record_income(&space_id, input)
    }

    pub fn allocate_to_vault(
        &self,
        space_id: String,
        income_id: String,
        amount: String,
    ) -> Result<VaultTxDto, AppError> {
        self.session
            .app()?
            .allocate_to_vault(&space_id, &income_id, &amount)
    }

    pub fn record_initial_balance(
        &self,
        space_id: String,
        amount: String,
    ) -> Result<VaultTxDto, AppError> {
        self.session
            .app()?
            .record_initial_balance(&space_id, &amount)
    }

    pub fn deposit_to_vault(
        &self,
        space_id: String,
        amount: String,
        note: Option<String>,
    ) -> Result<VaultTxDto, AppError> {
        self.session
            .app()?
            .deposit_to_vault(&space_id, &amount, note.as_deref())
    }

    /// «Kelajagim»dan pul olish: PIN qayta tasdiqlanadi va sabab majburiy.
    pub fn withdraw_from_vault(
        &self,
        platform_secret: Vec<u8>,
        space_id: String,
        pin: String,
        amount: String,
        reason: String,
    ) -> Result<VaultTxDto, AppError> {
        self.session
            .confirm_pin(&take_secret(platform_secret)?, &pin)?;
        self.session
            .app()?
            .withdraw_from_vault(&space_id, &amount, &reason)
    }

    pub fn vault(&self, space_id: String) -> Result<VaultDto, AppError> {
        self.session.app()?.vault(&space_id)
    }

    pub fn set_allocation_rule(
        &self,
        space_id: String,
        input: AllocationRuleInput,
    ) -> Result<AllocationRuleDto, AppError> {
        self.session.app()?.set_allocation_rule(&space_id, input)
    }

    pub fn record_expense(
        &self,
        space_id: String,
        input: NewExpenseInput,
    ) -> Result<ExpenseDto, AppError> {
        self.session.app()?.record_expense(&space_id, input)
    }

    pub fn monthly_summary(
        &self,
        space_id: String,
        date: Option<String>,
        balance_delta: Option<String>,
    ) -> Result<MonthlySummaryDto, AppError> {
        self.session
            .app()?
            .monthly_summary(&space_id, date.as_deref(), balance_delta.as_deref())
    }

    pub fn simulate_loan(&self, input: LoanSimulationInput) -> Result<LoanSimulationDto, AppError> {
        self.session.app()?.simulate_loan(input)
    }

    /// `draft_json` — `AgreementDraft`; natija — `Completeness` (JSON).
    pub fn check_agreement(
        &self,
        agreement_type: String,
        draft_json: String,
    ) -> Result<String, AppError> {
        let draft: AgreementDraft = from_json(&draft_json)?;
        to_json(
            &self
                .session
                .app()?
                .check_agreement(&agreement_type, draft)?,
        )
    }

    /// Qarz tilxati PDF baytlari (Dart tomonida `share_plus` / `printing` bilan ulashiladi).
    pub fn render_loan_receipt(&self, input: LoanReceiptInput) -> Result<Vec<u8>, AppError> {
        self.session.app()?.render_loan_receipt(input)
    }

    /// Qarzlar ekrani: inventar, bergan qarzlar, haqiqiy narx, oylik yuk, maqsadlar (U8).
    pub fn debts_overview(&self, space_id: String) -> Result<DebtsOverviewDto, AppError> {
        self.session.app()?.debts_overview(&space_id)
    }

    pub fn preview_borrow_check(
        &self,
        space_id: String,
        input: NewDebtInput,
    ) -> Result<BorrowCheckDto, AppError> {
        self.session.app()?.preview_borrow_check(&space_id, input)
    }

    /// O'qish puli qarzga (uy/SPEC 2G.2): «to'xta va o'yla» ogohlantirishlari (hech narsa saqlanmaydi).
    pub fn preview_study_debt(&self, input: StudyDebtInput) -> Result<Vec<String>, AppError> {
        self.session.app()?.preview_study_debt(input)
    }

    pub fn add_debt(&self, space_id: String, input: NewDebtInput) -> Result<DebtDto, AppError> {
        self.session.app()?.add_debt(&space_id, input)
    }

    pub fn add_receivable(
        &self,
        space_id: String,
        input: NewReceivableInput,
    ) -> Result<ReceivableDto, AppError> {
        self.session.app()?.add_receivable(&space_id, input)
    }

    pub fn record_repayment(
        &self,
        space_id: String,
        owner_type: String,
        id: String,
        input: RepaymentInput,
    ) -> Result<RepaymentResultDto, AppError> {
        self.session
            .app()?
            .record_repayment(&space_id, &owner_type, &id, input)
    }

    pub fn add_goal(&self, space_id: String, input: NewGoalInput) -> Result<GoalDto, AppError> {
        self.session.app()?.add_goal(&space_id, input)
    }

    pub fn delete_goal(&self, space_id: String, goal_id: String) -> Result<(), AppError> {
        self.session.app()?.delete_goal(&space_id, &goal_id)
    }

    /// Tilxatni saqlash: kelishuv + jurnal + qarz yozuvi.
    pub fn issue_loan_receipt(
        &self,
        space_id: String,
        input: IssueLoanReceiptInput,
    ) -> Result<IssuedReceiptDto, AppError> {
        self.session.app()?.issue_loan_receipt(&space_id, input)
    }

    /// Saqlangan tilxat PDF'i (joriy tekshirish kodi bilan).
    pub fn loan_receipt_pdf(
        &self,
        space_id: String,
        agreement_id: String,
    ) -> Result<Vec<u8>, AppError> {
        self.session
            .app()?
            .loan_receipt_pdf(&space_id, &agreement_id)
    }

    // U9: «Qarzdan chiqish» rejimi, rejalovchi, tartib, to'lovchilar, buyumlar.
    pub fn budget_mode(&self, space_id: String) -> Result<BudgetModeDto, AppError> {
        self.session.app()?.budget_mode(&space_id)
    }

    pub fn set_budget_mode(
        &self,
        space_id: String,
        input: BudgetModeInput,
    ) -> Result<BudgetModeDto, AppError> {
        self.session.app()?.set_budget_mode(&space_id, input)
    }

    pub fn payoff_planner(
        &self,
        space_id: String,
        input: PlannerInput,
    ) -> Result<PlannerDto, AppError> {
        self.session.app()?.payoff_planner(&space_id, input)
    }

    pub fn set_debt_order(&self, space_id: String, debt_ids: Vec<String>) -> Result<(), AppError> {
        self.session.app()?.set_debt_order(&space_id, debt_ids)
    }

    pub fn reset_debt_order(&self, space_id: String) -> Result<(), AppError> {
        self.session.app()?.reset_debt_order(&space_id)
    }

    pub fn add_contributor(
        &self,
        space_id: String,
        debt_id: String,
        input: NewContributorInput,
    ) -> Result<ContributorDto, AppError> {
        self.session
            .app()?
            .add_contributor(&space_id, &debt_id, input)
    }

    pub fn sellable_items(&self, space_id: String) -> Result<Vec<SellableItemDto>, AppError> {
        self.session.app()?.sellable_items(&space_id)
    }

    pub fn add_sellable_item(
        &self,
        space_id: String,
        input: NewSellableItemInput,
    ) -> Result<SellableItemDto, AppError> {
        self.session.app()?.add_sellable_item(&space_id, input)
    }

    pub fn sell_item(
        &self,
        space_id: String,
        item_id: String,
        input: SellItemInput,
    ) -> Result<SellResultDto, AppError> {
        self.session.app()?.sell_item(&space_id, &item_id, input)
    }

    // U10: marosim rejalovchisi.
    pub fn ceremonies(&self, space_id: String) -> Result<Vec<CeremonySummaryDto>, AppError> {
        self.session.app()?.ceremonies(&space_id)
    }

    pub fn ceremony(&self, space_id: String, ceremony_id: String) -> Result<CeremonyDto, AppError> {
        self.session.app()?.ceremony(&space_id, &ceremony_id)
    }

    pub fn create_ceremony(
        &self,
        space_id: String,
        input: NewCeremonyInput,
    ) -> Result<CeremonyDto, AppError> {
        self.session.app()?.create_ceremony(&space_id, input)
    }

    pub fn update_ceremony(
        &self,
        space_id: String,
        ceremony_id: String,
        input: CeremonyUpdateInput,
    ) -> Result<CeremonyDto, AppError> {
        self.session
            .app()?
            .update_ceremony(&space_id, &ceremony_id, input)
    }

    pub fn add_scenario(
        &self,
        space_id: String,
        ceremony_id: String,
        input: ScenarioInput,
    ) -> Result<CeremonyDto, AppError> {
        self.session
            .app()?
            .add_scenario(&space_id, &ceremony_id, input)
    }

    pub fn update_scenario(
        &self,
        space_id: String,
        ceremony_id: String,
        scenario_id: String,
        input: ScenarioInput,
    ) -> Result<CeremonyDto, AppError> {
        self.session
            .app()?
            .update_scenario(&space_id, &ceremony_id, &scenario_id, input)
    }

    pub fn delete_scenario(
        &self,
        space_id: String,
        ceremony_id: String,
        scenario_id: String,
    ) -> Result<CeremonyDto, AppError> {
        self.session
            .app()?
            .delete_scenario(&space_id, &ceremony_id, &scenario_id)
    }

    pub fn select_scenario(
        &self,
        space_id: String,
        ceremony_id: String,
        scenario_id: String,
    ) -> Result<CeremonyDto, AppError> {
        self.session
            .app()?
            .select_scenario(&space_id, &ceremony_id, &scenario_id)
    }

    pub fn add_ceremony_line(
        &self,
        space_id: String,
        ceremony_id: String,
        scenario_id: String,
        input: NewCeremonyLineInput,
    ) -> Result<CeremonyDto, AppError> {
        self.session
            .app()?
            .add_ceremony_line(&space_id, &ceremony_id, &scenario_id, input)
    }

    pub fn delete_ceremony_line(
        &self,
        space_id: String,
        ceremony_id: String,
        line_id: String,
    ) -> Result<CeremonyDto, AppError> {
        self.session
            .app()?
            .delete_ceremony_line(&space_id, &ceremony_id, &line_id)
    }

    pub fn save_discussion(
        &self,
        space_id: String,
        ceremony_id: String,
        answers: Vec<DiscussionAnswerDto>,
    ) -> Result<CeremonyDto, AppError> {
        self.session
            .app()?
            .save_discussion(&space_id, &ceremony_id, answers)
    }

    pub fn agree_discussion(
        &self,
        space_id: String,
        ceremony_id: String,
        member_id: String,
    ) -> Result<CeremonyDto, AppError> {
        self.session
            .app()?
            .agree_discussion(&space_id, &ceremony_id, &member_id)
    }

    pub fn confirm_ceremony(
        &self,
        space_id: String,
        ceremony_id: String,
    ) -> Result<CeremonyDto, AppError> {
        self.session
            .app()?
            .confirm_ceremony(&space_id, &ceremony_id)
    }

    pub fn reopen_ceremony(
        &self,
        space_id: String,
        ceremony_id: String,
    ) -> Result<CeremonyDto, AppError> {
        self.session.app()?.reopen_ceremony(&space_id, &ceremony_id)
    }

    pub fn delete_ceremony(&self, space_id: String, ceremony_id: String) -> Result<(), AppError> {
        self.session.app()?.delete_ceremony(&space_id, &ceremony_id)
    }

    pub fn add_goal_contribution(
        &self,
        space_id: String,
        goal_id: String,
        input: NewGoalContributionInput,
    ) -> Result<GoalDto, AppError> {
        self.session
            .app()?
            .add_goal_contribution(&space_id, &goal_id, input)
    }

    /// Marosim smetasi PDF baytlari (Dart tomonida ulashiladi yoki chop etiladi).
    pub fn ceremony_estimate_pdf(
        &self,
        space_id: String,
        ceremony_id: String,
    ) -> Result<Vec<u8>, AppError> {
        self.session
            .app()?
            .ceremony_estimate_pdf(&space_id, &ceremony_id)
    }

    // U11: sheriklik (mudoraba / musharaka), shartnoma, imzolar, darvoza.
    pub fn partnerships(&self, space_id: String) -> Result<Vec<PartnershipSummaryDto>, AppError> {
        self.session.app()?.partnerships(&space_id)
    }

    pub fn partnership(
        &self,
        space_id: String,
        partnership_id: String,
    ) -> Result<String, AppError> {
        to_json(
            &self
                .session
                .app()?
                .partnership(&space_id, &partnership_id)?,
        )
    }

    pub fn readiness_gate(&self, space_id: String) -> Result<GateDto, AppError> {
        self.session.app()?.readiness_gate(&space_id)
    }

    pub fn create_partnership(
        &self,
        space_id: String,
        input_json: String,
    ) -> Result<String, AppError> {
        let input: PartnershipInput = from_json(&input_json)?;
        to_json(&self.session.app()?.create_partnership(&space_id, input)?)
    }

    pub fn update_partnership(
        &self,
        space_id: String,
        partnership_id: String,
        input_json: String,
    ) -> Result<String, AppError> {
        let input: PartnershipInput = from_json(&input_json)?;
        to_json(
            &self
                .session
                .app()?
                .update_partnership(&space_id, &partnership_id, input)?,
        )
    }

    /// Imzo shu qurilmada chiziladi: nuqtalar 0..=1000 × 0..=400 maydonda.
    pub fn sign_partnership(
        &self,
        space_id: String,
        partnership_id: String,
        input_json: String,
    ) -> Result<String, AppError> {
        let input: SignInput = from_json(&input_json)?;
        to_json(
            &self
                .session
                .app()?
                .sign_partnership(&space_id, &partnership_id, input)?,
        )
    }

    pub fn acknowledge_not_debt(
        &self,
        space_id: String,
        partnership_id: String,
    ) -> Result<String, AppError> {
        to_json(
            &self
                .session
                .app()?
                .acknowledge_not_debt(&space_id, &partnership_id)?,
        )
    }

    pub fn consent_partnership(
        &self,
        space_id: String,
        partnership_id: String,
        member_id: String,
    ) -> Result<String, AppError> {
        to_json(
            &self
                .session
                .app()?
                .consent_partnership(&space_id, &partnership_id, &member_id)?,
        )
    }

    pub fn activate_partnership(
        &self,
        space_id: String,
        partnership_id: String,
    ) -> Result<String, AppError> {
        to_json(
            &self
                .session
                .app()?
                .activate_partnership(&space_id, &partnership_id)?,
        )
    }

    pub fn close_partnership(
        &self,
        space_id: String,
        partnership_id: String,
    ) -> Result<String, AppError> {
        to_json(
            &self
                .session
                .app()?
                .close_partnership(&space_id, &partnership_id)?,
        )
    }

    pub fn delete_partnership(
        &self,
        space_id: String,
        partnership_id: String,
    ) -> Result<(), AppError> {
        self.session
            .app()?
            .delete_partnership(&space_id, &partnership_id)
    }

    /// Sheriklik shartnomasi PDF baytlari.
    pub fn partnership_pdf(
        &self,
        space_id: String,
        partnership_id: String,
    ) -> Result<Vec<u8>, AppError> {
        self.session
            .app()?
            .partnership_pdf(&space_id, &partnership_id)
    }

    // U12: kassa daftari, davr taqsimoti, «Hunardan ishga», taklif tekshiruvi.
    pub fn venture_ledger(
        &self,
        space_id: String,
        partnership_id: String,
    ) -> Result<VentureLedgerDto, AppError> {
        self.session
            .app()?
            .venture_ledger(&space_id, &partnership_id)
    }

    /// Chek yoki dalil baytlari Dart tomonida tanlangan fayldan o'qiladi.
    pub fn add_venture_entry(
        &self,
        space_id: String,
        partnership_id: String,
        input: VentureEntryInput,
    ) -> Result<VentureLedgerDto, AppError> {
        self.session
            .app()?
            .add_venture_entry(&space_id, &partnership_id, input)
    }

    pub fn venture_attachment(
        &self,
        space_id: String,
        partnership_id: String,
        attachment_id: String,
    ) -> Result<AttachmentDto, AppError> {
        self.session
            .app()?
            .venture_attachment(&space_id, &partnership_id, &attachment_id)
    }

    pub fn venture_period_preview(
        &self,
        space_id: String,
        partnership_id: String,
        input: ClosePeriodInput,
    ) -> Result<VenturePeriodDto, AppError> {
        self.session
            .app()?
            .venture_period_preview(&space_id, &partnership_id, input)
    }

    pub fn close_venture_period(
        &self,
        space_id: String,
        partnership_id: String,
        input: ClosePeriodInput,
    ) -> Result<VentureLedgerDto, AppError> {
        self.session
            .app()?
            .close_venture_period(&space_id, &partnership_id, input)
    }

    /// Sherik uchun davr hisoboti PDF baytlari.
    pub fn venture_period_pdf(
        &self,
        space_id: String,
        partnership_id: String,
        period_id: String,
    ) -> Result<Vec<u8>, AppError> {
        self.session
            .app()?
            .venture_period_pdf(&space_id, &partnership_id, &period_id)
    }

    pub fn skills(&self, space_id: String) -> Result<Vec<SkillDto>, AppError> {
        self.session.app()?.skills(&space_id)
    }

    pub fn add_skill(
        &self,
        space_id: String,
        input: SkillInput,
    ) -> Result<Vec<SkillDto>, AppError> {
        self.session.app()?.add_skill(&space_id, input)
    }

    pub fn delete_skill(
        &self,
        space_id: String,
        skill_id: String,
    ) -> Result<Vec<SkillDto>, AppError> {
        self.session.app()?.delete_skill(&space_id, &skill_id)
    }

    pub fn venture_ideas(&self, space_id: String) -> Result<Vec<VentureIdeaDto>, AppError> {
        self.session.app()?.venture_ideas(&space_id)
    }

    pub fn create_venture_idea(
        &self,
        space_id: String,
        input: VentureIdeaInput,
    ) -> Result<VentureIdeaDto, AppError> {
        self.session.app()?.create_venture_idea(&space_id, input)
    }

    pub fn update_venture_idea(
        &self,
        space_id: String,
        idea_id: String,
        input: VentureIdeaInput,
    ) -> Result<VentureIdeaDto, AppError> {
        self.session
            .app()?
            .update_venture_idea(&space_id, &idea_id, input)
    }

    pub fn delete_venture_idea(&self, space_id: String, idea_id: String) -> Result<(), AppError> {
        self.session.app()?.delete_venture_idea(&space_id, &idea_id)
    }

    pub fn draft_partnership_from_idea(
        &self,
        space_id: String,
        idea_id: String,
        input: IdeaDraftInput,
    ) -> Result<String, AppError> {
        to_json(
            &self
                .session
                .app()?
                .draft_partnership_from_idea(&space_id, &idea_id, input)?,
        )
    }

    /// «Kafolatlangan foyda» detektori — ilovaning istalgan joyidan.
    pub fn check_offer(&self, input: OfferAnswersInput) -> Result<OfferCheckDto, AppError> {
        self.session.app()?.check_offer(input)
    }

    // U13: vazifa hodisalari, ochiq hisob ko'rigi, «katta foyda», nizo va hakam, yillik
    // yangilash, oilaviy kelishuvlar va kelishuvlar markazi.
    pub fn governance(
        &self,
        space_id: String,
        partnership_id: String,
    ) -> Result<GovernanceDto, AppError> {
        self.session.app()?.governance(&space_id, &partnership_id)
    }

    pub fn report_duty_incident(
        &self,
        space_id: String,
        partnership_id: String,
        input: IncidentInput,
    ) -> Result<GovernanceDto, AppError> {
        self.session
            .app()?
            .report_duty_incident(&space_id, &partnership_id, input)
    }

    pub fn resolve_duty_incident(
        &self,
        space_id: String,
        partnership_id: String,
        incident_id: String,
        note: String,
    ) -> Result<GovernanceDto, AppError> {
        self.session
            .app()?
            .resolve_duty_incident(&space_id, &partnership_id, &incident_id, &note)
    }

    pub fn review_draft(
        &self,
        space_id: String,
        partnership_id: String,
        to_on: String,
    ) -> Result<ReviewDraftDto, AppError> {
        self.session
            .app()?
            .review_draft(&space_id, &partnership_id, &to_on)
    }

    pub fn hold_review(
        &self,
        space_id: String,
        partnership_id: String,
        input: HoldReviewInput,
    ) -> Result<GovernanceDto, AppError> {
        self.session
            .app()?
            .hold_review(&space_id, &partnership_id, input)
    }

    /// Ko'rik bayonnomasi PDF baytlari (zanjir boshi QR bilan).
    pub fn review_pdf(
        &self,
        space_id: String,
        partnership_id: String,
        review_id: String,
    ) -> Result<Vec<u8>, AppError> {
        self.session
            .app()?
            .review_pdf(&space_id, &partnership_id, &review_id)
    }

    pub fn acknowledge_spike_reread(
        &self,
        space_id: String,
        partnership_id: String,
        party_id: String,
    ) -> Result<VentureLedgerDto, AppError> {
        self.session
            .app()?
            .acknowledge_spike_reread(&space_id, &partnership_id, &party_id)
    }

    pub fn open_partnership_dispute(
        &self,
        space_id: String,
        partnership_id: String,
        input: OpenDisputeInput,
    ) -> Result<GovernanceDto, AppError> {
        self.session
            .app()?
            .open_partnership_dispute(&space_id, &partnership_id, input)
    }

    pub fn add_dispute_claim(
        &self,
        space_id: String,
        partnership_id: String,
        dispute_id: String,
        input: DisputeClaimInput,
    ) -> Result<GovernanceDto, AppError> {
        self.session
            .app()?
            .add_dispute_claim(&space_id, &partnership_id, &dispute_id, input)
    }

    pub fn record_arbiter_decision(
        &self,
        space_id: String,
        partnership_id: String,
        dispute_id: String,
        input: DecisionInput,
    ) -> Result<GovernanceDto, AppError> {
        self.session
            .app()?
            .record_arbiter_decision(&space_id, &partnership_id, &dispute_id, input)
    }

    /// «Hakam uchun ish papkasi» PDF baytlari.
    pub fn dispute_folder_pdf(
        &self,
        space_id: String,
        partnership_id: String,
        dispute_id: String,
    ) -> Result<Vec<u8>, AppError> {
        self.session
            .app()?
            .dispute_folder_pdf(&space_id, &partnership_id, &dispute_id)
    }

    pub fn renew_partnership(
        &self,
        space_id: String,
        partnership_id: String,
    ) -> Result<String, AppError> {
        to_json(
            &self
                .session
                .app()?
                .renew_partnership(&space_id, &partnership_id)?,
        )
    }

    pub fn family_agreements(&self, space_id: String) -> Result<Vec<FamilyAgreementDto>, AppError> {
        self.session.app()?.family_agreements(&space_id)
    }

    pub fn create_family_agreement(
        &self,
        space_id: String,
        input: FamilyAgreementInput,
    ) -> Result<FamilyAgreementDto, AppError> {
        self.session
            .app()?
            .create_family_agreement(&space_id, input)
    }

    pub fn update_family_agreement(
        &self,
        space_id: String,
        id: String,
        input: FamilyAgreementInput,
    ) -> Result<FamilyAgreementDto, AppError> {
        self.session
            .app()?
            .update_family_agreement(&space_id, &id, input)
    }

    /// Katta a'zoning tasdig'i: PIN qayta so'raladi.
    pub fn confirm_family_agreement(
        &self,
        platform_secret: Vec<u8>,
        space_id: String,
        pin: String,
        id: String,
        member_id: String,
    ) -> Result<FamilyAgreementDto, AppError> {
        self.session
            .confirm_pin(&take_secret(platform_secret)?, &pin)?;
        self.session
            .app()?
            .confirm_family_agreement(&space_id, &id, &member_id)
    }

    pub fn delete_family_agreement(&self, space_id: String, id: String) -> Result<(), AppError> {
        self.session.app()?.delete_family_agreement(&space_id, &id)
    }

    pub fn agreement_reminders(&self, space_id: String) -> Result<Vec<ReminderDto>, AppError> {
        self.session.app()?.agreement_reminders(&space_id)
    }

    pub fn agreements_center(
        &self,
        space_id: String,
    ) -> Result<Vec<AgreementSummaryDto>, AppError> {
        self.session.app()?.agreements_center(&space_id)
    }

    // U14: `.baraka` eksport/import va qurilmalarni ulash.
    /// Mavjud xonadonga qo'shilish (ulash kodi) yoki zaxira nusxadan tiklash (parol).
    pub fn join_household(
        &self,
        platform_secret: Vec<u8>,
        pin: String,
        file: Vec<u8>,
        input: JoinInput,
    ) -> Result<SetupResult, AppError> {
        self.session
            .join_household(&take_secret(platform_secret)?, &pin, &file, input)
    }

    // ---- K1: Kasb-kor «ikki cho'ntak» ----

    pub fn kk_overview(
        &self,
        space_id: String,
        date: Option<String>,
    ) -> Result<KkOverviewDto, AppError> {
        self.session.app()?.kk_overview(&space_id, date)
    }

    pub fn kk_set_owner_salary(
        &self,
        space_id: String,
        amount: String,
    ) -> Result<KkOverviewDto, AppError> {
        self.session.app()?.kk_set_owner_salary(&space_id, amount)
    }

    pub fn kk_record_sale(
        &self,
        space_id: String,
        input: KkSaleInput,
    ) -> Result<KkOverviewDto, AppError> {
        self.session.app()?.kk_record_sale(&space_id, input)
    }

    pub fn kk_record_move(
        &self,
        space_id: String,
        input: KkMoveInput,
    ) -> Result<KkOverviewDto, AppError> {
        self.session.app()?.kk_record_move(&space_id, input)
    }

    /// Maosh Uy makoniga: Kasb-kor va Uy yozuvlari bitta tranzaksiyada.
    pub fn kk_pay_owner_salary(
        &self,
        space_id: String,
        input: KkSalaryInput,
    ) -> Result<KkSalaryPaidDto, AppError> {
        self.session.app()?.kk_pay_owner_salary(&space_id, input)
    }

    // ---- K2: haqiqiy foyda, uskunalar, oilaviy mehnat, buyurtma kalkulyatori ----

    pub fn kk_set_owner_labor(
        &self,
        space_id: String,
        amount: String,
    ) -> Result<KkOverviewDto, AppError> {
        self.session.app()?.kk_set_owner_labor(&space_id, amount)
    }

    pub fn kk_equipment(&self, space_id: String) -> Result<Vec<KkEquipmentDto>, AppError> {
        self.session.app()?.kk_equipment(&space_id)
    }

    pub fn kk_add_equipment(
        &self,
        space_id: String,
        input: KkEquipmentInput,
    ) -> Result<Vec<KkEquipmentDto>, AppError> {
        self.session.app()?.kk_add_equipment(&space_id, input)
    }

    pub fn kk_dispose_equipment(
        &self,
        space_id: String,
        id: String,
        input: KkDisposeInput,
    ) -> Result<Vec<KkEquipmentDto>, AppError> {
        self.session
            .app()?
            .kk_dispose_equipment(&space_id, &id, input)
    }

    pub fn kk_delete_equipment(
        &self,
        space_id: String,
        id: String,
    ) -> Result<Vec<KkEquipmentDto>, AppError> {
        self.session.app()?.kk_delete_equipment(&space_id, &id)
    }

    pub fn kk_family_labor(
        &self,
        space_id: String,
        date: Option<String>,
    ) -> Result<Vec<KkFamilyLaborDto>, AppError> {
        self.session.app()?.kk_family_labor(&space_id, date)
    }

    pub fn kk_add_family_labor(
        &self,
        space_id: String,
        input: KkFamilyLaborInput,
    ) -> Result<Vec<KkFamilyLaborDto>, AppError> {
        self.session.app()?.kk_add_family_labor(&space_id, input)
    }

    pub fn kk_delete_family_labor(
        &self,
        space_id: String,
        id: String,
    ) -> Result<Vec<KkFamilyLaborDto>, AppError> {
        self.session.app()?.kk_delete_family_labor(&space_id, &id)
    }

    pub fn kk_order_quote(
        &self,
        space_id: String,
        input: KkQuoteInput,
    ) -> Result<KkQuoteDto, AppError> {
        self.session.app()?.kk_order_quote(&space_id, input)
    }

    // ---- K3: «Hisob kuni» ----

    pub fn kk_close_rules(&self, space_id: String) -> Result<KkCloseRulesDto, AppError> {
        self.session.app()?.kk_close_rules(&space_id)
    }

    pub fn kk_set_close_rules(
        &self,
        space_id: String,
        input: KkCloseRulesInput,
    ) -> Result<KkCloseRulesDto, AppError> {
        self.session.app()?.kk_set_close_rules(&space_id, input)
    }

    pub fn kk_close_draft(
        &self,
        space_id: String,
        period_start: Option<String>,
    ) -> Result<KkCloseDraftDto, AppError> {
        self.session.app()?.kk_close_draft(&space_id, period_start)
    }

    /// Bayonnoma o'zgarmas; yopilgan oyga keyin yozib bo'lmaydi.
    pub fn kk_close_month(
        &self,
        space_id: String,
        input: KkCloseInput,
    ) -> Result<KkMonthCloseDto, AppError> {
        self.session.app()?.kk_close_month(&space_id, input)
    }

    pub fn kk_month_closes(&self, space_id: String) -> Result<Vec<KkMonthCloseDto>, AppError> {
        self.session.app()?.kk_month_closes(&space_id)
    }

    pub fn kk_month_close_pdf(
        &self,
        space_id: String,
        close_id: String,
    ) -> Result<Vec<u8>, AppError> {
        self.session.app()?.kk_month_close_pdf(&space_id, &close_id)
    }

    // ---- K4: kunlik kassa yopish va nasiya daftari ----

    pub fn kk_cash_draft(
        &self,
        space_id: String,
        day: Option<String>,
        counted: Option<String>,
    ) -> Result<KkCashDraftDto, AppError> {
        self.session.app()?.kk_cash_draft(&space_id, day, counted)
    }

    pub fn kk_close_cash_day(
        &self,
        space_id: String,
        input: KkCashCloseInput,
    ) -> Result<KkCashDayDto, AppError> {
        self.session.app()?.kk_close_cash_day(&space_id, input)
    }

    pub fn kk_cash_days(&self, space_id: String) -> Result<Vec<KkCashDayDto>, AppError> {
        self.session.app()?.kk_cash_days(&space_id)
    }

    pub fn kk_customers(&self, space_id: String) -> Result<Vec<KkCustomerDto>, AppError> {
        self.session.app()?.kk_customers(&space_id)
    }

    pub fn kk_add_customer(
        &self,
        space_id: String,
        input: KkCustomerInput,
    ) -> Result<Vec<KkCustomerDto>, AppError> {
        self.session.app()?.kk_add_customer(&space_id, input)
    }

    pub fn kk_credit_book(&self, space_id: String) -> Result<KkCreditBookDto, AppError> {
        self.session.app()?.kk_credit_book(&space_id)
    }

    pub fn kk_add_credit_sale(
        &self,
        space_id: String,
        input: KkCreditSaleInput,
    ) -> Result<KkCreditBookDto, AppError> {
        self.session.app()?.kk_add_credit_sale(&space_id, input)
    }

    pub fn kk_credit_payment(
        &self,
        space_id: String,
        sale_id: String,
        input: KkCreditPaymentInput,
    ) -> Result<KkCreditBookDto, AppError> {
        self.session
            .app()?
            .kk_credit_payment(&space_id, &sale_id, input)
    }

    pub fn kk_credit_forgive(
        &self,
        space_id: String,
        sale_id: String,
        input: KkCreditForgiveInput,
    ) -> Result<KkCreditBookDto, AppError> {
        self.session
            .app()?
            .kk_credit_forgive(&space_id, &sale_id, input)
    }

    pub fn kk_credit_extend(
        &self,
        space_id: String,
        sale_id: String,
        input: KkCreditExtendInput,
    ) -> Result<KkCreditBookDto, AppError> {
        self.session
            .app()?
            .kk_credit_extend(&space_id, &sale_id, input)
    }

    pub fn kk_credit_mark(
        &self,
        space_id: String,
        sale_id: String,
        talk: bool,
    ) -> Result<KkCreditBookDto, AppError> {
        self.session
            .app()?
            .kk_credit_mark(&space_id, &sale_id, talk)
    }

    pub fn kk_delete_credit_sale(
        &self,
        space_id: String,
        sale_id: String,
    ) -> Result<KkCreditBookDto, AppError> {
        self.session
            .app()?
            .kk_delete_credit_sale(&space_id, &sale_id)
    }

    pub fn kk_stock(&self, space_id: String) -> Result<KkStockDto, AppError> {
        self.session.app()?.kk_stock(&space_id)
    }

    pub fn kk_add_item(
        &self,
        space_id: String,
        input: KkItemInput,
    ) -> Result<KkStockDto, AppError> {
        self.session.app()?.kk_add_item(&space_id, input)
    }

    pub fn kk_update_item(
        &self,
        space_id: String,
        item_id: String,
        input: KkItemInput,
    ) -> Result<KkStockDto, AppError> {
        self.session
            .app()?
            .kk_update_item(&space_id, &item_id, input)
    }

    pub fn kk_delete_item(
        &self,
        space_id: String,
        item_id: String,
    ) -> Result<KkStockDto, AppError> {
        self.session.app()?.kk_delete_item(&space_id, &item_id)
    }

    pub fn kk_stock_move(
        &self,
        space_id: String,
        item_id: String,
        input: KkStockMoveInput,
    ) -> Result<KkStockDto, AppError> {
        self.session
            .app()?
            .kk_stock_move(&space_id, &item_id, input)
    }

    pub fn kk_staff(&self, space_id: String) -> Result<KkStaffDto, AppError> {
        self.session.app()?.kk_staff(&space_id)
    }

    pub fn kk_add_employee(
        &self,
        space_id: String,
        input: KkEmployeeInput,
    ) -> Result<KkStaffDto, AppError> {
        self.session.app()?.kk_add_employee(&space_id, input)
    }

    pub fn kk_update_employee(
        &self,
        space_id: String,
        id: String,
        input: KkEmployeeInput,
    ) -> Result<KkStaffDto, AppError> {
        self.session
            .app()?
            .kk_update_employee(&space_id, &id, input)
    }

    pub fn kk_staff_advance(
        &self,
        space_id: String,
        id: String,
        input: KkAdvanceInput,
    ) -> Result<KkStaffDto, AppError> {
        self.session.app()?.kk_staff_advance(&space_id, &id, input)
    }

    pub fn kk_staff_pay(
        &self,
        space_id: String,
        id: String,
        input: KkWageInput,
    ) -> Result<KkStaffDto, AppError> {
        self.session.app()?.kk_staff_pay(&space_id, &id, input)
    }

    pub fn kk_payslip_pdf(
        &self,
        space_id: String,
        id: String,
        month: String,
    ) -> Result<Vec<u8>, AppError> {
        self.session.app()?.kk_payslip_pdf(&space_id, &id, month)
    }

    pub fn kk_suppliers(&self, space_id: String) -> Result<KkSuppliersDto, AppError> {
        self.session.app()?.kk_suppliers(&space_id)
    }

    pub fn kk_add_supplier(
        &self,
        space_id: String,
        input: KkSupplierInput,
    ) -> Result<KkSuppliersDto, AppError> {
        self.session.app()?.kk_add_supplier(&space_id, input)
    }

    pub fn kk_update_supplier(
        &self,
        space_id: String,
        id: String,
        input: KkSupplierInput,
    ) -> Result<KkSuppliersDto, AppError> {
        self.session
            .app()?
            .kk_update_supplier(&space_id, &id, input)
    }

    pub fn kk_supply_delivery(
        &self,
        space_id: String,
        id: String,
        input: KkDeliveryInput,
    ) -> Result<KkSuppliersDto, AppError> {
        self.session
            .app()?
            .kk_supply_delivery(&space_id, &id, input)
    }

    pub fn kk_supply_payment(
        &self,
        space_id: String,
        id: String,
        input: KkSupplyPaymentInput,
    ) -> Result<KkSuppliersDto, AppError> {
        self.session.app()?.kk_supply_payment(&space_id, &id, input)
    }

    pub fn kk_sign_agreement(
        &self,
        space_id: String,
        id: String,
        input: KkSignInput,
    ) -> Result<(), AppError> {
        self.session.app()?.kk_sign_agreement(&space_id, &id, input)
    }

    pub fn kk_end_agreement(
        &self,
        space_id: String,
        id: String,
        ended_on: Option<String>,
    ) -> Result<(), AppError> {
        self.session
            .app()?
            .kk_end_agreement(&space_id, &id, ended_on)
    }

    pub fn kk_delete_agreement(&self, space_id: String, id: String) -> Result<(), AppError> {
        self.session.app()?.kk_delete_agreement(&space_id, &id)
    }

    pub fn kk_agreement_pdf(&self, space_id: String, id: String) -> Result<Vec<u8>, AppError> {
        self.session.app()?.kk_agreement_pdf(&space_id, &id)
    }

    pub fn kk_gate(&self, space_id: String) -> Result<KkGateDto, AppError> {
        self.session.app()?.kk_gate(&space_id)
    }

    pub fn kk_use_fund(
        &self,
        space_id: String,
        input: KkFundUseInput,
    ) -> Result<KkGateDto, AppError> {
        self.session.app()?.kk_use_fund(&space_id, input)
    }

    pub fn kk_growth_settings(&self, space_id: String) -> Result<KkGrowthSettingsDto, AppError> {
        self.session.app()?.kk_growth_settings(&space_id)
    }

    pub fn kk_set_growth_settings(
        &self,
        space_id: String,
        input: KkGrowthSettingsInput,
    ) -> Result<KkGrowthSettingsDto, AppError> {
        self.session.app()?.kk_set_growth_settings(&space_id, input)
    }

    pub fn kk_scale(&self, space_id: String) -> Result<KkScaleDto, AppError> {
        self.session.app()?.kk_scale(&space_id)
    }

    pub fn kk_scale_check(
        &self,
        space_id: String,
        input: KkScaleCheckInput,
    ) -> Result<KkScaleDto, AppError> {
        self.session.app()?.kk_scale_check(&space_id, input)
    }

    pub fn kk_zakat_draft(
        &self,
        space_id: String,
        input: KkZakatInput,
    ) -> Result<KkZakatDto, AppError> {
        self.session.app()?.kk_zakat_draft(&space_id, input)
    }

    pub fn kk_save_zakat(
        &self,
        space_id: String,
        input: KkZakatInput,
    ) -> Result<Vec<KkZakatCalcDto>, AppError> {
        self.session.app()?.kk_save_zakat(&space_id, input)
    }

    pub fn kk_zakat_history(&self, space_id: String) -> Result<Vec<KkZakatCalcDto>, AppError> {
        self.session.app()?.kk_zakat_history(&space_id)
    }

    pub fn kk_inventory(
        &self,
        space_id: String,
        input: KkInventoryInput,
    ) -> Result<KkStockDto, AppError> {
        self.session.app()?.kk_inventory(&space_id, input)
    }

    pub fn kk_stock_counts(&self, space_id: String) -> Result<Vec<KkStockCountDto>, AppError> {
        self.session.app()?.kk_stock_counts(&space_id)
    }

    // ---- K8: ko'p qurilma va rollar (ADR-0003) ----

    pub fn device_role(&self) -> Result<DeviceRoleDto, AppError> {
        self.session.app()?.device_role()
    }

    pub fn revoke_device(&self, device_id: String) -> Result<Vec<DeviceDto>, AppError> {
        self.session.app()?.revoke_device(&device_id)
    }

    pub fn kk_catalog(&self, space_id: String) -> Result<Vec<KkCatalogItemDto>, AppError> {
        self.session.app()?.kk_catalog(&space_id)
    }

    pub fn kk_seller_sale(
        &self,
        space_id: String,
        input: KkSellerSaleInput,
    ) -> Result<KkSellerDayDto, AppError> {
        self.session.app()?.kk_seller_sale(&space_id, input)
    }

    pub fn kk_seller_day(&self, space_id: String) -> Result<KkSellerDayDto, AppError> {
        self.session.app()?.kk_seller_day(&space_id)
    }

    pub fn kk_shift_draft(
        &self,
        space_id: String,
        input: KkShiftInput,
    ) -> Result<KkShiftDto, AppError> {
        self.session.app()?.kk_shift_draft(&space_id, input)
    }

    pub fn kk_close_shift(
        &self,
        space_id: String,
        input: KkShiftInput,
    ) -> Result<KkShiftDto, AppError> {
        self.session.app()?.kk_close_shift(&space_id, input)
    }

    pub fn kk_shifts(&self, space_id: String) -> Result<Vec<KkShiftRecordDto>, AppError> {
        self.session.app()?.kk_shifts(&space_id)
    }

    // ---- M1: Musofir makoni ----

    pub fn mf_overview(
        &self,
        space_id: String,
        date: Option<String>,
    ) -> Result<MfOverviewDto, AppError> {
        self.session.app()?.mf_overview(&space_id, date)
    }

    pub fn mf_set_settings(
        &self,
        space_id: String,
        input: MfSettingsInput,
    ) -> Result<MfOverviewDto, AppError> {
        self.session.app()?.mf_set_settings(&space_id, input)
    }

    pub fn mf_set_rate(
        &self,
        space_id: String,
        input: MfRateInput,
    ) -> Result<MfOverviewDto, AppError> {
        self.session.app()?.mf_set_rate(&space_id, input)
    }

    pub fn mf_record_income(
        &self,
        space_id: String,
        input: MfIncomeInput,
    ) -> Result<MfIncomeRecordedDto, AppError> {
        self.session.app()?.mf_record_income(&space_id, input)
    }

    pub fn mf_record_expense(
        &self,
        space_id: String,
        input: MfExpenseInput,
    ) -> Result<MfOverviewDto, AppError> {
        self.session.app()?.mf_record_expense(&space_id, input)
    }

    pub fn mf_record_move(
        &self,
        space_id: String,
        input: MfMoveInput,
    ) -> Result<MfOverviewDto, AppError> {
        self.session.app()?.mf_record_move(&space_id, input)
    }

    // ---- M2: «Ikki qirg'oq» ----

    pub fn mf_terms(&self, space_id: String) -> Result<MfTermsDto, AppError> {
        self.session.app()?.mf_terms(&space_id)
    }

    pub fn mf_set_terms(
        &self,
        space_id: String,
        input: MfTermsInput,
    ) -> Result<MfTermsDto, AppError> {
        self.session.app()?.mf_set_terms(&space_id, input)
    }

    pub fn mf_two_shores(&self, space_id: String) -> Result<MfTwoShoresDto, AppError> {
        self.session.app()?.mf_two_shores(&space_id)
    }

    pub fn mf_confirm_receipt(
        &self,
        space_id: String,
        move_id: String,
        input: MfReceiptInput,
    ) -> Result<MfTwoShoresDto, AppError> {
        self.session
            .app()?
            .mf_confirm_receipt(&space_id, &move_id, input)
    }

    pub fn mf_record_spend(
        &self,
        space_id: String,
        input: MfSpendInput,
    ) -> Result<MfTwoShoresDto, AppError> {
        self.session.app()?.mf_record_spend(&space_id, input)
    }

    // ---- M3: yo'l qarzi, «Qaytdim», katta qarorlar ----

    pub fn mf_travel_debt(&self, space_id: String) -> Result<MfTravelDebtDto, AppError> {
        self.session.app()?.mf_travel_debt(&space_id)
    }

    pub fn mf_set_travel_debt(
        &self,
        space_id: String,
        input: MfTravelDebtInput,
    ) -> Result<MfTravelDebtDto, AppError> {
        self.session.app()?.mf_set_travel_debt(&space_id, input)
    }

    pub fn mf_pay_debt(
        &self,
        space_id: String,
        input: MfDebtPaymentInput,
    ) -> Result<MfTwoShoresDto, AppError> {
        self.session.app()?.mf_pay_debt(&space_id, input)
    }

    pub fn mf_set_return(
        &self,
        space_id: String,
        input: MfReturnInput,
    ) -> Result<MfOverviewDto, AppError> {
        self.session.app()?.mf_set_return(&space_id, input)
    }

    pub fn mf_check_decision(
        &self,
        space_id: String,
        input: MfDecisionInput,
    ) -> Result<MfDecisionCheckDto, AppError> {
        self.session.app()?.mf_check_decision(&space_id, input)
    }

    pub fn mf_record_decision(
        &self,
        space_id: String,
        input: MfDecisionInput,
    ) -> Result<Vec<MfDecisionDto>, AppError> {
        self.session.app()?.mf_record_decision(&space_id, input)
    }

    pub fn mf_decisions(&self, space_id: String) -> Result<Vec<MfDecisionDto>, AppError> {
        self.session.app()?.mf_decisions(&space_id)
    }

    pub fn mf_decision_questions(&self, kind: String) -> Result<Vec<String>, AppError> {
        self.session.app()?.mf_decision_questions(&kind)
    }

    // ---- M4: zaxira pul, ish boshlash summasi, qaror natijasi ----

    pub fn mf_set_plan(
        &self,
        space_id: String,
        input: MfPlanInput,
    ) -> Result<MfOverviewDto, AppError> {
        self.session.app()?.mf_set_plan(&space_id, input)
    }

    pub fn mf_set_outcome(
        &self,
        space_id: String,
        decision_id: String,
        input: MfOutcomeInput,
    ) -> Result<Vec<MfDecisionDto>, AppError> {
        self.session
            .app()?
            .mf_set_outcome(&space_id, &decision_id, input)
    }

    // ---- U16: «O'zingizga sarmoya qiling» — soat qiymati, bilim rejasi, «Ilm zakoti» ----

    /// Kurs yoki ustoz taklifini tekshirish (umumiy detektorning `COURSE` turi).
    pub fn check_course(&self, input: CourseAnswersInput) -> Result<OfferCheckDto, AppError> {
        self.session.app()?.check_course(input)
    }

    pub fn hour_value_suggest(
        &self,
        space_id: String,
        member_id: String,
    ) -> Result<HourValueSuggestionDto, AppError> {
        self.session
            .app()?
            .hour_value_suggest(&space_id, &member_id)
    }

    pub fn hour_value_save(
        &self,
        space_id: String,
        input: HourValueInput,
    ) -> Result<HourValueDto, AppError> {
        self.session.app()?.hour_value_save(&space_id, input)
    }

    pub fn learning_plan_create(
        &self,
        space_id: String,
        input: LearningPlanInput,
    ) -> Result<LearningPlanDto, AppError> {
        self.session.app()?.learning_plan_create(&space_id, input)
    }

    pub fn learning_plan_set_status(
        &self,
        space_id: String,
        plan_id: String,
        status: String,
    ) -> Result<LearningPlanDto, AppError> {
        self.session
            .app()?
            .learning_plan_set_status(&space_id, &plan_id, &status)
    }

    pub fn learning_plan_result(
        &self,
        space_id: String,
        plan_id: String,
    ) -> Result<LearningResultDto, AppError> {
        self.session
            .app()?
            .learning_plan_result(&space_id, &plan_id)
    }

    pub fn study_log_add(
        &self,
        space_id: String,
        plan_id: String,
        input: StudyLogInput,
    ) -> Result<LearningPlanDto, AppError> {
        self.session
            .app()?
            .study_log_add(&space_id, &plan_id, input)
    }

    pub fn teaching_log_add(
        &self,
        space_id: String,
        input: TeachingLogInput,
    ) -> Result<TeachingLogDto, AppError> {
        self.session.app()?.teaching_log_add(&space_id, input)
    }

    pub fn learning_overview(
        &self,
        space_id: String,
        date: Option<String>,
    ) -> Result<LearningOverviewDto, AppError> {
        self.session
            .app()?
            .learning_overview(&space_id, date.as_deref())
    }

    // ---- K9: Kasb-kor «O'zingizga sarmoya qiling» — egasining soat qiymati, qarorlar, «Ilm zakoti» ----

    pub fn kk_owner_hour_suggest(
        &self,
        space_id: String,
    ) -> Result<KkOwnerHourSuggestionDto, AppError> {
        self.session.app()?.kk_owner_hour_suggest(&space_id)
    }

    pub fn kk_owner_hour_save(
        &self,
        space_id: String,
        input: KkOwnerHourInput,
    ) -> Result<KkOwnerHourDto, AppError> {
        self.session.app()?.kk_owner_hour_save(&space_id, input)
    }

    pub fn kk_delegate_calc(
        &self,
        space_id: String,
        input: KkDelegateInput,
    ) -> Result<KkDelegateResultDto, AppError> {
        self.session.app()?.kk_delegate_calc(&space_id, input)
    }

    pub fn kk_delegation_save(
        &self,
        space_id: String,
        input: KkDelegateInput,
    ) -> Result<KkDelegationDto, AppError> {
        self.session.app()?.kk_delegation_save(&space_id, input)
    }

    pub fn kk_delegation_delete(&self, space_id: String, id: String) -> Result<(), AppError> {
        self.session.app()?.kk_delegation_delete(&space_id, &id)
    }

    pub fn kk_teaching_add(
        &self,
        space_id: String,
        input: KkTeachingInput,
    ) -> Result<KkTeachingDto, AppError> {
        self.session.app()?.kk_teaching_add(&space_id, input)
    }

    pub fn kk_learning_overview(
        &self,
        space_id: String,
        date: Option<String>,
    ) -> Result<KkLearningOverviewDto, AppError> {
        self.session
            .app()?
            .kk_learning_overview(&space_id, date.as_deref())
    }

    // ---- M6: Musofir «O'zingizga sarmoya qiling» — soat qiymati, ikki maqsadli reja, «Ilm zakoti» ----

    pub fn mf_hour_suggest(&self, space_id: String) -> Result<MfHourSuggestionDto, AppError> {
        self.session.app()?.mf_hour_suggest(&space_id)
    }

    pub fn mf_hour_save(
        &self,
        space_id: String,
        input: MfHourInput,
    ) -> Result<MfHourDto, AppError> {
        self.session.app()?.mf_hour_save(&space_id, input)
    }

    pub fn mf_learning_plan_create(
        &self,
        space_id: String,
        input: MfLearningPlanInput,
    ) -> Result<MfLearningPlanDto, AppError> {
        self.session
            .app()?
            .mf_learning_plan_create(&space_id, input)
    }

    pub fn mf_learning_plan_set_status(
        &self,
        space_id: String,
        plan_id: String,
        status: String,
    ) -> Result<MfLearningPlanDto, AppError> {
        self.session
            .app()?
            .mf_learning_plan_set_status(&space_id, &plan_id, &status)
    }

    pub fn mf_learning_plan_result(
        &self,
        space_id: String,
        plan_id: String,
    ) -> Result<MfLearningResultDto, AppError> {
        self.session
            .app()?
            .mf_learning_plan_result(&space_id, &plan_id)
    }

    pub fn mf_teaching_add(
        &self,
        space_id: String,
        input: MfTeachingInput,
    ) -> Result<MfTeachingDto, AppError> {
        self.session.app()?.mf_teaching_add(&space_id, input)
    }

    pub fn mf_learning_overview(
        &self,
        space_id: String,
        date: Option<String>,
    ) -> Result<MfLearningOverviewDto, AppError> {
        self.session
            .app()?
            .mf_learning_overview(&space_id, date.as_deref())
    }

    // ---- U15: sozlamalar va bosh sahifa eslatmalari ----

    pub fn settings(&self) -> Result<SettingsDto, AppError> {
        self.session.app()?.settings()
    }

    /// Til faqat shu qurilmaga yoziladi; daromad ritmi va «qarzim bor» — xonadonniki.
    pub fn update_settings(&self, input: SettingsInput) -> Result<SettingsDto, AppError> {
        self.session.app()?.update_settings(input)
    }

    pub fn home_nudges(&self, space_id: String) -> Result<Vec<NudgeDto>, AppError> {
        self.session.app()?.home_nudges(&space_id)
    }

    pub fn devices(&self) -> Result<Vec<DeviceDto>, AppError> {
        self.session.app()?.devices()
    }

    /// Shifrlangan `.baraka` fayl baytlari (Dart tomonida ulashish oynasi bilan saqlanadi).
    pub fn export_baraka(&self, input: ExportInput) -> Result<ExportFileDto, AppError> {
        self.session.app()?.export_baraka(input)
    }

    pub fn inspect_baraka(
        &self,
        file: Vec<u8>,
        password: String,
    ) -> Result<ImportPreviewDto, AppError> {
        self.session.app()?.inspect_baraka(&file, &password)
    }

    pub fn apply_baraka(
        &self,
        file: Vec<u8>,
        password: String,
        choices: Vec<ConflictChoiceInput>,
    ) -> Result<ImportResultDto, AppError> {
        self.session.app()?.apply_baraka(&file, &password, choices)
    }

    /// Yangi qurilmani ulash: kod, QR (SVG) va shu kod bilan shifrlangan fayl. Rol bilan (K8) —
    /// sotuvchi yoki hisobchi qurilmasi uchun kamaytirilgan.
    pub fn pairing_offer(&self, input: PairingInput) -> Result<PairingOfferDto, AppError> {
        self.session.app()?.pairing_offer(input)
    }

    /// O'zgarish hodisalari: ochilgan ilovaning hodisalari Dart `Stream` iga uzatiladi
    /// (Riverpod provider'lari invalidatsiya qilinadi). Har `setup` / `unlock` dan keyin
    /// chaqiriladi; qulflanganda ilova yopiladi va oqim tugaydi.
    pub fn watch_changes(&self, sink: StreamSink<ChangeEvent>) -> Result<(), AppError> {
        let rx = self.session.app()?.subscribe();
        std::thread::spawn(move || {
            for ev in rx {
                if sink.add(ev).is_err() {
                    break;
                }
            }
        });
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn adapter_matches_desktop_flow() {
        let dir = tempfile::tempdir().unwrap();
        let core = BarakaCore::new(dir.path().display().to_string());
        assert!(!core.status().unwrap().initialized);
        let secret = PlatformSecret::generate().unwrap().as_bytes().to_vec();
        let setup = core
            .setup(
                secret.clone(),
                "135790".into(),
                BootstrapInput {
                    income_rhythm: None,
                    debts_declared: false,
                    household_name: "Ravshan akaning oilasi".into(),
                    device_name: "Telefon".into(),
                    platform: "android".into(),
                    locale: "uz-Cyrl".into(),
                    base_currency: "UZS".into(),
                    month_start_day: 10,
                    spaces: vec!["UY".into()],
                    members: vec![NewMemberInput {
                        display_name: "Karim".into(),
                        role: "ADULT".into(),
                    }],
                },
            )
            .unwrap();
        let uy = setup.household.spaces[0].id.clone();
        let rec = core
            .record_income(
                uy.clone(),
                NewIncomeInput {
                    amount: "3 000 000".into(),
                    source: "Oylik".into(),
                    channel: "CARD".into(),
                    member_id: None,
                    occurred_on: None,
                    source_type: None,
                    note: None,
                },
            )
            .unwrap();
        assert_eq!(rec.suggested_share.formatted, "150\u{a0}000\u{a0}сўм");
        core.lock().unwrap();
        assert_eq!(core.household().unwrap_err().code, "LOCKED");
        assert!(core.unlock(secret, "135790".into()).is_ok());
        assert_eq!(
            take_secret(vec![1, 2, 3]).map(|_| ()).unwrap_err().code,
            "KEYFILE_CORRUPT"
        );
    }
}
