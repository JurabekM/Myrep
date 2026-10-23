//! Android Key Attestation zanjirini tekshirish (`docs/specs/pqlink.md` §4.3).
//!
//! M2 qamrovi: ECDSA P-256 / SHA-256 bilan imzolangan zanjirlar (sandbox attestatsiya CA).
//! `TODO(spec):` Google'ning haqiqiy ildizlari (RSA-4096, ECDSA P-384) M6 da qo'shiladi.

use der::{Decode, Encode};
use mpay_common::ports::SecurityLevel;
use mpay_common::tlv;
use mpay_common::DeviceId;
use p256::ecdsa::signature::Verifier;
use p256::ecdsa::{DerSignature, VerifyingKey};
use sha2::{Digest, Sha256};
use x509_cert::Certificate;

use crate::wire::{MAX_CERTS, MAX_CERT_LEN};
use crate::PqLinkError;

/// `ecdsa-with-SHA256` (1.2.840.10045.4.3.2).
const OID_ECDSA_SHA256: &str = "1.2.840.10045.4.3.2";
/// `id-ecPublicKey` (1.2.840.10045.2.1).
const OID_EC_PUBLIC_KEY: &str = "1.2.840.10045.2.1";
/// `prime256v1` (1.2.840.10045.3.1.7).
const OID_P256: &str = "1.2.840.10045.3.1.7";
/// Android Key Attestation `KeyDescription` kengaytmasi.
pub const OID_KEY_DESCRIPTION: &str = "1.3.6.1.4.1.11129.2.1.17";

fn att(msg: impl Into<String>) -> PqLinkError {
    PqLinkError::Attestation(msg.into())
}

/// Ishonchli ildiz sertifikatlari.
#[derive(Clone, Default)]
pub struct TrustAnchors {
    roots: Vec<Certificate>,
}

impl std::fmt::Debug for TrustAnchors {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "TrustAnchors({} ildiz)", self.roots.len())
    }
}

impl TrustAnchors {
    /// DER sertifikatlardan.
    pub fn from_der(certs: &[Vec<u8>]) -> Result<Self, PqLinkError> {
        let roots = certs
            .iter()
            .map(|c| Certificate::from_der(c).map_err(|_| att("ildiz sertifikati DER xatosi")))
            .collect::<Result<_, _>>()?;
        Ok(Self { roots })
    }

    /// PEM fayl matnidan (bir yoki bir nechta sertifikat).
    pub fn from_pem(pem: &str) -> Result<Self, PqLinkError> {
        let roots =
            Certificate::load_pem_chain(pem.as_bytes()).map_err(|_| att("ildiz PEM xatosi"))?;
        Ok(Self { roots })
    }

    pub fn len(&self) -> usize {
        self.roots.len()
    }

    pub fn is_empty(&self) -> bool {
        self.roots.is_empty()
    }
}

/// Attestatsiya siyosati.
#[derive(Debug, Clone)]
pub struct AttestationPolicy {
    /// Minimal xavfsizlik darajasi (production: StrongBox).
    pub min_security_level: SecurityLevel,
}

impl Default for AttestationPolicy {
    fn default() -> Self {
        Self {
            min_security_level: SecurityLevel::StrongBox,
        }
    }
}

/// Tekshirilgan qurilma.
#[derive(Clone)]
pub struct VerifiedDevice {
    pub device_id: DeviceId,
    pub security_level: SecurityLevel,
    pub attestation_challenge: Vec<u8>,
    pub verifying_key: VerifyingKey,
}

impl std::fmt::Debug for VerifiedDevice {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("VerifiedDevice")
            .field("device_id", &self.device_id)
            .field("security_level", &self.security_level)
            .finish()
    }
}

impl VerifiedDevice {
    /// Qurilma imzosini (DER ECDSA P-256/SHA-256) tekshiradi.
    pub fn verify_signature(&self, msg: &[u8], der_sig: &[u8]) -> Result<(), PqLinkError> {
        let sig = DerSignature::try_from(der_sig).map_err(|_| PqLinkError::BadDeviceSignature)?;
        self.verifying_key
            .verify(msg, &sig)
            .map_err(|_| PqLinkError::BadDeviceSignature)
    }
}

/// KeyDescription'dan kerakli maydonlar.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct KeyDescription {
    pub attestation_version: u32,
    pub attestation_security_level: SecurityLevel,
    pub keymint_security_level: SecurityLevel,
    pub attestation_challenge: Vec<u8>,
}

