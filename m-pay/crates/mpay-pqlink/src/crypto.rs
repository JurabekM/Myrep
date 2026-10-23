//! PQ Link kriptografik qurilish bloklari: gibrid KEM, transkript, kalit jadvali, yozuv AEAD.

use chacha20poly1305::aead::{Aead, KeyInit, Payload};
use chacha20poly1305::{ChaCha20Poly1305, Nonce};
use hkdf::Hkdf;
use hmac::{Hmac, Mac};
use ml_kem::kem::{Decapsulate, KeyExport};
use ml_kem::{Ciphertext, DecapsulationKey768, EncapsulationKey768, MlKem768};
use mpay_crypto::{ct_eq, rng, SecretKey32};
use sha2::{Digest, Sha256};
use x25519_dalek::{PublicKey, StaticSecret};
use zeroize::Zeroizing;

use crate::wire::{MsgType, Sealed, MLKEM768_CT_LEN, MLKEM768_EK_LEN, SESSION_ID_LEN, X25519_LEN};
use crate::PqLinkError;

pub const DIR_C2S: u8 = 0x01;
pub const DIR_S2C: u8 = 0x02;

const TH1_LABEL: &[u8] = b"MPAY-PQLINK-V1 TH1";
const TH2_LABEL: &[u8] = b"MPAY-PQLINK-V1 TH2";
pub const SERVER_SIG_LABEL: &[u8] = b"MPAY-PQLINK-V1 server-sig";
pub const DEVICE_SIG_LABEL: &[u8] = b"MPAY-PQLINK-V1 device-sig";
/// ML-DSA kontekst satri.
pub const MLDSA_CTX: &[u8] = b"mpay-pqlink-v1";

/// Mijozning efemer KEM holati. `Drop` da ikkala sir ham tozalanadi
/// (`StaticSecret` va `DecapsulationKey` — `ZeroizeOnDrop`).
pub struct ClientKem {
    x25519: StaticSecret,
    mlkem: DecapsulationKey768,
}

impl ClientKem {
    /// Yangi efemer kalitlar (OS CSPRNG).
    pub fn generate() -> Result<Self, PqLinkError> {
        let x = rng::secret_array::<32>()?;
        let seed = rng::secret_array::<64>()?;
        let mlkem = DecapsulationKey768::from_seed((*seed).into());
        Ok(Self {
            x25519: StaticSecret::from(*x),
            mlkem,
        })
    }

    pub fn x25519_public(&self) -> [u8; X25519_LEN] {
        PublicKey::from(&self.x25519).to_bytes()
    }

    pub fn mlkem_ek(&self) -> Vec<u8> {
        self.mlkem.encapsulation_key().to_bytes().to_vec()
    }

    /// Server javobidan umumiy sirni hisoblaydi: `ss_x25519 ‖ ss_mlkem`.
    pub fn finish(
        self,
        server_x25519: &[u8; 32],
        mlkem_ct: &[u8],
    ) -> Result<Zeroizing<[u8; 64]>, PqLinkError> {
        let ct: Ciphertext<MlKem768> = mlkem_ct
            .try_into()
            .map_err(|_| PqLinkError::Malformed("ML-KEM shifrmatni"))?;
        let dh = self.x25519.diffie_hellman(&PublicKey::from(*server_x25519));
        if !dh.was_contributory() {
            return Err(PqLinkError::KeyExchange("X25519 kichik tartibli nuqta"));
        }
        let k = self.mlkem.decapsulate(&ct);
        let mut ss = Zeroizing::new([0u8; 64]);
        ss[..32].copy_from_slice(dh.as_bytes());
        ss[32..].copy_from_slice(k.as_slice());
        Ok(ss)
    }
}

/// Server inkapsulyatsiyasi natijasi: `(server_x25519_pub, mlkem_ct, ss_x25519 ‖ ss_mlkem)`.
pub type ServerKemOutput = ([u8; 32], Vec<u8>, Zeroizing<[u8; 64]>);

