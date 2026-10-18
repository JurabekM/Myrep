//! K4 — Kasb-kor «Nasiyani adolat bilan yurit» (`docs/kasbkor/SPEC.md` 5): kunlik kassa yopish,
//! mijozlar va nasiya daftari, haftalik ko'rik.
//!
//! Hisob `domain-kasbkor::{cash, credit}` da (vektorlar `kk_cash_close`, `kk_credit_sale`). Nasiya —
//! naqd asosida: savdo paytida tushum yo'q, har bir to'lov — Kasb-kor tushumi (bitta tranzaksiyada).
use baraka_domain_common::{week_start, WEEK_ANCHOR};
use baraka_domain_kasbkor::cash::{cash_close, CashClose, CashReason};
use baraka_domain_kasbkor::credit::{aging, CreditEvent, CreditState, CreditTerms};
use baraka_domain_kasbkor::owner::month_report;
use baraka_money::{parse_amount, Money};
use baraka_storage::repo::{incomes, kk_ledger};
use baraka_storage::SpaceScope;
use chrono::{Duration, Months, NaiveDate};
use serde::{Deserialize, Serialize};

use crate::app::Ctx;
use crate::events::Topic;
use crate::kasbkor::wallet;
use crate::receipt::ymd;
use crate::text::{clean_opt, required};
use crate::uy::positive;
use crate::*;

const BEGINNING: &str = "0000-01-01";
/// Takrorlanuvchi kamomad oynasi (SPEC 5.1: 4 hafta).
const SHORTAGE_WINDOW_DAYS: i64 = 28;

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
struct CashRecord {
    v: u32,
    cash_sales: i64,
    cash_expenses: i64,
    owner_draws: i64,
    handed_over: i64,
    other_in: i64,
    other_out: i64,
    suggest_search: bool,
}

fn parse_date(s: &str, field: &str) -> Result<NaiveDate, AppError> {
    NaiveDate::parse_from_str(s, "%Y-%m-%d").map_err(|_| AppError::on("INVALID_DATE", field))
}

fn corrupt() -> AppError {
    AppError::new("CORRUPT_ROW")
}

fn amount_opt(ctx: &Ctx, s: Option<&str>, field: &str) -> Result<Option<Money>, AppError> {
    match s.map(str::trim).filter(|t| !t.is_empty()) {
        None => Ok(None),
        Some(t) => Ok(Some(positive(ctx, t, field)?)),
    }
}

impl App {
    /// Yopilgan kassa kuni ichidagi naqd yozuvni qabul qilmaydi (kun o'zgarmas). Karta yozuvlari erkin.
    pub(crate) fn kk_ensure_cash_open(
        &self,
        scope: &SpaceScope,
        date: &str,
        touches_cash: bool,
    ) -> Result<(), AppError> {
        if !touches_cash {
            return Ok(());
        }
        match self.db.read(|c| kk_ledger::cash_closed_until(c, scope))? {
            Some(until) if date <= until.as_str() => {
                Err(AppError::on("CASH_DAY_CLOSED", "occurredOn"))
            }
            _ => Ok(()),
        }
    }

