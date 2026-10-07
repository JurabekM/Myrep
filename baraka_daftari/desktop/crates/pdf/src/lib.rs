//! typst asosidagi PDF hosil qilish. Shriftlar ilovaga o'rnatilgan (DejaVu Sans), shuning uchun
//! `ʻ` (U+02BB) va `ʼ` (U+02BC) belgilari tizim shriftlariga bog'liq bo'lmay to'g'ri chiqadi.
#![cfg_attr(test, allow(clippy::unwrap_used, clippy::expect_used))]

mod minutes;
mod world;

pub use minutes::{
    council_markup, council_minutes, CouncilMinutes, MinutesCategory, MinutesConsent,
};
pub use world::{render_pdf, PdfError, EMBEDDED_FONTS};
