//! Sinxronlanadigan jadvallar ro'yxati — `spec/interchange/export-format.schema.json` dagi
//! `x-baraka-tables` dan (yagona manba: Dart ham shu faylni o'qiydi). Tartib — import tartibi.
use std::sync::OnceLock;

use serde::Deserialize;

/// Sxema fayli (kompilyatsiya paytida ichiga olinadi).
pub const SCHEMA_JSON: &str =
    include_str!("../../../../spec/interchange/export-format.schema.json");

#[derive(Clone, Copy, Debug, PartialEq, Eq, Deserialize)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum TableMode {
    /// Uch tomonlama birlashtirish.
    Mutable,
    /// Faqat qo'shiladi; o'zgartirishga urinish — rad etiladi.
    AppendOnly,
}

#[derive(Clone, Debug, PartialEq, Eq, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct TableSpec {
    pub name: String,
    pub mode: TableMode,
    pub primary_key: String,
    pub blob_columns: Vec<String>,
}

#[derive(Deserialize)]
struct Registry {
    items: Vec<TableSpec>,
}

#[derive(Deserialize)]
struct Schema {
    #[serde(rename = "x-baraka-tables")]
    tables: Registry,
}

/// Jadvallar (import tartibida). Sxema buzilgan bo'lsa — bo'sh ro'yxat (testlar ushlaydi).
pub fn sync_tables() -> &'static [TableSpec] {
    static TABLES: OnceLock<Vec<TableSpec>> = OnceLock::new();
    TABLES.get_or_init(|| {
        serde_json::from_str::<Schema>(SCHEMA_JSON)
            .map(|s| s.tables.items)
            .unwrap_or_default()
    })
}

pub fn table(name: &str) -> Option<&'static TableSpec> {
    sync_tables().iter().find(|t| t.name == name)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn registry_matches_row_enum() {
        let tables = sync_tables();
        assert!(tables.len() > 40);
        let schema: serde_json::Value = serde_json::from_str(SCHEMA_JSON).unwrap_or_default();
        let names: Vec<&str> = schema["$defs"]["rowLine"]["properties"]["table"]["enum"]
            .as_array()
            .map(|a| a.iter().filter_map(|v| v.as_str()).collect())
            .unwrap_or_default();
        let ours: Vec<&str> = tables.iter().map(|t| t.name.as_str()).collect();
        assert_eq!(names, ours);
        assert_eq!(
            table("journal_entries").map(|t| t.mode),
            Some(TableMode::AppendOnly)
        );
        assert_eq!(table("incomes").map(|t| t.mode), Some(TableMode::Mutable));
        assert_eq!(
            table("venture_attachments").map(|t| t.blob_columns.clone()),
            Some(vec!["bytes".to_string()])
        );
    }
}
