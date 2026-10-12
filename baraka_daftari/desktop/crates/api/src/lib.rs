//! Tauri'siz buyruq qatlami (`src-tauri` shu crate ustiga quriladi).
//!
//! Nega alohida: `cargo test` Tauri'ga bog'langan test binary'sini Windows'da ishga tushira olmaydi
//! (`STATUS_ENTRYPOINT_NOT_FOUND`: Common Controls manifesti yo'q). Shu sababli sinaladigan mantiq
//! bu yerda, Tauri'siz turadi va barcha platformalarda testdan o'tadi.
#![cfg_attr(test, allow(clippy::unwrap_used, clippy::expect_used))]

pub mod dto;
pub mod error;
pub mod session;
pub mod text;

#[cfg(test)]
mod allocation_tests {
    use money::{allocate, Currency, Money};

    /// Eski `allocate_demo` testlari: summa nisbatlar bo'yicha yaxlit taqsimlanadi.
    #[test]
    fn splits_by_ratio() {
        let parts = allocate(Money::new(100, Currency::Uzs), &[1, 1, 1]).unwrap();
        let minors: Vec<String> = parts.iter().map(|p| p.minor().to_string()).collect();
        assert_eq!(minors, ["34", "33", "33"]);
        assert!(allocate(Money::new(10, Currency::Uzs), &[]).is_err());
    }
}
