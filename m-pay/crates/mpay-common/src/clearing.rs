//! Kliring fayli va emitent tasdig'i (ack) — M-Pay Test Scheme formati v1 (ADR-0025).
//!
//! Haqiqiy sxema formati emas: o'zimizning qat'iy uzunlikli matn qatorlari (har qator `\n` bilan
//! tugaydi, maydonlar o'ngdan probel yoki chapdan nol bilan to'ldiriladi). `TODO(spec):` haqiqiy
//! sxemaning kliring formati — kodek almashtiriladi, mantiq (`crate::clearing` ishlatuvchilari) emas.
//!
//! Kliring fayli:
//!
//! | Qator | Tarkib | Uzunlik |
//! |---|---|---|
//! | `H` | `MPAYCLR1` ‖ batch ID (12) ‖ kun `YYYYMMDD` ‖ yaratilgan vaqt (unix, 12) | 41 |
//! | `D` | tartib (6) ‖ terminal (8) ‖ merchant (15) ‖ STAN (6) ‖ RRN (12) ‖ summa (12) ‖ valyuta (3) ‖ vaqt (12) ‖ maskalangan DPAN (19) | 94 |
//! | `S` | valyuta (3) ‖ soni (6) ‖ jami (15) — har valyuta uchun, o'sish tartibida | 25 |
//! | `T` | yozuvlar soni (6) ‖ oldingi barcha baytlarning SHA-256 (64 hex) | 71 |
//!
//! Tasdiq (ack): `A` (`MPAYACK1` ‖ batch ID ‖ qabul vaqti, 33), har yozuvga `R` (tartib ‖ kod (2) ‖
//! sabab (24), 33), `Z` (qabul qilingan (6) ‖ rad etilgan (6) ‖ SHA-256, 77).
//!
//! Faylda PAN yo'q — faqat maskalangan DPAN; emitent yozuvni terminal, STAN va RRN bo'yicha topadi
//! (reversal kabi, ADR-0024). Tahlil qat'iy: har qator uzunligi, belgilar to'plami, tartib raqamlari,
//! nazorat yig'indilari va xesh tekshiriladi; xato matnida maydon qiymatlari yo'q.

use std::collections::BTreeMap;

use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use thiserror::Error;

/// Kliring fayli format belgisi.
pub const FILE_FORMAT: &str = "MPAYCLR1";
/// Tasdiq format belgisi.
pub const ACK_FORMAT: &str = "MPAYACK1";
/// Bitta fayldagi eng ko'p yozuv.
pub const MAX_RECORDS: usize = 999_999;

const MAX_AMOUNT: u64 = 999_999_999_999;
const MAX_SUM: u64 = 999_999_999_999_999;
const MAX_TIME: i64 = 999_999_999_999;

