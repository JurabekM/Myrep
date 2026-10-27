//! ISO 8583 subset packer/unpacker (M-Pay sandbox profili).
//!
//! Kodlash qoidalari (`docs/specs/api.md` va ADR-0007 ga qarang):
//! * MTI — 4 ta ASCII raqam (`0100`/`0110` avtorizatsiya, `0400`/`0401`/`0410` reversal — ADR-0024);
//! * bitmap — ikkilik (8 bayt birlamchi; bit 1 = ikkilamchi bitmap mavjud);
//! * raqamli va matnli maydonlar ASCII; LLVAR/LLLVAR uzunlik prefikslari ASCII raqamlar;
//! * maydon 55 — ikkilik LLLVAR (uzunlik baytlarda).
//!
//! Qo'llab-quvvatlanadigan maydonlar: 2, 3, 4, 7, 11, 14, 22, 35, 37, 39, 41, 42, 49, 55, 90.
//! Spetsifikatsiyasi yo'q maydon bitmap'da bo'lsa — xato (uzunligini bilib bo'lmaydi).
//!
//! `Debug` maydon qiymatlarini chiqarmaydi: 2 va 35 maydonlarda PAN, 55 da kriptogramma bor.

use std::collections::BTreeMap;
use std::fmt;

use thiserror::Error;

/// ISO 8583 xatolari. Xato matnida maydon qiymatlari bo'lmaydi.
#[derive(Debug, Error, Clone, PartialEq, Eq)]
pub enum Iso8583Error {
    #[error("xabar kutilganidan oldin tugadi (offset {0})")]
    Truncated(usize),
    #[error("MTI noto'g'ri")]
    BadMti,
    #[error("maydon {0} qo'llab-quvvatlanmaydi")]
    UnsupportedField(u8),
    #[error("maydon {field}: noto'g'ri uzunlik {len}")]
    BadLength { field: u8, len: usize },
    #[error("maydon {0}: ruxsat etilmagan belgi")]
    BadCharset(u8),
    #[error("xabar oxirida ortiqcha {0} bayt")]
    TrailingData(usize),
    #[error("majburiy maydon {0} yo'q")]
    Missing(u8),
    #[error("bitmap kanonik emas (bo'sh ikkilamchi bitmap)")]
    NonCanonicalBitmap,
}

/// Maydon belgilar to'plami.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Charset {
    /// Faqat raqamlar `0-9`.
    N,
    /// Harf va raqamlar.
    An,
    /// Harf, raqam va bosiladigan maxsus belgilar (ASCII 0x20–0x7E).
    Ans,
    /// Track 2: raqamlar va `=` ajratuvchi.
    Z,
    /// Ikkilik.
    B,
}

impl Charset {
    fn accepts(self, b: u8) -> bool {
        match self {
            Charset::N => b.is_ascii_digit(),
            Charset::An => b.is_ascii_alphanumeric(),
            Charset::Ans => (0x20..=0x7E).contains(&b),
            Charset::Z => b.is_ascii_digit() || b == b'=',
            Charset::B => true,
        }
    }
}

/// Uzunlik turi.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum LenKind {
    /// Qat'iy uzunlik.
    Fixed(usize),
    /// 2 raqamli ASCII prefiks, maksimal uzunlik.
    Llvar(usize),
    /// 3 raqamli ASCII prefiks, maksimal uzunlik.
    Lllvar(usize),
}

/// Maydon spetsifikatsiyasi.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct FieldSpec {
    pub field: u8,
    pub name: &'static str,
    pub charset: Charset,
    pub len: LenKind,
}

/// Sandbox profili maydonlari.
pub const FIELDS: &[FieldSpec] = &[
    f(2, "PAN", Charset::N, LenKind::Llvar(19)),
    f(3, "Processing code", Charset::N, LenKind::Fixed(6)),
    f(4, "Amount, transaction", Charset::N, LenKind::Fixed(12)),
    f(
        7,
        "Transmission date & time",
        Charset::N,
        LenKind::Fixed(10),
    ),
    f(11, "STAN", Charset::N, LenKind::Fixed(6)),
    f(14, "Expiration date", Charset::N, LenKind::Fixed(4)),
    f(22, "POS entry mode", Charset::N, LenKind::Fixed(3)),
    f(35, "Track 2 data", Charset::Z, LenKind::Llvar(37)),
    f(37, "RRN", Charset::An, LenKind::Fixed(12)),
    f(39, "Response code", Charset::An, LenKind::Fixed(2)),
    f(41, "Terminal ID", Charset::Ans, LenKind::Fixed(8)),
    f(42, "Merchant ID", Charset::Ans, LenKind::Fixed(15)),
    f(49, "Currency code", Charset::N, LenKind::Fixed(3)),
    f(55, "ICC data", Charset::B, LenKind::Lllvar(255)),
    // Asl xabar: MTI(4) ‖ STAN(6) ‖ maydon 7(10) ‖ acquirer ID(11) ‖ forwarding ID(11).
    f(90, "Original data elements", Charset::N, LenKind::Fixed(42)),
];

