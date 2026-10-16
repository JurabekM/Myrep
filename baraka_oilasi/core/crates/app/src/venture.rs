//! 5-qonun use-case'lari (U12): sheriklik kassa daftari (venture ledger), davrni yopish va
//! avtomatik taqsimot (buyout ayirmasi bilan), sherik uchun davr hisoboti PDF, «Hunardan ishga»
//! rejalovchisi va «kafolatlangan foyda» detektori.
//!
//! Qoidalar `domain-uy::venture` da (vektorlar `venture_period`, `venture_idea`, `offer_check`).
//! Har bir daftar yozuvi kelishuv jurnaliga ham yoziladi (xesh-zanjir). Yozuvlar, ilovalar va
//! yopilgan davrlar DB darajasida o'zgarmas: xato faqat yangi tuzatuvchi yozuv bilan to'g'rilanadi.
//! Biznes puli uy pulidan ajratilgan: xonadon byudjetiga faqat taqsimlangan ulush `Income`
//! (`MOL` / `TAVAKKAL`) sifatida tushadi. Daftarga faqat hisob yurituvchi (6-savol) yozadi.
use std::collections::{BTreeMap, BTreeSet};

use baraka_domain_uy::partnership::{Negligence, Partner, PartnerRole, PartnershipKind};
use baraka_domain_uy::venture::{
    close_period, offer_check, venture_idea, BuyoutDue, EntryKind as VKind, IdeaInput,
    IdeaScenario, Installment, LossPolicy, OfferAnswers, PeriodEntry, PeriodInput, PeriodResult,
    Reply, ScenarioName,
};
use baraka_journal::{
    short_code, verify_chain, EntryKind, JournalAmount, JournalEntry, GENESIS_HASH,
};
use baraka_money::{format, format_plain, Currency, Money};
use baraka_pdf::{ReportBuyout, ReportEntry, ReportParty, VentureReport};
use baraka_storage::repo::partnerships::{self as prepo, PartnershipRow};
use baraka_storage::repo::ventures::{
    self as repo, AttachmentMeta, AttachmentRow, EntryRow, IdeaRow, PeriodRow, SkillRow,
};
use baraka_storage::repo::{agreements, household, incomes, journal};
use baraka_storage::SpaceScope;
use chrono::{Days, NaiveDate};
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};

use crate::app::Ctx;
use crate::events::Topic;
use crate::partnership::{engine, Payload};
use crate::receipt::{amount_in, date, pdf_locale, positive, ymd};
use crate::text::{clean, clean_opt, required};
use crate::*;

const ACTIVE: &str = "ACTIVE";
pub(crate) const MAX_ATTACHMENTS: usize = 5;
pub(crate) const MAX_ATTACHMENT_BYTES: usize = 5 * 1024 * 1024;
const INCOME_CATEGORIES: [&str; 2] = ["ORDER", "OTHER"];
const EXPENSE_CATEGORIES: [&str; 6] = [
    "MATERIAL",
    "WAGE",
    "RENT",
    "EQUIPMENT",
    "TRANSPORT",
    "OTHER",
];

fn corrupt() -> AppError {
    AppError::new("CORRUPT_ROW")
}

fn overflow() -> AppError {
    AppError::new("OVERFLOW")
}

fn u32_of(n: usize) -> Result<u32, AppError> {
    u32::try_from(n).map_err(|_| overflow())
}

fn hex(bytes: &[u8]) -> String {
    bytes.iter().map(|b| format!("{b:02x}")).collect()
}

fn ymd_parse(s: &str) -> Result<NaiveDate, AppError> {
    NaiveDate::parse_from_str(s, "%Y-%m-%d").map_err(|_| corrupt())
}

fn show(d: &str) -> String {
    NaiveDate::parse_from_str(d, "%Y-%m-%d")
        .map_or_else(|_| d.to_string(), |x| x.format("%d.%m.%Y").to_string())
}

/// Natijaga ta'sir ishorasi: kirim `+`, xarajat va fors-major `−`, tuzatish — o'zi ishorali.
fn sign(kind: &str) -> i64 {
    match kind {
        "EXPENSE" | "FORCE_MAJEURE" => -1,
        _ => 1,
    }
}

fn effect(e: &EntryRow) -> Result<i64, AppError> {
    e.amount_minor
        .checked_mul(sign(&e.kind))
        .ok_or_else(overflow)
}

/// Fayl turini baytlardan aniqlaydi (kengaytmaga ishonilmaydi).
fn sniff(b: &[u8]) -> Option<&'static str> {
    if b.starts_with(&[0xFF, 0xD8, 0xFF]) {
        Some("image/jpeg")
    } else if b.starts_with(&[0x89, b'P', b'N', b'G', 0x0D, 0x0A, 0x1A, 0x0A]) {
        Some("image/png")
    } else if b.len() >= 12 && &b[..4] == b"RIFF" && &b[8..12] == b"WEBP" {
        Some("image/webp")
    } else if b.starts_with(b"%PDF-") {
        Some("application/pdf")
    } else {
        None
    }
}

// ---- yopilgan davrning saqlanadigan natijasi (`venture_periods.result_json`) ----

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
struct StoredParty {
    id: String,
    name: String,
    role: String,
    share: i64,
    recovered: i64,
    liability: i64,
    payout: i64,
    carried_after: i64,
    capital_after: i64,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
struct StoredBuyout {
    paid: Vec<u32>,
    unpaid: Vec<u32>,
    amount: i64,
    capital: i64,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
struct StoredNegligence {
    party_id: String,
    note: String,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
struct StoredPeriod {
    entries: u32,
    income: i64,
    expense: i64,
    force_majeure: i64,
    corrections: i64,
    result: i64,
    distributable: i64,
    parties: Vec<StoredParty>,
    buyout: Option<StoredBuyout>,
    negligence: Option<StoredNegligence>,
    my_income: i64,
    income_ids: Vec<String>,
}

// ---- «Hunardan ishga» saqlanadigan JSON ----

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
struct CapexJ {
    title: String,
    amount_minor: i64,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
struct ScenarioJ {
    name: String,
    income_minor: i64,
    expense_minor: i64,
}

/// Daftar holati: kuchdagi shartnoma shartlari, yozuvlar, yopilgan davrlar va zanjir.
struct Ledger {
    row: PartnershipRow,
    terms: Payload,
    version: i64,
    cur: Currency,
    entries: Vec<EntryRow>,
    attachments: Vec<AttachmentMeta>,
    periods: Vec<(PeriodRow, StoredPeriod)>,
    start: NaiveDate,
    keeper: Option<String>,
    read_only: Option<&'static str>,
    hashes: BTreeMap<String, String>,
    head: String,
    chain_ok: bool,
}

/// Davr boshidagi holat: kapital qoldiqlari, tiklanmagan zararlar, to'langan buyout bosqichlari.
struct State {
    capital: Vec<i64>,
    carried: Vec<i64>,
    paid: BTreeSet<u32>,
}

impl Ledger {
    fn last_end(&self) -> Option<&str> {
        self.periods.last().map(|(p, _)| p.end_on.as_str())
    }

