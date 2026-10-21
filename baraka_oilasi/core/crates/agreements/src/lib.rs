//! Umumiy kelishuv dvigateli (uy/SPEC 2F.1–2F.3). Qarz tilxati, sheriklik shartnomasi,
//! ijara, xizmat va oilaviy kelishuvlar bitta 9 savol strukturasidan foydalanadi.
//!
//! Ma'lumotlar modeli serde orqali DTO va test vektorlari bilan bir xil ko'rinishda (camelCase).
#![deny(clippy::float_arithmetic)]

mod model;
mod signature;
mod validate;

pub use model::*;
pub use signature::{signature_svg, validate_signature, Stroke, MAX_POINTS, PAD_HEIGHT, PAD_WIDTH};
pub use validate::{check_completeness, Completeness, QUESTION_COUNT, REVIEW_WARN_AFTER_DAYS};
