//! 6-qonun ijrosi (U13, uy/SPEC 2F.3–2F.10): vazifa hodisalari, ochiq hisob ko'rigi va
//! bayonnoma, «katta foyda»da 4–5-bandlarni qayta o'qish, nizo va hakam qarori, hakam uchun ish
//! papkasi, yillik yangilash, oilaviy kelishuvlar va kelishuvlar markazi.
//!
//! * Hodisa va ko'rikdagi har bir tomon belgisi kelishuv jurnaliga yoziladi (`DUTY_INCIDENT`,
//!   `REVIEW_ACK`). Bayonnomada o'sha paytdagi zanjir boshi saqlanadi; keyin o'tmishdagi yozuv
//!   o'zgartirilsa, `review::check_protocol` buni aniqlaydi (vektorlar `review_protocol`).
//! * Ochiq nizo (hakam qarori yo'q) — kelishuv `IN_DISPUTE`, davrni yopish va taqsimot bloklanadi.
//! * Eslatmalar saqlangan sanalardan hisoblanadi: ilova qayta ochilganda ham yo'qolmaydi.
use std::collections::BTreeSet;

use baraka_agreements::Answer;
use baraka_domain_uy::review::{
    check_protocol, next_review_due, reminder, renewed_review_date, ProtocolStatus, Reminder,
    RENEWAL_LEAD_DAYS, REVIEW_LEAD_DAYS,
};
use baraka_journal::{short_code, EntryKind, JournalEntry};
use baraka_money::{format, format_percent_bp, Currency, Money};
use baraka_pdf::{
    AckLine, ArbiterFolder, FolderClaim, FolderDecision, FolderPeriod, FolderReview, FolderVersion,
    IncidentLine, ReportEntry, ReviewProtocol,
};
use baraka_storage::repo::governance::{
    self as repo, AckRow, ClaimRow, DecisionRow, DisputeRow, FamilySignoffRow, IncidentRow,
    RereadRow, ReviewRow,
};
use baraka_storage::repo::partnerships::{self as prepo, PartnershipRow};
use baraka_storage::repo::ventures::EntryRow;
use baraka_storage::repo::{agreements, journal};
use baraka_storage::SpaceScope;
use chrono::{Days, NaiveDate};
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};

use crate::app::Ctx;
use crate::events::Topic;
use crate::partnership::{engine, Payload, View};
use crate::receipt::{date, pdf_locale, ymd};
use crate::text::{clean, clean_opt, required};
use crate::venture::{effect, show, Ledger};
use crate::*;

const ACTIVE: &str = "ACTIVE";
const DRAFT: &str = "DRAFT";
const IN_DISPUTE: &str = "IN_DISPUTE";
const FAMILY: &str = "FAMILY";
const PARTNERSHIP: &str = "PARTNERSHIP";
const REASONS: [&str; 3] = ["SCHEDULED", "PROFIT_SPIKE", "EXTRA"];
const VERDICTS: [&str; 2] = ["AGREE", "OBJECT"];
const OUTCOMES: [&str; 2] = ["RESUME", "AMEND"];
/// `REMITTANCE` — Musofir «Ikki qirg'oq» kelishuvi (M2, OQ-MF7).
const FAMILY_TEMPLATES: [&str; 6] = [
    "CHORES",
    "MONEY_PLACE",
    "WANT_LIMIT",
    "COUNCIL",
    "OTHER",
    "REMITTANCE",
];
const MAX_FAMILY_ITEMS: usize = 20;
const MAX_TEXT: usize = 500;
/// Versiya izohlari (PDF'da `vnote.*` kalitlari bilan ko'rsatiladi).
const RENEWED_UNCHANGED: &str = "RENEWED_UNCHANGED";
const ARBITER_AMEND: &str = "ARBITER_AMEND";

fn corrupt() -> AppError {
    AppError::new("CORRUPT_ROW")
}

fn overflow() -> AppError {
    AppError::new("OVERFLOW")
}

fn u32_of(n: usize) -> Result<u32, AppError> {
    u32::try_from(n).map_err(|_| overflow())
}

fn ymd_parse(s: &str) -> Result<NaiveDate, AppError> {
    NaiveDate::parse_from_str(s, "%Y-%m-%d").map_err(|_| corrupt())
}

fn hex(bytes: &[u8]) -> String {
    bytes.iter().map(|b| format!("{b:02x}")).collect()
}

/// Uzun erkin matn: kesilgan, bo'sh emas, chegaradan oshmaydi.
fn text(s: &str, field: &str) -> Result<String, AppError> {
    let t = required(s, field)?;
    if t.chars().count() > MAX_TEXT {
        return Err(AppError::on("TOO_LONG", field));
    }
    Ok(t)
}

fn text_opt(s: Option<&str>, field: &str) -> Result<Option<String>, AppError> {
    match clean_opt(s) {
        Some(t) if t.chars().count() > MAX_TEXT => Err(AppError::on("TOO_LONG", field)),
        other => Ok(other),
    }
}

fn reminder_parts(r: Reminder) -> (&'static str, i32) {
    let days = match r {
        Reminder::Upcoming { days } | Reminder::Overdue { days } => days,
        Reminder::Due => 0,
    };
    (r.as_str(), i32::try_from(days).unwrap_or(i32::MAX))
}

// ---- bayonnomaning saqlanadigan yakuni (`account_reviews.summary_json`) ----

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
struct Summary {
    currency: String,
    version: i64,
    entries: u32,
    periods_closed: u32,
    income: i64,
    expense: i64,
    force_majeure: i64,
    corrections: i64,
    result: i64,
    chain_ok: bool,
    open_incident_ids: Vec<String>,
}

// ---- oilaviy kelishuv matni (`agreements.payload_json`) ----

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
struct FamilyP {
    template_key: String,
    title: String,
    items: Vec<String>,
    review_date: Option<String>,
}

impl FamilyP {
    fn hash(&self) -> Result<String, AppError> {
        let bytes = serde_json::to_vec(self).map_err(|_| corrupt())?;
        Ok(hex(&Sha256::digest(&bytes)))
    }
}

/// Ko'rik va yangilash jadvali (saqlangan sanalardan).
struct Schedule {
    every_days: u32,
    next_due: Option<NaiveDate>,
    review: Option<ReminderDto>,
    review_date: Option<String>,
    renewal: Option<ReminderDto>,
}

/// Bitta sheriklikning 6-qonun yozuvlari.
struct Records {
    incidents: Vec<IncidentRow>,
    reviews: Vec<ReviewRow>,
    acks: Vec<AckRow>,
    disputes: Vec<(DisputeRow, Vec<ClaimRow>, Option<DecisionRow>)>,
    journal: Vec<JournalEntry>,
    hashes: Vec<String>,
    /// Jurnal yozuvi id → tartib raqami (1 dan).
    seqs: std::collections::BTreeMap<String, usize>,
}

/// Ko'rik qamraydigan raqamlar (bir xil qoida — qoralama, bayonnoma va PDF uchun).
struct Totals {
    entries: u32,
    periods_closed: u32,
    income: i64,
    expense: i64,
    force_majeure: i64,
    corrections: i64,
    result: i64,
}

