//! Server identifikatori va gibrid imzo (Ed25519 + ML-DSA-65).
//!
//! * Ed25519 kaliti HSM (`KeyStore`) ichida.
//! * ML-DSA-65 urug'i (32 bayt) KEK bilan AES-256-GCM o'ralgan blob sifatida saqlanadi va faqat
//!   imzolash paytida xotirada ochiladi (ADR-0003).

use std::sync::Arc;

use ed25519_dalek::{Signature as EdSignature, VerifyingKey as EdVerifyingKey};
use ml_dsa::{
    EncodedSignature, EncodedVerifyingKey, Keypair, MlDsa65, Signature as MlSignature,
    SigningKey as MlSigningKey, VerifyingKey as MlVerifyingKey,
};
use mpay_crypto::keystore::{KeyLabel, KeyStore};
use mpay_crypto::rng;
use zeroize::Zeroizing;

use crate::crypto::{server_fingerprint, MLDSA_CTX, ROTATION_LABEL, SERVER_SIG_LABEL};
use crate::wire::{MLDSA65_PK_LEN, MLDSA65_SIG_LEN};
use crate::PqLinkError;

/// Serverning ochiq identifikatori (qurilma uni pinlaydi).
#[derive(Clone, PartialEq, Eq)]
pub struct ServerIdentity {
    pub ed25519: [u8; 32],
    pub mldsa65: Vec<u8>,
}

impl std::fmt::Debug for ServerIdentity {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(
            f,
            "ServerIdentity(fp={})",
            hex::encode(&self.fingerprint()[..8])
        )
    }
}

impl ServerIdentity {
    pub fn new(ed25519: [u8; 32], mldsa65: Vec<u8>) -> Result<Self, PqLinkError> {
        if mldsa65.len() != MLDSA65_PK_LEN {
            return Err(PqLinkError::Malformed("ML-DSA-65 ochiq kaliti uzunligi"));
        }
        Ok(Self { ed25519, mldsa65 })
    }

    /// `SHA-256(ed25519_pk ‖ mldsa65_pk)`.
    pub fn fingerprint(&self) -> [u8; 32] {
        server_fingerprint(&self.ed25519, &self.mldsa65)
    }

    /// Gibrid imzoni tekshiradi: **ikkalasi ham** to'g'ri bo'lishi shart.
    pub fn verify(
        &self,
        th1: &[u8; 32],
        sig_ed25519: &[u8; 64],
        sig_mldsa65: &[u8],
    ) -> Result<(), PqLinkError> {
        self.verify_msg(&[SERVER_SIG_LABEL, th1].concat(), sig_ed25519, sig_mldsa65)
    }

    /// Kalit almashtirish (P1.6): shu identifikator `next_fp` ni tasdiqlaganini tekshiradi.
    pub fn verify_endorsement(
        &self,
        next_fp: &[u8; 32],
        sig_ed25519: &[u8; 64],
        sig_mldsa65: &[u8],
    ) -> Result<(), PqLinkError> {
        self.verify_msg(
            &[ROTATION_LABEL, next_fp].concat(),
            sig_ed25519,
            sig_mldsa65,
        )
    }

    pub(crate) fn verify_msg(
        &self,
        msg: &[u8],
        sig_ed25519: &[u8; 64],
        sig_mldsa65: &[u8],
    ) -> Result<(), PqLinkError> {
        let ed = EdVerifyingKey::from_bytes(&self.ed25519)
            .map_err(|_| PqLinkError::BadServerSignature("Ed25519 kaliti"))?;
        ed.verify_strict(msg, &EdSignature::from_bytes(sig_ed25519))
            .map_err(|_| PqLinkError::BadServerSignature("Ed25519"))?;

        let vk_enc = EncodedVerifyingKey::<MlDsa65>::try_from(self.mldsa65.as_slice())
            .map_err(|_| PqLinkError::BadServerSignature("ML-DSA kaliti"))?;
        let vk = MlVerifyingKey::<MlDsa65>::decode(&vk_enc);
        let sig_enc = EncodedSignature::<MlDsa65>::try_from(sig_mldsa65)
            .map_err(|_| PqLinkError::BadServerSignature("ML-DSA uzunligi"))?;
        let sig = MlSignature::<MlDsa65>::decode(&sig_enc)
            .ok_or(PqLinkError::BadServerSignature("ML-DSA kodlash"))?;
        if !vk.verify_with_context(msg, MLDSA_CTX, &sig) {
            return Err(PqLinkError::BadServerSignature("ML-DSA-65"));
        }
        Ok(())
    }
}

