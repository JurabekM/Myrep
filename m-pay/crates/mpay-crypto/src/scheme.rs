//! Kriptogramma sxemalari (ADR-0004). Algoritm `CryptogramScheme` trait'i orqali
//! almashtiriladi; sandbox'da yagona implementatsiya — [`MpayAes128CmacV1`].

use mpay_common::Pan;

use crate::keystore::{soft, KeyLabel, KeyStore};
use crate::{ct_eq, kdf, CryptoError, SecretKey16};

/// Kriptogramma sxemasi.
pub trait CryptogramScheme: Send + Sync + std::fmt::Debug {
    /// IAD bayt 1 dagi sxema ID.
    fn scheme_id(&self) -> u8;

    /// Inson o'qiydigan nom.
    fn name(&self) -> &'static str;

    /// `MK_tok = KDF(IMK, DPAN ‖ PSN)` — IMK HSM ichida.
    fn token_master_key(
        &self,
        ks: &dyn KeyStore,
        imk: &KeyLabel,
        dpan: &Pan,
        psn: u8,
    ) -> Result<SecretKey16, CryptoError>;

    /// `LUK_i = KDF(MK_tok, i)`.
    fn luk(&self, mk: &SecretKey16, seq: u32) -> SecretKey16;

    /// `SK = KDF(LUK, ATC)`.
    fn session_key(&self, luk: &SecretKey16, atc: u16) -> SecretKey16;

    /// ARQC (8 bayt).
    fn arqc(&self, sk: &SecretKey16, cdol: &[u8]) -> [u8; 8];

    /// ARPC (4 bayt), `arc` — javob kodining 2 ta ASCII bayti.
    fn arpc(&self, sk: &SecretKey16, arqc: &[u8; 8], arc: [u8; 2]) -> [u8; 4];

    /// ARQC'ni constant-time tekshiradi.
    fn verify_arqc(&self, sk: &SecretKey16, cdol: &[u8], arqc: &[u8]) -> bool {
        ct_eq(&self.arqc(sk, cdol), arqc)
    }

    /// Qulaylik: IMK'dan to'g'ridan-to'g'ri LUK (Vault provisioning va issuer uchun).
    fn luk_from_imk(
        &self,
        ks: &dyn KeyStore,
        imk: &KeyLabel,
        dpan: &Pan,
        psn: u8,
        seq: u32,
    ) -> Result<SecretKey16, CryptoError> {
        let mk = self.token_master_key(ks, imk, dpan, psn)?;
        Ok(self.luk(&mk, seq))
    }
}

/// `MPAY-AES128-CMAC-V1` (`docs/specs/emv-profile.md` §5–§7).
#[derive(Debug, Default, Clone, Copy)]
pub struct MpayAes128CmacV1;

impl MpayAes128CmacV1 {
    pub const SCHEME_ID: u8 = 0x01;
    pub const LABEL_MK: &'static [u8] = b"MPAY-TOKEN-MK";
    pub const LABEL_LUK: &'static [u8] = b"MPAY-LUK";
    pub const LABEL_SK: &'static [u8] = b"MPAY-SK-AC";

    /// `MK_tok` konteksti: `len(DPAN)` ‖ DPAN ASCII ‖ PSN.
    pub fn mk_context(dpan: &Pan, psn: u8) -> Vec<u8> {
        let d = dpan.expose_digits().as_bytes();
        let mut c = Vec::with_capacity(d.len() + 2);
        c.push(d.len() as u8);
        c.extend_from_slice(d);
        c.push(psn);
        c
    }
}

impl CryptogramScheme for MpayAes128CmacV1 {
    fn scheme_id(&self) -> u8 {
        Self::SCHEME_ID
    }

    fn name(&self) -> &'static str {
        "MPAY-AES128-CMAC-V1"
    }

    fn token_master_key(
        &self,
        ks: &dyn KeyStore,
        imk: &KeyLabel,
        dpan: &Pan,
        psn: u8,
    ) -> Result<SecretKey16, CryptoError> {
        let ctx = zeroize::Zeroizing::new(Self::mk_context(dpan, psn));
        kdf::derive_with_keystore(ks, imk, Self::LABEL_MK, &ctx)
    }

    fn luk(&self, mk: &SecretKey16, seq: u32) -> SecretKey16 {
        kdf::derive(mk, Self::LABEL_LUK, &seq.to_be_bytes())
    }

    fn session_key(&self, luk: &SecretKey16, atc: u16) -> SecretKey16 {
        kdf::derive(luk, Self::LABEL_SK, &atc.to_be_bytes())
    }

    fn arqc(&self, sk: &SecretKey16, cdol: &[u8]) -> [u8; 8] {
        let mac = soft::cmac_aes128(sk.expose(), cdol);
        let mut out = [0u8; 8];
        out.copy_from_slice(&mac[..8]);
        out
    }

    fn arpc(&self, sk: &SecretKey16, arqc: &[u8; 8], arc: [u8; 2]) -> [u8; 4] {
        let mut input = [0u8; 10];
        input[..8].copy_from_slice(arqc);
        input[8..].copy_from_slice(&arc);
        let mac = soft::cmac_aes128(sk.expose(), &input);
        let mut out = [0u8; 4];
        out.copy_from_slice(&mac[..4]);
        out
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::keystore::{KeyKind, MemoryKeyStore};

    #[test]
    fn chain_is_consistent_and_sensitive() {
        let ks = MemoryKeyStore::random();
        let imk = KeyLabel::new(KeyLabel::IMK_AC);
        ks.ensure_key(&imk, KeyKind::Aes128).unwrap();
        let s = MpayAes128CmacV1;
        let dpan = Pan::from_prefix("990077000000123").unwrap();
        let dpan2 = Pan::from_prefix("990077000000124").unwrap();

        let luk = s.luk_from_imk(&ks, &imk, &dpan, 0, 1).unwrap();
        assert_ne!(luk, s.luk_from_imk(&ks, &imk, &dpan, 0, 2).unwrap());
        assert_ne!(luk, s.luk_from_imk(&ks, &imk, &dpan, 1, 1).unwrap());
        assert_ne!(luk, s.luk_from_imk(&ks, &imk, &dpan2, 0, 1).unwrap());

        let sk = s.session_key(&luk, 5);
        let cdol = [0xAB; 41];
        let arqc = s.arqc(&sk, &cdol);
        assert!(s.verify_arqc(&sk, &cdol, &arqc));
        let mut tampered = cdol;
        tampered[3] ^= 1;
        assert!(!s.verify_arqc(&sk, &tampered, &arqc));
        assert!(!s.verify_arqc(&s.session_key(&luk, 6), &cdol, &arqc));
        assert_ne!(s.arpc(&sk, &arqc, *b"00"), s.arpc(&sk, &arqc, *b"05"));
    }
}
