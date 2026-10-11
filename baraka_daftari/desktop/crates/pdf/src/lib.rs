//! typst asosidagi PDF hosil qilish. Shriftlar ilovaga o'rnatilgan (DejaVu Sans), shuning uchun
//! `ʻ` (U+02BB) va `ʼ` (U+02BC) belgilari tizim shriftlariga bog'liq bo'lmay to'g'ri chiqadi.
#![cfg_attr(test, allow(clippy::unwrap_used, clippy::expect_used))]

mod budget;
mod contract;
mod minutes;
mod period;
mod receipt;
mod world;

pub use budget::{budget_markup, ceremony_budget, BudgetLine, CeremonyBudgetDoc};
pub use contract::{contract_markup, partnership_contract, ContractDoc, ContractParty};
pub use minutes::{
    council_markup, council_minutes, CouncilMinutes, MinutesCategory, MinutesConsent,
};
pub use period::{period_markup, period_report, PeriodReportDoc, ReportEntry};
pub use receipt::{loan_receipt, receipt_markup, LoanReceiptDoc, ReceiptSignatures};
pub use world::{render_pdf, render_pdf_with_files, PdfError, EMBEDDED_FONTS};

/// Sheriklik shartnomasi shabloni yurist va ulamo tasdig'idan o'tganmi (SPEC 8). Tasdiq olinmaguncha
/// `false`: ilova ogohlantirish ko'rsatadi, reliz tekshiruvi (`release_gate` testi) to'sib turadi.
pub const TEMPLATES_APPROVED: bool = false;
