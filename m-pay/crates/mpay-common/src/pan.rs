//! PAN (karta raqami), Luhn va maskalash.
//!
//! Qat'iy qoida: faqat M-Pay test BIN diapazoni (`990000`–`990099`) qabul qilinadi.
//! `Pan` tipi `Debug`/`Display` da **faqat maskalangan** ko'rinishni beradi, raqamlar
//! xotiradan `Drop` da tozalanadi. To'liq raqamlarga faqat [`Pan::expose_digits`] orqali,
//! ataylab, kirish mumkin.

use core::fmt;

use subtle::ConstantTimeEq;
use thiserror::Error;
use zeroize::Zeroizing;

/// Test FPAN (emitent kartalari) BIN diapazoni: `990000`–`990049`.
pub const FPAN_BIN_RANGE: core::ops::RangeInclusive<u32> = 990_000..=990_049;
/// Test DPAN (token PAN) BIN diapazoni: `990050`–`990099`.
pub const DPAN_BIN_RANGE: core::ops::RangeInclusive<u32> = 990_050..=990_099;

/// PAN uzunligi (M-Pay Test Scheme'da yagona qiymat).
pub const PAN_LEN: usize = 16;

/// PAN xatolari. Xato matnida PAN raqamlari hech qachon bo'lmaydi.
#[derive(Debug, Error, Clone, PartialEq, Eq)]
pub enum PanError {
    #[error("PAN faqat raqamlardan iborat bo'lishi kerak")]
    NotNumeric,
    #[error("PAN uzunligi {0}, kutilgan {PAN_LEN}")]
    BadLength(usize),
    #[error("Luhn nazorat raqami noto'g'ri")]
    LuhnMismatch,
    #[error("BIN M-Pay test diapazonida emas (990000–990099)")]
    NotTestBin,
    #[error("BIN kutilgan diapazonda emas ({expected:?})")]
    WrongKind { expected: PanKind },
}

/// PAN turi BIN bo'yicha.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum PanKind {
    /// Emitent kartasi (Funding PAN).
    Funding,
    /// Token PAN (Device PAN).
    Device,
}

/// Luhn nazorat raqamini hisoblaydi (`payload` — nazorat raqamisiz raqamlar).
///
/// `payload` faqat ASCII raqamlardan iborat bo'lishi shart; aks holda `None`.
pub fn luhn_check_digit(payload: &str) -> Option<u8> {
    let mut sum = 0u32;
    // O'ngdan boshlab: nazorat raqami qo'shilganda u 1-o'rin bo'ladi, shuning uchun
    // payload'ning eng o'ng raqami ikkilantiriladi.
    for (i, b) in payload.bytes().rev().enumerate() {
        if !b.is_ascii_digit() {
            return None;
        }
        let mut d = u32::from(b - b'0');
        if i % 2 == 0 {
            d *= 2;
            if d > 9 {
                d -= 9;
            }
        }
        sum += d;
    }
    Some(((10 - (sum % 10)) % 10) as u8)
}

/// To'liq raqam qatori Luhn bo'yicha to'g'rimi.
pub fn luhn_valid(digits: &str) -> bool {
    if digits.len() < 2 {
        return false;
    }
    let (payload, check) = digits.split_at(digits.len() - 1);
    match (luhn_check_digit(payload), check.as_bytes()[0]) {
        (Some(c), b) if b.is_ascii_digit() => c == b - b'0',
        _ => false,
    }
}

/// Test PAN. Klonlash mumkin, lekin har nusxa `Drop` da tozalanadi.
#[derive(Clone)]
pub struct Pan {
    digits: Zeroizing<String>,
    kind: PanKind,
}

impl Pan {
    /// Satrdan PAN: raqamlar, uzunlik, Luhn va test BIN tekshiriladi.
    pub fn parse(s: &str) -> Result<Self, PanError> {
        if !s.bytes().all(|b| b.is_ascii_digit()) {
            return Err(PanError::NotNumeric);
        }
        if s.len() != PAN_LEN {
            return Err(PanError::BadLength(s.len()));
        }
        if !luhn_valid(s) {
            return Err(PanError::LuhnMismatch);
        }
        let bin: u32 = s[..6].parse().map_err(|_| PanError::NotNumeric)?;
        let kind = if FPAN_BIN_RANGE.contains(&bin) {
            PanKind::Funding
        } else if DPAN_BIN_RANGE.contains(&bin) {
            PanKind::Device
        } else {
            return Err(PanError::NotTestBin);
        };
        Ok(Self {
            digits: Zeroizing::new(s.to_owned()),
            kind,
        })
    }

