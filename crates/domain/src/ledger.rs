//! Oy hisobi (SPEC 2.3, 2.4): daromad, xarajatlar, majburiyatlar, «Kelajagim» va izohsiz summa.
//!
//! Qoidalar mobil ilovadagi `month_ledger.dart` bilan bir xil:
//! * majburiyat o'z kategoriyasidagi yozilgan xarajat bilan qoplanadi; faqat yozilmagan qismi
//!   (`remainder`) alohida hisoblanadi — ikki marta sanash yo'q;
//! * izohsiz summa = daromad − (yozilmagan majburiyatlar + xarajatlar + sof jamg'arma)
//!   (`spec/test-vectors/unexplained_gap.json`).

use std::collections::BTreeMap;

use money::{Currency, Money};

use crate::DomainError;
use crate::calendar::{DateRange, tashkent_date};
use crate::category::CategoryKey;
use crate::expense::Expense;
use crate::income::Income;
use crate::obligation::{Obligation, ObligationKind};
use crate::vault::{VaultEntry, VaultMovement};

/// Majburiyatning davr uchun holati.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ObligationLine {
    /// Majburiyat (UUIDv7).
    pub obligation_id: String,
    /// Nomi.
    pub title: String,
    /// Turi (kimga to'lanishini belgilaydi).
    pub kind: ObligationKind,
    /// Oylik summa.
    pub amount: Money,
    /// Kategoriyada yozilgan va majburiyatni qoplagan qism.
    pub recorded: Money,
    /// Yozilmagan (faraz qilingan to'langan) qism.
    pub remainder: Money,
}

/// Bir davr (oy) bo'yicha pul harakati.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct MonthLedger {
    /// Davr.
    pub period: DateRange,
    /// Asosiy valyuta.
    pub currency: Currency,
    /// Jami daromad.
    pub income: Money,
    /// Kategoriya ID → yozilgan xarajatlar (kategoriyasiz — `None` kalit).
    pub expenses_by_category: BTreeMap<Option<String>, Money>,
    /// Barcha yozilgan xarajatlar.
    pub expenses: Money,
    /// Majburiyatlar (summa va holati).
    pub obligations: Vec<ObligationLine>,
    /// «Kelajagim»ga ajratilgan (boshlang'ich balans kirmaydi).
    pub saved_deposited: Money,
    /// «Kelajagim»dan olingan.
    pub saved_withdrawn: Money,
}

impl MonthLedger {
    /// Sof jamg'arma: ajratilgan − olingan.
    pub fn net_savings(&self) -> Result<Money, DomainError> {
        Ok(self.saved_deposited.checked_sub(self.saved_withdrawn)?)
    }

    /// Majburiyatlar jami (oylik summalar).
    pub fn obligations_total(&self) -> Result<Money, DomainError> {
        sum(
            self.currency,
            self.obligations.iter().map(|line| line.amount),
        )
    }

    /// Majburiyatlarning yozilmagan (faraz qilingan) qismi.
    pub fn obligations_unrecorded(&self) -> Result<Money, DomainError> {
        sum(
            self.currency,
            self.obligations.iter().map(|line| line.remainder),
        )
    }

    /// «Izohsiz qolgan summa» (manfiy bo'lishi mumkin).
    pub fn unexplained(&self) -> Result<Money, DomainError> {
        unexplained_gap(
            self.income,
            self.obligations_unrecorded()?,
            self.expenses,
            self.net_savings()?,
        )
    }
}

/// `daromad − (majburiyatlar + xarajatlar + jamg'arma)`; manfiy bo'lishi mumkin.
pub fn unexplained_gap(
    income: Money,
    obligations: Money,
    expenses: Money,
    savings: Money,
) -> Result<Money, DomainError> {
    let outgoing = obligations.checked_add(expenses)?.checked_add(savings)?;
    Ok(income.checked_sub(outgoing)?)
}

/// Yozuvlar to'plami. Boshqa valyutadagi yozuvlar hisobga olinmaydi.
pub struct LedgerInput<'a> {
    /// Hisob davri.
    pub period: DateRange,
    /// Asosiy valyuta.
    pub currency: Currency,
    /// Daromadlar (faqat davr ichidagilari olinadi).
    pub incomes: &'a [Income],
    /// Xarajatlar.
    pub expenses: &'a [Expense],
    /// Majburiyatlar (faqat faollari, davr oxirigacha yaratilganlari).
    pub obligations: &'a [Obligation],
    /// «Kelajagim» yozuvlari.
    pub vault: &'a [VaultEntry],
}

