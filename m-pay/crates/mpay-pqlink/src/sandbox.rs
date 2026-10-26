//! Sandbox attestatsiya CA va dasturiy qurilma kaliti (`sandbox-attestation` feature).
//!
//! **Faqat sandbox va testlar uchun.** Haqiqiy Android Key Attestation'ni simulyatsiya qiladi:
//! leaf sertifikatda `KeyDescription` kengaytmasi (`1.3.6.1.4.1.11129.2.1.17`) bo'ladi.
//! Production'da ishonchli ildizlar — Google attestatsiya ildizlari (M6).

use mpay_common::ports::SecurityLevel;
use mpay_common::tlv::Tlv;
use p256::ecdsa::signature::Signer;
use p256::ecdsa::{DerSignature, SigningKey};
use p256::pkcs8::DecodePrivateKey;
use rcgen::{
    BasicConstraints, CertificateParams, CustomExtension, DistinguishedName, DnType, IsCa, Issuer,
    KeyPair, KeyUsagePurpose, PKCS_ECDSA_P256_SHA256,
};
use time::{Duration, OffsetDateTime};
use zeroize::Zeroizing;

use crate::attestation::TrustAnchors;
use crate::device::DeviceSigner;
use crate::PqLinkError;

const CA_CN: &str = "M-Pay Sandbox Attestation Root";
const CA_ORG: &str = "M-Pay Sandbox (TEST ONLY)";
const KEY_DESCRIPTION_OID: &[u64] = &[1, 3, 6, 1, 4, 1, 11129, 2, 1, 17];

fn err(e: impl std::fmt::Display) -> PqLinkError {
    PqLinkError::Crypto(format!("sandbox CA: {e}"))
}

fn ca_params() -> CertificateParams {
    let mut p = CertificateParams::default();
    let mut dn = DistinguishedName::new();
    dn.push(DnType::CommonName, CA_CN);
    dn.push(DnType::OrganizationName, CA_ORG);
    p.distinguished_name = dn;
    p.is_ca = IsCa::Ca(BasicConstraints::Unconstrained);
    p.key_usages = vec![KeyUsagePurpose::KeyCertSign, KeyUsagePurpose::CrlSign];
    p.not_before = OffsetDateTime::now_utc() - Duration::days(1);
    p.not_after = OffsetDateTime::now_utc() + Duration::days(365 * 20);
    p
}

/// Sandbox `rootOfTrust`: `(deviceLocked, verifiedBootState)`; `None` — kengaytmada yo'q.
pub type SandboxRootOfTrust = Option<(bool, u8)>;

/// Haqiqiy qulflangan, tekshirilgan yuklashli qurilma (`Verified`, `deviceLocked = true`).
pub const ROT_VERIFIED: SandboxRootOfTrust = Some((true, 0));

/// Android KeyMint `KeyDescription` (soddalashtirilgan): `hardwareEnforced` da faqat `rootOfTrust`.
pub fn key_description_der(level: SecurityLevel, challenge: &[u8]) -> Vec<u8> {
    key_description_der_with(level, challenge, ROT_VERIFIED)
}

/// `rootOfTrust` ni tanlab (testlar: ochiq bootloader, RoT'siz).
pub fn key_description_der_with(
    level: SecurityLevel,
    challenge: &[u8],
    rot: SandboxRootOfTrust,
) -> Vec<u8> {
    let lvl = level as u8;
    let hw = match rot {
        Some((locked, state)) => vec![Tlv::constructed(
            0xBF_85_40,
            vec![Tlv::constructed(
                0x30,
                vec![
                    Tlv::primitive(0x04, vec![0; 32]), // verifiedBootKey
                    Tlv::primitive(0x01, vec![if locked { 0xFF } else { 0x00 }]),
                    Tlv::primitive(0x0A, vec![state]),
                    Tlv::primitive(0x04, vec![0; 32]), // verifiedBootHash
                ],
            )],
        )],
        None => vec![],
    };
    Tlv::constructed(
        0x30,
        vec![
            Tlv::primitive(0x02, vec![0x01, 0x2C]), // attestationVersion = 300 (KeyMint 3)
            Tlv::primitive(0x0A, vec![lvl]),
            Tlv::primitive(0x02, vec![0x01, 0x2C]), // keyMintVersion = 300
            Tlv::primitive(0x0A, vec![lvl]),
            Tlv::primitive(0x04, challenge.to_vec()),
            Tlv::primitive(0x04, vec![]),
            Tlv::constructed(0x30, vec![]),
            Tlv::constructed(0x30, hw),
        ],
    )
    .to_bytes()
}

