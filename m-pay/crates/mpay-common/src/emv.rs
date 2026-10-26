//! M-Pay Test Scheme profili: teglar, PDOL/CDOL, IAD, Track 2, BCD yordamchilari.
//!
//! Manba: `docs/specs/emv-profile.md`. Bu modul faqat ma'lumot tuzilmalari — kriptografiya
//! `mpay-crypto::scheme` da.

use thiserror::Error;

use crate::pan::{CardExpiry, Pan, PanError};
use crate::tlv::{DolEntry, Tag};

/// PPSE nomi `2PAY.SYS.DDF01`.
pub const PPSE_NAME: &[u8] = b"2PAY.SYS.DDF01";
/// M-Pay Test Scheme AID.
pub const AID: [u8; 6] = [0xF0, 0x4D, 0x50, 0x41, 0x59, 0x01];
/// Ilova yorlig'i.
pub const APP_LABEL: &[u8] = b"M-PAY TEST";
/// AIP: bayt 2 bit 8 = "EMV rejimi".
pub const AIP: [u8; 2] = [0x00, 0x80];
/// CID: ARQC.
pub const CID_ARQC: u8 = 0x80;
/// O'zbekiston mamlakat kodi / UZS valyuta kodi (ISO raqamli).
pub const UZ_NUMERIC: u16 = 860;
/// Track 2 servis kodi.
pub const SERVICE_CODE: &str = "201";

/// EMV teglari.
pub mod tag {
    pub const FCI_TEMPLATE: u32 = 0x6F;
    pub const DF_NAME: u32 = 0x84;
    pub const FCI_PROPRIETARY: u32 = 0xA5;
    pub const FCI_ISSUER_DISCRETIONARY: u32 = 0xBF0C;
    pub const APPLICATION_TEMPLATE: u32 = 0x61;
    pub const AID: u32 = 0x4F;
    pub const APP_LABEL: u32 = 0x50;
    pub const APP_PRIORITY: u32 = 0x87;
    pub const PDOL: u32 = 0x9F38;
    pub const COMMAND_TEMPLATE: u32 = 0x83;
    pub const RESPONSE_TEMPLATE_2: u32 = 0x77;
    pub const AIP: u32 = 0x82;
    pub const TRACK2: u32 = 0x57;
    pub const PSN: u32 = 0x5F34;
    pub const APP_EXPIRY: u32 = 0x5F24;
    pub const ATC: u32 = 0x9F36;
    pub const ARQC: u32 = 0x9F26;
    pub const CID: u32 = 0x9F27;
    pub const IAD: u32 = 0x9F10;
    pub const AMOUNT: u32 = 0x9F02;
    pub const AMOUNT_OTHER: u32 = 0x9F03;
    pub const TERMINAL_COUNTRY: u32 = 0x9F1A;
    pub const TVR: u32 = 0x95;
    pub const CURRENCY: u32 = 0x5F2A;
    pub const TXN_DATE: u32 = 0x9A;
    pub const TXN_TYPE: u32 = 0x9C;
    pub const UN: u32 = 0x9F37;
    pub const ISSUER_AUTH_DATA: u32 = 0x91;
    pub const ARC: u32 = 0x8A;
}

/// M-Pay Test Scheme PDOL (29 bayt ma'lumot).
pub const PDOL: [DolEntry; 8] = [
    DolEntry {
        tag: Tag(tag::AMOUNT),
        len: 6,
    },
    DolEntry {
        tag: Tag(tag::AMOUNT_OTHER),
        len: 6,
    },
    DolEntry {
        tag: Tag(tag::TERMINAL_COUNTRY),
        len: 2,
    },
    DolEntry {
        tag: Tag(tag::TVR),
        len: 5,
    },
    DolEntry {
        tag: Tag(tag::CURRENCY),
        len: 2,
    },
    DolEntry {
        tag: Tag(tag::TXN_DATE),
        len: 3,
    },
    DolEntry {
        tag: Tag(tag::TXN_TYPE),
        len: 1,
    },
    DolEntry {
        tag: Tag(tag::UN),
        len: 4,
    },
];