/// Gibrid server imzolovchisi.
pub trait ServerSigner: Send + Sync + std::fmt::Debug {
    fn identity(&self) -> &ServerIdentity;
    /// `(Ed25519 imzo, ML-DSA-65 imzo)` — `SERVER_SIG_LABEL ‖ th1` ustidan.
    fn sign(&self, th1: &[u8; 32]) -> Result<([u8; 64], Vec<u8>), PqLinkError>;
    /// Kalit almashtirish: `ROTATION_LABEL ‖ next_fp` ustidan gibrid imzo.
    fn endorse(&self, next_fp: &[u8; 32]) -> Result<([u8; 64], Vec<u8>), PqLinkError>;
}

/// KEK bilan o'ralgan ML-DSA-65 urug'i.
#[derive(Clone, PartialEq, Eq)]
pub struct MlDsaSeedBlob {
    pub kek_label: String,
    pub nonce: [u8; 12],
    pub ciphertext: Vec<u8>,
}

impl std::fmt::Debug for MlDsaSeedBlob {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "MlDsaSeedBlob(kek={})", self.kek_label)
    }
}

const BLOB_AAD: &[u8] = b"MPAY-PQLINK-MLDSA65-SEED-V1";
const BLOB_MAGIC: &[u8; 4] = b"MQS1";

impl MlDsaSeedBlob {
    /// Yangi urug' generatsiya qilib KEK bilan o'raydi.
    pub fn generate(ks: &dyn KeyStore, kek: &KeyLabel) -> Result<Self, PqLinkError> {
        let seed = rng::secret_array::<32>()?;
        Self::wrap(ks, kek, &seed)
    }

    /// Berilgan urug'ni o'raydi (testlar, migratsiya).
    pub fn wrap(ks: &dyn KeyStore, kek: &KeyLabel, seed: &[u8; 32]) -> Result<Self, PqLinkError> {
        let s = ks.aes_gcm_seal(kek, BLOB_AAD, seed)?;
        Ok(Self {
            kek_label: kek.to_string(),
            nonce: s.nonce,
            ciphertext: s.ciphertext,
        })
    }

    fn unwrap_key(&self, ks: &dyn KeyStore) -> Result<MlSigningKey<MlDsa65>, PqLinkError> {
        let pt = ks.aes_gcm_open(
            &KeyLabel::new(self.kek_label.clone()),
            &self.nonce,
            BLOB_AAD,
            &self.ciphertext,
        )?;
        let seed: [u8; 32] = pt
            .as_slice()
            .try_into()
            .map_err(|_| PqLinkError::Crypto("ML-DSA urug'i".into()))?;
        let seed = Zeroizing::new(seed);
        Ok(MlSigningKey::<MlDsa65>::from_seed(&(*seed).into()))
    }

    /// Fayl formati: `MQS1` ‖ u8 len ‖ kek_label ‖ nonce ‖ ciphertext.
    pub fn to_bytes(&self) -> Vec<u8> {
        let mut v = BLOB_MAGIC.to_vec();
        v.push(self.kek_label.len() as u8);
        v.extend_from_slice(self.kek_label.as_bytes());
        v.extend_from_slice(&self.nonce);
        v.extend_from_slice(&self.ciphertext);
        v
    }

    pub fn from_bytes(b: &[u8]) -> Result<Self, PqLinkError> {
        let bad = || PqLinkError::Malformed("ML-DSA blob");
        if b.len() < 5 || &b[..4] != BLOB_MAGIC {
            return Err(bad());
        }
        let n = usize::from(b[4]);
        let rest = b.get(5..).ok_or_else(bad)?;
        if rest.len() != n + 12 + 48 {
            return Err(bad());
        }
        let kek_label = std::str::from_utf8(&rest[..n])
            .map_err(|_| bad())?
            .to_owned();
        let mut nonce = [0u8; 12];
        nonce.copy_from_slice(&rest[n..n + 12]);
        Ok(Self {
            kek_label,
            nonce,
            ciphertext: rest[n + 12..].to_vec(),
        })
    }
}

/// `KeyStore` asosidagi imzolovchi: Ed25519 — HSM, ML-DSA-65 — o'ralgan blob.
pub struct KeyStoreServerSigner {
    ks: Arc<dyn KeyStore>,
    ed_label: KeyLabel,
    mldsa: MlDsaSeedBlob,
    identity: ServerIdentity,
}

impl std::fmt::Debug for KeyStoreServerSigner {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("KeyStoreServerSigner")
            .field("ed25519", &self.ed_label)
            .field("identity", &self.identity)
            .finish()
    }
}

impl KeyStoreServerSigner {
    pub fn new(
        ks: Arc<dyn KeyStore>,
        ed_label: KeyLabel,
        mldsa: MlDsaSeedBlob,
    ) -> Result<Self, PqLinkError> {
        let ed = ks.ed25519_public_key(&ed_label)?;
        let sk = mldsa.unwrap_key(ks.as_ref())?;
        let ml_pk = sk.verifying_key().encode().to_vec();
        drop(sk);
        let identity = ServerIdentity::new(ed, ml_pk)?;
        Ok(Self {
            ks,
            ed_label,
            mldsa,
            identity,
        })
    }
}

