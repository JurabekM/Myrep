//! `.baraka` almashish formati (`docs/BARAKA_OILASI.md` 8.3–8.5, 6.6).
//!
//! * [`container`] — sarlavha + XChaCha20-Poly1305 bilan shifrlangan JSON Lines; kalit —
//!   Argon2id(parol). Sarlavha AEAD'ning qo'shimcha ma'lumoti (AAD): o'zgartirilsa — xato.
//! * [`model`] — qatorlar: birinchisi `meta`, keyin jadval yozuvlari (`row`).
//! * [`canon`] — yozuvning kanonik JSON'i va SHA-256 xeshi (ikkala platformada bir xil).
//! * [`merge`] — uch tomonlama birlashtirish qarori: oxirgi kelishilgan holat (`base`) bilan
//!   solishtiriladi; ikkala tomonda o'zgargan yozuv — ziddiyat (LWW yo'q).
//! * [`chain`] — kelishuv jurnali: zanjir qayta hisoblanadi, mahalliy nusxadan ayrilib ketgan
//!   bo'lsa (fork) — import to'xtaydi.
//!
//! Sxema: `spec/interchange/export-format.schema.json`; mustaqil tekshiruv:
//! `spec/interchange/oracle.py` (KAT vektorlari).
pub mod canon;
pub mod chain;
pub mod container;
mod error;
pub mod merge;
pub mod model;
pub mod tables;

pub use error::InterchangeError;

/// Konteyner formati versiyasi (sarlavhada va `meta` qatorida).
pub const FORMAT_VERSION: u32 = 1;