#[derive(Debug, Error, Clone, PartialEq, Eq)]
pub enum ClearingError {
    #[error("kliring fayli, qator {line}: {msg}")]
    Format { line: usize, msg: &'static str },
    #[error("kliring yozuvi {seq}: {msg}")]
    Field { seq: u32, msg: &'static str },
}

fn fmt_err(line: usize, msg: &'static str) -> ClearingError {
    ClearingError::Format { line, msg }
}

/// Bitta tranzaksiya (acquirer tasdiqlagan, terminal tovar bergan).
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ClearingRecord {
    /// 1 dan boshlab ketma-ket.
    pub seq: u32,
    pub terminal_id: String,
    pub merchant_id: String,
    pub stan: u32,
    pub rrn: String,
    pub amount_minor: u64,
    pub currency: u16,
    /// Avtorizatsiya vaqti (unix).
    pub txn_at: i64,
    pub dpan_masked: String,
}

/// Kliring fayli.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ClearingFile {
    /// 12 ta harf/raqam; bitta kun — bitta ID (qayta yuborish idempotent).
    pub batch_id: String,
    /// `YYYYMMDD` — sxema vaqti bo'yicha kun (UTC+5).
    pub business_date: String,
    pub created_at: i64,
    pub records: Vec<ClearingRecord>,
}

/// Valyuta bo'yicha jami: valyuta → (soni, summa).
pub type Totals = BTreeMap<u16, (u64, u64)>;

fn is_id(s: &str, max: usize) -> bool {
    !s.is_empty() && s.len() <= max && s.bytes().all(|b| (0x21..=0x7E).contains(&b))
}

fn digits(s: &str) -> bool {
    s.bytes().all(|b| b.is_ascii_digit())
}

fn num(s: &str, line: usize) -> Result<u64, ClearingError> {
    if s.is_empty() || !digits(s) {
        return Err(fmt_err(line, "raqam kutilgan"));
    }
    s.parse().map_err(|_| fmt_err(line, "raqam juda katta"))
}

/// Chapdan probel bilan to'ldirilgan maydonni o'qiydi (bo'sh bo'lmasligi, ichida probel yo'q).
fn text(s: &str, line: usize) -> Result<String, ClearingError> {
    let v = s.trim_end_matches(' ');
    if v.is_empty() || v.contains(' ') || !v.bytes().all(|b| (0x21..=0x7E).contains(&b)) {
        return Err(fmt_err(line, "matn maydoni noto'g'ri"));
    }
    Ok(v.to_owned())
}

fn valid_date(d: &str) -> bool {
    d.len() == 8
        && digits(d)
        && matches!(d[4..6].parse::<u8>(), Ok(1..=12))
        && matches!(d[6..8].parse::<u8>(), Ok(1..=31))
}

fn is_batch_id(s: &str) -> bool {
    s.len() == 12 && s.bytes().all(|b| b.is_ascii_alphanumeric())
}

/// Qatorlarga bo'ladi: har qator `\n` bilan tugashi shart, oxirida ortiqcha bayt yo'q.
fn lines(data: &[u8]) -> Result<Vec<&str>, ClearingError> {
    let s = std::str::from_utf8(data).map_err(|_| fmt_err(0, "UTF-8 emas"))?;
    if !s.is_ascii() {
        return Err(fmt_err(0, "faqat ASCII"));
    }
    let body = s
        .strip_suffix('\n')
        .ok_or_else(|| fmt_err(0, "oxirgi qator \\n bilan tugamagan"))?;
    Ok(body.split('\n').collect())
}

/// `T`/`Z` qatoridan oldingi baytlarning xeshi.
fn digest_before(data: &[u8], last_line: &str) -> String {
    let end = data.len() - last_line.len() - 1;
    hex::encode(Sha256::digest(&data[..end]))
}

impl ClearingRecord {
    fn check(&self) -> Result<(), ClearingError> {
        let e = |msg| ClearingError::Field { seq: self.seq, msg };
        if !is_id(&self.terminal_id, 8) {
            return Err(e("terminal_id: 1–8 bosiladigan belgi"));
        }
        if !is_id(&self.merchant_id, 15) {
            return Err(e("merchant_id: 1–15 bosiladigan belgi"));
        }
        if self.stan > 999_999 {
            return Err(e("STAN 0–999999"));
        }
        if self.rrn.len() != 12 || !self.rrn.bytes().all(|b| b.is_ascii_alphanumeric()) {
            return Err(e("RRN: 12 harf/raqam"));
        }
        if self.amount_minor > MAX_AMOUNT || self.currency > 999 {
            return Err(e("summa yoki valyuta chegaradan tashqari"));
        }
        if !(0..=MAX_TIME).contains(&self.txn_at) {
            return Err(e("vaqt chegaradan tashqari"));
        }
        if self.dpan_masked.is_empty()
            || self.dpan_masked.len() > 19
            || !self
                .dpan_masked
                .bytes()
                .all(|b| b.is_ascii_digit() || b == b'*')
        {
            return Err(e("maskalangan DPAN: raqam va *"));
        }
        // Ochiq PAN kliring fayliga tushmasin.
        if !self.dpan_masked.contains('*') {
            return Err(e("DPAN maskalanmagan"));
        }
        Ok(())
    }
}

impl ClearingFile {
    /// Valyuta bo'yicha jami.
    pub fn totals(&self) -> Totals {
        let mut t = Totals::new();
        for r in &self.records {
            let e = t.entry(r.currency).or_default();
            e.0 += 1;
            e.1 += r.amount_minor;
        }
        t
    }

