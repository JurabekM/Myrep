//! IPC uchun ma'lumot shakllari (DTO). Pul — `minor` (satr, minor birlikda) va tayyor `formatted` matn;
//! frontend pul hisoblamaydi (DESKTOP_PROMPT.md 3.2). Sanalar — `YYYY-MM-DD` satri.

use domain::{Channel, Income, ObligationKind, ShareRule, ShareTarget, habit::HabitStats};
use money::{Locale, Money, format_money};
use serde::{Deserialize, Serialize};
use specta::Type;

/// Pul qiymati: minor birlik (satr), valyuta kodi va ko'rsatish uchun formatlangan matn.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Type)]
#[serde(rename_all = "camelCase")]
pub struct MoneyDto {
    /// Minor birliklar soni (satr: JS sonining 2^53 chegarasidan himoya).
    pub minor: String,
    /// ISO valyuta kodi.
    pub currency: String,
    /// Ko'rsatish uchun matn (`8 000 000 soʻm`).
    pub formatted: String,
}

impl MoneyDto {
    /// Pulni DTO'ga aylantiradi.
    pub fn of(money: Money) -> Self {
        Self {
            minor: money.minor().to_string(),
            currency: money.currency().iso_code().to_owned(),
            formatted: format_money(money, Locale::Uz),
        }
    }
}

/// Kanal (DTO): naqd yoki karta.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, Type)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum ChannelDto {
    /// Naqd pul.
    Cash,
    /// Karta.
    Card,
}

impl From<ChannelDto> for Channel {
    fn from(value: ChannelDto) -> Self {
        match value {
            ChannelDto::Cash => Self::Cash,
            ChannelDto::Card => Self::Card,
        }
    }
}

/// Majburiyat turi (DTO).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, Type)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum ObligationKindDto {
    /// Ijara.
    Rent,
    /// Kredit.
    Credit,
    /// Kommunal.
    Utility,
    /// Telefon.
    Phone,
    /// Yoqilg'i.
    Fuel,
    /// Boshqa.
    Other,
}

impl From<ObligationKindDto> for ObligationKind {
    fn from(value: ObligationKindDto) -> Self {
        match value {
            ObligationKindDto::Rent => Self::Rent,
            ObligationKindDto::Credit => Self::Credit,
            ObligationKindDto::Utility => Self::Utility,
            ObligationKindDto::Phone => Self::Phone,
            ObligationKindDto::Fuel => Self::Fuel,
            ObligationKindDto::Other => Self::Other,
        }
    }
}

/// Ulush rejimi (DTO).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, Type)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum ShareModeDto {
    /// Daromadning foizi.
    Percent,
    /// Oyiga qat'iy summa.
    Fixed,
}

/// Odat (streak) ko'rsatkichlari.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Type)]
#[serde(rename_all = "camelCase")]
pub struct HabitDto {
    /// Ketma-ket ajratilgan haftalar.
    pub current_streak_weeks: u32,
    /// Jami ajratilgan haftalar.
    pub total_weeks: u32,
    /// Joriy haftada ajratish bo'lganmi.
    pub this_week_done: bool,
}

impl From<&HabitStats> for HabitDto {
    fn from(stats: &HabitStats) -> Self {
        Self {
            current_streak_weeks: stats.current_streak_weeks,
            total_weeks: stats.total_weeks,
            this_week_done: stats.this_week_done,
        }
    }
}

/// Bosh ekran.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Type)]
#[serde(rename_all = "camelCase")]
pub struct HomeDto {
    /// «O'zingizga to'langan (shu oy)»: shu oy «Kelajagim»ga ajratilgan.
    pub paid_to_self: MoneyDto,
    /// «Kelajagim» balansi.
    pub vault_balance: MoneyDto,
    /// Shu oy daromadi.
    pub income: MoneyDto,
    /// Oy yakuni (+/−): daromad − (xarajat + yozilmagan majburiyat + sof jamg'arma).
    pub month_result: MoneyDto,
    /// Odat ko'rsatkichlari.
    pub habit: HabitDto,
    /// O'tgan oy auditi holati.
    pub audit: AuditStatusDto,
}

/// Audit holati: o'tkazilganmi va qaysi davr.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Type)]
#[serde(rename_all = "camelCase")]
pub struct AuditStatusDto {
    /// Audit yakunlanganmi.
    pub done: bool,
    /// Davr boshi (kiradi).
    pub period_start: String,
    /// Davr oxiri (kirmaydi).
    pub period_end: String,
}

/// Daromad yozuvi.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Type)]
#[serde(rename_all = "camelCase")]
pub struct IncomeDto {
    /// Identifikator.
    pub id: String,
    /// Manba.
    pub source: String,
    /// Kanal.
    pub channel: ChannelDto,
    /// Summa.
    pub amount: MoneyDto,
    /// Sana.
    pub occurred_on: String,
    /// Izoh.
    pub note: Option<String>,
}

impl IncomeDto {
    /// Daromadni DTO'ga aylantiradi.
    pub fn of(income: &Income) -> Self {
        Self {
            id: income.id.clone(),
            source: income.source.clone(),
            channel: match income.channel {
                Channel::Cash => ChannelDto::Cash,
                Channel::Card => ChannelDto::Card,
            },
            amount: MoneyDto::of(income.amount),
            occurred_on: crate::finance::date_text(income.occurred_on),
            note: income.note.clone(),
        }
    }
}

/// Daromad kiritilgandan keyingi natija: yozuv va ulush taklifi.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Type)]
#[serde(rename_all = "camelCase")]
pub struct IncomeOutcomeDto {
    /// Saqlangan daromad.
    pub income: IncomeDto,
    /// «Shundan X so'm — kelajagingiz uchun». `null` — taklif yo'q.
    pub share_suggestion: Option<MoneyDto>,
}

/// Daromad kiritish ma'lumoti (forma).
#[derive(Debug, Clone, PartialEq, Eq, Deserialize, Type)]
#[serde(rename_all = "camelCase")]
pub struct IncomeInputDto {
    /// Summa matni (masalan, `150 000`).
    pub amount: String,
    /// Manba.
    pub source: String,
    /// Kanal.
    pub channel: ChannelDto,
    /// Izoh.
    pub note: Option<String>,
}

/// «Qutqarilgan pul» hisobi (joriy davr). Summalar domen'da hisoblangan; UI faqat ko'rsatadi.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Type)]
#[serde(rename_all = "camelCase")]
pub struct RescueDto {
    /// Havas kamayishi (ko'rsatishda manfiy bo'lsa 0).
    pub havas: MoneyDto,
    /// Bekor qilingan obunalar tejami.
    pub subscriptions: MoneyDto,
    /// Konvertlardan qolgan qoldiqlar (davr ichida yopilgan).
    pub envelopes: MoneyDto,
    /// Jami qutqarilgan.
    pub total: MoneyDto,
    /// «Kelajagim»ga o'tkazilgan.
    pub transferred: MoneyDto,
    /// Hali o'tkazilmagan qismi.
    pub available: MoneyDto,
    /// Ko'proq sarflangan (ayblovsiz holat).
    pub spent_more: bool,
    /// Bazaviy davr bormi.
    pub has_baseline: bool,
    /// Bazaviy davr boshlanishi (`YYYY-MM-DD`), bo'lsa.
    pub baseline_start: Option<String>,
    /// Joriy davr boshlanishi (`YYYY-MM-DD`).
    pub period_start: String,
    /// Joriy davr tugashi, kirmaydi (`YYYY-MM-DD`).
    pub period_end: String,
}

