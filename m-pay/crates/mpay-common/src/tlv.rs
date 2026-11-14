//! BER-TLV (ISO/IEC 8825-1, EMV Book 3 Annex B) parser va encoder.
//!
//! Xususiyatlar:
//! * teg 1–4 bayt (birinchi baytning past 5 biti `11111` bo'lsa davomi bor);
//! * uzunlik: qisqa shakl (`< 0x80`) va uzun shakl `0x81`–`0x84`; noaniq uzunlik (`0x80`) rad;
//! * konstruktiv teglar (birinchi baytda bit `0x20`) rekursiv tahlil qilinadi, chuqurlik cheklangan;
//! * TLV obyektlari orasidagi `0x00` to'ldiruvchi baytlar o'tkazib yuboriladi (EMV Book 3);
//! * kodlash har doim minimal uzunlik shaklida.
//!
//! Parser hech qachon panic qilmaydi — `proptest` va `cargo-fuzz` bilan tekshiriladi.

use core::fmt;

use thiserror::Error;

/// Konstruktiv obyektlarning maksimal joylashuv chuqurligi.
pub const MAX_DEPTH: usize = 16;

/// TLV xatolari.
#[derive(Debug, Error, Clone, PartialEq, Eq)]
pub enum TlvError {
    #[error("ma'lumot kutilganidan oldin tugadi (offset {0})")]
    Truncated(usize),
    #[error("teg 4 baytdan uzun (offset {0})")]
    TagTooLong(usize),
    #[error("noto'g'ri uzunlik kodlashi (offset {0})")]
    BadLength(usize),
    #[error("joylashuv chuqurligi {MAX_DEPTH} dan oshdi")]
    TooDeep,
    #[error("teg {0} topilmadi")]
    Missing(Tag),
    #[error("teg {tag} uzunligi {got}, kutilgan {expected}")]
    WrongLength {
        tag: Tag,
        expected: usize,
        got: usize,
    },
}

/// BER-TLV tegi (1–4 bayt, big-endian `u32` sifatida).
#[derive(Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub struct Tag(pub u32);

impl Tag {
    /// Tegning birinchi bayti.
    fn first_byte(self) -> u8 {
        self.0.to_be_bytes()[4 - self.byte_len() as usize]
    }

    /// Kodlangan teg uzunligi (bayt).
    pub fn byte_len(self) -> u8 {
        match self.0 {
            0..=0xFF => 1,
            0x100..=0xFFFF => 2,
            0x1_0000..=0xFF_FFFF => 3,
            _ => 4,
        }
    }

    /// Konstruktiv tegmi (bit 6 birinchi baytda).
    pub fn is_constructed(self) -> bool {
        self.first_byte() & 0x20 != 0
    }

    /// Tegni baytlarga yozadi.
    pub fn encode(self, out: &mut Vec<u8>) {
        let n = self.byte_len() as usize;
        out.extend_from_slice(&self.0.to_be_bytes()[4 - n..]);
    }

    /// Teg kodlash qoidalariga mosmi (test generatorlari va builder uchun).
    pub fn is_well_formed(self) -> bool {
        let n = self.byte_len() as usize;
        let b = &self.0.to_be_bytes()[4 - n..];
        if b[0] == 0x00 {
            return false;
        }
        let multi = b[0] & 0x1F == 0x1F;
        if !multi {
            return n == 1;
        }
        if n == 1 {
            return false;
        }
        // Davom baytlari: oxirgisidan tashqari hammasida bit 8 = 1, oxirgisida 0.
        b[1..n - 1].iter().all(|x| x & 0x80 != 0) && b[n - 1] & 0x80 == 0
    }
}

impl fmt::Debug for Tag {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{self}")
    }
}

impl fmt::Display for Tag {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        let n = self.byte_len() as usize;
        for b in &self.0.to_be_bytes()[4 - n..] {
            write!(f, "{b:02X}")?;
        }
        Ok(())
    }
}

/// TLV qiymati.
#[derive(Clone, PartialEq, Eq)]
pub enum Value {
    /// Oddiy (primitiv) qiymat.
    Primitive(Vec<u8>),
    /// Ichki TLV obyektlari.
    Constructed(Vec<Tlv>),
}

/// Bitta TLV obyekti.
#[derive(Clone, PartialEq, Eq)]
pub struct Tlv {
    pub tag: Tag,
    pub value: Value,
}

// Debug qiymatlarni chiqarmaydi: TLV ichida kriptogramma yoki Track 2 bo'lishi mumkin.
impl fmt::Debug for Tlv {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match &self.value {
            Value::Primitive(v) => write!(f, "{}[{} bayt]", self.tag, v.len()),
            Value::Constructed(c) => f.debug_tuple(&self.tag.to_string()).field(c).finish(),
        }
    }
}

