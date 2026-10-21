//! K8 — sotuvchi smenasi (kasbkor/SPEC 12, ADR-0003).
//!
//! ```text
//! Kutilgan = Ochilish + naqd tushum + naqd nasiya to'lovlari   (kunlik kassa yopish qoidasi)
//! Farq     = Sanalgan − Kutilgan
//! Qoldi    = Sanalgan − Egasiga topshirilgan                   (keyingi smena ochilishi)
//! ```
//! Sotuvchi qurilmasi faqat o'z yozuvlarini biladi; «egasi oldi», chiqim va boshqa harakatlar egasining
//! qurilmasida. Karta tushumlari kassaga ta'sir qilmaydi.
//!
//! Vektorlar: `spec/test-vectors/kk_shift_close.json`.
use baraka_money::Money;

use crate::cash::{cash_close, CashReason, CashStatus};
use crate::owner::{Move, MoveKind, Wallet};
use crate::DomainError;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum ShiftInKind {
    Sale,
    CreditPayment,
}

impl ShiftInKind {
    pub fn parse(s: &str) -> Option<Self> {
        match s {
            "SALE" => Some(Self::Sale),
            "CREDIT_PAYMENT" => Some(Self::CreditPayment),
            _ => None,
        }
    }
}

/// Smenadagi tushum: savdo yoki nasiya to'lovi.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct ShiftIn {
    pub kind: ShiftInKind,
    pub wallet: Wallet,
    pub amount: Money,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct ShiftClose {
    pub cash_sales: Money,
    pub credit_payments: Money,
    pub card_in: Money,
    pub expected: Money,
    pub difference: Money,
    pub status: CashStatus,
    pub reason: Option<CashReason>,
    pub suggest_search: bool,
    pub handed_over: Money,
    /// Kassada qolgani — keyingi smena ochilishi.
    pub left: Money,
}

/// `recent` — shu qurilmaning oxirgi 4 haftadagi smena farqlari.
pub fn shift_close(
    opening: Money,
    ins: &[ShiftIn],
    counted: Money,
    handed_over: Money,
    reason: Option<CashReason>,
    recent: &[Money],
) -> Result<ShiftClose, DomainError> {
    if handed_over.is_negative() {
        return Err(DomainError::on("AMOUNT_NEGATIVE", "handedOver"));
    }
    let zero = Money::zero(opening.currency());
    let [mut sales, mut payments, mut card] = [zero; 3];
    for i in ins {
        if i.amount.is_positive() {
            let slot = match (i.wallet, i.kind) {
                (Wallet::Card, _) => &mut card,
                (Wallet::Cash, ShiftInKind::Sale) => &mut sales,
                (Wallet::Cash, ShiftInKind::CreditPayment) => &mut payments,
            };
            *slot = slot.checked_add(i.amount)?;
        }
    }
    let moves: Vec<Move> = ins
        .iter()
        .map(|i| Move {
            kind: MoveKind::Sale,
            wallet: i.wallet,
            amount: i.amount,
        })
        .collect();
    let r = cash_close(opening, &moves, counted, reason, recent)?;
    let left = counted.checked_sub(handed_over)?;
    if left.is_negative() {
        return Err(DomainError::on("HANDOVER_ABOVE_COUNTED", "handedOver"));
    }
    Ok(ShiftClose {
        cash_sales: sales,
        credit_payments: payments,
        card_in: card,
        expected: r.expected,
        difference: r.difference,
        status: r.status,
        reason: r.reason,
        suggest_search: r.suggest_search,
        handed_over,
        left,
    })
}