    fn open_from(&self) -> Result<NaiveDate, AppError> {
        match self.last_end() {
            None => Ok(self.start),
            Some(e) => ymd_parse(e)?
                .checked_add_days(Days::new(1))
                .ok_or(AppError::new("INVALID_DATE")),
        }
    }

    fn open_entries(&self) -> impl Iterator<Item = &EntryRow> {
        let last = self.last_end().map(str::to_string);
        self.entries
            .iter()
            .filter(move |e| last.as_deref().is_none_or(|l| e.occurred_on.as_str() > l))
    }

    fn me_index(&self) -> Option<usize> {
        self.terms.parties.iter().position(|p| p.is_me)
    }

    fn state(&self) -> State {
        let mut capital: Vec<i64> = self.terms.parties.iter().map(Payload::capital_of).collect();
        let mut carried = vec![0; capital.len()];
        let mut paid = BTreeSet::new();
        for (_, s) in &self.periods {
            for (i, p) in self.terms.parties.iter().enumerate() {
                if let Some(x) = s.parties.iter().find(|x| x.id == p.id) {
                    capital[i] = x.capital_after;
                    carried[i] = x.carried_after;
                }
            }
            if let Some(b) = &s.buyout {
                paid.extend(b.paid.iter().copied());
            }
        }
        State {
            capital,
            carried,
            paid,
        }
    }

    fn period_of(&self, d: &str) -> Option<u32> {
        self.periods
            .iter()
            .find(|(p, _)| p.start_on.as_str() <= d && d <= p.end_on.as_str())
            .and_then(|(p, _)| u32::try_from(p.period_no).ok())
    }
}

impl App {
    fn venture_book(&self, scope: &SpaceScope, id: &str) -> Result<Ledger, AppError> {
        let row = self.partnership_row(scope, id)?;
        let version = row.signed_version.ok_or(AppError::new("NOT_ACTIVE"))?;
        if row.activated_on.is_none() {
            return Err(AppError::new("NOT_ACTIVE"));
        }
        let versions = self
            .db
            .read(|c| prepo::versions(c, scope, &row.agreement_id))?;
        let signed = versions
            .iter()
            .find(|v| v.version_no == version)
            .ok_or_else(corrupt)?;
        let terms: Payload = serde_json::from_str(&signed.payload_json).map_err(|_| corrupt())?;
        let cur = Currency::from_code(&terms.currency)?;
        let start = match terms.term.value() {
            Some(t) => ymd_parse(&t.effective_from)?,
            None => ymd_parse(row.activated_on.as_deref().unwrap_or_default())?,
        };
        let me = terms.me().map(|m| m.id.clone());
        let keeper = terms
            .custody
            .value()
            .map(|c| c.keeper_party_id.clone())
            .or_else(|| me.clone());
        let agreement = self
            .db
            .read(|c| agreements::get(c, scope, &row.agreement_id))?
            .ok_or_else(corrupt)?;
        let read_only = if row.status != ACTIVE {
            Some("NOT_ACTIVE")
        } else if me.is_none() || keeper != me || agreement.keeper_device_id != self.device_id {
            Some("NOT_KEEPER")
        } else {
            None
        };
        let entries = self.db.read(|c| repo::entries(c, scope, id))?;
        let attachments = self.db.read(|c| repo::attachments(c, scope, id))?;
        let periods = self
            .db
            .read(|c| repo::periods(c, scope, id))?
            .into_iter()
            .map(|p| {
                let s: StoredPeriod =
                    serde_json::from_str(&p.result_json).map_err(|_| corrupt())?;
                Ok((p, s))
            })
            .collect::<Result<Vec<_>, AppError>>()?;
        let stored = self
            .db
            .read(|c| journal::list(c, scope, &row.agreement_id))?;
        let list: Vec<JournalEntry> = stored.iter().map(|s| s.entry.clone()).collect();
        let hs: Vec<String> = stored.iter().map(|s| s.hash.clone()).collect();
        let chain_ok = verify_chain(&list, &hs).is_ok();
        let head = hs
            .last()
            .cloned()
            .unwrap_or_else(|| GENESIS_HASH.to_string());
        let hashes = stored.into_iter().map(|s| (s.entry.id, s.hash)).collect();
        Ok(Ledger {
            row,
            terms,
            version,
            cur,
            entries,
            attachments,
            periods,
            start,
            keeper,
            read_only,
            hashes,
            head,
            chain_ok,
        })
    }

    fn writable(l: &Ledger) -> Result<(), AppError> {
        match l.read_only {
            Some(code) => Err(AppError::new(code)),
            None => Ok(()),
        }
    }

    /// Ochiq davrdagi yozuvlar soni — sheriklikni yopishdan oldin davr yopilishi kerak.
    pub(crate) fn venture_open_entries(
        &self,
        scope: &SpaceScope,
        row: &PartnershipRow,
    ) -> Result<usize, AppError> {
        if row.activated_on.is_none() {
            return Ok(0);
        }
        let last = self
            .db
            .read(|c| repo::periods(c, scope, &row.id))?
            .last()
            .map(|p| p.end_on.clone());
        Ok(self
            .db
            .read(|c| repo::entries(c, scope, &row.id))?
            .iter()
            .filter(|e| last.as_deref().is_none_or(|l| e.occurred_on.as_str() > l))
            .count())
    }

    fn period_input(
        l: &Ledger,
        end: NaiveDate,
        negligence: Option<&NegligenceInput>,
        prices: &[InstallmentPriceInput],
    ) -> Result<(PeriodInput, u32), AppError> {
        let kind = l.terms.kind()?;
        let st = l.state();
        let partners = l
            .terms
            .parties
            .iter()
            .zip(&st.capital)
            .map(|(p, c)| {
                Ok(Partner {
                    id: p.id.clone(),
                    role: PartnerRole::parse(&p.role).ok_or_else(corrupt)?,
                    profit_share_bp: p.profit_share_bp,
                    capital: Money::new(*c, l.cur),
                })
            })
            .collect::<Result<Vec<_>, AppError>>()?;
        let end_s = ymd(end);
        let mut entries = Vec::new();
        for e in l.open_entries().filter(|e| e.occurred_on <= end_s) {
            entries.push(PeriodEntry {
                kind: VKind::parse(&e.kind).ok_or_else(corrupt)?,
                amount: Money::new(e.amount_minor, l.cur),
            });
        }
        let count = u32_of(entries.len())?;
        let buyout = match (&l.terms.buyout, l.terms.buyout(l.cur)?) {
            (Some(b), Some(Ok(sch))) => {
                let mut due = Vec::new();
                for r in sch
                    .rows
                    .iter()
                    .filter(|r| r.date <= end && !st.paid.contains(&r.period))
                {
                    let price = match prices.iter().find(|p| p.no == r.period) {
                        Some(p) => {
                            let m = amount_in(&p.price, l.cur, "buyoutPrices")?;
                            if m.is_negative() {
                                return Err(AppError::on("AMOUNT_NEGATIVE", "buyoutPrices"));
                            }
                            m
                        }
                        None => r.payment,
                    };
                    due.push(Installment {
                        no: r.period,
                        units: r.units,
                        capital: r.payment,
                        price,
                    });
                }
                Some(BuyoutDue {
                    seller_id: b.seller_party_id.clone(),
                    buyer_id: b.buyer_party_id.clone(),
                    due,
                })
            }
            _ => None,
        };
        let negligence = match negligence {
            None => None,
            Some(n) => Some(Negligence {
                partner_id: n.party_id.clone(),
                note: required(&n.note, "negligence")?,
            }),
        };
        Ok((
            PeriodInput {
                kind,
                currency: l.cur,
                partners,
                entries,
                policy: LossPolicy::default(),
                carried: st.carried.iter().map(|c| Money::new(*c, l.cur)).collect(),
                negligence,
                buyout,
            },
            count,
        ))
    }