fn small_uint(b: &[u8]) -> Option<u32> {
    // DER INTEGER: manfiy emas (yuqori bit 0), belgi bayti 0x00 olib tashlangach 1–4 bayt.
    if b.is_empty() || b[0] & 0x80 != 0 {
        return None;
    }
    let b = match b {
        [0, rest @ ..] if !rest.is_empty() => rest,
        _ => b,
    };
    if b.len() > 4 {
        return None;
    }
    Some(b.iter().fold(0u32, |a, x| (a << 8) | u32::from(*x)))
}

/// KeyDescription (DER) ni tahlil qiladi — bizning BER-TLV parserimiz DER'ning ustki to'plamini o'qiydi.
pub fn parse_key_description(der: &[u8]) -> Result<KeyDescription, PqLinkError> {
    let list = tlv::parse_all(der).map_err(|_| att("KeyDescription DER"))?;
    let [seq] = list.as_slice() else {
        return Err(att("KeyDescription: bitta SEQUENCE kutilgan"));
    };
    if seq.tag.0 != 0x30 {
        return Err(att("KeyDescription: SEQUENCE emas"));
    }
    let c = seq.children();
    if c.len() < 8 {
        return Err(att("KeyDescription: maydonlar yetarli emas"));
    }
    let want = |i: usize, tag: u32| -> Result<&[u8], PqLinkError> {
        if c[i].tag.0 != tag {
            return Err(att(format!("KeyDescription: {i}-maydon turi")));
        }
        c[i].bytes()
            .ok_or_else(|| att("KeyDescription: primitiv kutilgan"))
    };
    let level = |b: &[u8]| {
        small_uint(b)
            .and_then(|v| u8::try_from(v).ok())
            .and_then(SecurityLevel::from_raw)
            .ok_or_else(|| att("KeyDescription: noma'lum SecurityLevel"))
    };
    Ok(KeyDescription {
        attestation_version: small_uint(want(0, 0x02)?).ok_or_else(|| att("attestationVersion"))?,
        attestation_security_level: level(want(1, 0x0A)?)?,
        keymint_security_level: level(want(3, 0x0A)?)?,
        attestation_challenge: want(4, 0x04)?.to_vec(),
    })
}

fn p256_key(cert: &Certificate) -> Result<VerifyingKey, PqLinkError> {
    let spki = cert.tbs_certificate().subject_public_key_info();
    if spki.algorithm.oid.to_string() != OID_EC_PUBLIC_KEY {
        return Err(att("ochiq kalit EC emas"));
    }
    let curve = spki
        .algorithm
        .parameters
        .as_ref()
        .and_then(|p| p.decode_as::<der::asn1::ObjectIdentifier>().ok())
        .map(|o| o.to_string());
    if curve.as_deref() != Some(OID_P256) {
        return Err(att("egri chiziq P-256 emas (TODO(spec): P-384, RSA — M6)"));
    }
    let bits = spki
        .subject_public_key
        .as_bytes()
        .ok_or_else(|| att("ochiq kalit bitlari"))?;
    VerifyingKey::from_sec1_bytes(bits).map_err(|_| att("P-256 nuqtasi yaroqsiz"))
}

fn verify_signed_by(cert: &Certificate, issuer_key: &VerifyingKey) -> Result<(), PqLinkError> {
    if cert.signature_algorithm().oid.to_string() != OID_ECDSA_SHA256 {
        return Err(att("imzo algoritmi ecdsa-with-SHA256 emas"));
    }
    let tbs = cert
        .tbs_certificate()
        .to_der()
        .map_err(|_| att("TBS DER"))?;
    let sig = cert
        .signature()
        .as_bytes()
        .ok_or_else(|| att("imzo bitlari"))?;
    let sig = DerSignature::try_from(sig).map_err(|_| att("imzo DER"))?;
    issuer_key
        .verify(&tbs, &sig)
        .map_err(|_| att("sertifikat imzosi noto'g'ri"))
}

fn check_validity(cert: &Certificate, now_unix: i64) -> Result<(), PqLinkError> {
    let v = cert.tbs_certificate().validity();
    let nb = v.not_before.to_unix_duration().as_secs() as i64;
    let na = v.not_after.to_unix_duration().as_secs() as i64;
    if now_unix < nb || now_unix > na {
        return Err(att("sertifikat amal qilish muddatidan tashqarida"));
    }
    Ok(())
}

