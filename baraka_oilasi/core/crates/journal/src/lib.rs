//! Append-only jurnal va xesh-zanjir (`docs/BARAKA_OILASI.md`, 6-bo'lim).
//!
//! * `canonical` — RFC 8785 (JCS): kalitlar UTF-16 bo'yicha tartiblangan, bo'sh joysiz;
//! * faqat whitelist'dagi maydonlar xeshlanadi (6.2), barcha qiymatlar string;
//! * `hash_n = hex(SHA256(prev_hash + "\n" + canonical(entry_n)))`, genesis — 64 ta `0`.
//!
//! Crate matnni normalizatsiya qilmaydi: NFC saqlashdan oldin `app` qatlamida bir marta
//! qo'llanadi va keyin baytlar o'zgarishsiz qoladi (6.4).
#![no_std]

extern crate alloc;

mod canonical;
mod chain;
mod entry;

pub use canonical::{canonical_json, CanonValue};
pub use chain::{chain_hash, compute_chain, short_code, verify_chain, ChainError, GENESIS_HASH};
pub use entry::{EntryError, EntryKind, JournalAmount, JournalEntry};