    /// Faylni yig'adi (har maydon tekshiriladi).
    pub fn encode(&self) -> Result<Vec<u8>, ClearingError> {
        if !is_batch_id(&self.batch_id) {
            return Err(fmt_err(1, "batch ID: 12 harf/raqam"));
        }
        if !valid_date(&self.business_date) {
            return Err(fmt_err(1, "kun: YYYYMMDD"));
        }
        if !(0..=MAX_TIME).contains(&self.created_at) {
            return Err(fmt_err(1, "vaqt chegaradan tashqari"));
        }
        if self.records.len() > MAX_RECORDS {
            return Err(fmt_err(0, "yozuvlar juda ko'p"));
        }
        let mut out = format!(
            "H{FILE_FORMAT}{}{}{:012}\n",
            self.batch_id, self.business_date, self.created_at
        );
        for (i, r) in self.records.iter().enumerate() {
            if r.seq as usize != i + 1 {
                return Err(ClearingError::Field {
                    seq: r.seq,
                    msg: "tartib raqami ketma-ket emas",
                });
            }
            r.check()?;
            out.push_str(&format!(
                "D{:06}{:<8}{:<15}{:06}{}{:012}{:03}{:012}{:<19}\n",
                r.seq,
                r.terminal_id,
                r.merchant_id,
                r.stan,
                r.rrn,
                r.amount_minor,
                r.currency,
                r.txn_at,
                r.dpan_masked
            ));
        }
        for (cur, (n, sum)) in self.totals() {
            if sum > MAX_SUM {
                return Err(fmt_err(0, "valyuta jami juda katta"));
            }
            out.push_str(&format!("S{cur:03}{n:06}{sum:015}\n"));
        }
        let h = hex::encode(Sha256::digest(out.as_bytes()));
        out.push_str(&format!("T{:06}{h}\n", self.records.len()));
        Ok(out.into_bytes())
    }

    /// Faylni qat'iy tahlil qiladi: tuzilma, jami va xesh.
    pub fn parse(data: &[u8]) -> Result<Self, ClearingError> {
        let ls = lines(data)?;
        let (first, rest) = ls.split_first().ok_or_else(|| fmt_err(1, "bo'sh"))?;
        let (last, mid) = rest
            .split_last()
            .ok_or_else(|| fmt_err(2, "trailer yo'q"))?;
        if first.len() != 41 || &first[..9] != "HMPAYCLR1" {
            return Err(fmt_err(1, "sarlavha"));
        }
        let batch_id = first[9..21].to_owned();
        let business_date = first[21..29].to_owned();
        if !is_batch_id(&batch_id) || !valid_date(&business_date) {
            return Err(fmt_err(1, "sarlavha maydonlari"));
        }
        let created_at = num(&first[29..41], 1)? as i64;

        let mut records = Vec::new();
        let mut sums = Vec::new();
        for (i, l) in mid.iter().enumerate() {
            let line = i + 2;
            match l.as_bytes().first() {
                Some(b'D') if sums.is_empty() => {
                    if l.len() != 94 {
                        return Err(fmt_err(line, "D qatori uzunligi"));
                    }
                    let seq = num(&l[1..7], line)? as u32;
                    if seq as usize != records.len() + 1 {
                        return Err(fmt_err(line, "tartib raqami ketma-ket emas"));
                    }
                    let r = ClearingRecord {
                        seq,
                        terminal_id: text(&l[7..15], line)?,
                        merchant_id: text(&l[15..30], line)?,
                        stan: num(&l[30..36], line)? as u32,
                        rrn: l[36..48].to_owned(),
                        amount_minor: num(&l[48..60], line)?,
                        currency: num(&l[60..63], line)? as u16,
                        txn_at: num(&l[63..75], line)? as i64,
                        dpan_masked: text(&l[75..94], line)?,
                    };
                    r.check()
                        .map_err(|_| fmt_err(line, "D qatori maydonlari"))?;
                    records.push(r);
                    if records.len() > MAX_RECORDS {
                        return Err(fmt_err(line, "yozuvlar juda ko'p"));
                    }
                }
                Some(b'S') => {
                    if l.len() != 25 {
                        return Err(fmt_err(line, "S qatori uzunligi"));
                    }
                    sums.push((
                        num(&l[1..4], line)? as u16,
                        num(&l[4..10], line)?,
                        num(&l[10..25], line)?,
                    ));
                }
                _ => return Err(fmt_err(line, "kutilmagan qator")),
            }
        }
        let tline = ls.len();
        if last.len() != 71 || !last.starts_with('T') {
            return Err(fmt_err(tline, "trailer"));
        }
        if num(&last[1..7], tline)? as usize != records.len() {
            return Err(fmt_err(tline, "yozuvlar soni mos emas"));
        }
        if !last[7..].eq_ignore_ascii_case(&digest_before(data, last)) {
            return Err(fmt_err(tline, "xesh mos emas"));
        }
        let f = Self {
            batch_id,
            business_date,
            created_at,
            records,
        };
        let expect: Vec<(u16, u64, u64)> = f
            .totals()
            .into_iter()
            .map(|(c, (n, s))| (c, n, s))
            .collect();
        if sums != expect {
            return Err(fmt_err(tline, "nazorat yig'indilari mos emas"));
        }
        Ok(f)
    }
}

/// Bitta yozuv natijasi.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct AckRecord {
    pub seq: u32,
    /// `00` — qabul qilindi; boshqasi — rad.
    pub code: String,
    /// `ACCEPTED`, `ORIGINAL_NOT_FOUND` … (≤ 24 belgi, katta harf va `_`).
    pub reason: String,
}

