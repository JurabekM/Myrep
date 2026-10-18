//! Imzo kalitlari: yaratish/yuklash, almashtirish (spec §7.5) va shifrlangan zaxira nusxa.
//!
//! `public-key.json` — **langar** kalit (jurnalning birinchi kaliti). U almashtirishdan keyin
//! o'zgarmaydi: auditor shu kalitdan boshlab almashtirishlar zanjirini jurnalning o'zidan tekshiradi.

use chacha20poly1305::aead::{Aead, KeyInit, Payload};
use chacha20poly1305::{XChaCha20Poly1305, XNonce};
use serde_json::{Value, json};
use tamga_core::b64;
use tamga_core::keys::{PublicKeys, SigningKeys};

use crate::secrets::SecretStore;
use crate::{Home, Result, StoreError, io_err, now_ts, random};

const SIGNING_SEED: &str = "signing-seed-v1";
/// Almashtirish davomida yangi kalit shu yerda turadi: jurnalga yozilib, eski kalit bilan
/// checkpoint olingandan keyingina asosiy nomga ko'chiriladi (yiqilishga chidamli).
const SIGNING_SEED_NEXT: &str = "signing-seed-next-v1";
pub const VAULT_MASTER: &str = "vault-master-v1";
/// Langar (birinchi) ochiq kalit — `ed(32) || ml(1952)`. `public-key.json` o'chirilsa shundan
/// tiklanadi, aks holda joriy (almashtirilgan) kalit langar o'rniga yozilib qolardi (L-1).
const ANCHOR_PUBLIC: &str = "anchor-public-v1";

fn store_anchor(store: &dyn SecretStore, pk: &PublicKeys) -> Result<()> {
    let mut bytes = pk.ed_bytes().to_vec();
    bytes.extend_from_slice(&pk.ml_bytes());
    store.set(ANCHOR_PUBLIC, &bytes)
}

fn load_anchor(store: &dyn SecretStore) -> Result<Option<PublicKeys>> {
    match store.get(ANCHOR_PUBLIC)? {
        Some(b) if b.len() == 32 + 1952 => PublicKeys::from_bytes(&b[..32], &b[32..])
            .map(Some)
            .map_err(|e| StoreError::Secret(e.to_string())),
        _ => Ok(None),
    }
}

fn keys_from_seed(seed: &[u8]) -> Result<SigningKeys> {
    let seed: [u8; 64] = seed
        .try_into()
        .map_err(|_| StoreError::Secret("imzo urug'i 64 bayt emas".into()))?;
    let ed: [u8; 32] = seed[..32].try_into().expect("32");
    let ml: [u8; 32] = seed[32..].try_into().expect("32");
    Ok(SigningKeys::from_seeds(&ed, &ml))
}

/// Imzo kalitlari: omborda bo'lmasa yangi tasodifiy urug'lardan yaratiladi.
/// Urug' = Ed25519 maxfiy kaliti (32) || ML-DSA ξ (32).
/// `public-key.json` faqat yo'q bo'lsa yoziladi — u langar kalit.
pub fn load_or_create(store: &dyn SecretStore, home: &Home) -> Result<(SigningKeys, bool)> {
    let (seed, created) = match store.get(SIGNING_SEED)? {
        Some(s) => (s, false),
        None => {
            let s: [u8; 64] = random();
            store.set(SIGNING_SEED, &s)?;
            (s.to_vec(), true)
        }
    };
    let keys = keys_from_seed(&seed)?;
    if created {
        // Birinchi kalit — langar. Uni faylga ham, omborga ham yozamiz.
        export_public(&keys.public(), home)?;
        store_anchor(store, &keys.public())?;
    } else if !home.public_key().exists() {
        // L-1: fayl o'chirilgan. Langarni omboridagi nusxadan tiklaymiz, joriy kalitdan emas.
        // Omborda langar bo'lmasa (eski o'rnatish) — joriy kalitni yozib, uni langar deb belgilaymiz.
        match load_anchor(store)? {
            Some(anchor) => export_public(&anchor, home)?,
            None => {
                export_public(&keys.public(), home)?;
                store_anchor(store, &keys.public())?;
            }
        }
    } else if load_anchor(store)?.is_none() {
        // Eski o'rnatish: fayl bor, lekin omborda langar yo'q — fayldagini langar deb saqlaymiz.
        store_anchor(store, &anchor(home)?)?;
    }
    Ok((keys, created))
}

