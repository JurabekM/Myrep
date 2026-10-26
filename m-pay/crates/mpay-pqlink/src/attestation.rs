//! Android Key Attestation zanjirini tekshirish (`docs/specs/pqlink.md` §4.3).
//!
//! Imzolovchilar: ECDSA P-256/P-384 (SHA-256/384) va RSA (SHA-256) — Google RSA-4096 va
//! "Key Attestation CA1" (P-384) ildizlari; qurilma (leaf) kaliti faqat P-256.

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
/// `ecdsa-with-SHA384` (1.2.840.10045.4.3.3) — Google "Key Attestation CA1" (P-384).
const OID_ECDSA_SHA384: &str = "1.2.840.10045.4.3.3";
/// `sha256WithRSAEncryption` (1.2.840.113549.1.1.11) — Google RSA-4096 ildizi.
const OID_RSA_SHA256: &str = "1.2.840.113549.1.1.11";
/// `rsaEncryption` (1.2.840.113549.1.1.1).
const OID_RSA: &str = "1.2.840.113549.1.1.1";
/// `secp384r1` (1.3.132.0.34).
const OID_P384: &str = "1.3.132.0.34";
/// `id-ecPublicKey` (1.2.840.10045.2.1).
const OID_EC_PUBLIC_KEY: &str = "1.2.840.10045.2.1";
/// `prime256v1` (1.2.840.10045.3.1.7).
const OID_P256: &str = "1.2.840.10045.3.1.7";
/// Android Key Attestation `KeyDescription` kengaytmasi.
pub const OID_KEY_DESCRIPTION: &str = "1.3.6.1.4.1.11129.2.1.17";
/// `basicConstraints` (2.5.29.19).
const OID_BASIC_CONSTRAINTS: &str = "2.5.29.19";

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
    /// Apparat kafolatlagan `rootOfTrust` talab qilinadi: `verifiedBootState = Verified` va
    /// `deviceLocked = true` (bootloader ochilgan yoki o'zgartirilgan proshivkali qurilma rad etiladi).
    /// Faqat emulyator sinovida `false` (emulyatorda apparat RoT yo'q).
    pub require_verified_boot: bool,
}

impl Default for AttestationPolicy {
    fn default() -> Self {
        Self {
            min_security_level: SecurityLevel::StrongBox,
            require_verified_boot: true,
        }
    }
}

/// `RootOfTrust.verifiedBootState`.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum VerifiedBootState {
    Verified,
    SelfSigned,
    Unverified,
    Failed,
}

impl VerifiedBootState {
    fn from_raw(v: u32) -> Option<Self> {
        Some(match v {
            0 => Self::Verified,
            1 => Self::SelfSigned,
            2 => Self::Unverified,
            3 => Self::Failed,
            _ => return None,
        })
    }
}

/// Apparat (`hardwareEnforced`) ro'yxatidagi `RootOfTrust` (`[704]`).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct RootOfTrust {
    pub device_locked: bool,
    pub verified_boot_state: VerifiedBootState,
}

/// `AuthorizationList` dagi `rootOfTrust [704] EXPLICIT` tegi (BER: `BF 85 40`).
const TAG_ROOT_OF_TRUST: u32 = 0xBF_85_40;

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
    /// `hardwareEnforced.rootOfTrust` (bo'lmasa `None` — masalan, dasturiy Keystore).
    pub root_of_trust: Option<RootOfTrust>,
}

/// `hardwareEnforced` AuthorizationList'dan `rootOfTrust` ni o'qiydi.
fn parse_root_of_trust(list: &tlv::Tlv) -> Result<Option<RootOfTrust>, PqLinkError> {
    let Some(rot) = list
        .children()
        .iter()
        .find(|t| t.tag.0 == TAG_ROOT_OF_TRUST)
    else {
        return Ok(None);
    };
    let [seq] = rot.children() else {
        return Err(att("rootOfTrust: SEQUENCE kutilgan"));
    };
    let f = seq.children();
    if seq.tag.0 != 0x30 || f.len() < 3 || f[1].tag.0 != 0x01 || f[2].tag.0 != 0x0A {
        return Err(att("rootOfTrust: maydonlar"));
    }
    let locked = f[1]
        .bytes()
        .ok_or_else(|| att("rootOfTrust: deviceLocked"))?;
    let state = f[2]
        .bytes()
        .and_then(small_uint)
        .and_then(VerifiedBootState::from_raw)
        .ok_or_else(|| att("rootOfTrust: verifiedBootState"))?;
    Ok(Some(RootOfTrust {
        device_locked: matches!(locked, [b] if *b != 0),
        verified_boot_state: state,
    }))
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
        root_of_trust: if c[7].tag.0 == 0x30 {
            parse_root_of_trust(&c[7])?
        } else {
            return Err(att("KeyDescription: hardwareEnforced SEQUENCE emas"));
        },
    })
}