    /// Domen natijasini saqlanadigan ko'rinishga o'tkazadi; `my_income` — xonadonga tushadigan ulush.
    fn stored(l: &Ledger, input: &PeriodInput, r: &PeriodResult, count: u32) -> StoredPeriod {
        let parties = l
            .terms
            .parties
            .iter()
            .enumerate()
            .map(|(i, p)| StoredParty {
                id: p.id.clone(),
                name: p.full_name.clone(),
                role: p.role.clone(),
                share: r.shares[i].minor(),
                recovered: r.recovered[i].minor(),
                liability: r.liability[i].minor(),
                payout: r.payouts[i].minor(),
                carried_after: r.carried_after[i].minor(),
                capital_after: r.capital_after[i].minor(),
            })
            .collect();
        StoredPeriod {
            entries: count,
            income: r.income.minor(),
            expense: r.expense.minor(),
            force_majeure: r.force_majeure.minor(),
            corrections: r.corrections.minor(),
            result: r.result.minor(),
            distributable: r.distributable.minor(),
            parties,
            buyout: r.buyout.as_ref().map(|b| StoredBuyout {
                paid: b.paid.clone(),
                unpaid: b.unpaid.clone(),
                amount: b.amount.minor(),
                capital: b.capital.minor(),
            }),
            negligence: input.negligence.as_ref().map(|n| StoredNegligence {
                party_id: n.partner_id.clone(),
                note: n.note.clone(),
            }),
            my_income: l.me_index().map_or(0, |i| r.payouts[i].minor()),
            income_ids: Vec::new(),
        }
    }

    #[allow(clippy::too_many_arguments)]
    fn period_dto(
        &self,
        ctx: &Ctx,
        l: &Ledger,
        id: Option<String>,
        no: u32,
        start: &str,
        end: &str,
        closed_at: Option<String>,
        s: &StoredPeriod,
        chain: Option<&str>,
    ) -> VenturePeriodDto {
        let m = |v: i64| self.money_dto(ctx, Money::new(v, l.cur));
        let me = l.terms.me().map(|p| p.id.clone());
        VenturePeriodDto {
            id,
            no,
            start_on: start.to_string(),
            end_on: end.to_string(),
            closed_at,
            entries: s.entries,
            income: m(s.income),
            expense: m(s.expense),
            force_majeure: m(s.force_majeure),
            corrections: m(s.corrections),
            result: m(s.result),
            recovered: m(s.parties.iter().map(|p| p.recovered).sum()),
            distributable: m(s.distributable),
            parties: s
                .parties
                .iter()
                .map(|p| PeriodPartyDto {
                    party_id: p.id.clone(),
                    name: p.name.clone(),
                    role: p.role.clone(),
                    is_me: me.as_deref() == Some(p.id.as_str()),
                    share: m(p.share),
                    recovered: m(p.recovered),
                    liability: m(p.liability),
                    payout: m(p.payout),
                    carried_after: m(p.carried_after),
                    capital_after: m(p.capital_after),
                })
                .collect(),
            buyout: s.buyout.as_ref().map(|b| PeriodBuyoutDto {
                paid: b.paid.clone(),
                unpaid: b.unpaid.clone(),
                amount: m(b.amount),
                capital: m(b.capital),
            }),
            loss_policy: LossPolicy::default().as_str().into(),
            negligent_party: s
                .negligence
                .as_ref()
                .map(|n| l.terms.party_name(&n.party_id)),
            negligence_note: s.negligence.as_ref().map(|n| n.note.clone()),
            my_income: m(s.my_income),
            chain_code: chain.map(short_code),
        }
    }

    fn entry_dto(&self, ctx: &Ctx, l: &Ledger, e: &EntryRow) -> Result<VentureEntryDto, AppError> {
        let m = |v: i64| self.money_dto(ctx, Money::new(v, l.cur));
        Ok(VentureEntryDto {
            id: e.id.clone(),
            kind: e.kind.clone(),
            category: e.category.clone(),
            amount: m(e.amount_minor),
            effect: m(effect(e)?),
            occurred_on: e.occurred_on.clone(),
            note: e.note.clone(),
            corrects_entry_id: e.corrects_entry_id.clone(),
            corrected: l
                .entries
                .iter()
                .any(|x| x.corrects_entry_id.as_deref() == Some(e.id.as_str())),
            period_no: l.period_of(&e.occurred_on),
            attachments: l
                .attachments
                .iter()
                .filter(|a| a.entry_id == e.id)
                .map(|a| AttachmentMetaDto {
                    id: a.id.clone(),
                    file_name: a.file_name.clone(),
                    mime: a.mime.clone(),
                    size_bytes: u32::try_from(a.size_bytes).unwrap_or(u32::MAX),
                })
                .collect(),
            hash_code: l
                .hashes
                .get(&e.journal_entry_id)
                .map(|h| short_code(h))
                .unwrap_or_default(),
        })
    }