/// Davr uchun hisob. Majburiyatlar muddati bo'yicha (kun) tartiblanib, kategoriya puli navbat bilan qoplanadi.
pub fn build_month_ledger(input: &LedgerInput<'_>) -> Result<MonthLedger, DomainError> {
    let currency = input.currency;
    let zero = Money::zero(currency);
    let in_period = |date| input.period.contains(date);

    let mut income = zero;
    for item in input
        .incomes
        .iter()
        .filter(|i| i.amount.currency() == currency && in_period(i.occurred_on))
    {
        income = income.checked_add(item.amount)?;
    }

    let mut expenses_by_category: BTreeMap<Option<String>, Money> = BTreeMap::new();
    let mut expenses = zero;
    for item in input
        .expenses
        .iter()
        .filter(|e| e.amount.currency() == currency && in_period(e.occurred_on))
    {
        let slot = expenses_by_category
            .entry(item.category_id.clone())
            .or_insert(zero);
        *slot = slot.checked_add(item.amount)?;
        expenses = expenses.checked_add(item.amount)?;
    }

    // Davr oxirigacha yaratilgan faol majburiyatlar (keyinroq qo'shilganlari o'tgan oyga kirmaydi).
    let mut active: Vec<&Obligation> = input
        .obligations
        .iter()
        .filter(|o| {
            o.active
                && o.amount.currency() == currency
                && tashkent_date(o.meta.created_at) < input.period.end
        })
        .collect();
    active.sort_by_key(|o| (o.due_day.unwrap_or(u8::MAX), o.id.clone()));

    let mut pools = expenses_by_category.clone();
    let mut obligations = Vec::with_capacity(active.len());
    for obligation in active {
        let recorded = match &obligation.category_id {
            Some(category) => {
                let key = Some(category.clone());
                let pool = pools.get(&key).copied().unwrap_or(zero);
                let covered = if pool.minor() < obligation.amount.minor() {
                    pool
                } else {
                    obligation.amount
                };
                pools.insert(key, pool.checked_sub(covered)?);
                covered
            }
            None => zero,
        };
        obligations.push(ObligationLine {
            obligation_id: obligation.id.clone(),
            title: obligation.title.clone(),
            kind: obligation.kind,
            amount: obligation.amount,
            recorded,
            remainder: obligation.amount.checked_sub(recorded)?,
        });
    }

    let mut saved_deposited = zero;
    let mut saved_withdrawn = zero;
    for entry in input
        .vault
        .iter()
        .filter(|v| v.amount.currency() == currency && in_period(v.occurred_on))
    {
        match entry.movement {
            VaultMovement::Withdrawal { .. } => {
                saved_withdrawn = saved_withdrawn.checked_add(entry.amount)?;
            }
            VaultMovement::IncomeShare { .. } | VaultMovement::RescueDeposit { .. } => {
                saved_deposited = saved_deposited.checked_add(entry.amount)?;
            }
            VaultMovement::Initial => {}
        }
    }

    Ok(MonthLedger {
        period: input.period,
        currency,
        income,
        expenses_by_category,
        expenses,
        obligations,
        saved_deposited,
        saved_withdrawn,
    })
}

/// «Kimning puli?» egalari (SPEC 2.4). Tartib — ekrandagi tartib bilan bir xil.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub enum MoneyOwner {
    /// Uy egasi (ijara).
    Landlord,
    /// Bank (kredit).
    Bank,
    /// Do'kondor (oziq-ovqat, mayda xarajatlar).
    Shop,
    /// Kommunal va telefon.
    Utilities,
    /// Yoqilg'i va yo'lkira.
    Fuel,
    /// O'zingiz («Kelajagim»).
    SelfOwner,
    /// Sadaqa — isrof emas, alohida (SPEC 2B.8).
    Sadaqa,
    /// Boshqa.
    Other,
    /// Izohsiz qolgan summa.
    Unexplained,
}

impl MoneyOwner {
    /// Bazada va testlarda ishlatiladigan kod.
    pub const fn code(self) -> &'static str {
        match self {
            Self::Landlord => "LANDLORD",
            Self::Bank => "BANK",
            Self::Shop => "SHOP",
            Self::Utilities => "UTILITIES",
            Self::Fuel => "FUEL",
            Self::SelfOwner => "SELF",
            Self::Sadaqa => "SADAQA",
            Self::Other => "OTHER",
            Self::Unexplained => "UNEXPLAINED",
        }
    }
}

