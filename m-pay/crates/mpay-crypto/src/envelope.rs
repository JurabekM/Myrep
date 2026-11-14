//! Envelope encryption: HSM ichidagi KEK → DB'dagi o'ralgan DEK'lar → AES-256-GCM shifrmatn.
//!
//! * DEK o'rash: `KeyStore::aes_gcm_seal(KEK, aad = "MPAY-DEK-V1" ‖ dek_id, DEK)`;
//! * ma'lumot shifrlash: `AES-256-GCM(DEK, nonce = CSPRNG, aad = "MPAY-DATA-V1" ‖ dek_id ‖ 0x00 ‖ caller_aad)`.
//!
//! `caller_aad` yozuvni kontekstga bog'laydi (masalan karta ID va maydon nomi) — shifrmatnni
//! boshqa qatorga ko'chirib qo'yish ochishda xato beradi.

use core::fmt;

use zeroize::Zeroizing;

use crate::keystore::{soft, KeyLabel, KeyStore};
use crate::{rng, CryptoError};

const DEK_AAD: &[u8] = b"MPAY-DEK-V1";
const DATA_AAD: &[u8] = b"MPAY-DATA-V1";

/// Ochiq DEK (faqat xotirada).
pub struct Dek {
    id: String,
    key: Zeroizing<[u8; 32]>,
}

impl fmt::Debug for Dek {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "Dek({}, <maxfiy>)", self.id)
    }
}

/// KEK bilan o'ralgan DEK (DB'da saqlanadi).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct WrappedDek {
    pub dek_id: String,
    pub kek_label: String,
    pub nonce: [u8; 12],
    pub ciphertext: Vec<u8>,
}

/// DEK bilan shifrlangan ma'lumot.
#[derive(Clone, PartialEq, Eq)]
pub struct Sealed {
    pub dek_id: String,
    pub nonce: [u8; 12],
    pub ciphertext: Vec<u8>,
}

impl fmt::Debug for Sealed {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "Sealed({}, {} bayt)", self.dek_id, self.ciphertext.len())
    }
}

fn dek_aad(dek_id: &str) -> Vec<u8> {
    [DEK_AAD, dek_id.as_bytes()].concat()
}

fn data_aad(dek_id: &str, caller: &[u8]) -> Vec<u8> {
    [DATA_AAD, dek_id.as_bytes(), &[0u8], caller].concat()
}

impl Dek {
    /// Yangi tasodifiy DEK.
    pub fn generate(dek_id: impl Into<String>) -> Result<Self, CryptoError> {
        Ok(Self {
            id: dek_id.into(),
            key: rng::secret_array::<32>()?,
        })
    }

    pub fn id(&self) -> &str {
        &self.id
    }

    /// KEK bilan o'raydi.
    pub fn wrap(&self, ks: &dyn KeyStore, kek: &KeyLabel) -> Result<WrappedDek, CryptoError> {
        let sealed = ks.aes_gcm_seal(kek, &dek_aad(&self.id), &self.key[..])?;
        Ok(WrappedDek {
            dek_id: self.id.clone(),
            kek_label: kek.to_string(),
            nonce: sealed.nonce,
            ciphertext: sealed.ciphertext,
        })
    }

    /// O'ralgan DEK'ni ochadi.
    pub fn unwrap(ks: &dyn KeyStore, w: &WrappedDek) -> Result<Self, CryptoError> {
        let pt = ks.aes_gcm_open(
            &KeyLabel::new(w.kek_label.clone()),
            &w.nonce,
            &dek_aad(&w.dek_id),
            &w.ciphertext,
        )?;
        let mut key = Zeroizing::new([0u8; 32]);
        if pt.len() != 32 {
            return Err(CryptoError::Decrypt);
        }
        key.copy_from_slice(&pt);
        Ok(Self {
            id: w.dek_id.clone(),
            key,
        })
    }

    /// Ma'lumotni shifrlaydi.
    pub fn seal(&self, aad: &[u8], plaintext: &[u8]) -> Result<Sealed, CryptoError> {
        let nonce = rng::array::<12>()?;
        Ok(Sealed {
            dek_id: self.id.clone(),
            nonce,
            ciphertext: soft::gcm_seal(&self.key, &nonce, &data_aad(&self.id, aad), plaintext)?,
        })
    }

    /// Ma'lumotni ochadi.
    pub fn open(&self, aad: &[u8], s: &Sealed) -> Result<Zeroizing<Vec<u8>>, CryptoError> {
        if s.dek_id != self.id {
            return Err(CryptoError::Decrypt);
        }
        soft::gcm_open(&self.key, &s.nonce, &data_aad(&self.id, aad), &s.ciphertext)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::keystore::{KeyKind, MemoryKeyStore};

    #[test]
    fn wrap_unwrap_seal_open() {
        let ks = MemoryKeyStore::random();
        let kek = KeyLabel::new(KeyLabel::KEK);
        ks.ensure_key(&kek, KeyKind::Aes256).unwrap();

        let dek = Dek::generate("dek-1").unwrap();
        let wrapped = dek.wrap(&ks, &kek).unwrap();
        assert_eq!(wrapped.ciphertext.len(), 48);
        let dek2 = Dek::unwrap(&ks, &wrapped).unwrap();

        let s = dek.seal(b"card:1|pan", b"9900120000003456").unwrap();
        assert_eq!(
            &dek2.open(b"card:1|pan", &s).unwrap()[..],
            b"9900120000003456"
        );
        // Boshqa kontekst — xato.
        assert_eq!(dek2.open(b"card:2|pan", &s), Err(CryptoError::Decrypt));

        // DEK ID'sini almashtirib qo'yish — xato.
        let mut w2 = wrapped.clone();
        w2.dek_id = "dek-2".into();
        assert_eq!(Dek::unwrap(&ks, &w2).unwrap_err(), CryptoError::Decrypt);

        // Boshqa KEK bilan ochib bo'lmaydi.
        let ks2 = MemoryKeyStore::random();
        ks2.ensure_key(&kek, KeyKind::Aes256).unwrap();
        assert_eq!(
            Dek::unwrap(&ks2, &wrapped).unwrap_err(),
            CryptoError::Decrypt
        );
        assert!(!format!("{dek:?}").contains(&hex::encode(&dek.key[..])));
    }
}