impl ServerSigner for KeyStoreServerSigner {
    fn identity(&self) -> &ServerIdentity {
        &self.identity
    }

    fn sign(&self, th1: &[u8; 32]) -> Result<([u8; 64], Vec<u8>), PqLinkError> {
        self.sign_msg(&[SERVER_SIG_LABEL, th1].concat())
    }

    fn endorse(&self, next_fp: &[u8; 32]) -> Result<([u8; 64], Vec<u8>), PqLinkError> {
        self.sign_msg(&[ROTATION_LABEL, next_fp].concat())
    }
}

impl KeyStoreServerSigner {
    fn sign_msg(&self, msg: &[u8]) -> Result<([u8; 64], Vec<u8>), PqLinkError> {
        let ed = self.ks.ed25519_sign(&self.ed_label, msg)?;
        // ML-DSA kaliti faqat shu blok ichida ochiq; `SigningKey` — ZeroizeOnDrop.
        let sk = self.mldsa.unwrap_key(self.ks.as_ref())?;
        let sig = sk
            .expanded_key()
            .sign_randomized(msg, MLDSA_CTX, &mut getrandom::SysRng)
            .map_err(|_| PqLinkError::Crypto("ML-DSA imzo".into()))?;
        let enc = sig.encode().to_vec();
        debug_assert_eq!(enc.len(), MLDSA65_SIG_LEN);
        Ok((ed, enc))
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use mpay_crypto::keystore::{KeyKind, MemoryKeyStore};

    fn signer() -> KeyStoreServerSigner {
        let ks: Arc<dyn KeyStore> = Arc::new(MemoryKeyStore::random());
        let kek = KeyLabel::new(KeyLabel::KEK);
        let ed = KeyLabel::new(KeyLabel::SERVER_ED25519);
        ks.ensure_key(&kek, KeyKind::Aes256).unwrap();
        ks.ensure_key(&ed, KeyKind::Ed25519).unwrap();
        let blob = MlDsaSeedBlob::generate(ks.as_ref(), &kek).unwrap();
        KeyStoreServerSigner::new(ks, ed, blob).unwrap()
    }

    #[test]
    fn hybrid_sign_verify_and_both_required() {
        let s = signer();
        let th = [3u8; 32];
        let (ed, ml) = s.sign(&th).unwrap();
        s.identity().verify(&th, &ed, &ml).unwrap();

        let mut bad_ed = ed;
        bad_ed[10] ^= 1;
        assert_eq!(
            s.identity().verify(&th, &bad_ed, &ml),
            Err(PqLinkError::BadServerSignature("Ed25519"))
        );
        let mut bad_ml = ml.clone();
        bad_ml[100] ^= 1;
        assert!(s.identity().verify(&th, &ed, &bad_ml).is_err());
        assert!(s.identity().verify(&[4u8; 32], &ed, &ml).is_err());
    }

    #[test]
    fn endorsement_is_domain_separated() {
        let cur = signer();
        let next = signer();
        let fp = next.identity().fingerprint();
        let (ed, ml) = cur.endorse(&fp).unwrap();
        cur.identity().verify_endorsement(&fp, &ed, &ml).unwrap();
        // Boshqa barmoq izi yoki boshqa imzolovchi — rad.
        assert!(cur
            .identity()
            .verify_endorsement(&[0u8; 32], &ed, &ml)
            .is_err());
        assert!(next.identity().verify_endorsement(&fp, &ed, &ml).is_err());
        // Tasdiq handshake imzosi sifatida o'tmaydi va aksincha (domen ajratish).
        assert!(cur.identity().verify(&fp, &ed, &ml).is_err());
        let (hs_ed, hs_ml) = cur.sign(&fp).unwrap();
        assert!(cur
            .identity()
            .verify_endorsement(&fp, &hs_ed, &hs_ml)
            .is_err());
    }

    #[test]
    fn blob_roundtrip() {
        let ks = MemoryKeyStore::random();
        let kek = KeyLabel::new(KeyLabel::KEK);
        ks.ensure_key(&kek, KeyKind::Aes256).unwrap();
        let b = MlDsaSeedBlob::generate(&ks, &kek).unwrap();
        assert_eq!(MlDsaSeedBlob::from_bytes(&b.to_bytes()).unwrap(), b);
        assert!(MlDsaSeedBlob::from_bytes(&b.to_bytes()[1..]).is_err());
        assert!(!format!("{b:?}").contains(&hex::encode(&b.ciphertext)));
    }
}
