//! K5 — «Tovar ham pul — u ham yotadi» (SPEC 4.1–4.4): tovar qoldig'i, tannarx, qayta tiklash narxi.
//!
//! - Miqdorlar butun sonda, asosiy birlikda (g, ml, dona, mm). Narxlar `factor` birlikka: 1000 (kg, l,
//!   m) yoki 1 (dona).
//! - Driftsiz tannarx: o'rtachada `round_half_up(qoldiq qiymati × chiqim / qoldiq miqdor)`, qiymat
//!   shunga kamayadi — oxirgi birlik chiqqanda qiymat aniq 0. FIFO — eng eski partiyadan, qisman partiya
//!   shu formula bilan.
//! - Chiqim: sotuv, hisobdan chiqarish, inventarizatsiyadagi kamomad. Ortiqcha — berilgan qiymat bilan
//!   yangi partiya (tannarxi manfiy, ya'ni foyda).
//!
//! Vektorlar: `spec/test-vectors/kk_cogs.json`, `kk_replacement.json`.
use baraka_money::{round_half_up, Currency, Money};
use chrono::NaiveDate;

use crate::DomainError;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum CostMethod {
    Average,
    Fifo,
}

impl CostMethod {
    pub fn parse(s: &str) -> Option<Self> {
        match s {
            "AVERAGE" => Some(Self::Average),
            "FIFO" => Some(Self::Fifo),
            _ => None,
        }
    }

    pub fn as_str(self) -> &'static str {
        match self {
            Self::Average => "AVERAGE",
            Self::Fifo => "FIFO",
        }
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum StockMove {
    /// Xarid: miqdor va jami narx.
    Purchase {
        qty: i64,
        amount: Money,
    },
    Sale {
        qty: i64,
    },
    WriteOff {
        qty: i64,
    },
    /// Inventarizatsiya: kamomad (`qty < 0`) yoki ortiqcha (`qty > 0`, `amount` — topilgan tovar qiymati).
    Adjust {
        qty: i64,
        amount: Money,
    },
}

/// Ko'rsatish birligi: 1000 (kg, l, m) yoki 1 (dona).
pub fn validate_factor(factor: i64) -> Result<(), DomainError> {
    if factor == 1 || factor == 1000 {
        Ok(())
    } else {
        Err(DomainError::on("INVALID_UNIT", "unit"))
    }
}

fn ratio(value: Money, num: i64, den: i64) -> Result<Money, DomainError> {
    let v = round_half_up(i128::from(value.minor()) * i128::from(num), i128::from(den))?;
    Ok(Money::new(
        i64::try_from(v).map_err(|_| DomainError::new("OVERFLOW"))?,
        value.currency(),
    ))
}

/// Tovar qoldig'i (har harakatdan keyin yangilanadi).
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Stock {
    pub method: CostMethod,
    pub qty: i64,
    pub value: Money,
    /// FIFO partiyalari (eskisi birinchi): `(miqdor, qiymat)`.
    pub layers: Vec<(i64, Money)>,
}

impl Stock {
    pub fn new(method: CostMethod, currency: Currency) -> Self {
        Self {
            method,
            qty: 0,
            value: Money::zero(currency),
            layers: Vec::new(),
        }
    }

    fn take(&mut self, qty: i64) -> Result<Money, DomainError> {
        if qty > self.qty {
            return Err(DomainError::on("INSUFFICIENT_STOCK", "qty"));
        }
        let cost = match self.method {
            CostMethod::Average => ratio(self.value, qty, self.qty)?,
            CostMethod::Fifo => {
                let mut cost = Money::zero(self.value.currency());
                let mut left = qty;
                while left > 0 {
                    let Some(layer) = self.layers.first_mut() else {
                        return Err(DomainError::on("INSUFFICIENT_STOCK", "qty"));
                    };
                    let t = left.min(layer.0);
                    let part = if t == layer.0 {
                        layer.1
                    } else {
                        ratio(layer.1, t, layer.0)?
                    };
                    layer.0 -= t;
                    layer.1 = layer.1.checked_sub(part)?;
                    if layer.0 == 0 {
                        self.layers.remove(0);
                    }
                    cost = cost.checked_add(part)?;
                    left -= t;
                }
                cost
            }
        };
        self.qty -= qty;
        self.value = self.value.checked_sub(cost)?;
        Ok(cost)
    }

