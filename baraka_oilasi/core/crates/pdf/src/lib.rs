//! typst asosidagi PDF renderer (`docs/BARAKA_OILASI.md` 9).
//!
//! * shablonlar `shared/pdf/*.typ`, shriftlar `shared/fonts/` — binarga o'rnatilgan, tarmoq yo'q;
//! * ma'lumot shablonga faqat `data.json` virtual fayli orqali beriladi (kod in'eksiyasi yo'q);
//! * deterministik: bir xil kirish → bir xil baytlar (sana, identifikator va yaratuvchi qotirilgan);
//! * PDF chop etish uchun — ilova mavzusidan qat'i nazar oq fonda.

mod documents;
mod engine;

pub use documents::{LoanReceipt, PdfLocale, ScheduleLine};
pub use engine::{PdfEngine, PdfError, Rendered};
