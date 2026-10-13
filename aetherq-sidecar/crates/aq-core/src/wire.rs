//! Wire formatlar — Python `aether_q_v51/handshake.py` (enc_*/dec_*) bilan bayt-mos.
//!
//! Handshake frame: type(1) ‖ version(2)=0x0501 ‖ length(3) ‖ body.
//! Ko'p baytli butun sonlar — big-endian.

use crate::error::{AqError, Result};

pub const AQ_VERSION: u16 = 0x0501;
pub const SUPPORTED_VERSIONS: [u16; 1] = [AQ_VERSION];
pub const HS_HDR: usize = 6;
pub const REC_HDR: usize = 5;
/// Bitta xabar uchun maksimal tana (DoS/xotira chegarasi, Python `MAX_MSG` bilan bir xil).
pub const MAX_MSG: usize = 1 << 22;

pub const MSG_CLIENT_HELLO: u8 = 0x01;
pub const MSG_SERVER_HELLO: u8 = 0x02;
pub const MSG_CLIENT_KEX: u8 = 0x03;
pub const MSG_FINISHED: u8 = 0x04;
pub const MSG_CLIENT_AUTH: u8 = 0x09;
pub const MSG_HELLO_RETRY: u8 = 0x06;
pub const MSG_CH_RETRY: u8 = 0x07;
pub const MSG_NST: u8 = 0x08;
pub const MSG_EARLY_DATA: u8 = 0x0A;
pub const MSG_ALERT: u8 = 0x15;

/// ClientHello flags: klient session ticket kutadi (NST yuboriladi).
pub const FLAG_WANT_TICKET: u8 = 0x01;
/// ClientHello flags: CH dan keyin 0-RTT EARLY_DATA frame keladi.
pub const FLAG_EARLY_DATA: u8 = 0x02;

/// ServerHello flags: server klient autentifikatsiyasini talab qiladi.
pub const SH_FLAG_CLIENT_AUTH: u8 = 0x01;

/// Bitta handshake frame'ni quradi.
pub fn frame(mtype: u8, body: &[u8]) -> Vec<u8> {
    let mut out = Vec::with_capacity(HS_HDR + body.len());
    out.push(mtype);
    out.extend_from_slice(&AQ_VERSION.to_be_bytes());
    let len = body.len() as u32;
    out.extend_from_slice(&len.to_be_bytes()[1..]); // 3 bayt
    out.extend_from_slice(body);
    out
}

/// ALERT frame: level=fatal(2) ‖ code.
pub fn alert_frame(code: u8) -> Vec<u8> {
    frame(MSG_ALERT, &[0x02, code])
}

/// Bufer boshidagi bitta frame'ni ajratadi. Qaytaradi: (type, body, frame uzunligi).
pub fn parse_frame(data: &[u8]) -> Result<(u8, &[u8], usize)> {
    if data.len() < HS_HDR {
        return Err(AqError::Malformed("sarlavha qisqa"));
    }
    let mtype = data[0];
    let length = u32::from_be_bytes([0, data[3], data[4], data[5]]) as usize;
    if length > MAX_MSG {
        return Err(AqError::Malformed("xabar juda katta"));
    }
    if data.len() < HS_HDR + length {
        return Err(AqError::Malformed("tana qisqa"));
    }
    Ok((mtype, &data[HS_HDR..HS_HDR + length], HS_HDR + length))
}

/// Buferda AYNAN bitta frame bo'lishini talab qiladi (ortiqcha bayt → rad, F-02 / S3.1).
pub fn parse_exact(data: &[u8]) -> Result<(u8, &[u8])> {
    let (t, body, n) = parse_frame(data)?;
    if n != data.len() {
        return Err(AqError::Malformed("ortiqcha bayt (transcript-injection?)"));
    }
    Ok((t, body))
}

fn need(body: &[u8], n: usize) -> Result<()> {
    if body.len() < n {
        Err(AqError::Malformed("tana qisqa"))
    } else {
        Ok(())
    }
}

/// CLIENT_HELLO tanasi.
pub struct ClientHello {
    pub versions: Vec<u16>,
    pub profiles: Vec<u8>,
    pub client_random: [u8; 32],
    pub flags: u8,
    pub ticket: Vec<u8>,
}

pub fn enc_client_hello(ch: &ClientHello) -> Vec<u8> {
    let mut b = vec![ch.versions.len() as u8];
    for v in &ch.versions {
        b.extend_from_slice(&v.to_be_bytes());
    }
    b.push(ch.profiles.len() as u8);
    b.extend_from_slice(&ch.profiles);
    b.extend_from_slice(&ch.client_random);
    b.push(ch.flags);
    b.extend_from_slice(&(ch.ticket.len() as u16).to_be_bytes());
    b.extend_from_slice(&ch.ticket);
    frame(MSG_CLIENT_HELLO, &b)
}

