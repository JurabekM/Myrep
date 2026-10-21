//! Qarz tilxati (uy/SPEC 2D.5, U8): `Agreement(type = LOAN)` + jurnal + PDF.
//!
//! `render_loan_receipt` — saqlamasdan oldindan ko'rish; `issue_loan_receipt` — kelishuv, jurnal
//! (`OPENING_BALANCE`, reja `refs` da xeshlanadi) va qarz yoki bergan qarz yozuvi bitta
//! tranzaksiyada; `loan_receipt_pdf` — saqlangan tilxatni joriy `chainHead` bilan chop etish.
use std::sync::OnceLock;

use baraka_domain_uy::debt::{PlanKind, PlanLine, PlanSpec, Receivable};
use baraka_journal::{short_code, EntryKind, JournalAmount, JournalEntry};
use baraka_money::{format, parse_amount, Currency, Locale, Money};
use baraka_pdf::{LoanReceipt, PdfEngine, PdfLocale, ScheduleLine};
use baraka_storage::repo::debts::{self, Owner};
use baraka_storage::repo::{agreements, journal};
use chrono::NaiveDate;
use serde::{Deserialize, Serialize};

use crate::app::Ctx;
use crate::events::Topic;
use crate::text::{clean, clean_opt, required};
use crate::{App, AppError, IssueLoanReceiptInput, IssuedReceiptDto, LoanReceiptInput};

fn engine() -> &'static PdfEngine {
    static ENGINE: OnceLock<PdfEngine> = OnceLock::new();
    ENGINE.get_or_init(PdfEngine::new)
}

/// Foydalanuvchi sanasi: `15.11.2026`, `5.1.2027` yoki `2026-11-15` (UI sanani o'zi o'qimaydi).
pub(crate) fn date(s: &str, field: &str) -> Result<NaiveDate, AppError> {
    let t = s.trim();
    NaiveDate::parse_from_str(t, "%d.%m.%Y")
        .or_else(|_| NaiveDate::parse_from_str(t, "%Y-%m-%d"))
        .map_err(|_| AppError::on("INVALID_DATE", field))
}

pub(crate) fn ymd(d: NaiveDate) -> String {
    d.format("%Y-%m-%d").to_string()
}

fn show_date(d: NaiveDate) -> String {
    d.format("%d.%m.%Y").to_string()
}

pub(crate) fn amount_in(s: &str, currency: Currency, field: &str) -> Result<Money, AppError> {
    parse_amount(s, currency).map_err(|e| AppError::on(e.code(), field))
}

pub(crate) fn positive(s: &str, currency: Currency, field: &str) -> Result<Money, AppError> {
    let m = amount_in(s, currency, field)?;
    if m.is_positive() {
        Ok(m)
    } else {
        Err(AppError::on("AMOUNT_NOT_POSITIVE", field))
    }
}

pub(crate) fn pdf_locale(locale: Locale) -> PdfLocale {
    match locale {
        Locale::Uz => PdfLocale::Uz,
        Locale::UzCyrl => PdfLocale::UzCyrl,
        Locale::Ru => PdfLocale::Ru,
    }
}

/// Tekshirilgan tilxat ma'lumotlari.
struct Parsed {
    lender: String,
    borrower: String,
    amount: Money,
    issued: NaiveDate,
    place: String,
    lines: Vec<PlanLine>,
    witnesses: Vec<String>,
    note: Option<String>,
}

/// Saqlangan tilxat (kelishuvning `payload_json`). Reja va summa qarz yozuvidan olinadi.
#[derive(Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
struct ReceiptPayload {
    record_type: String,
    record_id: String,
    lender: String,
    borrower: String,
    issued_on: String,
    place: String,
    witnesses: Vec<String>,
    note: Option<String>,
}

const LENDER: &str = "LENDER";
/// Jurnalda qarzni qaytaruvchi tomon.
pub(crate) const BORROWER: &str = "BORROWER";