    /// `day` kunining kassa hisobi. `counted` bo'lsa — farq va holat (sabab hali so'ralmaydi).
    fn kk_cash_compute(
        &self,
        ctx: &Ctx,
        scope: &SpaceScope,
        day: NaiveDate,
        counted: Option<Money>,
        reason: Option<CashReason>,
    ) -> Result<(Money, CashClose), AppError> {
        let next = day.succ_opt().ok_or(AppError::new("INVALID_DATE"))?;
        let zero = Money::zero(ctx.currency);
        let before = self.kk_book(ctx, scope, BEGINNING, &ymd(day))?;
        let prior = month_report(
            ctx.currency,
            before.opening_cash,
            before.opening_card,
            zero,
            &before.moves,
        )?;
        let today = self.kk_book(ctx, scope, &ymd(day), &ymd(next))?;
        let opening = prior.cash.checked_add(today.opening_cash)?;
        if opening.is_negative() {
            return Err(AppError::on("CASH_OPENING_NEGATIVE", "day"));
        }
        let from = day - Duration::days(SHORTAGE_WINDOW_DAYS - 1);
        let recent: Vec<Money> = self
            .db
            .read(|c| kk_ledger::cash_days_between(c, scope, &ymd(from), &ymd(day)))?
            .into_iter()
            .filter(|r| r.currency == ctx.currency.code())
            .map(|r| Money::new(r.difference_minor, ctx.currency))
            .collect();
        // Oldindan ko'rishda sabab hali tanlanmagan — farq va holat uchun vaqtincha «noma'lum».
        let r = cash_close(
            opening,
            &today.moves,
            counted.unwrap_or(zero),
            reason.or(Some(CashReason::Unknown)),
            &recent,
        )?;
        Ok((opening, r))
    }

    fn kk_cash_day(
        &self,
        ctx: &Ctx,
        scope: &SpaceScope,
        day: Option<&str>,
    ) -> Result<NaiveDate, AppError> {
        let today = self.today(ctx);
        let day = match day {
            Some(d) => parse_date(d, "day")?,
            None => today,
        };
        if day > today {
            return Err(AppError::on("FUTURE_DAY", "day"));
        }
        if self
            .db
            .read(|c| kk_ledger::cash_closed_until(c, scope))?
            .is_some_and(|u| ymd(day) <= u)
        {
            return Err(AppError::on("CASH_DAY_CLOSED", "day"));
        }
        Ok(day)
    }

    /// Kassa yopish ustasi (SPEC 5.1): bugungi (yoki `day`) naqd harakatlar va kutilgan qoldiq.
    pub fn kk_cash_draft(
        &self,
        space_id: &str,
        day: Option<String>,
        counted: Option<String>,
    ) -> Result<KkCashDraftDto, AppError> {
        let ctx = self.ctx()?;
        let scope = self.kk_scope(&ctx, space_id)?;
        let day = self.kk_cash_day(&ctx, &scope, day.as_deref())?;
        let counted = match counted.as_deref().map(str::trim).filter(|t| !t.is_empty()) {
            None => None,
            Some(t) => {
                let m =
                    parse_amount(t, ctx.currency).map_err(|e| AppError::on(e.code(), "counted"))?;
                if m.is_negative() {
                    return Err(AppError::on("AMOUNT_NEGATIVE", "counted"));
                }
                Some(m)
            }
        };
        let (opening, r) = self.kk_cash_compute(&ctx, &scope, day, counted, None)?;
        let d = |m: Money| self.money_dto(&ctx, m);
        Ok(KkCashDraftDto {
            day: ymd(day),
            opening: d(opening),
            cash_sales: d(r.cash_sales),
            cash_expenses: d(r.cash_expenses),
            owner_draws: d(r.owner_draws),
            handed_over: d(r.handed_over),
            other_in: d(r.other_in),
            other_out: d(r.other_out),
            expected: d(r.expected),
            counted: counted.map(d),
            difference: counted.map(|_| d(r.difference)),
            status: counted.map(|_| r.status.as_str().to_string()),
            suggest_search: counted.is_some() && r.suggest_search,
            last_closed: self.db.read(|c| kk_ledger::cash_closed_until(c, &scope))?,
        })
    }