const fn f(field: u8, name: &'static str, charset: Charset, len: LenKind) -> FieldSpec {
    FieldSpec {
        field,
        name,
        charset,
        len,
    }
}

/// Maydon spetsifikatsiyasini qaytaradi.
pub fn spec(field: u8) -> Option<&'static FieldSpec> {
    FIELDS.iter().find(|s| s.field == field)
}

/// Maydonlar soni qisqa bo'lgan yorliqlar (log uchun maxfiy bo'lmagan maydonlar).
const PUBLIC_FIELDS: &[u8] = &[3, 4, 7, 11, 22, 37, 39, 41, 42, 49, 90];

/// Message Type Indicator.
#[derive(Clone, Copy, PartialEq, Eq, Hash)]
pub struct Mti(pub [u8; 4]);

impl Mti {
    pub const AUTH_REQUEST: Mti = Mti(*b"0100");
    pub const AUTH_RESPONSE: Mti = Mti(*b"0110");
    /// Acquirer reversal'i — avtorizatsiya natijasi noma'lum, emitent yechimni qaytarsin (ADR-0024).
    pub const REVERSAL_REQUEST: Mti = Mti(*b"0400");
    /// Reversal'ning takroriy yuborilishi (birinchisiga javob kelmagan).
    pub const REVERSAL_REPEAT: Mti = Mti(*b"0401");
    /// Reversal javobi (`0400` va `0401` ga).
    pub const REVERSAL_RESPONSE: Mti = Mti(*b"0410");

    /// Satrdan (4 ta ASCII raqam).
    pub fn parse(s: &[u8]) -> Result<Self, Iso8583Error> {
        let arr: [u8; 4] = s.try_into().map_err(|_| Iso8583Error::BadMti)?;
        if !arr.iter().all(u8::is_ascii_digit) {
            return Err(Iso8583Error::BadMti);
        }
        Ok(Self(arr))
    }

    /// Javob MTI'si (`0100` → `0110`).
    pub fn response(self) -> Self {
        let mut a = self.0;
        a[2] = b'1';
        Self(a)
    }
}

impl fmt::Debug for Mti {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(std::str::from_utf8(&self.0).unwrap_or("????"))
    }
}

/// ISO 8583 xabari.
#[derive(Clone, PartialEq, Eq)]
pub struct IsoMessage {
    pub mti: Mti,
    fields: BTreeMap<u8, Vec<u8>>,
}

impl fmt::Debug for IsoMessage {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        let mut d = f.debug_struct("IsoMessage");
        d.field("mti", &self.mti);
        for (k, v) in &self.fields {
            let name = format!("f{k}");
            if PUBLIC_FIELDS.contains(k) {
                d.field(&name, &String::from_utf8_lossy(v));
            } else {
                d.field(&name, &format_args!("<{} bayt>", v.len()));
            }
        }
        d.finish()
    }
}

impl IsoMessage {
    /// Bo'sh xabar.
    pub fn new(mti: Mti) -> Self {
        Self {
            mti,
            fields: BTreeMap::new(),
        }
    }

    /// Maydonni o'rnatadi (spetsifikatsiya bo'yicha tekshiriladi).
    pub fn set(&mut self, field: u8, value: impl Into<Vec<u8>>) -> Result<&mut Self, Iso8583Error> {
        let value = value.into();
        validate(field, &value)?;
        self.fields.insert(field, value);
        Ok(self)
    }

    /// Matnli maydonni o'rnatadi.
    pub fn set_str(&mut self, field: u8, value: &str) -> Result<&mut Self, Iso8583Error> {
        self.set(field, value.as_bytes().to_vec())
    }

