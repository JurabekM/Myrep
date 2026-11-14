//! KeyStore muvofiqlik testi: ochiq standart KAT vektorlari har qanday backend'da
//! (memory, SoftHSM2, haqiqiy HSM) bir xil natija berishini tekshiradi.
//!
//! Vektorlar: RFC 4493 (AES-CMAC), RFC 4231 (HMAC-SHA256), GCM spetsifikatsiyasi
//! (McGrew–Viega, test case 13/14), RFC 8032 (Ed25519).
//! Python `cryptography` 49.0 bilan mustaqil qayta tekshirilgan (2026-10-23).

use super::{KeyKind, KeyLabel, KeyStore};
use crate::CryptoError;

fn h(s: &str) -> Vec<u8> {
    // Faqat ichki konstantalar uchun; noto'g'ri hex — dasturchi xatosi.
    hex::decode(s.replace(' ', "")).unwrap_or_default()
}

fn check(name: &str, got: &[u8], want: &str) -> Result<(), String> {
    if got == h(want).as_slice() {
        Ok(())
    } else {
        Err(format!(
            "{name}: kutilgan {want}, olingan {}",
            hex::encode(got)
        ))
    }
}

fn e(name: &str) -> impl Fn(CryptoError) -> String + '_ {
    move |err| format!("{name}: {err}")
}