/// Sandbox attestatsiya ildiz CA'si.
pub struct SandboxAttestationCa {
    key: KeyPair,
    cert_der: Vec<u8>,
}

impl std::fmt::Debug for SandboxAttestationCa {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str("SandboxAttestationCa(<maxfiy kalit>)")
    }
}

impl SandboxAttestationCa {
    /// Yangi CA.
    pub fn generate() -> Result<Self, PqLinkError> {
        let key = KeyPair::generate_for(&PKCS_ECDSA_P256_SHA256).map_err(err)?;
        let cert = ca_params().self_signed(&key).map_err(err)?;
        Ok(Self {
            key,
            cert_der: cert.der().to_vec(),
        })
    }

    /// Saqlangan CA'ni tiklaydi (kalit PEM + ildiz DER).
    pub fn from_parts(key_pem: &str, cert_der: Vec<u8>) -> Result<Self, PqLinkError> {
        let key = KeyPair::from_pem(key_pem).map_err(err)?;
        Ok(Self { key, cert_der })
    }

    /// CA kaliti PEM (faqat sandbox katalogiga, git'ga tushmaydi).
    pub fn key_pem(&self) -> Zeroizing<String> {
        Zeroizing::new(self.key.serialize_pem())
    }

    pub fn root_der(&self) -> &[u8] {
        &self.cert_der
    }

    pub fn anchors(&self) -> Result<TrustAnchors, PqLinkError> {
        TrustAnchors::from_der(std::slice::from_ref(&self.cert_der))
    }

    /// Yangi qurilma kaliti va unga attestatsiya sertifikati.
    pub fn issue_device(
        &self,
        level: SecurityLevel,
        challenge: &[u8],
    ) -> Result<SoftDeviceKey, PqLinkError> {
        self.issue_device_with(level, challenge, ROT_VERIFIED)
    }

    /// `rootOfTrust` ni tanlab (testlar).
    pub fn issue_device_with(
        &self,
        level: SecurityLevel,
        challenge: &[u8],
        rot: SandboxRootOfTrust,
    ) -> Result<SoftDeviceKey, PqLinkError> {
        let leaf_key = KeyPair::generate_for(&PKCS_ECDSA_P256_SHA256).map_err(err)?;
        let mut p = CertificateParams::default();
        let mut dn = DistinguishedName::new();
        dn.push(DnType::CommonName, "Android Keystore Key");
        p.distinguished_name = dn;
        p.not_before = OffsetDateTime::now_utc() - Duration::days(1);
        p.not_after = OffsetDateTime::now_utc() + Duration::days(365 * 10);
        p.key_usages = vec![KeyUsagePurpose::DigitalSignature];
        p.custom_extensions = vec![CustomExtension::from_oid_content(
            KEY_DESCRIPTION_OID,
            key_description_der_with(level, challenge, rot),
        )];
        let issuer = Issuer::new(ca_params(), &self.key);
        let leaf = p.signed_by(&leaf_key, &issuer).map_err(err)?;
        let pkcs8 = Zeroizing::new(leaf_key.serialize_der());
        let sk = SigningKey::from_pkcs8_der(&pkcs8).map_err(err)?;
        Ok(SoftDeviceKey {
            sk,
            chain: vec![leaf.der().to_vec(), self.cert_der.clone()],
        })
    }
}

/// Saqlanadigan qurilma kaliti: `(PKCS#8 DER kalit, sertifikat zanjiri)`.
pub type DeviceKeyParts = (Zeroizing<Vec<u8>>, Vec<Vec<u8>>);

/// Dasturiy qurilma kaliti (soft-wallet). Android'dagi StrongBox kalitining sandbox o'rinbosari.
#[derive(Clone)]
pub struct SoftDeviceKey {
    sk: SigningKey,
    chain: Vec<Vec<u8>>,
}