    fn add(&mut self, qty: i64, amount: Money) -> Result<(), DomainError> {
        self.qty = self
            .qty
            .checked_add(qty)
            .ok_or(DomainError::new("OVERFLOW"))?;
        self.value = self.value.checked_add(amount)?;
        self.layers.push((qty, amount));
        Ok(())
    }

    /// Harakatni qo'llaydi; qaytaradi — tannarx (xaridda — narx, ortiqchada — manfiy qiymat).
    pub fn apply(&mut self, m: StockMove) -> Result<Money, DomainError> {
        match m {
            StockMove::Purchase { qty, amount } => {
                if qty <= 0 {
                    return Err(DomainError::on("INVALID_QTY", "qty"));
                }
                if !amount.is_positive() {
                    return Err(DomainError::on("AMOUNT_NOT_POSITIVE", "amount"));
                }
                self.add(qty, amount)?;
                Ok(amount)
            }
            StockMove::Sale { qty } | StockMove::WriteOff { qty } => {
                if qty <= 0 {
                    return Err(DomainError::on("INVALID_QTY", "qty"));
                }
                self.take(qty)
            }
            StockMove::Adjust { qty, amount } => {
                if qty == 0 {
                    return Err(DomainError::on("INVALID_QTY", "qty"));
                }
                if qty < 0 {
                    return self.take(qty.checked_neg().ok_or(DomainError::new("OVERFLOW"))?);
                }
                if amount.is_negative() {
                    return Err(DomainError::on("AMOUNT_NEGATIVE", "amount"));
                }
                self.add(qty, amount)?;
                Ok(amount.checked_neg()?)
            }
        }
    }

    /// Bir birlik (`factor`) tannarxi; qoldiq yo'q bo'lsa — `None`.
    pub fn unit_cost(&self, factor: i64) -> Result<Option<Money>, DomainError> {
        validate_factor(factor)?;
        if self.qty == 0 {
            return Ok(None);
        }
        Ok(Some(ratio(self.value, factor, self.qty)?))
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct Replacement {
    pub replacement_value: Money,
    /// Qayta tiklash − hisobdagi qiymat: «inflyatsiya yegan kapital» (manfiy — narx tushgan).
    pub inflation_gap: Money,
    pub sale_below_replacement: bool,
}

/// Qayta tiklash narxi (SPEC 4.3). `price` va `sale_price` — `factor` birlikka.
pub fn replacement(
    qty: i64,
    book_value: Money,
    price: Money,
    factor: i64,
    sale_price: Option<Money>,
) -> Result<Replacement, DomainError> {
    if qty < 0 {
        return Err(DomainError::on("INVALID_QTY", "qty"));
    }
    validate_factor(factor)?;
    if !price.is_positive() {
        return Err(DomainError::on("AMOUNT_NOT_POSITIVE", "price"));
    }
    if book_value.is_negative() || sale_price.is_some_and(|p| !p.is_positive()) {
        return Err(DomainError::on("AMOUNT_NEGATIVE", "salePrice"));
    }
    let replacement_value = ratio(price, qty, factor)?;
    Ok(Replacement {
        replacement_value,
        inflation_gap: replacement_value.checked_sub(book_value)?,
        sale_below_replacement: match sale_price {
            Some(p) => p.compare(&price)?.is_lt(),
            None => false,
        },
    })
}

/// Muzlagan tovar (SPEC 4.4): qoldiq bor va oxirgi sotuvdan (sotilmagan bo'lsa — birinchi xariddan)
/// beri `days` kundan ko'p o'tgan.
pub fn is_frozen(
    qty: i64,
    last_sale: Option<NaiveDate>,
    first_purchase: Option<NaiveDate>,
    today: NaiveDate,
    days: i64,
) -> bool {
    match (qty > 0, last_sale.or(first_purchase)) {
        (true, Some(since)) => (today - since).num_days() > days,
        _ => false,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn d(s: &str) -> NaiveDate {
        NaiveDate::parse_from_str(s, "%Y-%m-%d").unwrap()
    }

    #[test]
    fn frozen_after_threshold_only_with_stock() {
        assert!(!is_frozen(
            10,
            Some(d("2026-07-01")),
            None,
            d("2026-09-29"),
            90
        ));
        assert!(is_frozen(
            10,
            Some(d("2026-07-01")),
            None,
            d("2026-09-30"),
            90
        ));
        assert!(is_frozen(
            10,
            None,
            Some(d("2026-01-01")),
            d("2026-06-01"),
            90
        ));
        assert!(!is_frozen(
            0,
            Some(d("2026-01-01")),
            None,
            d("2026-12-01"),
            90
        ));
    }
}
