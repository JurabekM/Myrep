//! ISO/IEC 7816-4 qisqa APDU'lar va transport abstraksiyasi.

use thiserror::Error;

/// Holat so'zlari.
pub mod sw {
    pub const OK: u16 = 0x9000;
    pub const WRONG_LENGTH: u16 = 0x6700;
    pub const WRONG_DATA: u16 = 0x6A80;
    pub const FILE_NOT_FOUND: u16 = 0x6A82;
    pub const CONDITIONS_NOT_SATISFIED: u16 = 0x6985;
    pub const SEE_PHONE: u16 = 0x6986;
    pub const INS_NOT_SUPPORTED: u16 = 0x6D00;
    pub const CLA_NOT_SUPPORTED: u16 = 0x6E00;
}

/// Buyruq APDU.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Command {
    pub cla: u8,
    pub ins: u8,
    pub p1: u8,
    pub p2: u8,
    pub data: Vec<u8>,
    pub le: Option<u8>,
}

#[derive(Debug, Error, Clone, PartialEq, Eq)]
pub enum ApduError {
    #[error("APDU uzunligi noto'g'ri")]
    BadLength,
}

impl Command {
    pub fn new(cla: u8, ins: u8, p1: u8, p2: u8, data: Vec<u8>, le: Option<u8>) -> Self {
        Self {
            cla,
            ins,
            p1,
            p2,
            data,
            le,
        }
    }

    /// `SELECT` nom bo'yicha.
    pub fn select(name: &[u8]) -> Self {
        Self::new(0x00, 0xA4, 0x04, 0x00, name.to_vec(), Some(0))
    }

    /// `GET PROCESSING OPTIONS` (`83` shablon ichida PDOL ma'lumoti).
    pub fn gpo(pdol_data: &[u8]) -> Self {
        let mut d = vec![0x83, pdol_data.len() as u8];
        d.extend_from_slice(pdol_data);
        Self::new(0x80, 0xA8, 0x00, 0x00, d, Some(0))
    }

    pub fn to_bytes(&self) -> Vec<u8> {
        let mut v = vec![self.cla, self.ins, self.p1, self.p2];
        if !self.data.is_empty() {
            v.push(self.data.len() as u8);
            v.extend_from_slice(&self.data);
        }
        if let Some(le) = self.le {
            v.push(le);
        }
        v
    }

    /// Qisqa APDU (1–4 holatlar).
    pub fn parse(b: &[u8]) -> Result<Self, ApduError> {
        if b.len() < 4 {
            return Err(ApduError::BadLength);
        }
        let (h, rest) = b.split_at(4);
        let (data, le) = match rest.len() {
            0 => (vec![], None),
            1 => (vec![], Some(rest[0])),
            _ => {
                let lc = usize::from(rest[0]);
                if lc == 0 {
                    return Err(ApduError::BadLength);
                }
                match rest.len() - 1 {
                    n if n == lc => (rest[1..].to_vec(), None),
                    n if n == lc + 1 => (rest[1..=lc].to_vec(), Some(rest[lc + 1])),
                    _ => return Err(ApduError::BadLength),
                }
            }
        };
        Ok(Self::new(h[0], h[1], h[2], h[3], data, le))
    }
}

/// Javob APDU.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Response {
    pub data: Vec<u8>,
    pub sw: u16,
}

impl Response {
    pub fn ok(data: Vec<u8>) -> Self {
        Self { data, sw: sw::OK }
    }

    pub fn status(sw: u16) -> Self {
        Self { data: vec![], sw }
    }

    pub fn to_bytes(&self) -> Vec<u8> {
        let mut v = self.data.clone();
        v.extend_from_slice(&self.sw.to_be_bytes());
        v
    }

    pub fn parse(b: &[u8]) -> Result<Self, ApduError> {
        if b.len() < 2 {
            return Err(ApduError::BadLength);
        }
        let (d, s) = b.split_at(b.len() - 2);
        Ok(Self {
            data: d.to_vec(),
            sw: u16::from_be_bytes([s[0], s[1]]),
        })
    }
}

/// Karta tomoni (applet): C-APDU → R-APDU.
pub trait ApduHandler: Send {
    fn process(&mut self, capdu: &[u8]) -> Vec<u8>;
}

/// Transport xatosi.
#[derive(Debug, Error, Clone, PartialEq, Eq)]
pub enum TransportError {
    #[error("karta javob bermadi: {0}")]
    Io(String),
}

/// APDU transporti: loopback (shu jarayondagi soft-karta), keyin PC/SC (ACR122U) yoki NFC.
pub trait ApduTransport {
    fn transmit(&mut self, capdu: &[u8]) -> Result<Vec<u8>, TransportError>;
}

/// Loopback transport: Rust ichidagi karta emulyatoriga to'g'ridan-to'g'ri.
pub struct Loopback<'a, H: ApduHandler> {
    pub card: &'a mut H,
    /// Almashinuv jurnali (test va diagnostika uchun; ichida kriptogrammalar bor — logga yozilmaydi).
    pub trace: Vec<(Vec<u8>, Vec<u8>)>,
}

impl<'a, H: ApduHandler> Loopback<'a, H> {
    pub fn new(card: &'a mut H) -> Self {
        Self {
            card,
            trace: vec![],
        }
    }
}

impl<H: ApduHandler> ApduTransport for Loopback<'_, H> {
    fn transmit(&mut self, capdu: &[u8]) -> Result<Vec<u8>, TransportError> {
        let r = self.card.process(capdu);
        self.trace.push((capdu.to_vec(), r.clone()));
        Ok(r)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use proptest::prelude::*;

    #[test]
    fn select_ppse_bytes_match_spec() {
        let c = Command::select(b"2PAY.SYS.DDF01");
        assert_eq!(
            hex::encode_upper(c.to_bytes()),
            "00A404000E325041592E5359532E444446303100"
        );
        assert_eq!(Command::parse(&c.to_bytes()).unwrap(), c);
    }

    #[test]
    fn parse_cases() {
        assert_eq!(Command::parse(&[0, 0xB0, 0, 0]).unwrap().le, None);
        assert_eq!(
            Command::parse(&[0, 0xB0, 0, 0, 0x10]).unwrap().le,
            Some(0x10)
        );
        let c3 = Command::parse(&[0, 0xA4, 4, 0, 2, 0xAA, 0xBB]).unwrap();
        assert_eq!((c3.data.as_slice(), c3.le), (&[0xAA, 0xBB][..], None));
        assert!(Command::parse(&[0, 0xA4, 4, 0, 3, 0xAA]).is_err());
        assert!(Command::parse(&[0, 0xA4]).is_err());
    }

    proptest! {
        #[test]
        fn parse_never_panics(b in proptest::collection::vec(any::<u8>(), 0..300)) {
            let _ = Command::parse(&b);
            let _ = Response::parse(&b);
        }
    }
}
