//! Matnli kiritishni tekshirish (Tauri'siz).

use services::ServiceError;

/// «12,5» → 1250 bp. Faqat butun va bir-ikki xonali kasr; manfiy yoki 1000% dan katta emas.
pub fn percent_to_bp(text: &str) -> Result<u32, ServiceError> {
    let t = text.trim().replace(',', ".");
    let bad = ServiceError::Invalid("foiz noto'g'ri (masalan, 12,5)");
    let (int, frac) = t.split_once('.').unwrap_or((&t, ""));
    if int.is_empty() || frac.len() > 2 || !int.bytes().all(|b| b.is_ascii_digit()) {
        return Err(bad);
    }
    if !frac.bytes().all(|b| b.is_ascii_digit()) {
        return Err(bad);
    }
    let int: u32 = int
        .parse()
        .map_err(|_| ServiceError::Invalid("foiz noto'g'ri"))?;
    let frac_bp = match frac.len() {
        0 => 0,
        1 => {
            frac.parse::<u32>()
                .map_err(|_| ServiceError::Invalid("foiz noto'g'ri"))?
                * 10
        }
        _ => frac
            .parse::<u32>()
            .map_err(|_| ServiceError::Invalid("foiz noto'g'ri"))?,
    };
    let bp = int
        .checked_mul(100)
        .and_then(|v| v.checked_add(frac_bp))
        .ok_or(ServiceError::Invalid("foiz juda katta"))?;
    if bp > 100_000 {
        return Err(ServiceError::Invalid("foiz juda katta"));
    }
    Ok(bp)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parses_percent_to_basis_points() {
        assert_eq!(percent_to_bp("12,5").unwrap(), 1250);
        assert_eq!(percent_to_bp(" 7.25 ").unwrap(), 725);
        assert_eq!(percent_to_bp("15").unwrap(), 1500);
        assert_eq!(percent_to_bp("0").unwrap(), 0);
        for bad in ["", "-1", "1.234", "abc", "1e2", ".5", "1000.01", "5%"] {
            assert!(percent_to_bp(bad).is_err(), "{bad}");
        }
    }
}