/// PDOL ma'lumoti uzunligi.
pub const PDOL_DATA_LEN: usize = 29;
/// CDOL (ARQC kirishi) uzunligi.
pub const CDOL_LEN: usize = 41;
/// IAD uzunligi.
pub const IAD_LEN: usize = 8;

/// EMV profil xatolari.
#[derive(Debug, Error, Clone, PartialEq, Eq)]
pub enum EmvError {
    #[error("noto'g'ri BCD")]
    BadBcd,
    #[error("qiymat BCD sig'imidan katta")]
    Overflow,
    #[error("noto'g'ri uzunlik: {0}")]
    BadLength(usize),
    #[error("IAD versiyasi yoki formati qo'llab-quvvatlanmaydi")]
    BadIad,
    #[error("Track 2 noto'g'ri")]
    BadTrack2,
    #[error("sana noto'g'ri")]
    BadDate,
    #[error(transparent)]
    Pan(#[from] PanError),
}

/// `value` ni `N` baytli BCD ga (2N raqam, chapdan nollar).
pub fn to_bcd<const N: usize>(mut value: u64) -> Result<[u8; N], EmvError> {
    let mut out = [0u8; N];
    for i in (0..N).rev() {
        let lo = (value % 10) as u8;
        value /= 10;
        let hi = (value % 10) as u8;
        value /= 10;
        out[i] = (hi << 4) | lo;
    }
    if value != 0 {
        return Err(EmvError::Overflow);
    }
    Ok(out)
}

/// BCD dan `u64` ga.
pub fn from_bcd(bytes: &[u8]) -> Result<u64, EmvError> {
    let mut v: u64 = 0;
    for b in bytes {
        let (hi, lo) = (b >> 4, b & 0x0F);
        if hi > 9 || lo > 9 {
            return Err(EmvError::BadBcd);
        }
        v = v
            .checked_mul(100)
            .and_then(|v| v.checked_add(u64::from(hi * 10 + lo)))
            .ok_or(EmvError::Overflow)?;
    }
    Ok(v)
}

/// Tranzaksiya sanasi (EMV `9A`, YYMMDD).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct EmvDate {
    pub year: u16,
    pub month: u8,
    pub day: u8,
}

impl EmvDate {
    /// Tekshirilgan sana (yil 2000–2099).
    pub fn new(year: u16, month: u8, day: u8) -> Result<Self, EmvError> {
        let exp = CardExpiry::new(year, month).ok_or(EmvError::BadDate)?;
        if day == 0 || day > exp.last_day() {
            return Err(EmvError::BadDate);
        }
        Ok(Self { year, month, day })
    }

    /// 3 baytli BCD.
    pub fn to_bcd(self) -> [u8; 3] {
        let n =
            u64::from(self.year % 100) * 10_000 + u64::from(self.month) * 100 + u64::from(self.day);
        // 6 raqam 3 baytga doim sig'adi.
        to_bcd::<3>(n).unwrap_or([0; 3])
    }

    /// BCD dan.
    pub fn from_bcd(b: [u8; 3]) -> Result<Self, EmvError> {
        let n = from_bcd(&b)?;
        Self::new(
            2000 + (n / 10_000) as u16,
            ((n / 100) % 100) as u8,
            (n % 100) as u8,
        )
    }
}

/// Terminal tomonidan PDOL orqali beriladigan ma'lumotlar.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct TerminalData {
    /// Summa, minor birlikda (tiyin).
    pub amount_minor: u64,
    pub other_amount_minor: u64,
    pub country: u16,
    pub tvr: [u8; 5],
    pub currency: u16,
    pub date: EmvDate,
    pub txn_type: u8,
    pub unpredictable_number: [u8; 4],
}

