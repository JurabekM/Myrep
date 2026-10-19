//! Imzolangan checkpoint'lar (signed tree head) va to'liq tekshiruv — spec §7, §8.

use serde_json::{Map, Value, json};

use crate::chain::{self, LogSummary};
use crate::digest::Digest;
use crate::error::{ErrorCode, VerifyError};
use crate::jcs::{self, JcsError};
use crate::keys::{PublicKeys, SigningKeys};
use crate::{FORMAT_VERSION, b64, merkle, record};

pub const SIGN_DOMAIN: &[u8] = b"TAMGA-CHECKPOINT-v1\0";

/// `M = "TAMGA-CHECKPOINT-v1" || 0x00 || JCS(checkpoint \ "sig")`
pub fn signing_message(checkpoint: &Value) -> Result<Vec<u8>, JcsError> {
    let body = jcs::canonicalize_without(checkpoint, "sig")?;
    Ok([SIGN_DOMAIN, body.as_bytes()].concat())
}

#[derive(Debug, thiserror::Error)]
pub enum CheckpointError {
    #[error("checkpoint o'lchami 1 dan {0} gacha bo'lishi shart")]
    Size(u64),
    #[error("noto'g'ri maydon: {0}")]
    Invalid(String),
    #[error(transparent)]
    Jcs(#[from] JcsError),
}

/// Birinchi `size` yozuv uchun checkpoint yaratadi va imzolaydi. Qaytgan qiymat — `\n` li qator.
/// ML-DSA deterministik imzolanadi (test vektorlari uchun); ishlab chiqarishda [`create_hedged`].
pub fn create(
    log: &str,
    hashes: &[Digest],
    size: u64,
    ts: &str,
    keys: &SigningKeys,
) -> Result<String, CheckpointError> {
    create_with(log, hashes, size, ts, keys, None)
}

/// [`create`] ning ishlab chiqarish varianti: ML-DSA hedged imzo, `rnd` — 32 tasodifiy bayt.
pub fn create_hedged(
    log: &str,
    hashes: &[Digest],
    size: u64,
    ts: &str,
    keys: &SigningKeys,
    rnd: &[u8; 32],
) -> Result<String, CheckpointError> {
    create_with(log, hashes, size, ts, keys, Some(rnd))
}

fn create_with(
    log: &str,
    hashes: &[Digest],
    size: u64,
    ts: &str,
    keys: &SigningKeys,
    rnd: Option<&[u8; 32]>,
) -> Result<String, CheckpointError> {
    if size == 0 || size > hashes.len() as u64 {
        return Err(CheckpointError::Size(hashes.len() as u64));
    }
    if !record::valid_log_id(log) || !record::valid_timestamp(ts) {
        return Err(CheckpointError::Invalid("log yoki ts".into()));
    }
    let covered = &hashes[..size as usize];
    let mut cp = json!({
        "tamga": FORMAT_VERSION,
        "type": "checkpoint",
        "log": log,
        "size": size,
        "root": merkle::root(covered).to_string(),
        "last": covered[covered.len() - 1].to_string(),
        "ts": ts,
        "key": keys.public().key_id(),
    });
    let msg = signing_message(&cp)?;
    let sig = match rnd {
        Some(rnd) => keys.sign_hedged(&msg, rnd),
        None => keys.sign(&msg),
    };
    cp["sig"] = json!({
        "ed25519": b64::encode(&sig.ed),
        "ml-dsa-65": b64::encode(&sig.ml),
    });
    let mut line = jcs::canonicalize(&cp)?;
    line.push('\n');
    Ok(line)
}

/// Imzosi tekshirilgan checkpoint maydonlari.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Checkpoint {
    pub log: String,
    pub size: u64,
    pub root: Digest,
    pub last: Digest,
    pub ts: String,
}

