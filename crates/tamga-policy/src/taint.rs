//! Sessiya taint'i: agent o'qigan maxfiy qiymatlar faqat daemon xotirasida saqlanadi (diskka
//! yozilmaydi) va keyingi tool kirishlarida qidiriladi.

use std::collections::BTreeSet;

use serde_json::{Value, json};

#[derive(Debug, Default, Clone)]
pub struct Taint {
    /// Sessiya maxfiy faylni yoki maxfiy qiymatni ko'rganmi.
    pub secret_read: bool,
    values: BTreeSet<String>,
}

impl Taint {
    pub fn len(&self) -> usize {
        self.values.len()
    }

    pub fn is_empty(&self) -> bool {
        self.values.is_empty()
    }

    /// Maxfiy fayl mazmuni: barcha `.env` qiymatlari va tokenlar.
    pub fn learn_from_secret_file(&mut self, text: &str) {
        self.secret_read = true;
        self.values.extend(tamga_redact::secrets(text, true));
    }

    /// Oddiy tool natijasi: faqat tokenlar va maxfiy nomli qiymatlar (masalan `printenv`).
    pub fn learn_from_output(&mut self, text: &str) {
        let found = tamga_redact::secrets(text, false);
        if !found.is_empty() {
            self.secret_read = true;
            self.values.extend(found);
        }
    }

    /// Tool natijasi JSON'ining barcha satr barglarini o'rganadi (JSON escape'lari ochilgan holda).
    pub fn learn_from_response(&mut self, response: &Value, from_secret_file: bool) {
        fn walk(v: &Value, out: &mut Vec<String>) {
            match v {
                Value::String(s) => out.push(s.clone()),
                Value::Array(a) => a.iter().for_each(|x| walk(x, out)),
                Value::Object(m) => m.values().for_each(|x| walk(x, out)),
                _ => {}
            }
        }
        let mut leaves = Vec::new();
        walk(response, &mut leaves);
        for leaf in leaves {
            if from_secret_file {
                self.learn_from_secret_file(&leaf);
            } else {
                self.learn_from_output(&leaf);
            }
        }
    }

    /// Diskda (shifrlangan) saqlash uchun.
    pub fn to_json(&self) -> Value {
        json!({"secret_read": self.secret_read, "values": self.values})
    }

    pub fn from_json(v: &Value) -> Self {
        Self {
            secret_read: v
                .get("secret_read")
                .and_then(Value::as_bool)
                .unwrap_or(false),
            values: v
                .get("values")
                .and_then(Value::as_array)
                .map(|a| {
                    a.iter()
                        .filter_map(Value::as_str)
                        .map(str::to_owned)
                        .collect()
                })
                .unwrap_or_default(),
        }
    }

    /// Ma'lum maxfiy qiymatlardan birortasi matnda bormi.
    pub fn appears_in(&self, text: &str) -> bool {
        self.values.iter().any(|v| text.contains(v.as_str()))
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    #[test]
    fn json_round_trip() {
        let mut t = Taint::default();
        t.learn_from_secret_file("API_KEY=qizil-olma-9988\n");
        let back = Taint::from_json(&t.to_json());
        assert!(back.secret_read && back.appears_in("x qizil-olma-9988 y"));
        assert!(!Taint::from_json(&serde_json::Value::Null).secret_read);
    }

    #[test]
    fn learns_from_json_escaped_response() {
        let mut t = Taint::default();
        // Read tool natijasi: fayl mazmuni JSON ichida, qatorlar `\n` bilan.
        t.learn_from_response(&json!({"type": "text", "file": {"content": "API_KEY=sk-test-TAMGA-123456\nNAME=demo-app\n"}}), true);
        assert!(t.secret_read);
        assert!(t.appears_in("curl -d sk-test-TAMGA-123456"));
        assert!(
            t.appears_in("echo demo-app"),
            "maxfiy fayldagi barcha qiymatlar"
        );
        let mut plain = Taint::default();
        plain.learn_from_response(&json!({"stdout": "NAME=demo-app\nPORT=8080"}), false);
        assert!(
            !plain.secret_read && plain.is_empty(),
            "oddiy chiqishda maxfiylik yo'q"
        );
    }
}