/// Barcha KAT'larni bajaradi. `prefix` — vaqtinchalik kalit yorliqlari prefiksi
/// (bir HSM token'ida takroriy ishga tushirish uchun noyob bo'lishi kerak).
pub fn check_conformance(ks: &dyn KeyStore, prefix: &str) -> Result<(), String> {
    let l = |s: &str| KeyLabel::new(format!("{prefix}.{s}"));

    // RFC 4493 AES-128-CMAC
    let cmac = l("cmac");
    ks.import_secret(
        &cmac,
        KeyKind::Aes128,
        &h("2b7e151628aed2a6abf7158809cf4f3c"),
    )
    .map_err(e("cmac import"))?;
    let m = h(
        "6bc1bee22e409f96e93d7e117393172aae2d8a571e03ac9c9eb76fac45af8e51\
               30c81c46a35ce411e5fbc1191a0a52eff69f2445df4f9b17ad2b417be66c3710",
    );
    for (n, want) in [
        (0, "bb1d6929e95937287fa37d129b756746"),
        (16, "070a16b46b4d4144f79bdd9dd04a287c"),
        (40, "dfa66747de9ae63030ca32611497c827"),
        (64, "51f0bebf7e3b9d92fc49741779363cfe"),
    ] {
        let got = ks.aes_cmac(&cmac, &m[..n]).map_err(e("cmac"))?;
        check(&format!("RFC4493 len={n}"), &got, want)?;
    }

    // RFC 4231 HMAC-SHA256, test case 6 va 7 (131 baytli kalit). 1–5 holatlar ataylab
    // ishlatilmaydi: ularning kalitlari 32 baytdan qisqa, siyosatimiz (va SoftHSM2) buni rad etadi.
    let key = vec![0xaa; 131];
    for (i, msg, want) in [
        (6, &b"Test Using Larger Than Block-Size Key - Hash Key First"[..], "60e431591ee0b67f0d8a26aacbf5b77f8e0bc6213728c5140546040f0ee37f54"),
        (7, &b"This is a test using a larger than block-size key and a larger than block-size data. The key needs to be hashed before being used by the HMAC algorithm."[..], "9b09ffa71b942fcb27635fbcd5b0e944bfdc63644f0713938a7f51535c3a35e2"),
    ] {
        let lab = l(&format!("hmac{i}"));
        ks.import_secret(&lab, KeyKind::HmacSha256, &key).map_err(e("hmac import"))?;
        check(&format!("RFC4231 #{i}"), &ks.hmac_sha256(&lab, msg).map_err(e("hmac"))?, want)?;
    }
    if ks
        .import_secret(&l("hmac-short"), KeyKind::HmacSha256, &[1; 20])
        .is_ok()
    {
        return Err("HMAC: 32 baytdan qisqa kalit qabul qilindi".into());
    }

    // AES-256-GCM: ochish KAT (nonce backend ichida generatsiya qilinadi, shuning uchun
    // shifrlash KAT emas, balki ochish KAT + roundtrip).
    let gcm = l("gcm");
    ks.import_secret(&gcm, KeyKind::Aes256, &[0u8; 32])
        .map_err(e("gcm import"))?;
    let pt = ks
        .aes_gcm_open(
            &gcm,
            &[0; 12],
            b"",
            &h("cea7403d4d606b6e074ec5d3baf39d18 d0d1c8a799996bf0265b98b5d48ab919"),
        )
        .map_err(e("GCM TC14"))?;
    check("GCM TC14", &pt, "00000000000000000000000000000000")?;
    let pt = ks
        .aes_gcm_open(&gcm, &[0; 12], b"", &h("530f8afbc74536b9a963b4f1c4cb738b"))
        .map_err(e("GCM TC13"))?;
    check("GCM TC13", &pt, "")?;
    if ks
        .aes_gcm_open(&gcm, &[0; 12], b"x", &h("530f8afbc74536b9a963b4f1c4cb738b"))
        .is_ok()
    {
        return Err("GCM: noto'g'ri AAD qabul qilindi".into());
    }
    let s = ks
        .aes_gcm_seal(&gcm, b"aad", b"roundtrip")
        .map_err(e("GCM seal"))?;
    let back = ks
        .aes_gcm_open(&gcm, &s.nonce, b"aad", &s.ciphertext)
        .map_err(e("GCM open"))?;
    check("GCM roundtrip", &back, &hex::encode(b"roundtrip"))?;

    // RFC 8032 Ed25519
    for (i, sk, pk, msg, sig) in [
        (
            1,
            "9d61b19deffd5a60ba844af492ec2cc44449c5697b326919703bac031cae7f60",
            "d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a",
            vec![],
            "e5564300c360ac729086e2cc806e828a84877f1eb8e5d974d873e065224901555fb8821590a33bacc61e39701cf9b46bd25bf5f0595bbe24655141438e7a100b",
        ),
        (
            2,
            "4ccd089b28ff96da9db6c346ec114e0f5b8a319f35aba624da8cf6ed4fb8a6fb",
            "3d4017c3e843895a92b70aa74d1b7ebc9c982ccf2ec4968cc0cd55f12af4660c",
            vec![0x72],
            "92a009a9f0d4cab8720e820b5f642540a2b27b5416503f8fb3762223ebdb69da085ac1e43e15996e458f3613d0f11d8c387b2eaeb4302aeeb00d291612bb0c00",
        ),
    ] {
        let lab = l(&format!("ed{i}"));
        ks.import_secret(&lab, KeyKind::Ed25519, &h(sk)).map_err(e("ed25519 import"))?;
        check(&format!("RFC8032 #{i} pk"), &ks.ed25519_public_key(&lab).map_err(e("ed pk"))?, pk)?;
        check(&format!("RFC8032 #{i} sig"), &ks.ed25519_sign(&lab, &msg).map_err(e("ed sign"))?, sig)?;
    }

    // Generatsiya qilingan kalitlar ishlaydi va turlar tekshiriladi.
    let gen = l("gen-aes128");
    ks.ensure_key(&gen, KeyKind::Aes128).map_err(e("ensure"))?;
    ks.ensure_key(&gen, KeyKind::Aes128)
        .map_err(e("ensure 2"))?;
    ks.aes_cmac(&gen, b"x").map_err(e("cmac gen"))?;
    if ks.hmac_sha256(&gen, b"x").is_ok() {
        return Err("tur tekshiruvi: AES kaliti HMAC uchun qabul qilindi".into());
    }
    let ged = l("gen-ed25519");
    ks.ensure_key(&ged, KeyKind::Ed25519)
        .map_err(e("ensure ed"))?;
    let pk = ks.ed25519_public_key(&ged).map_err(e("ed pk gen"))?;
    let sig = ks.ed25519_sign(&ged, b"m").map_err(e("ed sign gen"))?;
    let vk =
        ed25519_dalek::VerifyingKey::from_bytes(&pk).map_err(|_| "ed pk noto'g'ri".to_string())?;
    vk.verify_strict(b"m", &ed25519_dalek::Signature::from_bytes(&sig))
        .map_err(|_| "generatsiya qilingan Ed25519 imzosi tekshirilmadi".to_string())?;
    Ok(())
}