    /// PAN'ni o'qiydi va turini tekshiradi.
    pub fn parse_kind(s: &str, expected: PanKind) -> Result<Self, PanError> {
        let pan = Self::parse(s)?;
        if pan.kind != expected {
            return Err(PanError::WrongKind { expected });
        }
        Ok(pan)
    }

    /// 15 raqamli prefiksga Luhn nazorat raqamini qo'shib PAN yasaydi.
    pub fn from_prefix(prefix15: &str) -> Result<Self, PanError> {
        if prefix15.len() != PAN_LEN - 1 {
            return Err(PanError::BadLength(prefix15.len() + 1));
        }
        let c = luhn_check_digit(prefix15).ok_or(PanError::NotNumeric)?;
        let mut s = Zeroizing::new(String::with_capacity(PAN_LEN));
        s.push_str(prefix15);
        s.push(char::from(b'0' + c));
        Self::parse(&s)
    }

    /// To'liq raqamlar. **Faqat** kriptografik hisoblash, shifrlash yoki ISO 8583 maydoniga
    /// yozish uchun; logga yoki xato matniga uzatish taqiqlangan.
    pub fn expose_digits(&self) -> &str {
        &self.digits
    }

    /// PAN turi.
    pub fn kind(&self) -> PanKind {
        self.kind
    }

    /// BIN (birinchi 6 raqam) — maxfiy emas.
    pub fn bin(&self) -> &str {
        &self.digits[..6]
    }

    /// Oxirgi 4 raqam — maxfiy emas.
    pub fn last4(&self) -> &str {
        &self.digits[self.digits.len() - 4..]
    }

    /// Maskalangan ko'rinish: `990012******3456`.
    pub fn masked(&self) -> String {
        let stars = "*".repeat(self.digits.len() - 10);
        format!("{}{}{}", self.bin(), stars, self.last4())
    }
}

impl PartialEq for Pan {
    fn eq(&self, other: &Self) -> bool {
        self.digits.as_bytes().ct_eq(other.digits.as_bytes()).into()
    }
}
impl Eq for Pan {}

impl fmt::Debug for Pan {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "Pan({})", self.masked())
    }
}

impl fmt::Display for Pan {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(&self.masked())
    }
}

/// M-Pay Test Scheme profili: karta va token muddati O'zbekiston vaqti bilan (UTC+5, yozgi vaqt
/// yo'q) — `12/29` mahalliy 2030-01-01 00:00 gacha (2029-12-31 19:00 UTC) amal qiladi. Server va
/// emitent qayerda ishlamasin, natija bir xil. `TODO(spec):` haqiqiy sxema qoidasi.
pub const EXPIRY_UTC_OFFSET_SECS: i32 = 5 * 3600;

/// [`EXPIRY_UTC_OFFSET_SECS`] — `time::UtcOffset` sifatida.
pub fn expiry_offset() -> time::UtcOffset {
    time::UtcOffset::from_whole_seconds(EXPIRY_UTC_OFFSET_SECS).unwrap_or(time::UtcOffset::UTC)
}

/// Karta amal qilish muddati (YYMM).
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub struct CardExpiry {
    /// To'liq yil, masalan 2029.
    pub year: u16,
    /// Oy, 1..=12.
    pub month: u8,
}

impl CardExpiry {
    /// `YYMM` satridan (masalan `"2912"`). Yillar 2000–2099 deb talqin qilinadi.
    pub fn parse_yymm(s: &str) -> Option<Self> {
        if s.len() != 4 || !s.bytes().all(|b| b.is_ascii_digit()) {
            return None;
        }
        let yy: u16 = s[..2].parse().ok()?;
        let mm: u8 = s[2..].parse().ok()?;
        Self::new(2000 + yy, mm)
    }

    /// Yil va oydan (yil 2000–2099, oy 1–12).
    pub fn new(year: u16, month: u8) -> Option<Self> {
        if !(2000..=2099).contains(&year) || !(1..=12).contains(&month) {
            return None;
        }
        Some(Self { year, month })
    }

    /// `YYMM` ko'rinishi.
    pub fn to_yymm(&self) -> String {
        format!("{:02}{:02}", self.year % 100, self.month)
    }