    fn ledger_dto(&self, ctx: &Ctx, l: &Ledger) -> Result<VentureLedgerDto, AppError> {
        let m = |v: i64| self.money_dto(ctx, Money::new(v, l.cur));
        let st = l.state();
        let (mut inc, mut exp, mut fm, mut corr, mut n) = (0_i64, 0_i64, 0_i64, 0_i64, 0_usize);
        for e in l.open_entries() {
            let slot = match e.kind.as_str() {
                "INCOME" => &mut inc,
                "EXPENSE" => &mut exp,
                "FORCE_MAJEURE" => &mut fm,
                _ => &mut corr,
            };
            *slot = slot.checked_add(e.amount_minor).ok_or_else(overflow)?;
            n += 1;
        }
        let result = inc
            .checked_sub(exp)
            .and_then(|x| x.checked_sub(fm))
            .and_then(|x| x.checked_add(corr))
            .ok_or_else(overflow)?;
        let next_no = u32_of(l.periods.len() + 1)?;
        let mut entries = l
            .entries
            .iter()
            .map(|e| self.entry_dto(ctx, l, e))
            .collect::<Result<Vec<_>, AppError>>()?;
        entries.reverse();
        let periods = l
            .periods
            .iter()
            .rev()
            .map(|(p, s)| {
                Ok(self.period_dto(
                    ctx,
                    l,
                    Some(p.id.clone()),
                    u32::try_from(p.period_no).map_err(|_| corrupt())?,
                    &p.start_on,
                    &p.end_on,
                    Some(p.closed_at.clone()),
                    s,
                    Some(&p.chain_head),
                ))
            })
            .collect::<Result<Vec<_>, AppError>>()?;
        let balances = l
            .terms
            .parties
            .iter()
            .enumerate()
            .map(|(i, p)| PartyBalanceDto {
                party_id: p.id.clone(),
                name: p.full_name.clone(),
                role: p.role.clone(),
                is_me: p.is_me,
                capital: m(st.capital[i]),
                carried_loss: m(st.carried[i]),
            })
            .collect();
        let today = self.today(ctx);
        let buyout = match (&l.terms.buyout, l.terms.buyout(l.cur)?) {
            (Some(b), Some(Ok(sch))) => {
                let next = sch.rows.iter().find(|r| !st.paid.contains(&r.period));
                Some(BuyoutProgressDto {
                    seller_name: l.terms.party_name(&b.seller_party_id),
                    buyer_name: l.terms.party_name(&b.buyer_party_id),
                    paid: u32_of(st.paid.len())?,
                    total: u32_of(sch.rows.len())?,
                    next_no: next.map(|r| r.period),
                    next_date: next.map(|r| ymd(r.date)),
                    next_payment: next.map(|r| self.money_dto(ctx, r.payment)),
                    overdue: sch
                        .rows
                        .iter()
                        .filter(|r| r.date <= today && !st.paid.contains(&r.period))
                        .map(|r| r.period)
                        .collect(),
                })
            }
            _ => None,
        };
        Ok(VentureLedgerDto {
            partnership_id: l.row.id.clone(),
            title: l.row.title.clone(),
            kind: l.row.kind.clone(),
            status: l.row.status.clone(),
            currency: l.cur.code().to_string(),
            writable: l.read_only.is_none(),
            read_only_reason: l.read_only.map(str::to_string),
            keeper_name: l.keeper.as_deref().map(|k| l.terms.party_name(k)),
            start_on: ymd(l.start),
            open: OpenPeriodDto {
                no: next_no,
                from: ymd(l.open_from()?),
                entries: u32_of(n)?,
                income: m(inc),
                expense: m(exp),
                force_majeure: m(fm),
                corrections: m(corr),
                result: m(result),
            },
            entries,
            periods,
            balances,
            buyout,
            chain_code: short_code(&l.head),
            chain_ok: l.chain_ok,
            loss_policy: LossPolicy::default().as_str().into(),
        })
    }

    // ---- ommaviy use-case'lar: kassa daftari ----

    pub fn venture_ledger(
        &self,
        space_id: &str,
        partnership_id: &str,
    ) -> Result<VentureLedgerDto, AppError> {
        let ctx = self.ctx()?;
        let scope = self.scope(&ctx, space_id)?;
        let l = self.venture_book(&scope, partnership_id)?;
        self.ledger_dto(&ctx, &l)
    }

    /// Daftarga yozuv: kirim, xarajat, fors-major yoki tuzatish. Jurnalga ham yoziladi; ilovalar
    /// SHA-256 bilan jurnal `refs` ida qayd etiladi (keyin almashtirilsa — sezilad).
    pub fn add_venture_entry(
        &self,
        space_id: &str,
        partnership_id: &str,
        input: VentureEntryInput,
    ) -> Result<VentureLedgerDto, AppError> {
        let ctx = self.ctx()?;
        let scope = self.scope(&ctx, space_id)?;
        let l = self.venture_book(&scope, partnership_id)?;
        Self::writable(&l)?;
        let kind = VKind::parse(&input.kind).ok_or(AppError::on("INVALID_ENTRY_KIND", "kind"))?;
        let on = date(&input.occurred_on, "occurredOn")?;
        if on > self.today(&ctx) {
            return Err(AppError::on("FUTURE_DATE", "occurredOn"));
        }
        if on < l.start {
            return Err(AppError::on("BEFORE_START", "occurredOn"));
        }
        if on < l.open_from()? {
            return Err(AppError::on("PERIOD_CLOSED", "occurredOn"));
        }
        let note = clean_opt(input.note.as_deref());
        let category = match kind {
            VKind::Income | VKind::Expense => {
                let allowed: &[&str] = if kind == VKind::Income {
                    &INCOME_CATEGORIES
                } else {
                    &EXPENSE_CATEGORIES
                };
                let c = input.category.as_deref().unwrap_or("OTHER");
                if !allowed.contains(&c) {
                    return Err(AppError::on("INVALID_CATEGORY", "category"));
                }
                Some(c.to_string())
            }
            _ => None,
        };
        let (amount, target) = match kind {
            VKind::Correction => {
                if note.is_none() {
                    return Err(AppError::on("REQUIRED", "note"));
                }
                let tid = input
                    .corrects_entry_id
                    .as_deref()
                    .ok_or(AppError::on("REQUIRED", "correctsEntryId"))?;
                let t = l
                    .entries
                    .iter()
                    .find(|e| e.id == tid)
                    .ok_or(AppError::on("NOT_FOUND", "correctsEntryId"))?;
                if t.kind == VKind::Correction.as_str() {
                    return Err(AppError::on("CORRECTION_OF_CORRECTION", "correctsEntryId"));
                }
                let wanted = amount_in(&input.amount, l.cur, "amount")?;
                if wanted.is_negative() {
                    return Err(AppError::on("AMOUNT_NEGATIVE", "amount"));
                }
                let mut current = effect(t)?;
                for c in l
                    .entries
                    .iter()
                    .filter(|c| c.corrects_entry_id.as_deref() == Some(tid))
                {
                    current = current.checked_add(c.amount_minor).ok_or_else(overflow)?;
                }
                let desired = wanted
                    .minor()
                    .checked_mul(sign(&t.kind))
                    .ok_or_else(overflow)?;
                let delta = desired.checked_sub(current).ok_or_else(overflow)?;
                if delta == 0 {
                    return Err(AppError::on("NOTHING_TO_CORRECT", "amount"));
                }
                (delta, Some(t))
            }
            _ => {
                if kind == VKind::ForceMajeure && note.is_none() {
                    return Err(AppError::on("REQUIRED", "note"));
                }
                if input.corrects_entry_id.is_some() {
                    return Err(AppError::on(
                        "CORRECTION_TARGET_NOT_ALLOWED",
                        "correctsEntryId",
                    ));
                }
                (positive(&input.amount, l.cur, "amount")?.minor(), None)
            }
        };
        if input.attachments.len() > MAX_ATTACHMENTS {
            return Err(AppError::on("TOO_MANY_ATTACHMENTS", "attachments"));
        }
        let entry_id = self.new_id();
        let mut atts = Vec::new();
        for a in &input.attachments {
            if a.bytes.is_empty() || a.bytes.len() > MAX_ATTACHMENT_BYTES {
                return Err(AppError::on("ATTACHMENT_TOO_LARGE", "attachments"));
            }
            let mime = sniff(&a.bytes)
                .ok_or(AppError::on("ATTACHMENT_TYPE_NOT_ALLOWED", "attachments"))?;
            let name: String = required(&a.file_name, "attachments")?
                .chars()
                .take(120)
                .collect();
            atts.push(AttachmentRow {
                meta: AttachmentMeta {
                    id: self.new_id(),
                    entry_id: entry_id.clone(),
                    file_name: name,
                    mime: mime.into(),
                    size_bytes: i64::try_from(a.bytes.len()).map_err(|_| overflow())?,
                    sha256: hex(&Sha256::digest(&a.bytes)),
                },
                bytes: a.bytes.clone(),
            });
        }
        let mut refs = vec![format!("venture:{}", kind.as_str())];
        if let Some(c) = &category {
            refs.push(format!("category:{c}"));
        }
        refs.extend(atts.iter().map(|a| format!("att:sha256:{}", a.meta.sha256)));
        let je = JournalEntry {
            id: self.new_id(),
            agreement_id: l.row.agreement_id.clone(),
            kind: match kind {
                VKind::Income => EntryKind::Revenue,
                VKind::Expense | VKind::ForceMajeure => EntryKind::Expense,
                VKind::Correction => EntryKind::Correction,
            },
            party_id: None,
            amount: Some(JournalAmount {
                minor: amount,
                currency: l.cur.code().to_string(),
            }),
            date: ymd(on),
            note: note.clone(),
            corrects_entry_id: target.map(|t| t.journal_entry_id.clone()),
            refs,
        };
        je.validate()?;
        let row = EntryRow {
            id: entry_id,
            partnership_id: l.row.id.clone(),
            journal_entry_id: je.id.clone(),
            kind: kind.as_str().into(),
            category,
            amount_minor: amount,
            currency: l.cur.code().to_string(),
            occurred_on: ymd(on),
            note,
            corrects_entry_id: target.map(|t| t.id.clone()),
            created_at: String::new(),
        };
        let meta = self.meta();
        self.db.write(|tx| {
            journal::append(tx, &scope, &je, &meta)?;
            repo::insert_entry(tx, &scope, &row, &meta)?;
            for a in &atts {
                repo::insert_attachment(tx, &scope, a, &meta)?;
            }
            Ok(())
        })?;
        self.publish(Some(space_id), &[Topic::Ventures, Topic::Journal]);
        self.venture_ledger(space_id, partnership_id)
    }