    /// Kunni yopish: yozuv o'zgarmaydi; farq nol bo'lmasa — sabab majburiy.
    pub fn kk_close_cash_day(
        &self,
        space_id: &str,
        input: KkCashCloseInput,
    ) -> Result<KkCashDayDto, AppError> {
        let ctx = self.ctx()?;
        let scope = self.kk_scope(&ctx, space_id)?;
        let day = self.kk_cash_day(&ctx, &scope, Some(&input.day))?;
        self.kk_ensure_open(&scope, &ymd(day), "day")?;
        let counted = parse_amount(&input.counted, ctx.currency)
            .map_err(|e| AppError::on(e.code(), "counted"))?;
        let reason = match input.reason.as_deref() {
            None => None,
            Some(r) => Some(CashReason::parse(r).ok_or(AppError::on("INVALID_REASON", "reason"))?),
        };
        let (opening, preview) = self.kk_cash_compute(&ctx, &scope, day, Some(counted), reason)?;
        if !preview.difference.is_zero() && reason.is_none() {
            return Err(AppError::on("REASON_REQUIRED", "reason"));
        }
        let r = preview;
        let rec = CashRecord {
            v: 1,
            cash_sales: r.cash_sales.minor(),
            cash_expenses: r.cash_expenses.minor(),
            owner_draws: r.owner_draws.minor(),
            handed_over: r.handed_over.minor(),
            other_in: r.other_in.minor(),
            other_out: r.other_out.minor(),
            suggest_search: r.suggest_search,
        };
        let row = kk_ledger::KkCashDayRow {
            id: self.new_id(),
            day: ymd(day),
            currency: ctx.currency.code().to_string(),
            opening_minor: opening.minor(),
            expected_minor: r.expected.minor(),
            counted_minor: counted.minor(),
            difference_minor: r.difference.minor(),
            reason: r.reason.map(|x| x.as_str().to_string()),
            note: clean_opt(input.note.as_deref()),
            result_json: serde_json::to_string(&rec).map_err(|_| corrupt())?,
            closed_at: self.meta().now,
        };
        let meta = self.meta();
        self.db
            .write(|tx| kk_ledger::insert_cash_day(tx, &scope, &row, &meta))?;
        self.publish(Some(space_id), &[Topic::Kasbkor]);
        self.cash_day_dto(&ctx, &row)
    }

    fn cash_day_dto(
        &self,
        ctx: &Ctx,
        r: &kk_ledger::KkCashDayRow,
    ) -> Result<KkCashDayDto, AppError> {
        let rec: CashRecord = serde_json::from_str(&r.result_json).map_err(|_| corrupt())?;
        let m = |minor: i64| self.money_dto(ctx, Money::new(minor, ctx.currency));
        Ok(KkCashDayDto {
            id: r.id.clone(),
            day: r.day.clone(),
            opening: m(r.opening_minor),
            expected: m(r.expected_minor),
            counted: m(r.counted_minor),
            difference: m(r.difference_minor),
            status: match r.difference_minor {
                0 => "EXACT",
                d if d < 0 => "SHORT",
                _ => "OVER",
            }
            .to_string(),
            reason: r.reason.clone(),
            note: r.note.clone(),
            suggest_search: rec.suggest_search,
        })
    }

    /// Yopilgan kunlar (yangisi birinchi).
    pub fn kk_cash_days(&self, space_id: &str) -> Result<Vec<KkCashDayDto>, AppError> {
        let ctx = self.ctx()?;
        let scope = self.kk_scope(&ctx, space_id)?;
        let mut rows = self
            .db
            .read(|c| kk_ledger::cash_days_between(c, &scope, BEGINNING, "9999-12-31"))?;
        rows.reverse();
        rows.iter()
            .filter(|r| r.currency == ctx.currency.code())
            .map(|r| self.cash_day_dto(&ctx, r))
            .collect()
    }

    // ---- Nasiya daftari ----

    /// Har bir nasiyaning `today` dagi holati: (qator, hodisalar, holat).
    fn kk_credit_states(
        &self,
        ctx: &Ctx,
        scope: &SpaceScope,
        today: NaiveDate,
    ) -> Result<
        Vec<(
            kk_ledger::KkCreditSaleRow,
            Vec<kk_ledger::KkCreditEventRow>,
            CreditState,
        )>,
        AppError,
    > {
        let events = self.db.read(|c| kk_ledger::credit_events(c, scope))?;
        let mut out = Vec::new();
        for sale in self
            .db
            .read(|c| kk_ledger::credit_sales(c, scope))?
            .into_iter()
            .filter(|s| s.currency == ctx.currency.code())
        {
            let mine: Vec<_> = events
                .iter()
                .filter(|e| e.sale_id == sale.id)
                .cloned()
                .collect();
            let st = self
                .credit_terms(ctx, &sale)?
                .state(&to_events(ctx, &mine)?, today)?;
            out.push((sale, mine, st));
        }
        Ok(out)
    }