    /// Oyning oxirgi kuni (EMV tag `5F24` uchun YYMMDD).
    pub fn last_day(&self) -> u8 {
        match self.month {
            1 | 3 | 5 | 7 | 8 | 10 | 12 => 31,
            4 | 6 | 9 | 11 => 30,
            _ => {
                let y = self.year;
                if (y.is_multiple_of(4) && !y.is_multiple_of(100)) || y.is_multiple_of(400) {
                    29
                } else {
                    28
                }
            }
        }
    }

    /// Muddat tugaydigan lahza (unix): keyingi oyning 1-kuni 00:00 sxema vaqti bilan
    /// ([`EXPIRY_UTC_OFFSET_SECS`]).
    pub fn end_unix(&self) -> i64 {
        let (y, m) = if self.month == 12 {
            (i64::from(self.year) + 1, 1)
        } else {
            (i64::from(self.year), i64::from(self.month) + 1)
        };
        // Kunlar soni (fuqarolik kalendari, Howard Hinnant algoritmi), 1970-01-01 dan.
        let (yy, mm) = if m <= 2 { (y - 1, m + 9) } else { (y, m - 3) };
        let era = yy.div_euclid(400);
        let yoe = yy - era * 400;
        let doy = (153 * mm + 2) / 5;
        let doe = yoe * 365 + yoe / 4 - yoe / 100 + doy;
        (era * 146_097 + doe - 719_468) * 86_400 - i64::from(EXPIRY_UTC_OFFSET_SECS)
    }

    /// `now` paytida muddat o'tganmi (sxema vaqti bilan; oxirgi oy ichida hali amal qiladi).
    pub fn is_expired(&self, now: time::OffsetDateTime) -> bool {
        now.unix_timestamp() >= self.end_unix()
    }

    /// Sxema vaqti bo'yicha joriy oy (`now` dagi YYMM).
    pub fn current(now: time::OffsetDateTime) -> Self {
        let l = now.to_offset(expiry_offset());
        Self {
            year: l.year().clamp(2000, 2099) as u16,
            month: l.month() as u8,
        }
    }