/// Obuna satri.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Type)]
#[serde(rename_all = "camelCase")]
pub struct SubscriptionDto {
    /// Identifikator.
    pub id: String,
    /// Nomi.
    pub name: String,
    /// Oylik narx.
    pub monthly: MoneyDto,
    /// Yillik narx, bo'lsa.
    pub yearly: Option<MoneyDto>,
    /// Oxirgi «ishlatdim» sanasi.
    pub last_used_on: Option<String>,
    /// Bekor qilingan sana; `None` — faol.
    pub cancelled_on: Option<String>,
    /// «Unutilgan» obuna (faol va uzoq ishlatilmagan).
    pub forgotten: bool,
}

/// Konvert satri (joriy hafta).
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Type)]
#[serde(rename_all = "camelCase")]
pub struct EnvelopeDto {
    /// Identifikator.
    pub id: String,
    /// Nomi.
    pub name: String,
    /// Haftalik limit.
    pub weekly_limit: MoneyDto,
    /// Shu hafta sarflangan (bog'langan kategoriya bo'yicha).
    pub spent_this_week: MoneyDto,
    /// Shu hafta qoldiq (limit − sarflangan, manfiy emas).
    pub leftover_this_week: MoneyDto,
    /// Shu hafta yopilganmi (qoldiq «Qutqarilgan pul» ga yozilgan).
    pub closed_this_week: bool,
    /// Bog'langan kategoriya, bo'lsa.
    pub category_id: Option<String>,
}

/// Byudjet sahifasi: qutqarilgan pul, obunalar, konvertlar.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Type)]
#[serde(rename_all = "camelCase")]
pub struct BudgetDto {
    /// «Qutqarilgan pul» hisobi.
    pub rescue: RescueDto,
    /// Obunalar.
    pub subscriptions: Vec<SubscriptionDto>,
    /// Konvertlar.
    pub envelopes: Vec<EnvelopeDto>,
}

/// Obuna qo'shish.
#[derive(Debug, Clone, PartialEq, Eq, Deserialize, Type)]
#[serde(rename_all = "camelCase")]
pub struct SubscriptionInputDto {
    /// Nomi.
    pub name: String,
    /// Oylik narx matni.
    pub monthly: String,
    /// Yillik narx matni, ixtiyoriy.
    pub yearly: Option<String>,
}

/// Konvert qo'shish.
#[derive(Debug, Clone, PartialEq, Eq, Deserialize, Type)]
#[serde(rename_all = "camelCase")]
pub struct EnvelopeInputDto {
    /// Nomi.
    pub name: String,
    /// Haftalik limit matni.
    pub weekly_limit: String,
    /// Bog'lanadigan kategoriya, ixtiyoriy.
    pub category_id: Option<String>,
}

/// «Kelajagim»ga o'tkazish summasi.
#[derive(Debug, Clone, PartialEq, Eq, Deserialize, Type)]
#[serde(rename_all = "camelCase")]
pub struct TransferInputDto {
    /// Summa matni.
    pub amount: String,
}

/// Bazaviy davrni tanlash (shu davrning boshlanish sanasi).
#[derive(Debug, Clone, PartialEq, Eq, Deserialize, Type)]
#[serde(rename_all = "camelCase")]
pub struct BaselineInputDto {
    /// Davr boshlanishi (`YYYY-MM-DD`).
    pub period_start: String,
}

/// Amortizatsiya jadvalining bir qatori.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Type)]
#[serde(rename_all = "camelCase")]
pub struct ScheduleRowDto {
    /// Oy (1 dan).
    pub month: u32,
    /// Sana (`YYYY-MM-DD`).
    pub date: String,
    /// Foiz / ustama qismi.
    pub interest: MoneyDto,
    /// Asosiy qarz qismi.
    pub principal: MoneyDto,
    /// Qo'shimcha to'lov.
    pub extra: MoneyDto,
    /// Oydan keyingi qoldiq.
    pub balance: MoneyDto,
}

/// Jadval (odatiy yoki tezlashtirilgan).
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Type)]
#[serde(rename_all = "camelCase")]
pub struct ScheduleDto {
    /// Oylik to'lov (annuitetda doimiy; differensialda — birinchi oy).
    pub payment: MoneyDto,
    /// Oylar soni.
    pub months: u32,
    /// Jami foiz / ustama.
    pub total_interest: MoneyDto,
    /// Qarzsiz kun (oxirgi to'lov sanasi).
    pub debt_free_day: String,
    /// Qatorlar.
    pub rows: Vec<ScheduleRowDto>,
}

/// Payoff simulyatsiyasi natijasi: odatiy va tezlashtirilgan grafik.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Type)]
#[serde(rename_all = "camelCase")]
pub struct PayoffDto {
    /// Qo'shimcha to'lovsiz.
    pub standard: ScheduleDto,
    /// Qo'shimcha to'lov bilan.
    pub accelerated: ScheduleDto,
    /// Tejalgan foiz.
    pub interest_saved: MoneyDto,
    /// Qisqargan oylar.
    pub months_saved: u32,
}

/// Payoff simulyatsiyasi kirishi.
#[derive(Debug, Clone, PartialEq, Eq, Deserialize, Type)]
#[serde(rename_all = "camelCase")]
pub struct PayoffInputDto {
    /// `ANNUITY | DIFFERENTIATED | FIXED_MARKUP`.
    pub schedule_type: String,
    /// Asosiy summa matni.
    pub principal: String,
    /// Yillik stavka, bp (annuitet va differensial uchun).
    pub annual_bp: u32,
    /// Qat'iy ustama matni (`FIXED_MARKUP` uchun).
    pub markup: String,
    /// Muddat, oy.
    pub term_months: u32,
    /// Qo'shimcha oylik to'lov matni (bo'sh — 0).
    pub extra_per_month: String,
    /// Birinchi to'lov sanasi (`YYYY-MM-DD`); bo'sh — keyingi oy bugungi kun.
    pub start_date: Option<String>,
}

/// Byudjet rejimi va 70/20/10 taqsimoti.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Type)]
#[serde(rename_all = "camelCase")]
pub struct RecoveryDto {
    /// `STANDARD` yoki `DEBT_RECOVERY`.
    pub mode: String,
    /// Ulushlar, bp: ehtiyoj, qarz, jamg'arma.
    pub split_bp: Vec<u32>,
    /// Shu oy daromadi.
    pub income: MoneyDto,
    /// Qismlar (ehtiyoj, qarz, jamg'arma) shu oy daromadi bo'yicha.
    pub parts: Vec<MoneyDto>,
}

/// Byudjet rejimini va ulushlarni saqlash.
#[derive(Debug, Clone, PartialEq, Eq, Deserialize, Type)]
#[serde(rename_all = "camelCase")]
pub struct RecoveryInputDto {
    /// `STANDARD` yoki `DEBT_RECOVERY`.
    pub mode: String,
    /// Ulushlar, bp (yig'indisi 10 000; jamg'arma ≥ 100).
    pub split_bp: Vec<u32>,
}