/// Reja qatorlari jurnal `refs` ida: `plan:2026-11-15:300000000:UZS` (reja ham xeshlanadi).
pub(crate) fn plan_refs(lines: &[PlanLine]) -> Vec<String> {
    lines
        .iter()
        .map(|l| {
            format!(
                "plan:{}:{}:{}",
                ymd(l.date),
                l.amount.minor(),
                l.amount.currency().code()
            )
        })
        .collect()
}

impl App {
    /// Qoidalar: summa > 0, jadval bo'sh emas, jadval yig'indisi = summa, sanalar o'sib boradi va
    /// berilgan sanadan oldin emas, tomonlar har xil. Foiz maydoni umuman yo'q.
    fn parse_receipt(&self, ctx: &Ctx, input: &LoanReceiptInput) -> Result<Parsed, AppError> {
        let currency = Currency::from_code(&input.currency)?;
        let amount = positive(&input.amount, currency, "amount")?;
        let issued = match input.issued_on.as_deref() {
            Some(d) => date(d, "issuedOn")?,
            None => self.today(ctx),
        };
        let lines = input
            .schedule
            .iter()
            .map(|l| {
                Ok(PlanLine {
                    date: date(&l.date, "schedule")?,
                    amount: positive(&l.amount, currency, "schedule")?,
                })
            })
            .collect::<Result<Vec<_>, AppError>>()?;
        Receivable {
            debtor: String::new(),
            amount,
            lent_on: issued,
            lines: lines.clone(),
        }
        .validate()?;
        let lender = required(&input.lender, "lender")?;
        let borrower = required(&input.borrower, "borrower")?;
        if lender == borrower {
            return Err(AppError::on("SAME_PARTY", "borrower"));
        }
        Ok(Parsed {
            lender,
            borrower,
            amount,
            issued,
            place: required(&input.place, "place")?,
            lines,
            witnesses: input
                .witnesses
                .iter()
                .map(|w| clean(w))
                .filter(|w| !w.is_empty())
                .collect(),
            note: clean_opt(input.note.as_deref()),
        })
    }

    fn receipt_pdf(
        &self,
        ctx: &Ctx,
        ident: String,
        p: &Parsed,
        head: Option<String>,
    ) -> Result<Vec<u8>, AppError> {
        let receipt = LoanReceipt {
            ident,
            locale: pdf_locale(ctx.locale),
            lender: p.lender.clone(),
            borrower: p.borrower.clone(),
            amount: format(p.amount, ctx.locale),
            issued_on: show_date(p.issued),
            due_on: p
                .lines
                .last()
                .map_or_else(|| show_date(p.issued), |l| show_date(l.date)),
            place: p.place.clone(),
            schedule: p
                .lines
                .iter()
                .map(|l| ScheduleLine {
                    date: show_date(l.date),
                    amount: format(l.amount, ctx.locale),
                })
                .collect(),
            witnesses: p.witnesses.clone(),
            note: p.note.clone(),
            chain_short_code: head.as_deref().map(short_code),
            chain_head: head,
        };
        let rendered = receipt
            .render(engine(), self.today(ctx))
            .map_err(|e| AppError::new(e.code))?;
        Ok(rendered.pdf)
    }

    /// Tilxat PDF baytlari (oldindan ko'rish, hech narsa saqlanmaydi).
    pub fn render_loan_receipt(&self, input: LoanReceiptInput) -> Result<Vec<u8>, AppError> {
        let ctx = self.ctx()?;
        let p = self.parse_receipt(&ctx, &input)?;
        self.receipt_pdf(&ctx, format!("loan-receipt-{}", self.new_id()), &p, None)
    }

