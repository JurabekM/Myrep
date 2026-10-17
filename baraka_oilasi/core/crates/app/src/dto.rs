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
    /// Egasining oylik maoshi; belgilanmagan bo'lsa `null`.
    pub owner_salary: Option<MoneyDto>,
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
    /// Manfiy qoldiqli hamyonlar: `CASH`, `CARD`.
    pub negative_wallets: Vec<String>,
    /// Shu oy yozuvlari (yangisi birinchi).
    pub entries: Vec<KkEntryDto>,
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