/// Qarz (olingan yoki bergan) — ko'rsatish.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Type)]
#[serde(rename_all = "camelCase")]
pub struct LoanDto {
    /// Identifikator.
    pub id: String,
    /// `TAKEN` yoki `GIVEN`.
    pub direction: String,
    /// Kimdan / kimga.
    pub counterparty: String,
    /// Turi: `BANK | SHOP | RELATIVE | FRIEND | OTHER`.
    pub counterparty_type: String,
    /// Sabab.
    pub reason: Option<String>,
    /// Asosiy summa.
    pub principal: MoneyDto,
    /// To'langan.
    pub paid: MoneyDto,
    /// Qoldiq.
    pub outstanding: MoneyDto,
    /// Foizli (mavjud) qarz belgisi.
    pub has_markup: bool,
    /// Olingan sana.
    pub incurred_on: String,
    /// Keyingi to'lov sanasi, bo'lsa.
    pub next_due_on: Option<String>,
    /// Keyingi to'lov summasi, bo'lsa.
    pub next_amount: Option<MoneyDto>,
    /// Reja bo'yicha oxirgi to'lov sanasi.
    pub last_due_on: String,
    /// Rejadagi to'lovlar soni.
    pub installments: u32,
    /// Qarz oldidan tekshiruv natijasi (`OK | CAUTION | STOP`), bo'lsa.
    pub borrow_verdict: Option<String>,
    /// Tilxat (kelishuv), bo'lsa.
    pub agreement_id: Option<String>,
    /// To'liq yopilgan.
    pub settled: bool,
}

/// Qarzlar sahifasi.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Type)]
#[serde(rename_all = "camelCase")]
pub struct LoansDto {
    /// Olingan qarzlar.
    pub taken: Vec<LoanDto>,
    /// Bergan qarzlar.
    pub given: Vec<LoanDto>,
    /// Olingan qarzlar qoldig'i jami.
    pub total_outstanding: MoneyDto,
    /// Bergan qarzlardan qaytishi kutilayotgan jami.
    pub total_receivable: MoneyDto,
    /// Oylik yuk (barcha ochiq qarzlarning keyingi to'lovlari yig'indisi).
    pub monthly_burden: MoneyDto,
    /// Shu oy daromadi.
    pub monthly_income: MoneyDto,
    /// «Qarzsiz kun» (olingan qarzlar bo'yicha), bo'lsa.
    pub debt_free_day: Option<String>,
}

/// Qarz oldidan tekshiruv («to'xta va o'yla»).
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Type)]
#[serde(rename_all = "camelCase")]
pub struct BorrowCheckDto {
    /// `OK | CAUTION | STOP`.
    pub verdict: String,
    /// Yangi qarz bilan oylik yuk.
    pub monthly_burden: MoneyDto,
    /// Shu oy daromadi.
    pub monthly_income: MoneyDto,
    /// Yuk daromadga nisbatan, bp.
    pub burden_bp: u32,
}

/// Qarz qo'shish (olingan yoki bergan).
#[derive(Debug, Clone, PartialEq, Eq, Deserialize, Type)]
#[serde(rename_all = "camelCase")]
pub struct LoanInputDto {
    /// `TAKEN` yoki `GIVEN`.
    pub direction: String,
    /// Kimdan / kimga.
    pub counterparty: String,
    /// Turi.
    pub counterparty_type: String,
    /// Sabab.
    pub reason: Option<String>,
    /// Summa matni.
    pub principal: String,
    /// Mavjud foizli qarz (faqat kuzatish uchun).
    pub has_markup: bool,
    /// Olingan sana (`YYYY-MM-DD`); bo'sh — bugun.
    pub incurred_on: Option<String>,
    /// To'lovlar soni (teng bo'laklar).
    pub installments: u32,
    /// Birinchi to'lov sanasi (`YYYY-MM-DD`).
    pub first_due_on: String,
    /// Friction: zaruratmi (olingan qarz uchun).
    pub friction_necessity: Option<bool>,
    /// Friction: foizsiz muqobil tekshirilganmi.
    pub friction_alternative: Option<bool>,
}

/// Qarz oldidan tekshiruv so'rovi.
#[derive(Debug, Clone, PartialEq, Eq, Deserialize, Type)]
#[serde(rename_all = "camelCase")]
pub struct BorrowCheckInputDto {
    /// Summa matni.
    pub principal: String,
    /// To'lovlar soni.
    pub installments: u32,
}

/// Qarz to'lovi.
#[derive(Debug, Clone, PartialEq, Eq, Deserialize, Type)]
#[serde(rename_all = "camelCase")]
pub struct LoanPaymentInputDto {
    /// Qarz.
    pub loan_id: String,
    /// Summa matni.
    pub amount: String,
    /// Sana; bo'sh — bugun.
    pub paid_on: Option<String>,
}

/// Kelishuv tomoni (1-savol).
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize, Type)]
#[serde(rename_all = "camelCase")]
pub struct PartyDto {
    /// Identifikator (`P1`, `P2`, ...).
    pub id: String,
    /// To'liq ism-sharif.
    pub name: String,
    /// Roli.
    pub role: String,
    /// Aloqasi.
    pub relation: String,
    /// Shu qurilma egasi.
    pub is_me: bool,
}

/// Hissa (2-savol).
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize, Type)]
#[serde(rename_all = "camelCase")]
pub struct ContributionDto {
    /// Tomon.
    pub party_id: String,
    /// Turi: `money | goods | labor | connections`.
    pub kind: String,
    /// Miqdori matni (pul bo'lsa), bo'sh bo'lishi mumkin.
    pub amount: String,
    /// Tavsifi.
    pub description: String,
}

/// Vazifa (3-savol).
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize, Type)]
#[serde(rename_all = "camelCase")]
pub struct DutyDto {
    /// Identifikator.
    pub id: String,
    /// Nomi.
    pub title: String,
    /// Mas'ul tomon; bo'sh — egasiz (qabul qilinmaydi).
    pub owner_party_id: Option<String>,
    /// «Bajarilmasa» bandi.
    pub breach_clause: String,
}

/// Foyda ulushi (4-savol).
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize, Type)]
#[serde(rename_all = "camelCase")]
pub struct ProfitShareDto {
    /// Tomon.
    pub party_id: String,
    /// Ulush, bp.
    pub share_bp: u32,
}

/// Kelishuv javoblari — 9 savol (SPEC 2F.2). «Tegishli emas» — sabab matni bilan.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize, Type)]
#[serde(rename_all = "camelCase")]
pub struct AgreementAnswersDto {
    /// 1. Tomonlar.
    pub parties: Vec<PartyDto>,
    /// 2. Hissalar.
    pub contributions: Vec<ContributionDto>,
    /// 3. Vazifalar.
    pub duties: Vec<DutyDto>,
    /// 3 (LOAN). Qaytarish jadvali bormi.
    pub has_schedule: bool,
    /// 4. Ulushlar (bp).
    pub profit_shares: Vec<ProfitShareDto>,
    /// 4. Qat'iy summa matni (taqiqlangan; bo'sh bo'lishi kerak).
    pub profit_fixed_amount: String,
    /// 4. «Tegishli emas» sababi.
    pub profit_not_applicable: Option<String>,
    /// 5. Zarar qoidasi.
    pub loss_text: String,
    /// 5. «Tegishli emas» sababi.
    pub loss_not_applicable: Option<String>,
    /// 6. Pul qayerda.
    pub custody_location: String,
    /// 6. Hisob yurituvchi tomon.
    pub keeper_party_id: Option<String>,
    /// 6. Ko'rib chiqish davriyligi, kunlarda.
    pub review_every_days: u32,
    /// 7. Ogohlantirish muddati, kunlarda.
    pub exit_notice_days: u32,
    /// 7. Ulushni baholash.
    pub exit_valuation: String,
    /// 7. To'lash tartibi.
    pub exit_payout: String,
    /// 7. Mol-mulk.
    pub exit_assets: String,
    /// 7. «Tegishli emas» sababi.
    pub exit_not_applicable: Option<String>,
    /// 8. Hakam ismi (bo'sh — yo'q).
    pub arbiter_name: String,
    /// 8. Hakam roli.
    pub arbiter_role: String,
    /// 9. Muddat, oylarda.
    pub term_months: u32,
    /// 9. Keyingi ko'rib chiqish sanasi (`YYYY-MM-DD`), bo'sh — yo'q.
    pub review_date: String,
}

