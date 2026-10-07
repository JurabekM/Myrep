use money::{Currency, Money};
use time::{Date, OffsetDateTime};

use crate::{
    AllocationKind, AssetType, MemberRole, Meta, MoneyOwner, Necessity, ObligationKind,
    PaymentChannel, VaultSource, VaultTxKind, WithdrawalStatus,
};

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Household {
    pub meta: Meta,
    pub name: String,
    pub base_currency: Currency,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Member {
    pub meta: Meta,
    pub display_name: String,
    pub role: MemberRole,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Category {
    pub meta: Meta,
    pub name: String,
    pub necessity: Option<Necessity>,
    /// "Kimning puli?" egasi (masalan, benzin → `Fuel`).
    pub owner: Option<MoneyOwner>,
    /// Sadaqa (SPEC 2B.8): havas emas va «oqib ketish» hisobiga kirmaydi.
    pub is_charity: bool,
    /// Foydalanuvchi o'zi kuzatadigan odat (masalan, chekish): faqat statistika.
    pub is_habit: bool,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Income {
    pub meta: Meta,
    pub member_id: String,
    pub source: String,
    pub channel: PaymentChannel,
    pub amount: Money,
    pub received_on: Date,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Expense {
    pub meta: Meta,
    pub member_id: String,
    pub category_id: String,
    pub amount: Money,
    pub spent_on: Date,
    pub payment_channel: PaymentChannel,
    // Keyingi vazifalar maydonlari — hozirdan nullable.
    pub necessity: Option<Necessity>,
    pub envelope_id: Option<String>,
    pub is_gift: Option<bool>,
    pub is_ostentation: Option<bool>,
    pub funded_by_debt: Option<bool>,
    /// Oylik audit ustasi kiritgan jami (`YYYY-MM`); oddiy xarajatda `None`.
    pub audit_month: Option<String>,
    /// Erkin izoh («somsa», «benzin»): «Hafta varag'i» kategoriyani shundan avtomatik topadi.
    pub note: Option<String>,
}

/// Har bir qiymat saqlovchi narsa `Asset` (SPEC 4.3). `quantity` minor birlikda
/// (oltin uchun milligramm).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Asset {
    pub meta: Meta,
    pub asset_type: AssetType,
    pub name: String,
    pub quantity: i64,
    pub unit: String,
    pub currency: Option<Currency>,
    pub acquired_at: OffsetDateTime,
}

/// Balans tarixi (zakotdagi hawl hisobi uchun).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct AssetSnapshot {
    pub meta: Meta,
    pub asset_id: String,
    pub quantity: i64,
    pub taken_at: OffsetDateTime,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct VaultTransaction {
    pub meta: Meta,
    pub asset_id: String,
    pub kind: VaultTxKind,
    pub amount: Money,
    pub occurred_at: OffsetDateTime,
    pub note: Option<String>,
    pub source: Option<VaultSource>,
    /// Ajratma qaysi daromaddan qilingan.
    pub income_id: Option<String>,
}

/// `value`: `Percent` uchun bazis punkt, `FixedAmount` uchun minor birlik.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct AllocationRule {
    pub meta: Meta,
    pub kind: AllocationKind,
    pub value: i64,
    pub currency: Option<Currency>,
}

/// Doimiy to'lov (`Recurring`: `amount` — oylik) yoki nasiya daftari qarzi (`Nasiya`: `amount` —
/// jami, `remaining` — qolgan, `creditor` — do'kondor). `Nasiya` D9 da `Debt` (SHOP) ga ko'chadi.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Obligation {
    pub meta: Meta,
    pub name: String,
    pub amount: Money,
    pub due_day: u8,
    pub kind: ObligationKind,
    pub owner: MoneyOwner,
    pub creditor: Option<String>,
    pub remaining: Option<Money>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct FxRateRecord {
    pub meta: Meta,
    pub from: Currency,
    pub to: Currency,
    pub rate_num: i64,
    pub rate_den: i64,
    pub date: Date,
    pub source: String,
}

/// "Kelajagim"dan pul olish so'rovi: pauza tugaguncha pul chiqmaydi.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct WithdrawalRequest {
    pub meta: Meta,
    pub asset_id: String,
    pub amount: Money,
    pub reason: String,
    pub available_at: OffsetDateTime,
    pub status: WithdrawalStatus,
}

/// Qo'lda belgilangan haftalik vazifa (avtomatik triggerlar ma'lumotdan hisoblanadi, saqlanmaydi).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct TaskCompletion {
    pub meta: Meta,
    pub chapter_id: String,
    pub task_id: String,
    /// Hafta boshi (juma).
    pub week_start: Date,
    pub completed_at: OffsetDateTime,
}

/// Bob qachon ochilgan (hafta boshi). Xonadon va bob bo'yicha bitta faol yozuv.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ChapterProgress {
    pub meta: Meta,
    pub chapter_id: String,
    pub opened_on: Date,
}

/// «Daftar sahifasi»: foydalanuvchi qonunni o'z so'zi bilan yozadi.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct DaftarPage {
    pub meta: Meta,
    pub chapter_id: String,
    pub body: String,
}

/// Xonadon sozlamasi (kalit-qiymat).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Setting {
    pub meta: Meta,
    pub key: String,
    pub value: String,
}

/// A'zoning shaxsiy PIN tekshiruvchisi (Argon2id). Havas chegarasiga rozilik shu PIN bilan beriladi.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct MemberCredential {
    pub meta: Meta,
    pub member_id: String,
    pub pin_hash: String,
    pub failures: u32,
    /// Unix soniya; `0` — bloklanmagan.
    pub locked_until: i64,
}

/// Kategoriya toifasi o'zgarishi tarixi: kim va qachon (`meta.created_at`).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct NecessityChange {
    pub meta: Meta,
    pub category_id: String,
    pub from: Option<Necessity>,
    pub to: Necessity,
    pub changed_by: String,
}

/// Oylik havas chegarasi taklifi. Faqat barcha `ADULT` a'zolar rozilik bergandan keyin kuchga kiradi.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct HavasLimit {
    pub meta: Meta,
    pub amount: Money,
    pub proposed_by: String,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct LimitConsent {
    pub meta: Meta,
    pub limit_id: String,
    pub member_id: String,
    pub consented_at: OffsetDateTime,
}

/// «Juma shirinligi»: kundalik havasni haftalik ritualga aylantirish.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ScheduledTreat {
    pub meta: Meta,
    pub name: String,
    pub amount: Money,
    /// ISO hafta kuni: 1 = dushanba ... 5 = juma ... 7 = yakshanba.
    pub weekday: u8,
    pub active: bool,
}
