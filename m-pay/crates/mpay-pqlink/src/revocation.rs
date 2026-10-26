//! Bekor qilingan server identifikatorlari ro'yxati (1-faza, ADR-0014).
//!
//! Joriy server kaliti oshkor bo'lsa, hujumchi u bilan istalgan narsani — jumladan o'zining "keyingi"
//! kalitini (ADR-0012) — imzolay oladi. Shuning uchun bekor qilish ro'yxatini serverda **bo'lmagan**
//! oflayn ildiz kalit (Ed25519 + ML-DSA-65) imzolaydi; ilovaga faqat ildiz barmoq izi joylanadi.
//! Ro'yxat versiyalanadi: qurilma faqat kattaroq versiyani qabul qiladi (orqaga qaytarib bo'lmaydi).

use ed25519_dalek::{Signer, SigningKey as EdSigningKey};
use ml_dsa::{Keypair, MlDsa65, SigningKey as MlSigningKey};
use mpay_crypto::rng;
use zeroize::Zeroizing;

use crate::crypto::MLDSA_CTX;
use crate::identity::ServerIdentity;
use crate::PqLinkError;

/// Imzolanadigan xabar yorlig'i (handshake va rotation yorliqlaridan farqli).
pub const REVOCATION_LABEL: &[u8] = b"MPAY-PQLINK-V1 revocations";

/// Kanonik xabar: `REVOCATION_LABEL ‖ version (u64 BE) ‖ count (u32 BE) ‖ fp…` (tartiblangan, takrorsiz).
pub fn revocation_message(version: u64, revoked: &[[u8; 32]]) -> Vec<u8> {
    let mut list = revoked.to_vec();
    list.sort_unstable();
    list.dedup();
    let mut m = Vec::with_capacity(REVOCATION_LABEL.len() + 12 + list.len() * 32);
    m.extend_from_slice(REVOCATION_LABEL);
    m.extend_from_slice(&version.to_be_bytes());
    m.extend_from_slice(&(list.len() as u32).to_be_bytes());
    for fp in &list {
        m.extend_from_slice(fp);
    }
    m
}

/// Imzolangan ro'yxat.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct SignedRevocations {
    pub version: u64,
    pub revoked: Vec<[u8; 32]>,
    /// Ildiz ochiq kalitlari (qurilma ularning barmoq izini pinlangan qiymat bilan solishtiradi).
    pub root: ServerIdentity,
    pub sig_ed25519: [u8; 64],
    pub sig_mldsa65: Vec<u8>,
}

impl SignedRevocations {
    /// Ildiz barmoq izi pinlangan qiymatga teng va gibrid imzo (ikkalasi ham) to'g'ri bo'lishi shart.
    pub fn verify(&self, pinned_root_fp: &[u8; 32]) -> Result<(), PqLinkError> {
        if &self.root.fingerprint() != pinned_root_fp {
            return Err(PqLinkError::ServerNotPinned);
        }
        self.root.verify_msg(
            &revocation_message(self.version, &self.revoked),
            &self.sig_ed25519,
            &self.sig_mldsa65,
        )
    }

    pub fn is_revoked(&self, fp: &[u8; 32]) -> bool {
        self.revoked.contains(fp)
    }
}

/// Oflayn ildiz kaliti — faqat imzolash stansiyasida, serverga qo'yilmaydi.
pub struct RootKey {
    ed_seed: Zeroizing<[u8; 32]>,
    ml_seed: Zeroizing<[u8; 32]>,
}

impl std::fmt::Debug for RootKey {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str("RootKey(<maxfiy>)")
    }
}

impl RootKey {
    pub fn generate() -> Result<Self, PqLinkError> {
        let err = |e: mpay_crypto::CryptoError| PqLinkError::Crypto(e.to_string());
        Ok(Self {
            ed_seed: rng::secret_array::<32>().map_err(err)?,
            ml_seed: rng::secret_array::<32>().map_err(err)?,
        })
    }

    pub fn from_seeds(ed_seed: &[u8; 32], ml_seed: &[u8; 32]) -> Self {
        Self {
            ed_seed: Zeroizing::new(*ed_seed),
            ml_seed: Zeroizing::new(*ml_seed),
        }
    }

    /// `(ed25519 urug'i, ML-DSA urug'i)` — saqlash uchun (maxfiy).
    pub fn seeds(&self) -> (Zeroizing<[u8; 32]>, Zeroizing<[u8; 32]>) {
        (self.ed_seed.clone(), self.ml_seed.clone())
    }

    fn ml(&self) -> MlSigningKey<MlDsa65> {
        MlSigningKey::<MlDsa65>::from_seed(&(*self.ml_seed).into())
    }

    pub fn identity(&self) -> Result<ServerIdentity, PqLinkError> {
        let ed = EdSigningKey::from_bytes(&self.ed_seed);
        ServerIdentity::new(
            ed.verifying_key().to_bytes(),
            self.ml().verifying_key().encode().to_vec(),
        )
    }

    pub fn sign_revocations(
        &self,
        version: u64,
        revoked: &[[u8; 32]],
    ) -> Result<SignedRevocations, PqLinkError> {
        let mut list = revoked.to_vec();
        list.sort_unstable();
        list.dedup();
        let msg = revocation_message(version, &list);
        let sig_ed25519 = EdSigningKey::from_bytes(&self.ed_seed)
            .sign(&msg)
            .to_bytes();
        let sig_mldsa65 = self
            .ml()
            .expanded_key()
            .sign_randomized(&msg, MLDSA_CTX, &mut getrandom::SysRng)
            .map_err(|_| PqLinkError::Crypto("ML-DSA imzo".into()))?
            .encode()
            .to_vec();
        Ok(SignedRevocations {
            version,
            revoked: list,
            root: self.identity()?,
            sig_ed25519,
            sig_mldsa65,
        })
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn sign_verify_and_tamper() {
        let root = RootKey::generate().unwrap();
        let fp = root.identity().unwrap().fingerprint();
        let doc = root
            .sign_revocations(3, &[[2; 32], [1; 32], [2; 32]])
            .unwrap();
        assert_eq!(
            doc.revoked,
            vec![[1; 32], [2; 32]],
            "tartiblangan, takrorsiz"
        );
        doc.verify(&fp).unwrap();
        assert!(doc.is_revoked(&[1; 32]) && !doc.is_revoked(&[3; 32]));

        // Boshqa ildiz, o'zgartirilgan versiya yoki ro'yxat — rad.
        assert!(doc.verify(&[0; 32]).is_err());
        let mut v = doc.clone();
        v.version = 4;
        assert!(v.verify(&fp).is_err());
        let mut l = doc.clone();
        l.revoked.pop();
        assert!(l.verify(&fp).is_err());

        // Boshqa ildiz o'z kalitlari bilan imzolagan — pinga mos emas.
        let evil = RootKey::generate().unwrap();
        let forged = evil.sign_revocations(9, &[]).unwrap();
        assert_eq!(forged.verify(&fp), Err(PqLinkError::ServerNotPinned));

        // Urug'lardan tiklash — o'sha identifikator.
        let (e, m) = root.seeds();
        assert_eq!(
            RootKey::from_seeds(&e, &m).identity().unwrap(),
            root.identity().unwrap()
        );
    }
}
