//! `mpay-shield` — M-Pay Pay Sandbox moduli.
//!
//! Batafsil tavsif: crate'ning `README.md` fayli.
#![forbid(unsafe_code)]

/// Crate versiyasi (diagnostika va `/healthz` uchun).
pub const VERSION: &str = env!("CARGO_PKG_VERSION");

#[cfg(test)]
mod tests {
    #[test]
    fn version_is_set() {
        assert!(!super::VERSION.is_empty());
    }
}