impl std::fmt::Debug for SoftDeviceKey {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "SoftDeviceKey({} sertifikat)", self.chain.len())
    }
}

impl SoftDeviceKey {
    /// Saqlash uchun: PKCS#8 DER kalit va zanjir.
    pub fn to_parts(&self) -> Result<DeviceKeyParts, PqLinkError> {
        use p256::pkcs8::EncodePrivateKey;
        let der = self.sk.to_pkcs8_der().map_err(err)?;
        Ok((Zeroizing::new(der.as_bytes().to_vec()), self.chain.clone()))
    }

    pub fn from_parts(pkcs8_der: &[u8], chain: Vec<Vec<u8>>) -> Result<Self, PqLinkError> {
        Ok(Self {
            sk: SigningKey::from_pkcs8_der(pkcs8_der).map_err(err)?,
            chain,
        })
    }
}

impl DeviceSigner for SoftDeviceKey {
    fn cert_chain(&self) -> Vec<Vec<u8>> {
        self.chain.clone()
    }

    fn sign(&self, msg: &[u8]) -> Result<Vec<u8>, PqLinkError> {
        let sig: DerSignature = self.sk.sign(msg);
        Ok(sig.as_bytes().to_vec())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::attestation::{verify_chain, AttestationPolicy};

    fn now() -> i64 {
        OffsetDateTime::now_utc().unix_timestamp()
    }

    #[test]
    fn issued_chain_verifies() {
        let ca = SandboxAttestationCa::generate().unwrap();
        let dev = ca
            .issue_device(SecurityLevel::StrongBox, b"enroll-1")
            .unwrap();
        let v = verify_chain(
            &dev.cert_chain(),
            &ca.anchors().unwrap(),
            &AttestationPolicy::default(),
            now(),
        )
        .unwrap();
        assert_eq!(v.security_level, SecurityLevel::StrongBox);
        assert_eq!(v.attestation_challenge, b"enroll-1");
        let sig = dev.sign(b"hello").unwrap();
        v.verify_signature(b"hello", &sig).unwrap();
        assert!(v.verify_signature(b"hellO", &sig).is_err());

        // Faqat leaf (ildizsiz) ham ildizga bog'lanadi.
        assert!(verify_chain(
            &dev.cert_chain()[..1],
            &ca.anchors().unwrap(),
            &AttestationPolicy::default(),
            now()
        )
        .is_ok());
    }

    #[test]
    fn policy_and_foreign_root_rejected() {
        let ca = SandboxAttestationCa::generate().unwrap();
        let other = SandboxAttestationCa::generate().unwrap();
        let tee = ca
            .issue_device(SecurityLevel::TrustedEnvironment, b"")
            .unwrap();
        let pol = AttestationPolicy::default();
        assert!(verify_chain(&tee.cert_chain(), &ca.anchors().unwrap(), &pol, now()).is_err());
        let relaxed = AttestationPolicy {
            min_security_level: SecurityLevel::TrustedEnvironment,
            ..AttestationPolicy::default()
        };
        assert!(verify_chain(&tee.cert_chain(), &ca.anchors().unwrap(), &relaxed, now()).is_ok());
        // Boshqa CA bergan zanjir.
        let foreign = other.issue_device(SecurityLevel::StrongBox, b"").unwrap();
        assert!(verify_chain(&foreign.cert_chain(), &ca.anchors().unwrap(), &pol, now()).is_err());
        // Muddatidan tashqari vaqt.
        let sb = ca.issue_device(SecurityLevel::StrongBox, b"").unwrap();
        assert!(verify_chain(
            &sb.cert_chain(),
            &ca.anchors().unwrap(),
            &pol,
            now() + 400 * 86_400 * 30
        )
        .is_err());
    }

    #[test]
    fn unlocked_or_unverified_boot_rejected() {
        let ca = SandboxAttestationCa::generate().unwrap();
        let anchors = ca.anchors().unwrap();
        let pol = AttestationPolicy::default();
        for rot in [
            Some((false, 0)),
            Some((true, 2)),
            Some((true, 1)),
            Some((true, 3)),
            None,
        ] {
            let d = ca
                .issue_device_with(SecurityLevel::StrongBox, b"", rot)
                .unwrap();
            let e = verify_chain(&d.cert_chain(), &anchors, &pol, now()).unwrap_err();
            assert!(matches!(e, PqLinkError::Attestation(_)), "{rot:?}: {e:?}");
            // Emulyator sinovi siyosati (RoT talab qilinmaydi).
            let emu = AttestationPolicy {
                require_verified_boot: false,
                ..AttestationPolicy::default()
            };
            assert!(verify_chain(&d.cert_chain(), &anchors, &emu, now()).is_ok());
        }
    }

    /// Zanjirni uzaytirish: haqiqiy attestatsiyali kalit (TEE, ochiq bootloader) o'zi imzolagan soxta
    /// leaf (StrongBox, Verified, boshqa challenge) bilan — rad etilishi shart.
    #[test]
    fn chain_extension_by_device_key_rejected() {
        let ca = SandboxAttestationCa::generate().unwrap();
        let anchors = ca.anchors().unwrap();
        let real = ca
            .issue_device_with(SecurityLevel::TrustedEnvironment, b"real", Some((false, 2)))
            .unwrap();
        let (pkcs8, chain) = real.to_parts().unwrap();
        let real_kp = KeyPair::try_from(pkcs8.as_slice()).unwrap();
        // Haqiqiy leaf'ning subject'i soxta leaf'ning issuer'i bo'ladi.
        let mut real_params = CertificateParams::default();
        let mut dn = DistinguishedName::new();
        dn.push(DnType::CommonName, "Android Keystore Key");
        real_params.distinguished_name = dn;
        let fake_kp = KeyPair::generate_for(&PKCS_ECDSA_P256_SHA256).unwrap();
        let mut p = CertificateParams::default();
        let mut dn = DistinguishedName::new();
        dn.push(DnType::CommonName, "Android Keystore Key (fake)");
        p.distinguished_name = dn;
        p.not_before = OffsetDateTime::now_utc() - Duration::days(1);
        p.not_after = OffsetDateTime::now_utc() + Duration::days(30);
        p.custom_extensions = vec![CustomExtension::from_oid_content(
            KEY_DESCRIPTION_OID,
            key_description_der(SecurityLevel::StrongBox, b"forged-nonce"),
        )];
        let fake = p
            .signed_by(&fake_kp, &Issuer::new(real_params, &real_kp))
            .unwrap();
        let forged = [vec![fake.der().to_vec()], chain].concat();
        let lax = AttestationPolicy {
            min_security_level: SecurityLevel::Software,
            require_verified_boot: false,
        };
        let e = verify_chain(&forged, &anchors, &lax, now()).unwrap_err();
        assert!(format!("{e:?}").contains("CA emas"), "{e:?}");
    }

    #[test]
    fn tampered_leaf_rejected() {
        let ca = SandboxAttestationCa::generate().unwrap();
        let dev = ca.issue_device(SecurityLevel::StrongBox, b"x").unwrap();
        let mut chain = dev.cert_chain();
        let n = chain[0].len();
        chain[0][n - 10] ^= 0x01; // imzo baytini buzamiz
        assert!(verify_chain(
            &chain,
            &ca.anchors().unwrap(),
            &AttestationPolicy::default(),
            now()
        )
        .is_err());
    }

    #[test]
    fn ca_and_device_persist() {
        let ca = SandboxAttestationCa::generate().unwrap();
        let ca2 = SandboxAttestationCa::from_parts(&ca.key_pem(), ca.root_der().to_vec()).unwrap();
        let dev = ca2.issue_device(SecurityLevel::StrongBox, b"").unwrap();
        assert!(verify_chain(
            &dev.cert_chain(),
            &ca.anchors().unwrap(),
            &AttestationPolicy::default(),
            now()
        )
        .is_ok());
        let (k, c) = dev.to_parts().unwrap();
        let dev2 = SoftDeviceKey::from_parts(&k, c).unwrap();
        let v = verify_chain(
            &dev2.cert_chain(),
            &ca.anchors().unwrap(),
            &AttestationPolicy::default(),
            now(),
        )
        .unwrap();
        v.verify_signature(b"m", &dev2.sign(b"m").unwrap()).unwrap();
    }
}