impl TerminalData {
    /// PDOL ma'lumoti (29 bayt, `PDOL` tartibida).
    pub fn to_pdol_data(&self) -> Result<[u8; PDOL_DATA_LEN], EmvError> {
        let mut out = [0u8; PDOL_DATA_LEN];
        let mut w = Writer::new(&mut out);
        w.put(&to_bcd::<6>(self.amount_minor)?);
        w.put(&to_bcd::<6>(self.other_amount_minor)?);
        w.put(&to_bcd::<2>(u64::from(self.country))?);
        w.put(&self.tvr);
        w.put(&to_bcd::<2>(u64::from(self.currency))?);
        w.put(&self.date.to_bcd());
        w.put(&to_bcd::<1>(u64::from(self.txn_type))?);
        w.put(&self.unpredictable_number);
        Ok(out)
    }

    /// PDOL ma'lumotidan.
    pub fn from_pdol_data(d: &[u8]) -> Result<Self, EmvError> {
        if d.len() != PDOL_DATA_LEN {
            return Err(EmvError::BadLength(d.len()));
        }
        Ok(Self {
            amount_minor: from_bcd(&d[0..6])?,
            other_amount_minor: from_bcd(&d[6..12])?,
            country: from_bcd(&d[12..14])? as u16,
            tvr: arr(&d[14..19]),
            currency: from_bcd(&d[19..21])? as u16,
            date: EmvDate::from_bcd(arr(&d[21..24]))?,
            txn_type: from_bcd(&d[24..25])? as u8,
            unpredictable_number: arr(&d[25..29]),
        })
    }
}

fn arr<const N: usize>(s: &[u8]) -> [u8; N] {
    let mut a = [0u8; N];
    a.copy_from_slice(s);
    a
}

struct Writer<'a> {
    buf: &'a mut [u8],
    pos: usize,
}

impl<'a> Writer<'a> {
    fn new(buf: &'a mut [u8]) -> Self {
        Self { buf, pos: 0 }
    }
    fn put(&mut self, b: &[u8]) {
        self.buf[self.pos..self.pos + b.len()].copy_from_slice(b);
        self.pos += b.len();
    }
}

/// CVR bitlari (IAD bayt 6).
pub mod cvr {
    /// CDCVM muvaffaqiyatli bajarildi.
    pub const CDCVM_PERFORMED: u8 = 0x80;
    /// CDCVM talab qilingan edi.
    pub const CDCVM_REQUIRED: u8 = 0x40;
}

/// Issuer Application Data (`9F10`), 8 bayt.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Iad {
    pub scheme_id: u8,
    pub luk_seq: u32,
    pub cvr: u8,
}

impl Iad {
    pub const VERSION: u8 = 0x01;

    pub fn to_bytes(self) -> [u8; IAD_LEN] {
        let s = self.luk_seq.to_be_bytes();
        [
            Self::VERSION,
            self.scheme_id,
            s[0],
            s[1],
            s[2],
            s[3],
            self.cvr,
            0x00,
        ]
    }

    pub fn from_bytes(b: &[u8]) -> Result<Self, EmvError> {
        if b.len() != IAD_LEN || b[0] != Self::VERSION || b[7] != 0 {
            return Err(EmvError::BadIad);
        }
        Ok(Self {
            scheme_id: b[1],
            luk_seq: u32::from_be_bytes([b[2], b[3], b[4], b[5]]),
            cvr: b[6],
        })
    }
}

/// ARQC kirishi (CDOL) — `emv-profile.md` §6.
pub fn cdol_data(
    terminal_pdol_data: &[u8; PDOL_DATA_LEN],
    aip: [u8; 2],
    atc: u16,
    iad: &Iad,
) -> [u8; CDOL_LEN] {
    let mut out = [0u8; CDOL_LEN];
    let mut w = Writer::new(&mut out);
    w.put(terminal_pdol_data);
    w.put(&aip);
    w.put(&atc.to_be_bytes());
    w.put(&iad.to_bytes());
    out
}

