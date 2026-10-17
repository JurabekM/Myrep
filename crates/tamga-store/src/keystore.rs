//! Imzo kalitlarini yaratish/yuklash va ochiq kalitni eksport qilish.

use tamga_core::keys::{PublicKeys, SigningKeys};

use crate::secrets::SecretStore;
use crate::{Home, Result, StoreError, io_err, random};

const SIGNING_SEED: &str = "signing-seed-v1";
pub const VAULT_MASTER: &str = "vault-master-v1";

/// Imzo kalitlari: omborda bo'lmasa yangi tasodifiy urug'lardan yaratiladi.
/// Urug' = Ed25519 maxfiy kaliti (32) || ML-DSA ξ (32).
pub fn load_or_create(store: &dyn SecretStore, home: &Home) -> Result<(SigningKeys, bool)> {
    let (seed, created) = match store.get(SIGNING_SEED)? {
        Some(s) => (s, false),
        None => {
            let s: [u8; 64] = random();
            store.set(SIGNING_SEED, &s)?;
            (s.to_vec(), true)
        }
    };
    let seed: [u8; 64] = seed
        .try_into()
        .map_err(|_| StoreError::Secret("imzo urug'i 64 bayt emas".into()))?;
    let ed: [u8; 32] = seed[..32].try_into().expect("32");
    let ml: [u8; 32] = seed[32..].try_into().expect("32");
    let keys = SigningKeys::from_seeds(&ed, &ml);
    export_public(&keys.public(), home)?;
    Ok((keys, created))
}

/// Auditor uchun `public-key.json`. Auditor kalitni jurnal papkasidan emas, operatordan olishi
/// kerak (spec §10) — bu fayl faqat qulaylik uchun.
pub fn export_public(pk: &PublicKeys, home: &Home) -> Result<()> {
    let p = home.public_key();
    let text = tamga_core::jcs::canonicalize(&pk.to_json()).expect("kalit json") + "\n";
    std::fs::write(&p, text).map_err(io_err(&p))
}

/// Vault master kaliti (32 bayt).
pub fn vault_master(store: &dyn SecretStore) -> Result<[u8; 32]> {
    match store.get(VAULT_MASTER)? {
        Some(k) => k
            .try_into()
            .map_err(|_| StoreError::Secret("vault master kaliti 32 bayt emas".into())),
        None => {
            let k: [u8; 32] = random();
            store.set(VAULT_MASTER, &k)?;
            Ok(k)
        }
    }
}