impl Tlv {
    /// Primitiv obyekt.
    pub fn primitive(tag: u32, value: impl Into<Vec<u8>>) -> Self {
        Self {
            tag: Tag(tag),
            value: Value::Primitive(value.into()),
        }
    }

    /// Konstruktiv obyekt.
    pub fn constructed(tag: u32, children: Vec<Tlv>) -> Self {
        Self {
            tag: Tag(tag),
            value: Value::Constructed(children),
        }
    }

    /// Primitiv qiymat (konstruktiv bo'lsa `None`).
    pub fn bytes(&self) -> Option<&[u8]> {
        match &self.value {
            Value::Primitive(v) => Some(v),
            Value::Constructed(_) => None,
        }
    }

    /// Ichki obyektlar (primitiv bo'lsa bo'sh).
    pub fn children(&self) -> &[Tlv] {
        match &self.value {
            Value::Constructed(c) => c,
            Value::Primitive(_) => &[],
        }
    }

    /// Qiymat kodlangan uzunligi.
    fn value_len(&self) -> usize {
        match &self.value {
            Value::Primitive(v) => v.len(),
            Value::Constructed(c) => c.iter().map(Tlv::encoded_len).sum(),
        }
    }

    /// To'liq kodlangan uzunlik (teg + uzunlik + qiymat).
    pub fn encoded_len(&self) -> usize {
        let vl = self.value_len();
        self.tag.byte_len() as usize + length_len(vl) + vl
    }

    /// Kodlash (minimal uzunlik shakli).
    pub fn encode_into(&self, out: &mut Vec<u8>) {
        self.tag.encode(out);
        encode_length(self.value_len(), out);
        match &self.value {
            Value::Primitive(v) => out.extend_from_slice(v),
            Value::Constructed(c) => c.iter().for_each(|t| t.encode_into(out)),
        }
    }

    /// Kodlash.
    pub fn to_bytes(&self) -> Vec<u8> {
        let mut out = Vec::with_capacity(self.encoded_len());
        self.encode_into(&mut out);
        out
    }

    /// Daraxt ichida tegni chuqurlik bo'yicha birinchi topilgan obyekt.
    pub fn find(&self, tag: u32) -> Option<&Tlv> {
        if self.tag.0 == tag {
            return Some(self);
        }
        self.children().iter().find_map(|c| c.find(tag))
    }
}

/// Obyektlar ro'yxati ichida tegni qidiradi (rekursiv).
pub fn find(list: &[Tlv], tag: u32) -> Option<&Tlv> {
    list.iter().find_map(|t| t.find(tag))
}

/// Primitiv qiymatni qidiradi; yo'q bo'lsa `Missing`.
pub fn require(list: &[Tlv], tag: u32) -> Result<&[u8], TlvError> {
    find(list, tag)
        .and_then(Tlv::bytes)
        .ok_or(TlvError::Missing(Tag(tag)))
}

/// Aniq uzunlikdagi primitiv qiymat.
pub fn require_len<const N: usize>(list: &[Tlv], tag: u32) -> Result<[u8; N], TlvError> {
    let v = require(list, tag)?;
    v.try_into().map_err(|_| TlvError::WrongLength {
        tag: Tag(tag),
        expected: N,
        got: v.len(),
    })
}

/// Bir nechta obyektni ketma-ket kodlaydi.
pub fn encode_all(list: &[Tlv]) -> Vec<u8> {
    let mut out = Vec::new();
    list.iter().for_each(|t| t.encode_into(&mut out));
    out
}

fn length_len(len: usize) -> usize {
    match len {
        0..=0x7F => 1,
        0x80..=0xFF => 2,
        0x100..=0xFFFF => 3,
        0x1_0000..=0xFF_FFFF => 4,
        _ => 5,
    }
}

fn encode_length(len: usize, out: &mut Vec<u8>) {
    let n = length_len(len);
    if n == 1 {
        out.push(len as u8);
    } else {
        out.push(0x80 | (n as u8 - 1));
        out.extend_from_slice(&(len as u32).to_be_bytes()[4 - (n - 1)..]);
    }
}

/// Baytlardan barcha TLV obyektlarini o'qiydi. Ortiqcha yoki yarim qolgan baytlar — xato.
pub fn parse_all(data: &[u8]) -> Result<Vec<Tlv>, TlvError> {
    let mut p = Parser { data, pos: 0 };
    p.parse_list(data.len(), 0)
}

/// Bitta TLV obyektini o'qiydi va undan keyingi qolgan baytlarni qaytaradi.
pub fn parse_one(data: &[u8]) -> Result<(Tlv, &[u8]), TlvError> {
    let mut p = Parser { data, pos: 0 };
    let tlv = p.parse_tlv(0)?;
    Ok((tlv, &data[p.pos..]))
}

struct Parser<'a> {
    data: &'a [u8],
    pos: usize,
}