/// To'liqlik natijasi.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Type)]
#[serde(rename_all = "camelCase")]
pub struct CompletenessDto {
    /// 9/9 javoblangan.
    pub complete: bool,
    /// Javobsiz savollar (1–9).
    pub missing: Vec<u32>,
    /// Xato kodlari.
    pub errors: Vec<String>,
}

/// Imzo yozuvi.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Type)]
#[serde(rename_all = "camelCase")]
pub struct SignatureDto {
    /// Tomon (yoki guvoh/hakam) identifikatori.
    pub party_id: String,
    /// Roli: `PARTY | WITNESS | ARBITER`.
    pub role: String,
    /// Qaysi versiya uchun.
    pub version: u32,
    /// Imzolangan vaqt (RFC 3339).
    pub signed_at: String,
    /// Rasm (PNG, data URL).
    pub image: String,
}

/// Kelishuv (to'liq).
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Type)]
#[serde(rename_all = "camelCase")]
pub struct AgreementDto {
    /// Identifikator.
    pub id: String,
    /// Turi: `LOAN | PARTNERSHIP | FAMILY | OTHER`.
    pub kind: String,
    /// Sarlavha.
    pub title: String,
    /// Holati: `DRAFT | SIGNED | IN_DISPUTE | ENDED`.
    pub status: String,
    /// Versiya.
    pub version: u32,
    /// Amal qilish boshlanishi (`YYYY-MM-DD`), bo'lsa (og'zaki kelishuvda o'tmishda).
    pub effective_from: Option<String>,
    /// Javoblar.
    pub answers: AgreementAnswersDto,
    /// To'liqlik.
    pub completeness: CompletenessDto,
    /// Joriy versiya imzolari.
    pub signatures: Vec<SignatureDto>,
    /// Jurnal yozuvlari soni.
    pub journal_count: u32,
    /// Zanjir boshi (oxirgi xesh), bo'lsa.
    pub chain_head: Option<String>,
    /// Zanjir to'g'ri (qayta hisoblangan).
    pub chain_ok: bool,
    /// Shu qurilma hisob yurituvchimi (jurnalga yoza oladimi).
    pub can_write_journal: bool,
}

/// Kelishuv ro'yxati satri.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Type)]
#[serde(rename_all = "camelCase")]
pub struct AgreementSummaryDto {
    /// Identifikator.
    pub id: String,
    /// Turi.
    pub kind: String,
    /// Sarlavha.
    pub title: String,
    /// Holati.
    pub status: String,
    /// Versiya.
    pub version: u32,
    /// Javoblangan savollar (0–9).
    pub answered: u32,
    /// Keyingi ko'rib chiqish sanasi, bo'lsa.
    pub review_date: Option<String>,
}

/// Yangi kelishuv.
#[derive(Debug, Clone, PartialEq, Eq, Deserialize, Type)]
#[serde(rename_all = "camelCase")]
pub struct AgreementInputDto {
    /// Turi.
    pub kind: String,
    /// Sarlavha.
    pub title: String,
}

/// Javoblarni saqlash.
#[derive(Debug, Clone, PartialEq, Eq, Deserialize, Type)]
#[serde(rename_all = "camelCase")]
pub struct SaveAnswersInputDto {
    /// Kelishuv.
    pub id: String,
    /// Kutilgan versiya (optimistik).
    pub version: u32,
    /// Javoblar.
    pub answers: AgreementAnswersDto,
}

/// Imzo qo'shish.
#[derive(Debug, Clone, PartialEq, Eq, Deserialize, Type)]
#[serde(rename_all = "camelCase")]
pub struct SignatureInputDto {
    /// Kelishuv.
    pub agreement_id: String,
    /// Tomon / guvoh / hakam identifikatori.
    pub party_id: String,
    /// Roli: `PARTY | WITNESS | ARBITER`.
    pub role: String,
    /// Rasm (PNG, data URL).
    pub image: String,
}

/// Imzolashni yakunlash (og'zaki kelishuv uchun o'tmishdagi sana va boshlang'ich balans bilan).
#[derive(Debug, Clone, PartialEq, Eq, Deserialize, Type)]
#[serde(rename_all = "camelCase")]
pub struct SignInputDto {
    /// Kelishuv.
    pub agreement_id: String,
    /// Amal qilish boshlanishi (`YYYY-MM-DD`); bo'sh — bugun.
    pub effective_from: Option<String>,
    /// Boshlang'ich balans: tomon va summa matni (og'zaki kelishuvni yozib olishda).
    pub opening_balance_party_id: Option<String>,
    /// Boshlang'ich balans summasi.
    pub opening_balance_amount: Option<String>,
}

/// Jurnal yozuvi kiritish.
#[derive(Debug, Clone, PartialEq, Eq, Deserialize, Type)]
#[serde(rename_all = "camelCase")]
pub struct JournalEntryInputDto {
    /// Kelishuv.
    pub agreement_id: String,
    /// Tur: `CONTRIBUTION | PROFIT_DISTRIBUTION | LOAN_PAYMENT | CORRECTION`.
    pub kind: String,
    /// Tomon.
    pub party_id: String,
    /// Summa matni.
    pub amount: String,
    /// Sana (`YYYY-MM-DD`); bo'sh — bugun.
    pub date: Option<String>,
    /// Izoh.
    pub note: Option<String>,
}

/// Jurnal yozuvi (ko'rsatish).
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Type)]
#[serde(rename_all = "camelCase")]
pub struct JournalEntryDto {
    /// Tartib (1 dan).
    pub seq: u32,
    /// Tur.
    pub kind: String,
    /// Tomon.
    pub party_id: String,
    /// Summa.
    pub amount: MoneyDto,
    /// Sana.
    pub date: String,
    /// Izoh.
    pub note: Option<String>,
    /// Xesh.
    pub hash: String,
}

/// Jurnal ko'rinishi.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Type)]
#[serde(rename_all = "camelCase")]
pub struct JournalDto {
    /// Yozuvlar.
    pub entries: Vec<JournalEntryDto>,
    /// Zanjir to'g'ri.
    pub chain_ok: bool,
    /// Buzilgan bo'lsa — birinchi buzilgan yozuv (1 dan).
    pub first_broken: Option<u32>,
}

/// Qorovul zaxirasi holati (D8). Hisob domen'da; UI faqat ko'rsatadi.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Type)]
#[serde(rename_all = "camelCase")]
pub struct ReserveDto {
    /// «Kelajagim» balansi.
    pub balance: MoneyDto,
    /// Oylik `ZARUR + KERAK` o'rtachasi (3 ma'lumotli oy bo'yicha); yetarli oy bo'lmasa `null`.
    pub monthly_average: Option<MoneyDto>,
    /// Birinchi bosqich maqsadi (3 oy).
    pub target_first: Option<MoneyDto>,
    /// To'liq maqsad (6 oy).
    pub target_full: Option<MoneyDto>,
    /// Necha oylik zaxira bor, o'ndan bir (14 = 1,4 oy).
    pub reserve_months_tenths: Option<u32>,
    /// To'liq maqsad oylari (6).
    pub target_months: u32,
    /// Darvoza: `OPEN` yoki `LOCKED`.
    pub gate: String,
    /// Darvoza yopiq sabablari (`RESERVE_BELOW_TARGET`, `INTEREST_DEBT_WITHOUT_PLAN`).
    pub reasons: Vec<String>,
    /// Ma'lumotli (xarajati bo'lgan) o'tgan oylar soni (12 tagacha).
    pub data_months: u32,
}