/// Server tomoni: mijoz ochiq kalitlariga inkapsulyatsiya.
/// Natija: `(server_x25519_pub, mlkem_ct, ss_x25519 ‖ ss_mlkem)`.
pub fn server_encapsulate(
    client_x25519: &[u8; 32],
    client_ek: &[u8],
) -> Result<ServerKemOutput, PqLinkError> {
    if client_ek.len() != MLKEM768_EK_LEN {
        return Err(PqLinkError::Malformed("ML-KEM ochiq kaliti"));
    }
    let ek_arr = client_ek
        .try_into()
        .map_err(|_| PqLinkError::Malformed("ML-KEM ochiq kaliti"))?;
    // FIPS 203 §7.2 kirish tekshiruvi (modul tekshiruvi) `new` ichida.
    let ek = EncapsulationKey768::new(&ek_arr)
        .map_err(|_| PqLinkError::KeyExchange("ML-KEM ochiq kaliti yaroqsiz"))?;
    let m = rng::secret_array::<32>()?;
    let (ct, k) = ek.encapsulate_deterministic(&(*m).into());

    let xs = StaticSecret::from(*rng::secret_array::<32>()?);
    let x_pub = PublicKey::from(&xs).to_bytes();
    let dh = xs.diffie_hellman(&PublicKey::from(*client_x25519));
    if !dh.was_contributory() {
        return Err(PqLinkError::KeyExchange("X25519 kichik tartibli nuqta"));
    }
    let mut ss = Zeroizing::new([0u8; 64]);
    ss[..32].copy_from_slice(dh.as_bytes());
    ss[32..].copy_from_slice(k.as_slice());
    debug_assert_eq!(ct.len(), MLKEM768_CT_LEN);
    Ok((x_pub, ct.to_vec(), ss))
}

/// `th1 = SHA-256(TH1 ‖ ClientHello ‖ ServerHello[imzosiz])`.
pub fn th1(client_hello: &[u8], server_hello_unsigned: &[u8]) -> [u8; 32] {
    Sha256::new()
        .chain_update(TH1_LABEL)
        .chain_update(client_hello)
        .chain_update(server_hello_unsigned)
        .finalize()
        .into()
}

/// `th2 = SHA-256(TH2 ‖ ClientHello ‖ ServerHello[to'liq])`.
pub fn th2(client_hello: &[u8], server_hello: &[u8]) -> [u8; 32] {
    Sha256::new()
        .chain_update(TH2_LABEL)
        .chain_update(client_hello)
        .chain_update(server_hello)
        .finalize()
        .into()
}

/// Sessiya kalitlari.
pub struct SessionKeys {
    pub c2s: SecretKey32,
    pub s2c: SecretKey32,
    pub fin_c: SecretKey32,
    pub fin_s: SecretKey32,
}

/// `PRK = HKDF-Extract(salt = th1, IKM = ss)`, keyin yorliqli `Expand`.
pub fn key_schedule(ss: &[u8; 64], th1: &[u8; 32]) -> Result<SessionKeys, PqLinkError> {
    let hk = Hkdf::<Sha256>::new(Some(th1), ss);
    let exp = |info: &[u8]| -> Result<SecretKey32, PqLinkError> {
        let mut k = Zeroizing::new([0u8; 32]);
        hk.expand(info, &mut k[..])
            .map_err(|_| PqLinkError::Crypto("HKDF".into()))?;
        Ok(SecretKey32::from_bytes(*k))
    };
    Ok(SessionKeys {
        c2s: exp(b"mpay pqlink v1 c2s")?,
        s2c: exp(b"mpay pqlink v1 s2c")?,
        fin_c: exp(b"mpay pqlink v1 c fin")?,
        fin_s: exp(b"mpay pqlink v1 s fin")?,
    })
}

/// `HMAC-SHA256(key, th)`.
pub fn finished_mac(key: &SecretKey32, th: &[u8; 32]) -> Result<[u8; 32], PqLinkError> {
    let mut m = <Hmac<Sha256> as KeyInit>::new_from_slice(key.expose())
        .map_err(|_| PqLinkError::Crypto("HMAC".into()))?;
    m.update(th);
    Ok(m.finalize().into_bytes().into())
}

