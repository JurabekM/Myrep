//! typst asosidagi PDF hosil qilish. Shriftlar ilovaga o'rnatilgan (DejaVu Sans), shuning uchun
//! `ʻ` (U+02BB) va `ʼ` (U+02BC) belgilari tizim shriftlariga bog'liq bo'lmay to'g'ri chiqadi.
#![cfg_attr(test, allow(clippy::unwrap_used, clippy::expect_used))]

mod budget;
mod minutes;
mod receipt;
mod world;

pub use budget::{budget_markup, ceremony_budget, BudgetLine, CeremonyBudgetDoc};
pub use minutes::{
    council_markup, council_minutes, CouncilMinutes, MinutesCategory, MinutesConsent,
};
pub use receipt::{loan_receipt, receipt_markup, LoanReceiptDoc, ReceiptSignatures};
pub use world::{render_pdf, render_pdf_with_files, PdfError, EMBEDDED_FONTS};