/// Narx daftari yozuvi.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Type)]
#[serde(rename_all = "camelCase")]
pub struct PriceItemDto {
    /// Identifikator.
    pub id: String,
    /// Nomi.
    pub name: String,
    /// Bazaviy narx.
    pub base_price: MoneyDto,
    /// Joriy narx.
    pub current_price: MoneyDto,
    /// Bazaviy xarajatdagi ulush, bp.
    pub weight_bp: u32,
    /// O'zgarish, bp (indeks hisoblanmasa `null`).
    pub change_bp: Option<i32>,
}

/// Narx daftari: yozuvlar, indeks va «Sichqon kemirgani».
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Type)]
#[serde(rename_all = "camelCase")]
pub struct PricesDto {
    /// Yozuvlar.
    pub items: Vec<PriceItemDto>,
    /// Shaxsiy indeks, bp; og'irlikli yozuv bo'lmasa `null`.
    pub index_bp: Option<i32>,
    /// «Kelajagim» balansi (nominal).
    pub balance: MoneyDto,
    /// Balansning bugungi narxlardagi real qiymati.
    pub real_value: Option<MoneyDto>,
    /// Misol mahsulot nomi (birinchi yozuv).
    pub example_name: Option<String>,
    /// Bazaviy narxda nechta birlik.
    pub example_units_before: Option<u32>,
    /// Joriy narxda nechta birlik.
    pub example_units_now: Option<u32>,
}

/// Narx yozuvi kiritish.
#[derive(Debug, Clone, PartialEq, Eq, Deserialize, Type)]
#[serde(rename_all = "camelCase")]
pub struct PriceItemInputDto {
    /// Nomi.
    pub name: String,
    /// Bazaviy narx matni.
    pub base_price: String,
    /// Joriy narx matni.
    pub current_price: String,
    /// Ulush, bp (0..=10 000).
    pub weight_bp: u32,
}

/// CSV import: ustunlarni moslash.
#[derive(Debug, Clone, PartialEq, Eq, Deserialize, Type)]
#[serde(rename_all = "camelCase")]
pub struct CsvMappingDto {
    /// Ajratuvchi (`;`, `,` yoki tab). `None` — avtomatik.
    pub delimiter: Option<String>,
    /// Birinchi satr — sarlavha.
    pub has_header: bool,
    /// Sana ustuni (0 dan).
    pub date_column: u32,
    /// Summa ustuni (0 dan).
    pub amount_column: u32,
    /// Izoh ustuni, bo'lsa.
    pub note_column: Option<u32>,
    /// Barcha satrlar uchun kategoriya, bo'lsa.
    pub category_id: Option<String>,
    /// Musbat summalar (kirim) tashlanadi.
    pub skip_positive: bool,
}

/// CSV import: bitta satr ko'rinishi.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Type)]
#[serde(rename_all = "camelCase")]
pub struct CsvRowDto {
    /// Matndagi satr raqami (1 dan).
    pub line: u32,
    /// Sana (tahlil qilingan bo'lsa `YYYY-MM-DD`, aks holda asl matn).
    pub date: String,
    /// Summa (musbat, chiqim), tahlil qilingan bo'lsa.
    pub amount: Option<MoneyDto>,
    /// Izoh.
    pub note: Option<String>,
    /// Xato kodi: `CSV_BAD_DATE`, `CSV_DATE_OUT_OF_RANGE`, `CSV_BAD_AMOUNT`.
    pub error: Option<String>,
    /// Tashlangan (musbat summa).
    pub skipped: bool,
}

/// CSV import: ko'rib chiqish natijasi.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Type)]
#[serde(rename_all = "camelCase")]
pub struct CsvPreviewDto {
    /// Satrlar.
    pub rows: Vec<CsvRowDto>,
    /// Import bo'ladigan satrlar.
    pub importable: u32,
    /// Tashlanadigan (musbat) satrlar.
    pub skipped: u32,
    /// Xatoli satrlar.
    pub failed: u32,
}

/// CSV import so'rovi.
#[derive(Debug, Clone, PartialEq, Eq, Deserialize, Type)]
#[serde(rename_all = "camelCase")]
pub struct CsvImportInputDto {
    /// Joylangan matn.
    pub text: String,
    /// Ustunlar moslashuvi.
    pub mapping: CsvMappingDto,
}

/// «Kelajagim» yozuvi (tarix).
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Type)]
#[serde(rename_all = "camelCase")]
pub struct VaultEntryDto {
    /// Identifikator.
    pub id: String,
    /// Tur: `INITIAL`, `INCOME_SHARE` yoki `WITHDRAWAL`.
    pub kind: String,
    /// Summa.
    pub amount: MoneyDto,
    /// Sana.
    pub occurred_on: String,
    /// Pul olish sababi (faqat `WITHDRAWAL`).
    pub reason: Option<String>,
    /// Manba daromad (faqat `INCOME_SHARE`).
    pub income_id: Option<String>,
}

/// Ulush qoidasi.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Type)]
#[serde(rename_all = "camelCase")]
pub struct ShareRuleDto {
    /// Rejim.
    pub mode: ShareModeDto,
    /// Foiz (bp), faqat `PERCENT` rejimida.
    pub basis_points: Option<u32>,
    /// Oylik summa, faqat `FIXED` rejimida.
    pub fixed_amount: Option<MoneyDto>,
    /// Progressiv rejim.
    pub progressive: bool,
}

impl ShareRuleDto {
    /// Qoidani DTO'ga aylantiradi.
    pub fn of(rule: &ShareRule) -> Self {
        match rule.target {
            ShareTarget::Percent(bp) => Self {
                mode: ShareModeDto::Percent,
                basis_points: u32::try_from(bp).ok(),
                fixed_amount: None,
                progressive: rule.progressive,
            },
            ShareTarget::Fixed(amount) => Self {
                mode: ShareModeDto::Fixed,
                basis_points: None,
                fixed_amount: Some(MoneyDto::of(amount)),
                progressive: rule.progressive,
            },
        }
    }
}

/// «Kelajagim» ekrani.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Type)]
#[serde(rename_all = "camelCase")]
pub struct VaultDto {
    /// Balans.
    pub balance: MoneyDto,
    /// Shu oy ajratilgan summa.
    pub saved_this_month: MoneyDto,
    /// Boshlang'ich balans kiritilganmi.
    pub has_initial: bool,
    /// Ulush qoidasi.
    pub rule: ShareRuleDto,
    /// Odat.
    pub habit: HabitDto,
    /// Progressiv taklif: yangi ulush (bp). `null` — taklif yo'q.
    pub progression_offer_bp: Option<u32>,
    /// Oxirgi yozuvlar, eng yangisi birinchi.
    pub history: Vec<VaultEntryDto>,
}

