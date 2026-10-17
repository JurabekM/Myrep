//! K2 — buyurtma kalkulyatori (SPEC 3.2).
//!
//! Tannarx = material + mehnat (soat × soat bahosi) + yo'l + eskirish ulushi + zaxira (shu yig'indidan
//! foiz). Narx berilsa: marja, o'z mehnatingizga qoladigan pul (narx − mehnatsiz tannarx) va uning
//! soatbayi. Avans berilsa: materialga yetmagan va materialdan ortgan qism (Jasur ssenariysi).
//!
//! Vektorlar: `spec/test-vectors/kk_order_quote.json`.
use baraka_money::{percent_of, round_half_up, Money};

use crate::profit::hours_value;
use crate::DomainError;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct QuoteInput {
    pub material: Money,
    pub hours100: i64,
    pub hourly_rate: Money,
    pub travel: Money,
    pub depreciation: Money,
    pub reserve_bp: i64,
    pub price: Option<Money>,
    pub advance: Option<Money>,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct PriceCheck {
    pub margin: Money,
    /// O'z mehnatingizga qoladigan pul (manfiy bo'lishi mumkin).
    pub labor_paid: Money,
    pub below_cost: bool,
    /// Mehnat soati 0 bo'lsa — `None`.
    pub effective_hourly_rate: Option<Money>,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct AdvanceCheck {
    pub material_shortfall: Money,
    pub advance_after_material: Money,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct Quote {
    pub labor: Money,
    pub subtotal: Money,
    pub reserve: Money,
    pub cost: Money,
    pub price: Option<PriceCheck>,
    pub advance: Option<AdvanceCheck>,
}

pub fn order_quote(q: QuoteInput) -> Result<Quote, DomainError> {
    for (m, field) in [
        (q.material, "material"),
        (q.travel, "travel"),
        (q.depreciation, "depreciation"),
    ] {
        if m.is_negative() {
            return Err(DomainError::on("AMOUNT_NEGATIVE", field));
        }
    }
    let labor = hours_value(q.hours100, q.hourly_rate)?;
    let subtotal = q
        .material
        .checked_add(labor)?
        .checked_add(q.travel)?
        .checked_add(q.depreciation)?;
    let reserve = percent_of(subtotal, q.reserve_bp)?;
    let cost = subtotal.checked_add(reserve)?;
    let price = match q.price {
        None => None,
        Some(p) if p.is_negative() => return Err(DomainError::on("AMOUNT_NEGATIVE", "price")),
        Some(p) => {
            let labor_paid = p.checked_sub(cost.checked_sub(labor)?)?;
            let effective_hourly_rate = if q.hours100 == 0 {
                None
            } else {
                let v =
                    round_half_up(i128::from(labor_paid.minor()) * 100, i128::from(q.hours100))?;
                Some(Money::new(
                    i64::try_from(v).map_err(|_| DomainError::new("OVERFLOW"))?,
                    p.currency(),
                ))
            };
            Some(PriceCheck {
                margin: p.checked_sub(cost)?,
                labor_paid,
                below_cost: p.compare(&cost)?.is_lt(),
                effective_hourly_rate,
            })
        }
    };
    let advance = match q.advance {
        None => None,
        Some(a) if a.is_negative() => return Err(DomainError::on("AMOUNT_NEGATIVE", "advance")),
        Some(a) => Some(AdvanceCheck {
            material_shortfall: q.material.checked_sub(a)?.clamp_non_negative(),
            advance_after_material: a.checked_sub(q.material)?.clamp_non_negative(),
        }),
    };
    Ok(Quote {
        labor,
        subtotal,
        reserve,
        cost,
        price,
        advance,
    })
}
