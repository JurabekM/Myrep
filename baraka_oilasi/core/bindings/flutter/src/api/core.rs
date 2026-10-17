use std::path::Path;
use std::sync::Arc;

use baraka_agreements::{AgreementDraft, Completeness};
use baraka_app::*;
use zeroize::Zeroize;

/// Android avto-qulf vaqti (7.4): fonga o'tgandan 2 daqiqa.
const IDLE_LOCK_MINUTES: i64 = 2;

pub fn core_version() -> String {
    baraka_app::core_version().to_string()
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

    pub fn check_agreement(
        &self,
        agreement_type: String,
        draft: AgreementDraft,
    ) -> Result<Completeness, AppError> {
        self.session.app()?.check_agreement(&agreement_type, draft)
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
    ) -> Result<PartnershipDto, AppError> {
        self.session.app()?.partnership(&space_id, &partnership_id)
    }

    pub fn readiness_gate(&self, space_id: String) -> Result<GateDto, AppError> {
        self.session.app()?.readiness_gate(&space_id)
    }

    pub fn create_partnership(
        &self,
        space_id: String,
        input: PartnershipInput,
    ) -> Result<PartnershipDto, AppError> {
        self.session.app()?.create_partnership(&space_id, input)
    }

    pub fn update_partnership(
        &self,
        space_id: String,
        partnership_id: String,
        input: PartnershipInput,
    ) -> Result<PartnershipDto, AppError> {
        self.session
            .app()?
            .update_partnership(&space_id, &partnership_id, input)
    }

    /// Imzo shu qurilmada chiziladi: nuqtalar 0..=1000 × 0..=400 maydonda.
    pub fn sign_partnership(
        &self,
        space_id: String,
        partnership_id: String,
        input: SignInput,
    ) -> Result<PartnershipDto, AppError> {
        self.session
            .app()?
            .sign_partnership(&space_id, &partnership_id, input)
    }

    pub fn acknowledge_not_debt(
        &self,
        space_id: String,
        partnership_id: String,
    ) -> Result<PartnershipDto, AppError> {
        self.session
            .app()?
            .acknowledge_not_debt(&space_id, &partnership_id)
    }

    pub fn consent_partnership(
        &self,
        space_id: String,
        partnership_id: String,
        member_id: String,
    ) -> Result<PartnershipDto, AppError> {
        self.session
            .app()?
            .consent_partnership(&space_id, &partnership_id, &member_id)
    }

    pub fn activate_partnership(
        &self,
        space_id: String,
        partnership_id: String,
    ) -> Result<PartnershipDto, AppError> {
        self.session
            .app()?
            .activate_partnership(&space_id, &partnership_id)
    }

    pub fn close_partnership(
        &self,
        space_id: String,
        partnership_id: String,
    ) -> Result<PartnershipDto, AppError> {
        self.session
            .app()?
            .close_partnership(&space_id, &partnership_id)
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
    ) -> Result<PartnershipDto, AppError> {
        self.session
            .app()?
            .draft_partnership_from_idea(&space_id, &idea_id, input)
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
    ) -> Result<PartnershipDto, AppError> {
        self.session
            .app()?
            .renew_partnership(&space_id, &partnership_id)
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

    /// Yangi qurilmani ulash: kod, QR (SVG) va shu kod bilan shifrlangan fayl.
    pub fn pairing_offer(&self) -> Result<PairingOfferDto, AppError> {
        self.session.app()?.pairing_offer()
    }

    /// O'zgarish hodisalari: Android vazifasida FRB `StreamSink<ChangeEvent>` bilan ulanadi.
    /// Hozircha bloklovchi o'qish — keyingi hodisani kutadi (`None` — sessiya yopildi).
    pub fn next_change(&self) -> Result<Option<ChangeEvent>, AppError> {
        let rx = self.session.app()?.subscribe();
        Ok(rx.recv().ok())
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
                    household_name: "Karim akaning oilasi".into(),
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