    pub fn venture_attachment(
        &self,
        space_id: &str,
        partnership_id: &str,
        attachment_id: &str,
    ) -> Result<AttachmentDto, AppError> {
        let ctx = self.ctx()?;
        let scope = self.scope(&ctx, space_id)?;
        let a = self
            .db
            .read(|c| repo::attachment(c, &scope, partnership_id, attachment_id))?
            .ok_or(AppError::on("NOT_FOUND", "attachmentId"))?;
        Ok(AttachmentDto {
            file_name: a.meta.file_name,
            mime: a.meta.mime,
            bytes: a.bytes,
        })
    }

    fn checked_end(&self, ctx: &Ctx, l: &Ledger, end_on: &str) -> Result<NaiveDate, AppError> {
        let end = date(end_on, "endOn")?;
        if end > self.today(ctx) {
            return Err(AppError::on("FUTURE_DATE", "endOn"));
        }
        if end < l.open_from()? {
            return Err(AppError::on("INVALID_PERIOD_END", "endOn"));
        }
        Ok(end)
    }

    /// Davrni yopishdan oldin natija va taqsimotni ko'rsatadi (hech narsa yozilmaydi).
    pub fn venture_period_preview(
        &self,
        space_id: &str,
        partnership_id: &str,
        input: ClosePeriodInput,
    ) -> Result<VenturePeriodDto, AppError> {
        let ctx = self.ctx()?;
        let scope = self.scope(&ctx, space_id)?;
        let l = self.venture_book(&scope, partnership_id)?;
        let end = self.checked_end(&ctx, &l, &input.end_on)?;
        let (pi, count) =
            Self::period_input(&l, end, input.negligence.as_ref(), &input.buyout_prices)?;
        if count == 0 {
            return Err(AppError::on("PERIOD_EMPTY", "endOn"));
        }
        let r = close_period(&pi)?;
        let s = Self::stored(&l, &pi, &r, count);
        Ok(self.period_dto(
            &ctx,
            &l,
            None,
            u32_of(l.periods.len() + 1)?,
            &ymd(l.open_from()?),
            &ymd(end),
            None,
            &s,
            None,
        ))
    }

    /// Davrni yopish: taqsimot jurnalga yoziladi, davr o'zgarmas bo'ladi, «biz»ning ulushi
    /// xonadonga `Income` bo'lib tushadi (sotuvchi bo'lsak — buyout tushumi alohida, `MOL`).
    pub fn close_venture_period(
        &self,
        space_id: &str,
        partnership_id: &str,
        input: ClosePeriodInput,
    ) -> Result<VentureLedgerDto, AppError> {
        let ctx = self.ctx()?;
        let scope = self.scope(&ctx, space_id)?;
        let l = self.venture_book(&scope, partnership_id)?;
        Self::writable(&l)?;
        if !matches!(input.channel.as_str(), "CASH" | "CARD") {
            return Err(AppError::on("INVALID_CHANNEL", "channel"));
        }
        let end = self.checked_end(&ctx, &l, &input.end_on)?;
        let (pi, count) =
            Self::period_input(&l, end, input.negligence.as_ref(), &input.buyout_prices)?;
        if count == 0 {
            return Err(AppError::on("PERIOD_EMPTY", "endOn"));
        }
        let r = close_period(&pi)?;
        let mut s = Self::stored(&l, &pi, &r, count);
        let no = i64::try_from(l.periods.len() + 1).map_err(|_| overflow())?;
        let end_s = ymd(end);
        let cur = l.cur.code().to_string();
        // Har bir tomon uchun bitta jurnal yozuvi: foyda ulushi (to'lov) yoki zarar ulushi.
        let mut journal_entries = Vec::new();
        for (i, p) in s.parties.iter().enumerate() {
            let mut refs = vec![
                format!("venturePeriod:{no}"),
                format!("result:{}", s.result),
                format!("share:{}", p.share),
            ];
            if p.recovered != 0 {
                refs.push(format!("recovered:{}", p.recovered));
            }
            let (kind, amount) = if s.result >= 0 {
                if let Some(b) = &s.buyout {
                    let delta = p.payout - p.share.max(0);
                    if delta != 0 {
                        let nos: Vec<String> = b.paid.iter().map(u32::to_string).collect();
                        refs.push(format!("buyout:{delta}:{}", nos.join(",")));
                    }
                }
                (EntryKind::ProfitDistribution, p.payout)
            } else if p.liability > 0 {
                refs.push("negligence".into());
                (EntryKind::LossAllocation, p.liability)
            } else {
                (EntryKind::LossAllocation, -r.shares[i].minor())
            };
            journal_entries.push(JournalEntry {
                id: self.new_id(),
                agreement_id: l.row.agreement_id.clone(),
                kind,
                party_id: Some(p.id.clone()),
                amount: Some(JournalAmount {
                    minor: amount,
                    currency: cur.clone(),
                }),
                date: end_s.clone(),
                note: None,
                corrects_entry_id: None,
                refs,
            });
        }
        for e in &journal_entries {
            e.validate()?;
        }
        // Xonadon byudjetiga faqat taqsimlangan ulush (uy/SPEC 2E.3).
        let mut incomes_rows = Vec::new();
        if let Some(i) = l.me_index() {
            let me = &l.terms.parties[i];
            let p = &s.parties[i];
            let proceeds = match &s.buyout {
                Some(b)
                    if l.terms
                        .buyout
                        .as_ref()
                        .is_some_and(|x| x.seller_party_id == me.id) =>
                {
                    b.amount
                }
                _ => 0,
            };
            let profit = p.payout - proceeds;
            let source_type = if me.role == PartnerRole::CapitalProvider.as_str() {
                "MOL"
            } else {
                "TAVAKKAL"
            };
            for (amount, st) in [(profit, source_type), (proceeds, "MOL")] {
                if amount > 0 {
                    incomes_rows.push(incomes::IncomeRow {
                        id: self.new_id(),
                        member_id: None,
                        amount_minor: amount,
                        currency: cur.clone(),
                        source: l.row.title.clone(),
                        channel: input.channel.clone(),
                        source_type: Some(st.into()),
                        occurred_on: end_s.clone(),
                        note: None,
                    });
                }
            }
        }
        s.income_ids = incomes_rows.iter().map(|x| x.id.clone()).collect();
        let meta = self.meta();
        let period_id = self.new_id();
        let start_s = ymd(l.open_from()?);
        let policy = pi.policy.as_str().to_string();
        let json = serde_json::to_string(&s).map_err(|_| corrupt())?;
        self.db.write(|tx| {
            let mut head = l.head.clone();
            for e in &journal_entries {
                head = journal::append(tx, &scope, e, &meta)?.hash;
            }
            for x in &incomes_rows {
                incomes::insert(tx, &scope, x, &meta)?;
            }
            repo::insert_period(
                tx,
                &scope,
                &PeriodRow {
                    id: period_id.clone(),
                    partnership_id: l.row.id.clone(),
                    period_no: no,
                    start_on: start_s.clone(),
                    end_on: end_s.clone(),
                    currency: cur.clone(),
                    result_minor: s.result,
                    loss_policy: policy.clone(),
                    signed_version: l.version,
                    result_json: json.clone(),
                    chain_head: head,
                    closed_at: meta.now.clone(),
                },
                &meta,
            )
        })?;
        self.publish(
            Some(space_id),
            &[Topic::Ventures, Topic::Journal, Topic::Incomes],
        );
        self.venture_ledger(space_id, partnership_id)
    }

