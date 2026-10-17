//! Jurnal yozuvchi va xesh-zanjir verifikatori (spec §2.2, §3, §8).

use serde_json::{Map, Value};

use crate::FORMAT_VERSION;
use crate::digest::Digest;
use crate::error::{ErrorCode, VerifyError};
use crate::jcs::{self, JcsError};
use crate::record::{self, KNOWN_EVENTS, RESERVED};

/// Bitta qatorning eng katta uzunligi (spec §10).
pub const MAX_LINE_BYTES: usize = 1 << 20;

#[derive(Debug, thiserror::Error)]
pub enum AppendError {
    #[error("`{0}` maydonini yozuvchi o'zi qo'yadi")]
    Reserved(String),
    #[error("noto'g'ri yozuv: {0}")]
    Invalid(String),
    #[error(transparent)]
    Jcs(#[from] JcsError),
}

/// Xotiradagi jurnal yozuvchi: har `append` bitta kanonik qator (`\n` bilan) qaytaradi.
/// Diskka yozish va fsync `tamga-store` vazifasi.
#[derive(Debug, Clone)]
pub struct LogWriter {
    log: String,
    hashes: Vec<Digest>,
}

impl LogWriter {
    pub fn new(log: impl Into<String>) -> Result<Self, AppendError> {
        let log = log.into();
        if !record::valid_log_id(&log) {
            return Err(AppendError::Invalid(format!("log id: {log}")));
        }
        Ok(Self {
            log,
            hashes: Vec::new(),
        })
    }

    /// Mavjud jurnal davomidan yozish uchun (hashes — verifikatsiyadan o'tgan xeshlar).
    pub fn resume(log: impl Into<String>, hashes: Vec<Digest>) -> Result<Self, AppendError> {
        let mut w = Self::new(log)?;
        w.hashes = hashes;
        Ok(w)
    }

    pub fn log_id(&self) -> &str {
        &self.log
    }

    pub fn hashes(&self) -> &[Digest] {
        &self.hashes
    }

    /// Yozuv qo'shadi. `body` — ixtiyoriy maydonlar (`agent`, `tool`, `decision`, ...).
    pub fn append(
        &mut self,
        ts: &str,
        session: &str,
        event: &str,
        body: Map<String, Value>,
    ) -> Result<String, AppendError> {
        if let Some(k) = RESERVED
            .iter()
            .chain(["hash"].iter())
            .find(|k| body.contains_key(**k))
        {
            return Err(AppendError::Reserved((*k).to_owned()));
        }
        let mut map = body;
        let prev = self.hashes.last().copied().unwrap_or(Digest::GENESIS);
        map.insert("tamga".into(), FORMAT_VERSION.into());
        map.insert("log".into(), self.log.clone().into());
        map.insert("seq".into(), (self.hashes.len() as u64).into());
        map.insert("ts".into(), ts.into());
        map.insert("session".into(), session.into());
        map.insert("event".into(), event.into());
        map.insert("prev".into(), prev.to_string().into());

        let mut value = Value::Object(map);
        let hash = record::record_hash(&value)?;
        value["hash"] = hash.to_string().into();

        // Yozuvchi o'zi ham verifikator qoidalaridan o'tadi — yaroqsiz yozuv jurnalga tushmaydi.
        record::parse_header(value.as_object().expect("obyekt")).map_err(AppendError::Invalid)?;

        let mut line = jcs::canonicalize(&value)?;
        if line.len() >= MAX_LINE_BYTES {
            return Err(AppendError::Invalid("qator 1 MiB dan uzun".into()));
        }
        line.push('\n');
        self.hashes.push(hash);
        Ok(line)
    }
}

/// Muvaffaqiyatli zanjir tekshiruvi natijasi.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct LogSummary {
    pub log: Option<String>,
    /// Har bir yozuv xeshi, `seq` tartibida — Merkle daraxti barglari.
    pub hashes: Vec<Digest>,
    pub warnings: Vec<String>,
}

impl LogSummary {
    pub fn len(&self) -> u64 {
        self.hashes.len() as u64
    }

    pub fn is_empty(&self) -> bool {
        self.hashes.is_empty()
    }
}

/// Matnni spec §2.2 bo'yicha qatorlarga bo'ladi: har qator `\n` bilan tugashi shart.
pub(crate) fn split_lines(text: &str) -> Vec<Result<&str, &str>> {
    let mut out = Vec::new();
    let mut rest = text;
    while !rest.is_empty() {
        match rest.find('\n') {
            Some(i) => {
                out.push(Ok(&rest[..i]));
                rest = &rest[i + 1..];
            }
            None => {
                out.push(Err(rest)); // oxirgi qator yakunlanmagan (masalan, yozish uzilgan)
                rest = "";
            }
        }
    }
    out
}

/// Qatorni tahlil qilib, kanonikligini tekshiradi (E_PARSE / E_NONCANONICAL).
pub(crate) fn parse_canonical(
    line: Result<&str, &str>,
    index: u64,
) -> Result<Map<String, Value>, VerifyError> {
    let line =
        line.map_err(|_| VerifyError::new(ErrorCode::Parse, index, "qator \\n bilan tugamagan"))?;
    if line.len() > MAX_LINE_BYTES {
        return Err(VerifyError::new(
            ErrorCode::Parse,
            index,
            "qator 1 MiB dan uzun",
        ));
    }
    let value: Value = serde_json::from_str(line)
        .map_err(|e| VerifyError::new(ErrorCode::Parse, index, format!("JSON emas: {e}")))?;
    let Value::Object(map) = value else {
        return Err(VerifyError::new(ErrorCode::Parse, index, "obyekt emas"));
    };
    let canonical = jcs::canonicalize(&Value::Object(map.clone()))
        .map_err(|e| VerifyError::new(ErrorCode::NonCanonical, index, e.to_string()))?;
    if canonical != line {
        return Err(VerifyError::new(
            ErrorCode::NonCanonical,
            index,
            "qator kanonik shaklda emas (bo'shliq, kalit tartibi, takror kalit yoki escape)",
        ));
    }
    Ok(map)
}