impl Parser<'_> {
    fn byte(&mut self) -> Result<u8, TlvError> {
        let b = *self
            .data
            .get(self.pos)
            .ok_or(TlvError::Truncated(self.pos))?;
        self.pos += 1;
        Ok(b)
    }

    fn parse_list(&mut self, end: usize, depth: usize) -> Result<Vec<Tlv>, TlvError> {
        let mut out = Vec::new();
        while self.pos < end {
            if self.data[self.pos] == 0x00 {
                self.pos += 1; // to'ldiruvchi bayt
                continue;
            }
            let start = self.pos;
            let tlv = self.parse_tlv(depth)?;
            if self.pos > end {
                return Err(TlvError::Truncated(start));
            }
            out.push(tlv);
        }
        Ok(out)
    }

    fn parse_tag(&mut self) -> Result<Tag, TlvError> {
        let start = self.pos;
        let first = self.byte()?;
        let mut tag = u32::from(first);
        if first & 0x1F == 0x1F {
            loop {
                let b = self.byte()?;
                if self.pos - start > 4 {
                    return Err(TlvError::TagTooLong(start));
                }
                tag = (tag << 8) | u32::from(b);
                if b & 0x80 == 0 {
                    break;
                }
            }
        }
        Ok(Tag(tag))
    }

    fn parse_length(&mut self) -> Result<usize, TlvError> {
        let start = self.pos;
        let first = self.byte()?;
        if first < 0x80 {
            return Ok(usize::from(first));
        }
        let n = usize::from(first & 0x7F);
        if n == 0 || n > 4 {
            return Err(TlvError::BadLength(start));
        }
        let mut len = 0usize;
        for _ in 0..n {
            len = (len << 8) | usize::from(self.byte()?);
        }
        Ok(len)
    }

    fn parse_tlv(&mut self, depth: usize) -> Result<Tlv, TlvError> {
        if depth >= MAX_DEPTH {
            return Err(TlvError::TooDeep);
        }
        let start = self.pos;
        let tag = self.parse_tag()?;
        let len = self.parse_length()?;
        let end = self
            .pos
            .checked_add(len)
            .filter(|e| *e <= self.data.len())
            .ok_or(TlvError::Truncated(start))?;
        let value = if tag.is_constructed() {
            Value::Constructed(self.parse_list(end, depth + 1)?)
        } else {
            let v = self.data[self.pos..end].to_vec();
            self.pos = end;
            Value::Primitive(v)
        };
        Ok(Tlv { tag, value })
    }
}

/// DOL (Data Object List) elementi: teg va kutilgan uzunlik.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct DolEntry {
    pub tag: Tag,
    pub len: usize,
}

/// DOL'ni o'qiydi (masalan PDOL `9F38` qiymati): teg + uzunlik juftliklari, qiymatsiz.
pub fn parse_dol(data: &[u8]) -> Result<Vec<DolEntry>, TlvError> {
    let mut p = Parser { data, pos: 0 };
    let mut out = Vec::new();
    while p.pos < data.len() {
        let tag = p.parse_tag()?;
        let len = p.parse_length()?;
        out.push(DolEntry { tag, len });
    }
    Ok(out)
}

/// DOL kodlash.
pub fn encode_dol(entries: &[DolEntry]) -> Vec<u8> {
    let mut out = Vec::new();
    for e in entries {
        e.tag.encode(&mut out);
        encode_length(e.len, &mut out);
    }
    out
}

#[cfg(test)]
mod tests {
    use super::*;
    use hex_literal::hex;
    use proptest::prelude::*;

    #[test]
    fn parses_nested_fci() {
        // PPSE FCI (docs/specs/emv-profile.md §2.1)
        let data = hex!(
            "6F 2E 84 0E 325041592E5359532E4444463031"
            "A5 1C BF0C 19 61 17 4F 06 F04D50415901 50 0A 4D2D5041592054455354 87 01 01"
        );
        let list = parse_all(&data).unwrap();
        assert_eq!(list.len(), 1);
        assert_eq!(list[0].tag, Tag(0x6F));
        assert_eq!(require(&list, 0x4F).unwrap(), hex!("F04D50415901"));
        assert_eq!(require(&list, 0x50).unwrap(), b"M-PAY TEST");
        assert_eq!(find(&list, 0xBF0C).unwrap().children().len(), 1);
        assert_eq!(encode_all(&list), data);
    }

    #[test]
    fn long_form_lengths() {
        let v = vec![0xAB; 300];
        let t = Tlv::primitive(0x9F10, v.clone());
        let b = t.to_bytes();
        assert_eq!(&b[..5], &hex!("9F10 82 012C"));
        assert_eq!(parse_all(&b).unwrap(), vec![t]);
        // Uzun shakl qisqa qiymat uchun ham qabul qilinadi (BER).
        assert_eq!(
            parse_all(&hex!("5A 81 02 1234")).unwrap(),
            vec![Tlv::primitive(0x5A, hex!("1234").to_vec())]
        );
    }

