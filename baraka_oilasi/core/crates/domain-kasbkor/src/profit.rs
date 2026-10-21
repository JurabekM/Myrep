//! K2 — «Haqiqiy foydani bil» (SPEC 3.1).
//!
//! ```text
//! Ko'rinadigan foyda = Tushum − Sotilgan tovar tannarxi − Tovar yo'qotishi − Operatsion xarajatlar
//! Haqiqiy foyda      = Ko'rinadigan − O'z mehnati − Oilaviy mehnat − Eskirish − Uskuna chiqib ketishi
//! ```
//! Oilaviy mehnat pul to'lanmasa ham tannarxga kiradi; to'langan bo'lsa — u operatsion xarajatda,
//! ikki marta hisoblanmaydi.
//!
//! Vektorlar: `spec/test-vectors/kk_true_profit.json`.
use baraka_money::{round_half_up, Currency, Money};

use crate::DomainError;

/// Soat × soat bahosi. `hours100` — soatning yuzdan bir ulushlarida (250 = 2,5 soat);
/// natija yarimni noldan uzoqqa yaxlitlanadi.
pub fn hours_value(hours100: i64, rate: Money) -> Result<Money, DomainError> {
    if hours100 < 0 {
        return Err(DomainError::on("INVALID_HOURS", "hours"));
    }
    if rate.is_negative() {
        return Err(DomainError::on("AMOUNT_NEGATIVE", "hourlyRate"));
    }
    let v = round_half_up(i128::from(hours100) * i128::from(rate.minor()), 100)?;
    let minor = i64::try_from(v).map_err(|_| DomainError::new("OVERFLOW"))?;
    Ok(Money::new(minor, rate.currency()))
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct FamilyLabor {
    pub hours100: i64,
    pub hourly_rate: Money,
    /// Pul to'langan (operatsion xarajatda bor).
    pub paid: bool,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct ProfitInput {
    pub revenue: Money,
    pub cogs: Money,
    pub operating_expenses: Money,
    pub owner_labor: Money,
    pub depreciation: Money,
    /// Uskuna chiqib ketishi (manfiy — foyda).
    pub disposal: Money,
    /// Hisobdan chiqarilgan tovar va inventarizatsiya farqi (K5; manfiy — topilgan tovar).
    pub stock_losses: Money,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct TrueProfit {
    pub visible_profit: Money,
    pub stock_losses: Money,
    pub owner_labor: Money,
    /// To'lanmagan oilaviy mehnat bahosi.
    pub family_labor: Money,
    /// To'langan (faqat ma'lumot uchun; hisobga qo'shilmaydi).
    pub family_labor_paid: Money,
    pub depreciation: Money,
    pub disposal: Money,
    pub true_profit: Money,
}

pub fn true_profit(
    currency: Currency,
    input: ProfitInput,
    family: &[FamilyLabor],
) -> Result<TrueProfit, DomainError> {
    let fields = [
        (input.revenue, "revenue"),
        (input.cogs, "cogs"),
        (input.operating_expenses, "operatingExpenses"),
        (input.owner_labor, "ownerLabor"),
        (input.depreciation, "depreciation"),
    ];
    for (m, field) in fields {
        if m.is_negative() {
            return Err(DomainError::on("AMOUNT_NEGATIVE", field));
        }
    }
    let zero = Money::zero(currency);
    let (mut unpaid, mut paid) = (zero, zero);
    for f in family {
        let v = hours_value(f.hours100, f.hourly_rate)?;
        if f.paid {
            paid = paid.checked_add(v)?;
        } else {
            unpaid = unpaid.checked_add(v)?;
        }
    }
    let visible = input
        .revenue
        .checked_sub(input.cogs)?
        .checked_sub(input.stock_losses)?
        .checked_sub(input.operating_expenses)?;
    let true_profit = visible
        .checked_sub(input.owner_labor)?
        .checked_sub(unpaid)?
        .checked_sub(input.depreciation)?
        .checked_sub(input.disposal)?;
    Ok(TrueProfit {
        visible_profit: visible,
        stock_losses: input.stock_losses,
        owner_labor: input.owner_labor,
        family_labor: unpaid,
        family_labor_paid: paid,
        depreciation: input.depreciation,
        disposal: input.disposal,
        true_profit,
    })
}
