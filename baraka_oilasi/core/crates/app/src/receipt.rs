//! Qarz tilxati PDF'i (Y6 + U8 ning birinchi qismi). Hozircha jurnalga bog'lanmagan mustaqil
//! hujjat; U8 da `Agreement(type = LOAN)` va jurnal `chainHead` bilan bog'lanadi.
use std::sync::OnceLock;

use baraka_money::{format, parse_amount, Currency, Locale, Money};
use baraka_pdf::{LoanReceipt, PdfEngine, PdfLocale, ScheduleLine};
use chrono::NaiveDate;

use crate::app::Ctx;
use crate::text::{clean, clean_opt, required};
use crate::{App, AppError, LoanReceiptInput};

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

fn show_date(d: NaiveDate) -> String {
    d.format("%d.%m.%Y").to_string()
}

fn positive(s: &str, currency: Currency, field: &str) -> Result<Money, AppError> {
    let m = parse_amount(s, currency).map_err(|e| AppError::on(e.code(), field))?;
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

impl App {
    /// Tilxat PDF baytlari. Qoidalar: summa > 0, jadval bo'sh emas, jadval yig'indisi = summa,
    /// sanalar o'sib boradi va berilgan sanadan oldin emas. Foiz maydoni umuman yo'q.
    pub fn render_loan_receipt(&self, input: LoanReceiptInput) -> Result<Vec<u8>, AppError> {
        let ctx: Ctx = self.ctx()?;
        let currency = Currency::from_code(&input.currency)?;
        let amount = positive(&input.amount, currency, "amount")?;
        let issued = match input.issued_on.as_deref() {
            Some(d) => date(d, "issuedOn")?,
            None => self.today(&ctx),
        };
        if input.schedule.is_empty() {
            return Err(AppError::on("SCHEDULE_REQUIRED", "schedule"));
        }
        let mut lines = Vec::with_capacity(input.schedule.len());
        let mut total = Money::zero(currency);
        let mut prev = issued;
        for line in &input.schedule {
            let d = date(&line.date, "schedule")?;
            if d < prev {
                return Err(AppError::on("SCHEDULE_DATES_ORDER", "schedule"));
            }
            prev = d;
            let m = positive(&line.amount, currency, "schedule")?;
            total = total.checked_add(m)?;
            lines.push(ScheduleLine {
                date: show_date(d),
                amount: format(m, ctx.locale),
            });
        }
        if total != amount {
            return Err(AppError::on("SCHEDULE_SUM_MISMATCH", "schedule"));
        }
        let receipt = LoanReceipt {
            ident: format!("loan-receipt-{}", self.new_id()),
            locale: pdf_locale(ctx.locale),
            lender: required(&input.lender, "lender")?,
            borrower: required(&input.borrower, "borrower")?,
            amount: format(amount, ctx.locale),
            issued_on: show_date(issued),
            due_on: show_date(prev),
            place: required(&input.place, "place")?,
            schedule: lines,
            witnesses: input
                .witnesses
                .iter()
                .map(|w| clean(w))
                .filter(|w| !w.is_empty())
                .collect(),
            note: clean_opt(input.note.as_deref()),
            chain_head: None,
            chain_short_code: None,
        };
        if receipt.lender == receipt.borrower {
            return Err(AppError::on("SAME_PARTY", "borrower"));
        }
        let rendered = receipt
            .render(engine(), self.today(&ctx))
            .map_err(|e| AppError::new(e.code))?;
        Ok(rendered.pdf)
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