    /// Raqamli qat'iy uzunlikdagi maydonni chapdan nollar bilan to'ldirib o'rnatadi.
    pub fn set_num(&mut self, field: u8, value: u64) -> Result<&mut Self, Iso8583Error> {
        let s = spec(field).ok_or(Iso8583Error::UnsupportedField(field))?;
        let LenKind::Fixed(n) = s.len else {
            return Err(Iso8583Error::UnsupportedField(field));
        };
        let txt = format!("{value:0n$}");
        self.set(field, txt.into_bytes())
    }

    /// Maydon qiymati.
    pub fn get(&self, field: u8) -> Option<&[u8]> {
        self.fields.get(&field).map(Vec::as_slice)
    }

    /// Majburiy maydon.
    pub fn require(&self, field: u8) -> Result<&[u8], Iso8583Error> {
        self.get(field).ok_or(Iso8583Error::Missing(field))
    }

    /// Majburiy matnli maydon (ASCII maydonlar uchun).
    pub fn require_str(&self, field: u8) -> Result<&str, Iso8583Error> {
        std::str::from_utf8(self.require(field)?).map_err(|_| Iso8583Error::BadCharset(field))
    }

    /// Majburiy raqamli maydon `u64` sifatida.
    pub fn require_num(&self, field: u8) -> Result<u64, Iso8583Error> {
        self.require_str(field)?
            .parse()
            .map_err(|_| Iso8583Error::BadCharset(field))
    }

    /// Maydonni olib tashlaydi.
    pub fn remove(&mut self, field: u8) -> Option<Vec<u8>> {
        self.fields.remove(&field)
    }

    /// Mavjud maydon raqamlari.
    pub fn field_numbers(&self) -> impl Iterator<Item = u8> + '_ {
        self.fields.keys().copied()
    }

    /// Baytlarga yig'adi.
    pub fn pack(&self) -> Vec<u8> {
        let mut out = Vec::with_capacity(64);
        out.extend_from_slice(&self.mti.0);
        let secondary = self.fields.keys().any(|k| *k > 64);
        let mut bitmap = [0u8; 16];
        if secondary {
            bitmap[0] |= 0x80;
        }
        for k in self.fields.keys() {
            let i = usize::from(*k - 1);
            bitmap[i / 8] |= 0x80 >> (i % 8);
        }
        out.extend_from_slice(&bitmap[..if secondary { 16 } else { 8 }]);
        for (k, v) in &self.fields {
            // set() validatsiyadan o'tkazgan, spetsifikatsiya albatta bor.
            if let Some(s) = spec(*k) {
                match s.len {
                    LenKind::Fixed(_) => {}
                    LenKind::Llvar(_) => {
                        out.extend_from_slice(format!("{:02}", v.len()).as_bytes())
                    }
                    LenKind::Lllvar(_) => {
                        out.extend_from_slice(format!("{:03}", v.len()).as_bytes())
                    }
                }
            }
            out.extend_from_slice(v);
        }
        out
    }

    /// Baytlardan o'qiydi (qat'iy: ortiqcha bayt, noma'lum maydon, noto'g'ri belgi — xato).
    pub fn unpack(data: &[u8]) -> Result<Self, Iso8583Error> {
        let mut pos = 0usize;
        let mti = Mti::parse(take(data, &mut pos, 4)?)?;
        let mut bitmap = [0u8; 16];
        bitmap[..8].copy_from_slice(take(data, &mut pos, 8)?);
        let secondary = bitmap[0] & 0x80 != 0;
        if secondary {
            bitmap[8..].copy_from_slice(take(data, &mut pos, 8)?);
            if bitmap[8..].iter().all(|b| *b == 0) {
                return Err(Iso8583Error::NonCanonicalBitmap);
            }
        }
        let mut msg = IsoMessage::new(mti);
        let max_field = if secondary { 128 } else { 64 };
        for i in 2..=max_field {
            let idx = i - 1;
            if bitmap[idx / 8] & (0x80 >> (idx % 8)) == 0 {
                continue;
            }
            let field = u8::try_from(i).map_err(|_| Iso8583Error::UnsupportedField(u8::MAX))?;
            let s = spec(field).ok_or(Iso8583Error::UnsupportedField(field))?;
            let len = match s.len {
                LenKind::Fixed(n) => n,
                LenKind::Llvar(_) => parse_len(take(data, &mut pos, 2)?, field)?,
                LenKind::Lllvar(_) => parse_len(take(data, &mut pos, 3)?, field)?,
            };
            let v = take(data, &mut pos, len)?.to_vec();
            validate(field, &v)?;
            msg.fields.insert(field, v);
        }
        if pos != data.len() {
            return Err(Iso8583Error::TrailingData(data.len() - pos));
        }
        Ok(msg)
    }
}