    /// Tilxatni saqlash. `BORROWED` — qarz inventariga (`MANUAL` reja), `LENT` — bergan qarzlarga.
    /// Jurnal birinchi yozuvi — `OPENING_BALANCE`, reja qatorlari uning `refs` ida.
    pub fn issue_loan_receipt(
        &self,
        space_id: &str,
        input: IssueLoanReceiptInput,
    ) -> Result<IssuedReceiptDto, AppError> {
        let ctx = self.ctx()?;
        let scope = self.scope(&ctx, space_id)?;
        let p = self.parse_receipt(&ctx, &input.receipt)?;
        let cur = p.amount.currency();
        let agreement_id = self.new_id();
        let record_id = self.new_id();
        let (owner, debt_row, rec_row) = match input.direction.as_str() {
            "BORROWED" => {
                let creditor_type = input.creditor_type.as_deref().unwrap_or("FRIEND");
                if !matches!(creditor_type, "RELATIVE" | "FRIEND" | "OTHER") {
                    return Err(AppError::on("INVALID_CREDITOR_TYPE", "creditorType"));
                }
                let spec = PlanSpec {
                    kind: PlanKind::Manual,
                    principal: p.amount,
                    markup: Money::zero(cur),
                    annual_bp: 0,
                    months: 0,
                    first_date: p.issued,
                    lines: p.lines.clone(),
                };
                let check = self.borrow_check_json(
                    &ctx,
                    &scope,
                    &spec,
                    &p.lines,
                    input.is_new,
                    input.borrow_check.as_ref(),
                )?;
                let row = debts::DebtRow {
                    id: record_id.clone(),
                    creditor_type: creditor_type.to_string(),
                    creditor: p.lender.clone(),
                    reason: clean_opt(input.reason.as_deref()),
                    currency: cur.code().to_string(),
                    principal_minor: p.amount.minor(),
                    original_principal_minor: p.amount.minor(),
                    paid_before_minor: 0,
                    plan_kind: PlanKind::Manual.as_str().to_string(),
                    annual_bp: 0,
                    markup_minor: 0,
                    months: 0,
                    started_on: ymd(p.issued),
                    early_repayment_terms: None,
                    priority: None,
                    borrow_check_json: check,
                    agreement_id: Some(agreement_id.clone()),
                    status: "ACTIVE".to_string(),
                    prepayment_fee_bp: 0,
                };
                (Owner::Debt, Some(row), None)
            }
            "LENT" => {
                let row = debts::ReceivableRow {
                    id: record_id.clone(),
                    debtor: p.borrower.clone(),
                    currency: cur.code().to_string(),
                    amount_minor: p.amount.minor(),
                    lent_on: ymd(p.issued),
                    note: p.note.clone(),
                    agreement_id: Some(agreement_id.clone()),
                    status: "ACTIVE".to_string(),
                };
                (Owner::Receivable, None, Some(row))
            }
            _ => return Err(AppError::on("INVALID_DIRECTION", "direction")),
        };
        let payload = serde_json::to_string(&ReceiptPayload {
            record_type: owner.as_str().to_string(),
            record_id: record_id.clone(),
            lender: p.lender.clone(),
            borrower: p.borrower.clone(),
            issued_on: ymd(p.issued),
            place: p.place.clone(),
            witnesses: p.witnesses.clone(),
            note: p.note.clone(),
        })
        .map_err(|_| AppError::new("SERIALIZE"))?;
        let entry = JournalEntry {
            id: self.new_id(),
            agreement_id: agreement_id.clone(),
            kind: EntryKind::OpeningBalance,
            party_id: Some(LENDER.to_string()),
            amount: Some(JournalAmount {
                minor: p.amount.minor(),
                currency: cur.code().to_string(),
            }),
            date: ymd(p.issued),
            note: None,
            corrects_entry_id: None,
            refs: plan_refs(&p.lines),
        };
        entry.validate()?;
        let plan_rows = self.plan_rows(&p.lines);
        let meta = self.meta();
        let title = format!("{} → {}", p.lender, p.borrower);
        let stored = self.db.write(|tx| {
            agreements::insert(
                tx,
                &scope,
                &agreements::AgreementRow {
                    id: agreement_id.clone(),
                    agreement_type: "LOAN".to_string(),
                    status: "ACTIVE".to_string(),
                    title: title.clone(),
                    keeper_device_id: self.device_id.clone(),
                },
                &meta,
            )?;
            agreements::set_payload(tx, &scope, &agreement_id, &payload, &meta)?;
            let stored = journal::append(tx, &scope, &entry, &meta)?;
            if let Some(row) = &debt_row {
                debts::insert_debt(tx, &scope, row, &meta)?;
            }
            if let Some(row) = &rec_row {
                debts::insert_receivable(tx, &scope, row, &meta)?;
            }
            debts::insert_plan(tx, &scope, owner, &record_id, &plan_rows, &meta)?;
            Ok(stored)
        })?;
        self.publish(
            Some(space_id),
            &[Topic::Agreements, Topic::Journal, Topic::Debts],
        );
        Ok(IssuedReceiptDto {
            agreement_id,
            record_type: owner.as_str().to_string(),
            record_id,
            short_code: short_code(&stored.hash),
        })
    }