/// Qoida kiritish ma'lumoti.
#[derive(Debug, Clone, PartialEq, Eq, Deserialize, Type)]
#[serde(rename_all = "camelCase")]
pub struct ShareRuleInputDto {
    /// Rejim.
    pub mode: ShareModeDto,
    /// Foiz (bp), `PERCENT` uchun.
    pub basis_points: Option<u32>,
    /// Oylik summa matni, `FIXED` uchun.
    pub fixed_amount: Option<String>,
    /// Progressiv rejim.
    pub progressive: bool,
}

/// Majburiyat va audit qatori.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Type)]
#[serde(rename_all = "camelCase")]
pub struct ObligationLineDto {
    /// Nomi.
    pub title: String,
    /// Tur kodi.
    pub kind: String,
    /// Oylik summa.
    pub amount: MoneyDto,
    /// Kategoriyada yozilgan qism.
    pub recorded: MoneyDto,
    /// Yozilmagan qism.
    pub remainder: MoneyDto,
}

/// Kategoriya bo'yicha shu oy xarajatlari.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Type)]
#[serde(rename_all = "camelCase")]
pub struct CategorySpentDto {
    /// Kategoriya identifikatori; `null` — kategoriyasiz.
    pub category_id: Option<String>,
    /// Nomi; `null` — kategoriyasiz.
    pub name: Option<String>,
    /// Tizim kaliti (standart kategoriya bo'lsa).
    pub system_key: Option<String>,
    /// Summa.
    pub amount: MoneyDto,
}

/// Kategoriya.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Type)]
#[serde(rename_all = "camelCase")]
pub struct CategoryDto {
    /// Identifikator.
    pub id: String,
    /// Nomi.
    pub name: String,
    /// Tizim kaliti (standart bo'lsa).
    pub system_key: Option<String>,
    /// Toifa kodi: `ZARUR | KERAK | HAVAS`.
    pub necessity: String,
}

/// Oylik audit ekrani.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Type)]
#[serde(rename_all = "camelCase")]
pub struct AuditDto {
    /// Davr boshi.
    pub period_start: String,
    /// Davr oxiri (kirmaydi).
    pub period_end: String,
    /// Audit yakunlanganmi.
    pub done: bool,
    /// Daromad.
    pub income: MoneyDto,
    /// Yozilgan xarajatlar.
    pub expenses: MoneyDto,
    /// Majburiyatlar jami.
    pub obligations_total: MoneyDto,
    /// Yozilmagan majburiyatlar.
    pub obligations_unrecorded: MoneyDto,
    /// Sof jamg'arma.
    pub net_savings: MoneyDto,
    /// Izohsiz qolgan summa.
    pub unexplained: MoneyDto,
    /// Majburiyatlar qatorlari.
    pub lines: Vec<ObligationLineDto>,
    /// Kategoriyalar bo'yicha xarajatlar.
    pub spent: Vec<CategorySpentDto>,
    /// Xarajat kiritish uchun kategoriyalar.
    pub categories: Vec<CategoryDto>,
}

/// «Kimning puli?» bo'lagi.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Type)]
#[serde(rename_all = "camelCase")]
pub struct OwnerPartDto {
    /// Egasi kodi (`LANDLORD`, `BANK`, `SHOP`, `UTILITIES`, `FUEL`, `SELF`, `SADAQA`, `OTHER`, `UNEXPLAINED`).
    pub owner: String,
    /// Summa.
    pub amount: MoneyDto,
    /// Jamdagi ulushi, basis points (1 % = 100 bp). Frontend shu qiymat bo'yicha bo'lak kengligini chizadi.
    pub share_bp: u32,
}

/// «Kimning puli?» ekrani.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Type)]
#[serde(rename_all = "camelCase")]
pub struct WhoseMoneyDto {
    /// Davr boshi.
    pub period_start: String,
    /// Davr oxiri (kirmaydi).
    pub period_end: String,
    /// Jami (barcha bo'laklar yig'indisi).
    pub total: MoneyDto,
    /// Egalar bo'yicha bo'laklar (faqat musbat).
    pub parts: Vec<OwnerPartDto>,
}

/// Majburiyat.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Type)]
#[serde(rename_all = "camelCase")]
pub struct ObligationDto {
    /// Identifikator.
    pub id: String,
    /// Nomi.
    pub title: String,
    /// Tur kodi.
    pub kind: String,
    /// Oylik summa.
    pub amount: MoneyDto,
    /// To'lov kuni.
    pub due_day: Option<u8>,
    /// Faolmi.
    pub active: bool,
}

/// Majburiyat kiritish ma'lumoti.
#[derive(Debug, Clone, PartialEq, Eq, Deserialize, Type)]
#[serde(rename_all = "camelCase")]
pub struct ObligationInputDto {
    /// Nomi.
    pub title: String,
    /// Turi.
    pub kind: ObligationKindDto,
    /// Oylik summa matni.
    pub amount: String,
    /// To'lov kuni (1..31).
    pub due_day: Option<u8>,
}

/// Nasiya.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Type)]
#[serde(rename_all = "camelCase")]
pub struct DebtDto {
    /// Identifikator.
    pub id: String,
    /// Kimga qarzdor (do'kon).
    pub creditor: String,
    /// Asl summa.
    pub principal: MoneyDto,
    /// Qoldiq.
    pub outstanding: MoneyDto,
    /// Olingan sana.
    pub incurred_on: String,
    /// Izoh.
    pub note: Option<String>,
}

/// Ko'p tilli matn: ikkala til ham doim to'ldirilgan (ruscha yo'q bo'lsa o'zbekcha nusxa).
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Type)]
#[serde(rename_all = "camelCase")]
pub struct LocalizedDto {
    /// O'zbekcha (asosiy).
    pub uz: String,
    /// Ruscha (yo'q bo'lsa — o'zbekcha).
    pub ru: String,
}

/// Bob qonuni (sarlavha va matn).
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Type)]
#[serde(rename_all = "camelCase")]
pub struct LawDto {
    /// Qonun raqami.
    pub number: u32,
    /// Qonun matni.
    pub text: LocalizedDto,
}

/// Bob bloki. Diniy blok release'da faqat tasdiqlangan holda keladi (`approved` har doim `true`).
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Type)]
#[serde(tag = "type", rename_all = "camelCase")]
pub enum ContentBlockDto {
    /// Oddiy abzats.
    Paragraph {
        /// Matn.
        text: LocalizedDto,
    },
    /// Iqtibos.
    Quote {
        /// Matn.
        text: LocalizedDto,
    },
    /// Oyat yoki hadis. `approved` `false` faqat ishlab chiqish (debug) rejimida chiqadi.
    Religious {
        /// Matn.
        text: LocalizedDto,
        /// Manba.
        source: LocalizedDto,
        /// Ulamo tasdiqlaganmi.
        approved: bool,
    },
}

/// Haftalik vazifa.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Type)]
#[serde(rename_all = "camelCase")]
pub struct TaskDto {
    /// Vazifa ID (`ch01.t1`).
    pub id: String,
    /// Vazifa matni.
    pub text: LocalizedDto,
    /// Ilova avtomatik belgilaydi (ko'rsatma uchun).
    pub auto_completed: bool,
    /// Bajarilganmi.
    pub done: bool,
}

/// Bob kartochkasi (ro'yxat uchun).
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Type)]
#[serde(rename_all = "camelCase")]
pub struct ChapterCardDto {
    /// Bob ID.
    pub id: String,
    /// Tartib raqami (1..5).
    pub order: u32,
    /// Sarlavha.
    pub title: LocalizedDto,
    /// Hozir ochiqmi.
    pub unlocked: bool,
    /// Ochilish sanasi (`YYYY-MM-DD`), aniq bo'lsa.
    pub unlock_date: Option<String>,
    /// Oldingi bobdan yana nechta vazifa kerak (yopiq bob uchun).
    pub tasks_remaining: u32,
    /// Kun sharti bo'yicha eng erta sana (aniq bo'lsa).
    pub not_before: Option<String>,
}

