use std::collections::BTreeSet;
use std::path::Path;

use serde_json::{Map, Value};

use crate::translit::to_cyrillic;
use crate::write_if_changed;

type Dict = Map<String, Value>;

fn read(path: &Path) -> Result<Dict, String> {
    let text = std::fs::read_to_string(path).map_err(|e| format!("{}: {e}", path.display()))?;
    match serde_json::from_str::<Value>(&text).map_err(|e| format!("{}: {e}", path.display()))? {
        Value::Object(m) => Ok(m),
        _ => Err(format!("{}: obyekt kutilgan", path.display())),
    }
}

fn locales(root: &Path) -> Result<Vec<(&'static str, Dict)>, String> {
    let dir = root.join("shared/i18n");
    let uz = read(&dir.join("uz.json"))?;
    let ru = read(&dir.join("ru.json"))?;
    let overrides = read(&dir.join("uz-Cyrl.overrides.json"))?;
    let mut cyrl = Dict::new();
    for (k, v) in &uz {
        let text = match overrides.get(k) {
            Some(o) => o.clone(),
            None => Value::String(to_cyrillic(v.as_str().unwrap_or_default())),
        };
        cyrl.insert(k.clone(), text);
    }
    Ok(vec![("uz", uz), ("uz-Cyrl", cyrl), ("ru", ru)])
}

fn placeholders(s: &str) -> BTreeSet<String> {
    let mut out = BTreeSet::new();
    let mut rest = s;
    while let Some(start) = rest.find('{') {
        let Some(end) = rest[start..].find('}') else {
            break;
        };
        let name = rest[start + 1..start + end]
            .split(',')
            .next()
            .unwrap_or_default()
            .trim();
        out.insert(name.to_string());
        rest = &rest[start + end + 1..];
    }
    out
}

fn arb_key(key: &str) -> String {
    // ARB kalitlari Dart identifikatori bo'lishi kerak: `home.paidToSelf` → `home_paidToSelf`.
    key.replace(['.', '-'], "_")
}

fn pretty(v: &Value) -> Result<String, String> {
    serde_json::to_string_pretty(v)
        .map(|s| s + "\n")
        .map_err(|e| e.to_string())
}

pub fn generate(root: &Path) -> Result<(), String> {
    for (tag, dict) in locales(root)? {
        // i18next (desktop): tekis kalitlar.
        write_if_changed(
            &root.join(format!("apps/desktop/ui/src/i18n/{tag}.json")),
            &pretty(&Value::Object(dict.clone()))?,
        )?;
        // Flutter gen-l10n (Android).
        let arb_locale = tag.replace('-', "_");
        let mut arb = Dict::new();
        arb.insert("@@locale".into(), Value::String(arb_locale.clone()));
        for (k, v) in &dict {
            let key = arb_key(k);
            arb.insert(key.clone(), v.clone());
            let ph = placeholders(v.as_str().unwrap_or_default());
            if tag == "uz" && !ph.is_empty() {
                let mut p = Dict::new();
                for name in ph {
                    p.insert(name, Value::Object(Dict::new()));
                }
                let mut meta = Dict::new();
                meta.insert("placeholders".into(), Value::Object(p));
                arb.insert(format!("@{key}"), Value::Object(meta));
            }
        }
        write_if_changed(
            &root.join(format!("apps/android/lib/l10n/app_{arb_locale}.arb")),
            &pretty(&Value::Object(arb))?,
        )?;
    }
    Ok(())
}

pub fn lint(root: &Path) -> Result<(), String> {
    let all = locales(root)?;
    let forbidden = read(&root.join("shared/i18n/forbidden.json"))?;
    let phrases: Vec<String> = forbidden
        .get("phrases")
        .and_then(Value::as_array)
        .map(|a| {
            a.iter()
                .filter_map(|v| v.as_str().map(str::to_lowercase))
                .collect()
        })
        .unwrap_or_default();
    let allow: Vec<String> = forbidden
        .get("allowKeyPrefixes")
        .and_then(Value::as_array)
        .map(|a| {
            a.iter()
                .filter_map(|v| v.as_str().map(str::to_string))
                .collect()
        })
        .unwrap_or_default();
    let mut problems = Vec::new();
    let (_, base) = &all[0];
    for (tag, dict) in &all {
        let keys: BTreeSet<&String> = dict.keys().collect();
        let base_keys: BTreeSet<&String> = base.keys().collect();
        for k in base_keys.symmetric_difference(&keys) {
            problems.push(format!("{tag}: kalit mos emas: {k}"));
        }
        for (k, v) in dict {
            let Some(text) = v.as_str() else {
                problems.push(format!("{tag}/{k}: matn emas"));
                continue;
            };
            if text.trim().is_empty() {
                problems.push(format!("{tag}/{k}: bo'sh"));
            }
            if let Some(b) = base.get(k).and_then(Value::as_str) {
                if placeholders(b) != placeholders(text) {
                    problems.push(format!("{tag}/{k}: plaseholderlar mos emas"));
                }
            }
            if allow.iter().any(|p| k.starts_with(p.as_str())) {
                continue;
            }
            let lower = text.to_lowercase();
            for p in &phrases {
                if lower.contains(p.as_str()) {
                    problems.push(format!("{tag}/{k}: taqiqlangan ibora «{p}»"));
                }
            }
        }
    }
    if problems.is_empty() {
        println!("i18n lint: OK ({} kalit, {} lokal)", base.len(), all.len());
        Ok(())
    } else {
        Err(problems.join("\n"))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn placeholder_parsing() {
        let p = placeholders("{count} hafta, {amount} so'm");
        assert_eq!(p.into_iter().collect::<Vec<_>>(), vec!["amount", "count"]);
        assert_eq!(arb_key("income.channel.CASH"), "income_channel_CASH");
    }
}