    fn credit_terms(
        &self,
        ctx: &Ctx,
        s: &kk_ledger::KkCreditSaleRow,
    ) -> Result<CreditTerms, AppError> {
        Ok(CreditTerms {
            credit_price: Money::new(s.credit_price_minor, ctx.currency),
            cash_price: s.cash_price_minor.map(|m| Money::new(m, ctx.currency)),
            installments: u32::try_from(s.installments).map_err(|_| corrupt())?,
            first_due: parse_date(&s.first_due, "firstDue").map_err(|_| corrupt())?,
        })
    }

    /// Bosh sahifa uchun: mijozlardagi pul va undan muddati o'tgani.
    pub(crate) fn kk_receivables(
        &self,
        ctx: &Ctx,
        scope: &SpaceScope,
    ) -> Result<(Money, Money), AppError> {
        let states = self.kk_credit_states(ctx, scope, self.today(ctx))?;
        let a = aging(
            ctx.currency,
            &states.iter().map(|(_, _, s)| s).collect::<Vec<_>>(),
        )?;
        let overdue = a
            .overdue
            .iter()
            .try_fold(Money::zero(ctx.currency), |acc, m| acc.checked_add(*m))?;
        Ok((a.total, overdue))
    }

    fn sale_dto(
        &self,
        ctx: &Ctx,
        sale: &kk_ledger::KkCreditSaleRow,
        events: &[kk_ledger::KkCreditEventRow],
        st: &CreditState,
        customers: &[kk_ledger::KkCustomerRow],
        week: &str,
    ) -> Result<KkCreditSaleDto, AppError> {
        let d = |m: Money| self.money_dto(ctx, m);
        let m = |minor: i64| self.money_dto(ctx, Money::new(minor, ctx.currency));
        let customer = customers.iter().find(|c| c.id == sale.customer_id);
        Ok(KkCreditSaleDto {
            id: sale.id.clone(),
            customer_id: sale.customer_id.clone(),
            customer_name: customer.map(|c| c.name.clone()).unwrap_or_default(),
            customer_phone: customer.and_then(|c| c.phone.clone()),
            item: sale.item.clone(),
            sold_on: sale.sold_on.clone(),
            cash_price: sale.cash_price_minor.map(m),
            credit_price: m(sale.credit_price_minor),
            installments: u32::try_from(sale.installments).map_err(|_| corrupt())?,
            witness: sale.witness.clone(),
            note: sale.note.clone(),
            schedule: st
                .schedule
                .iter()
                .map(|r| KkInstallmentDto {
                    due: ymd(r.due),
                    amount: d(r.amount),
                    covered: d(r.covered),
                    state: r.state.as_str().to_string(),
                })
                .collect(),
            paid: d(st.paid),
            forgiven: d(st.forgiven),
            outstanding: d(st.outstanding),
            status: st.status.as_str().to_string(),
            overdue_days: u32::try_from(st.overdue_days).unwrap_or(u32::MAX),
            bucket: st.bucket.map(|b| b.as_str().to_string()),
            next_due: st.next_due.map(|(date, amount)| KkNextDueDto {
                date: ymd(date),
                amount: d(amount),
            }),
            credit_markup: st.credit_markup.map(d),
            events: events
                .iter()
                .map(|e| {
                    Ok(KkCreditEventDto {
                        id: e.id.clone(),
                        kind: e.kind.clone(),
                        occurred_on: e.occurred_on.clone(),
                        amount: e.amount_minor.map(m),
                        months: e
                            .months
                            .map(u32::try_from)
                            .transpose()
                            .map_err(|_| corrupt())?,
                        wallet: e.wallet.clone(),
                        note: e.note.clone(),
                    })
                })
                .collect::<Result<_, AppError>>()?,
            talk_this_week: sale.review_week.as_deref() == Some(week),
        })
    }