pub fn dec_client_hello(body: &[u8]) -> Result<ClientHello> {
    need(body, 1)?;
    let nv = body[0] as usize;
    let mut off = 1;
    need(body, off + 2 * nv)?;
    let versions = (0..nv)
        .map(|i| u16::from_be_bytes([body[off + 2 * i], body[off + 2 * i + 1]]))
        .collect();
    off += 2 * nv;
    need(body, off + 1)?;
    let np = body[off] as usize;
    off += 1;
    need(body, off + np)?;
    let profiles = body[off..off + np].to_vec();
    off += np;
    need(body, off + 32 + 1 + 2)?;
    let mut client_random = [0u8; 32];
    client_random.copy_from_slice(&body[off..off + 32]);
    off += 32;
    let flags = body[off];
    off += 1;
    let tlen = u16::from_be_bytes([body[off], body[off + 1]]) as usize;
    off += 2;
    need(body, off + tlen)?;
    Ok(ClientHello { versions, profiles, client_random, flags, ticket: body[off..off + tlen].to_vec() })
}

/// SH yadrosi (imzolanadigan qism): version(2) ‖ profile(1) ‖ srand(32) ‖ len(ek)(2) ‖ ek ‖ flags(1).
pub fn sh_core(version: u16, profile: u8, srand: &[u8; 32], ek: &[u8], flags: u8) -> Vec<u8> {
    let mut c = Vec::with_capacity(2 + 1 + 32 + 2 + ek.len() + 1);
    c.extend_from_slice(&version.to_be_bytes());
    c.push(profile);
    c.extend_from_slice(srand);
    c.extend_from_slice(&(ek.len() as u16).to_be_bytes());
    c.extend_from_slice(ek);
    c.push(flags);
    c
}

/// SERVER_HELLO tanasi: core ‖ len(sig)(2) ‖ sig.
pub fn enc_server_hello(core: &[u8], sig: &[u8]) -> Vec<u8> {
    let mut b = core.to_vec();
    b.extend_from_slice(&(sig.len() as u16).to_be_bytes());
    b.extend_from_slice(sig);
    frame(MSG_SERVER_HELLO, &b)
}

pub struct ServerHello {
    pub version: u16,
    pub profile: u8,
    pub srand: [u8; 32],
    pub ek: Vec<u8>,
    pub flags: u8,
    pub sig: Vec<u8>,
    /// Imzolangan yadro (sh_core) — imzoni tekshirish uchun.
    pub core: Vec<u8>,
}

pub fn dec_server_hello(body: &[u8]) -> Result<ServerHello> {
    need(body, 37)?;
    let version = u16::from_be_bytes([body[0], body[1]]);
    let profile = body[2];
    let mut srand = [0u8; 32];
    srand.copy_from_slice(&body[3..35]);
    let ek_len = u16::from_be_bytes([body[35], body[36]]) as usize;
    let mut off = 37;
    need(body, off + ek_len + 1)?;
    let ek = body[off..off + ek_len].to_vec();
    off += ek_len;
    let flags = body[off];
    off += 1;
    let core = sh_core(version, profile, &srand, &ek, flags);
    need(body, off + 2)?;
    let slen = u16::from_be_bytes([body[off], body[off + 1]]) as usize;
    off += 2;
    need(body, off + slen)?;
    let sig = body[off..off + slen].to_vec();
    Ok(ServerHello { version, profile, srand, ek, flags, sig, core })
}

/// CLIENT_KEX tanasi: len(ct)(2) ‖ ct.
pub fn enc_client_kex(ct: &[u8]) -> Vec<u8> {
    let mut b = (ct.len() as u16).to_be_bytes().to_vec();
    b.extend_from_slice(ct);
    frame(MSG_CLIENT_KEX, &b)
}

pub fn dec_client_kex(body: &[u8]) -> Result<Vec<u8>> {
    need(body, 2)?;
    let n = u16::from_be_bytes([body[0], body[1]]) as usize;
    need(body, 2 + n)?;
    Ok(body[2..2 + n].to_vec())
}

/// CLIENT_AUTH tanasi: len(pk)(2) ‖ pk ‖ len(sig)(2) ‖ sig.
pub fn enc_client_auth(pk: &[u8], sig: &[u8]) -> Vec<u8> {
    let mut b = (pk.len() as u16).to_be_bytes().to_vec();
    b.extend_from_slice(pk);
    b.extend_from_slice(&(sig.len() as u16).to_be_bytes());
    b.extend_from_slice(sig);
    frame(MSG_CLIENT_AUTH, &b)
}