/// `basicConstraints` (2.5.29.19) `cA = true` bormi.
fn is_ca(cert: &Certificate) -> bool {
    use x509_cert::ext::pkix::BasicConstraints;
    cert.tbs_certificate()
        .extensions()
        .and_then(|exts| {
            exts.iter()
                .find(|e| e.extn_id.to_string() == OID_BASIC_CONSTRAINTS)
        })
        .and_then(|e| BasicConstraints::from_der(e.extn_value.as_bytes()).ok())
        .is_some_and(|bc| bc.ca)
}

fn has_key_description(cert: &Certificate) -> bool {
    cert.tbs_certificate().extensions().is_some_and(|exts| {
        exts.iter()
            .any(|e| e.extn_id.to_string() == OID_KEY_DESCRIPTION)
    })
}

/// Zanjirdagi imzolovchi (issuer) kaliti.
enum IssuerKey {
    P256(VerifyingKey),
    P384(p384::ecdsa::VerifyingKey),
    Rsa(rsa::RsaPublicKey),
}

fn spki_bits(cert: &Certificate) -> Result<&[u8], PqLinkError> {
    cert.tbs_certificate()
        .subject_public_key_info()
        .subject_public_key
        .as_bytes()
        .ok_or_else(|| att("ochiq kalit bitlari"))
}

fn ec_curve(cert: &Certificate) -> Option<String> {
    cert.tbs_certificate()
        .subject_public_key_info()
        .algorithm
        .parameters
        .as_ref()
        .and_then(|p| p.decode_as::<der::asn1::ObjectIdentifier>().ok())
        .map(|o| o.to_string())
}

/// Qurilma (leaf) kaliti — faqat P-256 (StrongBox ECDSA).
fn p256_key(cert: &Certificate) -> Result<VerifyingKey, PqLinkError> {
    let spki = cert.tbs_certificate().subject_public_key_info();
    if spki.algorithm.oid.to_string() != OID_EC_PUBLIC_KEY
        || ec_curve(cert).as_deref() != Some(OID_P256)
    {
        return Err(att("qurilma kaliti EC P-256 emas"));
    }
    VerifyingKey::from_sec1_bytes(spki_bits(cert)?).map_err(|_| att("P-256 nuqtasi yaroqsiz"))
}

/// Oraliq va ildiz sertifikatlar kaliti: P-256, P-384 yoki RSA.
fn issuer_key(cert: &Certificate) -> Result<IssuerKey, PqLinkError> {
    let alg = cert
        .tbs_certificate()
        .subject_public_key_info()
        .algorithm
        .oid
        .to_string();
    match (alg.as_str(), ec_curve(cert).as_deref()) {
        (OID_EC_PUBLIC_KEY, Some(OID_P256)) => Ok(IssuerKey::P256(p256_key(cert)?)),
        (OID_EC_PUBLIC_KEY, Some(OID_P384)) => {
            p384::ecdsa::VerifyingKey::from_sec1_bytes(spki_bits(cert)?)
                .map(IssuerKey::P384)
                .map_err(|_| att("P-384 nuqtasi yaroqsiz"))
        }
        (OID_RSA, _) => {
            use rsa::pkcs1::DecodeRsaPublicKey;
            let k = rsa::RsaPublicKey::from_pkcs1_der(spki_bits(cert)?)
                .map_err(|_| att("RSA ochiq kaliti"))?;
            if rsa::traits::PublicKeyParts::size(&k) < 256 {
                return Err(att("RSA kaliti 2048 bitdan qisqa"));
            }
            Ok(IssuerKey::Rsa(k))
        }
        _ => Err(att(
            "qo'llab-quvvatlanmaydigan imzolovchi kaliti (P-256, P-384, RSA kutilgan)",
        )),
    }
}

