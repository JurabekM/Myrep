//! Adapterlar (FRB, tauri-specta) uchun DTO'lar. Pul har doim `MoneyDto`, sonli summalar string.
use baraka_agreements::{Answer, Arbiter, Custody, Duty, ExitClause, Stroke, Term};
use serde::{Deserialize, Serialize};

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct MoneyDto {
    pub minor: String,
    pub currency: String,
    /// Ko'rsatish uchun: `8 000 000 soʻm`.
    pub formatted: String,
    /// Kirish maydoniga qaytarish uchun: `8000000`, `123,45` (UI hisoblamaydi).
    pub plain: String,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct BootstrapInput {
    pub household_name: String,
    pub device_name: String,
    pub platform: String,
    /// `uz`, `uz-Cyrl` yoki `ru`.
    pub locale: String,
    pub base_currency: String,
    pub month_start_day: u32,
    /// Yoqiladigan makonlar: `UY`, `KASBKOR`, `MUSOFIR`.
    pub spaces: Vec<String>,
    pub members: Vec<NewMemberInput>,
    /// Onboarding: `DAILY` (kunlik naqd), `ORDERS` (buyurtma bo'yicha), `MONTHLY` (oylik maosh).
    #[serde(default)]
    pub income_rhythm: Option<String>,
    /// Onboarding: «faol qarzim bor» — qarzlar inventarga kiritilguncha taklif ko'rsatiladi.
    #[serde(default)]
    pub debts_declared: bool,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct NewMemberInput {
    pub display_name: String,
    /// `ADULT` yoki `CHILD`.
    pub role: String,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct SpaceDto {
    pub id: String,
    pub kind: String,
    pub name: String,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct MemberDto {
    pub id: String,
    pub display_name: String,
    pub role: String,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct HouseholdDto {
    pub id: String,
    pub name: String,
    pub locale: String,
    pub base_currency: String,
    pub month_start_day: u32,
    pub spaces: Vec<SpaceDto>,
    pub members: Vec<MemberDto>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct CategoryDto {
    pub id: String,
    /// i18n kaliti; `customName` bo'lsa, UI shuni ko'rsatadi.
    pub name_key: String,
    pub custom_name: Option<String>,
    pub default_necessity: Option<String>,
    pub is_system: bool,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct NewIncomeInput {
    pub amount: String,
    pub source: String,
    /// `CASH` yoki `CARD`.
    pub channel: String,
    pub member_id: Option<String>,
    /// `YYYY-MM-DD`; bo'lmasa — bugungi lokal sana.
    pub occurred_on: Option<String>,
    pub source_type: Option<String>,
    pub note: Option<String>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct IncomeDto {
    pub id: String,
    pub amount: MoneyDto,
    pub source: String,
    pub channel: String,
    pub occurred_on: String,
}

/// Daromad saqlangandan keyingi taklif: «Shundan X so'm — kelajagingiz uchun».
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct IncomeRecordedDto {
    pub income: IncomeDto,
    pub suggested_share: MoneyDto,
    /// Progressiv rejim taklifi (bp) — 4 hafta ketma-ket ajratilgan bo'lsa.
    pub progressive_suggestion_bp: Option<i32>,
    /// Shu taklif foizda, ko'rsatish uchun: `6`, `6,5`.
    pub progressive_suggestion_percent: Option<String>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct AllocationRuleInput {
    /// `PERCENT` yoki `FIXED`.
    pub kind: String,
    pub bp: Option<i32>,
    pub amount: Option<String>,
    pub progressive: bool,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct AllocationRuleDto {
    pub kind: String,
    pub bp: Option<i32>,
    pub amount: Option<MoneyDto>,
    pub progressive: bool,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct VaultTxDto {
    pub id: String,
    pub amount: MoneyDto,
    pub reason: String,
    pub note: Option<String>,
    pub occurred_on: String,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct StreakDto {
    pub current_weeks: u32,
    pub longest_weeks: u32,
    pub total_weeks: u32,
    pub current_week_done: bool,
}

/// «Kelajagim» ekrani: odat ko'rsatkichi summadan oldin (uy/SPEC 2.2).
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct VaultDto {
    pub streak: StreakDto,
    pub balance: MoneyDto,
    pub rule: Option<AllocationRuleDto>,
    pub history: Vec<VaultTxDto>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct NewExpenseInput {
    pub amount: String,
    pub category_id: String,
    pub channel: String,
    pub member_id: Option<String>,
    pub occurred_on: Option<String>,
    /// Bo'lmasa — kategoriyaning standart toifasi.
    pub necessity: Option<String>,
    pub obligation_id: Option<String>,
    pub is_gift: bool,
    pub is_ostentation: bool,
    pub funded_by_debt: bool,
    pub note: Option<String>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct ExpenseDto {
    pub id: String,
    pub amount: MoneyDto,
    pub category_id: String,
    pub necessity: Option<String>,
    pub occurred_on: String,
    pub funded_by_debt: bool,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct NecessityTotalsDto {
    pub zarur: MoneyDto,
    pub kerak: MoneyDto,
    pub havas: MoneyDto,
    /// Sadaqa havas ham, «oqib ketish» ham emas — alohida ko'rsatiladi.
    pub sadaqa: MoneyDto,
    pub unclassified: MoneyDto,
}

/// Oylik audit va bosh ekran KPI'lari (uy/SPEC 2.3–2.4).
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct MonthlySummaryDto {
    pub period_start: String,
    pub period_end: String,
    pub income: MoneyDto,
    /// Bosh ekrandagi 1-raqam: «O'zingizga to'langan (shu oy)».
    pub paid_to_self: MoneyDto,
    pub obligations_paid: MoneyDto,
    pub expenses: MoneyDto,
    pub by_necessity: NecessityTotalsDto,
    pub vault_net: MoneyDto,
    pub balance_delta: MoneyDto,
    /// Izohsiz qolgan summa (5.9). Musbat — izohsiz chiqib ketgan.
    pub unexplained_gap: MoneyDto,
    /// Oy yakuni: daromad − majburiyatlar − xarajatlar.
    pub month_result: MoneyDto,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct AgreementDto {
    pub id: String,
    pub agreement_type: String,
    pub status: String,
    pub title: String,
    pub keeper_device_id: String,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct NewJournalEntryInput {
    pub kind: String,
    pub party_id: Option<String>,
    pub amount: Option<String>,
    pub currency: Option<String>,
    pub date: Option<String>,
    pub note: Option<String>,
    pub corrects_entry_id: Option<String>,
    pub refs: Vec<String>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct JournalEntryDto {
    pub id: String,
    pub seq: u32,
    pub kind: String,
    pub party_id: Option<String>,
    pub amount: Option<MoneyDto>,
    pub date: String,
    pub note: Option<String>,
    pub corrects_entry_id: Option<String>,
    pub hash: String,
    pub short_code: String,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct ChainStatusDto {
    pub ok: bool,
    pub entries: u32,
    pub head: Option<String>,
    pub short_code: Option<String>,
    pub first_broken_seq: Option<u32>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct LoanSimulationInput {
    pub principal: String,
    pub currency: String,
    pub annual_bp: i32,
    pub months: u32,
    /// `ANNUITY` yoki `DIFFERENTIATED`.
    pub kind: String,
    pub extra_per_month: String,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct ScheduleRowDto {
    pub month: u32,
    pub interest: MoneyDto,
    pub principal: MoneyDto,
    pub extra: MoneyDto,
    pub balance: MoneyDto,
}

/// Odatiy va tezlashtirilgan grafik yonma-yon: «N oy erta», «X so'm tejaldi».
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct LoanSimulationDto {
    pub payment: MoneyDto,
    pub base_months: u32,
    pub base_total_interest: MoneyDto,
    pub accelerated_months: u32,
    pub accelerated_total_interest: MoneyDto,
    pub months_saved: u32,
    pub interest_saved: MoneyDto,
    pub accelerated_schedule: Vec<ScheduleRowDto>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct ScheduleLineInput {
    /// `15.11.2026` yoki `2026-11-15` (yadroda o'qiladi).
    pub date: String,
    pub amount: String,
}

/// Qarz tilxati (uy/SPEC 2D.5): foizsiz, yozma, guvohli va to'lov rejasi bilan.
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct LoanReceiptInput {
    pub lender: String,
    pub borrower: String,
    pub amount: String,
    pub currency: String,
    /// Bo'lmasa — bugun.
    pub issued_on: Option<String>,
    pub place: String,
    /// To'lov rejasi majburiy; yig'indisi qarz summasiga teng bo'lishi kerak.
    pub schedule: Vec<ScheduleLineInput>,
    pub witnesses: Vec<String>,
    pub note: Option<String>,
}

/// «To'xta va o'yla» javoblari (uy/SPEC 2D.6).
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct BorrowCheckInput {
    /// `NECESSITY` yoki `LUXURY`.
    pub need: String,
    /// Mavjud foizsiz muqobillar: `QOROVUL`, `RELATIVE`, `SELL_ITEM`.
    pub alternatives: Vec<String>,
}

/// Olingan qarz (inventar). Reja turi bo'yicha: `ANNUITY`/`DIFFERENTIATED` — `annualBp` va `months`,
/// `FIXED_MARKUP` — `markup` va `months`, `MANUAL` — `schedule` (yig'indisi = summa + ustama).
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct NewDebtInput {
    /// `BANK`, `SHOP`, `RELATIVE`, `FRIEND`, `OTHER`.
    pub creditor_type: String,
    pub creditor: String,
    pub reason: Option<String>,
    pub currency: String,
    /// Reja tuzilayotgan summa (hozirgi qoldiq).
    pub principal: String,
    /// Dastlab olingan summa (haqiqiy narx uchun); bo'lmasa — `principal`.
    pub original_principal: Option<String>,
    /// Ilovaga kiritilgunga qadar to'langan.
    pub paid_before: Option<String>,
    pub plan_kind: String,
    pub annual_bp: Option<i32>,
    pub markup: Option<String>,
    pub months: Option<u32>,
    /// Bank turlarida — birinchi to'lov sanasi; `MANUAL` da — qarz boshlangan sana. Bo'lmasa — bugun.
    pub first_date: Option<String>,
    pub schedule: Vec<ScheduleLineInput>,
    pub early_repayment_terms: Option<String>,
    /// Muddatidan oldin to'lash jarimasi/komissiyasi: qo'shimcha to'lovdan bp (100 = 1%).
    pub prepayment_fee_bp: Option<i32>,
    /// Yangi olinayotgan qarz: «to'xta va o'yla» javoblari majburiy.
    pub is_new: bool,
    pub borrow_check: Option<BorrowCheckInput>,
}

/// Bergan qarz. **Foiz yoki ustama maydoni yo'q**: noma'lum maydon (masalan `interestBp`) rad etiladi.
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
pub struct NewReceivableInput {
    pub debtor: String,
    pub currency: String,
    pub amount: String,
    pub lent_on: Option<String>,
    /// Qaytarish rejasi majburiy; yig'indisi aynan summaga teng.
    pub schedule: Vec<ScheduleLineInput>,
    pub note: Option<String>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct RepaymentInput {
    pub amount: String,
    /// Bo'lmasa — bugun.
    pub date: Option<String>,
    /// Rejadan tashqari (muddatidan oldin) to'lov.
    pub is_prepayment: bool,
    pub note: Option<String>,
    /// Qarzni kim to'ladi (`DebtContributor`); bo'lmasa — oilaning o'zi.
    pub contributor_id: Option<String>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct NewGoalInput {
    pub title: String,
    pub target: String,
    pub currency: String,
}

/// Tilxat yozish va saqlash: `Agreement(type = LOAN)` + jurnal + qarz yoki bergan qarz yozuvi.
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct IssueLoanReceiptInput {
    /// `BORROWED` (men oldim) yoki `LENT` (men berdim).
    pub direction: String,
    /// `BORROWED` da kreditor turi: `RELATIVE`, `FRIEND` yoki `OTHER` (standart — `FRIEND`).
    pub creditor_type: Option<String>,
    pub reason: Option<String>,
    pub receipt: LoanReceiptInput,
    pub is_new: bool,
    pub borrow_check: Option<BorrowCheckInput>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct IssuedReceiptDto {
    pub agreement_id: String,
    /// `DEBT` yoki `RECEIVABLE`.
    pub record_type: String,
    pub record_id: String,
    pub short_code: String,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct PlanLineDto {
    /// `YYYY-MM-DD`.
    pub date: String,
    pub amount: MoneyDto,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct RepaymentDto {
    pub id: String,
    pub amount: MoneyDto,
    pub date: String,
    pub is_prepayment: bool,
    pub note: Option<String>,
    /// Tilxatga bog'langan bo'lsa — jurnal yozuvining qisqa kodi.
    pub journal_short_code: Option<String>,
    pub contributor_id: Option<String>,
}

/// To'lov natijasi: qarz yopildimi, barcha qarzlar tugadimi («Qarzsiz kun»), rejim qaytdimi.
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct RepaymentResultDto {
    pub repayment: RepaymentDto,
    pub closed: bool,
    /// Bu oxirgi faol qarz edi.
    pub debt_free: bool,
    /// `DEBT_RECOVERY` avtomatik `STANDARD` ga qaytdi.
    pub mode_returned: bool,
    /// Bo'shagan oylik to'lov (jamg'armaga yo'naltirish taklifi uchun).
    pub freed_monthly: Option<MoneyDto>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct ContributorDto {
    pub id: String,
    pub name: String,
    pub monthly_share: Option<MoneyDto>,
    pub paid: MoneyDto,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct NewContributorInput {
    pub name: String,
    pub monthly_share: Option<String>,
}

/// Reja bo'yicha holat: keyingi to'lov, kechikkan summa, qoldiq, eslatma.
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct PlanStatusDto {
    pub paid: MoneyDto,
    pub remaining: MoneyDto,
    pub next_due: Option<PlanLineDto>,
    pub overdue: MoneyDto,
    pub payoff_date: Option<String>,
    /// `DUE_SOON` yoki `OVERDUE`.
    pub reminder: Option<String>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct GoalEquivalentDto {
    pub goal_id: String,
    pub title: String,
    /// Ortiqcha to'lov maqsadning necha foiziga teng: `45`, `250`.
    pub percent: String,
}

/// Qarzning haqiqiy narxi (uy/SPEC 2D.3).
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct TrueCostDto {
    pub original_principal: MoneyDto,
    pub total_cost: MoneyDto,
    pub overpay: MoneyDto,
    pub overpay_percent: String,
    pub goal_equivalents: Vec<GoalEquivalentDto>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct DebtDto {
    pub id: String,
    pub creditor_type: String,
    pub creditor: String,
    pub reason: Option<String>,
    pub plan_kind: String,
    /// Foizli yoki ustamali — qizil bayroq.
    pub is_ribo: bool,
    pub annual_bp: i32,
    pub status: String,
    pub principal: MoneyDto,
    pub true_cost: TrueCostDto,
    pub status_info: PlanStatusDto,
    pub plan: Vec<PlanLineDto>,
    pub payments: Vec<RepaymentDto>,
    pub early_repayment_terms: Option<String>,
    pub prepayment_fee_bp: i32,
    /// Qo'lda qo'yilgan yopish tartibi (1 — birinchi).
    pub priority: Option<i32>,
    /// Bank qarzida — asosiy qarz qoldig'i, boshqalarida — qolgan to'lovlar.
    pub balance: MoneyDto,
    pub contributors: Vec<ContributorDto>,
    pub borrow_warnings: Vec<String>,
    pub agreement_id: Option<String>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct ReceivableDto {
    pub id: String,
    pub debtor: String,
    pub amount: MoneyDto,
    pub lent_on: String,
    pub note: Option<String>,
    pub status: String,
    pub status_info: PlanStatusDto,
    pub plan: Vec<PlanLineDto>,
    pub payments: Vec<RepaymentDto>,
    pub agreement_id: Option<String>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct GoalDto {
    pub id: String,
    pub title: String,
    pub target: MoneyDto,
    /// Mehmonlar va oila hissasi (to'yona o'rniga jamg'arma).
    pub collected: MoneyDto,
    pub collected_percent: String,
    pub contributions: Vec<GoalContributionDto>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct GoalContributionDto {
    pub id: String,
    pub contributor: String,
    pub amount: MoneyDto,
    pub given_on: String,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct NewGoalContributionInput {
    pub contributor: String,
    pub amount: String,
    pub given_on: Option<String>,
}

/// Qarzlar ekrani: «yaraning hajmi» (uy/SPEC 2C.7).
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct DebtsOverviewDto {
    pub debts: Vec<DebtDto>,
    pub receivables: Vec<ReceivableDto>,
    /// Faol qarzlar qoldig'i, valyuta bo'yicha (asosiy valyuta birinchi).
    pub total_debt: Vec<MoneyDto>,
    pub total_receivable: Vec<MoneyDto>,
    /// Shu oy davridagi reja to'lovlari (asosiy valyutada).
    pub monthly_due: MoneyDto,
    /// Oylik yuk hisobidagi daromad: oxirgi 3 to'liq oy o'rtachasi, bo'lmasa — shu oy.
    pub monthly_income: Option<MoneyDto>,
    pub load_percent: Option<String>,
    pub load_high: bool,
    /// Boshqa valyutadagi qarzlar oylik yukka kirmagan.
    pub load_excludes_foreign: bool,
    pub has_ribo_debt: bool,
    pub goals: Vec<GoalDto>,
    /// «Qarzsiz kun» — qo'shimcha to'lovsiz prognoz (asosiy valyutadagi qarzlar).
    pub debt_free_date: Option<String>,
    pub debt_free_months: u32,
    /// `DEBT_RECOVERY` da: 20% qo'shimcha to'lov bilan «Qarzsiz kun».
    pub debt_free_date_with_plan: Option<String>,
    /// `STANDARD` yoki `DEBT_RECOVERY`.
    pub budget_mode: String,
}

/// «To'xta va o'yla» natijasi: taqiqlamaydi, ko'rsatadi.
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct BorrowCheckDto {
    pub is_ribo: bool,
    pub projected_load_percent: Option<String>,
    /// `RIBO`, `LUXURY`, `ALTERNATIVE_AVAILABLE`, `LOAD_HIGH`, `LOAD_UNKNOWN`.
    pub warnings: Vec<String>,
    pub plan: Vec<PlanLineDto>,
    pub true_cost: TrueCostDto,
}

/// Byudjet rejimi (uy/SPEC 2D.1). Ulushlar bp: 7000/2000/1000 = 70/20/10.
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct BudgetModeInput {
    /// `STANDARD` yoki `DEBT_RECOVERY`.
    pub mode: String,
    pub household_bp: i32,
    pub extra_debt_bp: i32,
    pub savings_bp: i32,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct BudgetModeDto {
    pub mode: String,
    pub household_bp: i32,
    pub extra_debt_bp: i32,
    pub savings_bp: i32,
    pub household_percent: String,
    pub extra_debt_percent: String,
    pub savings_percent: String,
    /// Faol qarz bor, rejim esa `STANDARD` — «Qarzdan chiqish» rejimini taklif qilish.
    pub suggested: bool,
    pub has_active_debt: bool,
    /// Oylik daromad (oxirgi 3 to'liq oy o'rtachasi; bo'lmasa — shu oy).
    pub monthly_income: Option<MoneyDto>,
    pub household: MoneyDto,
    pub extra_debt: MoneyDto,
    pub savings: MoneyDto,
    /// Shu oy majburiy qarz to'lovlari — ro'zg'or ulushi ichida `ZARUR` sifatida.
    pub mandatory_debt_payments: MoneyDto,
    pub household_after_debts: MoneyDto,
    /// Majburiy to'lovlar ro'zg'or ulushidan oshib ketdi.
    pub household_short: bool,
    pub changed_on: Option<String>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct PlannerInput {
    /// Bo'lmasa: `DEBT_RECOVERY` da — 20% ulush, aks holda — 0.
    pub extra_per_month: Option<String>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct PlanTotalsDto {
    pub payoff_date: Option<String>,
    pub months: u32,
    pub interest: MoneyDto,
    pub fees: MoneyDto,
    pub paid: MoneyDto,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct PlannerDebtDto {
    pub id: String,
    pub creditor: String,
    pub is_ribo: bool,
    /// 1 — birinchi yopiladigan.
    pub order: u32,
    pub manual_order: bool,
    pub balance: MoneyDto,
    pub base_payoff: Option<String>,
    pub accelerated_payoff: Option<String>,
    pub months_saved: i32,
    pub interest_saved: MoneyDto,
    pub fees: MoneyDto,
    pub prepayment_fee_bp: i32,
}

/// Grafik nuqtasi: oy oxiridagi umumiy qoldiq (odatiy va tezlashtirilgan).
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct TimelinePointDto {
    /// `YYYY-MM-01`.
    pub month: String,
    pub base_balance: MoneyDto,
    pub accelerated_balance: MoneyDto,
}

/// Katta jadval qatori (tezlashtirilgan reja, barcha qarzlar yig'indisi).
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct TimelineRowDto {
    pub month: String,
    pub due: MoneyDto,
    pub interest: MoneyDto,
    pub extra: MoneyDto,
    pub fee: MoneyDto,
    pub balance: MoneyDto,
}

/// Qarzdan chiqish rejalovchisi (uy/SPEC 2D.2, 2D.9). Taxminiy hisob.
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct PlannerDto {
    pub extra_per_month: MoneyDto,
    /// `RECOVERY_SHARE` (20% ulush), `MANUAL` yoki `NONE`.
    pub extra_source: String,
    pub base: PlanTotalsDto,
    pub accelerated: PlanTotalsDto,
    pub months_saved: i32,
    pub interest_saved: MoneyDto,
    /// Tejalgan foiz − jarima/komissiya.
    pub net_saved: MoneyDto,
    pub debts: Vec<PlannerDebtDto>,
    pub timeline: Vec<TimelinePointDto>,
    pub schedule: Vec<TimelineRowDto>,
    /// Boshqa valyutadagi qarzlar rejaga kirmagan.
    pub excluded_foreign: u32,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct NewSellableItemInput {
    pub title: String,
    pub estimated: String,
    pub currency: String,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct SellableItemDto {
    pub id: String,
    pub title: String,
    pub estimated: MoneyDto,
    /// `LISTED` yoki `SOLD`.
    pub status: String,
    pub sold: Option<MoneyDto>,
    pub sold_on: Option<String>,
    pub debt_id: Option<String>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct SellItemInput {
    pub price: String,
    pub date: Option<String>,
    /// Pul shu qarzga muddatidan oldingi to'lov sifatida yo'naltiriladi (bir bosishda).
    pub debt_id: Option<String>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct SellResultDto {
    pub item: SellableItemDto,
    pub repayment: Option<RepaymentResultDto>,
}

/// Marosim rejasi (uy/SPEC 2D.8). Turlari: `TOY`, `BESHIK_TOY`, `SUNNAT_TOY`, `MARAKA`, `OTHER`.
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct NewCeremonyInput {
    pub kind: String,
    pub title: String,
    /// `15.06.2027` yoki `2027-06-15`.
    pub planned_on: Option<String>,
    /// Birinchi stsenariy.
    pub scenario_name: String,
    pub guests: i32,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct CeremonyUpdateInput {
    pub title: String,
    pub planned_on: Option<String>,
    /// Qarzni uzish uchun oylik ajratma; bo'lmasa — daromadning qo'shimcha to'lov ulushi.
    pub monthly_capacity: Option<String>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct ScenarioInput {
    pub name: String,
    pub guests: i32,
    /// Yangi stsenariy shu stsenariy qatorlaridan nusxa olinadi.
    pub copy_from: Option<String>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct NewCeremonyLineInput {
    pub title: String,
    /// `ONE_OFF` yoki `PER_GUEST`.
    pub kind: String,
    /// Bir martalik summa yoki kishi boshiga narx.
    pub amount: String,
    /// `SAVINGS`, `FAMILY`, `EXPECTED_GIFTS`, `DEBT`.
    pub source: String,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct DiscussionAnswerDto {
    /// `guests`, `days`, `cut`, `sources`.
    pub key: String,
    pub note: String,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct CeremonyLineDto {
    pub id: String,
    pub title: String,
    pub kind: String,
    /// Bir martalik summa yoki kishi boshiga narx.
    pub amount: MoneyDto,
    pub total: MoneyDto,
    pub source: String,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct SourceTotalsDto {
    pub savings: MoneyDto,
    pub family: MoneyDto,
    pub expected_gifts: MoneyDto,
    pub debt: MoneyDto,
}

/// Stsenariy: jami, manbalar, qarzni uzish muddati (U9 simulyatori), eng qimmatiga nisbatan tejam.
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct ScenarioDto {
    pub id: String,
    pub name: String,
    pub guests: i32,
    pub selected: bool,
    pub lines: Vec<CeremonyLineDto>,
    pub total: MoneyDto,
    pub by_source: SourceTotalsDto,
    pub has_debt: bool,
    pub payoff_months: Option<u32>,
    pub payoff_date: Option<String>,
    /// Qarz bor, oylik ajratma 0 — qarz yopilmaydi.
    pub not_repayable: bool,
    pub saved_vs_max: MoneyDto,
    pub goal_equivalents: Vec<GoalEquivalentDto>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct SignoffDto {
    pub member_id: String,
    pub name: String,
    pub agreed_on: Option<String>,
}

/// «Buni qarzsiz qanday o'tkazamiz?» oilaviy muhokamasi.
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct DiscussionDto {
    /// Tanlangan stsenariyda qarz bor — tasdiqlashdan oldin majburiy.
    pub required: bool,
    pub answers: Vec<DiscussionAnswerDto>,
    pub adults: Vec<SignoffDto>,
    pub complete: bool,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct CeremonyDto {
    pub id: String,
    pub kind: String,
    pub title: String,
    pub planned_on: Option<String>,
    /// `DRAFT`, `DISCUSSED`, `CONFIRMED`.
    pub status: String,
    pub monthly_capacity: MoneyDto,
    /// `MANUAL`, `INCOME_SHARE` yoki `NONE`.
    pub capacity_source: String,
    pub scenarios: Vec<ScenarioDto>,
    pub discussion: DiscussionDto,
    pub can_confirm: bool,
    /// `NO_SCENARIO_SELECTED`, `DISCUSSION_REQUIRED`, `CEREMONY_LOCKED`.
    pub confirm_blocker: Option<String>,
    /// Kutilayotgan to'yona manbasi bor — bu kelajakda qaytariladigan majburiyat (OQ-P1).
    pub gifts_warning: bool,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct CeremonySummaryDto {
    pub id: String,
    pub kind: String,
    pub title: String,
    pub planned_on: Option<String>,
    pub status: String,
    /// Tanlangan (bo'lmasa — birinchi) stsenariy jami.
    pub total: Option<MoneyDto>,
    pub has_debt: bool,
}

// ---- U11: sheriklik (mudoraba / musharaka), shartnoma, imzolar, darvoza ----

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct CapitalItemInput {
    /// `MONEY` yoki `EQUIPMENT` (narxlangan uskuna).
    pub kind: String,
    pub description: String,
    pub amount: String,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct PartnerInput {
    /// Shartnoma ichidagi barqaror belgi (`P1`, `P2`) — vazifa, hisob va buyout shunga bog'lanadi.
    pub id: String,
    pub full_name: String,
    /// `CAPITAL_PROVIDER`, `WORKER`, `BOTH`.
    pub role: String,
    pub profit_share_bp: i32,
    /// Bu tomon — shu oila (darvoza va oilaviy rozilik shunga qarab).
    pub is_me: bool,
    pub capital: Vec<CapitalItemInput>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct BuyoutTermsInput {
    pub seller_party_id: String,
    pub buyer_party_id: String,
    pub units: u32,
    pub units_per_period: u32,
    pub period_months: u32,
    pub start: String,
    /// Davr uchun taxminiy sof foyda (to'lov ulushdan oshadimi — ko'rsatish uchun).
    pub expected_profit: Option<String>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct PartnershipInput {
    /// `MUDARABA` yoki `MUSHARAKA`.
    pub kind: String,
    pub title: String,
    pub parties: Vec<PartnerInput>,
    /// Kapital egasiga qat'iy summa urinishi — domen har doim rad etadi
    /// (`GUARANTEED_RETURN_FORBIDDEN`: «Bu sheriklik emas — ribo yoki qarz»).
    pub fixed_return: Option<String>,
    pub duties: Answer<Vec<Duty>>,
    /// Mudoraba: beparvolik yoki shart buzilishi deb nima hisoblanadi.
    pub negligence_clause: Option<String>,
    pub custody: Answer<Custody>,
    pub exit_clause: Answer<ExitClause>,
    pub arbiter: Answer<Arbiter>,
    pub term: Answer<Term>,
    pub witnesses: Vec<String>,
    pub buyout: Option<BuyoutTermsInput>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct CapitalItemDto {
    pub kind: String,
    pub description: String,
    pub amount: MoneyDto,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct PartnerDto {
    pub id: String,
    pub full_name: String,
    pub role: String,
    pub profit_share_bp: i32,
    /// `50%`.
    pub profit_share: String,
    pub is_me: bool,
    pub capital_items: Vec<CapitalItemDto>,
    pub capital: MoneyDto,
    /// Zarar ulushi (`75%`); shartlarda xato bo'lsa — `None`.
    pub loss_share: Option<String>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct BuyoutRowDto {
    pub period: u32,
    pub date: String,
    pub units: u32,
    pub payment: MoneyDto,
    pub remaining: MoneyDto,
    pub seller_bp: i32,
    pub seller_percent: String,
    pub buyer_bp: i32,
    pub buyer_percent: String,
    pub exceeds_share: bool,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct BuyoutDto {
    pub seller_party_id: String,
    pub buyer_party_id: String,
    pub units: u32,
    pub units_per_period: u32,
    pub period_months: u32,
    pub start: String,
    pub expected_profit: Option<MoneyDto>,
    pub rows: Vec<BuyoutRowDto>,
    pub end_date: Option<String>,
    pub buyer_profit: Option<MoneyDto>,
    /// Jadval tuzilmadi: `STAKE_EXCEEDS_CAPITAL`, `INVALID_UNITS` ...
    pub error: Option<String>,
}

/// 9 savol to'liqligi + sheriklik qoidalari (birlashtirilgan).
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct ContractCheckDto {
    pub answered: u8,
    pub complete: bool,
    pub can_sign: bool,
    pub missing: Vec<u8>,
    pub errors: Vec<String>,
    pub warnings: Vec<String>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct SignerDto {
    /// `party:P1`, `witness:0`, `arbiter`.
    pub key: String,
    /// `PARTY`, `WITNESS`, `ARBITER`.
    pub role: String,
    pub name: String,
    pub signed_at: Option<String>,
    /// Chizilgan imzo (SVG, faqat raqamlardan).
    pub svg: Option<String>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct VersionInfoDto {
    pub no: u32,
    pub created_on: String,
    /// `RENEWED_UNCHANGED` — yillik yangilash, matn o'zgarmagan (2F.3).
    pub change_note: Option<String>,
    pub signed: u32,
    pub required: u32,
    pub in_force: bool,
}

/// Tayyorgarlik darvozasi (uy/SPEC 2C.4) — faqat kapital kirituvchiga qo'llanadi.
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct GateDto {
    pub open: bool,
    /// `EMERGENCY_FUND_BELOW_TARGET`, `INTEREST_DEBT_WITHOUT_PLAN`, `INTEREST_DEBT_ACTIVE`.
    pub reasons: Vec<String>,
    /// Necha oylik qorovul pul: `1,4`; xarajat tarixi bo'lmasa — `None`.
    pub coverage_months: Option<String>,
    pub required_months: u32,
    pub balance: MoneyDto,
    pub monthly_essentials: Option<MoneyDto>,
    pub has_interest_debt: bool,
    pub has_payoff_plan: bool,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct FamilyConsentDto {
    pub adults: Vec<SignoffDto>,
    /// «Bu qarz emas» tushuntirishi o'qilgan sana.
    pub not_debt_ack_on: Option<String>,
    pub complete: bool,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct PartnershipDto {
    pub id: String,
    pub agreement_id: String,
    pub kind: String,
    pub title: String,
    /// `DRAFT`, `SIGNED`, `ACTIVE`, `CLOSED`.
    pub status: String,
    pub currency: String,
    pub parties: Vec<PartnerDto>,
    pub capital_total: MoneyDto,
    pub duties: Answer<Vec<Duty>>,
    pub negligence_clause: Option<String>,
    pub custody: Answer<Custody>,
    pub exit_clause: Answer<ExitClause>,
    pub arbiter: Answer<Arbiter>,
    pub term: Answer<Term>,
    pub witnesses: Vec<String>,
    pub buyout: Option<BuyoutDto>,
    pub check: ContractCheckDto,
    /// Joriy matnga mos versiya (`None` — matn hali imzolashga berilmagan yoki o'zgargan).
    pub version: Option<u32>,
    /// Kuchdagi (to'liq imzolangan) versiya.
    pub signed_version: Option<u32>,
    /// Faol sheriklik matni o'zgargan — yangi versiya imzolanmaguncha eski versiya kuchda.
    pub amendment_pending: bool,
    pub signers: Vec<SignerDto>,
    pub all_signed: bool,
    pub me_provides_capital: bool,
    pub me_receives_capital: bool,
    pub gate: Option<GateDto>,
    pub consent: Option<FamilyConsentDto>,
    pub can_activate: bool,
    /// `NOT_SIGNED`, `ME_PARTY_REQUIRED`, `GATE_CLOSED`, `NOT_DEBT_ACK_REQUIRED`,
    /// `FAMILY_CONSENT_REQUIRED`, `ALREADY_ACTIVE`, `PARTNERSHIP_CLOSED`.
    pub activate_blocker: Option<String>,
    pub history: Vec<VersionInfoDto>,
    /// Shablon tekshiruvi: `PENDING` — yurist va ulamo hali ko'rmagan.
    pub template_review: String,
    /// Joriy matn xeshining qisqa kodi.
    pub hash_code: String,
    pub in_dispute: bool,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct PartnershipSummaryDto {
    pub id: String,
    pub kind: String,
    pub title: String,
    pub status: String,
    /// Ochiq nizo bor — taqsimot to'xtatilgan (2F.8).
    pub in_dispute: bool,
    pub capital_total: MoneyDto,
    pub my_role: Option<String>,
    pub signed_version: Option<u32>,
    pub answered: u8,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct SignInput {
    pub signer_key: String,
    pub strokes: Vec<Stroke>,
}

// ---- U12: sheriklik kassa daftari, davr taqsimoti, «Hunardan ishga», taklif tekshiruvi ----

/// Chek, rasm yoki dalil fayli. Turi baytlardan aniqlanadi (JPEG, PNG, WebP, PDF).
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct AttachmentInput {
    pub file_name: String,
    pub bytes: Vec<u8>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct VentureEntryInput {
    /// `INCOME`, `EXPENSE`, `FORCE_MAJEURE`, `CORRECTION`.
    pub kind: String,
    /// Kirim: `ORDER`, `OTHER`; xarajat: `MATERIAL`, `WAGE`, `RENT`, `EQUIPMENT`, `TRANSPORT`, `OTHER`.
    pub category: Option<String>,
    /// Tuzatishda — yozuvning **to'g'ri** summasi (`0` — yozuv bekor); yadro farqni hisoblaydi.
    pub amount: String,
    pub occurred_on: String,
    /// Fors-major va tuzatishda majburiy.
    pub note: Option<String>,
    pub corrects_entry_id: Option<String>,
    pub attachments: Vec<AttachmentInput>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct AttachmentMetaDto {
    pub id: String,
    pub file_name: String,
    pub mime: String,
    pub size_bytes: u32,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct AttachmentDto {
    pub file_name: String,
    pub mime: String,
    pub bytes: Vec<u8>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct VentureEntryDto {
    pub id: String,
    pub kind: String,
    pub category: Option<String>,
    /// Yozuv summasi (tuzatishda — natijaga ta'sir, ishorasi bilan).
    pub amount: MoneyDto,
    /// Davr natijasiga ta'siri: kirim `+`, xarajat va fors-major `−`.
    pub effect: MoneyDto,
    pub occurred_on: String,
    pub note: Option<String>,
    pub corrects_entry_id: Option<String>,
    /// Bu yozuvga keyinroq tuzatish kiritilgan.
    pub corrected: bool,
    /// Yopilgan davr raqami (`None` — ochiq davr).
    pub period_no: Option<u32>,
    pub attachments: Vec<AttachmentMetaDto>,
    /// Jurnal yozuvi xeshining qisqa kodi.
    pub hash_code: String,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct PartyBalanceDto {
    pub party_id: String,
    pub name: String,
    pub role: String,
    pub is_me: bool,
    pub capital: MoneyDto,
    /// Hali tiklanmagan zarar (OQ-D1: keyingi foydadan avval qoplanadi).
    pub carried_loss: MoneyDto,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct BuyoutProgressDto {
    pub seller_name: String,
    pub buyer_name: String,
    pub paid: u32,
    pub total: u32,
    pub next_no: Option<u32>,
    pub next_date: Option<String>,
    pub next_payment: Option<MoneyDto>,
    /// Muddati o'tgan, lekin hali to'lanmagan bosqichlar.
    pub overdue: Vec<u32>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct OpenPeriodDto {
    pub no: u32,
    pub from: String,
    pub entries: u32,
    pub income: MoneyDto,
    pub expense: MoneyDto,
    pub force_majeure: MoneyDto,
    pub corrections: MoneyDto,
    pub result: MoneyDto,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct PeriodPartyDto {
    pub party_id: String,
    pub name: String,
    pub role: String,
    pub is_me: bool,
    /// Foyda ulushi (musbat) yoki zarar ulushi (manfiy).
    pub share: MoneyDto,
    pub recovered: MoneyDto,
    pub liability: MoneyDto,
    pub payout: MoneyDto,
    pub carried_after: MoneyDto,
    pub capital_after: MoneyDto,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct PeriodBuyoutDto {
    pub paid: Vec<u32>,
    pub unpaid: Vec<u32>,
    pub amount: MoneyDto,
    pub capital: MoneyDto,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct VenturePeriodDto {
    /// `None` — oldindan ko'rish (hali yopilmagan).
    pub id: Option<String>,
    pub no: u32,
    pub start_on: String,
    pub end_on: String,
    pub closed_at: Option<String>,
    pub entries: u32,
    pub income: MoneyDto,
    pub expense: MoneyDto,
    pub force_majeure: MoneyDto,
    pub corrections: MoneyDto,
    pub result: MoneyDto,
    pub recovered: MoneyDto,
    pub distributable: MoneyDto,
    pub parties: Vec<PeriodPartyDto>,
    pub buyout: Option<PeriodBuyoutDto>,
    /// `CAPITAL_FIRST` (OQ-D1 bo'yicha vaqtinchalik standart) yoki `PER_PERIOD`.
    pub loss_policy: String,
    pub negligent_party: Option<String>,
    pub negligence_note: Option<String>,
    /// Xonadon byudjetiga `Income` sifatida tushgan (yoki tushadigan) summa.
    pub my_income: MoneyDto,
    pub chain_code: Option<String>,
    /// «Katta foyda» (2F.7): taqsimotdan oldin 4–5-bandlarni hamma qayta o'qishi kerak.
    pub profit_spike: bool,
    /// Shu davr uchun qayta o'qigan tomonlar.
    pub spike_rereads: Vec<String>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct VentureLedgerDto {
    pub partnership_id: String,
    pub title: String,
    pub kind: String,
    pub status: String,
    pub currency: String,
    /// Yozuv qo'shish va davr yopish mumkin (faqat hisob yurituvchi, faol sheriklikda).
    pub writable: bool,
    /// `NOT_ACTIVE`, `NOT_KEEPER` — faqat o'qish rejimi sababi.
    pub read_only_reason: Option<String>,
    pub keeper_name: Option<String>,
    pub start_on: String,
    pub open: OpenPeriodDto,
    pub entries: Vec<VentureEntryDto>,
    pub periods: Vec<VenturePeriodDto>,
    pub balances: Vec<PartyBalanceDto>,
    pub buyout: Option<BuyoutProgressDto>,
    /// Kelishuv jurnali zanjiri boshi (qisqa kod) va tekshiruv natijasi.
    pub chain_code: String,
    pub chain_ok: bool,
    pub loss_policy: String,
    /// Ochiq nizo bor (2F.8): yozuvlar davom etadi, lekin davrni yopish va taqsimot bloklangan.
    pub in_dispute: bool,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct NegligenceInput {
    pub party_id: String,
    pub note: String,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct InstallmentPriceInput {
    pub no: u32,
    /// Shu kuni kelishilgan narx (OQ-D6); berilmasa — jadvaldagi qiymat.
    pub price: String,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct ClosePeriodInput {
    pub end_on: String,
    pub negligence: Option<NegligenceInput>,
    pub buyout_prices: Vec<InstallmentPriceInput>,
    /// Xonadonga tushadigan ulush: `CASH` yoki `CARD`.
    pub channel: String,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct SkillInput {
    pub member_id: Option<String>,
    pub title: String,
    pub note: Option<String>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct SkillDto {
    pub id: String,
    pub member_id: Option<String>,
    pub member_name: Option<String>,
    pub title: String,
    pub note: Option<String>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct CapexLineInput {
    pub title: String,
    pub amount: String,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct IdeaScenarioInput {
    /// `PESSIMISTIC`, `BASE`, `OPTIMISTIC`.
    pub name: String,
    pub income: String,
    pub expense: String,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct VentureIdeaInput {
    pub title: String,
    pub skill_id: Option<String>,
    pub capex: Vec<CapexLineInput>,
    pub scenarios: Vec<IdeaScenarioInput>,
    /// Sheriklikda mehnat egasining foyda ulushi; `None` — o'z puli bilan.
    pub worker_share_bp: Option<i32>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct CapexLineDto {
    pub title: String,
    pub amount: MoneyDto,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct IdeaScenarioDto {
    pub name: String,
    pub income: MoneyDto,
    pub expense: MoneyDto,
    pub net: MoneyDto,
    pub annual_net: MoneyDto,
    /// `None` — sof foyda yo'q, qoplanmaydi.
    pub payback_months: Option<u32>,
    pub worker_monthly: Option<MoneyDto>,
    pub investor_monthly: Option<MoneyDto>,
    pub investor_payback_months: Option<u32>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct VentureIdeaDto {
    pub id: String,
    pub title: String,
    pub skill_id: Option<String>,
    pub skill_title: Option<String>,
    pub capex_lines: Vec<CapexLineDto>,
    pub capex: MoneyDto,
    pub scenarios: Vec<IdeaScenarioDto>,
    pub worker_share_bp: Option<i32>,
    pub warnings: Vec<String>,
    pub partnership_id: Option<String>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct IdeaDraftInput {
    pub capital_provider_name: String,
    pub my_name: String,
}

/// Har bir javob: `YES`, `NO` yoki `UNKNOWN`.
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct OfferAnswersInput {
    pub guaranteed: String,
    pub loss_shared: String,
    pub real_activity: String,
    pub recruitment: String,
    pub urgency: String,
    pub written: String,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct OfferFlagDto {
    pub code: String,
    /// `RED` yoki `YELLOW`.
    pub level: String,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct OfferCheckDto {
    /// `GREEN`, `YELLOW`, `RED`.
    pub verdict: String,
    pub flags: Vec<OfferFlagDto>,
}

// ---- U13: vazifa hodisalari, ochiq hisob ko'rigi, nizo va hakam, yangilash, oilaviy kelishuvlar ----

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct DutyDto {
    pub id: String,
    pub title: String,
    pub owner_party_id: Option<String>,
    pub owner_name: Option<String>,
    /// 3-banddagi «bajarilmasa» qoidasi — hodisa paytida darhol ko'rsatiladi.
    pub breach_clause: Option<String>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct IncidentInput {
    pub duty_id: String,
    pub party_id: String,
    pub reason: String,
    pub occurred_on: String,
    pub proposed_solution: Option<String>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct IncidentDto {
    pub id: String,
    pub duty_id: String,
    pub duty_title: String,
    pub breach_clause: Option<String>,
    pub party_id: String,
    pub party_name: String,
    pub reason: String,
    pub occurred_on: String,
    pub proposed_solution: Option<String>,
    pub resolved_on: Option<String>,
    pub resolution_note: Option<String>,
    pub hash_code: String,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct ReviewTotalsDto {
    pub entries: u32,
    pub periods_closed: u32,
    pub income: MoneyDto,
    pub expense: MoneyDto,
    pub force_majeure: MoneyDto,
    pub corrections: MoneyDto,
    pub result: MoneyDto,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct PartyRefDto {
    pub party_id: String,
    pub name: String,
}

/// Ko'rik sessiyasi ekrani: davr yozuvlari, yakun, ochiq hodisalar, zanjir tekshiruvi.
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct ReviewDraftDto {
    pub no: u32,
    pub from_on: String,
    pub to_on: String,
    pub entries: Vec<VentureEntryDto>,
    pub totals: ReviewTotalsDto,
    pub open_incidents: Vec<IncidentDto>,
    pub chain_ok: bool,
    pub chain_code: String,
    pub chain_entries: u32,
    pub parties: Vec<PartyRefDto>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct ReviewAckInput {
    pub party_id: String,
    /// `AGREE` yoki `OBJECT` (izoh bilan).
    pub verdict: String,
    pub note: Option<String>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct HoldReviewInput {
    pub to_on: String,
    /// `SCHEDULED`, `PROFIT_SPIKE`, `EXTRA`.
    pub reason: String,
    pub acks: Vec<ReviewAckInput>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct ReviewAckDto {
    pub party_id: String,
    pub party_name: String,
    pub verdict: String,
    pub note: Option<String>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct ReviewDto {
    pub id: String,
    pub no: u32,
    pub from_on: String,
    pub to_on: String,
    pub reason: String,
    pub held_on: String,
    pub totals: ReviewTotalsDto,
    pub open_incidents: u32,
    pub acks: Vec<ReviewAckDto>,
    /// Bayonnomadagi zanjir boshi (qisqa kod).
    pub chain_code: String,
    /// Bayonnoma joriy jurnal bilan: `INTACT`, `CHAIN_BROKEN`, `HEAD_MISMATCH`, `TRUNCATED`.
    pub integrity: String,
    pub entries_after: u32,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct DisputeClaimInput {
    pub party_id: String,
    pub claim: String,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct OpenDisputeInput {
    pub subject: String,
    /// Tegishli bandlar (1..9).
    pub clauses: Vec<u8>,
    pub opened_by: String,
    pub claims: Vec<DisputeClaimInput>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct DecisionInput {
    pub decided_on: String,
    pub decision: String,
    /// `RESUME` yoki `AMEND` (shartnomaning yangi versiyasi kerak).
    pub outcome: String,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct ClaimDto {
    pub party_id: String,
    pub party_name: String,
    pub claim: String,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct DecisionDto {
    pub decided_on: String,
    pub arbiter_name: String,
    pub decision: String,
    pub outcome: String,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct DisputeDto {
    pub id: String,
    pub opened_on: String,
    pub opened_by: String,
    pub opened_by_name: String,
    pub subject: String,
    pub clauses: Vec<u8>,
    pub claims: Vec<ClaimDto>,
    pub decision: Option<DecisionDto>,
    pub open: bool,
}

/// Eslatma: `REVIEW` (ochiq hisob ko'rigi) yoki `RENEWAL` (yillik yangilash).
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct ReminderDto {
    pub agreement_id: String,
    /// Sheriklik yoki oilaviy kelishuv identifikatori (ekranni ochish uchun).
    pub ref_id: String,
    pub agreement_type: String,
    pub kind: String,
    pub title: String,
    pub due_on: String,
    /// `UPCOMING`, `DUE`, `OVERDUE`.
    pub state: String,
    pub days: i32,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct GovernanceDto {
    pub partnership_id: String,
    pub title: String,
    pub status: String,
    pub in_dispute: bool,
    pub writable: bool,
    pub read_only_reason: Option<String>,
    pub parties: Vec<PartyRefDto>,
    pub duties: Vec<DutyDto>,
    pub incidents: Vec<IncidentDto>,
    pub reviews: Vec<ReviewDto>,
    pub disputes: Vec<DisputeDto>,
    pub arbiter_name: Option<String>,
    pub review_every_days: u32,
    pub next_review_due: Option<String>,
    pub review_reminder: Option<ReminderDto>,
    /// Kuchdagi versiyadagi `reviewDate` (9-savol).
    pub review_date: Option<String>,
    pub renewal_reminder: Option<ReminderDto>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct FamilyAgreementInput {
    /// `CHORES`, `MONEY_PLACE`, `WANT_LIMIT`, `COUNCIL`, `OTHER`.
    pub template_key: String,
    pub title: String,
    pub items: Vec<String>,
    pub review_date: Option<String>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct FamilyAgreementDto {
    pub id: String,
    pub template_key: String,
    pub title: String,
    pub items: Vec<String>,
    pub review_date: Option<String>,
    /// `DRAFT` — kattalar hali tasdiqlamagan, `ACTIVE` — hamma tasdiqlagan.
    pub status: String,
    pub adults: Vec<SignoffDto>,
    pub hash_code: String,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct AgreementSummaryDto {
    pub agreement_id: String,
    pub agreement_type: String,
    /// Sheriklik id (PARTNERSHIP), aks holda kelishuv id.
    pub ref_id: String,
    pub title: String,
    pub status: String,
    pub next_review: Option<String>,
    pub reminder: Option<ReminderDto>,
    pub open_incidents: u32,
    pub open_disputes: u32,
}

// ---- U14: `.baraka` eksport/import va qurilmalarni ulash ----

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct DeviceDto {
    pub id: String,
    pub name: String,
    pub platform: String,
    pub paired_at: String,
    /// Shu qurilma.
    pub is_this: bool,
    pub last_import_at: Option<String>,
    pub last_export_at: Option<String>,
    /// K8: `SELLER` yoki `ACCOUNTANT` (rolsiz — egasi va oila qurilmasi).
    pub role: Option<String>,
    pub space_id: Option<String>,
    pub revoked: bool,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct ExportInput {
    pub password: String,
    /// `FULL` (zaxira yoki birinchi sinxronlash) yoki `INCREMENTAL`.
    pub mode: String,
    /// Qaysi qurilma uchun (inkremental eksportda majburiy).
    pub peer_device_id: Option<String>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct ExportFileDto {
    pub export_id: String,
    pub file_name: String,
    pub mode: String,
    pub rows: u32,
    pub bytes: Vec<u8>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct ImportItemDto {
    /// `<jadval>:<kalit>` — ziddiyatni tanlashda shu kalit qaytariladi.
    pub key: String,
    pub table: String,
    pub row_id: String,
    pub label: String,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct RejectedItemDto {
    pub key: String,
    pub table: String,
    pub row_id: String,
    pub label: String,
    /// `ROLE_FORBIDDEN`, `PERIOD_CLOSED`, `CASH_DAY_CLOSED`, `INSUFFICIENT_STOCK`, `EXCEEDS_OUTSTANDING`, `LINKED_REJECTED`.
    pub reason: String,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct FieldDiffDto {
    pub field: String,
    /// Ko'rsatish uchun tayyor qiymat (summa — formatlangan).
    pub local: String,
    pub remote: String,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct ConflictDto {
    pub key: String,
    pub table: String,
    pub row_id: String,
    pub label: String,
    pub fields: Vec<FieldDiffDto>,
    pub local_deleted: bool,
    pub remote_deleted: bool,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct ForkDto {
    pub agreement_id: String,
    pub title: String,
    pub seq: u32,
    /// `FORK` (ayrilish), `TAMPERED` (fayldagi yozuv o'zgartirilgan), `NOT_KEEPER_WRITE`
    /// (jurnalga hisob yurituvchi bo'lmagan qurilma yozgan).
    pub reason: String,
}

/// Import oldidan: nima qo'shiladi, nima o'zgaradi, ziddiyatlar va to'xtatuvchi muammolar.
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct ImportPreviewDto {
    pub source_device_id: String,
    pub source_device_name: String,
    pub mode: String,
    pub exported_at: String,
    pub rows: u32,
    pub inserts: u32,
    pub updates: u32,
    pub same: u32,
    pub kept_local: u32,
    pub journal_appended: u32,
    pub protected: Vec<ImportItemDto>,
    /// K8: rolli qurilmaning qabul qilinmagan yozuvlari (sababi bilan).
    pub rejected: Vec<RejectedItemDto>,
    /// K8: rolli qurilma faylidagi egasining o'z yozuvlari — e'tiborsiz.
    pub ignored: u32,
    pub conflicts: Vec<ConflictDto>,
    pub forks: Vec<ForkDto>,
    /// Ayrilish yo'q — import qilish mumkin (ziddiyatlar tanlangandan keyin).
    pub can_apply: bool,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct ConflictChoiceInput {
    pub key: String,
    /// `LOCAL` yoki `REMOTE`.
    pub choice: String,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct ImportResultDto {
    pub inserted: u32,
    pub updated: u32,
    pub conflicts_local: u32,
    pub conflicts_remote: u32,
    pub protected: u32,
    pub journal_appended: u32,
    pub rejected: u32,
    pub ignored: u32,
}

/// Yangi qurilmani ulash (8.5): QR va qo'lda kiritiladigan kod, shu kod bilan shifrlangan fayl.
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct PairingOfferDto {
    pub code: String,
    pub qr_svg: String,
    pub file_name: String,
    pub household_name: String,
    pub bytes: Vec<u8>,
}

/// Mavjud xonadonga qo'shilish yoki zaxira nusxadan tiklash.
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct JoinInput {
    /// Ulash kodi (QR'dan yoki qo'lda) yoki zaxira nusxa paroli.
    pub secret: String,
    pub device_name: String,
    pub platform: String,
}

/// U15: sozlamalar. `locale` — amaldagi til (qurilmaniki bo'lsa — u, aks holda xonadonniki).
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct SettingsDto {
    pub locale: String,
    pub household_locale: String,
    /// Faqat shu qurilmaga tegishli til (sinxronlanmaydi).
    pub device_locale: Option<String>,
    pub income_rhythm: Option<String>,
    pub debts_declared: bool,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct SettingsInput {
    /// `uz`, `uz-Cyrl`, `ru` yoki `null` (xonadon tili).
    pub locale: Option<String>,
    pub income_rhythm: Option<String>,
    pub debts_declared: bool,
}

/// Bosh sahifa eslatmasi: `INCOME_TODAY`, `INCOME_QUIET` (`days` — oxirgi daromaddan beri,
/// `null` — hali yo'q), `PAYDAY`, `DEBT_INVENTORY`, `BACKUP` (`days` — oxirgi zaxiradan beri).
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct NudgeDto {
    pub kind: String,
    pub days: Option<u32>,
}

// ---- K1: Kasb-kor «ikki cho'ntak» ----

/// Kasb-kor bosh sahifasi. `cashFlow` = tushum − chiqim («egasi oldi», kapital va maosh kirmaydi).
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct KkOverviewDto {
    pub period_start: String,
    /// Davrning oxirgi kuni (shu kun ham kiradi).
    pub period_end: String,
    /// Shu oy egasi maoshi (o'tgan «Hisob kuni»da ushlangan summa ayirilgan); belgilanmagan bo'lsa `null`.
    pub owner_salary: Option<MoneyDto>,
    /// O'tgan oy maoshdan ortiq olingani uchun shu oy maoshidan ushlangan summa.
    pub salary_carry: Option<MoneyDto>,
    pub revenue: MoneyDto,
    pub expenses: MoneyDto,
    pub cash_flow: MoneyDto,
    pub owner_draws: MoneyDto,
    pub owner_salary_transferred: MoneyDto,
    pub contributions: MoneyDto,
    /// Bosh ekran 2-raqami: Uy'ga o'tkazilgan maosh + «egasi oldi».
    pub owner_paid: MoneyDto,
    pub salary_remaining: Option<MoneyDto>,
    /// Maoshdan ortiq olingan (faqat musbat bo'lsa).
    pub overdrawn: Option<MoneyDto>,
    pub cash: MoneyDto,
    pub card: MoneyDto,
    /// Uskuna xaridi va sotuvi (hamyonga ta'sir qiladi, pul oqimiga kirmaydi).
    pub equipment_purchases: MoneyDto,
    pub equipment_sales: MoneyDto,
    /// Tovar xaridi (K5): hamyondan chiqadi, pul oqimiga kirmaydi (tannarx sotilganda foydadan ayiriladi).
    pub stock_purchases: MoneyDto,
    /// Tovar qoldig'i hisobdagi qiymati va muzlagan tovarlar (qayta tiklash narxida), bugungi holat.
    pub stock_value: MoneyDto,
    pub stock_frozen_value: MoneyDto,
    pub stock_frozen_count: u32,
    /// Ta'minotchilarga qarz va undan muddati o'tgani (K6).
    pub payables: MoneyDto,
    pub payables_overdue: MoneyDto,
    /// Xodimlarga hozir to'lanadigani — o'tgan oylar uchun (K6).
    pub wages_owed: MoneyDto,
    /// Keyingi «Zakot kuni» — 30 kun ichida bo'lsa (K7).
    pub zakat_reminder: Option<String>,
    /// Tarozi tekshiruvi vaqti keldi (K7).
    pub scale_check_due: bool,
    /// Bosh ekran 1-raqami: haqiqiy foyda va uning tarkibi (K2).
    pub profit: KkProfitDto,
    /// Manfiy qoldiqli hamyonlar: `CASH`, `CARD`.
    pub negative_wallets: Vec<String>,
    /// Shu oy yozuvlari (yangisi birinchi).
    pub entries: Vec<KkEntryDto>,
    /// Oxirgi yopilgan davrning oxirgi kuni: undan oldingi sanaga yozib bo'lmaydi.
    pub closed_until: Option<String>,
    /// O'tgan oy hali yopilmagan va unda yozuvlar bor bo'lsa — o'sha davr boshi («Hisob kuni» eslatmasi).
    pub close_due: Option<String>,
    /// Oxirgi yopilgan kassa kuni (K4).
    pub cash_closed_until: Option<String>,
    /// Mijozlardagi pul (nasiya qoldig'i) va undan muddati o'tgani.
    pub receivables: MoneyDto,
    pub receivables_overdue: MoneyDto,
}

/// `kind`: `SALE`, `EXPENSE`, `OPENING`, `OWNER_DRAW`, `OWNER_CONTRIBUTION`, `OWNER_SALARY`, `TRANSFER`.
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct KkEntryDto {
    pub id: String,
    pub kind: String,
    pub wallet: String,
    pub to_wallet: Option<String>,
    pub amount: MoneyDto,
    pub occurred_on: String,
    pub note: Option<String>,
    pub category_id: Option<String>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct KkSaleInput {
    pub amount: String,
    /// `CASH` yoki `CARD`.
    pub channel: String,
    pub occurred_on: Option<String>,
    /// Buyurtma, mijoz yoki izoh.
    pub note: Option<String>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct KkMoveInput {
    /// `OPENING`, `OWNER_DRAW`, `OWNER_CONTRIBUTION`, `TRANSFER`.
    pub kind: String,
    pub wallet: String,
    pub to_wallet: Option<String>,
    pub amount: String,
    pub occurred_on: Option<String>,
    pub note: Option<String>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct KkSalaryInput {
    /// Bo'lmasa — shu oy maosh qoldig'i.
    pub amount: Option<String>,
    /// Qaysi hamyondan: `CASH` yoki `CARD` (Uy'dagi daromad kanali ham shu).
    pub wallet: String,
    pub occurred_on: Option<String>,
    pub note: Option<String>,
}

/// Maosh o'tkazildi: Kasb-kor hisobi va Uy'dagi daromad (1-qonun ulushi taklifi bilan).
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct KkSalaryPaidDto {
    pub overview: KkOverviewDto,
    pub uy_space_id: String,
    pub uy_income: IncomeRecordedDto,
}

/// Haqiqiy foyda (kasbkor/SPEC 3.1): ko'rinadigan − o'z mehnati − to'lanmagan oilaviy mehnat − eskirish
/// − uskuna chiqib ketishi. Ko'rinadigan = tushum − sotilgan tovar tannarxi − tovar yo'qotishlari − chiqim (K5).
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct KkProfitDto {
    pub revenue: MoneyDto,
    pub cogs: MoneyDto,
    /// Hisobdan chiqarish va inventarizatsiya farqi (manfiy — ortiqcha topilgan).
    pub stock_losses: MoneyDto,
    pub operating_expenses: MoneyDto,
    pub visible_profit: MoneyDto,
    /// O'z mehnati bahosi; kiritilmagan bo'lsa `null` (hisobda 0).
    pub owner_labor: Option<MoneyDto>,
    pub family_labor: MoneyDto,
    /// To'langan oilaviy mehnat (chiqimda bor; qayta ayirilmaydi).
    pub family_labor_paid: MoneyDto,
    pub depreciation: MoneyDto,
    /// Uskuna chiqib ketishi; manfiy — balansdan qimmatga sotilgan.
    pub disposal: MoneyDto,
    pub true_profit: MoneyDto,
}

/// `status`: `ACTIVE`, `DEPRECIATED` (muddat tugagan, ishlatilyapti), `DISPOSED`.
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct KkEquipmentDto {
    pub id: String,
    pub name: String,
    pub cost: MoneyDto,
    pub salvage: MoneyDto,
    pub useful_months: u32,
    pub acquired_on: String,
    /// Qaysi hamyondan to'langan; `null` — ilovagacha bor edi.
    pub wallet: Option<String>,
    /// Shu oy eskirishi.
    pub month_depreciation: MoneyDto,
    /// Shu oy oxiridagi balans qiymati.
    pub book_value: MoneyDto,
    /// Shu oydan keyin qolgan eskirish oylari.
    pub months_left: u32,
    pub status: String,
    pub disposed_on: Option<String>,
    pub disposal_proceeds: Option<MoneyDto>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct KkEquipmentInput {
    pub name: String,
    pub cost: String,
    /// Muddat oxirida qoladigan qiymat; bo'lmasa — 0.
    pub salvage: Option<String>,
    pub useful_months: u32,
    pub acquired_on: Option<String>,
    /// `CASH` / `CARD`; `null` — ilovagacha bor edi (hamyondan pul chiqmaydi).
    pub wallet: Option<String>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct KkDisposeInput {
    /// Sotilgan narx; bo'lmasa yoki 0 — yaroqsiz bo'ldi.
    pub proceeds: Option<String>,
    /// Pul tushgan hamyon (sotilgan bo'lsa majburiy).
    pub wallet: Option<String>,
    pub disposed_on: Option<String>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct KkFamilyLaborDto {
    pub id: String,
    pub person: String,
    pub worked_on: String,
    /// Ko'rsatish uchun: `80`, `2,5`.
    pub hours: String,
    pub hourly_rate: MoneyDto,
    pub value: MoneyDto,
    pub paid: bool,
    pub note: Option<String>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct KkFamilyLaborInput {
    pub person: String,
    /// Soat: `80`, `2,5` (ko'pi bilan 2 kasr raqam).
    pub hours: String,
    pub hourly_rate: String,
    /// Pul to'langan va chiqim sifatida yozilgan.
    pub paid: bool,
    pub worked_on: Option<String>,
    pub note: Option<String>,
}

/// Buyurtma kalkulyatori (kasbkor/SPEC 3.2). Summalar matn, yadroda parse qilinadi.
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct KkQuoteInput {
    pub material: Option<String>,
    pub hours: Option<String>,
    pub hourly_rate: Option<String>,
    pub travel: Option<String>,
    /// Uskuna eskirishidan shu buyurtmaga ulush.
    pub depreciation: Option<String>,
    /// Zaxira foizi: `5`, `2,5`.
    pub reserve_percent: Option<String>,
    pub price: Option<String>,
    pub advance: Option<String>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct KkQuoteDto {
    pub labor: MoneyDto,
    pub subtotal: MoneyDto,
    pub reserve: MoneyDto,
    pub cost: MoneyDto,
    pub margin: Option<MoneyDto>,
    /// Narx berilsa: o'z mehnatingizga qoladigan pul.
    pub labor_paid: Option<MoneyDto>,
    pub below_cost: Option<bool>,
    pub effective_hourly_rate: Option<MoneyDto>,
    pub material_shortfall: Option<MoneyDto>,
    pub advance_after_material: Option<MoneyDto>,
}

/// «Hisob kuni» qoidalari: soliq zaxirasi (OQ-K3) va qolgan pul taqsimoti. Foizlar matn (`4`, `2,5`).
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct KkCloseRulesDto {
    /// `NONE`, `REVENUE`, `PROFIT`, `FIXED`.
    pub tax_base: String,
    pub tax_percent: String,
    pub tax_fixed: Option<MoneyDto>,
    pub reserve_percent: String,
    pub working_percent: String,
    pub expansion_percent: String,
    pub sadaqa_percent: String,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct KkCloseRulesInput {
    pub tax_base: String,
    pub tax_percent: Option<String>,
    pub tax_fixed: Option<String>,
    pub reserve_percent: String,
    pub working_percent: String,
    pub expansion_percent: String,
    pub sadaqa_percent: String,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct KkAllocationDto {
    pub reserve: MoneyDto,
    pub working: MoneyDto,
    pub expansion: MoneyDto,
    pub sadaqa: MoneyDto,
}

/// «Hisob kuni» hisobi (kasbkor/SPEC 4.5): oy yakunlari, soliq zaxirasi, egasi maoshi, qolgan pul va
/// uning taqsimoti. Qolgan manfiy bo'lsa — taqsimot yo'q, izoh so'raladi.
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct KkCloseDraftDto {
    pub period_start: String,
    pub period_end: String,
    pub revenue: MoneyDto,
    pub expenses: MoneyDto,
    pub depreciation: MoneyDto,
    pub true_profit: MoneyDto,
    /// Shu oy maoshi; belgilanmagan bo'lsa `null` (unda «egasi oldi» maosh o'rnida).
    pub owner_salary: Option<MoneyDto>,
    pub owner_paid: MoneyDto,
    pub salary_remaining: Option<MoneyDto>,
    pub rules: KkCloseRulesDto,
    pub tax: MoneyDto,
    pub owner_pay: MoneyDto,
    /// Maoshdan ortiq olingan (faqat musbat bo'lsa).
    pub overdrawn: Option<MoneyDto>,
    pub remaining: MoneyDto,
    pub needs_explanation: bool,
    pub allocation: Option<KkAllocationDto>,
    /// Zaxira ulushi shu oy eskirishidan kam («uskunani almashtirish puli» yetmaydi).
    pub reserve_below_depreciation: bool,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct KkCloseInput {
    /// Yopiladigan davr boshi (`YYYY-MM-DD`).
    pub period_start: String,
    /// Maoshdan ortig'i keyingi oy maoshidan ushlansinmi.
    pub carry_overdraw: bool,
    /// Qolgan pul manfiy bo'lsa — majburiy: «nima bo'ldi?».
    pub explanation: Option<String>,
}

/// Yopilgan oy bayonnomasi (o'zgarmas).
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct KkMonthCloseDto {
    pub id: String,
    pub closed_at: String,
    pub summary: KkCloseDraftDto,
    pub carry_forward: MoneyDto,
    pub explanation: Option<String>,
    /// Tekshirish kodi (bayonnomalar zanjiri xeshining boshi).
    pub short_code: String,
}

/// Kunlik kassa yopish hisobi (kasbkor/SPEC 5.1). `counted` berilsa — farq va holat ham.
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct KkCashDraftDto {
    pub day: String,
    pub opening: MoneyDto,
    pub cash_sales: MoneyDto,
    pub cash_expenses: MoneyDto,
    pub owner_draws: MoneyDto,
    /// Kassadan kartaga (bankka) topshirilgan.
    pub handed_over: MoneyDto,
    pub other_in: MoneyDto,
    pub other_out: MoneyDto,
    pub expected: MoneyDto,
    pub counted: Option<MoneyDto>,
    pub difference: Option<MoneyDto>,
    /// `EXACT`, `SHORT`, `OVER`.
    pub status: Option<String>,
    /// 4 hafta ichida 3+ kamomad — «xato qidirish» taklifi.
    pub suggest_search: bool,
    pub last_closed: Option<String>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct KkCashCloseInput {
    pub day: String,
    pub counted: String,
    /// Farq bo'lsa majburiy: `UNRECORDED_EXPENSE`, `CHANGE_ERROR`, `GIVEN_ON_CREDIT`, `OWNER_TOOK`, `UNKNOWN`.
    pub reason: Option<String>,
    pub note: Option<String>,
}

/// Yopilgan kassa kuni (o'zgarmas).
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct KkCashDayDto {
    pub id: String,
    pub day: String,
    pub opening: MoneyDto,
    pub expected: MoneyDto,
    pub counted: MoneyDto,
    pub difference: MoneyDto,
    pub status: String,
    pub reason: Option<String>,
    pub note: Option<String>,
    pub suggest_search: bool,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct KkCustomerDto {
    pub id: String,
    pub name: String,
    pub phone: Option<String>,
    pub note: Option<String>,
    pub outstanding: MoneyDto,
    pub open_sales: u32,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct KkCustomerInput {
    pub name: String,
    pub phone: Option<String>,
    /// Telefon saqlansa — mijoz roziligi belgisi majburiy (OQ-Y3).
    pub phone_consent: bool,
    pub note: Option<String>,
}

/// Nasiya (kasbkor/SPEC 5.2). Ustama, jarima yoki foiz maydoni yo'q.
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct KkCreditSaleInput {
    pub customer_id: String,
    pub item: String,
    pub cash_price: Option<String>,
    pub credit_price: String,
    pub installments: u32,
    pub sold_on: Option<String>,
    /// Bo'lmasa — sotuvdan bir oy keyin.
    pub first_due: Option<String>,
    pub witness: Option<String>,
    pub note: Option<String>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct KkInstallmentDto {
    pub due: String,
    pub amount: MoneyDto,
    pub covered: MoneyDto,
    /// `PAID`, `OVERDUE`, `DUE`.
    pub state: String,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct KkCreditEventDto {
    pub id: String,
    /// `PAYMENT`, `FORGIVE`, `EXTEND`.
    pub kind: String,
    pub occurred_on: String,
    pub amount: Option<MoneyDto>,
    pub months: Option<u32>,
    pub wallet: Option<String>,
    pub note: Option<String>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct KkNextDueDto {
    pub date: String,
    pub amount: MoneyDto,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct KkCreditSaleDto {
    pub id: String,
    pub customer_id: String,
    pub customer_name: String,
    pub customer_phone: Option<String>,
    pub item: String,
    pub sold_on: String,
    pub cash_price: Option<MoneyDto>,
    pub credit_price: MoneyDto,
    pub installments: u32,
    pub witness: Option<String>,
    pub note: Option<String>,
    pub schedule: Vec<KkInstallmentDto>,
    pub paid: MoneyDto,
    pub forgiven: MoneyDto,
    pub outstanding: MoneyDto,
    /// `SETTLED`, `CURRENT`, `OVERDUE`.
    pub status: String,
    pub overdue_days: u32,
    /// `D1_30`, `D31_60`, `D61_90`, `D90_PLUS`.
    pub bucket: Option<String>,
    pub next_due: Option<KkNextDueDto>,
    /// Nasiya narxi − naqd narx (ma'lumot uchun).
    pub credit_markup: Option<MoneyDto>,
    pub events: Vec<KkCreditEventDto>,
    /// Shu hafta «gaplashaman» deb belgilangan.
    pub talk_this_week: bool,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct KkAgingDto {
    pub current: MoneyDto,
    #[serde(rename = "d1_30")]
    pub d1_30: MoneyDto,
    #[serde(rename = "d31_60")]
    pub d31_60: MoneyDto,
    #[serde(rename = "d61_90")]
    pub d61_90: MoneyDto,
    #[serde(rename = "d90_plus")]
    pub d90_plus: MoneyDto,
    pub total: MoneyDto,
}

/// Nasiya daftari: savdolar (ochiqlari birinchi), yosh guruhlari va joriy hafta (juma) boshi.
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct KkCreditBookDto {
    pub sales: Vec<KkCreditSaleDto>,
    pub aging: KkAgingDto,
    pub week_start: String,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct KkCreditPaymentInput {
    pub amount: String,
    pub wallet: String,
    pub paid_on: Option<String>,
    pub note: Option<String>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct KkCreditForgiveInput {
    /// Bo'lmasa — butun qoldiq.
    pub amount: Option<String>,
    pub on: Option<String>,
    pub note: Option<String>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct KkCreditExtendInput {
    pub months: u32,
    pub on: Option<String>,
    pub note: Option<String>,
}

// ---- K5: Kasb-kor «Tovar ham pul» ----

/// Tovar kartochkasi. Narxlar ko'rsatish birligiga: kg, l, m (`G`, `ML`, `MM`) yoki dona (`PCS`).
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct KkItemInput {
    pub name: String,
    /// `G`, `ML`, `PCS`, `MM`; yaratilgandan keyin o'zgarmaydi.
    pub unit: String,
    /// `AVERAGE` (standart) yoki `FIFO`; harakat bo'lgach o'zgarmaydi.
    pub method: Option<String>,
    pub sale_price: Option<String>,
    /// Joriy xarid narxi (qo'lda); bo'lmasa — oxirgi xarid narxi.
    pub replacement_price: Option<String>,
    /// Minimal qoldiq, ko'rsatish birligida (masalan «20» kg yoki «1,5» l).
    pub min_qty: Option<String>,
    /// «Muzlagan» chegarasi, kun (standart 90).
    pub frozen_days: Option<u32>,
    pub note: Option<String>,
}

/// `kind`: `PURCHASE`, `SALE`, `WRITE_OFF`, `COUNT` (inventarizatsiya: sanalgan miqdor).
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct KkStockMoveInput {
    pub kind: String,
    /// Ko'rsatish birligida (kg uchun 3 xonagacha kasr). `COUNT` da — sanalgan miqdor.
    pub qty: String,
    /// Xaridda — jami narx; sotuvda — tushum (bo'lmasa — sotuv narxi × miqdor); ortiqchada — qiymat.
    pub amount: Option<String>,
    /// Xaridda ixtiyoriy (`null` — ilovagacha bor edi); sotuvda majburiy.
    pub wallet: Option<String>,
    pub occurred_on: Option<String>,
    /// Hisobdan chiqarish va inventarizatsiyada majburiy.
    pub reason: Option<String>,
}

/// `kind`: `PURCHASE`, `SALE`, `WRITE_OFF`, `ADJUST`. `cost` — tannarx (xaridda — narx, ortiqchada — manfiy).
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct KkStockMoveDto {
    pub id: String,
    pub kind: String,
    pub occurred_on: String,
    /// Ishorali miqdor, ko'rsatish birligida («-80», «1,5»).
    pub qty: String,
    pub amount: Option<MoneyDto>,
    pub cost: MoneyDto,
    pub wallet: Option<String>,
    pub reason: Option<String>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct KkItemDto {
    pub id: String,
    pub name: String,
    pub unit: String,
    pub method: String,
    /// Qoldiq, ko'rsatish birligida («70», «1,5»).
    pub qty: String,
    /// Hisobdagi qiymat (tannarx bo'yicha).
    pub value: MoneyDto,
    /// Bir birlik tannarxi; qoldiq yo'q bo'lsa `null`.
    pub unit_cost: Option<MoneyDto>,
    pub sale_price: Option<MoneyDto>,
    /// Qo'lda kiritilgan joriy xarid narxi.
    pub replacement_price_input: Option<MoneyDto>,
    /// Hisobda ishlatilgani: qo'lda kiritilgan yoki oxirgi xarid narxi.
    pub replacement_price: Option<MoneyDto>,
    pub replacement_value: Option<MoneyDto>,
    /// «Inflyatsiya yegan kapital»: qayta tiklash − hisobdagi.
    pub inflation_gap: Option<MoneyDto>,
    /// «Shu narxda sotsangiz, bu tovarni qayta ololmaysiz».
    pub sale_below_replacement: bool,
    pub min_qty: Option<String>,
    pub below_min: bool,
    pub frozen_days: u32,
    pub last_sale_on: Option<String>,
    pub frozen: bool,
    pub note: Option<String>,
    /// Harakatlar (yangisi birinchi).
    pub moves: Vec<KkStockMoveDto>,
}

/// Tovarlar sahifasi: qoldiqlar va jami qiymatlar (qayta tiklash narxi bo'lmasa — hisobdagi).
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct KkStockDto {
    pub items: Vec<KkItemDto>,
    pub value: MoneyDto,
    pub replacement_value: MoneyDto,
    pub inflation_gap: MoneyDto,
    /// Muzlagan tovarlar qiymati (qayta tiklash narxida).
    pub frozen_value: MoneyDto,
    pub frozen_count: u32,
}

// ---- K6: Kasb-kor «Kelishuvni yozing» — xodimlar va ta'minotchilar ----

/// Xodim kelishuvi (`EMPLOYMENT`) shartlari. Summalar matn holida («3 000 000»); foiz, ustama yoki jarima
/// maydoni yo'q.
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct KkEmployeeInput {
    pub name: String,
    pub role: Option<String>,
    pub phone: Option<String>,
    pub phone_consent: bool,
    pub duties: Option<String>,
    pub hours: Option<String>,
    /// Oylik qat'iy haq.
    pub salary: String,
    /// Har oyning qaysi kuni to'lanadi (1–28).
    pub pay_day: u32,
    pub notice_days: u32,
    /// Avans qoldig'i chegarasi; bo'lmasa — kelishilmagan.
    pub max_advance: Option<String>,
    /// Avans necha oygacha ushlanadi (standart — 3).
    pub max_advance_installments: Option<u32>,
    /// Ishga kirgan sana (bo'lmasa — bugun).
    pub started_on: Option<String>,
    /// Ilovagacha xodimga qolgan qarz (manfiy — ortiq to'langan).
    pub opening_balance: Option<String>,
    pub arbiter: Option<String>,
    /// Qayta ko'rish sanasi (bo'lmasa — bir yildan keyin).
    pub review_on: Option<String>,
    pub note: Option<String>,
}

/// Ta'minotchi kelishuvi (`SUPPLY`). Tovar bog'lansa — yetkazish tovar qoldig'iga kiradi, narx shu
/// kelishuvda qotiriladi (ko'rsatish birligiga).
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct KkSupplierInput {
    pub name: String,
    pub phone: Option<String>,
    pub phone_consent: bool,
    pub goods: Option<String>,
    pub item_id: Option<String>,
    pub unit_price: Option<String>,
    /// Yetkazishdan necha kun ichida to'lanadi (0 — darhol).
    pub payment_days: u32,
    pub delivery: Option<String>,
    pub returns: Option<String>,
    pub started_on: Option<String>,
    pub arbiter: Option<String>,
    pub review_on: Option<String>,
    pub note: Option<String>,
}

/// Kelishuv holati. `status`: `DRAFT`, `SIGNED`, `ENDED`. `missing` — imzolashdan oldin to'ldiriladigan
/// maydonlar. `templateReview`: `PENDING` — shablon yurist ko'rigidan o'tmagan.
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct KkAgreementStateDto {
    pub status: String,
    pub signed_versions: u32,
    pub signed_on: Option<String>,
    pub effective_from: Option<String>,
    /// Oxirgi imzolangan versiyadan keyin shartlar o'zgargan.
    pub unsigned_changes: bool,
    pub missing: Vec<String>,
    pub can_sign: bool,
    pub template_version: u32,
    pub template_review: String,
    pub started_on: String,
    pub ended_on: Option<String>,
    pub review_on: String,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct KkSignInput {
    /// Qog'oz nusxa imzolangan sana (bo'lmasa — bugun).
    pub signed_on: Option<String>,
    /// Yangi shartlar qachondan amal qiladi (bo'lmasa — birinchi versiyada ishga kirgan sana, keyin — imzo sanasi).
    pub effective_from: Option<String>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct KkEmployeeTermsDto {
    pub role: Option<String>,
    pub duties: Option<String>,
    pub hours: Option<String>,
    pub salary: MoneyDto,
    pub pay_day: u32,
    pub notice_days: u32,
    pub max_advance: Option<MoneyDto>,
    pub max_advance_installments: u32,
    pub opening_balance: MoneyDto,
    pub arbiter: Option<String>,
    pub note: Option<String>,
}

/// Oylik hisob: `balance` — oy oxirida xodimga qarzimiz (manfiy — ortiq to'langan).
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct KkPayMonthDto {
    pub period_start: String,
    pub period_end: String,
    pub salary: MoneyDto,
    pub deducted: MoneyDto,
    pub net: MoneyDto,
    pub paid: MoneyDto,
    pub balance: MoneyDto,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct KkAdvanceDto {
    pub id: String,
    pub given_on: String,
    pub amount: MoneyDto,
    pub installments: u32,
    /// Har oy ushlanadigan ulushlar: davr boshi va summa.
    pub schedule: Vec<KkNextDueDto>,
    pub deducted: MoneyDto,
    pub outstanding: MoneyDto,
}

/// `kind`: `ADVANCE`, `WAGE`.
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct KkStaffEventDto {
    pub id: String,
    pub kind: String,
    pub occurred_on: String,
    pub amount: MoneyDto,
    pub wallet: String,
    pub note: Option<String>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct KkEmployeeDto {
    pub id: String,
    pub name: String,
    pub phone: Option<String>,
    pub agreement: KkAgreementStateDto,
    pub terms: KkEmployeeTermsDto,
    /// Shu oy hisoblangani bilan qoldiq (manfiy — ortiq to'langan).
    pub balance: MoneyDto,
    /// Hozir to'lanadigani: o'tgan oylar uchun qoldiq − shu oy to'langan (manfiy bo'lsa 0).
    pub due_now: MoneyDto,
    pub advances_outstanding: MoneyDto,
    /// Shu oy (yangisi birinchi).
    pub months: Vec<KkPayMonthDto>,
    pub advances: Vec<KkAdvanceDto>,
    pub events: Vec<KkStaffEventDto>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct KkStaffDto {
    pub employees: Vec<KkEmployeeDto>,
    /// Xodimlarga hozir to'lanadigani (o'tgan oylar uchun).
    pub owed: MoneyDto,
    pub advances_outstanding: MoneyDto,
    pub template_review: String,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct KkAdvanceInput {
    pub amount: String,
    pub installments: u32,
    /// Ushlash boshlanadigan oy ichidagi sana (bo'lmasa — avans berilgan oy).
    pub start_on: Option<String>,
    pub wallet: String,
    pub occurred_on: Option<String>,
    pub note: Option<String>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct KkWageInput {
    /// Bo'lmasa — hozirgi qoldiq (xodimga qarzimiz).
    pub amount: Option<String>,
    pub wallet: String,
    pub occurred_on: Option<String>,
    pub note: Option<String>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct KkSupplyTermsDto {
    pub goods: Option<String>,
    pub item_id: Option<String>,
    pub item_name: Option<String>,
    /// Tovar birligi: `G`, `ML`, `PCS`, `MM`.
    pub unit: Option<String>,
    pub unit_price: Option<MoneyDto>,
    pub payment_days: u32,
    pub delivery: Option<String>,
    pub returns: Option<String>,
    pub arbiter: Option<String>,
    pub note: Option<String>,
}

/// `state`: `PAID`, `DUE`, `OVERDUE`.
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct KkDeliveryDto {
    pub id: String,
    pub delivered_on: String,
    pub due_on: String,
    pub amount: MoneyDto,
    pub paid: MoneyDto,
    pub outstanding: MoneyDto,
    pub state: String,
    pub overdue_days: u32,
    /// Tovar bog'langan bo'lsa — miqdor (ko'rsatish birligida).
    pub qty: Option<String>,
    pub note: Option<String>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct KkSupplyPaymentDto {
    pub id: String,
    pub paid_on: String,
    pub amount: MoneyDto,
    pub wallet: String,
    /// Tovarsiz ta'minot: to'lov chiqim sifatida yozilgan.
    pub as_expense: bool,
    pub note: Option<String>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct KkSupplierDto {
    pub id: String,
    pub name: String,
    pub phone: Option<String>,
    pub agreement: KkAgreementStateDto,
    pub terms: KkSupplyTermsDto,
    pub outstanding: MoneyDto,
    pub overdue: MoneyDto,
    pub due_soon: MoneyDto,
    pub next_due: Option<KkNextDueDto>,
    /// Yangisi birinchi.
    pub deliveries: Vec<KkDeliveryDto>,
    pub payments: Vec<KkSupplyPaymentDto>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct KkSuppliersDto {
    pub suppliers: Vec<KkSupplierDto>,
    pub outstanding: MoneyDto,
    pub overdue: MoneyDto,
    pub due_soon: MoneyDto,
    pub template_review: String,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct KkDeliveryInput {
    pub delivered_on: Option<String>,
    /// Tovar bog'langan bo'lsa majburiy (ko'rsatish birligida).
    pub qty: Option<String>,
    /// Bo'lmasa — qotirilgan narx × miqdor.
    pub amount: Option<String>,
    pub note: Option<String>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct KkSupplyPaymentInput {
    /// Bo'lmasa — eng yaqin muddatdagi qoldiq.
    pub amount: Option<String>,
    pub wallet: String,
    pub paid_on: Option<String>,
    pub note: Option<String>,
}

// ---- K7: Kasb-kor kengayish darvozasi, konvertlar, zakot, inventarizatsiya, tarozi ----

/// `fund`: `TAX`, `RESERVE`, `WORKING`, `EXPANSION`, `SADAQA`.
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct KkFundDto {
    pub fund: String,
    pub added: MoneyDto,
    pub used: MoneyDto,
    pub balance: MoneyDto,
}

/// `code`: `RESERVE`, `PROFIT`, `RECEIVABLES`, `INTEREST_DEBT`, `PLAN`.
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct KkGateConditionDto {
    pub code: String,
    pub ok: bool,
}

/// Kengayish darvozasi (kasbkor/SPEC 6.1): shartlar, ularning raqamlari va konvertlar.
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct KkGateDto {
    pub open: bool,
    pub conditions: Vec<KkGateConditionDto>,
    pub reasons: Vec<String>,
    /// Biznes zaxirasi (konvert qoldig'i).
    pub reserve: MoneyDto,
    pub average_opex: Option<MoneyDto>,
    pub required_reserve: Option<MoneyDto>,
    /// Necha oylik zaxira: «2,35».
    pub coverage_months: Option<String>,
    pub required_months: u32,
    /// Hisobga olingan oxirgi «Hisob kuni»lar haqiqiy foydasi (eskisi birinchi).
    pub true_profits: Vec<MoneyDto>,
    pub receivables: MoneyDto,
    pub receivables_90: MoneyDto,
    /// 90+ nasiya ulushi va chegarasi, foizda («5», «10»).
    pub bad_debt_percent: String,
    pub max_bad_percent: String,
    pub has_interest_debt: bool,
    pub has_payoff_plan: bool,
    /// Kengayish rejalari («Hunardan ishga») soni.
    pub plans: u32,
    pub funds: Vec<KkFundDto>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct KkFundUseInput {
    /// `RESERVE`, `WORKING`, `EXPANSION`, `SADAQA` (soliq zaxirasi — «Soliq» chiqimi bilan).
    pub fund: String,
    pub amount: String,
    pub used_on: Option<String>,
    pub note: Option<String>,
}

/// Darvoza chegaralari (OQ-K6), «Zakot kuni» (hijriy oy/kun), oltin narxi va nisob (OQ-D7), tovarni baholash
/// (`REPLACEMENT` yoki `BOOK`, OQ-D5), tarozi eslatmasi.
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct KkGrowthSettingsDto {
    pub reserve_months: u32,
    pub max_bad_percent: String,
    pub zakat_month: Option<u32>,
    pub zakat_day: Option<u32>,
    /// Keyingi «Zakot kuni» (milodiy, taxminiy ±1–2 kun).
    pub next_zakat_day: Option<String>,
    pub gold_price: Option<MoneyDto>,
    pub nisab_grams: u32,
    pub stock_valuation: String,
    pub scale_reminder: bool,
    /// Bugungi hijriy sana: `1448-05-06`.
    pub today_hijri: String,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct KkGrowthSettingsInput {
    pub reserve_months: u32,
    pub max_bad_percent: String,
    pub zakat_month: Option<u32>,
    pub zakat_day: Option<u32>,
    pub gold_price: Option<String>,
    pub nisab_grams: u32,
    pub stock_valuation: String,
    pub scale_reminder: bool,
}

/// `result`: `OK`, `ADJUSTED`, `FAULTY`.
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct KkScaleCheckInput {
    pub result: String,
    pub checked_on: Option<String>,
    pub note: Option<String>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct KkScaleCheckDto {
    pub id: String,
    pub checked_on: String,
    pub result: String,
    pub note: Option<String>,
}

/// Tarozi tekshiruvlari; `due` — eslatma yoqilgan va oxirgi tekshiruvdan 30 kundan ko'p o'tgan.
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct KkScaleDto {
    pub checks: Vec<KkScaleCheckDto>,
    pub reminder: bool,
    pub due: bool,
}

/// Zakot hisobi kiritmalari; bo'sh maydonlar — sozlamalardan yoki taklifdan.
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct KkZakatInput {
    pub gold_price: Option<String>,
    pub nisab_grams: Option<u32>,
    /// `REPLACEMENT` yoki `BOOK`.
    pub valuation: Option<String>,
    /// Egasi «umidsiz» deb belgilagan 90+ kunlik nasiyalar — bazaga kirmaydi.
    pub hopeless_sale_ids: Vec<String>,
    /// Hawl to'ldimi; bo'lmasa — ilova taklifi (birinchi yozuv yoki oxirgi hisobdan bir qamariy yil).
    pub hawl_complete: Option<bool>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct KkZakatReceivableDto {
    pub sale_id: String,
    pub customer: String,
    pub item: String,
    pub outstanding: MoneyDto,
    pub overdue_days: u32,
    /// 90+ kun — «umidsiz» deb belgilash mumkin.
    pub d90_plus: bool,
    pub hopeless: bool,
}

/// Zakot hisobi (kasbkor/SPEC 8.3) — **hisob, fatvo emas**. `religiousNote` — faqat ulamo tasdiqlagan matn
/// (`religiousReviewStatus = APPROVED`), aks holda `null`.
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct KkZakatDto {
    pub calculated_on: String,
    pub hijri_date: String,
    pub valuation: String,
    pub stock: MoneyDto,
    pub cash: MoneyDto,
    pub receivables: MoneyDto,
    pub payables: MoneyDto,
    pub wages_due: MoneyDto,
    pub debts: MoneyDto,
    pub gold_price: Option<MoneyDto>,
    pub nisab_grams: u32,
    pub nisab: Option<MoneyDto>,
    pub base: MoneyDto,
    pub zakat: MoneyDto,
    pub due: bool,
    /// `BASE_NOT_POSITIVE`, `BELOW_NISAB`, `HAWL_NOT_COMPLETE`, `GOLD_PRICE_MISSING`.
    pub reason: Option<String>,
    pub hawl_complete: bool,
    pub hawl_suggested: bool,
    pub hawl_since: Option<String>,
    pub receivable_lines: Vec<KkZakatReceivableDto>,
    pub religious_note: Option<String>,
    pub religious_review: String,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct KkZakatCalcDto {
    pub id: String,
    pub calculated_on: String,
    pub hijri_date: String,
    pub base: MoneyDto,
    pub nisab: MoneyDto,
    pub zakat: MoneyDto,
    pub reason: Option<String>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct KkInventoryLineInput {
    pub item_id: String,
    /// Sanalgan miqdor (ko'rsatish birligida); bo'sh — sanalmadi.
    pub counted: String,
}

/// Yillik inventarizatsiya (kasbkor/SPEC 8.4): barcha sanalgan tovarlar bitta tranzaksiyada.
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct KkInventoryInput {
    pub counted_on: Option<String>,
    /// Farqlar uchun umumiy izoh.
    pub reason: String,
    pub lines: Vec<KkInventoryLineInput>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct KkStockCountDto {
    pub id: String,
    pub counted_on: String,
    pub value_before: MoneyDto,
    pub value_after: MoneyDto,
    /// Sanalgan va farqi bor tovarlar soni.
    pub counted: u32,
    pub changed: u32,
}

// ---- K8: ko'p qurilma va rollar (ADR-0003) ----

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct DeviceRoleDto {
    /// `OWNER`, `SELLER`, `ACCOUNTANT`.
    pub role: String,
    pub space_id: Option<String>,
    pub space_name: Option<String>,
}

/// Ulash taklifi: rolsiz (oila qurilmasi, to'liq) yoki rol va Kasb-kor makoni bilan.
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct PairingInput {
    pub role: Option<String>,
    pub space_id: Option<String>,
}

/// Sotuvchi uchun tovar katalogi: tannarxsiz.
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct KkCatalogItemDto {
    pub id: String,
    pub name: String,
    pub unit: String,
    pub sale_price: Option<MoneyDto>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct KkSellerSaleInput {
    /// Katalogdan tovar (bo'lsa — miqdor majburiy, summa bo'sh bo'lsa sotuv narxi × miqdor).
    pub item_id: Option<String>,
    pub qty: Option<String>,
    pub amount: Option<String>,
    /// `CASH` yoki `CARD`.
    pub channel: String,
    pub note: Option<String>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct KkSellerSaleDto {
    pub id: String,
    /// `SALE` yoki `CREDIT_PAYMENT`.
    pub kind: String,
    pub label: String,
    pub qty: Option<String>,
    pub amount: MoneyDto,
    pub channel: String,
}

/// Sotuvchining bugungi kuni: faqat o'z yozuvlari.
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct KkSellerDayDto {
    pub day: String,
    pub sales: Vec<KkSellerSaleDto>,
    pub cash: MoneyDto,
    pub card: MoneyDto,
    pub shift_closed: bool,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct KkShiftInput {
    /// Faqat birinchi smenada (oldingi smena bo'lmasa): kassadagi boshlang'ich naqd.
    pub opening: Option<String>,
    pub counted: Option<String>,
    pub handed_over: Option<String>,
    /// Farq bo'lsa majburiy (kassa yopish sabablari).
    pub reason: Option<String>,
    pub note: Option<String>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct KkShiftDto {
    pub day: String,
    pub opening: MoneyDto,
    /// Ochilish oldingi smenadan olingan (kiritish shart emas).
    pub opening_known: bool,
    pub cash_sales: MoneyDto,
    pub credit_payments: MoneyDto,
    pub card_in: MoneyDto,
    pub expected: MoneyDto,
    pub counted: Option<MoneyDto>,
    pub difference: Option<MoneyDto>,
    pub status: Option<String>,
    pub handed_over: Option<MoneyDto>,
    pub left: Option<MoneyDto>,
    pub suggest_search: bool,
    pub closed: bool,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct KkShiftRecordDto {
    pub id: String,
    pub device_id: String,
    pub device_name: String,
    pub day: String,
    pub opening: MoneyDto,
    pub cash_sales: MoneyDto,
    pub credit_payments: MoneyDto,
    pub card_in: MoneyDto,
    pub expected: MoneyDto,
    pub counted: MoneyDto,
    pub difference: MoneyDto,
    pub status: String,
    pub reason: Option<String>,
    pub handed_over: MoneyDto,
    pub left: MoneyDto,
    pub note: Option<String>,
}

// ---- M1: Musofir makoni (docs/musofir/SPEC.md 2–4) ----

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct MfSettingsInput {
    pub country: Option<String>,
    /// `KRW`, `RUB`, `KZT`, `TRY`, `USD`, `EUR`, `GBP` (yoki uy valyutasi).
    pub work_currency: String,
    /// O'z ulushi foizda: `"20"`, `"12,5"`.
    pub share_percent: String,
    /// Qaytish jamg'armasi maqsadi — uy valyutasida (bo'sh — yo'q).
    pub target: Option<String>,
    pub return_on: Option<String>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct MfSettingsDto {
    pub country: Option<String>,
    pub work_currency: String,
    pub home_currency: String,
    pub share_bp: i32,
    pub share_percent: String,
    pub target: Option<MoneyDto>,
    pub return_on: Option<String>,
    /// Ish valyutasidagi yozuvlar bor — valyutani o'zgartirib bo'lmaydi.
    pub currency_locked: bool,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct MfRateInput {
    /// 1 ish valyutasi necha uy valyutasi: `"9,1"`.
    pub rate: String,
    pub rate_on: Option<String>,
    pub source: Option<String>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct MfRateDto {
    pub from_currency: String,
    pub to_currency: String,
    /// `"9,1"`.
    pub rate: String,
    pub rate_on: String,
    pub source: Option<String>,
    /// 30 kundan eski.
    pub stale: bool,
    /// Ish valyutasi uy valyutasi bilan bir xil (kurs 1).
    pub identity: bool,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct MfIncomeInput {
    /// `SALARY` yoki `OTHER_INCOME`.
    pub kind: String,
    pub amount: String,
    pub channel: String,
    pub occurred_on: Option<String>,
    pub note: Option<String>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct MfExpenseInput {
    pub amount: String,
    pub category_id: String,
    pub channel: String,
    pub occurred_on: Option<String>,
    pub note: Option<String>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct MfMoveInput {
    /// `OPENING`, `SENT_HOME`, `FUND_IN`, `FUND_OUT`, `FUND_OPENING`.
    pub kind: String,
    pub amount: String,
    /// `SENT_HOME`: komissiya (ish valyutasida).
    pub fee: Option<String>,
    /// `SENT_HOME`: uyda olingan summa (uy valyutasida).
    pub received: Option<String>,
    pub occurred_on: Option<String>,
    /// `FUND_OUT` uchun majburiy (sabab).
    pub note: Option<String>,
    /// `SENT_HOME`: maqsadlar (M2); bo'lmasa — kelishuv shartlaridan, ular ham bo'lmasa — uy xarajati 100 %.
    pub purposes: Option<Vec<MfShareInput>>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct MfEntryDto {
    pub id: String,
    /// `SALARY`, `OTHER_INCOME`, `EXPENSE` yoki `mf_moves` turi.
    pub kind: String,
    pub amount: MoneyDto,
    pub fee: Option<MoneyDto>,
    pub received: Option<MoneyDto>,
    pub channel: Option<String>,
    pub category_id: Option<String>,
    pub occurred_on: String,
    pub note: Option<String>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct MfMonthDto {
    pub income: MoneyDto,
    pub expenses: MoneyDto,
    pub sent_home: MoneyDto,
    pub fees: MoneyDto,
    pub fund_in: MoneyDto,
    pub fund_out: MoneyDto,
    pub fund_net: MoneyDto,
    pub pocket: MoneyDto,
    pub share_target: MoneyDto,
    pub share_gap: MoneyDto,
    /// Daromaddan ulushlar (`"31,15 %"`); daromad bo'lmasa `null`.
    pub expenses_percent: Option<String>,
    pub sent_percent: Option<String>,
    pub fund_percent: Option<String>,
    /// `POCKET_NEGATIVE`, `NO_SHARE`, `SHARE_BELOW_TARGET`, `FUND_WITHDRAWN`.
    pub warnings: Vec<String>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct MfFundDto {
    /// Ish valyutasida.
    pub balance: MoneyDto,
    pub avg_monthly: Option<MoneyDto>,
    /// Prognozga olingan to'liq oylar soni (0 — prognoz yo'q).
    pub months_used: u32,
    pub months_until_return: Option<i32>,
    /// Quyidagilar — uy valyutasida, kurs bilan (kurs yo'q bo'lsa `null`).
    pub balance_home: Option<MoneyDto>,
    pub avg_monthly_home: Option<MoneyDto>,
    pub target: Option<MoneyDto>,
    pub remaining_home: Option<MoneyDto>,
    pub progress_bp: Option<i32>,
    pub progress_percent: Option<String>,
    pub months_to_target: Option<i32>,
    pub projected_home: Option<MoneyDto>,
    pub shortfall_at_return: Option<MoneyDto>,
    /// `REACHED`, `ON_TRACK`, `BEHIND`, `NO_SAVING`, `NO_TARGET`, `NO_RATE`.
    pub status: String,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct MfOverviewDto {
    /// Sozlanmagan bo'lsa `null` — UI sozlash ustasini ochadi.
    pub settings: Option<MfSettingsDto>,
    /// Sozlash ustasidagi standart o'z ulushi (OQ-MF1).
    pub default_share_percent: String,
    pub period_start: String,
    pub period_end: String,
    pub month: Option<MfMonthDto>,
    pub fund: Option<MfFundDto>,
    pub rate: Option<MfRateDto>,
    pub entries: Vec<MfEntryDto>,
    /// «Qaytdim» belgilangan bo'lsa — sovutish davri (M3).
    pub cooling: Option<MfCoolingDto>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct MfIncomeRecordedDto {
    pub overview: MfOverviewDto,
    /// O'z ulushi taklifi: shu daromaddan qaytish jamg'armasiga.
    pub suggested_share: MoneyDto,
}

// ---- M2: «Ikki qirg'oq» (docs/musofir/SPEC.md 5, ADR-0004) ----

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct MfShareInput {
    /// `HOUSEHOLD`, `DEBT`, `BUILD`, `EDUCATION`, `CEREMONY`, `SAVINGS`, `OTHER`.
    pub purpose: String,
    /// Foizda: `"50"`, `"12,5"`.
    pub percent: String,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct MfShareDto {
    pub purpose: String,
    pub bp: i32,
    pub percent: String,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct MfTermsInput {
    pub shares: Vec<MfShareInput>,
    /// Uyda kim qabul qiladi (xonadon a'zosi).
    pub receiver_member_id: Option<String>,
    /// Oilaviy kelishuv matni (UI shartlardan taklif qiladi, foydalanuvchi o'zgartiradi).
    pub title: String,
    pub items: Vec<String>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct MfTermsDto {
    /// Belgilanmagan bo'lsa — bo'sh (standart: uy xarajati 100 %).
    pub shares: Vec<MfShareDto>,
    pub receiver_member_id: Option<String>,
    /// Uy makonidagi oilaviy kelishuv (kattalar tasdig'i bilan).
    pub agreement: Option<FamilyAgreementDto>,
    pub uy_space_id: Option<String>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct MfPurposeAmountDto {
    pub purpose: String,
    pub amount: MoneyDto,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct MfReceiptDto {
    pub received: MoneyDto,
    pub received_on: String,
    pub member_id: Option<String>,
    pub member_name: Option<String>,
    pub note: Option<String>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct MfRemittanceDto {
    pub move_id: String,
    /// Ish valyutasida (komissiyasiz).
    pub sent: MoneyDto,
    pub sent_on: String,
    pub note: Option<String>,
    pub shares: Vec<MfShareDto>,
    /// Musofir yozgan «uyda olingan» summa (taklif sifatida).
    pub expected: Option<MoneyDto>,
    /// `null` — hali qabul qilinmagan («yo'lda»).
    pub receipt: Option<MfReceiptDto>,
    /// Qabul qilingan summaning maqsadlarga bo'linishi.
    pub allocation: Vec<MfPurposeAmountDto>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct MfPurposeDto {
    pub purpose: String,
    pub received: MoneyDto,
    pub spent: MoneyDto,
    pub balance: MoneyDto,
    pub overspent: bool,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct MfSpendDto {
    /// Xarajat yoki U8 qarz to'lovining identifikatori.
    pub id: String,
    /// `EXPENSE` — Uy xarajati; `DEBT_PAYMENT` — «Qarz to'lovi» maqsadidan U8 to'lovi (M3).
    pub kind: String,
    pub purpose: String,
    pub amount: MoneyDto,
    /// Faqat `EXPENSE` da.
    pub category_id: Option<String>,
    /// Faqat `DEBT_PAYMENT` da: qarz va kreditor.
    pub debt_id: Option<String>,
    pub creditor: Option<String>,
    pub occurred_on: String,
    pub note: Option<String>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct MfTwoShoresDto {
    pub uy_space_id: Option<String>,
    pub remittances: Vec<MfRemittanceDto>,
    pub purposes: Vec<MfPurposeDto>,
    pub received: MoneyDto,
    pub spent: MoneyDto,
    pub balance: MoneyDto,
    /// Qabul qilinmagan yuborishlar.
    pub pending: u32,
    pub overspent: bool,
    pub spends: Vec<MfSpendDto>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct MfReceiptInput {
    /// Haqiqatda olingan summa — uy valyutasida.
    pub received: String,
    pub channel: String,
    pub member_id: Option<String>,
    pub received_on: Option<String>,
    pub note: Option<String>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct MfSpendInput {
    pub purpose: String,
    pub amount: String,
    /// Uy makonining kategoriyasi.
    pub category_id: String,
    pub channel: String,
    pub occurred_on: Option<String>,
    pub note: Option<String>,
}

// ---- M3: yo'l qarzi, qaytish va katta qarorlar (docs/musofir/SPEC.md 6) ----

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct MfDebtRefDto {
    pub id: String,
    pub creditor: String,
    pub reason: Option<String>,
    pub status: String,
    /// U8 qarz qoldig'i (uy valyutasida).
    pub outstanding: MoneyDto,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct MfTravelPlanDto {
    /// Qarz qoldig'i − «Qarz to'lovi» maqsadidagi pul.
    pub remaining: MoneyDto,
    /// «Qarz to'lovi» maqsadi qoldig'i (uyda).
    pub available: MoneyDto,
    pub avg_monthly: Option<MoneyDto>,
    /// O'rtacha nechta to'liq oydan (qabuli borlaridan) olindi.
    pub months_used: u32,
    pub months_to_clear: Option<i32>,
    pub clear_on: Option<String>,
    /// Maqsadli muddatda yopish uchun oyiga kerak.
    pub required_monthly: MoneyDto,
    /// `CLEARED`, `ON_TRACK`, `BEHIND`, `NO_PAYMENTS`.
    pub status: String,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct MfTravelDebtDto {
    /// Belgilangan yo'l qarzi (o'chirilgan bo'lsa — `null`).
    pub debt: Option<MfDebtRefDto>,
    pub target_months: u32,
    /// Uy makonidagi faol qarzlar (uy valyutasida) — tanlash uchun.
    pub candidates: Vec<MfDebtRefDto>,
    pub plan: Option<MfTravelPlanDto>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct MfTravelDebtInput {
    /// `null` — belgini olib tashlash.
    pub debt_id: Option<String>,
    /// 1–60 oy; bo'lmasa — 6 (OQ-MF8).
    pub target_months: Option<u32>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct MfDebtPaymentInput {
    /// Uy makonidagi U8 qarzi.
    pub debt_id: String,
    pub amount: String,
    pub paid_on: Option<String>,
    pub note: Option<String>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct MfReturnInput {
    /// `null` — «Qaytdim» belgisini olib tashlash.
    pub returned_on: Option<String>,
    /// Olib kelingan summa (uy valyutasida).
    pub brought_home: Option<String>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct MfCoolingDto {
    pub returned_on: String,
    pub brought_home: Option<MoneyDto>,
    pub in_cooling: bool,
    pub ends_on: Option<String>,
    pub days_left: i32,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct MfAnswerInput {
    pub key: String,
    /// `YES`, `NO`, `UNKNOWN`.
    pub reply: String,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct MfDecisionInput {
    /// `LEND`, `PARTNERSHIP`, `INVEST`, `PURCHASE`, `OTHER`.
    pub kind: String,
    pub title: String,
    /// Uy valyutasida.
    pub amount: String,
    pub answers: Vec<MfAnswerInput>,
    /// Yozishda: `WAIT`, `PROCEED`, `DECLINE`; tekshiruvda e'tiborga olinmaydi.
    pub choice: Option<String>,
    pub note: Option<String>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct MfFlagDto {
    pub code: String,
    /// `YELLOW`, `RED`.
    pub level: String,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct MfDecisionCheckDto {
    /// Shu qaror turi uchun savollar (tartibi bilan).
    pub questions: Vec<String>,
    pub in_cooling: bool,
    pub ends_on: Option<String>,
    pub days_left: i32,
    /// Summa olib kelinganning necha foizi.
    pub share_percent: Option<String>,
    pub flags: Vec<MfFlagDto>,
    /// `GREEN`, `YELLOW`, `RED`.
    pub verdict: String,
    pub wait_until: Option<String>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct MfAnswerDto {
    pub key: String,
    pub reply: String,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct MfDecisionDto {
    pub id: String,
    pub decided_on: String,
    pub kind: String,
    pub title: String,
    pub amount: MoneyDto,
    pub answers: Vec<MfAnswerDto>,
    pub flags: Vec<MfFlagDto>,
    pub verdict: String,
    pub in_cooling: bool,
    pub wait_until: Option<String>,
    pub choice: String,
    pub note: Option<String>,
}
