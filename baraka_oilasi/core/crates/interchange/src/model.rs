//! Shifrlangan tarkib: JSON Lines. Birinchi qator — `meta`, keyin `row` qatorlari.
use serde::{Deserialize, Serialize};
use serde_json::Value;

use crate::canon::{canonical, Row};
use crate::{InterchangeError, FORMAT_VERSION};

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum Mode {
    /// Barcha yozuvlar (zaxira nusxa yoki birinchi sinxronlash).
    Full,
    /// Faqat qabul qiluvchida bo'lmasligi mumkin bo'lgan yozuvlar.
    Incremental,
    /// Yangi qurilmani ulash (8.5): to'liq, kalit — bir martalik ulash siri.
    Pairing,
}

impl Mode {
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Full => "FULL",
            Self::Incremental => "INCREMENTAL",
            Self::Pairing => "PAIRING",
        }
    }
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
pub struct Meta {
    pub format_version: u32,
    /// Manba bazasining sxema versiyasi (`PRAGMA user_version`).
    pub schema_version: i64,
    pub household_id: String,
    pub source_device_id: String,
    pub source_device_name: String,
    /// Shu eksportning identifikatori: qabul qiluvchi keyingi eksportida `ackExportId` qiladi.
    pub export_id: String,
    /// Manba qurilma oxirgi marta qabul qilgan, qabul qiluvchining eksporti.
    pub ack_export_id: Option<String>,
    pub mode: Mode,
    pub exported_at: String,
    pub row_count: u64,
    /// Rolli qurilma uchun ulash fayli (ADR-0003): yangi qurilma rolini shundan biladi.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub audience: Option<Audience>,
}

/// Fayl kim uchun kamaytirilgan: rol va bog'langan Kasb-kor makoni.
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
pub struct Audience {
    pub role: String,
    pub space_id: String,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(tag = "kind", rename_all = "camelCase", deny_unknown_fields)]
enum Line {
    Meta(Meta),
    Row { table: String, data: Row },
}

/// Bitta jadval yozuvi.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct RowRecord {
    pub table: String,
    pub data: Row,
}

fn valid_ident(s: &str) -> bool {
    !s.is_empty()
        && s.len() <= 64
        && s.bytes()
            .all(|b| b.is_ascii_lowercase() || b.is_ascii_digit() || b == b'_')
}

fn valid_value(v: &Value) -> bool {
    match v {
        Value::Null | Value::String(_) => true,
        Value::Number(n) => n.is_i64(),
        Value::Object(_) => crate::canon::blob_bytes(v).is_some(),
        Value::Bool(_) | Value::Array(_) => false,
    }
}

/// Tarkibni yozadi: `meta` (`rowCount` to'ldiriladi) va yozuvlar. Har qator kanonik JSON.
pub fn encode(meta: &Meta, rows: &[RowRecord]) -> Result<Vec<u8>, InterchangeError> {
    let mut meta = meta.clone();
    meta.format_version = FORMAT_VERSION;
    meta.row_count = u64::try_from(rows.len()).map_err(|_| InterchangeError::Corrupt)?;
    let mut out = String::new();
    let head = serde_json::to_value(Line::Meta(meta)).map_err(|_| InterchangeError::Corrupt)?;
    out.push_str(&canonical(&head)?);
    out.push('\n');
    for r in rows {
        if !valid_ident(&r.table) || !r.data.iter().all(|(k, v)| valid_ident(k) && valid_value(v)) {
            return Err(InterchangeError::Corrupt);
        }
        let line = serde_json::to_value(Line::Row {
            table: r.table.clone(),
            data: r.data.clone(),
        })
        .map_err(|_| InterchangeError::Corrupt)?;
        out.push_str(&canonical(&line)?);
        out.push('\n');
    }
    Ok(out.into_bytes())
}

