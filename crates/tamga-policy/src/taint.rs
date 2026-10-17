//! Sessiya taint'i: agent o'qigan maxfiy qiymatlar faqat daemon xotirasida saqlanadi (diskka
//! yozilmaydi) va keyingi tool kirishlarida qidiriladi.

use std::collections::BTreeSet;

use serde_json::Value;

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