    /// Nasiya daftari: ochiq nasiyalar (eng ko'p kechikkani birinchi), keyin yopilganlar; yosh guruhlari.
    pub fn kk_credit_book(&self, space_id: &str) -> Result<KkCreditBookDto, AppError> {
        let ctx = self.ctx()?;
        let scope = self.kk_scope(&ctx, space_id)?;
        let today = self.today(&ctx);
        let week = ymd(week_start(today, WEEK_ANCHOR));
        let customers = self.db.read(|c| kk_ledger::customers(c, &scope))?;
        let mut states = self.kk_credit_states(&ctx, &scope, today)?;
        let a = aging(
            ctx.currency,
            &states.iter().map(|(_, _, s)| s).collect::<Vec<_>>(),
        )?;
        states.sort_by(|x, y| {
            let settled = |s: &CreditState| s.outstanding.is_zero();
            settled(&x.2)
                .cmp(&settled(&y.2))
                .then(y.2.overdue_days.cmp(&x.2.overdue_days))
                .then(x.0.sold_on.cmp(&y.0.sold_on))
        });
        let d = |m: Money| self.money_dto(&ctx, m);
        Ok(KkCreditBookDto {
            sales: states
                .iter()
                .map(|(s, e, st)| self.sale_dto(&ctx, s, e, st, &customers, &week))
                .collect::<Result<_, _>>()?,
            aging: KkAgingDto {
                current: d(a.current),
                d1_30: d(a.overdue[0]),
                d31_60: d(a.overdue[1]),
                d61_90: d(a.overdue[2]),
                d90_plus: d(a.overdue[3]),
                total: d(a.total),
            },
            week_start: week,
        })
    }

    /// Mijozlar va ularning nasiya qoldig'i.
    pub fn kk_customers(&self, space_id: &str) -> Result<Vec<KkCustomerDto>, AppError> {
        let ctx = self.ctx()?;
        let scope = self.kk_scope(&ctx, space_id)?;
        let states = self.kk_credit_states(&ctx, &scope, self.today(&ctx))?;
        let mut out = Vec::new();
        for c in self.db.read(|c| kk_ledger::customers(c, &scope))? {
            let mine: Vec<_> = states
                .iter()
                .filter(|(s, _, st)| s.customer_id == c.id && !st.outstanding.is_zero())
                .collect();
            let total = mine
                .iter()
                .try_fold(Money::zero(ctx.currency), |acc, (_, _, st)| {
                    acc.checked_add(st.outstanding)
                })?;
            out.push(KkCustomerDto {
                id: c.id,
                name: c.name,
                phone: c.phone,
                note: c.note,
                outstanding: self.money_dto(&ctx, total),
                open_sales: u32::try_from(mine.len()).unwrap_or(u32::MAX),
            });
        }
        Ok(out)
    }

    /// Mijoz (OQ-Y3): telefon ixtiyoriy, saqlansa — rozilik belgisi shart.
    pub fn kk_add_customer(
        &self,
        space_id: &str,
        input: KkCustomerInput,
    ) -> Result<Vec<KkCustomerDto>, AppError> {
        let ctx = self.ctx()?;
        let scope = self.kk_scope(&ctx, space_id)?;
        let name = required(&input.name, "name")?;
        if name.chars().count() > 100 {
            return Err(AppError::on("TOO_LONG", "name"));
        }
        let phone = clean_opt(input.phone.as_deref());
        if phone.is_some() && !input.phone_consent {
            return Err(AppError::on("PHONE_CONSENT_REQUIRED", "phoneConsent"));
        }
        let row = kk_ledger::KkCustomerRow {
            id: self.new_id(),
            name,
            phone_consent: phone.is_some() && input.phone_consent,
            phone,
            note: clean_opt(input.note.as_deref()),
        };
        let meta = self.meta();
        self.db
            .write(|tx| kk_ledger::insert_customer(tx, &scope, &row, &meta))?;
        self.publish(Some(space_id), &[Topic::Kasbkor]);
        self.kk_customers(space_id)
    }

