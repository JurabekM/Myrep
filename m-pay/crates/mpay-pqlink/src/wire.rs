//! PQ Link xabarlarini kodlash (`docs/specs/pqlink.md` §3–§5).
//!
//! Barcha butun sonlar big-endian. Parser har uzunlikni qolgan bufer bilan solishtiradi,
//! ortiqcha baytlar xato. Hech qachon panic qilmaydi (proptest + `cargo-fuzz`).

use crate::PqLinkError;

pub const MAGIC: [u8; 4] = *b"MPQL";
pub const VERSION: u8 = 0x01;
/// Yagona kripto to'plami.
pub const SUITE_V1: u8 = 0x01;

pub const X25519_LEN: usize = 32;
pub const MLKEM768_EK_LEN: usize = 1184;
pub const MLKEM768_CT_LEN: usize = 1088;
pub const ED25519_SIG_LEN: usize = 64;
pub const MLDSA65_SIG_LEN: usize = 3309;
pub const MLDSA65_PK_LEN: usize = 1952;
pub const SESSION_ID_LEN: usize = 16;
pub const HEADER_LEN: usize = 6;

/// Bitta yozuvning maksimal shifrmatn hajmi.
pub const MAX_RECORD_LEN: usize = 64 * 1024;
/// Attestatsiya zanjiridagi sertifikatlar soni chegarasi.
pub const MAX_CERTS: usize = 6;
/// Bitta sertifikat hajmi chegarasi.
pub const MAX_CERT_LEN: usize = 8 * 1024;

/// Xabar turlari.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
#[repr(u8)]
pub enum MsgType {
    ClientHello = 0x01,
    ServerHello = 0x02,
    ClientFinished = 0x03,
    ServerAccept = 0x04,
    Record = 0x10,
}

impl MsgType {
    fn from_u8(b: u8) -> Option<Self> {
        Some(match b {
            0x01 => Self::ClientHello,
            0x02 => Self::ServerHello,
            0x03 => Self::ClientFinished,
            0x04 => Self::ServerAccept,
            0x10 => Self::Record,
            _ => return None,
        })
    }
}

/// Sarlavha baytlari.
pub fn header(t: MsgType) -> [u8; HEADER_LEN] {
    [MAGIC[0], MAGIC[1], MAGIC[2], MAGIC[3], VERSION, t as u8]
}

/// Xabar turini sarlavhadan o'qiydi (to'liq tahlilsiz).
pub fn peek_type(data: &[u8]) -> Result<MsgType, PqLinkError> {
    if data.len() < HEADER_LEN || data[..4] != MAGIC || data[4] != VERSION {
        return Err(PqLinkError::UnexpectedMessage);
    }
    MsgType::from_u8(data[5]).ok_or(PqLinkError::UnexpectedMessage)
}

pub(crate) struct Reader<'a> {
    data: &'a [u8],
    pos: usize,
}

impl<'a> Reader<'a> {
    /// Sarlavhani tekshirib o'qishni boshlaydi.
    pub(crate) fn new(data: &'a [u8], expect: MsgType) -> Result<Self, PqLinkError> {
        if peek_type(data)? != expect {
            return Err(PqLinkError::UnexpectedMessage);
        }
        Ok(Self {
            data,
            pos: HEADER_LEN,
        })
    }

    /// Sarlavhasiz ichki tarkib uchun.
    pub(crate) fn raw(data: &'a [u8]) -> Self {
        Self { data, pos: 0 }
    }

    pub(crate) fn pos(&self) -> usize {
        self.pos
    }

    pub(crate) fn bytes(&mut self, n: usize) -> Result<&'a [u8], PqLinkError> {
        let end = self
            .pos
            .checked_add(n)
            .filter(|e| *e <= self.data.len())
            .ok_or(PqLinkError::Malformed("qisqa xabar"))?;
        let s = &self.data[self.pos..end];
        self.pos = end;
        Ok(s)
    }

    pub(crate) fn array<const N: usize>(&mut self) -> Result<[u8; N], PqLinkError> {
        let mut a = [0u8; N];
        a.copy_from_slice(self.bytes(N)?);
        Ok(a)
    }

    pub(crate) fn u8(&mut self) -> Result<u8, PqLinkError> {
        Ok(self.bytes(1)?[0])
    }

    pub(crate) fn u16(&mut self) -> Result<u16, PqLinkError> {
        Ok(u16::from_be_bytes(self.array()?))
    }

    pub(crate) fn u64(&mut self) -> Result<u64, PqLinkError> {
        Ok(u64::from_be_bytes(self.array()?))
    }

    /// `u16` uzunlik prefiksli maydon.
    pub(crate) fn var16(&mut self, max: usize) -> Result<&'a [u8], PqLinkError> {
        let n = usize::from(self.u16()?);
        if n > max {
            return Err(PqLinkError::Malformed("maydon juda uzun"));
        }
        self.bytes(n)
    }

    pub(crate) fn rest(&mut self) -> &'a [u8] {
        let s = &self.data[self.pos..];
        self.pos = self.data.len();
        s
    }

    pub(crate) fn finish(&self) -> Result<(), PqLinkError> {
        if self.pos == self.data.len() {
            Ok(())
        } else {
            Err(PqLinkError::Malformed("ortiqcha baytlar"))
        }
    }
}

