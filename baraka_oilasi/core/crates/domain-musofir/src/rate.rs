//! M1 — foydalanuvchi kiritgan kurs (musofir/SPEC 4.1): `"9,1"` → `91/10`.
//! Ma'nosi `FxRate` bilan bir xil: 1 major ish valyutasi = `num / den` major uy valyutasi.
use crate::DomainError;

/// Kasr qismidagi raqamlar chegarasi.
pub const MAX_RATE_DECIMALS: u32 = 6;

/// `"9,1"`, `"9.1"`, `"12 650"`, `"0,0745"` → `(num, den)`; bo'sh, nol, manfiy yoki 6 tadan ortiq kasr — xato.
pub fn parse_rate(input: &str) -> Result<(i64, i64), DomainError> {
    let err = || DomainError::on("INVALID_RATE", "rate");
    let s: String = input
        .chars()
        .filter(|c| !c.is_whitespace() && *c != '\u{a0}')
        .map(|c| if c == ',' { '.' } else { c })
        .collect();
    let (int, frac) = match s.split_once('.') {
        Some((i, f)) => (i, f),
        None => (s.as_str(), ""),
    };
    if int.is_empty() && frac.is_empty()
        || !int.chars().all(|c| c.is_ascii_digit())
        || !frac.chars().all(|c| c.is_ascii_digit())
    {
        return Err(err());
    }
    let decimals = u32::try_from(frac.len()).map_err(|_| err())?;
    if decimals > MAX_RATE_DECIMALS {
        return Err(err());
    }
    let digits = format!("{int}{frac}");
    let num: i64 = digits.parse().map_err(|_| err())?;
    let den = 10_i64.pow(decimals);
    if num <= 0 {
        return Err(err());
    }
    // Ortiqcha nollarni qisqartirish: 9,10 → 91/10.
    let (mut n, mut d) = (num, den);
    while d > 1 && n % 10 == 0 {
        n /= 10;
        d /= 10;
    }
    Ok((n, d))
}

/// Kursni ko'rsatish uchun: `91/10` → `"9,1"`.
pub fn format_rate(num: i64, den: i64) -> String {
    let mut decimals = 0;
    let mut d = den;
    while d > 1 && d % 10 == 0 {
        d /= 10;
        decimals += 1;
    }
    if d != 1 || decimals == 0 {
        return if den == 1 {
            group(num)
        } else {
            format!("{}/{}", group(num), group(den))
        };
    }
    let p = 10_i64.pow(decimals);
    let frac = format!(
        "{:0w$}",
        num % p,
        w = usize::try_from(decimals).unwrap_or(0)
    );
    let frac = frac.trim_end_matches('0');
    if frac.is_empty() {
        group(num / p)
    } else {
        format!("{},{frac}", group(num / p))
    }
}

fn group(n: i64) -> String {
    let s = n.to_string();
    let mut out = String::new();
    for (i, c) in s.chars().enumerate() {
        if i > 0 && (s.len() - i).is_multiple_of(3) {
            out.push('\u{a0}');
        }
        out.push(c);
    }
    out
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parses_decimal_rates() {
        assert_eq!(parse_rate("9,1"), Ok((91, 10)));
        assert_eq!(parse_rate("9.10"), Ok((91, 10)));
        assert_eq!(parse_rate("12 650"), Ok((12_650, 1)));
        assert_eq!(parse_rate("0,0745"), Ok((745, 10_000)));
        for bad in ["", "0", "-1", "1,2345678", "abc", ",", "1,2,3"] {
            assert_eq!(parse_rate(bad).unwrap_err().code, "INVALID_RATE", "{bad}");
        }
    }

    #[test]
    fn formats_rates() {
        assert_eq!(format_rate(91, 10), "9,1");
        assert_eq!(format_rate(12_650, 1), "12\u{a0}650");
        assert_eq!(format_rate(745, 10_000), "0,0745");
        assert_eq!(format_rate(1, 3), "1/3");
    }
}
