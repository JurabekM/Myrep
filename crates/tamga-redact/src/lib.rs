//! Maxfiy qiymatlarni topish: ma'lum token shakllari va `.env` uslubidagi `KALIT=qiymat` qatorlari.
//!
//! Ikki maqsad: (1) sessiya taint'i — agent o'qigan maxfiy qiymatlar keyin tarmoq buyrug'ida paydo
//! bo'lsa, uni aniqlash; (2) Studio'da ko'rsatishdan oldin yashirish ([`redact`]).

use std::sync::LazyLock;

use regex::Regex;

/// Ma'lum provayderlar tokenlari va kalit bloklari.
static TOKEN: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(
        r"(?x)
        sk-ant-[A-Za-z0-9_\-]{20,}            # Anthropic
      | sk-(?:proj-)?[A-Za-z0-9_\-]{20,}      # OpenAI uslubi
      | AKIA[0-9A-Z]{16}                      # AWS access key id
      | gh[pousr]_[A-Za-z0-9]{36,}            # GitHub
      | github_pat_[A-Za-z0-9_]{40,}
      | xox[abposr]-[A-Za-z0-9\-]{10,}        # Slack
      | AIza[0-9A-Za-z_\-]{35}                # Google API
      | eyJ[A-Za-z0-9_\-]{10,}\.eyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}   # JWT
      | -----BEGIN\ [A-Z\ ]*PRIVATE\ KEY-----",
    )
    .expect("regex")
});

/// `KALIT=qiymat` qatori (ixtiyoriy `export`, qo'shtirnoqlar).
static ENV_LINE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r#"(?m)^[ \t]*(?:export[ \t]+)?([A-Za-z_][A-Za-z0-9_]*)[ \t]*=[ \t]*(?:"([^"\r\n]*)"|'([^'\r\n]*)'|([^\s#]+))"#)
        .expect("regex")
});

/// Kalit nomi maxfiy ekanini bildiruvchi qismlar.
static SECRET_NAME: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"(?i)(KEY|TOKEN|SECRET|PASS|PWD|CREDENTIAL|AUTH|PRIVATE|DSN|DATABASE_URL|CONN)")
        .expect("regex")
});

/// Taint uchun eng qisqa qiymat: juda qisqa qiymatlar (`true`, `8080`) yolg'on signal beradi.
pub const MIN_SECRET_LEN: usize = 6;

/// Matndagi ma'lum token shakllari.
pub fn tokens(text: &str) -> Vec<String> {
    TOKEN
        .find_iter(text)
        .map(|m| m.as_str().to_owned())
        .collect()
}

pub fn contains_token(text: &str) -> bool {
    TOKEN.is_match(text)
}

/// `.env` uslubidagi qatorlardan qiymatlar. `all = true` — maxfiy fayldan o'qilgan matn uchun
/// barcha qiymatlar; aks holda faqat nomi maxfiylikni bildiradigan kalitlar.
pub fn env_values(text: &str, all: bool) -> Vec<String> {
    ENV_LINE
        .captures_iter(text)
        .filter(|c| all || SECRET_NAME.is_match(&c[1]))
        .filter_map(|c| {
            c.get(2)
                .or(c.get(3))
                .or(c.get(4))
                .map(|m| m.as_str().to_owned())
        })
        .filter(|v| v.len() >= MIN_SECRET_LEN)
        .collect()
}

/// Matndagi barcha maxfiy qiymatlar (tokenlar + maxfiy nomli `.env` qiymatlari).
pub fn secrets(text: &str, from_secret_file: bool) -> Vec<String> {
    let mut out = tokens(text);
    out.extend(env_values(text, from_secret_file));
    out.sort();
    out.dedup();
    out
}

/// Ko'rsatish uchun yashirish: har bir topilgan maxfiy qiymat `‹yashirildi›` bilan almashtiriladi.
pub fn redact(text: &str) -> String {
    let mut out = text.to_owned();
    let mut found = secrets(text, false);
    found.sort_by_key(|s| std::cmp::Reverse(s.len())); // uzunlari avval — qisman almashtirishning oldini oladi
    for s in found {
        out = out.replace(&s, "‹yashirildi›");
    }
    out
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn finds_known_tokens() {
        let t = "key sk-ant-api03-AbCdEfGhIjKlMnOpQrStUv and AKIAIOSFODNN7EXAMPLE and ghp_0123456789abcdefghijABCDEFGHIJ0123456789";
        assert_eq!(tokens(t).len(), 3);
        assert!(contains_token("-----BEGIN OPENSSH PRIVATE KEY-----"));
        assert!(!contains_token("oddiy matn sk-qisqa"));
    }

    #[test]
    fn env_values_by_name_or_all() {
        let env = "# izoh\nAPI_KEY=sk-test-TAMGA-123456\nexport DB_PASSWORD=\"p@ss w0rd!\"\nPORT=8080\nDEBUG=true\nAPP_NAME=myservice\n";
        assert_eq!(
            env_values(env, false),
            ["sk-test-TAMGA-123456", "p@ss w0rd!"]
        );
        let all = env_values(env, true);
        assert!(all.contains(&"myservice".to_owned()));
        assert!(!all.contains(&"true".to_owned()), "qisqa qiymat olinmaydi");
    }

    #[test]
    fn redacts_for_display() {
        let r = redact("API_KEY=sk-test-TAMGA-123456 ishlatildi");
        assert!(!r.contains("sk-test"), "{r}");
        assert!(r.contains("‹yashirildi›"));
    }
}