pub(crate) fn put_var16(out: &mut Vec<u8>, v: &[u8]) -> Result<(), PqLinkError> {
    let n = u16::try_from(v.len()).map_err(|_| PqLinkError::Malformed("maydon juda uzun"))?;
    out.extend_from_slice(&n.to_be_bytes());
    out.extend_from_slice(v);
    Ok(())
}

// ------------------------------------------------------------------ xabarlar

/// ClientHello.
#[derive(Clone, PartialEq, Eq)]
pub struct ClientHello {
    pub client_random: [u8; 32],
    pub suites: Vec<u8>,
    pub x25519: [u8; X25519_LEN],
    pub mlkem_ek: Vec<u8>,
}

impl std::fmt::Debug for ClientHello {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("ClientHello")
            .field("suites", &self.suites)
            .finish_non_exhaustive()
    }
}

impl ClientHello {
    pub fn encode(&self) -> Result<Vec<u8>, PqLinkError> {
        if self.suites.is_empty()
            || self.suites.len() > 16
            || self.mlkem_ek.len() != MLKEM768_EK_LEN
        {
            return Err(PqLinkError::Malformed("ClientHello maydonlari"));
        }
        let mut out =
            Vec::with_capacity(HEADER_LEN + 32 + 1 + self.suites.len() + 32 + MLKEM768_EK_LEN);
        out.extend_from_slice(&header(MsgType::ClientHello));
        out.extend_from_slice(&self.client_random);
        out.push(self.suites.len() as u8);
        out.extend_from_slice(&self.suites);
        out.extend_from_slice(&self.x25519);
        out.extend_from_slice(&self.mlkem_ek);
        Ok(out)
    }

    pub fn decode(data: &[u8]) -> Result<Self, PqLinkError> {
        let mut r = Reader::new(data, MsgType::ClientHello)?;
        let client_random = r.array()?;
        let n = usize::from(r.u8()?);
        if n == 0 || n > 16 {
            return Err(PqLinkError::Malformed("suites soni"));
        }
        let suites = r.bytes(n)?.to_vec();
        let x25519 = r.array()?;
        let mlkem_ek = r.bytes(MLKEM768_EK_LEN)?.to_vec();
        r.finish()?;
        Ok(Self {
            client_random,
            suites,
            x25519,
            mlkem_ek,
        })
    }
}

/// ServerHello.
#[derive(Clone, PartialEq, Eq)]
pub struct ServerHello {
    pub server_random: [u8; 32],
    pub session_id: [u8; SESSION_ID_LEN],
    pub suite: u8,
    pub x25519: [u8; X25519_LEN],
    pub mlkem_ct: Vec<u8>,
    pub server_fp: [u8; 32],
    pub sig_ed25519: [u8; ED25519_SIG_LEN],
    pub sig_mldsa65: Vec<u8>,
    pub server_finished: [u8; 32],
}

impl std::fmt::Debug for ServerHello {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("ServerHello")
            .field("session_id", &hex::encode(self.session_id))
            .finish_non_exhaustive()
    }
}

impl ServerHello {
    /// Imzo va `s_finished` dan oldingi qism (th1 uchun).
    pub fn encode_unsigned(&self) -> Result<Vec<u8>, PqLinkError> {
        if self.mlkem_ct.len() != MLKEM768_CT_LEN {
            return Err(PqLinkError::Malformed("ML-KEM shifrmatni uzunligi"));
        }
        let mut out = Vec::with_capacity(4096 + MLDSA65_SIG_LEN);
        out.extend_from_slice(&header(MsgType::ServerHello));
        out.extend_from_slice(&self.server_random);
        out.extend_from_slice(&self.session_id);
        out.push(self.suite);
        out.extend_from_slice(&self.x25519);
        out.extend_from_slice(&self.mlkem_ct);
        out.extend_from_slice(&self.server_fp);
        Ok(out)
    }