/// Finished MAC'ni constant-time tekshiradi.
pub fn verify_finished(key: &SecretKey32, th: &[u8; 32], got: &[u8; 32]) -> bool {
    finished_mac(key, th).is_ok_and(|m| ct_eq(&m, got))
}

/// Server identifikatori barmoq izi: `SHA-256(ed25519_pk ‖ mldsa65_pk)`.
pub fn server_fingerprint(ed25519_pk: &[u8; 32], mldsa65_pk: &[u8]) -> [u8; 32] {
    Sha256::new()
        .chain_update(ed25519_pk)
        .chain_update(mldsa65_pk)
        .finalize()
        .into()
}

fn nonce(seq: u64) -> Nonce {
    let mut n = [0u8; 12];
    n[4..].copy_from_slice(&seq.to_be_bytes());
    Nonce::from(n)
}

/// Yozuvni muhrlaydi.
pub fn seal(
    key: &SecretKey32,
    kind: MsgType,
    session_id: &[u8; SESSION_ID_LEN],
    seq: u64,
    dir: u8,
    plaintext: &[u8],
) -> Result<Sealed, PqLinkError> {
    let aad = Sealed::aad(kind, session_id, seq, dir);
    let c = ChaCha20Poly1305::new(key.expose().into());
    let ciphertext = c
        .encrypt(
            &nonce(seq),
            Payload {
                msg: plaintext,
                aad: &aad,
            },
        )
        .map_err(|_| PqLinkError::Crypto("AEAD".into()))?;
    Ok(Sealed {
        kind,
        session_id: *session_id,
        seq,
        ciphertext,
    })
}

/// Yozuvni ochadi (seq tekshiruvi chaqiruvchida).
pub fn open(key: &SecretKey32, rec: &Sealed, dir: u8) -> Result<Zeroizing<Vec<u8>>, PqLinkError> {
    let aad = Sealed::aad(rec.kind, &rec.session_id, rec.seq, dir);
    let c = ChaCha20Poly1305::new(key.expose().into());
    c.decrypt(
        &nonce(rec.seq),
        Payload {
            msg: &rec.ciphertext,
            aad: &aad,
        },
    )
    .map(Zeroizing::new)
    .map_err(|_| PqLinkError::Decrypt)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn hybrid_kem_agrees() {
        let c = ClientKem::generate().unwrap();
        let (sx, ct, ss_s) = server_encapsulate(&c.x25519_public(), &c.mlkem_ek()).unwrap();
        let ss_c = c.finish(&sx, &ct).unwrap();
        assert_eq!(*ss_s, *ss_c);
    }

    #[test]
    fn low_order_x25519_rejected() {
        let c = ClientKem::generate().unwrap();
        assert_eq!(
            server_encapsulate(&[0u8; 32], &c.mlkem_ek()).err(),
            Some(PqLinkError::KeyExchange("X25519 kichik tartibli nuqta"))
        );
    }

    #[test]
    fn invalid_mlkem_ek_rejected() {
        // Koeffitsiyentlar q dan katta (0xFF..): FIPS 203 modul tekshiruvidan o'tmaydi.
        let bad = vec![0xFF; MLKEM768_EK_LEN];
        assert!(server_encapsulate(&[9u8; 32], &bad).is_err());
    }

    #[test]
    fn record_roundtrip_and_binding() {
        let k = SecretKey32::from_bytes([7; 32]);
        let sid = [1; 16];
        let r = seal(&k, MsgType::Record, &sid, 5, DIR_C2S, b"salom").unwrap();
        assert_eq!(&open(&k, &r, DIR_C2S).unwrap()[..], b"salom");
        // Yo'nalish, seq, sessiya va tur AAD'ga bog'langan.
        assert_eq!(open(&k, &r, DIR_S2C).unwrap_err(), PqLinkError::Decrypt);
        let mut r2 = r.clone();
        r2.seq = 6;
        assert!(open(&k, &r2, DIR_C2S).is_err());
        let mut r3 = r.clone();
        r3.session_id[0] ^= 1;
        assert!(open(&k, &r3, DIR_C2S).is_err());
        let mut r4 = r.clone();
        r4.kind = MsgType::ClientFinished;
        assert!(open(&k, &r4, DIR_C2S).is_err());
    }
}
