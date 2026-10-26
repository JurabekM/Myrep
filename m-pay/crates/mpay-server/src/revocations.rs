//! Bekor qilingan server identifikatorlari ro'yxati fayli (ADR-0014): JSON ↔ `SignedRevocations`.
//! Server ro'yxatni faqat tarqatadi; imzo oflayn ildiz kalitida (`mpay-server revoke`).

use mpay_common::api::RevocationsDto;
use mpay_pqlink::revocation::SignedRevocations;
use mpay_pqlink::ServerIdentity;

pub const FORMAT: &str = "mpay-pqlink-revocations/1";

fn h32(s: &str) -> Result<[u8; 32], String> {
    let mut b = [0u8; 32];
    hex::decode_to_slice(s, &mut b).map_err(|_| format!("32 bayt hex kutilgan: {s}"))?;
    Ok(b)
}

pub fn to_dto(s: &SignedRevocations) -> RevocationsDto {
    RevocationsDto {
        format: FORMAT.into(),
        version: s.version,
        revoked: s.revoked.iter().map(hex::encode).collect(),
        root_ed25519: hex::encode(s.root.ed25519),
        root_mldsa65: hex::encode(&s.root.mldsa65),
        sig_ed25519: hex::encode(s.sig_ed25519),
        sig_mldsa65: hex::encode(&s.sig_mldsa65),
    }
}

pub fn from_dto(d: &RevocationsDto) -> Result<SignedRevocations, String> {
    if d.format != FORMAT {
        return Err(format!("noma'lum format: {}", d.format));
    }
    let mut sig = [0u8; 64];
    hex::decode_to_slice(&d.sig_ed25519, &mut sig).map_err(|_| "sig_ed25519".to_owned())?;
    Ok(SignedRevocations {
        version: d.version,
        revoked: d.revoked.iter().map(|s| h32(s)).collect::<Result<_, _>>()?,
        root: ServerIdentity::new(
            h32(&d.root_ed25519)?,
            hex::decode(&d.root_mldsa65).map_err(|_| "root_mldsa65".to_owned())?,
        )
        .map_err(|e| e.to_string())?,
        sig_ed25519: sig,
        sig_mldsa65: hex::decode(&d.sig_mldsa65).map_err(|_| "sig_mldsa65".to_owned())?,
    })
}
