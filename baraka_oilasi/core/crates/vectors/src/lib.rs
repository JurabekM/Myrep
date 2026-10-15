//! Oltin test vektorlari runner'i (`docs/BARAKA_OILASI.md` 12).
//!
//! Har bir suite uchun kirishni o'qiydi, yadro funksiyasini chaqiradi va natijani `expected`
//! bilan **to'liq** solishtiradi. Noma'lum suite — xato: har bir vektor fayli tekshirilishi shart.
//! FFI runner'lari (Dart, TS) xuddi shu fayllarni ishlatadi.

use std::fs;
use std::path::{Path, PathBuf};

use serde_json::{json, Value};

mod suites;

/// Bitta case natijasi.
#[derive(Debug)]
pub struct CaseFailure {
    pub suite: String,
    pub id: String,
    pub expected: Value,
    pub actual: Value,
}

/// Repo ildizidagi `spec/test-vectors` papkasi.
pub fn default_dir() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR")).join("../../../spec/test-vectors")
}

/// Papkadagi barcha suite'larni ishga tushiradi. `Ok(case soni)` yoki muvaffaqiyatsizliklar.
pub fn run_dir(dir: &Path) -> Result<usize, Vec<CaseFailure>> {
    let mut failures = Vec::new();
    let mut count = 0;
    let mut paths: Vec<PathBuf> = match fs::read_dir(dir) {
        Ok(rd) => rd.filter_map(|e| e.ok().map(|e| e.path())).collect(),
        Err(e) => {
            failures.push(fail("<dir>", "<read>", json!(null), json!(e.to_string())));
            return Err(failures);
        }
    };
    paths.retain(|p| p.extension().is_some_and(|e| e == "json"));
    paths.sort();
    for path in paths {
        let text = match fs::read_to_string(&path) {
            Ok(t) => t,
            Err(e) => {
                failures.push(fail(
                    &path.display().to_string(),
                    "<read>",
                    json!(null),
                    json!(e.to_string()),
                ));
                continue;
            }
        };
        let doc: Value = match serde_json::from_str(&text) {
            Ok(v) => v,
            Err(e) => {
                failures.push(fail(
                    &path.display().to_string(),
                    "<parse>",
                    json!(null),
                    json!(e.to_string()),
                ));
                continue;
            }
        };
        let suite = doc["suite"].as_str().unwrap_or_default().to_string();
        let cases = doc["cases"].as_array().cloned().unwrap_or_default();
        for case in cases {
            count += 1;
            let id = case["id"].as_str().unwrap_or_default().to_string();
            let actual = suites::run(&suite, &case["input"]);
            if actual != case["expected"] {
                failures.push(fail(&suite, &id, case["expected"].clone(), actual));
            }
        }
    }
    if failures.is_empty() {
        Ok(count)
    } else {
        Err(failures)
    }
}

fn fail(suite: &str, id: &str, expected: Value, actual: Value) -> CaseFailure {
    CaseFailure {
        suite: suite.to_string(),
        id: id.to_string(),
        expected,
        actual,
    }
}
