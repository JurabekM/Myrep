//! Shaxsiy inflyatsiya indeksi («Narx daftari», SPEC 2C.2).
//!
//! Mahsulot o'zgarishi bazis punktlarda (1 bp = 0,01%, 100% = 10 000):
//! `bp = round_half_up((to − from) × 10 000 / from)`.
//! Indeks — bazaviy xarajat ulushlari (`weight_bp`) bo'yicha o'rtacha:
//! `round_half_up(Σ(w·bp) / Σ(w))`. Pul faqat minor birlikda hisoblanadi.

use money::{Money, round_half_up_div};
use time::OffsetDateTime;

use crate::{DomainError, Meta, validate_name, validate_uuid_v7};

/// «Narx daftari» yozuvi: bitta mahsulotning bazaviy va joriy narxi, bazaviy xarajatdagi ulushi.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PriceItem {
    /// UUIDv7.
    pub id: String,
    /// Xonadon (UUIDv7).
    pub household_id: String,
    /// Mahsulot nomi («go'sht, 1 kg»).
    pub name: String,
    /// Bazaviy narx (musbat).
    pub base_price: Money,
    /// Joriy narx (musbat).
    pub current_price: Money,
    /// Bazaviy xarajatdagi ulush, bp (0..=10 000).
    pub weight_bp: i64,
    /// Metama'lumot.
    pub meta: Meta,
}

/// Yangi narx yozuvi uchun kirish.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PriceDraft {
    /// Mahsulot nomi.
    pub name: String,
    /// Bazaviy narx (musbat).
    pub base_price: Money,
    /// Joriy narx (musbat, o'sha valyuta).
    pub current_price: Money,
    /// Bazaviy xarajatdagi ulush, bp (0..=10 000).
    pub weight_bp: i64,
}

impl PriceItem {
    /// Yangi yozuv. Narxlar musbat, bir valyutada; og'irlik 0..=10 000 bp.
    pub fn create(
        id: &str,
        household_id: &str,
        draft: PriceDraft,
        now: OffsetDateTime,
        origin_device_id: &str,
    ) -> Result<Self, DomainError> {
        validate_uuid_v7(id)?;
        validate_uuid_v7(household_id)?;
        if draft.base_price.minor() <= 0 || draft.current_price.minor() <= 0 {
            return Err(DomainError::AmountNotPositive);
        }
        if draft.base_price.currency() != draft.current_price.currency()
            || !(0..=FULL_BP as i64).contains(&draft.weight_bp)
        {
            return Err(DomainError::InvalidPrice);
        }
        Ok(Self {
            id: id.to_owned(),
            household_id: household_id.to_owned(),
            name: validate_name(&draft.name)?,
            base_price: draft.base_price,
            current_price: draft.current_price,
            weight_bp: draft.weight_bp,
            meta: Meta::created(now, origin_device_id),
        })
    }

    /// Joriy narxni yangilaydi (musbat, o'sha valyuta).
    pub fn with_current_price(
        mut self,
        current_price: Money,
        now: OffsetDateTime,
    ) -> Result<Self, DomainError> {
        if current_price.minor() <= 0 {
            return Err(DomainError::AmountNotPositive);
        }
        if current_price.currency() != self.base_price.currency() {
            return Err(DomainError::InvalidPrice);
        }
        self.current_price = current_price;
        self.meta.updated_at = now;
        self.meta.version += 1;
        Ok(self)
    }

    /// Indeks uchun o'zgarish kirishi.
    pub fn change(&self) -> PriceChange {
        PriceChange {
            name: self.name.clone(),
            from: self.base_price,
            to: self.current_price,
            weight_bp: self.weight_bp,
        }
    }
}

/// «Inflyatsiya ta'siri»: yotgan pulning bugungi narxlardagi real qiymati —
/// `balance × 10 000 / (10 000 + index_bp)`, yarim tiyin yuqoriga. Indeks −100% dan past bo'lmaydi.
pub fn real_value(balance: Money, index_bp: i64) -> Result<Money, DomainError> {
    let denominator = FULL_BP + i128::from(index_bp);
    if denominator <= 0 {
        return Err(DomainError::InvalidPrice);
    }
    let value = round_half_up_div(i128::from(balance.minor()) * FULL_BP, denominator)?;
    Ok(Money::new(
        i64::try_from(value).map_err(|_| DomainError::InvalidPrice)?,
        balance.currency(),
    ))
}

/// Shu pulga nechta birlik (masalan, kilo go'sht) olish mumkin: `balance / price` (pastga).
pub fn units_affordable(balance: Money, price: Money) -> Result<i64, DomainError> {
    if price.minor() <= 0 || price.currency() != balance.currency() {
        return Err(DomainError::InvalidPrice);
    }
    Ok((balance.minor().max(0)) / price.minor())
}

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

#[cfg(test)]
mod tests {
    use super::*;
    use money::Currency;

    fn uzs(minor: i64) -> Money {
        Money::new(minor, Currency::Uzs)
    }

    #[test]
    fn real_qiymat_indeks_bilan_kamayadi() {
        // 10% inflyatsiya: 110 000 → 100 000.
        assert_eq!(
            real_value(uzs(11_000_000), 1_000).expect("qiymat"),
            uzs(10_000_000)
        );
        assert_eq!(real_value(uzs(100), 0).expect("qiymat"), uzs(100));
        assert!(real_value(uzs(100), -10_000).is_err());
    }

    #[test]
    fn birliklar_pastga_yaxlitlanadi() {
        assert_eq!(
            units_affordable(uzs(100_000_000), uzs(13_000_000)).expect("birlik"),
            7
        );
        assert!(units_affordable(uzs(100), uzs(0)).is_err());
    }
}