    /// Nasiya (SPEC 5.2): narx va jadval qotiriladi. Savdo paytida tushum yo'q — to'lovlar tushum.
    pub fn kk_add_credit_sale(
        &self,
        space_id: &str,
        input: KkCreditSaleInput,
    ) -> Result<KkCreditBookDto, AppError> {
        let ctx = self.ctx()?;
        let scope = self.kk_scope(&ctx, space_id)?;
        if self
            .db
            .read(|c| kk_ledger::customer_name(c, &scope, &input.customer_id))?
            .is_none()
        {
            return Err(AppError::on("NOT_FOUND", "customerId"));
        }
        let item = required(&input.item, "item")?;
        if item.chars().count() > 200 {
            return Err(AppError::on("TOO_LONG", "item"));
        }
        let credit_price = positive(&ctx, &input.credit_price, "creditPrice")?;
        let cash_price = amount_opt(&ctx, input.cash_price.as_deref(), "cashPrice")?;
        let sold_on = self.date_or_today(&ctx, input.sold_on.as_deref(), "soldOn")?;
        let first_due = match input.first_due.as_deref().filter(|t| !t.trim().is_empty()) {
            Some(d) => parse_date(d, "firstDue")?,
            None => sold_on
                .checked_add_months(Months::new(1))
                .ok_or(AppError::on("INVALID_DATE", "firstDue"))?,
        };
        if first_due < sold_on {
            return Err(AppError::on("INVALID_DATE", "firstDue"));
        }
        CreditTerms {
            credit_price,
            cash_price,
            installments: input.installments,
            first_due,
        }
        .validate()?;
        let row = kk_ledger::KkCreditSaleRow {
            id: self.new_id(),
            customer_id: input.customer_id,
            item,
            currency: ctx.currency.code().to_string(),
            cash_price_minor: cash_price.map(|m| m.minor()),
            credit_price_minor: credit_price.minor(),
            installments: i64::from(input.installments),
            sold_on: ymd(sold_on),
            first_due: ymd(first_due),
            witness: clean_opt(input.witness.as_deref()),
            note: clean_opt(input.note.as_deref()),
            review_week: None,
        };
        let meta = self.meta();
        self.db
            .write(|tx| kk_ledger::insert_credit_sale(tx, &scope, &row, &meta))?;
        self.publish(Some(space_id), &[Topic::Kasbkor]);
        self.kk_credit_book(space_id)
    }

    /// Yangi hodisani domen orqali tekshiradi (sana tartibi, qoldiqdan oshmaslik) va qaytaradi.
    fn credit_check(
        &self,
        ctx: &Ctx,
        scope: &SpaceScope,
        sale_id: &str,
        event: CreditEvent,
    ) -> Result<(kk_ledger::KkCreditSaleRow, CreditState), AppError> {
        let sale = self
            .db
            .read(|c| kk_ledger::credit_sales(c, scope))?
            .into_iter()
            .find(|s| s.id == sale_id)
            .ok_or(AppError::on("NOT_FOUND", "saleId"))?;
        if ymd(event.on()) < sale.sold_on {
            return Err(AppError::on("INVALID_DATE", "date"));
        }
        let rows: Vec<_> = self
            .db
            .read(|c| kk_ledger::credit_events(c, scope))?
            .into_iter()
            .filter(|e| e.sale_id == sale_id)
            .collect();
        let mut events = to_events(ctx, &rows)?;
        events.push(event);
        let st = self
            .credit_terms(ctx, &sale)?
            .state(&events, self.today(ctx))?;
        Ok((sale, st))
    }