    pub fn encode(&self) -> Result<Vec<u8>, PqLinkError> {
        if self.sig_mldsa65.len() != MLDSA65_SIG_LEN {
            return Err(PqLinkError::Malformed("ML-DSA imzosi uzunligi"));
        }
        let mut out = self.encode_unsigned()?;
        out.extend_from_slice(&self.sig_ed25519);
        out.extend_from_slice(&self.sig_mldsa65);
        out.extend_from_slice(&self.server_finished);
        Ok(out)
    }

    /// `(xabar, imzosiz qism uzunligi)`.
    pub fn decode(data: &[u8]) -> Result<(Self, usize), PqLinkError> {
        let mut r = Reader::new(data, MsgType::ServerHello)?;
        let server_random = r.array()?;
        let session_id = r.array()?;
        let suite = r.u8()?;
        let x25519 = r.array()?;
        let mlkem_ct = r.bytes(MLKEM768_CT_LEN)?.to_vec();
        let server_fp = r.array()?;
        let unsigned_len = r.pos();
        let sig_ed25519 = r.array()?;
        let sig_mldsa65 = r.bytes(MLDSA65_SIG_LEN)?.to_vec();
        let server_finished = r.array()?;
        r.finish()?;
        Ok((
            Self {
                server_random,
                session_id,
                suite,
                x25519,
                mlkem_ct,
                server_fp,
                sig_ed25519,
                sig_mldsa65,
                server_finished,
            },
            unsigned_len,
        ))
    }
}

/// Shifrlangan xabar (ClientFinished, ServerAccept, Record) — umumiy ramka.
#[derive(Clone, PartialEq, Eq)]
pub struct Sealed {
    pub kind: MsgType,
    pub session_id: [u8; SESSION_ID_LEN],
    pub seq: u64,
    pub ciphertext: Vec<u8>,
}

impl std::fmt::Debug for Sealed {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(
            f,
            "Sealed({:?}, seq={}, {} bayt)",
            self.kind,
            self.seq,
            self.ciphertext.len()
        )
    }
}

impl Sealed {
    /// AAD = sarlavha ‖ session_id ‖ seq ‖ yo'nalish.
    pub fn aad(kind: MsgType, session_id: &[u8; SESSION_ID_LEN], seq: u64, dir: u8) -> Vec<u8> {
        let mut a = Vec::with_capacity(HEADER_LEN + SESSION_ID_LEN + 9);
        a.extend_from_slice(&header(kind));
        a.extend_from_slice(session_id);
        a.extend_from_slice(&seq.to_be_bytes());
        a.push(dir);
        a
    }

    pub fn encode(&self) -> Vec<u8> {
        let mut out = Vec::with_capacity(HEADER_LEN + SESSION_ID_LEN + 8 + self.ciphertext.len());
        out.extend_from_slice(&header(self.kind));
        out.extend_from_slice(&self.session_id);
        out.extend_from_slice(&self.seq.to_be_bytes());
        out.extend_from_slice(&self.ciphertext);
        out
    }

    pub fn decode(data: &[u8], kind: MsgType) -> Result<Self, PqLinkError> {
        if !matches!(
            kind,
            MsgType::ClientFinished | MsgType::ServerAccept | MsgType::Record
        ) {
            return Err(PqLinkError::UnexpectedMessage);
        }
        let mut r = Reader::new(data, kind)?;
        let session_id = r.array()?;
        let seq = r.u64()?;
        let ciphertext = r.rest().to_vec();
        if ciphertext.len() < 16 || ciphertext.len() > MAX_RECORD_LEN + 16 {
            return Err(PqLinkError::Malformed("shifrmatn uzunligi"));
        }
        Ok(Self {
            kind,
            session_id,
            seq,
            ciphertext,
        })
    }
}

/// ClientFinished ichki tarkibi.
#[derive(Clone, PartialEq, Eq)]
pub struct ClientFinishedInner {
    pub cert_chain: Vec<Vec<u8>>,
    pub device_sig: Vec<u8>,
    pub client_finished: [u8; 32],
}

impl std::fmt::Debug for ClientFinishedInner {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(
            f,
            "ClientFinishedInner({} sertifikat)",
            self.cert_chain.len()
        )
    }
}

impl ClientFinishedInner {
    pub fn encode(&self) -> Result<Vec<u8>, PqLinkError> {
        if self.cert_chain.is_empty() || self.cert_chain.len() > MAX_CERTS {
            return Err(PqLinkError::Malformed("sertifikatlar soni"));
        }
        let mut out = Vec::new();
        out.push(self.cert_chain.len() as u8);
        for c in &self.cert_chain {
            if c.len() > MAX_CERT_LEN {
                return Err(PqLinkError::Malformed("sertifikat juda katta"));
            }
            put_var16(&mut out, c)?;
        }
        put_var16(&mut out, &self.device_sig)?;
        out.extend_from_slice(&self.client_finished);
        Ok(out)
    }