    /// Sherik uchun davr hisoboti PDF'i: kirim, xarajat, natija, taqsimot, buyout, zanjir boshi.
    pub fn venture_period_pdf(
        &self,
        space_id: &str,
        partnership_id: &str,
        period_id: &str,
    ) -> Result<Vec<u8>, AppError> {
        let ctx = self.ctx()?;
        let scope = self.scope(&ctx, space_id)?;
        let l = self.venture_book(&scope, partnership_id)?;
        let (p, s) = l
            .periods
            .iter()
            .find(|(p, _)| p.id == period_id)
            .ok_or(AppError::on("NOT_FOUND", "periodId"))?;
        let f = |v: i64| format(Money::new(v, l.cur), ctx.locale);
        let signed = |v: i64| {
            let t = f(v.abs());
            match v.signum() {
                1 => format!("+{t}"),
                -1 => format!("−{t}"),
                _ => t,
            }
        };
        let mut totals = vec![
            ("vtotal.income", f(s.income)),
            ("vtotal.expense", f(s.expense)),
        ];
        if s.force_majeure != 0 {
            totals.push(("vtotal.forceMajeure", f(s.force_majeure)));
        }
        if s.corrections != 0 {
            totals.push(("vtotal.corrections", signed(s.corrections)));
        }
        totals.push(("vtotal.result", signed(s.result)));
        let recovered: i64 = s.parties.iter().map(|x| x.recovered).sum();
        if recovered != 0 {
            totals.push(("vtotal.recovered", f(recovered)));
        }
        if s.result >= 0 {
            totals.push(("vtotal.distributable", f(s.distributable)));
        }
        let entries = l
            .entries
            .iter()
            .filter(|e| p.start_on <= e.occurred_on && e.occurred_on <= p.end_on)
            .map(|e| {
                Ok(ReportEntry {
                    date: show(&e.occurred_on),
                    kind: e.kind.clone(),
                    category: e.category.clone(),
                    note: e.note.clone().unwrap_or_default(),
                    amount: signed(effect(e)?),
                    attachments: u32_of(
                        l.attachments.iter().filter(|a| a.entry_id == e.id).count(),
                    )?,
                })
            })
            .collect::<Result<Vec<_>, AppError>>()?;
        let buyout = match (&s.buyout, &l.terms.buyout, l.terms.buyout(l.cur)?) {
            (Some(b), Some(t), Some(Ok(sch))) => {
                let paid_so_far: usize = l
                    .periods
                    .iter()
                    .take_while(|(x, _)| x.period_no <= p.period_no)
                    .filter_map(|(_, x)| x.buyout.as_ref())
                    .map(|x| x.paid.len())
                    .sum();
                let list = |v: &[u32]| {
                    if v.is_empty() {
                        "—".to_string()
                    } else {
                        v.iter().map(u32::to_string).collect::<Vec<_>>().join(", ")
                    }
                };
                Some(ReportBuyout {
                    seller: l.terms.party_name(&t.seller_party_id),
                    buyer: l.terms.party_name(&t.buyer_party_id),
                    paid: list(&b.paid),
                    unpaid: list(&b.unpaid),
                    amount: f(b.amount),
                    progress: format!("{paid_so_far} / {}", sch.rows.len()),
                })
            }
            _ => None,
        };
        let doc = VentureReport {
            ident: p.id.clone(),
            locale: pdf_locale(ctx.locale),
            title: l.row.title.clone(),
            kind: l.row.kind.clone(),
            period_no: u32::try_from(p.period_no).map_err(|_| corrupt())?,
            start: show(&p.start_on),
            end: show(&p.end_on),
            version: format!("v{}", p.signed_version),
            loss_policy: p.loss_policy.clone(),
            totals: totals
                .into_iter()
                .map(|(k, v)| (k.to_string(), v))
                .collect(),
            entries,
            parties: s
                .parties
                .iter()
                .map(|x| ReportParty {
                    name: x.name.clone(),
                    role: x.role.clone(),
                    share: signed(x.share),
                    recovered: f(x.recovered),
                    liability: f(x.liability),
                    payout: f(x.payout),
                    capital_after: f(x.capital_after),
                })
                .collect(),
            buyout,
            negligence: s
                .negligence
                .as_ref()
                .map(|n| format!("{}: {}", l.terms.party_name(&n.party_id), n.note)),
            chain_head: p.chain_head.clone(),
            chain_short_code: short_code(&p.chain_head),
        };
        let today = ymd_parse(&p.end_on)?;
        let rendered = doc
            .render(engine(), today)
            .map_err(|e| AppError::new(e.code))?;
        Ok(rendered.pdf)
    }