    /// To'lov: nasiya hodisasi va Kasb-kor tushumi bitta tranzaksiyada.
    pub fn kk_credit_payment(
        &self,
        space_id: &str,
        sale_id: &str,
        input: KkCreditPaymentInput,
    ) -> Result<KkCreditBookDto, AppError> {
        let ctx = self.ctx()?;
        let scope = self.kk_scope(&ctx, space_id)?;
        let amount = positive(&ctx, &input.amount, "amount")?;
        let w = wallet(&input.wallet, "wallet")?;
        let on = self.date_or_today(&ctx, input.paid_on.as_deref(), "paidOn")?;
        self.kk_ensure_open(&scope, &ymd(on), "paidOn")?;
        self.kk_ensure_cash_open(&scope, &ymd(on), w.as_str() == "CASH")?;
        let (sale, _) =
            self.credit_check(&ctx, &scope, sale_id, CreditEvent::Payment { on, amount })?;
        let name = self
            .db
            .read(|c| kk_ledger::customer_name(c, &scope, &sale.customer_id))?
            .unwrap_or_default();
        let income = incomes::IncomeRow {
            id: self.new_id(),
            member_id: None,
            amount_minor: amount.minor(),
            currency: ctx.currency.code().to_string(),
            source: format!("{name}: {}", sale.item),
            channel: w.as_str().to_string(),
            source_type: None,
            occurred_on: ymd(on),
            note: None,
        };
        let event = kk_ledger::KkCreditEventRow {
            id: self.new_id(),
            sale_id: sale_id.to_string(),
            kind: "PAYMENT".to_string(),
            occurred_on: ymd(on),
            amount_minor: Some(amount.minor()),
            months: None,
            wallet: Some(w.as_str().to_string()),
            income_id: Some(income.id.clone()),
            note: clean_opt(input.note.as_deref()),
        };
        let meta = self.meta();
        self.db.write(|tx| {
            incomes::insert(tx, &scope, &income, &meta)?;
            kk_ledger::insert_credit_event(tx, &scope, &event, &meta)
        })?;
        self.publish(Some(space_id), &[Topic::Incomes, Topic::Kasbkor]);
        self.kk_credit_book(space_id)
    }

    /// Kechirish (to'liq yoki qisman). Summa bo'lmasa — butun qoldiq.
    pub fn kk_credit_forgive(
        &self,
        space_id: &str,
        sale_id: &str,
        input: KkCreditForgiveInput,
    ) -> Result<KkCreditBookDto, AppError> {
        let ctx = self.ctx()?;
        let scope = self.kk_scope(&ctx, space_id)?;
        let on = self.date_or_today(&ctx, input.on.as_deref(), "on")?;
        let amount = match amount_opt(&ctx, input.amount.as_deref(), "amount")? {
            Some(a) => a,
            None => {
                let st = self
                    .kk_credit_states(&ctx, &scope, on)?
                    .into_iter()
                    .find(|(s, _, _)| s.id == sale_id)
                    .ok_or(AppError::on("NOT_FOUND", "saleId"))?
                    .2;
                if st.outstanding.is_zero() {
                    return Err(AppError::new("ALREADY_SETTLED"));
                }
                st.outstanding
            }
        };
        self.credit_check(&ctx, &scope, sale_id, CreditEvent::Forgive { on, amount })?;
        self.credit_event(
            space_id,
            &scope,
            sale_id,
            "FORGIVE",
            on,
            Some(amount.minor()),
            None,
            input.note.as_deref(),
        )
    }