/// Langar ochiq kalit (`public-key.json`).
pub fn anchor(home: &Home) -> Result<PublicKeys> {
    let p = home.public_key();
    let text = std::fs::read_to_string(&p).map_err(io_err(&p))?;
    let v: Value = serde_json::from_str(&text)
        .map_err(|e| StoreError::Secret(format!("{}: {e}", p.display())))?;
    PublicKeys::from_json(&v).map_err(|e| StoreError::Secret(format!("{}: {e}", p.display())))
}

/// Auditor uchun `public-key.json`. Auditor kalitni jurnal papkasidan emas, operatordan olishi
/// kerak (spec §10) — bu fayl faqat qulaylik uchun.
pub fn export_public(pk: &PublicKeys, home: &Home) -> Result<()> {
    let p = home.public_key();
    let text = tamga_core::jcs::canonicalize(&pk.to_json()).expect("kalit json") + "\n";
    std::fs::write(&p, text).map_err(io_err(&p))
}

/// Yangi kalitni tayyorlaydi (hali faol emas).
pub fn stage_next(store: &dyn SecretStore) -> Result<SigningKeys> {
    let s: [u8; 64] = random();
    store.set(SIGNING_SEED_NEXT, &s)?;
    keys_from_seed(&s)
}

/// Tayyorlangan, lekin hali faollashtirilmagan kalit (yiqilishdan keyin tiklash uchun).
pub fn staged_next(store: &dyn SecretStore) -> Result<Option<SigningKeys>> {
    store
        .get(SIGNING_SEED_NEXT)?
        .map(|s| keys_from_seed(&s))
        .transpose()
}

/// Tayyorlangan kalitni asosiy qiladi; eski urug' ustiga yoziladi (yo'q qilinadi).
pub fn promote_next(store: &dyn SecretStore) -> Result<()> {
    let s = store
        .get(SIGNING_SEED_NEXT)?
        .ok_or_else(|| StoreError::Secret("tayyorlangan kalit yo'q".into()))?;
    store.set(SIGNING_SEED, &s)?;
    store.delete(SIGNING_SEED_NEXT)
}