impl AckRecord {
    pub fn accepted(&self) -> bool {
        self.code == "00"
    }
}

/// Emitent tasdig'i.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ClearingAck {
    pub batch_id: String,
    pub received_at: i64,
    pub records: Vec<AckRecord>,
}

impl ClearingAck {
    pub fn accepted(&self) -> usize {
        self.records.iter().filter(|r| r.accepted()).count()
    }

    pub fn encode(&self) -> Result<Vec<u8>, ClearingError> {
        if !is_batch_id(&self.batch_id) || !(0..=MAX_TIME).contains(&self.received_at) {
            return Err(fmt_err(1, "ack sarlavhasi"));
        }
        let mut out = format!("A{ACK_FORMAT}{}{:012}\n", self.batch_id, self.received_at);
        for (i, r) in self.records.iter().enumerate() {
            let ok_reason = !r.reason.is_empty()
                && r.reason.len() <= 24
                && r.reason
                    .bytes()
                    .all(|b| b.is_ascii_uppercase() || b == b'_');
            if r.seq as usize != i + 1
                || r.code.len() != 2
                || !r.code.bytes().all(|b| b.is_ascii_alphanumeric())
                || !ok_reason
            {
                return Err(ClearingError::Field {
                    seq: r.seq,
                    msg: "ack yozuvi",
                });
            }
            out.push_str(&format!("R{:06}{}{:<24}\n", r.seq, r.code, r.reason));
        }
        let acc = self.accepted();
        let h = hex::encode(Sha256::digest(out.as_bytes()));
        out.push_str(&format!("Z{acc:06}{:06}{h}\n", self.records.len() - acc));
        Ok(out.into_bytes())
    }