/// Bitta checkpoint obyektini shakl va imzo bo'yicha tekshiradi.
pub fn verify_one(
    map: &Map<String, Value>,
    pk: &PublicKeys,
    index: u64,
) -> Result<Checkpoint, VerifyError> {
    let fmt = |d: &str| VerifyError::new(ErrorCode::CkptFormat, index, d.to_owned());
    let s = |k: &str| {
        map.get(k)
            .and_then(Value::as_str)
            .ok_or_else(|| fmt(&format!("`{k}` satr emas")))
    };
    let digest = |k: &str| {
        s(k).and_then(|v| Digest::parse(v).ok_or_else(|| fmt(&format!("`{k}` digest emas"))))
    };

    if s("tamga")? != FORMAT_VERSION || s("type")? != "checkpoint" {
        return Err(fmt("tamga/type noto'g'ri"));
    }
    let log = s("log")?;
    let size = map
        .get("size")
        .and_then(Value::as_u64)
        .filter(|n| *n >= 1)
        .ok_or_else(|| fmt("`size` musbat butun son emas"))?;
    let root = digest("root")?;
    let last = digest("last")?;
    let ts = s("ts")?;
    if !record::valid_timestamp(ts) || !record::valid_log_id(log) {
        return Err(fmt("`ts` yoki `log` shakli noto'g'ri"));
    }
    if s("key")? != pk.key_id() {
        return Err(fmt("`key` berilgan ochiq kalitga mos emas"));
    }
    let sig = map
        .get("sig")
        .and_then(Value::as_object)
        .ok_or_else(|| fmt("`sig` obyekt emas"))?;
    let sig_bytes = |k: &str| {
        sig.get(k)
            .and_then(Value::as_str)
            .and_then(b64::decode)
            .ok_or_else(|| fmt(&format!("`sig.{k}` base64url emas")))
    };
    let (ed, ml) = (sig_bytes("ed25519")?, sig_bytes("ml-dsa-65")?);

    let msg = signing_message(&Value::Object(map.clone()))
        .map_err(|e| VerifyError::new(ErrorCode::CkptFormat, index, e.to_string()))?;
    if !pk.verify(&msg, &ed, &ml) {
        return Err(VerifyError::new(
            ErrorCode::CkptSig,
            index,
            "imzo tasdiqlanmadi",
        ));
    }
    Ok(Checkpoint {
        log: log.to_owned(),
        size,
        root,
        last,
        ts: ts.to_owned(),
    })
}

/// To'liq hisobot.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Report {
    pub log: LogSummary,
    pub checkpoints: Vec<Checkpoint>,
    /// Kalitlar zanjiri: langar (operator bergan) va kuchga kirgan har almashtirishdan keyingi kalit.
    pub keys: Vec<String>,
    /// Kalitlar bo'yicha ogohlantirishlar (buzilgan deb e'lon qilingan kalit, tasdiqlanmagan almashtirish).
    pub key_warnings: Vec<String>,
}

