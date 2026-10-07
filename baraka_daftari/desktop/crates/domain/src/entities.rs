use money::{Currency, Money};
use time::{Date, OffsetDateTime};

use crate::{AllocationKind, AssetType, MemberRole, Meta, Necessity, PaymentChannel, VaultTxKind};

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
}

/// `value`: `Percent` uchun bazis punkt, `FixedAmount` uchun minor birlik.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct AllocationRule {
    pub meta: Meta,
    pub kind: AllocationKind,
    pub value: i64,
    pub currency: Option<Currency>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Obligation {
    pub meta: Meta,
    pub name: String,
    pub amount: Money,
    pub due_day: u8,
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