/// Track 2 ekvivalenti.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Track2 {
    pub pan: Pan,
    pub expiry: CardExpiry,
    pub service_code: String,
    pub discretionary: String,
}

impl Track2 {
    /// Standart M-Pay Test Scheme track 2.
    pub fn new(pan: Pan, expiry: CardExpiry) -> Self {
        Self {
            pan,
            expiry,
            service_code: SERVICE_CODE.to_owned(),
            discretionary: "0000".to_owned(),
        }
    }

    fn digits_with(&self, sep: char) -> zeroize::Zeroizing<String> {
        zeroize::Zeroizing::new(format!(
            "{}{sep}{}{}{}",
            self.pan.expose_digits(),
            self.expiry.to_yymm(),
            self.service_code,
            self.discretionary
        ))
    }

    /// EMV tag `57` (BCD, `D` ajratuvchi, toq bo'lsa `F` bilan to'ldiriladi).
    pub fn to_emv(&self) -> Vec<u8> {
        let s = self.digits_with('D');
        let mut nibbles: Vec<u8> = s
            .bytes()
            .map(|c| if c == b'D' { 0xD } else { c - b'0' })
            .collect();
        if nibbles.len() % 2 == 1 {
            nibbles.push(0xF);
        }
        let out = nibbles.chunks(2).map(|p| (p[0] << 4) | p[1]).collect();
        zeroize::Zeroize::zeroize(&mut nibbles);
        out
    }

    /// ISO 8583 maydon 35 (ASCII, `=` ajratuvchi).
    pub fn to_iso(&self) -> zeroize::Zeroizing<String> {
        self.digits_with('=')
    }

    /// EMV tag `57` dan.
    pub fn from_emv(b: &[u8]) -> Result<Self, EmvError> {
        let mut s = zeroize::Zeroizing::new(String::with_capacity(b.len() * 2));
        for (i, nib) in b.iter().flat_map(|x| [x >> 4, x & 0x0F]).enumerate() {
            match nib {
                0..=9 => s.push(char::from(b'0' + nib)),
                0xD => s.push('='),
                0xF if i == b.len() * 2 - 1 => {}
                _ => return Err(EmvError::BadTrack2),
            }
        }
        Self::from_iso(&s)
    }

