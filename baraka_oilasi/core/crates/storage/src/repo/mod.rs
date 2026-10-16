//! Repository funksiyalari. Makon jadvallari uchun har bir funksiya `SpaceScope` oladi.
pub mod agreements;
pub mod assets;
pub mod categories;
pub mod ceremonies;
pub mod debts;
pub mod expenses;
pub mod governance;
pub mod household;
pub mod incomes;
pub mod journal;
pub mod partnerships;
pub mod recovery;
pub mod rules;
pub mod sync;
pub mod vault;
pub mod ventures;

/// Makon chegarasi: barcha so'rovlar `household_id` va `space_id` bo'yicha filtrlanadi.
#[derive(Clone, Debug, PartialEq, Eq, Hash)]
pub struct SpaceScope {
    pub household_id: String,
    pub space_id: String,
}

pub(crate) fn opt_bool(v: i64) -> bool {
    v != 0
}
