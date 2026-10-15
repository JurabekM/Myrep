//! Qarzlar va bergan qarzlar (SPEC 2D.5, DESKTOP_PROMPT D9).
//!
//! * To'lash rejasi majburiy: rejasiz qarz saqlanmaydi (`REPAYMENT_PLAN_REQUIRED`).
//! * Reja summasi qarzga teng bo'lishi shart (foizsiz qarz — «qarzi hasana» standart).
//! * Bergan qarz ([`Receivable`]) da foiz maydoni yo'q — tuzilmaning o'zi foizni taqiqlaydi.
//! * [`borrow_check`] — qarz oldidan oylik yukni daromadga nisbatan baholaydi. Chegaralar — mahsulot qarori
//!   (OPEN_QUESTIONS, «Hal qilingan»).

use money::{Money, round_half_up_div};
use time::Date;

use crate::{DomainError, Meta, validate_name, validate_uuid_v7};

/// To'lash rejasidagi bitta to'lov.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Installment {
    /// To'lov sanasi (Toshkent).
    pub due_on: Date,
    /// Summa (musbat).
    pub amount: Money,
}

/// To'lash rejasi: kamida bitta to'lov, sanalar o'sish tartibida, summa musbat.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct RepaymentPlan {
    installments: Vec<Installment>,
}

impl RepaymentPlan {
    /// Rejani tekshirib yaratadi. Bo'sh reja — `REPAYMENT_PLAN_REQUIRED`.
    pub fn new(installments: Vec<Installment>) -> Result<Self, DomainError> {
        if installments.is_empty() {
            return Err(DomainError::RepaymentPlanRequired);
        }
        let ordered = installments
            .windows(2)
            .all(|pair| pair[0].due_on < pair[1].due_on);
        if !ordered || installments.iter().any(|item| item.amount.minor() <= 0) {
            return Err(DomainError::InvalidRule);
        }
        Ok(Self { installments })
    }

    /// To'lovlar, sana bo'yicha.
    pub fn installments(&self) -> &[Installment] {
        &self.installments
    }

    /// Rejadagi jami summa.
    pub fn total(&self) -> Result<Money, DomainError> {
        let mut total = Money::zero(self.installments[0].amount.currency());
        for item in &self.installments {
            total = total.checked_add(item.amount)?;
        }
        Ok(total)
    }
}

/// Qarz (olingan). Foiz maydoni yo'q: foizli qarz bu yerda ifodalanmaydi.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Loan {
    /// UUIDv7.
    pub id: String,
    /// Xonadon (UUIDv7).
    pub household_id: String,
    /// Kimdan olingan (nomi).
    pub creditor: String,
    /// Asosiy summa (musbat).
    pub principal: Money,
    /// To'lash rejasi.
    pub plan: RepaymentPlan,
    /// Metama'lumot.
    pub meta: Meta,
}

impl Loan {
    /// Yangi qarz. Reja summasi asosiy qarzga teng bo'lishi shart.
    pub fn create(
        id: &str,
        household_id: &str,
        creditor: &str,
        principal: Money,
        plan: RepaymentPlan,
        now: time::OffsetDateTime,
        origin_device_id: &str,
    ) -> Result<Self, DomainError> {
        validate_uuid_v7(id)?;
        validate_uuid_v7(household_id)?;
        if principal.minor() <= 0 {
            return Err(DomainError::AmountNotPositive);
        }
        if plan.total()? != principal {
            return Err(DomainError::PlanMismatch);
        }
        Ok(Self {
            id: id.to_owned(),
            household_id: household_id.to_owned(),
            creditor: validate_name(creditor)?,
            principal,
            plan,
            meta: Meta::created(now, origin_device_id),
        })
    }
}

/// Bergan qarz. Foiz maydoni umuman yo'q — bu SPEC 2D.5 talabi (kompilyatsiya darajasida).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Receivable {
    /// UUIDv7.
    pub id: String,
    /// Xonadon (UUIDv7).
    pub household_id: String,
    /// Kimga berilgan (nomi).
    pub debtor: String,
    /// Asosiy summa (musbat).
    pub principal: Money,
    /// Qaytarish rejasi.
    pub plan: RepaymentPlan,
    /// Metama'lumot.
    pub meta: Meta,
}

impl Receivable {
    /// Yangi bergan qarz. Qoidalar [`Loan::create`] bilan bir xil.
    pub fn create(
        id: &str,
        household_id: &str,
        debtor: &str,
        principal: Money,
        plan: RepaymentPlan,
        now: time::OffsetDateTime,
        origin_device_id: &str,
    ) -> Result<Self, DomainError> {
        validate_uuid_v7(id)?;
        validate_uuid_v7(household_id)?;
        if principal.minor() <= 0 {
            return Err(DomainError::AmountNotPositive);
        }
        if plan.total()? != principal {
            return Err(DomainError::PlanMismatch);
        }
        Ok(Self {
            id: id.to_owned(),
            household_id: household_id.to_owned(),
            debtor: validate_name(debtor)?,
            principal,
            plan,
            meta: Meta::created(now, origin_device_id),
        })
    }
}

/// Qarz oldidan tekshiruv natijasi.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum BorrowVerdict {
    /// Oylik yuk me'yorida.
    Ok,
    /// Ogohlantirish: yuk daromadning katta qismi.
    Caution,
    /// To'xtash: yuk daromaddan ortiq darajada.
    Stop,
}

/// Oylik yuk ogohlantirish chegarasi: daromadning 30% (bp: 3 000).
pub const CAUTION_SHARE_BP: i128 = 3_000;
/// To'xtash chegarasi: daromadning 50% (bp: 5 000).
pub const STOP_SHARE_BP: i128 = 5_000;

/// Oylik yuk / oylik daromad. Daromad nolga teng yoki manfiy bo'lsa — `STOP`.
pub fn borrow_check(
    monthly_payment: Money,
    monthly_income: Money,
) -> Result<BorrowVerdict, DomainError> {
    if monthly_income.minor() <= 0 {
        return Ok(BorrowVerdict::Stop);
    }
    let share_bp = round_half_up_div(
        i128::from(monthly_payment.minor()) * 10_000,
        i128::from(monthly_income.minor()),
    )?;
    Ok(if share_bp >= STOP_SHARE_BP {
        BorrowVerdict::Stop
    } else if share_bp >= CAUTION_SHARE_BP {
        BorrowVerdict::Caution
    } else {
        BorrowVerdict::Ok
    })
}
