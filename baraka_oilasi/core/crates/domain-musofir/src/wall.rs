//! M5 — «qal'a devori» (musofir/SPEC 6.8): qaytgandan keyin olib kelingan puldan avval
//! oilaning olti oylik ro'zg'ori ajratiladi — u savdoga ham, sheriklikka ham qo'shilmaydi.
//!
//! ```text
//! Devor = round_half_up(Σ Uy makonining oylik xarajati × N / oylar soni)      (N = 6)
//! ```
//! Tarix (yozuvi bor to'liq oy) bo'lmasa — devor yo'q.
//!
//! Vektorlar: `spec/test-vectors/mf_wall.json`.
use baraka_money::{round_half_up, Money};

use crate::DomainError;

pub const WALL_MONTHS: i64 = 6;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct Wall {
    pub avg_monthly: Money,
    pub wall: Money,
}

fn ratio(num: i128, den: i128) -> Result<i64, DomainError> {
    let v = round_half_up(num, den)?;
    i64::try_from(v).map_err(|_| DomainError::new("OVERFLOW"))
}

/// `monthly` — oxirgi to'liq oylardagi Uy xarajatlari (uy valyutasida); bo'sh bo'lsa `None`.
pub fn fortress_wall(monthly: &[Money], months: i64) -> Result<Option<Wall>, DomainError> {
    if !(1..=12).contains(&months) {
        return Err(DomainError::on("INVALID_MONTHS", "months"));
    }
    if monthly.iter().any(Money::is_negative) {
        return Err(DomainError::new("AMOUNT_NEGATIVE"));
    }
    let Some(first) = monthly.first() else {
        return Ok(None);
    };
    let c = first.currency();
    let sum = i128::from(Money::sum(monthly.iter().copied(), c)?.minor());
    let n = i128::try_from(monthly.len()).map_err(|_| DomainError::new("OVERFLOW"))?;
    Ok(Some(Wall {
        avg_monthly: Money::new(ratio(sum, n)?, c),
        wall: Money::new(ratio(sum * i128::from(months), n)?, c),
    }))
}

#[cfg(test)]
mod tests {
    use super::*;
    use baraka_money::Currency;

    #[test]
    fn six_months_of_household() {
        let u = |m| Money::new(m, Currency::Uzs);
        let w = fortress_wall(
            &[u(800_000_000), u(780_000_000), u(820_000_000)],
            WALL_MONTHS,
        )
        .unwrap()
        .unwrap();
        assert_eq!(w.wall, u(4_800_000_000));
        assert!(fortress_wall(&[], WALL_MONTHS).unwrap().is_none());
    }
}