/// Tayyorlangan kalitni bekor qiladi (almashtirish jurnalga yozilmagan bo'lsa).
pub fn discard_next(store: &dyn SecretStore) -> Result<()> {
    store.delete(SIGNING_SEED_NEXT)
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

// ---------------------------------------------------------------- shifrlangan zaxira

pub const BACKUP_FORMAT: &str = "tamga-key-backup";
/// Parol uchun eng kam uzunlik (belgilarda).
pub const MIN_PASSPHRASE: usize = 12;
/// Argon2id: 64 MiB, 3 o'tish, 1 oqim (OWASP tavsiyasidan kuchliroq).
const KDF_M_KIB: u32 = 64 * 1024;
const KDF_T: u32 = 3;
const KDF_P: u32 = 1;

fn kdf(passphrase: &str, salt: &[u8], m: u32, t: u32, p: u32) -> Result<[u8; 32]> {
    use argon2::{Algorithm, Argon2, Params, Version};
    let params = Params::new(m, t, p, Some(32))
        .map_err(|e| StoreError::Secret(format!("argon2 parametrlari: {e}")))?;
    let mut key = [0u8; 32];
    Argon2::new(Algorithm::Argon2id, Version::V0x13, params)
        .hash_password_into(passphrase.as_bytes(), salt, &mut key)
        .map_err(|e| StoreError::Secret(format!("argon2: {e}")))?;
    Ok(key)
}

/// Joriy imzo kaliti, vault master kaliti va langar ochiq kalitni parol bilan shifrlaydi.
/// Natija — bitta JSON fayl matni. Jurnal va vault fayllari zaxiraga **kirmaydi** (ular alohida
/// nusxalanadi; vault ichidagilar baribir shu master kalitsiz o'qilmaydi).
pub fn backup(store: &dyn SecretStore, home: &Home, passphrase: &str) -> Result<String> {
    if passphrase.chars().count() < MIN_PASSPHRASE {
        return Err(StoreError::Secret(format!(
            "parol kamida {MIN_PASSPHRASE} belgi bo'lsin"
        )));
    }
    if staged_next(store)?.is_some() {
        return Err(StoreError::Secret(
            "kalit almashtirish yakunlanmagan — avval daemon'ni ishga tushiring".into(),
        ));
    }
    let seed = store
        .get(SIGNING_SEED)?
        .ok_or_else(|| StoreError::Secret("imzo kaliti yo'q — avval `tamga init`".into()))?;
    let current = keys_from_seed(&seed)?.public().key_id();
    let master = vault_master(store)?;
    let anchor_pk = anchor(home)?;
    let plain = json!({
        "signing_seed": b64::encode(&seed),
        "vault_master": b64::encode(&master),
        "anchor_public_key": anchor_pk.to_json(),
    })
    .to_string();

    let salt: [u8; 16] = random();
    let nonce: [u8; 24] = random();
    // Sarlavha shifrlanmaydi, lekin AEAD'ning `aad` qismi — uni o'zgartirib bo'lmaydi.
    let hdr = json!({
        "format": BACKUP_FORMAT, "v": 1,
        "kdf": {"alg": "argon2id", "m_kib": KDF_M_KIB, "t": KDF_T, "p": KDF_P, "salt": b64::encode(&salt)},
        "cipher": "xchacha20poly1305", "nonce": b64::encode(&nonce),
        "anchor": anchor_pk.key_id(), "key": current, "created": now_ts(),
    });
    let aad = tamga_core::jcs::canonicalize(&hdr).expect("sarlavha kanonik");
    let key = kdf(passphrase, &salt, KDF_M_KIB, KDF_T, KDF_P)?;
    let ct = XChaCha20Poly1305::new(&key.into())
        .encrypt(
            &XNonce::from(nonce),
            Payload {
                msg: plain.as_bytes(),
                aad: aad.as_bytes(),
            },
        )
        .map_err(|_| StoreError::Secret("shifrlash xatosi".into()))?;
    let mut out = hdr;
    out["ct"] = b64::encode(&ct).into();
    Ok(serde_json::to_string_pretty(&out).expect("json") + "\n")
}

/// Zaxiradan nima tiklanishini ko'rsatadi (tiklashdan oldin tasdiqlash uchun).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct RestoreInfo {
    pub anchor: String,
    pub key: String,
    pub created: String,
}