    /// Muddatni uzaytirish: yopilmagan to'lovlar `months` oyga suriladi, narx o'zgarmaydi.
    pub fn kk_credit_extend(
        &self,
        space_id: &str,
        sale_id: &str,
        input: KkCreditExtendInput,
    ) -> Result<KkCreditBookDto, AppError> {
        let ctx = self.ctx()?;
        let scope = self.kk_scope(&ctx, space_id)?;
        let on = self.date_or_today(&ctx, input.on.as_deref(), "on")?;
        self.credit_check(
            &ctx,
            &scope,
            sale_id,
            CreditEvent::Extend {
                on,
                months: input.months,
            },
        )?;
        self.credit_event(
            space_id,
            &scope,
            sale_id,
            "EXTEND",
            on,
            None,
            Some(i64::from(input.months)),
            input.note.as_deref(),
        )
    }

    #[allow(clippy::too_many_arguments)]
    fn credit_event(
        &self,
        space_id: &str,
        scope: &SpaceScope,
        sale_id: &str,
        kind: &str,
        on: NaiveDate,
        amount_minor: Option<i64>,
        months: Option<i64>,
        note: Option<&str>,
    ) -> Result<KkCreditBookDto, AppError> {
        let row = kk_ledger::KkCreditEventRow {
            id: self.new_id(),
            sale_id: sale_id.to_string(),
            kind: kind.to_string(),
            occurred_on: ymd(on),
            amount_minor,
            months,
            wallet: None,
            income_id: None,
            note: clean_opt(note),
        };
        let meta = self.meta();
        self.db
            .write(|tx| kk_ledger::insert_credit_event(tx, scope, &row, &meta))?;
        self.publish(Some(space_id), &[Topic::Kasbkor]);
        self.kk_credit_book(space_id)
    }

    /// «Bu hafta kim bilan gaplashaman» belgisi (haftalik ko'rik, juma).
    pub fn kk_credit_mark(
        &self,
        space_id: &str,
        sale_id: &str,
        talk: bool,
    ) -> Result<KkCreditBookDto, AppError> {
        let ctx = self.ctx()?;
        let scope = self.kk_scope(&ctx, space_id)?;
        let week = ymd(week_start(self.today(&ctx), WEEK_ANCHOR));
        let meta = self.meta();
        self.db.write(|tx| {
            kk_ledger::set_review_week(tx, &scope, sale_id, talk.then_some(week.as_str()), &meta)
        })?;
        self.publish(Some(space_id), &[Topic::Kasbkor]);
        self.kk_credit_book(space_id)
    }

    /// Xato kiritilgan nasiyani o'chirish — faqat hodisasi (to'lov va h.k.) bo'lmasa.
    pub fn kk_delete_credit_sale(
        &self,
        space_id: &str,
        sale_id: &str,
    ) -> Result<KkCreditBookDto, AppError> {
        let ctx = self.ctx()?;
        let scope = self.kk_scope(&ctx, space_id)?;
        let meta = self.meta();
        self.db
            .write(|tx| kk_ledger::delete_credit_sale(tx, &scope, sale_id, &meta))
            .map_err(|_| AppError::on("CREDIT_HAS_EVENTS", "saleId"))?;
        self.publish(Some(space_id), &[Topic::Kasbkor]);
        self.kk_credit_book(space_id)
    }
}

fn to_events(
    ctx: &Ctx,
    rows: &[kk_ledger::KkCreditEventRow],
) -> Result<Vec<CreditEvent>, AppError> {
    rows.iter()
        .map(|e| {
            let on = parse_date(&e.occurred_on, "date").map_err(|_| corrupt())?;
            let amount = || {
                e.amount_minor
                    .map(|m| Money::new(m, ctx.currency))
                    .ok_or_else(corrupt)
            };
            Ok(match e.kind.as_str() {
                "PAYMENT" => CreditEvent::Payment {
                    on,
                    amount: amount()?,
                },
                "FORGIVE" => CreditEvent::Forgive {
                    on,
                    amount: amount()?,
                },
                "EXTEND" => CreditEvent::Extend {
                    on,
                    months: e
                        .months
                        .and_then(|m| u32::try_from(m).ok())
                        .ok_or_else(corrupt)?,
                },
                _ => return Err(corrupt()),
            })
        })
        .collect()
}