/// «Daftar sahifasi»: foydalanuvchining o'z so'zlari.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Type)]
#[serde(rename_all = "camelCase")]
pub struct DaftarPageDto {
    /// Bob ID.
    pub chapter_id: String,
    /// Qonun raqami.
    pub law_number: u32,
    /// Matn.
    pub body: String,
    /// Oxirgi yangilanish sanasi (Toshkent, `YYYY-MM-DD`).
    pub updated_on: String,
}

/// Bob sahifasi (ochiq bob uchun).
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Type)]
#[serde(rename_all = "camelCase")]
pub struct ChapterDto {
    /// Bob ID.
    pub id: String,
    /// Tartib raqami.
    pub order: u32,
    /// Sarlavha.
    pub title: LocalizedDto,
    /// Bloklar (diniy bloklar release'da tasdiqlangani bilan).
    pub blocks: Vec<ContentBlockDto>,
    /// Qonun.
    pub law: LawDto,
    /// Haftalik vazifalar. Joriy bob uchun — shu haftaniki; boshqa bob uchun — bir marta bajarilgan bo'lsa `done`.
    pub weekly_tasks: Vec<TaskDto>,
    /// Hozirgi (eng so'nggi ochilgan) bob mi — vazifalarni shu hafta belgilash mumkin.
    pub is_current: bool,
    /// Audio (https), bo'lsa.
    pub audio_url: Option<String>,
    /// «Daftar sahifasi», yozilgan bo'lsa.
    pub daftar_page: Option<DaftarPageDto>,
}

/// Joriy bobning shu haftalik vazifalari (bosh sahifa va bob sahifasi uchun).
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Type)]
#[serde(rename_all = "camelCase")]
pub struct WeeklyTasksDto {
    /// Joriy bob ID.
    pub chapter_id: String,
    /// Joriy bob sarlavhasi.
    pub chapter_title: LocalizedDto,
    /// Hafta boshi (juma, `YYYY-MM-DD`).
    pub week_start: String,
    /// Vazifalar.
    pub tasks: Vec<TaskDto>,
}

/// Xarajat yozuvi (ro'yxat va qo'shish natijasi).
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Type)]
#[serde(rename_all = "camelCase")]
pub struct ExpenseDto {
    /// Identifikator.
    pub id: String,
    /// Sana (`YYYY-MM-DD`, Toshkent).
    pub occurred_on: String,
    /// Summa.
    pub amount: MoneyDto,
    /// Kategoriya nomi (bo'lsa).
    pub category_name: Option<String>,
    /// Toifa kodi: `ZARUR | KERAK | HAVAS`.
    pub necessity: String,
    /// Izoh.
    pub note: Option<String>,
    /// Sovg'a: havas hisobiga kirmaydi.
    pub is_gift: bool,
    /// Obro' xarajati.
    pub is_ostentation: bool,
    /// Qarz bilan qilingan (qizil bayroq).
    pub funded_by_debt: bool,
}

/// Xarajat qo'shish formasi.
#[derive(Debug, Clone, PartialEq, Eq, Deserialize, Type)]
#[serde(rename_all = "camelCase")]
pub struct ExpenseInputDto {
    /// Sana (`YYYY-MM-DD`, shu hafta ichida). Yo'q bo'lsa — bugun.
    pub occurred_on: Option<String>,
    /// Summa matni (masalan, `150 000`).
    pub amount: String,
    /// Kategoriya (bo'lsa). Toifa kategoriyadan olinadi.
    pub category_id: Option<String>,
    /// Izoh.
    pub note: Option<String>,
    /// Sovg'a.
    pub is_gift: bool,
    /// Obro' xarajati.
    pub is_ostentation: bool,
    /// Qarz bilan qilingan.
    pub funded_by_debt: bool,
}

/// Oylik xulosa: uch toifa va belgilar bo'yicha jamlanma.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Type)]
#[serde(rename_all = "camelCase")]
pub struct MonthSummaryDto {
    /// Joriy hafta boshi (juma, `YYYY-MM-DD`) — hafta varag'i uchun.
    pub week_start: String,
    /// Bugun (Toshkent, `YYYY-MM-DD`).
    pub today: String,
    /// Davr boshi (`YYYY-MM-DD`).
    pub period_start: String,
    /// Davr oxiri (kirmaydi, `YYYY-MM-DD`).
    pub period_end: String,
    /// `ZARUR` toifadagi xarajatlar.
    pub zarur: MoneyDto,
    /// `KERAK` toifadagi xarajatlar.
    pub kerak: MoneyDto,
    /// Havas hisobi: `HAVAS`, sovg'a va sadaqa bo'lmagan xarajatlar.
    pub havas: MoneyDto,
    /// Sadaqa (havas hisobiga kirmaydi).
    pub sadaqa: MoneyDto,
    /// Sovg'alar (havas hisobiga kirmaydi).
    pub gifts: MoneyDto,
    /// Obro' xarajatlari (isrof tahlilida alohida).
    pub ostentation: MoneyDto,
    /// Qarz bilan qilingan xarajatlar (qizil bayroq).
    pub funded_by_debt: MoneyDto,
}

/// Kattaning havas chegarasiga roziligi.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Type)]
#[serde(rename_all = "camelCase")]
pub struct AdultConsentDto {
    /// A'zo identifikatori.
    pub member_id: String,
    /// Ismi.
    pub name: String,
    /// Rozilik bergan mi.
    pub consented: bool,
    /// PIN o'rnatilganmi (rozilik uchun kerak).
    pub has_pin: bool,
}

/// Havas chegarasi holati (ekran uchun).
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Type)]
#[serde(rename_all = "camelCase")]
pub struct HavasLimitDto {
    /// Oylik chegara (o'rnatilmagan bo'lsa — `null`).
    pub limit: Option<MoneyDto>,
    /// Shu oy havas sarfi.
    pub spent: MoneyDto,
    /// Daraja: `OK | WARNING | REACHED` (faqat faol chegarada yumshoq ogohlantirish).
    pub level: String,
    /// Chegara faolmi: barcha kattalar rozi bo'lgan.
    pub active: bool,
    /// Kattalar va ularning roziligi.
    pub adults: Vec<AdultConsentDto>,
}

/// Oila a'zosi.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Type)]
#[serde(rename_all = "camelCase")]
pub struct MemberDto {
    /// Identifikator.
    pub id: String,
    /// Ismi.
    pub name: String,
    /// Rol: `ADULT | CHILD`.
    pub role: String,
    /// PIN o'rnatilganmi.
    pub has_pin: bool,
}

/// Oila a'zosini qo'shish formasi. Kattaga PIN majburiy.
#[derive(Debug, Clone, PartialEq, Eq, Deserialize, Type)]
#[serde(rename_all = "camelCase")]
pub struct MemberInputDto {
    /// Ismi.
    pub name: String,
    /// Rol: `ADULT | CHILD`.
    pub role: String,
    /// PIN (6 raqam). Faqat kattalar uchun.
    pub pin: Option<String>,
}