fn verify_signed_by(cert: &Certificate, issuer: &IssuerKey) -> Result<(), PqLinkError> {
    use p256::ecdsa::signature::hazmat::PrehashVerifier;
    let tbs = cert
        .tbs_certificate()
        .to_der()
        .map_err(|_| att("TBS DER"))?;
    let sig = cert
        .signature()
        .as_bytes()
        .ok_or_else(|| att("imzo bitlari"))?;
    let alg = cert.signature_algorithm().oid.to_string();
    let bad = || att("sertifikat imzosi noto'g'ri");
    let digest: Vec<u8> = match alg.as_str() {
        OID_ECDSA_SHA256 | OID_RSA_SHA256 => Sha256::digest(&tbs).to_vec(),
        OID_ECDSA_SHA384 => sha2::Sha384::digest(&tbs).to_vec(),
        _ => {
            return Err(att(
                "imzo algoritmi qo'llab-quvvatlanmaydi (ECDSA-SHA256/384, RSA-SHA256)",
            ))
        }
    };
    match (issuer, alg.as_str()) {
        (IssuerKey::P256(k), OID_ECDSA_SHA256 | OID_ECDSA_SHA384) => {
            let s = p256::ecdsa::Signature::from_der(sig).map_err(|_| att("imzo DER"))?;
            k.verify_prehash(&digest, &s).map_err(|_| bad())
        }
        (IssuerKey::P384(k), OID_ECDSA_SHA256 | OID_ECDSA_SHA384) => {
            let s = p384::ecdsa::Signature::from_der(sig).map_err(|_| att("imzo DER"))?;
            k.verify_prehash(&digest, &s).map_err(|_| bad())
        }
        (IssuerKey::Rsa(k), OID_RSA_SHA256) => k
            .verify(rsa::Pkcs1v15Sign::new::<sha2_010::Sha256>(), &digest, sig)
            .map_err(|_| bad()),
        _ => Err(att("imzo algoritmi va kalit turi mos emas")),
    }
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
    // Zanjirni "uzaytirish" hujumiga qarshi: haqiqiy attestatsiya qilingan kalit (u istalgan baytni
    // imzolay oladi) o'z ostida soxta leaf (soxta KeyDescription — StrongBox, istalgan challenge) chiqara
    // olmasin. Har bir imzolovchi CA bo'lishi va KeyDescription faqat leaf'da bo'lishi shart.
    for c in &certs[1..] {
        if !is_ca(c) {
            return Err(att("zanjirdagi imzolovchi CA emas (basicConstraints)"));
        }
        if has_key_description(c) {
            return Err(att("KeyDescription leaf'dan boshqa sertifikatda"));
        }
    }
    for pair in certs.windows(2) {
        if pair[0].tbs_certificate().issuer() != pair[1].tbs_certificate().subject() {
            return Err(att("issuer/subject mos emas"));
        }
        verify_signed_by(&pair[0], &issuer_key(&pair[1])?)?;
    }

    // Oxirgi sertifikat — ishonchli ildizning o'zi yoki u tomonidan imzolangan.
    let last = certs.last().ok_or_else(|| att("bo'sh zanjir"))?;
    let anchored = anchors.roots.iter().any(|root| {
        if root == last {
            return true;
        }
        root.tbs_certificate().subject() == last.tbs_certificate().issuer()
            && check_validity(root, now_unix).is_ok()
            && issuer_key(root)
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
    if policy.require_verified_boot {
        match kd.root_of_trust {
            Some(RootOfTrust {
                device_locked: true,
                verified_boot_state: VerifiedBootState::Verified,
            }) => {}
            // TODO(spec): `SelfSigned` (foydalanuvchi kaliti bilan qulflangan maxsus proshivka) —
            // pilot bank siyosati bo'yicha `verifiedBootKey` ruxsat ro'yxati bilan.
            Some(r) => {
                return Err(att(format!(
                    "qurilma ishonchli emas: verifiedBootState {:?}, deviceLocked {}",
                    r.verified_boot_state, r.device_locked
                )))
            }
            None => return Err(att("apparat rootOfTrust yo'q")),
        }
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