/// Zaxirani ochadi va omborga yozadi. Omborda **boshqa** kalit bo'lsa yoki langar boshqa bo'lsa —
/// `force` siz rad etiladi (mavjud kalitni tasodifan almashtirib, jurnalni imzolab bo'lmaydigan
/// qilib qo'ymaslik uchun). Daemon to'xtatilgan bo'lishi kerak (chaqiruvchi tekshiradi).
pub fn restore(
    store: &dyn SecretStore,
    home: &Home,
    backup_text: &str,
    passphrase: &str,
    force: bool,
) -> Result<RestoreInfo> {
    let bad = |m: &str| StoreError::Secret(format!("zaxira fayli: {m}"));
    let mut v: Value = serde_json::from_str(backup_text).map_err(|e| bad(&e.to_string()))?;
    let ct = v
        .as_object_mut()
        .and_then(|o| o.remove("ct"))
        .and_then(|c| c.as_str().and_then(b64::decode))
        .ok_or_else(|| bad("`ct` yo'q"))?;
    if v["format"] != BACKUP_FORMAT || v["v"] != 1 || v["kdf"]["alg"] != "argon2id" {
        return Err(bad("format yoki versiya noma'lum"));
    }
    let num = |k: &str| {
        v["kdf"][k]
            .as_u64()
            .and_then(|n| u32::try_from(n).ok())
            .ok_or_else(|| bad(&format!("kdf.{k}")))
    };
    let (m, t, p) = (num("m_kib")?, num("t")?, num("p")?);
    // Sarlavhani buzib, juda katta xotira so'ratib qo'yishga yo'l qo'ymaymiz.
    if m > 1024 * 1024 || t > 16 || p > 16 {
        return Err(bad("kdf parametrlari ruxsat etilganidan katta"));
    }
    let salt = v["kdf"]["salt"]
        .as_str()
        .and_then(b64::decode)
        .ok_or_else(|| bad("salt"))?;
    let nonce = v["nonce"]
        .as_str()
        .and_then(b64::decode)
        .filter(|n| n.len() == 24)
        .ok_or_else(|| bad("nonce"))?;
    let aad = tamga_core::jcs::canonicalize(&v).map_err(|e| bad(&e.to_string()))?;
    let key = kdf(passphrase, &salt, m, t, p)?;
    let plain = XChaCha20Poly1305::new(&key.into())
        .decrypt(
            &XNonce::try_from(nonce.as_slice()).map_err(|_| bad("nonce"))?,
            Payload {
                msg: &ct,
                aad: aad.as_bytes(),
            },
        )
        .map_err(|_| {
            StoreError::Secret("parol noto'g'ri yoki zaxira fayli o'zgartirilgan".into())
        })?;
    let inner: Value = serde_json::from_slice(&plain).map_err(|e| bad(&e.to_string()))?;
    let seed = inner["signing_seed"]
        .as_str()
        .and_then(b64::decode)
        .ok_or_else(|| bad("signing_seed"))?;
    let master = inner["vault_master"]
        .as_str()
        .and_then(b64::decode)
        .filter(|k| k.len() == 32)
        .ok_or_else(|| bad("vault_master"))?;
    let anchor_pk =
        PublicKeys::from_json(&inner["anchor_public_key"]).map_err(|e| bad(&e.to_string()))?;
    let keys = keys_from_seed(&seed)?;

    if !force {
        if let Some(existing) = store.get(SIGNING_SEED)?
            && existing != seed
        {
            return Err(StoreError::Secret(
                "omborda boshqa imzo kaliti bor — ustiga yozish uchun --force".into(),
            ));
        }
        if let Ok(a) = anchor(home)
            && a.key_id() != anchor_pk.key_id()
        {
            return Err(StoreError::Secret(format!(
                "bu papkaning langar kaliti {} — zaxiradagi {} boshqa jurnalga tegishli (--force)",
                a.key_id(),
                anchor_pk.key_id()
            )));
        }
    }
    store.set(SIGNING_SEED, &seed)?;
    store.set(VAULT_MASTER, &master)?;
    store_anchor(store, &anchor_pk)?;
    discard_next(store)?;
    export_public(&anchor_pk, home)?;
    Ok(RestoreInfo {
        anchor: anchor_pk.key_id(),
        key: keys.public().key_id(),
        created: v["created"].as_str().unwrap_or("").to_owned(),
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::secrets::FileStore;

    fn setup(name: &str) -> (Home, FileStore) {
        let dir = std::env::temp_dir().join(format!("tamga-ks-{name}-{}", std::process::id()));
        std::fs::remove_dir_all(&dir).ok();
        let home = Home::at(dir.clone());
        home.ensure().unwrap();
        let store = FileStore::new(dir.join("secrets")).unwrap();
        (home, store)
    }

    #[test]
    fn anchor_survives_rotation_and_staging_is_crash_safe() {
        let (home, store) = setup("rot");
        let (k0, created) = load_or_create(&store, &home).unwrap();
        assert!(created);
        let a = anchor(&home).unwrap().key_id();
        assert_eq!(a, k0.public().key_id());

        let next = stage_next(&store).unwrap();
        assert_eq!(
            staged_next(&store).unwrap().unwrap().public().key_id(),
            next.public().key_id()
        );
        // Hali asosiy emas: qayta yuklash eski kalitni beradi.
        assert_eq!(
            load_or_create(&store, &home).unwrap().0.public().key_id(),
            a
        );
        promote_next(&store).unwrap();
        assert!(staged_next(&store).unwrap().is_none());
        let (k1, _) = load_or_create(&store, &home).unwrap();
        assert_eq!(k1.public().key_id(), next.public().key_id());
        assert_eq!(anchor(&home).unwrap().key_id(), a, "langar o'zgarmaydi");

        // L-1: public-key.json o'chirilsa, langar (K0) omboridan tiklanadi, joriy kalit (K1) emas.
        std::fs::remove_file(home.public_key()).unwrap();
        let (k_after, _) = load_or_create(&store, &home).unwrap();
        assert_eq!(
            k_after.public().key_id(),
            next.public().key_id(),
            "imzo kaliti K1 bo'lib qoladi"
        );
        assert_eq!(
            anchor(&home).unwrap().key_id(),
            a,
            "langar K0 dan tiklandi, K1 yozilmadi"
        );
        std::fs::remove_dir_all(home.root()).ok();
    }

    #[test]
    fn backup_restores_keys_and_rejects_wrong_passphrase_or_tampering() {
        let (home, store) = setup("bk");
        let (k, _) = load_or_create(&store, &home).unwrap();
        let master = vault_master(&store).unwrap();
        assert!(backup(&store, &home, "qisqa").is_err());
        let text = backup(&store, &home, "uzun-va-yaxshi-parol-2026").unwrap();
        assert!(
            !text.contains(&b64::encode(&master)),
            "master ochiq yozilmagan"
        );

        // Yangi mashina: bo'sh ombor va papka.
        let (home2, store2) = setup("bk2");
        assert!(restore(&store2, &home2, &text, "noto'g'ri-parol-0000", false).is_err());
        let mut forged: Value = serde_json::from_str(&text).unwrap();
        forged["key"] = "k:00000000000000000000000000000000".into();
        assert!(
            restore(
                &store2,
                &home2,
                &forged.to_string(),
                "uzun-va-yaxshi-parol-2026",
                false
            )
            .is_err(),
            "sarlavha AEAD bilan bog'langan"
        );

        let info = restore(&store2, &home2, &text, "uzun-va-yaxshi-parol-2026", false).unwrap();
        assert_eq!(info.key, k.public().key_id());
        assert_eq!(
            load_or_create(&store2, &home2).unwrap().0.public().key_id(),
            k.public().key_id()
        );
        assert_eq!(vault_master(&store2).unwrap(), master);
        assert_eq!(
            anchor(&home2).unwrap().key_id(),
            anchor(&home).unwrap().key_id()
        );

        // Boshqa kaliti bor ombor: --force siz rad etiladi.
        let (home3, store3) = setup("bk3");
        load_or_create(&store3, &home3).unwrap();
        assert!(restore(&store3, &home3, &text, "uzun-va-yaxshi-parol-2026", false).is_err());
        assert!(restore(&store3, &home3, &text, "uzun-va-yaxshi-parol-2026", true).is_ok());
        for h in [home, home2, home3] {
            std::fs::remove_dir_all(h.root()).ok();
        }
    }
}