/// Kategoriya kaliti bo'yicha egasi. Kalitsiz (foydalanuvchi kategoriyasi) — «Boshqa».
pub fn owner_of_category(key: Option<CategoryKey>) -> MoneyOwner {
    match key {
        Some(CategoryKey::Rent) => MoneyOwner::Landlord,
        Some(CategoryKey::Credit) => MoneyOwner::Bank,
        Some(CategoryKey::Groceries | CategoryKey::DailySmall | CategoryKey::Snacks) => {
            MoneyOwner::Shop
        }
        Some(CategoryKey::Utilities | CategoryKey::Phone) => MoneyOwner::Utilities,
        Some(CategoryKey::Fuel | CategoryKey::Transport) => MoneyOwner::Fuel,
        Some(CategoryKey::Sadaqa) => MoneyOwner::Sadaqa,
        Some(CategoryKey::Children | CategoryKey::Cafe | CategoryKey::Other) | None => {
            MoneyOwner::Other
        }
    }
}

/// Majburiyat turi bo'yicha egasi.
pub fn owner_of_obligation(kind: ObligationKind) -> MoneyOwner {
    match kind {
        ObligationKind::Rent => MoneyOwner::Landlord,
        ObligationKind::Credit => MoneyOwner::Bank,
        ObligationKind::Utility | ObligationKind::Phone => MoneyOwner::Utilities,
        ObligationKind::Fuel => MoneyOwner::Fuel,
        ObligationKind::Other => MoneyOwner::Other,
    }
}

/// Egalar bo'yicha taqsimot: faqat musbat bo'laklar, [`MoneyOwner`] tartibida.
/// `category_keys` — kategoriya ID → tizim kaliti (foydalanuvchi kategoriyasi uchun kalit yo'q).
pub fn whose_money(
    ledger: &MonthLedger,
    category_keys: &BTreeMap<String, CategoryKey>,
) -> Result<Vec<(MoneyOwner, Money)>, DomainError> {
    let mut totals: BTreeMap<MoneyOwner, Money> = BTreeMap::new();
    for (category, amount) in &ledger.expenses_by_category {
        let key = category
            .as_ref()
            .and_then(|id| category_keys.get(id).copied());
        add_positive(&mut totals, owner_of_category(key), *amount)?;
    }
    for line in &ledger.obligations {
        add_positive(&mut totals, owner_of_obligation(line.kind), line.remainder)?;
    }
    add_positive(&mut totals, MoneyOwner::SelfOwner, ledger.net_savings()?)?;
    add_positive(&mut totals, MoneyOwner::Unexplained, ledger.unexplained()?)?;
    Ok(totals.into_iter().collect())
}

fn add_positive(
    totals: &mut BTreeMap<MoneyOwner, Money>,
    owner: MoneyOwner,
    amount: Money,
) -> Result<(), DomainError> {
    if amount.minor() <= 0 {
        return Ok(());
    }
    let next = match totals.get(&owner) {
        Some(current) => current.checked_add(amount)?,
        None => amount,
    };
    totals.insert(owner, next);
    Ok(())
}

fn sum(currency: Currency, amounts: impl Iterator<Item = Money>) -> Result<Money, DomainError> {
    let mut total = Money::zero(currency);
    for amount in amounts {
        total = total.checked_add(amount)?;
    }
    Ok(total)
}

#[cfg(test)]
mod tests {
    use super::*;
    use money::Currency::Uzs;

    #[test]
    fn izohsiz_summa_spec_vektori_bilan() {
        // unexplained_gap.json, gap-001 (minor birlikda): 800 − (535 + 165 + 0) = 100 mln tiyin.
        let gap = unexplained_gap(
            Money::new(800_000_000, Uzs),
            Money::new(535_000_000, Uzs),
            Money::new(165_000_000, Uzs),
            Money::zero(Uzs),
        )
        .expect("hisob");
        assert_eq!(gap.minor(), 100_000_000);
    }

    #[test]
    fn owner_kategoriya_va_majburiyat_boyicha() {
        assert_eq!(
            owner_of_category(Some(CategoryKey::Groceries)),
            MoneyOwner::Shop
        );
        assert_eq!(owner_of_category(None), MoneyOwner::Other);
        assert_eq!(
            owner_of_obligation(ObligationKind::Credit),
            MoneyOwner::Bank
        );
    }

    #[test]
    fn musbat_bolaklar_tartib_bilan() {
        let mut totals = BTreeMap::new();
        add_positive(&mut totals, MoneyOwner::Shop, Money::new(5, Uzs)).expect("qo'shish");
        add_positive(&mut totals, MoneyOwner::Shop, Money::new(7, Uzs)).expect("qo'shish");
        add_positive(&mut totals, MoneyOwner::Bank, Money::new(-3, Uzs)).expect("qo'shish");
        let ordered: Vec<(MoneyOwner, i64)> = totals
            .into_iter()
            .map(|(owner, amount)| (owner, amount.minor()))
            .collect();
        assert_eq!(ordered, vec![(MoneyOwner::Shop, 12)]);
    }
}