/// Jurnalni boshidan oxirigacha tekshiradi va birinchi xatoda to'xtaydi.
pub fn verify_log(text: &str) -> Result<LogSummary, VerifyError> {
    let mut summary = LogSummary::default();
    let mut last_ts: Option<String> = None;

    for (i, line) in split_lines(text).into_iter().enumerate() {
        let index = i as u64;
        let map = parse_canonical(line, index)?;

        if map.get("tamga").and_then(Value::as_str) != Some(FORMAT_VERSION) {
            return Err(VerifyError::new(
                ErrorCode::Version,
                index,
                "`tamga` \"0.1\" emas",
            ));
        }
        let header =
            record::parse_header(&map).map_err(|d| VerifyError::new(ErrorCode::Field, index, d))?;

        match &summary.log {
            None => summary.log = Some(header.log.clone()),
            Some(log) if *log != header.log => {
                return Err(VerifyError::new(
                    ErrorCode::Log,
                    index,
                    format!("log `{}` kutilgan `{log}`", header.log),
                ));
            }
            Some(_) => {}
        }
        if header.seq != index {
            return Err(VerifyError::new(
                ErrorCode::Seq,
                index,
                format!("seq {} kutilgan {index}", header.seq),
            ));
        }
        let computed = record::record_hash(&Value::Object(map))
            .map_err(|e| VerifyError::new(ErrorCode::NonCanonical, index, e.to_string()))?;
        if computed != header.hash {
            return Err(VerifyError::new(
                ErrorCode::Hash,
                index,
                format!("yozuv o'zgartirilgan: hisoblangan {computed}"),
            ));
        }
        let expected_prev = summary.hashes.last().copied().unwrap_or(Digest::GENESIS);
        if header.prev != expected_prev {
            return Err(VerifyError::new(
                ErrorCode::Prev,
                index,
                format!("zanjir uzilgan: prev kutilgan {expected_prev}"),
            ));
        }

        if !KNOWN_EVENTS.contains(&header.event.as_str()) {
            summary
                .warnings
                .push(format!("#{index}: noma'lum hodisa `{}`", header.event));
        }
        if last_ts.as_deref().is_some_and(|t| header.ts.as_str() < t) {
            summary
                .warnings
                .push(format!("#{index}: vaqt orqaga ketgan ({})", header.ts));
        }
        last_ts = Some(header.ts);
        summary.hashes.push(header.hash);
    }
    Ok(summary)
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    fn obj(v: Value) -> Map<String, Value> {
        v.as_object().unwrap().clone()
    }

    fn sample_log(n: usize) -> String {
        let mut w = LogWriter::new("t").unwrap();
        let mut text = String::new();
        for i in 0..n {
            text += &w
                .append(
                    &format!("2026-10-17T10:00:{:02}.000Z", i % 60),
                    "s1",
                    "tool.pre",
                    obj(json!({"tool": {"name": "Bash"}, "decision": {"verdict": "allow", "by": "policy"}})),
                )
                .unwrap();
        }
        text
    }

    #[test]
    fn writer_output_verifies() {
        let text = sample_log(5);
        let s = verify_log(&text).unwrap();
        assert_eq!(s.len(), 5);
        assert_eq!(s.log.as_deref(), Some("t"));
        assert!(s.warnings.is_empty());
        assert_eq!(verify_log("").unwrap().len(), 0, "bo'sh jurnal yaroqli");
    }

    #[test]
    fn reserved_fields_are_rejected() {
        let mut w = LogWriter::new("t").unwrap();
        for k in ["seq", "prev", "hash", "tamga"] {
            let err = w.append(
                "2026-10-17T10:00:00.000Z",
                "s",
                "prompt",
                obj(json!({ k: 1 })),
            );
            assert!(matches!(err, Err(AppendError::Reserved(_))), "{k}");
        }
    }

    #[test]
    fn writer_rejects_invalid_records() {
        let mut w = LogWriter::new("t").unwrap();
        assert!(w.append("bugun", "s", "prompt", Map::new()).is_err());
        assert!(
            w.append(
                "2026-10-17T10:00:00.000Z",
                "s",
                "prompt",
                obj(json!({"x": 1.5}))
            )
            .is_err()
        );
        assert!(
            w.append(
                "2026-10-17T10:00:00.000Z",
                "s",
                "tool.pre",
                obj(json!({"decision": {"verdict": "maybe", "by": "policy"}}))
            )
            .is_err()
        );
        assert!(
            w.hashes().is_empty(),
            "rad etilgan yozuv zanjirga qo'shilmaydi"
        );
    }

    #[test]
    fn unterminated_last_line_is_parse_error() {
        let text = sample_log(2);
        let cut = &text[..text.len() - 1];
        assert_eq!(verify_log(cut).unwrap_err().code, ErrorCode::Parse);
        assert_eq!(verify_log(cut).unwrap_err().index, 1);
    }

    #[test]
    fn warnings_for_unknown_event_and_clock_skew() {
        let mut w = LogWriter::new("t").unwrap();
        let mut text = w
            .append("2026-10-17T10:00:05.000Z", "s", "future.event", Map::new())
            .unwrap();
        text += &w
            .append("2026-10-17T10:00:01.000Z", "s", "prompt", Map::new())
            .unwrap();
        let s = verify_log(&text).unwrap();
        assert_eq!(s.warnings.len(), 2, "{:?}", s.warnings);
    }
}