fn totals(l: &Ledger, from: &str, to: &str) -> Result<Totals, AppError> {
    let (mut inc, mut exp, mut fm, mut corr, mut n) = (0_i64, 0_i64, 0_i64, 0_i64, 0_usize);
    for e in l
        .entries
        .iter()
        .filter(|e| from <= e.occurred_on.as_str() && e.occurred_on.as_str() <= to)
    {
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
    let periods = l
        .periods
        .iter()
        .filter(|(p, _)| from <= p.end_on.as_str() && p.end_on.as_str() <= to)
        .count();
    Ok(Totals {
        entries: u32_of(n)?,
        periods_closed: u32_of(periods)?,
        income: inc,
        expense: exp,
        force_majeure: fm,
        corrections: corr,
        result,
    })
}

impl App {
    /// Ochiq nizo (hakam qarori hali yozilmagan).
    pub(crate) fn open_dispute(
        &self,
        scope: &SpaceScope,
        partnership_id: &str,
    ) -> Result<Option<DisputeRow>, AppError> {
        for d in self.db.read(|c| repo::disputes(c, scope, partnership_id))? {
            if self.db.read(|c| repo::decision(c, scope, &d.id))?.is_none() {
                return Ok(Some(d));
            }
        }
        Ok(None)
    }

    /// Yangi versiya izohi: faqat `reviewDate` o'zgargan bo'lsa — «o'zgarishsiz yangilandi»
    /// (2F.3), hakamning `AMEND` qaroridan keyingi birinchi versiya — «hakam qarori bo'yicha».
    pub(crate) fn version_note(
        &self,
        scope: &SpaceScope,
        v: &View,
    ) -> Result<Option<String>, AppError> {
        let Some(prev) = v.versions.last() else {
            return Ok(None);
        };
        let old: Payload = serde_json::from_str(&prev.payload_json).map_err(|_| corrupt())?;
        let mut same = old.clone();
        if let (Answer::Answered { value: t }, Some(new)) = (&mut same.term, v.payload.term.value())
        {
            t.review_date.clone_from(&new.review_date);
        }
        if same == v.payload && old.term != v.payload.term {
            return Ok(Some(RENEWED_UNCHANGED.into()));
        }
        let since = prev.created_at.get(..10).unwrap_or_default();
        for d in self.db.read(|c| repo::disputes(c, scope, &v.row.id))? {
            if let Some(x) = self.db.read(|c| repo::decision(c, scope, &d.id))? {
                if x.outcome == "AMEND" && x.decided_on.as_str() >= since {
                    return Ok(Some(ARBITER_AMEND.into()));
                }
            }
        }
        Ok(None)
    }

    fn records(&self, scope: &SpaceScope, l: &Ledger) -> Result<Records, AppError> {
        let id = l.row.id.as_str();
        let incidents = self.db.read(|c| repo::incidents(c, scope, id))?;
        let reviews = self.db.read(|c| repo::reviews(c, scope, id))?;
        let acks = self.db.read(|c| repo::acks(c, scope, id))?;
        let mut disputes = Vec::new();
        for d in self.db.read(|c| repo::disputes(c, scope, id))? {
            let claims = self.db.read(|c| repo::claims(c, scope, &d.id))?;
            let decision = self.db.read(|c| repo::decision(c, scope, &d.id))?;
            disputes.push((d, claims, decision));
        }
        let stored = self
            .db
            .read(|c| journal::list(c, scope, &l.row.agreement_id))?;
        let seqs = stored
            .iter()
            .enumerate()
            .map(|(i, s)| (s.entry.id.clone(), i + 1))
            .collect();
        let hashes = stored.iter().map(|s| s.hash.clone()).collect();
        let journal = stored.into_iter().map(|s| s.entry).collect();
        Ok(Records {
            incidents,
            reviews,
            acks,
            disputes,
            journal,
            hashes,
            seqs,
        })
    }

    fn party_refs(l: &Ledger) -> Vec<PartyRefDto> {
        l.terms
            .parties
            .iter()
            .map(|p| PartyRefDto {
                party_id: p.id.clone(),
                name: p.full_name.clone(),
            })
            .collect()
    }

    fn duties(l: &Ledger) -> Vec<DutyDto> {
        l.terms
            .duties
            .value()
            .map(|list| {
                list.iter()
                    .map(|d| DutyDto {
                        id: d.id.clone(),
                        title: d.title.clone(),
                        owner_party_id: d.owner_party_id.clone(),
                        owner_name: d.owner_party_id.as_deref().map(|p| l.terms.party_name(p)),
                        breach_clause: d.breach_clause.clone(),
                    })
                    .collect()
            })
            .unwrap_or_default()
    }

    fn incident_dto(l: &Ledger, i: &IncidentRow) -> IncidentDto {
        let duty = l
            .terms
            .duties
            .value()
            .and_then(|list| list.iter().find(|d| d.id == i.duty_id));
        IncidentDto {
            id: i.id.clone(),
            duty_id: i.duty_id.clone(),
            duty_title: duty.map_or_else(|| i.duty_id.clone(), |d| d.title.clone()),
            breach_clause: duty.and_then(|d| d.breach_clause.clone()),
            party_id: i.party_id.clone(),
            party_name: l.terms.party_name(&i.party_id),
            reason: i.reason.clone(),
            occurred_on: i.occurred_on.clone(),
            proposed_solution: i.proposed_solution.clone(),
            resolved_on: i.resolved_on.clone(),
            resolution_note: i.resolution_note.clone(),
            chain_code: l
                .hashes
                .get(&i.journal_entry_id)
                .map(|h| short_code(h))
                .unwrap_or_default(),
        }
    }

    fn review_totals_dto(&self, ctx: &Ctx, cur: Currency, t: &Totals) -> ReviewTotalsDto {
        let m = |v: i64| self.money_dto(ctx, Money::new(v, cur));
        ReviewTotalsDto {
            entries: t.entries,
            periods_closed: t.periods_closed,
            income: m(t.income),
            expense: m(t.expense),
            force_majeure: m(t.force_majeure),
            corrections: m(t.corrections),
            result: m(t.result),
        }
    }

    /// Bayonnoma joriy jurnal bilan solishtiriladi (6.5 bloki).
    fn integrity(rec: &Records, r: &ReviewRow) -> Result<(ProtocolStatus, u32), AppError> {
        let seq = usize::try_from(r.chain_seq).map_err(|_| corrupt())?;
        let check = check_protocol(&rec.journal, &rec.hashes, seq, &r.chain_head)?;
        // Bayonnomaning o'z belgilari (REVIEW_ACK) «keyin qo'shilgan» hisoblanmaydi.
        let own = rec.acks.iter().filter(|a| a.review_id == r.id).count();
        Ok((
            check.status,
            u32_of(check.entries_after.saturating_sub(own))?,
        ))
    }

    fn review_dto(
        &self,
        ctx: &Ctx,
        l: &Ledger,
        rec: &Records,
        r: &ReviewRow,
    ) -> Result<ReviewDto, AppError> {
        let s: Summary = serde_json::from_str(&r.summary_json).map_err(|_| corrupt())?;
        let (status, after) = Self::integrity(rec, r)?;
        let cur = Currency::from_code(&s.currency)?;
        Ok(ReviewDto {
            id: r.id.clone(),
            no: u32::try_from(r.review_no).map_err(|_| corrupt())?,
            from_on: r.from_on.clone(),
            to_on: r.to_on.clone(),
            reason: r.reason.clone(),
            held_on: r.held_on.clone(),
            totals: self.review_totals_dto(ctx, cur, &Self::summary_totals(&s)),
            open_incidents: u32_of(s.open_incident_ids.len())?,
            acks: rec
                .acks
                .iter()
                .filter(|a| a.review_id == r.id)
                .map(|a| ReviewAckDto {
                    party_id: a.party_id.clone(),
                    party_name: l.terms.party_name(&a.party_id),
                    verdict: a.verdict.clone(),
                    note: a.note.clone(),
                })
                .collect(),
            chain_code: short_code(&r.chain_head),
            integrity: status.as_str().into(),
            entries_after: after,
        })
    }

    fn summary_totals(s: &Summary) -> Totals {
        Totals {
            entries: s.entries,
            periods_closed: s.periods_closed,
            income: s.income,
            expense: s.expense,
            force_majeure: s.force_majeure,
            corrections: s.corrections,
            result: s.result,
        }
    }

    fn dispute_dto(
        l: &Ledger,
        d: &DisputeRow,
        claims: &[ClaimRow],
        decision: Option<&DecisionRow>,
    ) -> Result<DisputeDto, AppError> {
        Ok(DisputeDto {
            id: d.id.clone(),
            opened_on: d.opened_on.clone(),
            opened_by: d.opened_by_party.clone(),
            opened_by_name: l.terms.party_name(&d.opened_by_party),
            subject: d.subject.clone(),
            clauses: serde_json::from_str(&d.clauses_json).map_err(|_| corrupt())?,
            claims: claims
                .iter()
                .map(|c| ClaimDto {
                    party_id: c.party_id.clone(),
                    party_name: l.terms.party_name(&c.party_id),
                    claim: c.claim.clone(),
                })
                .collect(),
            decision: decision.map(|x| DecisionDto {
                decided_on: x.decided_on.clone(),
                arbiter_name: x.arbiter_name.clone(),
                decision: x.decision.clone(),
                outcome: x.outcome.clone(),
            }),
            open: decision.is_none(),
        })
    }

    fn schedule(&self, ctx: &Ctx, l: &Ledger, reviews: &[ReviewRow]) -> Result<Schedule, AppError> {
        let today = self.today(ctx);
        let every_days = l.terms.custody.value().map_or(0, |c| c.review_every_days);
        let every_days = if every_days == 0 {
            baraka_domain_uy::review::DEFAULT_REVIEW_EVERY_DAYS
        } else {
            every_days
        };
        let reminder_dto = |kind: &str, due: NaiveDate, r: Reminder| {
            let (state, days) = reminder_parts(r);
            ReminderDto {
                agreement_id: l.row.agreement_id.clone(),
                ref_id: l.row.id.clone(),
                agreement_type: PARTNERSHIP.into(),
                kind: kind.into(),
                title: l.row.title.clone(),
                due_on: ymd(due),
                state: state.into(),
                days,
            }
        };
        let active = l.row.status == ACTIVE;
        let anchor = match reviews.last() {
            Some(r) => ymd_parse(&r.held_on)?,
            None => l.start,
        };
        let next_due = if active {
            next_review_due(anchor, every_days)
        } else {
            None
        };
        let review = next_due.and_then(|due| {
            reminder(today, due, REVIEW_LEAD_DAYS).map(|r| reminder_dto("REVIEW", due, r))
        });
        let review_date = l.terms.term.value().map(|t| t.review_date.clone());
        let renewal = match (&review_date, active) {
            (Some(d), true) => {
                let due = ymd_parse(d)?;
                reminder(today, due, RENEWAL_LEAD_DAYS).map(|r| reminder_dto("RENEWAL", due, r))
            }
            _ => None,
        };
        Ok(Schedule {
            every_days,
            next_due,
            review,
            review_date,
            renewal,
        })
    }

    fn governance_dto(
        &self,
        ctx: &Ctx,
        scope: &SpaceScope,
        l: &Ledger,
    ) -> Result<GovernanceDto, AppError> {
        let rec = self.records(scope, l)?;
        let sch = self.schedule(ctx, l, &rec.reviews)?;
        let mut reviews = rec
            .reviews
            .iter()
            .map(|r| self.review_dto(ctx, l, &rec, r))
            .collect::<Result<Vec<_>, AppError>>()?;
        reviews.reverse();
        let mut incidents: Vec<IncidentDto> = rec
            .incidents
            .iter()
            .map(|i| Self::incident_dto(l, i))
            .collect();
        incidents.reverse();
        let mut disputes = rec
            .disputes
            .iter()
            .map(|(d, c, x)| Self::dispute_dto(l, d, c, x.as_ref()))
            .collect::<Result<Vec<_>, AppError>>()?;
        disputes.reverse();
        Ok(GovernanceDto {
            partnership_id: l.row.id.clone(),
            title: l.row.title.clone(),
            status: l.row.status.clone(),
            in_dispute: l.in_dispute,
            writable: l.read_only.is_none(),
            read_only_reason: l.read_only.map(str::to_string),
            parties: Self::party_refs(l),
            duties: Self::duties(l),
            incidents,
            reviews,
            disputes,
            arbiter_name: l.terms.arbiter.value().map(|a| a.full_name.clone()),
            review_every_days: sch.every_days,
            next_review_due: sch.next_due.map(ymd),
            review_reminder: sch.review,
            review_date: sch.review_date,
            renewal_reminder: sch.renewal,
        })
    }

    fn keeper_writes(l: &Ledger) -> Result<(), AppError> {
        match l.read_only {
            Some(code) => Err(AppError::new(code)),
            None => Ok(()),
        }
    }

    fn known_party(l: &Ledger, id: &str, field: &str) -> Result<String, AppError> {
        let id = clean(id);
        if l.terms.parties.iter().any(|p| p.id == id) {
            Ok(id)
        } else {
            Err(AppError::on("UNKNOWN_PARTY", field))
        }
    }

    fn gov_reload(
        &self,
        ctx: &Ctx,
        scope: &SpaceScope,
        id: &str,
    ) -> Result<GovernanceDto, AppError> {
        let l = self.venture_book(scope, id)?;
        self.governance_dto(ctx, scope, &l)
    }

    // ---- ommaviy use-case'lar: sheriklik boshqaruvi ----

    pub fn governance(
        &self,
        space_id: &str,
        partnership_id: &str,
    ) -> Result<GovernanceDto, AppError> {
        let ctx = self.ctx()?;
        let scope = self.scope(&ctx, space_id)?;
        self.gov_reload(&ctx, &scope, partnership_id)
    }

    /// «Bajara olmayapman» (2F.4): hodisa jurnalga yoziladi, 3-banddagi «bajarilmasa» qoidasi
    /// javobda darhol ko'rsatiladi.
    pub fn report_duty_incident(
        &self,
        space_id: &str,
        partnership_id: &str,
        input: IncidentInput,
    ) -> Result<GovernanceDto, AppError> {
        let ctx = self.ctx()?;
        let scope = self.scope(&ctx, space_id)?;
        let l = self.venture_book(&scope, partnership_id)?;
        Self::keeper_writes(&l)?;
        let duty_id = clean(&input.duty_id);
        if !Self::duties(&l).iter().any(|d| d.id == duty_id) {
            return Err(AppError::on("UNKNOWN_DUTY", "dutyId"));
        }
        let party = Self::known_party(&l, &input.party_id, "partyId")?;
        let reason = text(&input.reason, "reason")?;
        let solution = text_opt(input.proposed_solution.as_deref(), "proposedSolution")?;
        let on = date(&input.occurred_on, "occurredOn")?;
        if on > self.today(&ctx) {
            return Err(AppError::on("FUTURE_DATE", "occurredOn"));
        }
        if on < l.start {
            return Err(AppError::on("BEFORE_START", "occurredOn"));
        }
        let je = JournalEntry {
            id: self.new_id(),
            agreement_id: l.row.agreement_id.clone(),
            kind: EntryKind::DutyIncident,
            party_id: Some(party.clone()),
            amount: None,
            date: ymd(on),
            note: Some(reason.clone()),
            corrects_entry_id: None,
            refs: vec![format!("duty:{duty_id}")],
        };
        je.validate()?;
        let row = IncidentRow {
            id: self.new_id(),
            partnership_id: l.row.id.clone(),
            duty_id,
            party_id: party,
            reason,
            occurred_on: ymd(on),
            proposed_solution: solution,
            journal_entry_id: je.id.clone(),
            resolved_on: None,
            resolution_note: None,
        };
        let meta = self.meta();
        self.db.write(|tx| {
            journal::append(tx, &scope, &je, &meta)?;
            repo::insert_incident(tx, &scope, &row, &meta)
        })?;
        self.publish(Some(space_id), &[Topic::Governance, Topic::Journal]);
        self.gov_reload(&ctx, &scope, partnership_id)
    }

    /// Hodisa yechimi — alohida o'zgarmas yozuv (hodisaning o'zi tahrirlanmaydi).
    pub fn resolve_duty_incident(
        &self,
        space_id: &str,
        partnership_id: &str,
        incident_id: &str,
        note: &str,
    ) -> Result<GovernanceDto, AppError> {
        let ctx = self.ctx()?;
        let scope = self.scope(&ctx, space_id)?;
        let l = self.venture_book(&scope, partnership_id)?;
        Self::keeper_writes(&l)?;
        let note = text(note, "note")?;
        let incidents = self
            .db
            .read(|c| repo::incidents(c, &scope, partnership_id))?;
        let i = incidents
            .iter()
            .find(|i| i.id == incident_id)
            .ok_or(AppError::on("NOT_FOUND", "incidentId"))?;
        if i.resolved_on.is_some() {
            return Err(AppError::new("ALREADY_RESOLVED"));
        }
        let today = ymd(self.today(&ctx));
        let meta = self.meta();
        self.db
            .write(|tx| repo::resolve_incident(tx, &scope, &i.id, &today, &note, &meta))?;
        self.publish(Some(space_id), &[Topic::Governance]);
        self.gov_reload(&ctx, &scope, partnership_id)
    }

    /// Ko'rik qamraydigan oraliq: oxirgi bayonnomadan keyingi kundan (yoki sheriklik boshidan).
    fn review_range(
        &self,
        ctx: &Ctx,
        l: &Ledger,
        reviews: &[ReviewRow],
        to_on: &str,
    ) -> Result<(NaiveDate, NaiveDate), AppError> {
        let from = match reviews.last() {
            Some(r) => ymd_parse(&r.to_on)?
                .checked_add_days(Days::new(1))
                .ok_or(AppError::new("INVALID_DATE"))?,
            None => l.start,
        };
        // Bo'sh sana — bugun (yadro soati bo'yicha; UI o'z soatiga tayanmaydi).
        let to = if to_on.trim().is_empty() {
            self.today(ctx)
        } else {
            date(to_on, "toOn")?
        };
        if to > self.today(ctx) {
            return Err(AppError::on("FUTURE_DATE", "toOn"));
        }
        if to < from {
            return Err(AppError::on("INVALID_REVIEW_RANGE", "toOn"));
        }
        Ok((from, to))
    }

    fn open_incidents_at<'a>(rec: &'a Records, to: &str) -> Vec<&'a IncidentRow> {
        rec.incidents
            .iter()
            .filter(|i| i.resolved_on.is_none() && i.occurred_on.as_str() <= to)
            .collect()
    }

    /// Ko'rik sessiyasi ekrani (hech narsa yozilmaydi).
    pub fn review_draft(
        &self,
        space_id: &str,
        partnership_id: &str,
        to_on: &str,
    ) -> Result<ReviewDraftDto, AppError> {
        let ctx = self.ctx()?;
        let scope = self.scope(&ctx, space_id)?;
        let l = self.venture_book(&scope, partnership_id)?;
        let rec = self.records(&scope, &l)?;
        let (from, to) = self.review_range(&ctx, &l, &rec.reviews, to_on)?;
        let (from_s, to_s) = (ymd(from), ymd(to));
        let t = totals(&l, &from_s, &to_s)?;
        let mut entries = l
            .entries
            .iter()
            .filter(|e| from_s <= e.occurred_on && e.occurred_on <= to_s)
            .map(|e| self.entry_dto(&ctx, &l, e))
            .collect::<Result<Vec<_>, AppError>>()?;
        entries.reverse();
        Ok(ReviewDraftDto {
            no: u32_of(rec.reviews.len() + 1)?,
            from_on: from_s,
            to_on: to_s.clone(),
            entries,
            totals: self.review_totals_dto(&ctx, l.cur, &t),
            open_incidents: Self::open_incidents_at(&rec, &to_s)
                .into_iter()
                .map(|i| Self::incident_dto(&l, i))
                .collect(),
            chain_ok: l.chain_ok,
            chain_code: short_code(&l.head),
            chain_entries: u32_of(rec.journal.len())?,
            parties: Self::party_refs(&l),
        })
    }

    /// Ochiq hisob ko'rigi (2F.5): har bir tomonning `AGREE` yoki `OBJECT + izoh` belgisi
    /// jurnalga yoziladi, bayonnomada o'sha paytdagi zanjir boshi qayd etiladi.
    pub fn hold_review(
        &self,
        space_id: &str,
        partnership_id: &str,
        input: HoldReviewInput,
    ) -> Result<GovernanceDto, AppError> {
        let ctx = self.ctx()?;
        let scope = self.scope(&ctx, space_id)?;
        let l = self.venture_book(&scope, partnership_id)?;
        Self::keeper_writes(&l)?;
        if !REASONS.contains(&input.reason.as_str()) {
            return Err(AppError::on("INVALID_REASON", "reason"));
        }
        let rec = self.records(&scope, &l)?;
        let (from, to) = self.review_range(&ctx, &l, &rec.reviews, &input.to_on)?;
        let (from_s, to_s) = (ymd(from), ymd(to));
        let mut seen = BTreeSet::new();
        let mut acks = Vec::new();
        for a in &input.acks {
            let party = Self::known_party(&l, &a.party_id, "acks")?;
            if !seen.insert(party.clone()) {
                return Err(AppError::on("DUPLICATE_ACK", "acks"));
            }
            if !VERDICTS.contains(&a.verdict.as_str()) {
                return Err(AppError::on("INVALID_VERDICT", "acks"));
            }
            let note = text_opt(a.note.as_deref(), "acks")?;
            if a.verdict == "OBJECT" && note.is_none() {
                return Err(AppError::on("OBJECTION_NOTE_REQUIRED", "acks"));
            }
            acks.push((party, a.verdict.clone(), note));
        }
        if l.terms.parties.iter().any(|p| !seen.contains(&p.id)) {
            return Err(AppError::on("ACKS_INCOMPLETE", "acks"));
        }
        let t = totals(&l, &from_s, &to_s)?;
        let open: Vec<String> = Self::open_incidents_at(&rec, &to_s)
            .into_iter()
            .map(|i| i.id.clone())
            .collect();
        let no = i64::try_from(rec.reviews.len() + 1).map_err(|_| overflow())?;
        let held = ymd(self.today(&ctx));
        let summary = Summary {
            currency: l.cur.code().to_string(),
            version: l.version,
            entries: t.entries,
            periods_closed: t.periods_closed,
            income: t.income,
            expense: t.expense,
            force_majeure: t.force_majeure,
            corrections: t.corrections,
            result: t.result,
            chain_ok: l.chain_ok,
            open_incident_ids: open,
        };
        let review = ReviewRow {
            id: self.new_id(),
            partnership_id: l.row.id.clone(),
            review_no: no,
            from_on: from_s,
            to_on: to_s,
            reason: input.reason.clone(),
            chain_seq: i64::try_from(rec.journal.len()).map_err(|_| overflow())?,
            chain_head: l.head.clone(),
            summary_json: serde_json::to_string(&summary).map_err(|_| corrupt())?,
            held_on: held.clone(),
        };
        let mut rows = Vec::new();
        for (party, verdict, note) in acks {
            let je = JournalEntry {
                id: self.new_id(),
                agreement_id: l.row.agreement_id.clone(),
                kind: EntryKind::ReviewAck,
                party_id: Some(party.clone()),
                amount: None,
                date: held.clone(),
                note: note.clone(),
                corrects_entry_id: None,
                refs: vec![
                    format!("review:{no}"),
                    format!("verdict:{verdict}"),
                    format!("head:{}", l.head),
                ],
            };
            je.validate()?;
            let ack = AckRow {
                id: self.new_id(),
                review_id: review.id.clone(),
                party_id: party,
                verdict,
                note,
                journal_entry_id: je.id.clone(),
            };
            rows.push((je, ack));
        }
        let meta = self.meta();
        self.db.write(|tx| {
            repo::insert_review(tx, &scope, &review, &meta)?;
            for (je, ack) in &rows {
                journal::append(tx, &scope, je, &meta)?;
                repo::insert_ack(tx, &scope, ack, &meta)?;
            }
            Ok(())
        })?;
        self.publish(Some(space_id), &[Topic::Governance, Topic::Journal]);
        self.gov_reload(&ctx, &scope, partnership_id)
    }

    fn report_entries(
        &self,
        ctx: &Ctx,
        l: &Ledger,
        list: &[&EntryRow],
    ) -> Result<Vec<ReportEntry>, AppError> {
        list.iter()
            .map(|e| {
                Ok(ReportEntry {
                    date: show(&e.occurred_on),
                    kind: e.kind.clone(),
                    category: e.category.clone(),
                    note: e.note.clone().unwrap_or_default(),
                    amount: signed(effect(e)?, l.cur, ctx),
                    attachments: u32_of(
                        l.attachments.iter().filter(|a| a.entry_id == e.id).count(),
                    )?,
                })
            })
            .collect()
    }

    fn report_totals(ctx: &Ctx, cur: Currency, t: &Totals) -> Vec<(String, String)> {
        let f = |v: i64| format(Money::new(v, cur), ctx.locale);
        let mut out = vec![
            ("vtotal.income".to_string(), f(t.income)),
            ("vtotal.expense".to_string(), f(t.expense)),
        ];
        if t.force_majeure != 0 {
            out.push(("vtotal.forceMajeure".into(), f(t.force_majeure)));
        }
        if t.corrections != 0 {
            out.push(("vtotal.corrections".into(), signed(t.corrections, cur, ctx)));
        }
        out.push(("vtotal.result".into(), signed(t.result, cur, ctx)));
        out.push(("vtotal.entries".into(), t.entries.to_string()));
        out.push(("vtotal.periods".into(), t.periods_closed.to_string()));
        out
    }

    /// Bayonnoma PDF'i: o'sha paytdagi yozuvlar, yakun, ochiq hodisalar, belgilar va zanjir boshi.
    pub fn review_pdf(
        &self,
        space_id: &str,
        partnership_id: &str,
        review_id: &str,
    ) -> Result<Vec<u8>, AppError> {
        let ctx = self.ctx()?;
        let scope = self.scope(&ctx, space_id)?;
        let l = self.venture_book(&scope, partnership_id)?;
        let rec = self.records(&scope, &l)?;
        let r = rec
            .reviews
            .iter()
            .find(|r| r.id == review_id)
            .ok_or(AppError::on("NOT_FOUND", "reviewId"))?;
        let s: Summary = serde_json::from_str(&r.summary_json).map_err(|_| corrupt())?;
        let cur = Currency::from_code(&s.currency)?;
        let seq = usize::try_from(r.chain_seq).map_err(|_| corrupt())?;
        // Bayonnoma paytida mavjud bo'lgan yozuvlargina (keyingi tuzatishlar kirmaydi).
        let list: Vec<&EntryRow> = l
            .entries
            .iter()
            .filter(|e| r.from_on <= e.occurred_on && e.occurred_on <= r.to_on)
            .filter(|e| rec.seqs.get(&e.journal_entry_id).is_some_and(|n| *n <= seq))
            .collect();
        let incidents = rec
            .incidents
            .iter()
            .filter(|i| s.open_incident_ids.contains(&i.id))
            .map(|i| Self::incident_line(&l, i, false))
            .collect();
        let doc = ReviewProtocol {
            ident: r.id.clone(),
            locale: pdf_locale(ctx.locale),
            title: l.row.title.clone(),
            review_no: u32::try_from(r.review_no).map_err(|_| corrupt())?,
            range: format!("{} — {}", show(&r.from_on), show(&r.to_on)),
            held_on: show(&r.held_on),
            reason: r.reason.clone(),
            version: format!("v{}", s.version),
            totals: Self::report_totals(&ctx, cur, &Self::summary_totals(&s)),
            entries: self.report_entries(&ctx, &l, &list)?,
            incidents,
            acks: rec
                .acks
                .iter()
                .filter(|a| a.review_id == r.id)
                .map(|a| AckLine {
                    party: l.terms.party_name(&a.party_id),
                    verdict: a.verdict.clone(),
                    note: a.note.clone().unwrap_or_default(),
                })
                .collect(),
            chain_ok: s.chain_ok,
            chain_head: r.chain_head.clone(),
            chain_short_code: short_code(&r.chain_head),
        };
        let rendered = doc
            .render(engine(), ymd_parse(&r.held_on)?)
            .map_err(|e| AppError::new(e.code))?;
        Ok(rendered.pdf)
    }

    fn incident_line(l: &Ledger, i: &IncidentRow, with_status: bool) -> IncidentLine {
        let d = Self::incident_dto(l, i);
        IncidentLine {
            date: show(&i.occurred_on),
            duty: d.duty_title,
            party: d.party_name,
            reason: i.reason.clone(),
            solution: i.proposed_solution.clone().unwrap_or_default(),
            status: if with_status && i.resolved_on.is_some() {
                "RESOLVED".into()
            } else {
                "OPEN".into()
            },
        }
    }

    /// «Katta foyda» (2F.7): tomon taqsimotdan oldin 4–5-bandlarni qayta o'qidi.
    pub fn acknowledge_spike_reread(
        &self,
        space_id: &str,
        partnership_id: &str,
        party_id: &str,
    ) -> Result<VentureLedgerDto, AppError> {
        let ctx = self.ctx()?;
        let scope = self.scope(&ctx, space_id)?;
        let l = self.venture_book(&scope, partnership_id)?;
        Self::keeper_writes(&l)?;
        let party = Self::known_party(&l, party_id, "partyId")?;
        if !l.next_rereads.contains(&party) {
            let row = RereadRow {
                id: self.new_id(),
                partnership_id: l.row.id.clone(),
                period_no: i64::try_from(l.periods.len() + 1).map_err(|_| overflow())?,
                party_id: party,
                acked_on: ymd(self.today(&ctx)),
            };
            let meta = self.meta();
            self.db
                .write(|tx| repo::insert_reread(tx, &scope, &row, &meta))?;
            self.publish(Some(space_id), &[Topic::Ventures]);
        }
        self.venture_ledger(space_id, partnership_id)
    }

    fn clauses(list: &[u8]) -> Result<Vec<u8>, AppError> {
        let set: BTreeSet<u8> = list.iter().copied().collect();
        if set.is_empty() || set.iter().any(|c| !(1..=9).contains(c)) {
            return Err(AppError::on("INVALID_CLAUSE", "clauses"));
        }
        Ok(set.into_iter().collect())
    }

    /// Nizo ochish (2F.8): kelishuv `IN_DISPUTE`, hakam qarorigacha taqsimot to'xtaydi.
    pub fn open_partnership_dispute(
        &self,
        space_id: &str,
        partnership_id: &str,
        input: OpenDisputeInput,
    ) -> Result<GovernanceDto, AppError> {
        let ctx = self.ctx()?;
        let scope = self.scope(&ctx, space_id)?;
        let l = self.venture_book(&scope, partnership_id)?;
        if l.row.status != ACTIVE {
            return Err(AppError::new("NOT_ACTIVE"));
        }
        if l.in_dispute {
            return Err(AppError::new("DISPUTE_ALREADY_OPEN"));
        }
        let subject = text(&input.subject, "subject")?;
        let clauses = Self::clauses(&input.clauses)?;
        let opened_by = Self::known_party(&l, &input.opened_by, "openedBy")?;
        let mut seen = BTreeSet::new();
        let mut claims = Vec::new();
        let dispute_id = self.new_id();
        for c in &input.claims {
            let party = Self::known_party(&l, &c.party_id, "claims")?;
            if !seen.insert(party.clone()) {
                return Err(AppError::on("DUPLICATE_CLAIM", "claims"));
            }
            claims.push((
                self.new_id(),
                ClaimRow {
                    dispute_id: dispute_id.clone(),
                    party_id: party,
                    claim: text(&c.claim, "claims")?,
                },
            ));
        }
        let row = DisputeRow {
            id: dispute_id,
            partnership_id: l.row.id.clone(),
            opened_on: ymd(self.today(&ctx)),
            opened_by_party: opened_by,
            subject,
            clauses_json: serde_json::to_string(&clauses).map_err(|_| corrupt())?,
        };
        let meta = self.meta();
        self.db.write(|tx| {
            repo::insert_dispute(tx, &scope, &row, &meta)?;
            for (id, c) in &claims {
                repo::insert_claim(tx, &scope, id, c, &meta)?;
            }
            agreements::set_status(tx, &scope, &l.row.agreement_id, IN_DISPUTE, &meta)
        })?;
        self.publish(
            Some(space_id),
            &[
                Topic::Governance,
                Topic::Partnerships,
                Topic::Agreements,
                Topic::Ventures,
            ],
        );
        self.gov_reload(&ctx, &scope, partnership_id)
    }

    fn dispute_of<'a>(
        rec: &'a Records,
        dispute_id: &str,
    ) -> Result<&'a (DisputeRow, Vec<ClaimRow>, Option<DecisionRow>), AppError> {
        rec.disputes
            .iter()
            .find(|(d, _, _)| d.id == dispute_id)
            .ok_or(AppError::on("NOT_FOUND", "disputeId"))
    }

    pub fn add_dispute_claim(
        &self,
        space_id: &str,
        partnership_id: &str,
        dispute_id: &str,
        input: DisputeClaimInput,
    ) -> Result<GovernanceDto, AppError> {
        let ctx = self.ctx()?;
        let scope = self.scope(&ctx, space_id)?;
        let l = self.venture_book(&scope, partnership_id)?;
        let rec = self.records(&scope, &l)?;
        let (d, claims, decision) = Self::dispute_of(&rec, dispute_id)?;
        if decision.is_some() {
            return Err(AppError::new("DISPUTE_DECIDED"));
        }
        let party = Self::known_party(&l, &input.party_id, "partyId")?;
        if claims.iter().any(|c| c.party_id == party) {
            return Err(AppError::on("DUPLICATE_CLAIM", "partyId"));
        }
        let claim = ClaimRow {
            dispute_id: d.id.clone(),
            party_id: party,
            claim: text(&input.claim, "claim")?,
        };
        let id = self.new_id();
        let meta = self.meta();
        self.db
            .write(|tx| repo::insert_claim(tx, &scope, &id, &claim, &meta))?;
        self.publish(Some(space_id), &[Topic::Governance]);
        self.gov_reload(&ctx, &scope, partnership_id)
    }

    /// Hakam qarori: nizo yopiladi, kelishuv yana `ACTIVE`. `AMEND` — shartnomaning yangi
    /// versiyasi kerak (foydalanuvchi matnni o'zgartirib, qayta imzolaydi).
    pub fn record_arbiter_decision(
        &self,
        space_id: &str,
        partnership_id: &str,
        dispute_id: &str,
        input: DecisionInput,
    ) -> Result<GovernanceDto, AppError> {
        let ctx = self.ctx()?;
        let scope = self.scope(&ctx, space_id)?;
        let l = self.venture_book(&scope, partnership_id)?;
        let rec = self.records(&scope, &l)?;
        let (d, _, decision) = Self::dispute_of(&rec, dispute_id)?;
        if decision.is_some() {
            return Err(AppError::new("DISPUTE_DECIDED"));
        }
        let arbiter = l
            .terms
            .arbiter
            .value()
            .map(|a| a.full_name.clone())
            .ok_or(AppError::new("ARBITER_REQUIRED"))?;
        if !OUTCOMES.contains(&input.outcome.as_str()) {
            return Err(AppError::on("INVALID_OUTCOME", "outcome"));
        }
        let on = date(&input.decided_on, "decidedOn")?;
        if on > self.today(&ctx) {
            return Err(AppError::on("FUTURE_DATE", "decidedOn"));
        }
        if ymd(on) < d.opened_on {
            return Err(AppError::on("BEFORE_DISPUTE", "decidedOn"));
        }
        let row = DecisionRow {
            dispute_id: d.id.clone(),
            decided_on: ymd(on),
            arbiter_name: arbiter,
            decision: text(&input.decision, "decision")?,
            outcome: input.outcome.clone(),
        };
        // Sheriklik yozuvi nizo davomida ham `ACTIVE`; kelishuv holati unga qaytadi.
        let status = l.row.status.as_str();
        let meta = self.meta();
        self.db.write(|tx| {
            repo::insert_decision(tx, &scope, &row, &meta)?;
            agreements::set_status(tx, &scope, &l.row.agreement_id, status, &meta)
        })?;
        self.publish(
            Some(space_id),
            &[
                Topic::Governance,
                Topic::Partnerships,
                Topic::Agreements,
                Topic::Ventures,
            ],
        );
        self.gov_reload(&ctx, &scope, partnership_id)
    }

    fn folder_terms(&self, ctx: &Ctx, l: &Ledger) -> Vec<(String, String)> {
        let f = |v: i64| format(Money::new(v, l.cur), ctx.locale);
        let t = &l.terms;
        let mut out = vec![(
            "folder.term.parties".to_string(),
            t.parties
                .iter()
                .map(|p| {
                    format!(
                        "{} — {}%",
                        p.full_name,
                        format_percent_bp(p.profit_share_bp)
                    )
                })
                .collect::<Vec<_>>()
                .join("; "),
        )];
        let capital: Vec<String> = t
            .parties
            .iter()
            .filter(|p| Payload::capital_of(p) > 0)
            .map(|p| format!("{}: {}", p.full_name, f(Payload::capital_of(p))))
            .collect();
        if !capital.is_empty() {
            out.push(("folder.term.capital".into(), capital.join("; ")));
        }
        // 5-band: zarar ulushlari (domen qoidasi bo'yicha) va beparvolik bandi.
        let mut loss: Vec<String> = match t.rules(l.cur).ok().and_then(|r| r.loss_share_bp) {
            Some(bp) => t
                .parties
                .iter()
                .zip(bp)
                .map(|(p, b)| format!("{} — {}%", p.full_name, format_percent_bp(b)))
                .collect(),
            None => Vec::new(),
        };
        loss.extend(t.negligence_clause.clone());
        if !loss.is_empty() {
            out.push(("folder.term.loss".into(), loss.join("; ")));
        }
        if let Some(c) = t.custody.value() {
            out.push((
                "folder.term.custody".into(),
                format!("{} — {}", c.location, t.party_name(&c.keeper_party_id)),
            ));
        }
        if let Some(e) = t.exit_clause.value() {
            out.push((
                "folder.term.exit".into(),
                format!("{}; {}", e.valuation_method, e.payout_terms),
            ));
        }
        if let Some(x) = t.term.value() {
            out.push((
                "folder.term.term".into(),
                format!("{} — {}", show(&x.effective_from), show(&x.review_date)),
            ));
        }
        out
    }

    /// «Hakam uchun ish papkasi» (2F.8): nizo va talablar, shartnoma va versiyalar, davr
    /// yozuvlari va zanjir tekshiruvi, bayonnomalar, hodisalar, hakam qarori — bitta PDF.
    pub fn dispute_folder_pdf(
        &self,
        space_id: &str,
        partnership_id: &str,
        dispute_id: &str,
    ) -> Result<Vec<u8>, AppError> {
        let ctx = self.ctx()?;
        let scope = self.scope(&ctx, space_id)?;
        let l = self.venture_book(&scope, partnership_id)?;
        let rec = self.records(&scope, &l)?;
        let (d, claims, decision) = Self::dispute_of(&rec, dispute_id)?;
        let view = self.partnership_view(&scope, self.partnership_row(&scope, partnership_id)?)?;
        let mut versions = Vec::new();
        for ver in &view.versions {
            let sigs = self.db.read(|c| prepo::signatures(c, &scope, &ver.id))?;
            let p: Payload = serde_json::from_str(&ver.payload_json).map_err(|_| corrupt())?;
            versions.push(FolderVersion {
                no: format!("v{}", ver.version_no),
                date: show(ver.created_at.get(..10).unwrap_or_default()),
                hash_code: short_code(&ver.payload_hash),
                signatures: format!("{} / {}", sigs.len(), p.required_signers().len()),
                note: ver.change_note.clone().unwrap_or_default(),
                in_force: view.row.signed_version == Some(ver.version_no),
            });
        }
        let mut periods = Vec::new();
        for (p, s) in &l.periods {
            let list: Vec<&EntryRow> = l
                .entries
                .iter()
                .filter(|e| p.start_on <= e.occurred_on && e.occurred_on <= p.end_on)
                .collect();
            let t = Totals {
                entries: s.entries,
                periods_closed: 1,
                income: s.income,
                expense: s.expense,
                force_majeure: s.force_majeure,
                corrections: s.corrections,
                result: s.result,
            };
            let mut totals = Self::report_totals(&ctx, l.cur, &t);
            totals.retain(|(k, _)| k != "vtotal.periods" && k != "vtotal.entries");
            periods.push(FolderPeriod {
                title: format!(
                    "{} · {} — {}",
                    p.period_no,
                    show(&p.start_on),
                    show(&p.end_on)
                ),
                totals,
                entries: self.report_entries(&ctx, &l, &list)?,
            });
        }
        let open: Vec<&EntryRow> = l
            .entries
            .iter()
            .filter(|e| l.last_end().is_none_or(|x| e.occurred_on.as_str() > x))
            .collect();
        if !open.is_empty() {
            let from = ymd(l.open_from()?);
            let last = open
                .iter()
                .map(|e| e.occurred_on.as_str())
                .max()
                .unwrap_or(from.as_str())
                .to_string();
            let mut totals = Self::report_totals(&ctx, l.cur, &totals(&l, &from, &last)?);
            totals.retain(|(k, _)| k != "vtotal.periods" && k != "vtotal.entries");
            periods.push(FolderPeriod {
                title: format!("{} · {} — …", l.periods.len() + 1, show(&from)),
                totals,
                entries: self.report_entries(&ctx, &l, &open)?,
            });
        }
        let mut reviews = Vec::new();
        for r in &rec.reviews {
            let (status, _) = Self::integrity(&rec, r)?;
            reviews.push(FolderReview {
                no: r.review_no.to_string(),
                range: format!("{} — {}", show(&r.from_on), show(&r.to_on)),
                held_on: show(&r.held_on),
                acks: rec
                    .acks
                    .iter()
                    .filter(|a| a.review_id == r.id)
                    .map(|a| AckLine {
                        party: l.terms.party_name(&a.party_id),
                        verdict: a.verdict.clone(),
                        note: a.note.clone().unwrap_or_default(),
                    })
                    .collect(),
                chain_code: short_code(&r.chain_head),
                integrity: status.as_str().into(),
            });
        }
        let clauses: Vec<u8> = serde_json::from_str(&d.clauses_json).map_err(|_| corrupt())?;
        let doc = ArbiterFolder {
            ident: d.id.clone(),
            locale: pdf_locale(ctx.locale),
            title: l.row.title.clone(),
            kind: l.row.kind.clone(),
            arbiter: l
                .terms
                .arbiter
                .value()
                .map_or_else(|| "—".to_string(), |a| a.full_name.clone()),
            opened_on: show(&d.opened_on),
            opened_by: l.terms.party_name(&d.opened_by_party),
            subject: d.subject.clone(),
            clauses: clauses
                .iter()
                .map(u8::to_string)
                .collect::<Vec<_>>()
                .join(", "),
            claims: claims
                .iter()
                .map(|c| FolderClaim {
                    party: l.terms.party_name(&c.party_id),
                    claim: c.claim.clone(),
                })
                .collect(),
            terms: self.folder_terms(&ctx, &l),
            versions,
            periods,
            chain_ok: l.chain_ok,
            chain_entries: u32_of(rec.journal.len())?,
            chain_short_code: short_code(&l.head),
            reviews,
            incidents: rec
                .incidents
                .iter()
                .map(|i| Self::incident_line(&l, i, true))
                .collect(),
            decision: decision.as_ref().map(|x| FolderDecision {
                decided_on: show(&x.decided_on),
                arbiter: x.arbiter_name.clone(),
                decision: x.decision.clone(),
                outcome: x.outcome.clone(),
            }),
        };
        let rendered = doc
            .render(engine(), self.today(&ctx))
            .map_err(|e| AppError::new(e.code))?;
        Ok(rendered.pdf)
    }

    /// Yillik yangilash (2F.3): kuchdagi versiyadagi `reviewDate` bir yilga suriladi. Hamma
    /// qayta imzolagach yangi versiya kuchga kiradi («o'zgarishsiz tasdiqlash» ham versiya).
    pub fn renew_partnership(
        &self,
        space_id: &str,
        partnership_id: &str,
    ) -> Result<PartnershipDto, AppError> {
        let ctx = self.ctx()?;
        let scope = self.scope(&ctx, space_id)?;
        let l = self.venture_book(&scope, partnership_id)?;
        if l.row.status != ACTIVE {
            return Err(AppError::new("NOT_ACTIVE"));
        }
        let current = l.terms.term.value().ok_or(AppError::new("TERM_REQUIRED"))?;
        let next = renewed_review_date(ymd_parse(&current.review_date)?)
            .ok_or(AppError::new("INVALID_DATE"))?;
        let mut payload = self.load_payload(&scope, &l.row)?;
        match &mut payload.term {
            Answer::Answered { value } => value.review_date = ymd(next),
            _ => return Err(AppError::new("TERM_REQUIRED")),
        }
        let json = serde_json::to_string(&payload).map_err(|_| corrupt())?;
        let meta = self.meta();
        self.db
            .write(|tx| agreements::set_payload(tx, &scope, &l.row.agreement_id, &json, &meta))?;
        self.publish(Some(space_id), &[Topic::Partnerships, Topic::Agreements]);
        self.reload(&ctx, &scope, partnership_id)
    }

    // ---- oilaviy kelishuvlar (2F.10) ----

    fn parse_family(&self, input: FamilyAgreementInput) -> Result<FamilyP, AppError> {
        if !FAMILY_TEMPLATES.contains(&input.template_key.as_str()) {
            return Err(AppError::on("INVALID_TEMPLATE", "templateKey"));
        }
        let title = text(&input.title, "title")?;
        let items: Vec<String> = input
            .items
            .iter()
            .filter_map(|i| clean_opt(Some(i)))
            .collect();
        if items.is_empty() {
            return Err(AppError::on("REQUIRED", "items"));
        }
        if items.len() > MAX_FAMILY_ITEMS {
            return Err(AppError::on("TOO_MANY_ITEMS", "items"));
        }
        if items.iter().any(|i| i.chars().count() > MAX_TEXT) {
            return Err(AppError::on("TOO_LONG", "items"));
        }
        let review_date = match clean_opt(input.review_date.as_deref()) {
            None => None,
            Some(d) => Some(ymd(date(&d, "reviewDate")?)),
        };
        Ok(FamilyP {
            template_key: input.template_key,
            title,
            items,
            review_date,
        })
    }

    fn family_payload(
        &self,
        scope: &SpaceScope,
        id: &str,
    ) -> Result<(agreements::AgreementRow, FamilyP), AppError> {
        let row = self
            .db
            .read(|c| agreements::get(c, scope, id))?
            .filter(|a| a.agreement_type == FAMILY)
            .ok_or(AppError::on("NOT_FOUND", "agreementId"))?;
        let json = self
            .db
            .read(|c| agreements::payload(c, scope, id))?
            .ok_or_else(corrupt)?;
        let p = serde_json::from_str(&json).map_err(|_| corrupt())?;
        Ok((row, p))
    }

    fn family_dto(
        &self,
        ctx: &Ctx,
        scope: &SpaceScope,
        row: &agreements::AgreementRow,
        p: &FamilyP,
    ) -> Result<FamilyAgreementDto, AppError> {
        let hash = p.hash()?;
        let signoffs = self.db.read(|c| repo::family_signoffs(c, scope, &row.id))?;
        let adults = self
            .adult_members(ctx)?
            .iter()
            .map(|m| SignoffDto {
                member_id: m.id.clone(),
                name: m.display_name.clone(),
                agreed_on: signoffs
                    .iter()
                    .find(|s| s.member_id == m.id && s.payload_hash == hash)
                    .map(|s| s.agreed_on.clone()),
            })
            .collect();
        Ok(FamilyAgreementDto {
            id: row.id.clone(),
            template_key: p.template_key.clone(),
            title: p.title.clone(),
            items: p.items.clone(),
            review_date: p.review_date.clone(),
            status: row.status.clone(),
            adults,
            chain_code: short_code(&hash),
        })
    }

    /// Hamma katta a'zo joriy matnni tasdiqlaganmi.
    fn family_complete(
        &self,
        ctx: &Ctx,
        scope: &SpaceScope,
        id: &str,
        hash: &str,
    ) -> Result<bool, AppError> {
        let signoffs = self.db.read(|c| repo::family_signoffs(c, scope, id))?;
        let adults = self.adult_members(ctx)?;
        Ok(!adults.is_empty()
            && adults.iter().all(|m| {
                signoffs
                    .iter()
                    .any(|s| s.member_id == m.id && s.payload_hash == hash)
            }))
    }

    pub fn family_agreements(&self, space_id: &str) -> Result<Vec<FamilyAgreementDto>, AppError> {
        let ctx = self.ctx()?;
        let scope = self.scope(&ctx, space_id)?;
        self.db
            .read(|c| agreements::list(c, &scope))?
            .into_iter()
            .filter(|a| a.agreement_type == FAMILY)
            .map(|a| {
                let (row, p) = self.family_payload(&scope, &a.id)?;
                self.family_dto(&ctx, &scope, &row, &p)
            })
            .collect()
    }

    pub fn create_family_agreement(
        &self,
        space_id: &str,
        input: FamilyAgreementInput,
    ) -> Result<FamilyAgreementDto, AppError> {
        let ctx = self.ctx()?;
        let scope = self.scope(&ctx, space_id)?;
        let p = self.parse_family(input)?;
        let json = serde_json::to_string(&p).map_err(|_| corrupt())?;
        let row = agreements::AgreementRow {
            id: self.new_id(),
            agreement_type: FAMILY.into(),
            status: DRAFT.into(),
            title: p.title.clone(),
            keeper_device_id: self.device_id.clone(),
        };
        let meta = self.meta();
        self.db.write(|tx| {
            agreements::insert(tx, &scope, &row, &meta)?;
            agreements::set_payload(tx, &scope, &row.id, &json, &meta)
        })?;
        self.publish(Some(space_id), &[Topic::Agreements]);
        self.family_dto(&ctx, &scope, &row, &p)
    }

    /// Matn o'zgarsa, oldingi tasdiqlar yangi matnga o'tmaydi — hamma qayta tasdiqlaydi.
    pub fn update_family_agreement(
        &self,
        space_id: &str,
        id: &str,
        input: FamilyAgreementInput,
    ) -> Result<FamilyAgreementDto, AppError> {
        let ctx = self.ctx()?;
        let scope = self.scope(&ctx, space_id)?;
        let (mut row, old) = self.family_payload(&scope, id)?;
        let p = self.parse_family(input)?;
        if p != old {
            let json = serde_json::to_string(&p).map_err(|_| corrupt())?;
            let complete = self.family_complete(&ctx, &scope, id, &p.hash()?)?;
            row.status = if complete { ACTIVE } else { DRAFT }.into();
            row.title.clone_from(&p.title);
            let meta = self.meta();
            self.db.write(|tx| {
                agreements::set_payload(tx, &scope, id, &json, &meta)?;
                agreements::set_title(tx, &scope, id, &row.title, &meta)?;
                agreements::set_status(tx, &scope, id, &row.status, &meta)
            })?;
            self.publish(Some(space_id), &[Topic::Agreements]);
        }
        self.family_dto(&ctx, &scope, &row, &p)
    }

    /// Katta a'zoning tasdig'i (PIN'ni adapter tekshiradi) — joriy matn xeshiga bog'lanadi.
    pub fn confirm_family_agreement(
        &self,
        space_id: &str,
        id: &str,
        member_id: &str,
    ) -> Result<FamilyAgreementDto, AppError> {
        let ctx = self.ctx()?;
        let scope = self.scope(&ctx, space_id)?;
        let (mut row, p) = self.family_payload(&scope, id)?;
        let adult = self
            .adult_members(&ctx)?
            .into_iter()
            .any(|m| m.id == member_id);
        if !adult {
            return Err(AppError::on("NOT_ADULT_MEMBER", "memberId"));
        }
        let hash = p.hash()?;
        let done = self.db.read(|c| repo::family_signoffs(c, &scope, id))?;
        if !done
            .iter()
            .any(|s| s.member_id == member_id && s.payload_hash == hash)
        {
            let signoff = FamilySignoffRow {
                member_id: member_id.into(),
                payload_hash: hash.clone(),
                agreed_on: ymd(self.today(&ctx)),
            };
            let sid = self.new_id();
            let meta = self.meta();
            self.db
                .write(|tx| repo::insert_family_signoff(tx, &scope, &sid, id, &signoff, &meta))?;
            if self.family_complete(&ctx, &scope, id, &hash)? && row.status != ACTIVE {
                row.status = ACTIVE.into();
                self.db
                    .write(|tx| agreements::set_status(tx, &scope, id, ACTIVE, &meta))?;
            }
            self.publish(Some(space_id), &[Topic::Agreements]);
        }
        self.family_dto(&ctx, &scope, &row, &p)
    }

    /// Yumshoq o'chirish: tasdiqlar dalil sifatida bazada qoladi.
    pub fn delete_family_agreement(&self, space_id: &str, id: &str) -> Result<(), AppError> {
        let ctx = self.ctx()?;
        let scope = self.scope(&ctx, space_id)?;
        self.family_payload(&scope, id)?;
        let meta = self.meta();
        self.db
            .write(|tx| agreements::delete(tx, &scope, id, &meta))?;
        self.publish(Some(space_id), &[Topic::Agreements]);
        Ok(())
    }

    // ---- eslatmalar va kelishuvlar markazi ----

    fn family_reminder(
        &self,
        ctx: &Ctx,
        row: &agreements::AgreementRow,
        p: &FamilyP,
    ) -> Result<Option<ReminderDto>, AppError> {
        let Some(d) = &p.review_date else {
            return Ok(None);
        };
        let due = ymd_parse(d)?;
        Ok(reminder(self.today(ctx), due, REVIEW_LEAD_DAYS).map(|r| {
            let (state, days) = reminder_parts(r);
            ReminderDto {
                agreement_id: row.id.clone(),
                ref_id: row.id.clone(),
                agreement_type: FAMILY.into(),
                kind: "REVIEW".into(),
                title: p.title.clone(),
                due_on: ymd(due),
                state: state.into(),
                days,
            }
        }))
    }

    /// Faol sheriklik daftari (faollashtirilmagan bo'lsa — `None`).
    fn active_book(
        &self,
        scope: &SpaceScope,
        row: &PartnershipRow,
    ) -> Result<Option<Ledger>, AppError> {
        if row.activated_on.is_none() || row.signed_version.is_none() {
            return Ok(None);
        }
        Ok(Some(self.venture_book(scope, &row.id)?))
    }

    /// Bosh sahifa eslatmalari: ko'rik, yillik yangilash, oilaviy kelishuvni qayta ko'rish.
    pub fn agreement_reminders(&self, space_id: &str) -> Result<Vec<ReminderDto>, AppError> {
        let ctx = self.ctx()?;
        let scope = self.scope(&ctx, space_id)?;
        let mut out = Vec::new();
        for row in self.db.read(|c| prepo::list(c, &scope))? {
            if let Some(l) = self.active_book(&scope, &row)? {
                let reviews = self.db.read(|c| repo::reviews(c, &scope, &row.id))?;
                let sch = self.schedule(&ctx, &l, &reviews)?;
                out.extend(sch.review);
                out.extend(sch.renewal);
            }
        }
        for a in self.db.read(|c| agreements::list(c, &scope))? {
            if a.agreement_type == FAMILY {
                let (row, p) = self.family_payload(&scope, &a.id)?;
                out.extend(self.family_reminder(&ctx, &row, &p)?);
            }
        }
        out.sort_by(|a, b| a.due_on.cmp(&b.due_on).then(a.title.cmp(&b.title)));
        Ok(out)
    }

    /// Kelishuvlar markazi (D13A): turi, holati, keyingi ko'rik, ochiq hodisa va nizolar.
    pub fn agreements_center(&self, space_id: &str) -> Result<Vec<AgreementSummaryDto>, AppError> {
        let ctx = self.ctx()?;
        let scope = self.scope(&ctx, space_id)?;
        let partnerships = self.db.read(|c| prepo::list(c, &scope))?;
        let mut out = Vec::new();
        for a in self.db.read(|c| agreements::list(c, &scope))? {
            let mut dto = AgreementSummaryDto {
                agreement_id: a.id.clone(),
                agreement_type: a.agreement_type.clone(),
                ref_id: a.id.clone(),
                title: a.title.clone(),
                status: a.status.clone(),
                next_review: None,
                reminder: None,
                open_incidents: 0,
                open_disputes: 0,
            };
            if a.agreement_type == PARTNERSHIP {
                let Some(row) = partnerships.iter().find(|p| p.agreement_id == a.id) else {
                    continue;
                };
                dto.ref_id.clone_from(&row.id);
                dto.title.clone_from(&row.title);
                if let Some(l) = self.active_book(&scope, row)? {
                    let rec = self.records(&scope, &l)?;
                    let sch = self.schedule(&ctx, &l, &rec.reviews)?;
                    dto.next_review = sch.next_due.map(ymd);
                    dto.reminder = [sch.review, sch.renewal]
                        .into_iter()
                        .flatten()
                        .min_by(|x, y| x.due_on.cmp(&y.due_on));
                    dto.open_incidents = u32_of(
                        rec.incidents
                            .iter()
                            .filter(|i| i.resolved_on.is_none())
                            .count(),
                    )?;
                    dto.open_disputes =
                        u32_of(rec.disputes.iter().filter(|(_, _, x)| x.is_none()).count())?;
                }
            } else if a.agreement_type == FAMILY {
                let (row, p) = self.family_payload(&scope, &a.id)?;
                dto.next_review.clone_from(&p.review_date);
                dto.reminder = self.family_reminder(&ctx, &row, &p)?;
            }
            out.push(dto);
        }
        Ok(out)
    }
}

/// Ishorali summa: `+12 000 000 so'm`, `−1 000 000 so'm`.
fn signed(v: i64, cur: Currency, ctx: &Ctx) -> String {
    let t = format(Money::new(v.saturating_abs(), cur), ctx.locale);
    match v.signum() {
        1 => format!("+{t}"),
        -1 => format!("−{t}"),
        _ => t,
    }
}