    /// Saqlangan tilxat PDF'i: reja qarz yozuvidan, tekshirish kodi — jurnalning joriy boshi.
    pub fn loan_receipt_pdf(
        &self,
        space_id: &str,
        agreement_id: &str,
    ) -> Result<Vec<u8>, AppError> {
        let ctx = self.ctx()?;
        let scope = self.scope(&ctx, space_id)?;
        let raw = self
            .db
            .read(|c| agreements::payload(c, &scope, agreement_id))?
            .ok_or(AppError::on("NOT_FOUND", "agreementId"))?;
        let pl: ReceiptPayload =
            serde_json::from_str(&raw).map_err(|_| AppError::new("CORRUPT_ROW"))?;
        let (owner, amount_minor, currency) = match pl.record_type.as_str() {
            "DEBT" => {
                let d = self
                    .db
                    .read(|c| debts::get_debt(c, &scope, &pl.record_id))?
                    .ok_or(AppError::new("NOT_FOUND"))?;
                (Owner::Debt, d.principal_minor, d.currency)
            }
            "RECEIVABLE" => {
                let r = self
                    .db
                    .read(|c| debts::get_receivable(c, &scope, &pl.record_id))?
                    .ok_or(AppError::new("NOT_FOUND"))?;
                (Owner::Receivable, r.amount_minor, r.currency)
            }
            _ => return Err(AppError::new("CORRUPT_ROW")),
        };
        let cur = Currency::from_code(&currency)?;
        let lines = self.load_plan(&scope, owner, &pl.record_id, cur)?;
        // Reja jurnalning birinchi yozuvida xeshlangan: bazada o'zgartirilgan bo'lsa — chop etilmaydi.
        if !self.plan_matches_journal(&scope, agreement_id, &lines)? {
            return Err(AppError::new("PLAN_JOURNAL_MISMATCH"));
        }
        let (seq, head) = self.db.read(|c| journal::head(c, &scope, agreement_id))?;
        let parsed = Parsed {
            lender: pl.lender,
            borrower: pl.borrower,
            amount: Money::new(amount_minor, cur),
            issued: date(&pl.issued_on, "issuedOn")?,
            place: pl.place,
            lines,
            witnesses: pl.witnesses,
            note: pl.note,
        };
        let head = (seq > 0).then_some(head);
        self.receipt_pdf(&ctx, format!("loan-{agreement_id}"), &parsed, head)
    }
}

#[cfg(test)]
mod tests {
    use super::date;

    #[test]
    fn user_dates() {
        let d = |s| date(s, "d").map(|x| x.to_string());
        assert_eq!(d("15.11.2026").unwrap(), "2026-11-15");
        assert_eq!(d(" 5.1.2027 ").unwrap(), "2027-01-05");
        assert_eq!(d("2026-11-15").unwrap(), "2026-11-15");
        for bad in ["31.02.2026", "11/15/2026", "", "15.11.26x"] {
            assert_eq!(d(bad).unwrap_err().code, "INVALID_DATE", "{bad}");
        }
    }
}