    pub fn parse(data: &[u8]) -> Result<Self, ClearingError> {
        let ls = lines(data)?;
        let (first, rest) = ls.split_first().ok_or_else(|| fmt_err(1, "bo'sh"))?;
        let (last, mid) = rest
            .split_last()
            .ok_or_else(|| fmt_err(2, "trailer yo'q"))?;
        if first.len() != 33 || &first[..9] != "AMPAYACK1" || !is_batch_id(&first[9..21]) {
            return Err(fmt_err(1, "ack sarlavhasi"));
        }
        let mut records = Vec::new();
        for (i, l) in mid.iter().enumerate() {
            let line = i + 2;
            if l.len() != 33 || !l.starts_with('R') {
                return Err(fmt_err(line, "R qatori"));
            }
            let seq = num(&l[1..7], line)? as u32;
            if seq as usize != i + 1 {
                return Err(fmt_err(line, "tartib raqami ketma-ket emas"));
            }
            let code = l[7..9].to_owned();
            let reason = text(&l[9..33], line)?;
            if !code.bytes().all(|b| b.is_ascii_alphanumeric())
                || !reason.bytes().all(|b| b.is_ascii_uppercase() || b == b'_')
            {
                return Err(fmt_err(line, "R qatori maydonlari"));
            }
            records.push(AckRecord { seq, code, reason });
        }
        let zline = ls.len();
        if last.len() != 77 || !last.starts_with('Z') {
            return Err(fmt_err(zline, "trailer"));
        }
        let ack = Self {
            batch_id: first[9..21].to_owned(),
            received_at: num(&first[21..33], 1)? as i64,
            records,
        };
        let acc = num(&last[1..7], zline)? as usize;
        let rej = num(&last[7..13], zline)? as usize;
        if acc != ack.accepted() || acc + rej != ack.records.len() {
            return Err(fmt_err(zline, "nazorat yig'indilari mos emas"));
        }
        if !last[13..].eq_ignore_ascii_case(&digest_before(data, last)) {
            return Err(fmt_err(zline, "xesh mos emas"));
        }
        Ok(ack)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use proptest::prelude::*;

    fn rec(seq: u32, cur: u16, amount: u64) -> ClearingRecord {
        ClearingRecord {
            seq,
            terminal_id: "TERM0001".into(),
            merchant_id: "SHOP0000000001".into(),
            stan: seq,
            rrn: format!("63001400{seq:04}"),
            amount_minor: amount,
            currency: cur,
            txn_at: 1_793_050_000 + i64::from(seq),
            dpan_masked: "990077******1234".into(),
        }
    }

    fn sample() -> ClearingFile {
        ClearingFile {
            batch_id: "MPAY20261027".into(),
            business_date: "20261027".into(),
            created_at: 1_793_128_000,
            records: vec![rec(1, 860, 125_000), rec(2, 860, 5_000), rec(3, 840, 700)],
        }
    }

    #[test]
    fn roundtrip_layout_and_totals() {
        let f = sample();
        let bytes = f.encode().unwrap();
        let text = String::from_utf8(bytes.clone()).unwrap();
        let ls: Vec<&str> = text.lines().collect();
        assert_eq!(ls[0], "HMPAYCLR1MPAY2026102720261027001793128000");
        assert_eq!(ls[1].len(), 94);
        assert!(
            ls[1].starts_with("D000001TERM0001SHOP0000000001 000001630014000001000000125000860")
        );
        // Valyutalar o'sish tartibida: 840, keyin 860.
        assert_eq!(ls[4], "S840000001000000000000700");
        assert_eq!(ls[5], "S860000002000000000130000");
        assert!(ls[6].starts_with("T000003"));
        assert_eq!(ClearingFile::parse(&bytes).unwrap(), f);
        assert_eq!(f.totals()[&860], (2, 130_000));
    }

    #[test]
    fn tampering_is_detected() {
        let bytes = sample().encode().unwrap();
        // Summani o'zgartirish — xesh va nazorat yig'indisi.
        let mut t = bytes.clone();
        let pos = String::from_utf8(t.clone())
            .unwrap()
            .find("000000125000")
            .unwrap();
        t[pos + 6] = b'9';
        assert!(ClearingFile::parse(&t).is_err());
        // Qatorni olib tashlash.
        let text = String::from_utf8(bytes.clone()).unwrap();
        let without: String = text
            .lines()
            .filter(|l| !l.starts_with("D000002"))
            .map(|l| format!("{l}\n"))
            .collect();
        assert!(ClearingFile::parse(without.as_bytes()).is_err());
        // Oxirgi \n yo'q, ortiqcha qator.
        assert!(ClearingFile::parse(&bytes[..bytes.len() - 1]).is_err());
        let mut extra = bytes.clone();
        extra.extend_from_slice(b"X\n");
        assert!(ClearingFile::parse(&extra).is_err());
    }

    #[test]
    fn encode_rejects_bad_fields_and_open_pan() {
        let mut f = sample();
        f.records[0].dpan_masked = "9900770000001234".into();
        assert_eq!(
            f.encode().unwrap_err(),
            ClearingError::Field {
                seq: 1,
                msg: "DPAN maskalanmagan"
            }
        );
        let mut f = sample();
        f.records[1].merchant_id = "SHOP 1".into();
        assert!(f.encode().is_err());
        let mut f = sample();
        f.records[2].seq = 7;
        assert!(f.encode().is_err());
        let mut f = sample();
        f.batch_id = "MPAY-2026".into();
        assert!(f.encode().is_err());
        let mut f = sample();
        f.business_date = "20261332".into();
        assert!(f.encode().is_err());
    }

    #[test]
    fn empty_batch_is_valid() {
        let f = ClearingFile {
            records: vec![],
            ..sample()
        };
        assert_eq!(ClearingFile::parse(&f.encode().unwrap()).unwrap(), f);
    }

    #[test]
    fn ack_roundtrip_and_tamper() {
        let a = ClearingAck {
            batch_id: "MPAY20261027".into(),
            received_at: 1_793_128_100,
            records: vec![
                AckRecord {
                    seq: 1,
                    code: "00".into(),
                    reason: "ACCEPTED".into(),
                },
                AckRecord {
                    seq: 2,
                    code: "25".into(),
                    reason: "ORIGINAL_NOT_FOUND".into(),
                },
            ],
        };
        let b = a.encode().unwrap();
        assert_eq!(ClearingAck::parse(&b).unwrap(), a);
        assert_eq!(a.accepted(), 1);
        let mut t = b.clone();
        let pos = String::from_utf8(t.clone())
            .unwrap()
            .find("R00000225")
            .unwrap();
        t[pos + 7] = b'0';
        t[pos + 8] = b'0';
        assert!(
            ClearingAck::parse(&t).is_err(),
            "rad etilganni qabulga aylantirish"
        );
    }

    proptest! {
        #[test]
        fn parse_never_panics(data in proptest::collection::vec(any::<u8>(), 0..400)) {
            let _ = ClearingFile::parse(&data);
            let _ = ClearingAck::parse(&data);
        }

        #[test]
        fn parse_never_panics_on_line_shapes(lines in proptest::collection::vec("[HDSTARZ][ -~]{0,100}", 0..6)) {
            let s: String = lines.iter().map(|l| format!("{l}\n")).collect();
            let _ = ClearingFile::parse(s.as_bytes());
            let _ = ClearingAck::parse(s.as_bytes());
        }
    }
}