    /// ISO 8583 maydon 35 dan.
    pub fn from_iso(s: &str) -> Result<Self, EmvError> {
        let (pan, rest) = s.split_once('=').ok_or(EmvError::BadTrack2)?;
        if rest.len() < 7 || !rest.bytes().all(|b| b.is_ascii_digit()) {
            return Err(EmvError::BadTrack2);
        }
        Ok(Self {
            pan: Pan::parse(pan)?,
            expiry: CardExpiry::parse_yymm(&rest[..4]).ok_or(EmvError::BadTrack2)?,
            service_code: rest[4..7].to_owned(),
            discretionary: rest[7..].to_owned(),
        })
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::tlv::encode_dol;
    use hex_literal::hex;
    use proptest::prelude::*;

    fn td() -> TerminalData {
        TerminalData {
            amount_minor: 1_250_000,
            other_amount_minor: 0,
            country: UZ_NUMERIC,
            tvr: [0; 5],
            currency: UZ_NUMERIC,
            date: EmvDate::new(2026, 10, 23).unwrap(),
            txn_type: 0,
            unpredictable_number: hex!("A1B2C3D4"),
        }
    }

    #[test]
    fn pdol_matches_spec() {
        assert_eq!(
            encode_dol(&PDOL),
            hex!("9F02 06 9F03 06 9F1A 02 95 05 5F2A 02 9A 03 9C 01 9F37 04")
        );
        assert_eq!(PDOL.iter().map(|e| e.len).sum::<usize>(), PDOL_DATA_LEN);
    }

    #[test]
    fn pdol_data_layout() {
        let d = td().to_pdol_data().unwrap();
        assert_eq!(
            d,
            hex!("000001250000 000000000000 0860 0000000000 0860 261023 00 A1B2C3D4")
        );
        assert_eq!(TerminalData::from_pdol_data(&d).unwrap(), td());
    }

    #[test]
    fn bcd() {
        assert_eq!(to_bcd::<6>(1_250_000).unwrap(), hex!("000001250000"));
        assert_eq!(to_bcd::<2>(860).unwrap(), hex!("0860"));
        assert_eq!(to_bcd::<1>(100), Err(EmvError::Overflow));
        assert_eq!(from_bcd(&hex!("0860")).unwrap(), 860);
        assert_eq!(from_bcd(&hex!("0A")), Err(EmvError::BadBcd));
    }

    #[test]
    fn iad_roundtrip() {
        let iad = Iad {
            scheme_id: 1,
            luk_seq: 0x01020304,
            cvr: cvr::CDCVM_PERFORMED,
        };
        assert_eq!(iad.to_bytes(), hex!("01 01 01020304 80 00"));
        assert_eq!(Iad::from_bytes(&iad.to_bytes()).unwrap(), iad);
        assert_eq!(
            Iad::from_bytes(&hex!("02 01 01020304 80 00")),
            Err(EmvError::BadIad)
        );
        assert_eq!(
            Iad::from_bytes(&hex!("01 01 01020304 80")),
            Err(EmvError::BadIad)
        );
    }

    #[test]
    fn cdol_layout() {
        let d = td().to_pdol_data().unwrap();
        let iad = Iad {
            scheme_id: 1,
            luk_seq: 7,
            cvr: 0,
        };
        let c = cdol_data(&d, AIP, 0x0102, &iad);
        assert_eq!(&c[..29], &d);
        assert_eq!(&c[29..31], &AIP);
        assert_eq!(&c[31..33], &hex!("0102"));
        assert_eq!(&c[33..], &iad.to_bytes());
    }

    #[test]
    fn track2() {
        let pan = Pan::from_prefix("990077000000123").unwrap();
        let t = Track2::new(pan.clone(), CardExpiry::new(2029, 12).unwrap());
        let iso = t.to_iso();
        assert_eq!(iso.as_str(), format!("{}=29122010000", pan.expose_digits()));
        let emv = t.to_emv();
        // 16 + 1 + 4 + 3 + 4 = 28 nibble = 14 bayt, to'ldirish yo'q
        assert_eq!(emv.len(), 14);
        assert_eq!(emv[8], 0xD2);
        assert_eq!(Track2::from_emv(&emv).unwrap(), t);
        assert_eq!(Track2::from_iso(&iso).unwrap(), t);
        let mut odd = t.clone();
        odd.discretionary = "000".into();
        let e = odd.to_emv();
        assert_eq!(e.last().unwrap() & 0x0F, 0x0F);
        assert_eq!(Track2::from_emv(&e).unwrap(), odd);
        assert!(Track2::from_emv(&hex!("99 00 77 AA")).is_err());
    }

    #[test]
    fn dates() {
        assert!(EmvDate::new(2026, 2, 29).is_err());
        assert!(EmvDate::new(2028, 2, 29).is_ok());
        let d = EmvDate::new(2026, 10, 23).unwrap();
        assert_eq!(EmvDate::from_bcd(d.to_bcd()).unwrap(), d);
    }

    proptest! {
        #[test]
        fn bcd_roundtrip(v in 0u64..1_000_000_000_000) {
            prop_assert_eq!(from_bcd(&to_bcd::<6>(v).unwrap()).unwrap(), v);
        }

        #[test]
        fn pdol_parse_never_panics(d in proptest::collection::vec(any::<u8>(), 0..40)) {
            let _ = TerminalData::from_pdol_data(&d);
            let _ = Track2::from_emv(&d);
            let _ = Iad::from_bytes(&d);
        }
    }
}
