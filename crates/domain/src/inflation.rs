//! Shaxsiy inflyatsiya indeksi («Narx daftari», SPEC 2C.2).
//!
//! Mahsulot o'zgarishi bazis punktlarda (1 bp = 0,01%, 100% = 10 000):
//! `bp = round_half_up((to − from) × 10 000 / from)`.
//! Indeks — bazaviy xarajat ulushlari (`weight_bp`) bo'yicha o'rtacha:
//! `round_half_up(Σ(w·bp) / Σ(w))`. Pul faqat minor birlikda hisoblanadi.

use money::{Money, round_half_up_div};

use crate::DomainError;

/// 100% bazis punktlarda.
pub const FULL_BP: i128 = 10_000;

/// Narx o'zgarishi: bazaviy va joriy narx, bazaviy xarajatdagi ulush (bp).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PriceChange {
    /// Mahsulot nomi (hisobga ta'sir qilmaydi).
    pub name: String,
    /// Bazaviy narx (musbat).
    pub from: Money,
    /// Joriy narx.
    pub to: Money,
    /// Bazaviy xarajatdagi ulush, bp (manfiy emas).
    pub weight_bp: i64,
}

/// Indeks natijasi.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PersonalIndex {
    /// Har bir mahsulotning o'zgarishi, bp.
    pub item_bps: Vec<i64>,
    /// Shaxsiy indeks, bp.
    pub index_bp: i64,
}

/// Bitta mahsulot o'zgarishi, bp. Bazaviy narx musbat va ikki narx bir valyutada bo'lishi shart.
pub fn change_bp(from: Money, to: Money) -> Result<i64, DomainError> {
    if from.minor() <= 0 || from.currency() != to.currency() {
        return Err(DomainError::InvalidPrice);
    }
    let diff = i128::from(to.minor()) - i128::from(from.minor());
    let bp = round_half_up_div(diff * FULL_BP, i128::from(from.minor()))?;
    Ok(i64::try_from(bp).unwrap_or(i64::MAX))
}

/// Shaxsiy indeks. Og'irliklar yig'indisi nolga teng bo'lsa — [`DomainError::InvalidPrice`].
pub fn personal_index(items: &[PriceChange]) -> Result<PersonalIndex, DomainError> {
    let mut item_bps = Vec::with_capacity(items.len());
    let mut weighted: i128 = 0;
    let mut weights: i128 = 0;
    for item in items {
        if item.weight_bp < 0 {
            return Err(DomainError::InvalidPrice);
        }
        let bp = change_bp(item.from, item.to)?;
        weighted += i128::from(bp) * i128::from(item.weight_bp);
        weights += i128::from(item.weight_bp);
        item_bps.push(bp);
    }
    if weights == 0 {
        return Err(DomainError::InvalidPrice);
    }
    let index = round_half_up_div(weighted, weights)?;
    Ok(PersonalIndex {
        item_bps,
        index_bp: i64::try_from(index).unwrap_or(i64::MAX),
    })
}