/// Juma shirinligi (rejalashtirilgan ritual).
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Type)]
#[serde(rename_all = "camelCase")]
pub struct TreatDto {
    /// Identifikator.
    pub id: String,
    /// Nomi.
    pub name: String,
    /// Odatiy summa.
    pub amount: MoneyDto,
    /// Hafta kuni: 0 dushanba … 6 yakshanba.
    pub weekday: u8,
    /// Bugun ritual kunimi.
    pub due_today: bool,
}

/// Juma shirinligini qo'shish formasi.
#[derive(Debug, Clone, PartialEq, Eq, Deserialize, Type)]
#[serde(rename_all = "camelCase")]
pub struct TreatInputDto {
    /// Nomi.
    pub name: String,
    /// Summa matni.
    pub amount: String,
    /// Hafta kuni: 0 dushanba … 6 yakshanba.
    pub weekday: u8,
}

/// Odat statistikasi: oyiga va yiliga jami (ayblov yo'q — SPEC 2B.9).
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Type)]
#[serde(rename_all = "camelCase")]
pub struct OdatHabitDto {
    /// Kategoriya identifikatori.
    pub id: String,
    /// Nomi.
    pub name: String,
    /// Joriy oy jami.
    pub monthly: MoneyDto,
    /// Joriy yil jami.
    pub yearly: MoneyDto,
    /// Yil ichidagi yozuvlar soni.
    pub entries_this_year: u32,
}

/// Pul olish ma'lumoti (forma). PIN alohida argument sifatida keladi.
#[derive(Debug, Clone, PartialEq, Eq, Deserialize, Type)]
#[serde(rename_all = "camelCase")]
pub struct WithdrawInputDto {
    /// Summa matni.
    pub amount: String,
    /// Sabab (majburiy).
    pub reason: String,
}

#[cfg(test)]
mod tests {
    use super::*;
    use money::Currency;

    #[test]
    fn pul_dto_minor_satr_va_formatlangan_matn() {
        let dto = MoneyDto::of(Money::new(800_000_000, Currency::Uzs));
        assert_eq!(dto.minor, "800000000");
        assert_eq!(dto.currency, "UZS");
        assert!(dto.formatted.contains("8"), "{}", dto.formatted);
    }

    #[test]
    fn ulush_qoidasi_dto_shakli() {
        let percent = ShareRuleDto::of(&ShareRule::default_rule());
        assert_eq!(percent.mode, ShareModeDto::Percent);
        assert_eq!(percent.basis_points, Some(500));
        assert_eq!(percent.fixed_amount, None);
    }
}

/// Marosimlar sahifasi (D11).
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Type)]
#[serde(rename_all = "camelCase")]
pub struct CeremoniesDto {
    /// Marosimlar (yaratilish tartibida).
    pub items: Vec<CeremonyDto>,
}

/// Marosim rejasi.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Type)]
#[serde(rename_all = "camelCase")]
pub struct CeremonyDto {
    /// Identifikator.
    pub id: String,
    /// Turi: `TOY | BESHIK | SUNNAT | MARAKA | OTHER`.
    pub kind: String,
    /// Nomi.
    pub title: String,
    /// Sana (`YYYY-MM-DD`), bo'lmasligi mumkin.
    pub event_on: Option<String>,
    /// `PLANNED | CONFIRMED`.
    pub status: String,
    /// Oilaviy muhokama o'tkazilganmi.
    pub family_discussed: bool,
    /// Tanlangan stsenariy.
    pub chosen_scenario_id: Option<String>,
    /// Jamg'arma maqsadi nomi (to'yona o'rniga).
    pub goal_name: Option<String>,
    /// Maqsad summasi.
    pub goal_target: Option<MoneyDto>,
    /// Biror stsenariyda qarz manbasi bormi.
    pub has_debt: bool,
    /// Stsenariylar (taqqoslash uchun).
    pub scenarios: Vec<ScenarioDto>,
}

/// Marosim stsenariysi (hisoblangan ko'rsatkichlar bilan).
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Type)]
#[serde(rename_all = "camelCase")]
pub struct ScenarioDto {
    /// Identifikator.
    pub id: String,
    /// Nomi.
    pub name: String,
    /// Mehmonlar soni.
    pub guests: u32,
    /// Kunlar soni.
    pub days: u32,
    /// Byudjet qatorlari.
    pub lines: Vec<CeremonyLineDto>,
    /// Umumiy narx.
    pub total: MoneyDto,
    /// Qarz bilan qoplanadigan qism.
    pub debt_part: MoneyDto,
    /// Jamg'armadan.
    pub savings_part: MoneyDto,
    /// Oila hissasi.
    pub family_part: MoneyDto,
    /// Kutilayotgan to'yona.
    pub gifts_part: MoneyDto,
    /// Qarz manbasi bormi.
    pub has_debt: bool,
    /// Qarz qismini 70/20/10 «qarz» ulushi bilan to'lash muddati (oy); ulush 0 bo'lsa — yo'q.
    pub payoff_months: Option<u32>,
    /// Shu pulga necha oylik zarur xarajat chiqadi (muqobil maqsad); ma'lumot bo'lmasa — yo'q.
    pub months_of_needs: Option<u32>,
}

/// Byudjet qatori.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Type)]
#[serde(rename_all = "camelCase")]
pub struct CeremonyLineDto {
    /// Identifikator.
    pub id: String,
    /// Nomi.
    pub name: String,
    /// Miqdor.
    pub quantity: u32,
    /// Birlik narxi.
    pub unit_price: MoneyDto,
    /// Manba: `SAVINGS | FAMILY | EXPECTED_GIFTS | DEBT`.
    pub funding: String,
    /// Qator jami.
    pub total: MoneyDto,
}

/// Yangi marosim.
#[derive(Debug, Clone, PartialEq, Eq, Deserialize, Type)]
#[serde(rename_all = "camelCase")]
pub struct CeremonyInputDto {
    /// Turi.
    pub kind: String,
    /// Nomi.
    pub title: String,
    /// Sana (`YYYY-MM-DD`), ixtiyoriy.
    pub event_on: Option<String>,
}

/// Yangi stsenariy.
#[derive(Debug, Clone, PartialEq, Eq, Deserialize, Type)]
#[serde(rename_all = "camelCase")]
pub struct ScenarioInputDto {
    /// Marosim.
    pub ceremony_id: String,
    /// Nomi.
    pub name: String,
    /// Mehmonlar soni.
    pub guests: u32,
    /// Kunlar soni.
    pub days: u32,
}

/// Yangi byudjet qatori.
#[derive(Debug, Clone, PartialEq, Eq, Deserialize, Type)]
#[serde(rename_all = "camelCase")]
pub struct CeremonyLineInputDto {
    /// Stsenariy.
    pub scenario_id: String,
    /// Nomi.
    pub name: String,
    /// Miqdor.
    pub quantity: u32,
    /// Birlik narxi matni.
    pub unit_price: String,
    /// Manba.
    pub funding: String,
}

/// Tasdiqlash: tanlangan stsenariy bilan.
#[derive(Debug, Clone, PartialEq, Eq, Deserialize, Type)]
#[serde(rename_all = "camelCase")]
pub struct ConfirmCeremonyInputDto {
    /// Marosim.
    pub id: String,
    /// Tanlangan stsenariy.
    pub scenario_id: String,
}

/// To'yona o'rniga jamg'arma maqsadi.
#[derive(Debug, Clone, PartialEq, Eq, Deserialize, Type)]
#[serde(rename_all = "camelCase")]
pub struct CeremonyGoalInputDto {
    /// Marosim.
    pub id: String,
    /// Maqsad nomi.
    pub name: String,
    /// Summa matni.
    pub target: String,
}
