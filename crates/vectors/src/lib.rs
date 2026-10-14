//! Umumiy oltin test vektorlarini yuklash (DESKTOP_PROMPT.md 5-bo'lim).
//!
//! Vektorlar `spec/test-vectors/*.json` da turadi — mobil va desktop uchun umumiy. Bu kutubxona faqat
//! yuklaydi va maydonlarni o'qiydi. Har bir suite'ni qanday tekshirish `tests/` dagi runner'larda yoziladi;
//! shunday qilib kutubxona hech qanday domen kodiga bog'lanmaydi.

use std::fs;
use std::path::{Path, PathBuf};

use serde::Deserialize;
use serde_json::Value;
use thiserror::Error;

/// Bitta vektor fayli: `{ "suite", "version", "description", "cases": [...] }`.
#[derive(Debug, Deserialize)]
pub struct Suite {
    pub suite: String,
    pub version: u32,
    pub description: String,
    pub cases: Vec<Case>,
}

/// Bitta sinov holati. `input` va `expected` — JSON obyektlari; maydonlarni quyidagi yordamchilar o'qiydi.
#[derive(Debug, Deserialize)]
pub struct Case {
    pub id: String,
    pub input: Value,
    pub expected: Value,
}

/// Vektor fayllarini o'qish yoki tahlil qilishdagi xatolar.
#[derive(Debug, Error)]
pub enum VectorsError {
    /// Fayl o'qilmadi.
    #[error("vektor fayli o'qilmadi ({path}): {source}")]
    Io {
        path: PathBuf,
        #[source]
        source: std::io::Error,
    },
    /// Fayl noto'g'ri JSON.
    #[error("vektor JSON noto'g'ri ({path}): {source}")]
    Json {
        path: PathBuf,
        #[source]
        source: serde_json::Error,
    },
    /// Maydon yo'q yoki kutilgan turda emas.
    #[error("maydon yo'q yoki noto'g'ri turda: {0}")]
    Field(String),
}

/// `spec/test-vectors` papkasi. `crates/vectors/` dan ikki daraja yuqorida (repo ildizi).
pub fn vectors_dir() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR")).join("../../spec/test-vectors")
}

/// Nomi bo'yicha suite yuklaydi: `load_suite("allocate")` → `allocate.json`.
pub fn load_suite(name: &str) -> Result<Suite, VectorsError> {
    let path = vectors_dir().join(format!("{name}.json"));
    let text = fs::read_to_string(&path).map_err(|source| VectorsError::Io {
        path: path.clone(),
        source,
    })?;
    serde_json::from_str(&text).map_err(|source| VectorsError::Json { path, source })
}

/// Papkadagi barcha vektor fayllarining nomlari (kengaytmasiz), alifbo tartibida.
pub fn suite_names() -> Result<Vec<String>, VectorsError> {
    let dir = vectors_dir();
    let entries = fs::read_dir(&dir).map_err(|source| VectorsError::Io {
        path: dir.clone(),
        source,
    })?;

    let mut names = Vec::new();
    for entry in entries {
        let path = entry
            .map_err(|source| VectorsError::Io {
                path: dir.clone(),
                source,
            })?
            .path();
        let is_json = path.extension().and_then(|ext| ext.to_str()) == Some("json");
        if let (true, Some(stem)) = (is_json, path.file_stem().and_then(|stem| stem.to_str())) {
            names.push(stem.to_owned());
        }
    }
    names.sort();
    Ok(names)
}

/// Satr maydoni. Yo'q yoki satr bo'lmasa — [`VectorsError::Field`].
pub fn str_field<'a>(object: &'a Value, key: &str) -> Result<&'a str, VectorsError> {
    opt_str_field(object, key).ok_or_else(|| VectorsError::Field(key.to_owned()))
}

/// Ixtiyoriy satr maydoni.
pub fn opt_str_field<'a>(object: &'a Value, key: &str) -> Option<&'a str> {
    object.get(key).and_then(Value::as_str)
}

/// Butun son maydoni. JSON son ham, raqamli satr (`"100"`) ham qabul qilinadi.
pub fn int_field(object: &Value, key: &str) -> Result<i64, VectorsError> {
    let value = object
        .get(key)
        .ok_or_else(|| VectorsError::Field(key.to_owned()))?;
    value
        .as_i64()
        .or_else(|| value.as_str().and_then(|text| text.parse().ok()))
        .ok_or_else(|| VectorsError::Field(key.to_owned()))
}

/// Musbat butun sonlar massivi (masalan, `ratios`).
pub fn u64_array_field(object: &Value, key: &str) -> Result<Vec<u64>, VectorsError> {
    let items = object
        .get(key)
        .and_then(Value::as_array)
        .ok_or_else(|| VectorsError::Field(key.to_owned()))?;
    items
        .iter()
        .map(|item| {
            item.as_u64()
                .ok_or_else(|| VectorsError::Field(key.to_owned()))
        })
        .collect()
}
