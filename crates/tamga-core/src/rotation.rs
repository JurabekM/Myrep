//! Imzo kalitini jurnal ichida almashtirish — spec §7.5.
//!
//! `key.rotate` yozuvi yangi ochiq kalitni va **yangi** kalit bilan qo'yilgan egalik isbotini
//! olib yuradi. Uni **eski** kalit imzolagan checkpoint qamraganda almashtirish kuchga kiradi:
//! shundan keyingi checkpoint'lar faqat yangi kalit bilan qabul qilinadi. Auditor faqat
//! birinchi (langar) kalitni operatordan oladi, qolgan zanjirni jurnalning o'zi isbotlaydi.

use serde_json::{Map, Value, json};

use crate::b64;
use crate::jcs;
use crate::keys::{PublicKeys, SigningKeys};

pub const EVENT: &str = "key.rotate";
/// Yozuvdagi a'zo nomi.
pub const MEMBER: &str = "key_rotation";
/// Isbot imzosi domeni — checkpoint imzosi bilan aralashmaydi.
pub const DOMAIN: &[u8] = b"TAMGA-ROTATE-v1\0";
/// Isbot uchun FIPS 204 kontekst satri.
pub const CONTEXT: &[u8] = b"tamga-rotate";
/// Ruxsat etilgan sabablar.
pub const REASONS: [&str; 3] = ["scheduled", "compromise", "restore"];

/// Isbot imzolanadigan xabar: `DOMAIN || JCS({"from","log","seq","to"})`.
pub fn proof_message(log: &str, seq: u64, from: &str, to: &str) -> Vec<u8> {
    let body = json!({"from": from, "log": log, "seq": seq, "to": to});
    let mut m = DOMAIN.to_vec();
    m.extend_from_slice(
        jcs::canonicalize(&body)
            .expect("oddiy obyekt kanonik")
            .as_bytes(),
    );
    m
}

/// `key.rotate` yozuvining tanasi (`append` ga beriladi). `seq` — yozuv oladigan raqam.
/// `rnd` — ML-DSA hedged imzosi uchun (test vektorlarida `None` — deterministik).
pub fn body(
    log: &str,
    seq: u64,
    old: &PublicKeys,
    new: &SigningKeys,
    reason: &str,
    rnd: Option<&[u8; 32]>,
) -> Map<String, Value> {
    let new_pk = new.public();
    let (from, to) = (old.key_id(), new_pk.key_id());
    let sig = new.sign_with(&proof_message(log, seq, &from, &to), CONTEXT, rnd);
    let member = json!({
        "from": from,
        "to": to,
        "reason": reason,
        "ed25519": b64::encode(&new_pk.ed_bytes()),
        "ml-dsa-65": b64::encode(&new_pk.ml_bytes()),
        "proof": {"ed25519": b64::encode(&sig.ed), "ml-dsa-65": b64::encode(&sig.ml)},
    });
    let mut m = Map::new();
    m.insert(MEMBER.into(), member);
    m
}

/// Tekshirilgan almashtirish.
#[derive(Clone)]
pub struct Rotation {
    pub seq: u64,
    pub from: String,
    pub to: PublicKeys,
    pub reason: String,
}

impl PartialEq for Rotation {
    fn eq(&self, o: &Self) -> bool {
        (self.seq, &self.from, self.to.key_id(), &self.reason)
            == (o.seq, &o.from, o.to.key_id(), &o.reason)
    }
}

impl Eq for Rotation {}

impl std::fmt::Debug for Rotation {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("Rotation")
            .field("seq", &self.seq)
            .field("from", &self.from)
            .field("to", &self.to.key_id())
            .field("reason", &self.reason)
            .finish()
    }
}

/// Yozuvdan almashtirishni o'qiydi va o'z-o'zidan tekshiriladigan qismlarini tekshiradi:
/// shakl, `to` = yangi kalitlardan hisoblangan identifikator, egalik isboti.
/// `from` ning faol kalitga mosligini chaqiruvchi (verifikator) tekshiradi.
pub fn parse(record: &Map<String, Value>, log: &str, seq: u64) -> Result<Rotation, String> {
    let m = record
        .get(MEMBER)
        .and_then(Value::as_object)
        .ok_or("`key_rotation` obyekti yo'q")?;
    let s = |k: &str| {
        m.get(k)
            .and_then(Value::as_str)
            .ok_or_else(|| format!("`key_rotation.{k}` satr emas"))
    };
    let bytes = |v: Option<&Value>, k: &str| {
        v.and_then(Value::as_str)
            .and_then(b64::decode)
            .ok_or_else(|| format!("`{k}` base64url emas"))
    };
    let (from, to, reason) = (s("from")?, s("to")?, s("reason")?);
    if !REASONS.contains(&reason) {
        return Err(format!("noma'lum sabab `{reason}`"));
    }
    let pk = PublicKeys::from_bytes(
        &bytes(m.get("ed25519"), "ed25519")?,
        &bytes(m.get("ml-dsa-65"), "ml-dsa-65")?,
    )
    .map_err(|e| e.to_string())?;
    if pk.key_id() != to {
        return Err("`to` yangi ochiq kalitlarga mos emas".into());
    }
    if from == to {
        return Err("kalit o'ziga almashtirilgan".into());
    }
    let proof = m
        .get("proof")
        .and_then(Value::as_object)
        .ok_or("`proof` obyekt emas")?;
    let (ed, ml) = (
        bytes(proof.get("ed25519"), "proof.ed25519")?,
        bytes(proof.get("ml-dsa-65"), "proof.ml-dsa-65")?,
    );
    if !pk.verify_with(&proof_message(log, seq, from, to), CONTEXT, &ed, &ml) {
        return Err("egalik isboti (yangi kalit imzosi) tasdiqlanmadi".into());
    }
    Ok(Rotation {
        seq,
        from: from.to_owned(),
        to: pk,
        reason: reason.to_owned(),
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    fn k(n: u8) -> SigningKeys {
        SigningKeys::from_seeds(&[n; 32], &[n + 1; 32])
    }

    #[test]
    fn body_round_trips_and_binds_log_and_seq() {
        let (old, new) = (k(1), k(3));
        let b = body("L", 5, &old.public(), &new, "scheduled", None);
        let r = parse(&b, "L", 5).unwrap();
        assert_eq!(r.from, old.public().key_id());
        assert_eq!(r.to.key_id(), new.public().key_id());
        // Isbot boshqa joyga ko'chirilsa yaroqsiz.
        assert!(parse(&b, "L", 6).unwrap_err().contains("isbot"));
        assert!(parse(&b, "M", 5).unwrap_err().contains("isbot"));
    }

    #[test]
    fn foreign_key_or_bad_fields_are_rejected() {
        let (old, new, other) = (k(1), k(3), k(5));
        let mut b = body("L", 0, &old.public(), &new, "compromise", None);
        // Boshqa birovning ochiq kaliti — isbot unga tegishli emas.
        let other_pk = other.public();
        let m = b.get_mut(MEMBER).unwrap().as_object_mut().unwrap();
        m.insert("ed25519".into(), b64::encode(&other_pk.ed_bytes()).into());
        m.insert("ml-dsa-65".into(), b64::encode(&other_pk.ml_bytes()).into());
        m.insert("to".into(), other_pk.key_id().into());
        assert!(parse(&b, "L", 0).unwrap_err().contains("isbot"));

        let mut b = body("L", 0, &old.public(), &new, "scheduled", None);
        b.get_mut(MEMBER).unwrap()["reason"] = "whim".into();
        assert!(parse(&b, "L", 0).unwrap_err().contains("sabab"));
    }
}