    #[test]
    fn rejects_malformed() {
        assert_eq!(parse_all(&hex!("9F")), Err(TlvError::Truncated(1)));
        assert_eq!(parse_all(&hex!("5A 05 1234")), Err(TlvError::Truncated(0)));
        assert_eq!(parse_all(&hex!("5A 80")), Err(TlvError::BadLength(1)));
        assert_eq!(
            parse_all(&hex!("5A 85 0000000001 00")),
            Err(TlvError::BadLength(1))
        );
        assert_eq!(
            parse_all(&hex!("1F 81 82 83 84 01 00")),
            Err(TlvError::TagTooLong(0))
        );
        // Ichki obyekt tashqi chegaradan chiqib ketadi.
        assert!(parse_all(&hex!("70 03 5A 05 11 22 33 44 55")).is_err());
    }

    #[test]
    fn depth_limited() {
        // MAX_DEPTH + 1 darajali joylashtirilgan konstruktivlar.
        let mut t = Tlv::constructed(0x70, vec![]);
        for _ in 0..MAX_DEPTH {
            t = Tlv::constructed(0x70, vec![t]);
        }
        assert_eq!(parse_all(&t.to_bytes()), Err(TlvError::TooDeep));
    }

    #[test]
    fn padding_skipped() {
        let list = parse_all(&hex!("00 00 5A 01 11 00 9F36 02 0001 00")).unwrap();
        assert_eq!(list.len(), 2);
    }

    #[test]
    fn dol_roundtrip() {
        let pdol = hex!("9F02 06 9F03 06 9F1A 02 95 05 5F2A 02 9A 03 9C 01 9F37 04");
        let entries = parse_dol(&pdol).unwrap();
        assert_eq!(entries.len(), 8);
        assert_eq!(entries.iter().map(|e| e.len).sum::<usize>(), 29);
        assert_eq!(encode_dol(&entries), pdol);
    }

    #[test]
    fn tag_well_formed() {
        assert!(Tag(0x5A).is_well_formed());
        assert!(Tag(0x9F36).is_well_formed());
        assert!(Tag(0xBF0C).is_well_formed());
        assert!(Tag(0xDF8101).is_well_formed());
        assert!(!Tag(0x9F).is_well_formed());
        assert!(!Tag(0x5A01).is_well_formed());
        assert!(!Tag(0x9F81).is_well_formed());
    }

    #[test]
    fn debug_hides_values() {
        let t = Tlv::primitive(0x9F26, hex!("1122334455667788").to_vec());
        let s = format!("{t:?}");
        assert_eq!(s, "9F26[8 bayt]");
    }

    fn arb_tag(constructed: bool) -> impl Strategy<Value = Tag> {
        let c = if constructed { 0x20u8 } else { 0x00 };
        prop_oneof![
            // bitta baytli: past 5 bit != 11111, bayt != 0
            (0u8..0x1F, 0u8..4)
                .prop_map(move |(low, class)| Tag(u32::from((class << 6) | c | low.max(1)))),
            // ikki baytli
            (0u8..4, 0u8..0x80).prop_map(move |(class, b2)| Tag(u32::from_be_bytes([
                0,
                0,
                (class << 6) | c | 0x1F,
                b2
            ]))),
            // uch baytli
            (0u8..4, 0x80u8..=0xFF, 0u8..0x80).prop_map(move |(class, b2, b3)| Tag(
                u32::from_be_bytes([0, (class << 6) | c | 0x1F, b2, b3])
            )),
        ]
    }

    fn arb_tlv() -> impl Strategy<Value = Tlv> {
        let leaf = (
            arb_tag(false),
            proptest::collection::vec(any::<u8>(), 0..300),
        )
            .prop_map(|(tag, v)| Tlv {
                tag,
                value: Value::Primitive(v),
            });
        leaf.prop_recursive(4, 64, 6, |inner| {
            (arb_tag(true), proptest::collection::vec(inner, 0..6)).prop_map(|(tag, c)| Tlv {
                tag,
                value: Value::Constructed(c),
            })
        })
    }

    proptest! {
        #[test]
        fn roundtrip(list in proptest::collection::vec(arb_tlv(), 0..5)) {
            let bytes = encode_all(&list);
            prop_assert_eq!(parse_all(&bytes).unwrap(), list);
        }

        #[test]
        fn never_panics(data in proptest::collection::vec(any::<u8>(), 0..512)) {
            let _ = parse_all(&data);
            let _ = parse_dol(&data);
            let _ = parse_one(&data);
        }

        #[test]
        fn generated_tags_well_formed(t in arb_tag(false)) {
            prop_assert!(t.is_well_formed());
        }
    }
}