    /// Berilgan sanada (yil, oy) muddat o'tganmi. Karta muddatining oxirgi oyi ichida haliyam amal qiladi.
    pub fn is_expired_at(&self, year: u16, month: u8) -> bool {
        (year, month) > (self.year, self.month)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use proptest::prelude::*;

    #[test]
    fn expiry_end_unix() {
        // Mahalliy (UTC+5) yarim tun: 2029-10 → 2029-11-01T00:00+05 = 2029-10-31T19:00Z;
        // 2029-12 → 2030-01-01; kabisa fevrali → 2028-03-01.
        const H5: i64 = 5 * 3600;
        assert_eq!(
            CardExpiry::new(2029, 10).unwrap().end_unix(),
            1_888_185_600 - H5
        );
        assert_eq!(
            CardExpiry::new(2029, 12).unwrap().end_unix(),
            1_893_456_000 - H5
        );
        assert_eq!(
            CardExpiry::new(2028, 2).unwrap().end_unix(),
            1_835_481_600 - H5
        );
        assert_eq!(
            CardExpiry::new(2000, 1).unwrap().end_unix(),
            949_363_200 - H5
        );
    }

    #[test]
    fn expiry_in_uzbekistan_time() {
        use time::macros::datetime;
        let e = CardExpiry::new(2029, 10).unwrap();
        // 31-oktabr 18:59:59 UTC = 23:59:59 Toshkent — hali amal qiladi; 19:00 UTC — tugadi.
        assert!(!e.is_expired(datetime!(2029-10-31 18:59:59 UTC)));
        assert!(e.is_expired(datetime!(2029-10-31 19:00 UTC)));
        // UTC bo'yicha hali oktabr, Toshkentda esa noyabr.
        assert_eq!(
            CardExpiry::current(datetime!(2029-10-31 20:00 UTC)),
            CardExpiry::new(2029, 11).unwrap()
        );
        assert_eq!(
            CardExpiry::current(datetime!(2029-10-31 18:00 UTC)),
            CardExpiry::new(2029, 10).unwrap()
        );
        // Mahalliy ko'rinish ham bir xil.
        assert!(e.is_expired(datetime!(2029-11-01 00:00 +5)));
        assert!(!e.is_expired(datetime!(2029-10-31 23:59:59 +5)));
    }

    #[test]
    fn luhn_known_values() {
        // Klassik misol: 7992739871 → nazorat raqami 3.
        assert_eq!(luhn_check_digit("7992739871"), Some(3));
        assert!(luhn_valid("79927398713"));
        assert!(!luhn_valid("79927398710"));
        assert_eq!(luhn_check_digit("12a"), None);
    }

    #[test]
    fn parse_accepts_test_bins_only() {
        let fpan = Pan::from_prefix("990012000000345").unwrap();
        assert_eq!(fpan.kind(), PanKind::Funding);
        let dpan = Pan::from_prefix("990077000000123").unwrap();
        assert_eq!(dpan.kind(), PanKind::Device);

        // Real BIN'lar rad etiladi (Luhn to'g'ri bo'lsa ham).
        for prefix in ["986000000000000", "860000000000000", "411111111111111"] {
            let c = luhn_check_digit(prefix).unwrap();
            let s = format!("{prefix}{c}");
            assert_eq!(Pan::parse(&s), Err(PanError::NotTestBin), "{prefix}");
        }
        assert_eq!(Pan::parse("99001200000034"), Err(PanError::BadLength(14)));
        assert_eq!(Pan::parse("99001200000034x5"), Err(PanError::NotNumeric));
    }

    #[test]
    fn luhn_mismatch_rejected() {
        let pan = Pan::from_prefix("990012000000345").unwrap();
        let mut s = pan.expose_digits().to_owned();
        let last = s.pop().unwrap();
        s.push(if last == '0' { '1' } else { '0' });
        assert_eq!(Pan::parse(&s), Err(PanError::LuhnMismatch));
    }

    #[test]
    fn masking_never_leaks_middle_digits() {
        let pan = Pan::from_prefix("990012987654345").unwrap();
        let masked = pan.masked();
        assert_eq!(masked.len(), 16);
        assert!(masked.starts_with("990012******"));
        assert_eq!(format!("{pan}"), masked);
        assert_eq!(format!("{pan:?}"), format!("Pan({masked})"));
        assert!(!format!("{pan:?}").contains("987654"));
    }

    #[test]
    fn kind_enforced() {
        let s = Pan::from_prefix("990077000000123").unwrap();
        assert!(Pan::parse_kind(s.expose_digits(), PanKind::Device).is_ok());
        assert_eq!(
            Pan::parse_kind(s.expose_digits(), PanKind::Funding),
            Err(PanError::WrongKind {
                expected: PanKind::Funding
            })
        );
    }

    #[test]
    fn expiry() {
        let e = CardExpiry::parse_yymm("2902").unwrap();
        assert_eq!(e, CardExpiry::new(2029, 2).unwrap());
        assert_eq!(e.to_yymm(), "2902");
        assert_eq!(e.last_day(), 28);
        assert_eq!(CardExpiry::new(2028, 2).unwrap().last_day(), 29);
        assert!(!e.is_expired_at(2029, 2));
        assert!(e.is_expired_at(2029, 3));
        assert!(CardExpiry::parse_yymm("2913").is_none());
        assert!(CardExpiry::parse_yymm("29a1").is_none());
    }

    proptest! {
        #[test]
        fn generated_pans_always_valid(bin in 990_000u32..=990_099, acct in 0u64..1_000_000_000) {
            let prefix = format!("{bin}{acct:09}");
            let pan = Pan::from_prefix(&prefix).unwrap();
            prop_assert!(luhn_valid(pan.expose_digits()));
            prop_assert_eq!(Pan::parse(pan.expose_digits()).unwrap(), pan.clone());
            let masked = pan.masked();
            prop_assert_eq!(&masked[6..12], "******");
            prop_assert_eq!(&masked[12..], pan.last4());
        }

        #[test]
        fn single_digit_error_detected(bin in 990_000u32..=990_099, acct in 0u64..1_000_000_000,
                                       pos in 0usize..16, delta in 1u8..10) {
            let pan = Pan::from_prefix(&format!("{bin}{acct:09}")).unwrap();
            let mut bytes = pan.expose_digits().as_bytes().to_vec();
            bytes[pos] = b'0' + (bytes[pos] - b'0' + delta) % 10;
            let s = String::from_utf8(bytes).unwrap();
            prop_assert!(!luhn_valid(&s));
        }
    }
}