pub fn dec_client_auth(body: &[u8]) -> Result<(Vec<u8>, Vec<u8>)> {
    need(body, 2)?;
    let pl = u16::from_be_bytes([body[0], body[1]]) as usize;
    need(body, 2 + pl + 2)?;
    let pk = body[2..2 + pl].to_vec();
    let off = 2 + pl;
    let sl = u16::from_be_bytes([body[off], body[off + 1]]) as usize;
    need(body, off + 2 + sl)?;
    Ok((pk, body[off + 2..off + 2 + sl].to_vec()))
}

/// HELLO_RETRY tanasi: difficulty(1) ‖ len(cookie)(1) ‖ cookie.
pub fn enc_hello_retry(cookie: &[u8], difficulty: u8) -> Vec<u8> {
    let mut b = vec![difficulty, cookie.len() as u8];
    b.extend_from_slice(cookie);
    frame(MSG_HELLO_RETRY, &b)
}

pub fn dec_hello_retry(body: &[u8]) -> Result<(u8, Vec<u8>)> {
    need(body, 2)?;
    let clen = body[1] as usize;
    need(body, 2 + clen)?;
    Ok((body[0], body[2..2 + clen].to_vec()))
}

/// CH_RETRY tanasi: len(cookie)(1) ‖ cookie ‖ nonce(8) ‖ len(CH)(3) ‖ CH.
pub fn enc_client_hello_retry(cookie: &[u8], nonce: u64, ch: &[u8]) -> Vec<u8> {
    let mut b = vec![cookie.len() as u8];
    b.extend_from_slice(cookie);
    b.extend_from_slice(&nonce.to_be_bytes());
    let l = ch.len() as u32;
    b.extend_from_slice(&l.to_be_bytes()[1..]);
    b.extend_from_slice(ch);
    frame(MSG_CH_RETRY, &b)
}

pub fn dec_client_hello_retry(body: &[u8]) -> Result<(Vec<u8>, u64, Vec<u8>)> {
    need(body, 1)?;
    let clen = body[0] as usize;
    need(body, 1 + clen + 8 + 3)?;
    let cookie = body[1..1 + clen].to_vec();
    let mut off = 1 + clen;
    let mut nb = [0u8; 8];
    nb.copy_from_slice(&body[off..off + 8]);
    let nonce = u64::from_be_bytes(nb);
    off += 8;
    let chl = u32::from_be_bytes([0, body[off], body[off + 1], body[off + 2]]) as usize;
    off += 3;
    need(body, off + chl)?;
    Ok((cookie, nonce, body[off..off + chl].to_vec()))
}

/// NEW_SESSION_TICKET tanasi: ttl(4) ‖ len(ticket)(2) ‖ ticket.
pub fn enc_nst(ticket: &[u8], ttl: u32) -> Vec<u8> {
    let mut b = ttl.to_be_bytes().to_vec();
    b.extend_from_slice(&(ticket.len() as u16).to_be_bytes());
    b.extend_from_slice(ticket);
    frame(MSG_NST, &b)
}

pub fn dec_nst(body: &[u8]) -> Result<(Vec<u8>, u32)> {
    need(body, 6)?;
    let ttl = u32::from_be_bytes([body[0], body[1], body[2], body[3]]);
    let tl = u16::from_be_bytes([body[4], body[5]]) as usize;
    need(body, 6 + tl)?;
    Ok((body[6..6 + tl].to_vec(), ttl))
}

/// EARLY_DATA tanasi: blob (nonce ‖ AEAD).
pub fn enc_early_data(blob: &[u8]) -> Vec<u8> {
    frame(MSG_EARLY_DATA, blob)
}

/// FINISHED: 32 baytli MAC (tanasi shu MAC).
pub fn enc_finished(mac: &[u8; 32]) -> Vec<u8> {
    frame(MSG_FINISHED, mac)
}

pub fn dec_finished(body: &[u8]) -> Result<[u8; 32]> {
    if body.len() != 32 {
        return Err(AqError::Malformed("FINISHED tanasi 32 bayt emas"));
    }
    let mut m = [0u8; 32];
    m.copy_from_slice(body);
    Ok(m)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn frame_header_layout() {
        let f = frame(MSG_FINISHED, &[1, 2, 3]);
        assert_eq!(f, vec![0x04, 0x05, 0x01, 0x00, 0x00, 0x03, 1, 2, 3]);
        let (t, body, n) = parse_frame(&f).unwrap();
        assert_eq!((t, body, n), (0x04, &[1u8, 2, 3][..], 9));
    }

    #[test]
    fn parse_exact_rejects_trailing() {
        let mut f = frame(MSG_FINISHED, &[0; 32]);
        f.push(0xFF);
        assert!(parse_exact(&f).is_err());
    }
}
