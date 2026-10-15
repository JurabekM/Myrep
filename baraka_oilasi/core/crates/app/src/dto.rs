//! Adapterlar (FRB, tauri-specta) uchun DTO'lar. Pul har doim `MoneyDto`, sonli summalar string.
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
