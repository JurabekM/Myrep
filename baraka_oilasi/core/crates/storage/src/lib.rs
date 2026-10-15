//! SQLCipher saqlash qatlami (`docs/BARAKA_OILASI.md`, 4.4, 8, Y5).
//!
//! * Baza faqat `DbKey` bilan ochiladi; kalit noto'g'ri bo'lsa — `StorageError::WrongKey`.
//! * Makon jadvallaridagi har bir repository funksiyasi `SpaceScope` talab qiladi:
//!   makonsiz so'rov yozib bo'lmaydi.
//! * `journal_entries` — append-only: UPDATE/DELETE DB triggerlari bilan rad etiladi va
//!   repository'da bunday funksiyalar yo'q.
//!
//! Hozircha bitta ulanish `Mutex` orqali ketma-ket ishlatiladi (yozuvchi aktor bilan teng
//! kafolat). O'qish ulanishlari puli ishlash talab qilganda qo'shiladi.

mod db;
mod error;
pub mod repo;

pub use db::{Database, Meta};
pub use error::StorageError;
pub use repo::SpaceScope;