    // ---- «Hunardan ishga» ----

    pub fn skills(&self, space_id: &str) -> Result<Vec<SkillDto>, AppError> {
        let ctx = self.ctx()?;
        let scope = self.scope(&ctx, space_id)?;
        let members = self
            .db
            .read(|c| household::list_members(c, &ctx.household_id))?;
        Ok(self
            .db
            .read(|c| repo::skills(c, &scope))?
            .into_iter()
            .map(|k| SkillDto {
                member_name: k.member_id.as_ref().and_then(|m| {
                    members
                        .iter()
                        .find(|x| &x.id == m)
                        .map(|x| x.display_name.clone())
                }),
                id: k.id,
                member_id: k.member_id,
                title: k.title,
                note: k.note,
            })
            .collect())
    }

    pub fn add_skill(&self, space_id: &str, input: SkillInput) -> Result<Vec<SkillDto>, AppError> {
        let ctx = self.ctx()?;
        let scope = self.scope(&ctx, space_id)?;
        if let Some(m) = &input.member_id {
            let members = self
                .db
                .read(|c| household::list_members(c, &ctx.household_id))?;
            if !members.iter().any(|x| &x.id == m) {
                return Err(AppError::on("NOT_FOUND", "memberId"));
            }
        }
        let row = SkillRow {
            id: self.new_id(),
            member_id: input.member_id,
            title: required(&input.title, "title")?,
            note: clean_opt(input.note.as_deref()),
        };
        let meta = self.meta();
        self.db
            .write(|tx| repo::insert_skill(tx, &scope, &row, &meta))?;
        self.publish(Some(space_id), &[Topic::Ideas]);
        self.skills(space_id)
    }

    pub fn delete_skill(&self, space_id: &str, id: &str) -> Result<Vec<SkillDto>, AppError> {
        let ctx = self.ctx()?;
        let scope = self.scope(&ctx, space_id)?;
        let meta = self.meta();
        self.db
            .write(|tx| repo::delete_skill(tx, &scope, id, &meta))?;
        self.publish(Some(space_id), &[Topic::Ideas]);
        self.skills(space_id)
    }

    fn parse_idea(
        &self,
        scope: &SpaceScope,
        cur: Currency,
        input: &VentureIdeaInput,
    ) -> Result<(String, Vec<CapexJ>, Vec<ScenarioJ>), AppError> {
        let title = required(&input.title, "title")?;
        if let Some(sid) = &input.skill_id {
            if !self
                .db
                .read(|c| repo::skills(c, scope))?
                .iter()
                .any(|k| &k.id == sid)
            {
                return Err(AppError::on("NOT_FOUND", "skillId"));
            }
        }
        let capex = input
            .capex
            .iter()
            .map(|c| {
                Ok(CapexJ {
                    title: required(&c.title, "capex")?,
                    amount_minor: positive(&c.amount, cur, "capex")?.minor(),
                })
            })
            .collect::<Result<Vec<_>, AppError>>()?;
        let scenarios = input
            .scenarios
            .iter()
            .map(|s| {
                let non_negative = |v: &str| -> Result<i64, AppError> {
                    let m = amount_in(v, cur, "scenarios")?;
                    if m.is_negative() {
                        return Err(AppError::on("AMOUNT_NEGATIVE", "scenarios"));
                    }
                    Ok(m.minor())
                };
                Ok(ScenarioJ {
                    name: ScenarioName::parse(&s.name)
                        .ok_or(AppError::on("INVALID_SCENARIOS", "scenarios"))?
                        .as_str()
                        .into(),
                    income_minor: non_negative(&s.income)?,
                    expense_minor: non_negative(&s.expense)?,
                })
            })
            .collect::<Result<Vec<_>, AppError>>()?;
        Ok((title, capex, scenarios))
    }

    fn compute_idea(
        cur: Currency,
        capex: &[CapexJ],
        scenarios: &[ScenarioJ],
        worker_share_bp: Option<i64>,
    ) -> Result<baraka_domain_uy::venture::IdeaResult, AppError> {
        Ok(venture_idea(&IdeaInput {
            currency: cur,
            capex: capex
                .iter()
                .map(|c| Money::new(c.amount_minor, cur))
                .collect(),
            scenarios: scenarios
                .iter()
                .map(|s| {
                    Ok(IdeaScenario {
                        name: ScenarioName::parse(&s.name).ok_or_else(corrupt)?,
                        income: Money::new(s.income_minor, cur),
                        expense: Money::new(s.expense_minor, cur),
                    })
                })
                .collect::<Result<Vec<_>, AppError>>()?,
            worker_share_bp,
        })?)
    }

    fn idea_dto(
        &self,
        ctx: &Ctx,
        scope: &SpaceScope,
        row: &IdeaRow,
    ) -> Result<VentureIdeaDto, AppError> {
        let cur = Currency::from_code(&row.currency)?;
        let capex: Vec<CapexJ> = serde_json::from_str(&row.capex_json).map_err(|_| corrupt())?;
        let scenarios: Vec<ScenarioJ> =
            serde_json::from_str(&row.scenarios_json).map_err(|_| corrupt())?;
        let r = Self::compute_idea(cur, &capex, &scenarios, row.worker_share_bp)?;
        let m = |v: Money| self.money_dto(ctx, v);
        let months = |v: Option<i64>| v.map(|x| u32::try_from(x).unwrap_or(u32::MAX));
        let skill_title = match &row.skill_id {
            Some(s) => self
                .db
                .read(|c| repo::skills(c, scope))?
                .into_iter()
                .find(|k| &k.id == s)
                .map(|k| k.title),
            None => None,
        };
        Ok(VentureIdeaDto {
            id: row.id.clone(),
            title: row.title.clone(),
            skill_id: row.skill_id.clone(),
            skill_title,
            capex_lines: capex
                .iter()
                .map(|c| CapexLineDto {
                    title: c.title.clone(),
                    amount: m(Money::new(c.amount_minor, cur)),
                })
                .collect(),
            capex: m(r.capex),
            scenarios: r
                .scenarios
                .iter()
                .map(|x| {
                    let src = scenarios.iter().find(|s| s.name == x.name.as_str());
                    IdeaScenarioDto {
                        name: x.name.as_str().into(),
                        income: m(Money::new(src.map_or(0, |s| s.income_minor), cur)),
                        expense: m(Money::new(src.map_or(0, |s| s.expense_minor), cur)),
                        net: m(x.net),
                        annual_net: m(x.annual_net),
                        payback_months: months(x.payback_months),
                        worker_monthly: x.worker_monthly.map(m),
                        investor_monthly: x.investor_monthly.map(m),
                        investor_payback_months: months(x.investor_payback_months),
                    }
                })
                .collect(),
            worker_share_bp: row
                .worker_share_bp
                .map(|b| i32::try_from(b).unwrap_or(i32::MAX)),
            warnings: r.warnings.iter().map(|w| (*w).to_string()).collect(),
            partnership_id: row.partnership_id.clone(),
        })
    }