/// Jurnal + checkpoint fayli + **langar** ochiq kalit: spec §8 bo'yicha to'liq tekshiruv.
/// Avval zanjir, keyin har bir checkpoint (imzo → o'lcham → ildiz). Checkpoint faqat shu paytdagi
/// faol kalit bilan qabul qilinadi; u qamragan `key.rotate` yozuvlari tartib bilan qo'llanadi
/// (spec §7.5) va keyingi checkpoint'lar yangi kalitni talab qiladi.
pub fn verify_all(
    log_text: &str,
    checkpoint_text: &str,
    anchor: &PublicKeys,
) -> Result<Report, VerifyError> {
    let summary = chain::verify_log(log_text)?;
    let mut checkpoints = Vec::new();
    let mut active = anchor.clone();
    let mut keys = vec![anchor.key_id()];
    let mut key_warnings = Vec::new();
    let mut applied = 0usize;
    let mut prev_size = 0u64;

    for (i, line) in chain::split_lines(checkpoint_text).into_iter().enumerate() {
        let index = i as u64;
        let map = chain::parse_canonical(line, index)
            .map_err(|e| VerifyError::new(ErrorCode::CkptFormat, index, e.detail))?;
        let cp = verify_one(&map, &active, index)?;

        // L-2: checkpoint'lar o'suvchi tartibda bo'lishi shart (keyingisi oldingisidan kam qamramaydi).
        if cp.size < prev_size {
            return Err(VerifyError::new(
                ErrorCode::CkptFormat,
                index,
                format!(
                    "checkpoint {} yozuvni qamraydi, oldingisi {} — kamaygan",
                    cp.size, prev_size
                ),
            ));
        }
        prev_size = cp.size;

        if summary.log.as_deref().is_some_and(|l| l != cp.log) {
            return Err(VerifyError::new(
                ErrorCode::CkptFormat,
                index,
                "checkpoint boshqa jurnalga tegishli",
            ));
        }
        if cp.size > summary.len() {
            return Err(VerifyError::new(
                ErrorCode::CkptSize,
                index,
                format!(
                    "checkpoint {} yozuvni qamraydi, jurnalda {} ta — jurnal qisqartirilgan",
                    cp.size,
                    summary.len()
                ),
            ));
        }
        let covered = &summary.hashes[..cp.size as usize];
        if merkle::root(covered) != cp.root || covered[covered.len() - 1] != cp.last {
            return Err(VerifyError::new(
                ErrorCode::CkptRoot,
                index,
                format!(
                    "dastlabki {} yozuv checkpoint'dan keyin qayta yozilgan",
                    cp.size
                ),
            ));
        }
        // Faol kalit imzolagan checkpoint qamragan almashtirishlar endi tasdiqlangan.
        while let Some(r) = summary.rotations.get(applied).filter(|r| r.seq < cp.size) {
            if r.from != active.key_id() {
                return Err(VerifyError::new(
                    ErrorCode::KeyRotate,
                    r.seq,
                    format!(
                        "almashtirish `{}` dan, lekin faol kalit `{}`",
                        r.from,
                        active.key_id()
                    ),
                ));
            }
            if r.reason == "compromise" {
                key_warnings.push(format!(
                    "#{}: kalit {} buzilgan deb e'lon qilingan — u imzolagan checkpoint'larga faqat guvoh nusxasi bilan ishoning",
                    r.seq, r.from
                ));
            }
            active = r.to.clone();
            keys.push(active.key_id());
            applied += 1;
        }
        checkpoints.push(cp);
    }
    for r in &summary.rotations[applied..] {
        key_warnings.push(format!(
            "#{}: {} ga almashtirish hali eski kalit imzolagan checkpoint bilan tasdiqlanmagan",
            r.seq,
            r.to.key_id()
        ));
    }
    Ok(Report {
        log: summary,
        checkpoints,
        keys,
        key_warnings,
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::chain::LogWriter;

    fn setup(n: usize) -> (String, Vec<Digest>, SigningKeys) {
        let mut w = LogWriter::new("cp").unwrap();
        let mut text = String::new();
        for i in 0..n {
            text += &w
                .append(
                    &format!("2026-10-17T10:00:{i:02}.000Z"),
                    "s",
                    "prompt",
                    Map::new(),
                )
                .unwrap();
        }
        (
            text,
            w.hashes().to_vec(),
            SigningKeys::from_seeds(&[1; 32], &[2; 32]),
        )
    }

    #[test]
    fn valid_checkpoints_pass() {
        let (text, hashes, keys) = setup(6);
        let mut cps = create("cp", &hashes, 3, "2026-10-17T10:01:00.000Z", &keys).unwrap();
        cps += &create("cp", &hashes, 6, "2026-10-17T10:02:00.000Z", &keys).unwrap();
        let r = verify_all(&text, &cps, &keys.public()).unwrap();
        assert_eq!(r.checkpoints.len(), 2);
        assert_eq!(r.checkpoints[1].root, merkle::root(&hashes));
    }

    #[test]
    fn truncated_log_is_detected() {
        let (text, hashes, keys) = setup(5);
        let cps = create("cp", &hashes, 5, "2026-10-17T10:01:00.000Z", &keys).unwrap();
        let lines: Vec<&str> = text.split_inclusive('\n').collect();
        let truncated: String = lines[..4].concat();
        let err = verify_all(&truncated, &cps, &keys.public()).unwrap_err();
        assert_eq!((err.code, err.index), (ErrorCode::CkptSize, 0));
    }

    #[test]
    fn rewritten_history_is_detected() {
        // Hujumchi oxirgi 2 yozuvni o'chirib, o'rniga zanjirni to'g'ri davom ettiradigan yangilarini yozdi.
        let (text, hashes, keys) = setup(5);
        let cps = create("cp", &hashes, 5, "2026-10-17T10:01:00.000Z", &keys).unwrap();
        let lines: Vec<&str> = text.split_inclusive('\n').collect();
        let mut w = LogWriter::resume("cp", hashes[..3].to_vec()).unwrap();
        let mut forged: String = lines[..3].concat();
        for i in 0..2 {
            forged += &w
                .append(
                    &format!("2026-10-17T10:00:{i:02}.500Z"),
                    "s",
                    "prompt",
                    Map::new(),
                )
                .unwrap();
        }
        assert!(
            chain::verify_log(&forged).is_ok(),
            "zanjirning o'zi buni sezmaydi"
        );
        let err = verify_all(&forged, &cps, &keys.public()).unwrap_err();
        assert_eq!(err.code, ErrorCode::CkptRoot);
    }

    #[test]
    fn signature_and_key_errors() {
        let (text, hashes, keys) = setup(2);
        let cps = create("cp", &hashes, 2, "2026-10-17T10:01:00.000Z", &keys).unwrap();
        let other = SigningKeys::from_seeds(&[3; 32], &[4; 32]);
        assert_eq!(
            verify_all(&text, &cps, &other.public()).unwrap_err().code,
            ErrorCode::CkptFormat
        );

        // Imzolangan maydonni o'zgartirish (size 2 → 1) va kanonik shaklni saqlash.
        let mut v: Value = serde_json::from_str(cps.trim_end()).unwrap();
        v["size"] = 1.into();
        let forged = jcs::canonicalize(&v).unwrap() + "\n";
        assert_eq!(
            verify_all(&text, &forged, &keys.public()).unwrap_err().code,
            ErrorCode::CkptSig
        );
    }

    #[test]
    fn checkpoint_size_must_not_decrease() {
        // L-2: kamayuvchi tartibdagi checkpoint'lar (4 dan keyin 2) rad etiladi.
        let (text, hashes, keys) = setup(4);
        let ts = "2026-10-17T10:01:00.000Z";
        let cps = create("cp", &hashes, 4, ts, &keys).unwrap()
            + &create("cp", &hashes, 2, ts, &keys).unwrap();
        let e = verify_all(&text, &cps, &keys.public()).unwrap_err();
        assert_eq!((e.code, e.index), (ErrorCode::CkptFormat, 1));
    }

    /// 0..3 yozuv, #3 = A→B almashtirish, 4..6 yozuv. Checkpoint'lar: A(4), B(7).
    fn rotated() -> (String, Vec<Digest>, SigningKeys, SigningKeys) {
        let (a, b) = (
            SigningKeys::from_seeds(&[1; 32], &[2; 32]),
            SigningKeys::from_seeds(&[5; 32], &[6; 32]),
        );
        let mut w = LogWriter::new("cp").unwrap();
        let mut text = String::new();
        for i in 0..7u64 {
            let ts = format!("2026-10-17T10:00:{i:02}.000Z");
            text += &if i == 3 {
                let body = crate::rotation::body("cp", 3, &a.public(), &b, "scheduled", None);
                w.append(&ts, "tamga", crate::rotation::EVENT, body)
                    .unwrap()
            } else {
                w.append(&ts, "s", "prompt", Map::new()).unwrap()
            };
        }
        (text, w.hashes().to_vec(), a, b)
    }

    #[test]
    fn rotation_hands_over_to_new_key() {
        let (text, hashes, a, b) = rotated();
        let ts = "2026-10-17T10:01:00.000Z";
        let cps =
            create("cp", &hashes, 4, ts, &a).unwrap() + &create("cp", &hashes, 7, ts, &b).unwrap();
        let rep = verify_all(&text, &cps, &a.public()).unwrap();
        assert_eq!(rep.keys, vec![a.public().key_id(), b.public().key_id()]);
        assert!(rep.key_warnings.is_empty());

        // Almashtirishdan keyin eski kalit bilan imzolash rad etiladi.
        let old =
            create("cp", &hashes, 4, ts, &a).unwrap() + &create("cp", &hashes, 7, ts, &a).unwrap();
        let e = verify_all(&text, &old, &a.public()).unwrap_err();
        assert_eq!((e.code, e.index), (ErrorCode::CkptFormat, 1));

        // Eski kalit qamramagan almashtirish kuchga kirmaydi: yangi kalit hali faol emas.
        let skip = create("cp", &hashes, 7, ts, &b).unwrap();
        let e = verify_all(&text, &skip, &a.public()).unwrap_err();
        assert_eq!((e.code, e.index), (ErrorCode::CkptFormat, 0));

        // Hali checkpoint yo'q: ogohlantirish, xato emas.
        let rep = verify_all(&text, "", &a.public()).unwrap();
        assert_eq!(rep.key_warnings.len(), 1);
    }

    #[test]
    fn rotation_from_wrong_key_or_forged_proof_is_rejected() {
        let (_, _, a, b) = rotated();
        let c = SigningKeys::from_seeds(&[8; 32], &[9; 32]);
        let ts = "2026-10-17T10:00:00.000Z";
        // C→B almashtirish, lekin faol kalit A.
        let mut w = LogWriter::new("cp").unwrap();
        let mut text = w.append(ts, "s", "prompt", Map::new()).unwrap();
        text += &w
            .append(
                ts,
                "tamga",
                crate::rotation::EVENT,
                crate::rotation::body("cp", 1, &c.public(), &b, "scheduled", None),
            )
            .unwrap();
        let cps = create("cp", w.hashes(), 2, ts, &a).unwrap();
        let e = verify_all(&text, &cps, &a.public()).unwrap_err();
        assert_eq!((e.code, e.index), (ErrorCode::KeyRotate, 1));

        // Isbot boshqa seq uchun qo'yilgan — zanjirning o'zi rad etadi.
        let mut w = LogWriter::new("cp").unwrap();
        let text = w
            .append(
                ts,
                "tamga",
                crate::rotation::EVENT,
                crate::rotation::body("cp", 9, &a.public(), &b, "scheduled", None),
            )
            .unwrap();
        let e = chain::verify_log(&text).unwrap_err();
        assert_eq!((e.code, e.index), (ErrorCode::KeyRotate, 0));
    }
}