fn take<'a>(data: &'a [u8], pos: &mut usize, n: usize) -> Result<&'a [u8], Iso8583Error> {
    let end = pos
        .checked_add(n)
        .filter(|e| *e <= data.len())
        .ok_or(Iso8583Error::Truncated(*pos))?;
    let s = &data[*pos..end];
    *pos = end;
    Ok(s)
}

fn parse_len(digits: &[u8], field: u8) -> Result<usize, Iso8583Error> {
    if !digits.iter().all(u8::is_ascii_digit) {
        return Err(Iso8583Error::BadLength { field, len: 0 });
    }
    Ok(digits
        .iter()
        .fold(0usize, |acc, d| acc * 10 + usize::from(d - b'0')))
}

fn validate(field: u8, value: &[u8]) -> Result<(), Iso8583Error> {
    let s = spec(field).ok_or(Iso8583Error::UnsupportedField(field))?;
    let ok_len = match s.len {
        LenKind::Fixed(n) => value.len() == n,
        LenKind::Llvar(max) | LenKind::Lllvar(max) => value.len() <= max,
    };
    if !ok_len {
        return Err(Iso8583Error::BadLength {
            field,
            len: value.len(),
        });
    }
    if !value.iter().all(|b| s.charset.accepts(*b)) {
        return Err(Iso8583Error::BadCharset(field));
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use proptest::prelude::*;

    fn sample() -> IsoMessage {
        let mut m = IsoMessage::new(Mti::AUTH_REQUEST);
        m.set_str(2, "9900770000001236").unwrap();
        m.set_str(3, "000000").unwrap();
        m.set_num(4, 1_250_000).unwrap();
        m.set_str(7, "1023153000").unwrap();
        m.set_num(11, 42).unwrap();
        m.set_str(14, "2912").unwrap();
        m.set_str(22, "071").unwrap();
        m.set_str(35, "9900770000001236=29122010000").unwrap();
        m.set_str(37, "629615000042").unwrap();
        m.set_str(41, "TERM0001").unwrap();
        m.set_str(42, "MERCHANT0000001").unwrap();
        m.set_str(49, "860").unwrap();
        m.set(55, vec![0x9F, 0x26, 0x08, 1, 2, 3, 4, 5, 6, 7, 8])
            .unwrap();
        m
    }

    #[test]
    fn known_layout() {
        let bytes = sample().pack();
        assert_eq!(&bytes[..4], b"0100");
        // Fields 2,3,4,7,11,14,22,35,37,41,42,49,55
        // bayt0: 2,3,4,7 → 0x72; bayt1: 11,14 → 0x24; bayt2: 22 → 0x04; bayt4: 35,37 → 0x28;
        // bayt5: 41,42 → 0xC0; bayt6: 49,55 → 0x82
        assert_eq!(
            &bytes[4..12],
            &[0x72, 0x24, 0x04, 0x00, 0x28, 0xC0, 0x82, 0x00]
        );
        assert_eq!(&bytes[12..14], b"16");
        let back = IsoMessage::unpack(&bytes).unwrap();
        assert_eq!(back, sample());
        assert_eq!(back.require_num(4).unwrap(), 1_250_000);
    }

    #[test]
    fn validation() {
        let mut m = IsoMessage::new(Mti::AUTH_REQUEST);
        assert_eq!(
            m.set_str(4, "12").unwrap_err(),
            Iso8583Error::BadLength { field: 4, len: 2 }
        );
        assert_eq!(
            m.set_str(3, "00000A").unwrap_err(),
            Iso8583Error::BadCharset(3)
        );
        assert_eq!(
            m.set_str(5, "1").unwrap_err(),
            Iso8583Error::UnsupportedField(5)
        );
        assert!(m.set(55, vec![0; 256]).is_err());
        assert!(m.set_str(35, "1234D5678").is_err());
    }

    #[test]
    fn strict_unpack() {
        let bytes = sample().pack();
        let mut extra = bytes.clone();
        extra.push(0);
        assert_eq!(
            IsoMessage::unpack(&extra),
            Err(Iso8583Error::TrailingData(1))
        );
        assert!(matches!(
            IsoMessage::unpack(&bytes[..bytes.len() - 1]),
            Err(Iso8583Error::Truncated(_))
        ));
        // Noma'lum maydon 5 bitmap'da.
        let mut unknown = bytes.clone();
        unknown[4] |= 0x08;
        assert!(IsoMessage::unpack(&unknown).is_err());
        assert_eq!(IsoMessage::unpack(b"01x0"), Err(Iso8583Error::BadMti));
    }

    #[test]
    fn debug_hides_sensitive_fields() {
        let s = format!("{:?}", sample());
        assert!(!s.contains("9900770000001236"));
        assert!(s.contains("f2: <16 bayt>"));
        assert!(s.contains("f35: <28 bayt>"));
        assert!(s.contains("1250000"));
    }

    #[test]
    fn response_mti() {
        assert_eq!(Mti::AUTH_REQUEST.response(), Mti::AUTH_RESPONSE);
        assert_eq!(Mti::REVERSAL_REQUEST.response(), Mti::REVERSAL_RESPONSE);
    }

    #[test]
    fn reversal_with_original_data_uses_secondary_bitmap() {
        let mut m = IsoMessage::new(Mti::REVERSAL_REQUEST);
        m.set_num(4, 1_250_000).unwrap();
        m.set_num(11, 42).unwrap();
        let orig = format!("0100{:06}{}{:011}{:011}", 42, "1023153000", 0, 0);
        m.set_str(90, &orig).unwrap();
        let bytes = m.pack();
        assert_eq!(&bytes[..4], b"0400");
        // Bit 1 — ikkilamchi bitmap; maydon 90 — ikkilamchi bitmap'ning 26-biti (bayt 3, 0x40).
        assert_eq!(bytes[4] & 0x80, 0x80);
        assert_eq!(bytes[12 + 3], 0x40);
        assert_eq!(IsoMessage::unpack(&bytes).unwrap(), m);
        assert!(format!("{m:?}").contains(&orig), "maydon 90 maxfiy emas");
        assert_eq!(
            m.set_str(90, "0100").unwrap_err(),
            Iso8583Error::BadLength { field: 90, len: 4 }
        );
    }

    fn arb_value(s: &'static FieldSpec) -> BoxedStrategy<Vec<u8>> {
        let chars: Vec<u8> = (0u8..=0xFF).filter(|b| s.charset.accepts(*b)).collect();
        let (lo, hi) = match s.len {
            LenKind::Fixed(n) => (n, n),
            LenKind::Llvar(m) | LenKind::Lllvar(m) => (0, m),
        };
        proptest::collection::vec(proptest::sample::select(chars), lo..=hi).boxed()
    }

    type FieldStrategy = BoxedStrategy<Option<(u8, Vec<u8>)>>;

    fn arb_msg() -> impl Strategy<Value = IsoMessage> {
        let parts: Vec<FieldStrategy> = FIELDS
            .iter()
            .map(|s| proptest::option::of(arb_value(s).prop_map(move |v| (s.field, v))).boxed())
            .collect();
        (
            parts,
            prop_oneof![Just(Mti::AUTH_REQUEST), Just(Mti::AUTH_RESPONSE)],
        )
            .prop_map(|(fields, mti)| {
                let mut m = IsoMessage::new(mti);
                for (k, v) in fields.into_iter().flatten() {
                    m.set(k, v).unwrap();
                }
                m
            })
    }

    proptest! {
        #[test]
        fn roundtrip(m in arb_msg()) {
            prop_assert_eq!(IsoMessage::unpack(&m.pack()).unwrap(), m);
        }

        #[test]
        fn never_panics(data in proptest::collection::vec(any::<u8>(), 0..300)) {
            let _ = IsoMessage::unpack(&data);
        }

        #[test]
        fn never_panics_with_valid_header(bitmap in any::<[u8; 8]>(),
                                          rest in proptest::collection::vec(any::<u8>(), 0..200)) {
            let mut data = b"0100".to_vec();
            data.extend_from_slice(&bitmap);
            data.extend_from_slice(&rest);
            let _ = IsoMessage::unpack(&data);
        }
    }
}