/// Zanjirni tekshiradi: `chain[0]` — leaf (qurilma kaliti), oxirgisi ildizga bog'lanadi.
pub fn verify_chain(
    chain: &[Vec<u8>],
    anchors: &TrustAnchors,
    policy: &AttestationPolicy,
    now_unix: i64,
) -> Result<VerifiedDevice, PqLinkError> {
    if chain.is_empty() || chain.len() > MAX_CERTS {
        return Err(att("zanjir uzunligi"));
    }
    if anchors.is_empty() {
        return Err(att("ishonchli ildizlar sozlanmagan"));
    }
    let certs = chain
        .iter()
        .map(|c| {
            if c.len() > MAX_CERT_LEN {
                return Err(att("sertifikat juda katta"));
            }
            Certificate::from_der(c).map_err(|_| att("sertifikat DER xatosi"))
        })
        .collect::<Result<Vec<_>, _>>()?;

    for c in &certs {
        check_validity(c, now_unix)?;
    }
    for pair in certs.windows(2) {
        if pair[0].tbs_certificate().issuer() != pair[1].tbs_certificate().subject() {
            return Err(att("issuer/subject mos emas"));
        }
        verify_signed_by(&pair[0], &p256_key(&pair[1])?)?;
    }

    // Oxirgi sertifikat — ishonchli ildizning o'zi yoki u tomonidan imzolangan.
    let last = certs.last().ok_or_else(|| att("bo'sh zanjir"))?;
    let anchored = anchors.roots.iter().any(|root| {
        if root == last {
            return true;
        }
        root.tbs_certificate().subject() == last.tbs_certificate().issuer()
            && check_validity(root, now_unix).is_ok()
            && p256_key(root)
                .and_then(|k| verify_signed_by(last, &k))
                .is_ok()
    });
    if !anchored {
        return Err(att("zanjir ishonchli ildizga bog'lanmagan"));
    }

    let leaf = &certs[0];
    let ext = leaf
        .tbs_certificate()
        .extensions()
        .and_then(|exts| {
            exts.iter()
                .find(|e| e.extn_id.to_string() == OID_KEY_DESCRIPTION)
        })
        .ok_or_else(|| att("leaf'da KeyDescription kengaytmasi yo'q"))?;
    let kd = parse_key_description(ext.extn_value.as_bytes())?;
    let level = kd.attestation_security_level.min(kd.keymint_security_level);
    if level < policy.min_security_level {
        return Err(att(format!(
            "xavfsizlik darajasi {level:?} < {:?}",
            policy.min_security_level
        )));
    }

    let spki_der = leaf
        .tbs_certificate()
        .subject_public_key_info()
        .to_der()
        .map_err(|_| att("SPKI DER"))?;
    Ok(VerifiedDevice {
        device_id: DeviceId(Sha256::digest(&spki_der).into()),
        security_level: level,
        attestation_challenge: kd.attestation_challenge,
        verifying_key: p256_key(leaf)?,
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    use mpay_common::tlv::Tlv;

    fn kd(level: u8) -> Vec<u8> {
        Tlv::constructed(
            0x30,
            vec![
                Tlv::primitive(0x02, vec![0x01, 0x2C]),
                Tlv::primitive(0x0A, vec![level]),
                Tlv::primitive(0x02, vec![0x01, 0x2C]),
                Tlv::primitive(0x0A, vec![level]),
                Tlv::primitive(0x04, b"challenge".to_vec()),
                Tlv::primitive(0x04, vec![]),
                Tlv::constructed(0x30, vec![]),
                Tlv::constructed(
                    0x30,
                    vec![Tlv::constructed(
                        0xBF853D,
                        vec![Tlv::primitive(0x02, vec![1])],
                    )],
                ),
            ],
        )
        .to_bytes()
    }

    #[test]
    fn key_description_parse() {
        let k = parse_key_description(&kd(2)).unwrap();
        assert_eq!(k.attestation_version, 300);
        assert_eq!(k.attestation_security_level, SecurityLevel::StrongBox);
        assert_eq!(k.attestation_challenge, b"challenge");
        assert!(parse_key_description(&kd(7)).is_err());
        assert!(parse_key_description(&[0x30, 0x00]).is_err());
        assert!(parse_key_description(b"garbage").is_err());
    }

    #[test]
    fn small_uint_cases() {
        assert_eq!(small_uint(&[0x01, 0x2C]), Some(300));
        assert_eq!(small_uint(&[0x00, 0xFF]), Some(255));
        assert_eq!(small_uint(&[0xFF]), None);
        assert_eq!(small_uint(&[]), None);
        assert_eq!(small_uint(&[1, 2, 3, 4, 5]), None);
    }
}