    pub fn decode(data: &[u8]) -> Result<Self, PqLinkError> {
        let mut r = Reader::raw(data);
        let n = usize::from(r.u8()?);
        if n == 0 || n > MAX_CERTS {
            return Err(PqLinkError::Malformed("sertifikatlar soni"));
        }
        let mut cert_chain = Vec::with_capacity(n);
        for _ in 0..n {
            cert_chain.push(r.var16(MAX_CERT_LEN)?.to_vec());
        }
        let device_sig = r.var16(80)?.to_vec();
        let client_finished = r.array()?;
        r.finish()?;
        Ok(Self {
            cert_chain,
            device_sig,
            client_finished,
        })
    }
}

/// ServerAccept ichki tarkibi.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ServerAcceptInner {
    pub device_id: [u8; 32],
    /// Sessiya tugash vaqti (unix sekund).
    pub expires_at: i64,
}

impl ServerAcceptInner {
    pub fn encode(&self) -> Vec<u8> {
        let mut out = Vec::with_capacity(40);
        out.extend_from_slice(&self.device_id);
        out.extend_from_slice(&self.expires_at.to_be_bytes());
        out
    }

    pub fn decode(data: &[u8]) -> Result<Self, PqLinkError> {
        let mut r = Reader::raw(data);
        let device_id = r.array()?;
        let expires_at = i64::from_be_bytes(r.array()?);
        r.finish()?;
        Ok(Self {
            device_id,
            expires_at,
        })
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use proptest::prelude::*;

    fn ch() -> ClientHello {
        ClientHello {
            client_random: [1; 32],
            suites: vec![SUITE_V1],
            x25519: [2; 32],
            mlkem_ek: vec![3; MLKEM768_EK_LEN],
        }
    }

    #[test]
    fn client_hello_roundtrip_and_strictness() {
        let b = ch().encode().unwrap();
        assert_eq!(b.len(), 6 + 32 + 2 + 32 + 1184);
        assert_eq!(ClientHello::decode(&b).unwrap(), ch());
        let mut extra = b.clone();
        extra.push(0);
        assert!(ClientHello::decode(&extra).is_err());
        assert!(ClientHello::decode(&b[..b.len() - 1]).is_err());
        let mut wrong = b.clone();
        wrong[4] = 2;
        assert_eq!(
            ClientHello::decode(&wrong),
            Err(PqLinkError::UnexpectedMessage)
        );
    }

    #[test]
    fn server_hello_roundtrip() {
        let sh = ServerHello {
            server_random: [4; 32],
            session_id: [5; 16],
            suite: SUITE_V1,
            x25519: [6; 32],
            mlkem_ct: vec![7; MLKEM768_CT_LEN],
            server_fp: [8; 32],
            sig_ed25519: [9; 64],
            sig_mldsa65: vec![10; MLDSA65_SIG_LEN],
            server_finished: [11; 32],
        };
        let b = sh.encode().unwrap();
        assert_eq!(b.len(), 4612); // pqlink.md §3.1
        let (back, ul) = ServerHello::decode(&b).unwrap();
        assert_eq!(back, sh);
        assert_eq!(&b[..ul], &sh.encode_unsigned().unwrap()[..]);
    }

    #[test]
    fn inner_roundtrip() {
        let cf = ClientFinishedInner {
            cert_chain: vec![vec![1; 300], vec![2; 400]],
            device_sig: vec![3; 71],
            client_finished: [4; 32],
        };
        assert_eq!(
            ClientFinishedInner::decode(&cf.encode().unwrap()).unwrap(),
            cf
        );
        let sa = ServerAcceptInner {
            device_id: [9; 32],
            expires_at: 1_800_000_000,
        };
        assert_eq!(ServerAcceptInner::decode(&sa.encode()).unwrap(), sa);
    }

    proptest! {
        #[test]
        fn decoders_never_panic(data in proptest::collection::vec(any::<u8>(), 0..2048), t in 0u8..0x12) {
            let mut d = header(MsgType::Record).to_vec();
            d[5] = t;
            d.extend_from_slice(&data);
            let _ = ClientHello::decode(&d);
            let _ = ServerHello::decode(&d);
            let _ = Sealed::decode(&d, MsgType::Record);
            let _ = Sealed::decode(&d, MsgType::ClientFinished);
            let _ = ClientFinishedInner::decode(&data);
            let _ = ServerAcceptInner::decode(&data);
            let _ = peek_type(&data);
        }
    }
}