    pub fn venture_ideas(&self, space_id: &str) -> Result<Vec<VentureIdeaDto>, AppError> {
        let ctx = self.ctx()?;
        let scope = self.scope(&ctx, space_id)?;
        self.db
            .read(|c| repo::ideas(c, &scope))?
            .iter()
            .map(|r| self.idea_dto(&ctx, &scope, r))
            .collect()
    }

    fn save_idea(
        &self,
        space_id: &str,
        id: Option<&str>,
        input: VentureIdeaInput,
    ) -> Result<VentureIdeaDto, AppError> {
        let ctx = self.ctx()?;
        let scope = self.scope(&ctx, space_id)?;
        let (title, capex, scenarios) = self.parse_idea(&scope, ctx.currency, &input)?;
        let share = input.worker_share_bp.map(i64::from);
        // Hisob to'g'ri bo'lmasa (3 stsenariy yo'q, ulush noto'g'ri) — saqlanmaydi.
        Self::compute_idea(ctx.currency, &capex, &scenarios, share)?;
        let old = match id {
            Some(i) => Some(
                self.db
                    .read(|c| repo::get_idea(c, &scope, i))?
                    .ok_or(AppError::on("NOT_FOUND", "ideaId"))?,
            ),
            None => None,
        };
        let row = IdeaRow {
            id: old.as_ref().map_or_else(|| self.new_id(), |o| o.id.clone()),
            skill_id: input.skill_id,
            title,
            currency: old
                .as_ref()
                .map_or_else(|| ctx.currency.code().to_string(), |o| o.currency.clone()),
            capex_json: serde_json::to_string(&capex).map_err(|_| corrupt())?,
            scenarios_json: serde_json::to_string(&scenarios).map_err(|_| corrupt())?,
            worker_share_bp: share,
            partnership_id: old.as_ref().and_then(|o| o.partnership_id.clone()),
        };
        let meta = self.meta();
        self.db.write(|tx| {
            if old.is_some() {
                repo::update_idea(tx, &scope, &row, &meta)
            } else {
                repo::insert_idea(tx, &scope, &row, &meta)
            }
        })?;
        self.publish(Some(space_id), &[Topic::Ideas]);
        self.idea_dto(&ctx, &scope, &row)
    }

    pub fn create_venture_idea(
        &self,
        space_id: &str,
        input: VentureIdeaInput,
    ) -> Result<VentureIdeaDto, AppError> {
        self.save_idea(space_id, None, input)
    }

    pub fn update_venture_idea(
        &self,
        space_id: &str,
        id: &str,
        input: VentureIdeaInput,
    ) -> Result<VentureIdeaDto, AppError> {
        self.save_idea(space_id, Some(id), input)
    }

    pub fn delete_venture_idea(&self, space_id: &str, id: &str) -> Result<(), AppError> {
        let ctx = self.ctx()?;
        let scope = self.scope(&ctx, space_id)?;
        let meta = self.meta();
        self.db
            .write(|tx| repo::delete_idea(tx, &scope, id, &meta))?;
        self.publish(Some(space_id), &[Topic::Ideas]);
        Ok(())
    }

    /// G'oyadan bir bosishda mudoraba shartnomasi qoralamasi: CAPEX — kapital egasining pul
    /// hissasi, «biz» — mehnat egasi, ulushlar g'oyadagidek (standart 50/50).
    pub fn draft_partnership_from_idea(
        &self,
        space_id: &str,
        idea_id: &str,
        input: IdeaDraftInput,
    ) -> Result<PartnershipDto, AppError> {
        let ctx = self.ctx()?;
        let scope = self.scope(&ctx, space_id)?;
        let mut idea = self
            .db
            .read(|c| repo::get_idea(c, &scope, idea_id))?
            .ok_or(AppError::on("NOT_FOUND", "ideaId"))?;
        if idea.partnership_id.is_some() {
            return Err(AppError::on("ALREADY_DRAFTED", "ideaId"));
        }
        let cur = Currency::from_code(&idea.currency)?;
        let capex: Vec<CapexJ> = serde_json::from_str(&idea.capex_json).map_err(|_| corrupt())?;
        let worker = idea.worker_share_bp.unwrap_or(5000);
        let worker_bp = i32::try_from(worker).map_err(|_| corrupt())?;
        let dto = self.create_partnership(
            space_id,
            PartnershipInput {
                kind: PartnershipKind::Mudaraba.as_str().into(),
                title: idea.title.clone(),
                parties: vec![
                    PartnerInput {
                        id: "P1".into(),
                        full_name: clean(&input.capital_provider_name),
                        role: PartnerRole::CapitalProvider.as_str().into(),
                        profit_share_bp: 10_000 - worker_bp,
                        is_me: false,
                        capital: capex
                            .iter()
                            .map(|c| CapitalItemInput {
                                kind: "MONEY".into(),
                                description: c.title.clone(),
                                amount: format_plain(c.amount_minor, cur),
                            })
                            .collect(),
                    },
                    PartnerInput {
                        id: "P2".into(),
                        full_name: clean(&input.my_name),
                        role: PartnerRole::Worker.as_str().into(),
                        profit_share_bp: worker_bp,
                        is_me: true,
                        capital: Vec::new(),
                    },
                ],
                fixed_return: None,
                duties: baraka_agreements::Answer::Unanswered,
                negligence_clause: None,
                custody: baraka_agreements::Answer::Unanswered,
                exit_clause: baraka_agreements::Answer::Unanswered,
                arbiter: baraka_agreements::Answer::Unanswered,
                term: baraka_agreements::Answer::Unanswered,
                witnesses: Vec::new(),
                buyout: None,
            },
        )?;
        idea.partnership_id = Some(dto.id.clone());
        let meta = self.meta();
        self.db
            .write(|tx| repo::update_idea(tx, &scope, &idea, &meta))?;
        self.publish(Some(space_id), &[Topic::Ideas, Topic::Partnerships]);
        Ok(dto)
    }

    // ---- «Kafolatlangan foyda» detektori ----

    /// Taklifni tekshirish (2E.5): sof funksiya, hech narsa saqlanmaydi.
    pub fn check_offer(&self, input: OfferAnswersInput) -> Result<OfferCheckDto, AppError> {
        let q = |v: &str, field: &str| {
            Reply::parse(v).ok_or_else(|| AppError::on("INVALID_ANSWER", field))
        };
        let r = offer_check(&OfferAnswers {
            guaranteed: q(&input.guaranteed, "guaranteed")?,
            loss_shared: q(&input.loss_shared, "lossShared")?,
            real_activity: q(&input.real_activity, "realActivity")?,
            recruitment: q(&input.recruitment, "recruitment")?,
            urgency: q(&input.urgency, "urgency")?,
            written: q(&input.written, "written")?,
        });
        Ok(OfferCheckDto {
            verdict: r.verdict.as_str().into(),
            flags: r
                .flags
                .iter()
                .map(|f| OfferFlagDto {
                    code: f.code.into(),
                    level: f.level.as_str().into(),
                })
                .collect(),
        })
    }
}