/// Tarkibni o'qiydi va tekshiradi: birinchi qator `meta`, yozuvlar soni mos, jadval va
/// ustun nomlari `[a-z0-9_]`, qiymatlar ruxsat etilgan turlarda.
pub fn decode(bytes: &[u8]) -> Result<(Meta, Vec<RowRecord>), InterchangeError> {
    let text = std::str::from_utf8(bytes).map_err(|_| InterchangeError::Corrupt)?;
    let mut lines = text.split_terminator('\n');
    let meta = match lines.next().map(serde_json::from_str::<Line>) {
        Some(Ok(Line::Meta(m))) => m,
        _ => return Err(InterchangeError::Corrupt),
    };
    if meta.format_version != FORMAT_VERSION {
        return Err(InterchangeError::VersionUnsupported);
    }
    let mut rows = Vec::new();
    for l in lines {
        match serde_json::from_str::<Line>(l) {
            Ok(Line::Row { table, data })
                if valid_ident(&table)
                    && data.iter().all(|(k, v)| valid_ident(k) && valid_value(v)) =>
            {
                rows.push(RowRecord { table, data });
            }
            _ => return Err(InterchangeError::Corrupt),
        }
    }
    if u64::try_from(rows.len()).ok() != Some(meta.row_count) {
        return Err(InterchangeError::Corrupt);
    }
    Ok((meta, rows))
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    fn meta() -> Meta {
        Meta {
            format_version: FORMAT_VERSION,
            schema_version: 8,
            household_id: "h1".into(),
            source_device_id: "d1".into(),
            source_device_name: "Kompyuter".into(),
            export_id: "e1".into(),
            ack_export_id: None,
            mode: Mode::Full,
            exported_at: "2026-10-16T09:00:00.000Z".into(),
            row_count: 0,
            audience: None,
        }
    }

    fn row(table: &str, v: Value) -> RowRecord {
        RowRecord {
            table: table.into(),
            data: v.as_object().cloned().unwrap_or_default(),
        }
    }

    #[test]
    fn round_trip() {
        let rows = vec![
            row(
                "incomes",
                json!({"id": "i1", "amount_minor": 800_000_000, "note": null}),
            ),
            row(
                "venture_attachments",
                json!({"id": "a1", "bytes": crate::canon::blob(b"\x89PNG")}),
            ),
        ];
        let bytes = encode(&meta(), &rows).unwrap();
        let (m, back) = decode(&bytes).unwrap();
        assert_eq!(m.row_count, 2);
        assert_eq!(back, rows);
        let text = String::from_utf8(bytes).unwrap();
        assert!(text.starts_with("{\"ackExportId\":null,\"exportId\":\"e1\""));
    }

    #[test]
    fn rejects_bad_content() {
        let bad = |rows: Vec<RowRecord>| encode(&meta(), &rows).err();
        assert_eq!(
            bad(vec![row("incomes; DROP", json!({"id": "x"}))]),
            Some(InterchangeError::Corrupt)
        );
        assert_eq!(
            bad(vec![row("incomes", json!({"Id": "x"}))]),
            Some(InterchangeError::Corrupt)
        );
        assert_eq!(
            bad(vec![row("incomes", json!({"amount": 1.5}))]),
            Some(InterchangeError::Corrupt)
        );
        assert_eq!(
            bad(vec![row("incomes", json!({"ok": true}))]),
            Some(InterchangeError::Corrupt)
        );
        // Yozuvlar soni mos emas.
        let mut bytes = encode(&meta(), &[row("incomes", json!({"id": "x"}))]).unwrap();
        bytes.extend_from_slice(
            b"{\"data\":{\"id\":\"y\"},\"kind\":\"row\",\"table\":\"incomes\"}\n",
        );
        assert_eq!(decode(&bytes).err(), Some(InterchangeError::Corrupt));
        // Meta birinchi emas.
        assert_eq!(
            decode(b"{\"data\":{},\"kind\":\"row\",\"table\":\"a\"}\n").err(),
            Some(InterchangeError::Corrupt)
        );
    }
}
