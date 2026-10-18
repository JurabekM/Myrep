//! K6 — Kasb-kor «Kelishuvni yozing» (`docs/kasbkor/SPEC.md` 7): xodim (`EMPLOYMENT`) va ta'minotchi
//! (`SUPPLY`) kelishuvlari, imzolangan versiyalar, avans (foizsiz, jarimasiz) va haq to'lovlari, oylik
//! hisob varaqchasi, yetkazish va ta'minotchiga qarz.
//!
//! Hisob `domain-kasbkor::{payroll, supply, terms}` da (vektorlar `kk_payroll`, `kk_supplier_balance`).
//! Pul naqd asosida: avans va haq to'lovi — Kasb-kor chiqimi (`category.kk.wages`); tovar bog'langan
//! ta'minotda yetkazish — hamyonsiz xarid (tannarx sotilganda), to'lov — tovar xaridi kabi; tovarsiz
//! ta'minotda to'lov — chiqim (`category.kk.materials`).
use std::sync::OnceLock;

use baraka_domain_common::month_period;
use baraka_domain_kasbkor::payroll::{payroll, Advance, PayMonth, Payroll};
use baraka_domain_kasbkor::stock::replacement;
use baraka_domain_kasbkor::supply::{supplier_balance, Delivery, SupplierBalance, SupplyPayment};
use baraka_domain_kasbkor::terms::{EmploymentTerms, SupplyTerms};
use baraka_money::{parse_amount, Money};
use baraka_pdf::{KkAgreementDoc, KkClauseLine, KkPayslip};
use baraka_storage::repo::{categories, expenses, household, kk_staff, kk_stock};
use baraka_storage::SpaceScope;
use chrono::{Months, NaiveDate};
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};

use crate::app::Ctx;
use crate::events::Topic;
use crate::kasbkor::wallet;
use crate::kasbkor_stock::{factor, parse_qty, show_qty};
use crate::partnership::engine;
use crate::receipt::{pdf_locale, ymd};
use crate::text::{clean_opt, required};
use crate::uy::positive;
use crate::venture::show;
use crate::*;

const EMPLOYMENT: &str = "EMPLOYMENT";
const SUPPLY: &str = "SUPPLY";
const DRAFT: &str = "DRAFT";
const SIGNED: &str = "SIGNED";
const ENDED: &str = "ENDED";
const WAGES_KEY: &str = "category.kk.wages";
const MATERIALS_KEY: &str = "category.kk.materials";
const DEFAULT_MAX_INSTALLMENTS: u32 = 3;

/// Kelishuv shabloni (`shared/content/templates`): bandlar tartibi va `reviewStatus`.
#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
pub(crate) struct Template {
    pub version: u32,
    pub review_status: String,
    pub clauses: Vec<TemplateClause>,
    pub disclaimer: String,
}

#[derive(Debug, Deserialize)]
pub(crate) struct TemplateClause {
    pub n: u32,
    pub label: String,
    pub text: String,
}

const EMPLOYMENT_TEMPLATE: &str =
    include_str!("../../../../shared/content/templates/kk_employment.json");
const SUPPLY_TEMPLATE: &str = include_str!("../../../../shared/content/templates/kk_supply.json");

pub(crate) fn template(kind: &str) -> Result<&'static Template, AppError> {
    static EMP: OnceLock<Option<Template>> = OnceLock::new();
    static SUP: OnceLock<Option<Template>> = OnceLock::new();
    let (cell, raw) = if kind == EMPLOYMENT {
        (&EMP, EMPLOYMENT_TEMPLATE)
    } else {
        (&SUP, SUPPLY_TEMPLATE)
    };
    cell.get_or_init(|| serde_json::from_str(raw).ok())
        .as_ref()
        .ok_or(AppError::new("CORRUPT_TEMPLATE"))
}

/// Xodim kelishuvi shartlari (`terms_json`). Maydon tartibi barqaror — xesh shu matndan.
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
struct EmploymentP {
    v: u32,
    name: String,
    role: Option<String>,
    duties: Option<String>,
    hours: Option<String>,
    salary: i64,
    pay_day: u32,
    notice_days: u32,
    max_advance: Option<i64>,
    max_installments: u32,
    arbiter: Option<String>,
    review_on: String,
    note: Option<String>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
struct SupplyP {
    v: u32,
    name: String,
    goods: Option<String>,
    item_id: Option<String>,
    unit_price: Option<i64>,
    payment_days: u32,
    delivery: Option<String>,
    returns: Option<String>,
    arbiter: Option<String>,
    review_on: String,
    note: Option<String>,
}

impl EmploymentP {
    fn terms(&self, ctx: &Ctx) -> EmploymentTerms {
        EmploymentTerms {
            salary: Money::new(self.salary, ctx.currency),
            pay_day: self.pay_day,
            notice_days: self.notice_days,
            max_advance: self.max_advance.map(|m| Money::new(m, ctx.currency)),
            max_advance_installments: self.max_installments,
        }
    }
}

fn corrupt() -> AppError {
    AppError::new("CORRUPT_ROW")
}

fn parse_day(s: &str, field: &str) -> Result<NaiveDate, AppError> {
    NaiveDate::parse_from_str(s, "%Y-%m-%d").map_err(|_| AppError::on("INVALID_DATE", field))
}

fn terms_hash(json: &str, kind: &str, template_version: u32) -> String {
    let mut h = Sha256::new();
    h.update(format!("{kind}:{template_version}\n").as_bytes());
    h.update(json.as_bytes());
    h.finalize().iter().map(|b| format!("{b:02x}")).collect()
}

fn opt_amount(ctx: &Ctx, s: Option<&str>, field: &str) -> Result<Option<Money>, AppError> {
    match s.map(str::trim).filter(|t| !t.is_empty()) {
        None => Ok(None),
        Some(t) => Ok(Some(positive(ctx, t, field)?)),
    }
}

fn phone(p: Option<&str>, consent: bool) -> Result<Option<String>, AppError> {
    let p = clean_opt(p);
    if p.is_some() && !consent {
        return Err(AppError::on("PHONE_CONSENT_REQUIRED", "phoneConsent"));
    }
    Ok(p)
}

/// Bir kelishuvning yig'ilgan holati.
struct Agreement {
    row: kk_staff::KkAgreementRow,
    versions: Vec<kk_staff::KkAgreementVersionRow>,
}

impl Agreement {
    fn last_signed(&self) -> Option<&kk_staff::KkAgreementVersionRow> {
        self.versions.last()
    }
}

impl App {
    fn kk_agreements(
        &self,
        scope: &SpaceScope,
        kind: &str,
        currency: &str,
    ) -> Result<Vec<Agreement>, AppError> {
        let versions = self.db.read(|c| kk_staff::versions(c, scope))?;
        Ok(self
            .db
            .read(|c| kk_staff::agreements(c, scope))?
            .into_iter()
            .filter(|r| r.kind == kind && r.currency == currency)
            .map(|row| Agreement {
                versions: versions
                    .iter()
                    .filter(|v| v.agreement_id == row.id)
                    .cloned()
                    .collect(),
                row,
            })
            .collect())
    }

    fn kk_agreement(
        &self,
        ctx: &Ctx,
        scope: &SpaceScope,
        id: &str,
        kind: &str,
    ) -> Result<Agreement, AppError> {
        self.kk_agreements(scope, kind, ctx.currency.code())?
            .into_iter()
            .find(|a| a.row.id == id)
            .ok_or(AppError::on("NOT_FOUND", "id"))
    }

    fn state_dto(
        &self,
        a: &Agreement,
        missing: Vec<String>,
        review_on: &str,
    ) -> Result<KkAgreementStateDto, AppError> {
        let t = template(&a.row.kind)?;
        let last = a.last_signed();
        let unsigned_changes = last.is_none_or(|v| v.terms_json != a.row.terms_json);
        Ok(KkAgreementStateDto {
            status: a.row.status.clone(),
            signed_versions: u32::try_from(a.versions.len()).map_err(|_| corrupt())?,
            signed_on: last.map(|v| v.signed_on.clone()),
            effective_from: last.map(|v| v.effective_from.clone()),
            unsigned_changes,
            can_sign: missing.is_empty() && unsigned_changes && a.row.status != ENDED,
            missing,
            template_version: t.version,
            template_review: t.review_status.clone(),
            started_on: a.row.started_on.clone(),
            ended_on: a.row.ended_on.clone(),
            review_on: review_on.to_string(),
        })
    }

    fn category_id(&self, scope: &SpaceScope, key: &str) -> Result<String, AppError> {
        self.db
            .read(|c| categories::list(c, scope))?
            .into_iter()
            .find(|c| c.name_key == key)
            .map(|c| c.id)
            .ok_or(AppError::new("CATEGORY_MISSING"))
    }

    fn expense_row(
        &self,
        ctx: &Ctx,
        category_id: &str,
        amount: Money,
        wallet: &str,
        on: &str,
        note: Option<String>,
    ) -> expenses::ExpenseRow {
        expenses::ExpenseRow {
            id: self.new_id(),
            category_id: category_id.to_string(),
            member_id: None,
            amount_minor: amount.minor(),
            currency: ctx.currency.code().to_string(),
            channel: wallet.to_string(),
            occurred_on: on.to_string(),
            necessity: None,
            obligation_id: None,
            is_gift: false,
            is_ostentation: false,
            funded_by_debt: false,
            note,
        }
    }

    fn review_default(
        &self,
        started: NaiveDate,
        review_on: Option<&str>,
    ) -> Result<String, AppError> {
        match clean_opt(review_on) {
            Some(d) => Ok(ymd(parse_day(&d, "reviewOn")?)),
            None => Ok(ymd(started
                .checked_add_months(Months::new(12))
                .ok_or(AppError::new("INVALID_DATE"))?)),
        }
    }

    // ---- xodimlar ----

    fn employment_p(
        &self,
        ctx: &Ctx,
        input: &KkEmployeeInput,
        started: NaiveDate,
    ) -> Result<EmploymentP, AppError> {
        let name = required(&input.name, "name")?;
        if name.chars().count() > 100 {
            return Err(AppError::on("TOO_LONG", "name"));
        }
        let p = EmploymentP {
            v: 1,
            name,
            role: clean_opt(input.role.as_deref()),
            duties: clean_opt(input.duties.as_deref()),
            hours: clean_opt(input.hours.as_deref()),
            salary: positive(ctx, &input.salary, "salary")?.minor(),
            pay_day: input.pay_day,
            notice_days: input.notice_days,
            max_advance: opt_amount(ctx, input.max_advance.as_deref(), "maxAdvance")?
                .map(|m| m.minor()),
            max_installments: input
                .max_advance_installments
                .unwrap_or(DEFAULT_MAX_INSTALLMENTS),
            arbiter: clean_opt(input.arbiter.as_deref()),
            review_on: self.review_default(started, input.review_on.as_deref())?,
            note: clean_opt(input.note.as_deref()),
        };
        p.terms(ctx).validate()?;
        Ok(p)
    }

    fn opening(&self, ctx: &Ctx, s: Option<&str>) -> Result<i64, AppError> {
        match s.map(str::trim).filter(|t| !t.is_empty()) {
            None => Ok(0),
            Some(t) => Ok(parse_amount(t, ctx.currency)
                .map_err(|e| AppError::on(e.code(), "openingBalance"))?
                .minor()),
        }
    }

    pub fn kk_add_employee(
        &self,
        space_id: &str,
        input: KkEmployeeInput,
    ) -> Result<KkStaffDto, AppError> {
        let ctx = self.ctx()?;
        let scope = self.kk_scope(&ctx, space_id)?;
        let started = self.date_or_today(&ctx, input.started_on.as_deref(), "startedOn")?;
        let p = self.employment_p(&ctx, &input, started)?;
        let row = kk_staff::KkAgreementRow {
            id: self.new_id(),
            kind: EMPLOYMENT.into(),
            party_name: p.name.clone(),
            phone: phone(input.phone.as_deref(), input.phone_consent)?,
            phone_consent: input.phone_consent,
            status: DRAFT.into(),
            currency: ctx.currency.code().to_string(),
            terms_json: serde_json::to_string(&p).map_err(|_| corrupt())?,
            started_on: ymd(started),
            ended_on: None,
            opening_balance_minor: self.opening(&ctx, input.opening_balance.as_deref())?,
        };
        let meta = self.meta();
        self.db
            .write(|tx| kk_staff::insert_agreement(tx, &scope, &row, &meta))?;
        self.publish(Some(space_id), &[Topic::Kasbkor]);
        self.kk_staff(space_id)
    }

    /// Shartlar o'zgarsa — imzolangan versiya o'z holicha qoladi, yangisi imzolanguncha eski shartlar amal qiladi.
    pub fn kk_update_employee(
        &self,
        space_id: &str,
        id: &str,
        input: KkEmployeeInput,
    ) -> Result<KkStaffDto, AppError> {
        let ctx = self.ctx()?;
        let scope = self.kk_scope(&ctx, space_id)?;
        let a = self.kk_agreement(&ctx, &scope, id, EMPLOYMENT)?;
        if a.row.status == ENDED {
            return Err(AppError::on("AGREEMENT_ENDED", "id"));
        }
        let started = match (&input.started_on, a.versions.is_empty()) {
            (Some(s), true) => self.date_or_today(&ctx, Some(s), "startedOn")?,
            _ => parse_day(&a.row.started_on, "startedOn")?,
        };
        let p = self.employment_p(&ctx, &input, started)?;
        let mut row = a.row.clone();
        row.party_name.clone_from(&p.name);
        row.phone = phone(input.phone.as_deref(), input.phone_consent)?;
        row.phone_consent = input.phone_consent;
        row.terms_json = serde_json::to_string(&p).map_err(|_| corrupt())?;
        row.started_on = ymd(started);
        row.opening_balance_minor = self.opening(&ctx, input.opening_balance.as_deref())?;
        let meta = self.meta();
        self.db
            .write(|tx| kk_staff::update_agreement(tx, &scope, &row, &meta))?;
        self.publish(Some(space_id), &[Topic::Kasbkor]);
        self.kk_staff(space_id)
    }

    /// Xodim oylari: ishga kirgan oydan bugungi (yoki oxirgi hodisa) oyigacha davrlar.
    fn employee_payroll(
        &self,
        ctx: &Ctx,
        a: &Agreement,
        events: &[kk_staff::KkStaffEventRow],
        until: NaiveDate,
    ) -> Result<(Vec<(NaiveDate, NaiveDate)>, Payroll), AppError> {
        let cur = ctx.currency;
        let started = parse_day(&a.row.started_on, "startedOn")?;
        let ended = a
            .row
            .ended_on
            .as_deref()
            .map(|d| parse_day(d, "endedOn"))
            .transpose()?;
        let last_event = events
            .iter()
            .filter_map(|e| parse_day(&e.occurred_on, "occurredOn").ok())
            .max();
        let until = last_event.map_or(until, |d| d.max(until));
        let mut periods = Vec::new();
        let (mut s, mut e) =
            month_period(started, ctx.month_start_day).ok_or(AppError::new("INVALID_PERIOD"))?;
        loop {
            periods.push((s, e));
            if e > until || periods.len() > 1200 {
                break;
            }
            (s, e) = month_period(e, ctx.month_start_day).ok_or(AppError::new("INVALID_PERIOD"))?;
        }
        let index = |d: NaiveDate| periods.iter().position(|(s, e)| d >= *s && d < *e);
        let mut months = Vec::with_capacity(periods.len());
        for (s, e) in &periods {
            let last = e.pred_opt().ok_or(AppError::new("INVALID_PERIOD"))?;
            let terms = a
                .versions
                .iter()
                .rfind(|v| v.effective_from.as_str() <= ymd(last).as_str());
            let working = ended.is_none_or(|d| d >= *s);
            let salary = match (terms, working) {
                (Some(v), true) => {
                    let p: EmploymentP =
                        serde_json::from_str(&v.terms_json).map_err(|_| corrupt())?;
                    Money::new(p.salary, cur)
                }
                _ => Money::zero(cur),
            };
            let paid = events
                .iter()
                .filter(|ev| {
                    ev.kind == "WAGE"
                        && ev.occurred_on.as_str() >= ymd(*s).as_str()
                        && ev.occurred_on.as_str() < ymd(*e).as_str()
                })
                .map(|ev| Money::new(ev.amount_minor, cur))
                .collect();
            months.push(PayMonth { salary, paid });
        }
        let mut advances = Vec::new();
        for ev in events.iter().filter(|e| e.kind == "ADVANCE") {
            let given = index(parse_day(&ev.occurred_on, "occurredOn")?).ok_or_else(corrupt)?;
            let start_on = parse_day(ev.start_month.as_deref().unwrap_or_default(), "startOn")?;
            let start = match index(start_on) {
                Some(i) => i,
                // Ushlash hali kelmagan oydan boshlanadi.
                None => periods.len() + months_between(periods.last().map(|p| p.1), start_on, ctx)?,
            };
            advances.push(Advance {
                id: ev.id.clone(),
                month: u32::try_from(given).map_err(|_| corrupt())?,
                amount: Money::new(ev.amount_minor, cur),
                installments: u32::try_from(ev.installments.unwrap_or(1)).map_err(|_| corrupt())?,
                start_month: u32::try_from(start).map_err(|_| corrupt())?,
            });
        }
        let r = payroll(
            cur,
            &months,
            &advances,
            Money::new(a.row.opening_balance_minor, cur),
        )?;
        Ok((periods, r))
    }

    fn employee_dto(
        &self,
        ctx: &Ctx,
        a: &Agreement,
        events: &[kk_staff::KkStaffEventRow],
    ) -> Result<KkEmployeeDto, AppError> {
        let cur = ctx.currency;
        let d = |m: Money| self.money_dto(ctx, m);
        let p: EmploymentP = serde_json::from_str(&a.row.terms_json).map_err(|_| corrupt())?;
        let mut missing = Vec::new();
        if p.role.is_none() {
            missing.push("role".to_string());
        }
        if p.duties.is_none() {
            missing.push("duties".to_string());
        }
        let today = self.today(ctx);
        let (periods, r) = self.employee_payroll(ctx, a, events, today)?;
        let mut months = Vec::new();
        for ((s, e), m) in periods.iter().zip(&r.months) {
            months.push(KkPayMonthDto {
                period_start: ymd(*s),
                period_end: ymd(e.pred_opt().ok_or(AppError::new("INVALID_PERIOD"))?),
                salary: d(m.salary),
                deducted: d(m.deducted),
                net: d(m.net),
                paid: d(m.paid),
                balance: d(m.balance),
            });
        }
        let balance = r
            .months
            .last()
            .map_or(Money::new(a.row.opening_balance_minor, cur), |m| m.balance);
        let due_now = due_at(&periods, &r, today)?;
        let mut outstanding = Money::zero(cur);
        let mut advances = Vec::new();
        for (st, ev) in r
            .advances
            .iter()
            .zip(events.iter().filter(|e| e.kind == "ADVANCE"))
        {
            outstanding = outstanding.checked_add(st.outstanding)?;
            advances.push(KkAdvanceDto {
                id: ev.id.clone(),
                given_on: ev.occurred_on.clone(),
                amount: d(Money::new(ev.amount_minor, cur)),
                installments: u32::try_from(ev.installments.unwrap_or(1)).map_err(|_| corrupt())?,
                schedule: st
                    .schedule
                    .iter()
                    .map(|(mo, x)| {
                        Ok(KkNextDueDto {
                            date: ymd(period_start(ctx, &periods, *mo)?),
                            amount: d(*x),
                        })
                    })
                    .collect::<Result<_, AppError>>()?,
                deducted: d(st.deducted),
                outstanding: d(st.outstanding),
            });
        }
        advances.reverse();
        months.reverse();
        Ok(KkEmployeeDto {
            id: a.row.id.clone(),
            name: a.row.party_name.clone(),
            phone: a.row.phone.clone(),
            agreement: self.state_dto(a, missing, &p.review_on)?,
            terms: KkEmployeeTermsDto {
                role: p.role.clone(),
                duties: p.duties.clone(),
                hours: p.hours.clone(),
                salary: d(Money::new(p.salary, cur)),
                pay_day: p.pay_day,
                notice_days: p.notice_days,
                max_advance: p.max_advance.map(|m| d(Money::new(m, cur))),
                max_advance_installments: p.max_installments,
                opening_balance: d(Money::new(a.row.opening_balance_minor, cur)),
                arbiter: p.arbiter.clone(),
                note: p.note.clone(),
            },
            balance: d(balance),
            due_now: d(due_now),
            advances_outstanding: d(outstanding),
            months,
            advances,
            events: events
                .iter()
                .rev()
                .map(|e| KkStaffEventDto {
                    id: e.id.clone(),
                    kind: e.kind.clone(),
                    occurred_on: e.occurred_on.clone(),
                    amount: d(Money::new(e.amount_minor, cur)),
                    wallet: e.wallet.clone(),
                    note: e.note.clone(),
                })
                .collect(),
        })
    }

    pub fn kk_staff(&self, space_id: &str) -> Result<KkStaffDto, AppError> {
        let ctx = self.ctx()?;
        let scope = self.kk_scope(&ctx, space_id)?;
        let (employees, owed, advances) = self.kk_staff_summary(&ctx, &scope)?;
        Ok(KkStaffDto {
            employees,
            owed: self.money_dto(&ctx, owed),
            advances_outstanding: self.money_dto(&ctx, advances),
            template_review: template(EMPLOYMENT)?.review_status.clone(),
        })
    }

    /// (xodimlar, ularga qarzimiz, ushlanmagan avanslar) — bosh sahifa uchun ham.
    pub(crate) fn kk_staff_summary(
        &self,
        ctx: &Ctx,
        scope: &SpaceScope,
    ) -> Result<(Vec<KkEmployeeDto>, Money, Money), AppError> {
        let cur = ctx.currency;
        let events = self.db.read(|c| kk_staff::staff_events(c, scope))?;
        let mut out = Vec::new();
        let (mut owed, mut adv) = (Money::zero(cur), Money::zero(cur));
        for a in self.kk_agreements(scope, EMPLOYMENT, cur.code())? {
            let ev: Vec<_> = events
                .iter()
                .filter(|e| e.agreement_id == a.row.id)
                .cloned()
                .collect();
            let dto = self.employee_dto(ctx, &a, &ev)?;
            let due = Money::new(dto.due_now.minor.parse().map_err(|_| corrupt())?, cur);
            owed = owed.checked_add(due)?;
            adv = adv.checked_add(Money::new(
                dto.advances_outstanding
                    .minor
                    .parse()
                    .map_err(|_| corrupt())?,
                cur,
            ))?;
            out.push(dto);
        }
        Ok((out, owed, adv))
    }

    fn signed_employee(
        &self,
        ctx: &Ctx,
        scope: &SpaceScope,
        id: &str,
    ) -> Result<(Agreement, EmploymentP, Vec<kk_staff::KkStaffEventRow>), AppError> {
        let a = self.kk_agreement(ctx, scope, id, EMPLOYMENT)?;
        let last = a
            .last_signed()
            .ok_or(AppError::on("AGREEMENT_NOT_SIGNED", "id"))?;
        let p: EmploymentP = serde_json::from_str(&last.terms_json).map_err(|_| corrupt())?;
        let events: Vec<_> = self
            .db
            .read(|c| kk_staff::staff_events(c, scope))?
            .into_iter()
            .filter(|e| e.agreement_id == id)
            .collect();
        Ok((a, p, events))
    }

    /// Avans: kelishilgan qoida bo'yicha (qoldiq chegarasi, necha oyda), foizsiz va jarimasiz.
    /// Bitta tranzaksiyada Kasb-kor chiqimi ham yoziladi.
    pub fn kk_staff_advance(
        &self,
        space_id: &str,
        id: &str,
        input: KkAdvanceInput,
    ) -> Result<KkStaffDto, AppError> {
        let ctx = self.ctx()?;
        let scope = self.kk_scope(&ctx, space_id)?;
        let (a, p, events) = self.signed_employee(&ctx, &scope, id)?;
        if a.row.status == ENDED {
            return Err(AppError::on("AGREEMENT_ENDED", "id"));
        }
        let amount = positive(&ctx, &input.amount, "amount")?;
        let w = wallet(&input.wallet, "wallet")?;
        let on = self.date_or_today(&ctx, input.occurred_on.as_deref(), "occurredOn")?;
        if ymd(on) < a.row.started_on {
            return Err(AppError::on("BEFORE_START", "occurredOn"));
        }
        let (given_start, _) =
            month_period(on, ctx.month_start_day).ok_or(AppError::new("INVALID_PERIOD"))?;
        let start = match clean_opt(input.start_on.as_deref()) {
            None => given_start,
            Some(s) => {
                month_period(parse_day(&s, "startOn")?, ctx.month_start_day)
                    .ok_or(AppError::new("INVALID_PERIOD"))?
                    .0
            }
        };
        if start < given_start {
            return Err(AppError::on("INVALID_START", "startOn"));
        }
        let (_, r) = self.employee_payroll(&ctx, &a, &events, on)?;
        let outstanding = r
            .advances
            .iter()
            .try_fold(Money::zero(ctx.currency), |s, x| {
                s.checked_add(x.outstanding)
            })?;
        p.terms(&ctx)
            .check_advance(amount, input.installments, outstanding)?;
        self.kk_ensure_open(&scope, &ymd(on), "occurredOn")?;
        self.kk_ensure_cash_open(&scope, &ymd(on), w.as_str() == "CASH")?;
        let cat = self.category_id(&scope, WAGES_KEY)?;
        let note = clean_opt(input.note.as_deref());
        let exp = self.expense_row(
            &ctx,
            &cat,
            amount,
            w.as_str(),
            &ymd(on),
            Some(a.row.party_name.clone()),
        );
        let ev = kk_staff::KkStaffEventRow {
            id: self.new_id(),
            agreement_id: id.to_string(),
            kind: "ADVANCE".into(),
            occurred_on: ymd(on),
            amount_minor: amount.minor(),
            currency: ctx.currency.code().to_string(),
            installments: Some(i64::from(input.installments)),
            start_month: Some(ymd(start)),
            wallet: w.as_str().to_string(),
            expense_id: exp.id.clone(),
            note,
        };
        // Yangi avans bilan to'liq hisob (domen qoidalari) — saqlashdan oldin.
        let mut check = events.clone();
        check.push(ev.clone());
        self.employee_payroll(&ctx, &a, &check, on)?;
        let meta = self.meta();
        self.db.write(|tx| {
            expenses::insert(tx, &scope, &exp, &meta)?;
            kk_staff::insert_staff_event(tx, &scope, &ev, &meta)
        })?;
        self.publish(Some(space_id), &[Topic::Expenses, Topic::Kasbkor]);
        self.kk_staff(space_id)
    }

    /// Haq to'lovi; summa bo'lmasa — hozirgi qoldiq (xodimga qarzimiz).
    pub fn kk_staff_pay(
        &self,
        space_id: &str,
        id: &str,
        input: KkWageInput,
    ) -> Result<KkStaffDto, AppError> {
        let ctx = self.ctx()?;
        let scope = self.kk_scope(&ctx, space_id)?;
        let (a, _, events) = self.signed_employee(&ctx, &scope, id)?;
        let w = wallet(&input.wallet, "wallet")?;
        let on = self.date_or_today(&ctx, input.occurred_on.as_deref(), "occurredOn")?;
        if ymd(on) < a.row.started_on {
            return Err(AppError::on("BEFORE_START", "occurredOn"));
        }
        let amount = match opt_amount(&ctx, input.amount.as_deref(), "amount")? {
            Some(m) => m,
            None => {
                let (periods, r) = self.employee_payroll(&ctx, &a, &events, on)?;
                let bal = due_at(&periods, &r, on)?;
                if !bal.is_positive() {
                    return Err(AppError::on("NOTHING_OWED", "amount"));
                }
                bal
            }
        };
        self.kk_ensure_open(&scope, &ymd(on), "occurredOn")?;
        self.kk_ensure_cash_open(&scope, &ymd(on), w.as_str() == "CASH")?;
        let cat = self.category_id(&scope, WAGES_KEY)?;
        let exp = self.expense_row(
            &ctx,
            &cat,
            amount,
            w.as_str(),
            &ymd(on),
            Some(a.row.party_name.clone()),
        );
        let ev = kk_staff::KkStaffEventRow {
            id: self.new_id(),
            agreement_id: id.to_string(),
            kind: "WAGE".into(),
            occurred_on: ymd(on),
            amount_minor: amount.minor(),
            currency: ctx.currency.code().to_string(),
            installments: None,
            start_month: None,
            wallet: w.as_str().to_string(),
            expense_id: exp.id.clone(),
            note: clean_opt(input.note.as_deref()),
        };
        let meta = self.meta();
        self.db.write(|tx| {
            expenses::insert(tx, &scope, &exp, &meta)?;
            kk_staff::insert_staff_event(tx, &scope, &ev, &meta)
        })?;
        self.publish(Some(space_id), &[Topic::Expenses, Topic::Kasbkor]);
        self.kk_staff(space_id)
    }

    // ---- imzo, tugatish, o'chirish (ikkala tur uchun) ----

    fn any_agreement(
        &self,
        ctx: &Ctx,
        scope: &SpaceScope,
        id: &str,
    ) -> Result<Agreement, AppError> {
        self.kk_agreement(ctx, scope, id, EMPLOYMENT)
            .or_else(|_| self.kk_agreement(ctx, scope, id, SUPPLY))
    }

    fn missing_of(&self, a: &Agreement) -> Result<Vec<String>, AppError> {
        let mut missing = Vec::new();
        if a.row.kind == EMPLOYMENT {
            let p: EmploymentP = serde_json::from_str(&a.row.terms_json).map_err(|_| corrupt())?;
            if p.role.is_none() {
                missing.push("role".to_string());
            }
            if p.duties.is_none() {
                missing.push("duties".to_string());
            }
        } else {
            let p: SupplyP = serde_json::from_str(&a.row.terms_json).map_err(|_| corrupt())?;
            if p.goods.is_none() && p.item_id.is_none() {
                missing.push("goods".to_string());
            }
        }
        Ok(missing)
    }

    /// Qog'oz nusxa imzolandi: joriy shartlar o'zgarmas versiya sifatida yoziladi (xesh va shablon
    /// versiyasi bilan). Keyingi o'zgarishlar yangi versiya imzolanguncha amal qilmaydi.
    pub fn kk_sign_agreement(
        &self,
        space_id: &str,
        id: &str,
        input: KkSignInput,
    ) -> Result<(), AppError> {
        let ctx = self.ctx()?;
        let scope = self.kk_scope(&ctx, space_id)?;
        let a = self.any_agreement(&ctx, &scope, id)?;
        if a.row.status == ENDED {
            return Err(AppError::on("AGREEMENT_ENDED", "id"));
        }
        if !self.missing_of(&a)?.is_empty() {
            return Err(AppError::on("AGREEMENT_INCOMPLETE", "id"));
        }
        if a.last_signed()
            .is_some_and(|v| v.terms_json == a.row.terms_json)
        {
            return Err(AppError::on("NOTHING_TO_SIGN", "id"));
        }
        let signed = self.date_or_today(&ctx, input.signed_on.as_deref(), "signedOn")?;
        let effective = match clean_opt(input.effective_from.as_deref()) {
            Some(d) => parse_day(&d, "effectiveFrom")?,
            None if a.versions.is_empty() => parse_day(&a.row.started_on, "startedOn")?,
            None => signed,
        };
        if a.last_signed()
            .is_some_and(|v| v.effective_from > ymd(effective))
        {
            return Err(AppError::on("INVALID_DATE", "effectiveFrom"));
        }
        let t = template(&a.row.kind)?;
        let seq = i64::try_from(a.versions.len()).map_err(|_| corrupt())? + 1;
        let v = kk_staff::KkAgreementVersionRow {
            id: self.new_id(),
            agreement_id: id.to_string(),
            seq,
            terms_json: a.row.terms_json.clone(),
            terms_hash: terms_hash(&a.row.terms_json, &a.row.kind, t.version),
            template_version: i64::from(t.version),
            template_review: t.review_status.clone(),
            effective_from: ymd(effective),
            signed_on: ymd(signed),
        };
        let mut row = a.row.clone();
        row.status = SIGNED.into();
        let meta = self.meta();
        self.db.write(|tx| {
            kk_staff::insert_version(tx, &scope, &v, &meta)?;
            kk_staff::update_agreement(tx, &scope, &row, &meta)
        })?;
        self.publish(Some(space_id), &[Topic::Kasbkor]);
        Ok(())
    }

    /// Ajralish yoki ta'minotni to'xtatish: yozuvlar saqlanadi, yangi avans va yetkazish yo'q.
    pub fn kk_end_agreement(
        &self,
        space_id: &str,
        id: &str,
        ended_on: Option<String>,
    ) -> Result<(), AppError> {
        let ctx = self.ctx()?;
        let scope = self.kk_scope(&ctx, space_id)?;
        let a = self.any_agreement(&ctx, &scope, id)?;
        if a.row.status == ENDED {
            return Err(AppError::on("AGREEMENT_ENDED", "id"));
        }
        let on = self.date_or_today(&ctx, ended_on.as_deref(), "endedOn")?;
        if ymd(on) < a.row.started_on {
            return Err(AppError::on("INVALID_DATE", "endedOn"));
        }
        let mut row = a.row.clone();
        row.status = ENDED.into();
        row.ended_on = Some(ymd(on));
        let meta = self.meta();
        self.db
            .write(|tx| kk_staff::update_agreement(tx, &scope, &row, &meta))?;
        self.publish(Some(space_id), &[Topic::Kasbkor]);
        Ok(())
    }

    /// Faqat imzolanmagan va yozuvsiz (adashib qo'shilgan) kelishuv o'chiriladi.
    pub fn kk_delete_agreement(&self, space_id: &str, id: &str) -> Result<(), AppError> {
        let ctx = self.ctx()?;
        let scope = self.kk_scope(&ctx, space_id)?;
        let a = self.any_agreement(&ctx, &scope, id)?;
        if !a.versions.is_empty() {
            return Err(AppError::on("AGREEMENT_SIGNED", "id"));
        }
        let meta = self.meta();
        self.db
            .write(|tx| kk_staff::delete_agreement(tx, &scope, id, &meta))
            .map_err(|_| AppError::on("AGREEMENT_HAS_RECORDS", "id"))?;
        self.publish(Some(space_id), &[Topic::Kasbkor]);
        Ok(())
    }

    // ---- ta'minotchilar ----

    fn supply_p(
        &self,
        ctx: &Ctx,
        scope: &SpaceScope,
        input: &KkSupplierInput,
        started: NaiveDate,
    ) -> Result<SupplyP, AppError> {
        let name = required(&input.name, "name")?;
        if name.chars().count() > 100 {
            return Err(AppError::on("TOO_LONG", "name"));
        }
        let item_id = clean_opt(input.item_id.as_deref());
        if let Some(i) = &item_id {
            let ok = self
                .db
                .read(|c| kk_stock::items(c, scope))?
                .iter()
                .any(|x| &x.id == i && x.currency == ctx.currency.code());
            if !ok {
                return Err(AppError::on("NOT_FOUND", "itemId"));
            }
        }
        let p = SupplyP {
            v: 1,
            name,
            goods: clean_opt(input.goods.as_deref()),
            item_id,
            unit_price: opt_amount(ctx, input.unit_price.as_deref(), "unitPrice")?
                .map(|m| m.minor()),
            payment_days: input.payment_days,
            delivery: clean_opt(input.delivery.as_deref()),
            returns: clean_opt(input.returns.as_deref()),
            arbiter: clean_opt(input.arbiter.as_deref()),
            review_on: self.review_default(started, input.review_on.as_deref())?,
            note: clean_opt(input.note.as_deref()),
        };
        SupplyTerms {
            unit_price: p.unit_price.map(|m| Money::new(m, ctx.currency)),
            payment_days: p.payment_days,
        }
        .validate()?;
        Ok(p)
    }

    pub fn kk_add_supplier(
        &self,
        space_id: &str,
        input: KkSupplierInput,
    ) -> Result<KkSuppliersDto, AppError> {
        let ctx = self.ctx()?;
        let scope = self.kk_scope(&ctx, space_id)?;
        let started = self.date_or_today(&ctx, input.started_on.as_deref(), "startedOn")?;
        let p = self.supply_p(&ctx, &scope, &input, started)?;
        let row = kk_staff::KkAgreementRow {
            id: self.new_id(),
            kind: SUPPLY.into(),
            party_name: p.name.clone(),
            phone: phone(input.phone.as_deref(), input.phone_consent)?,
            phone_consent: input.phone_consent,
            status: DRAFT.into(),
            currency: ctx.currency.code().to_string(),
            terms_json: serde_json::to_string(&p).map_err(|_| corrupt())?,
            started_on: ymd(started),
            ended_on: None,
            opening_balance_minor: 0,
        };
        let meta = self.meta();
        self.db
            .write(|tx| kk_staff::insert_agreement(tx, &scope, &row, &meta))?;
        self.publish(Some(space_id), &[Topic::Kasbkor]);
        self.kk_suppliers(space_id)
    }

    pub fn kk_update_supplier(
        &self,
        space_id: &str,
        id: &str,
        input: KkSupplierInput,
    ) -> Result<KkSuppliersDto, AppError> {
        let ctx = self.ctx()?;
        let scope = self.kk_scope(&ctx, space_id)?;
        let a = self.kk_agreement(&ctx, &scope, id, SUPPLY)?;
        if a.row.status == ENDED {
            return Err(AppError::on("AGREEMENT_ENDED", "id"));
        }
        let started = match (&input.started_on, a.versions.is_empty()) {
            (Some(s), true) => self.date_or_today(&ctx, Some(s), "startedOn")?,
            _ => parse_day(&a.row.started_on, "startedOn")?,
        };
        let p = self.supply_p(&ctx, &scope, &input, started)?;
        let mut row = a.row.clone();
        row.party_name.clone_from(&p.name);
        row.phone = phone(input.phone.as_deref(), input.phone_consent)?;
        row.phone_consent = input.phone_consent;
        row.terms_json = serde_json::to_string(&p).map_err(|_| corrupt())?;
        row.started_on = ymd(started);
        let meta = self.meta();
        self.db
            .write(|tx| kk_staff::update_agreement(tx, &scope, &row, &meta))?;
        self.publish(Some(space_id), &[Topic::Kasbkor]);
        self.kk_suppliers(space_id)
    }

    fn supplier_state(
        &self,
        ctx: &Ctx,
        deliveries: &[kk_staff::KkDeliveryRow],
        payments: &[kk_staff::KkSupplyPaymentRow],
        today: NaiveDate,
    ) -> Result<SupplierBalance, AppError> {
        let cur = ctx.currency;
        let mut ds = Vec::with_capacity(deliveries.len());
        for d in deliveries {
            ds.push(Delivery {
                id: d.id.clone(),
                on: parse_day(&d.delivered_on, "deliveredOn")?,
                amount: Money::new(d.amount_minor, cur),
                due_days: u32::try_from(d.due_days).map_err(|_| corrupt())?,
            });
        }
        let mut ps = Vec::with_capacity(payments.len());
        for p in payments {
            ps.push(SupplyPayment {
                on: parse_day(&p.paid_on, "paidOn")?,
                amount: Money::new(p.amount_minor, cur),
            });
        }
        // Saqlangan tartib: sana bo'yicha (bir kunda — yozilish tartibida).
        ps.sort_by_key(|p| p.on);
        Ok(supplier_balance(cur, &ds, &ps, today)?)
    }

    pub fn kk_suppliers(&self, space_id: &str) -> Result<KkSuppliersDto, AppError> {
        let ctx = self.ctx()?;
        let scope = self.kk_scope(&ctx, space_id)?;
        let (suppliers, outstanding, overdue, soon) = self.kk_suppliers_summary(&ctx, &scope)?;
        let d = |m: Money| self.money_dto(&ctx, m);
        Ok(KkSuppliersDto {
            suppliers,
            outstanding: d(outstanding),
            overdue: d(overdue),
            due_soon: d(soon),
            template_review: template(SUPPLY)?.review_status.clone(),
        })
    }

    /// (ta'minotchilar, qarz, muddati o'tgan, 7 kun ichida) — bosh sahifa uchun ham.
    pub(crate) fn kk_suppliers_summary(
        &self,
        ctx: &Ctx,
        scope: &SpaceScope,
    ) -> Result<(Vec<KkSupplierDto>, Money, Money, Money), AppError> {
        let cur = ctx.currency;
        let d = |m: Money| self.money_dto(ctx, m);
        let today = self.today(ctx);
        let deliveries = self.db.read(|c| kk_staff::deliveries(c, scope))?;
        let payments = self.db.read(|c| kk_staff::supply_payments(c, scope))?;
        let items = self.db.read(|c| kk_stock::items(c, scope))?;
        let moves = self.db.read(|c| kk_stock::moves(c, scope))?;
        let zero = Money::zero(cur);
        let (mut total, mut overdue, mut soon) = (zero, zero, zero);
        let mut out = Vec::new();
        for a in self.kk_agreements(scope, SUPPLY, cur.code())? {
            let p: SupplyP = serde_json::from_str(&a.row.terms_json).map_err(|_| corrupt())?;
            let ds: Vec<_> = deliveries
                .iter()
                .filter(|x| x.agreement_id == a.row.id)
                .cloned()
                .collect();
            let ps: Vec<_> = payments
                .iter()
                .filter(|x| x.agreement_id == a.row.id)
                .cloned()
                .collect();
            let b = self.supplier_state(ctx, &ds, &ps, today)?;
            total = total.checked_add(b.outstanding)?;
            overdue = overdue.checked_add(b.overdue)?;
            soon = soon.checked_add(b.due_soon)?;
            let item = p
                .item_id
                .as_ref()
                .and_then(|i| items.iter().find(|x| &x.id == i));
            let mut dl = Vec::new();
            for (row, st) in ds.iter().zip(&b.deliveries) {
                let qty = match (&row.stock_move_id, item) {
                    (Some(m), Some(it)) => moves
                        .iter()
                        .find(|x| &x.id == m)
                        .map(|x| factor(&it.unit).map(|f| show_qty(x.qty, f)))
                        .transpose()?,
                    _ => None,
                };
                dl.push(KkDeliveryDto {
                    id: row.id.clone(),
                    delivered_on: row.delivered_on.clone(),
                    due_on: ymd(st.due),
                    amount: d(st.amount),
                    paid: d(st.paid),
                    outstanding: d(st.outstanding),
                    state: st.state.as_str().to_string(),
                    overdue_days: st.overdue_days,
                    qty,
                    note: row.note.clone(),
                });
            }
            dl.reverse();
            let mut missing = Vec::new();
            if p.goods.is_none() && p.item_id.is_none() {
                missing.push("goods".to_string());
            }
            out.push(KkSupplierDto {
                id: a.row.id.clone(),
                name: a.row.party_name.clone(),
                phone: a.row.phone.clone(),
                agreement: self.state_dto(&a, missing, &p.review_on)?,
                terms: KkSupplyTermsDto {
                    goods: p.goods.clone(),
                    item_id: p.item_id.clone(),
                    item_name: item.map(|i| i.name.clone()),
                    unit: item.map(|i| i.unit.clone()),
                    unit_price: p.unit_price.map(|m| d(Money::new(m, cur))),
                    payment_days: p.payment_days,
                    delivery: p.delivery.clone(),
                    returns: p.returns.clone(),
                    arbiter: p.arbiter.clone(),
                    note: p.note.clone(),
                },
                outstanding: d(b.outstanding),
                overdue: d(b.overdue),
                due_soon: d(b.due_soon),
                next_due: b.next_due.map(|(dt, m)| KkNextDueDto {
                    date: ymd(dt),
                    amount: d(m),
                }),
                deliveries: dl,
                payments: ps
                    .iter()
                    .rev()
                    .map(|x| KkSupplyPaymentDto {
                        id: x.id.clone(),
                        paid_on: x.paid_on.clone(),
                        amount: d(Money::new(x.amount_minor, cur)),
                        wallet: x.wallet.clone(),
                        as_expense: x.expense_id.is_some(),
                        note: x.note.clone(),
                    })
                    .collect(),
            });
        }
        Ok((out, total, overdue, soon))
    }

    fn signed_supplier(
        &self,
        ctx: &Ctx,
        scope: &SpaceScope,
        id: &str,
    ) -> Result<(Agreement, SupplyP), AppError> {
        let a = self.kk_agreement(ctx, scope, id, SUPPLY)?;
        let last = a
            .last_signed()
            .ok_or(AppError::on("AGREEMENT_NOT_SIGNED", "id"))?;
        let p: SupplyP = serde_json::from_str(&last.terms_json).map_err(|_| corrupt())?;
        Ok((a, p))
    }

    /// Yetkazish (nasiyaga tovar): to'lov muddati — kelishuvdagi kunlar. Tovar bog'langan bo'lsa — bitta
    /// tranzaksiyada hamyonsiz xarid (narx — qotirilgan narx × miqdor, yoki kiritilgan summa).
    pub fn kk_supply_delivery(
        &self,
        space_id: &str,
        id: &str,
        input: KkDeliveryInput,
    ) -> Result<KkSuppliersDto, AppError> {
        let ctx = self.ctx()?;
        let cur = ctx.currency;
        let scope = self.kk_scope(&ctx, space_id)?;
        let (a, p) = self.signed_supplier(&ctx, &scope, id)?;
        if a.row.status == ENDED {
            return Err(AppError::on("AGREEMENT_ENDED", "id"));
        }
        let on = self.date_or_today(&ctx, input.delivered_on.as_deref(), "deliveredOn")?;
        if ymd(on) < a.row.started_on {
            return Err(AppError::on("BEFORE_START", "deliveredOn"));
        }
        self.kk_ensure_open(&scope, &ymd(on), "deliveredOn")?;
        let given = opt_amount(&ctx, input.amount.as_deref(), "amount")?;
        let mut stock_row = None;
        let amount = match &p.item_id {
            Some(item_id) => {
                let item = self
                    .db
                    .read(|c| kk_stock::items(c, &scope))?
                    .into_iter()
                    .find(|x| &x.id == item_id)
                    .ok_or(AppError::on("NOT_FOUND", "itemId"))?;
                let f = factor(&item.unit)?;
                let qty = parse_qty(input.qty.as_deref().unwrap_or_default(), f, "qty")?;
                if qty <= 0 {
                    return Err(AppError::on("INVALID_QTY", "qty"));
                }
                let amount = match (given, p.unit_price) {
                    (Some(m), _) => m,
                    (None, Some(u)) => {
                        replacement(qty, Money::zero(cur), Money::new(u, cur), f, None)?
                            .replacement_value
                    }
                    (None, None) => return Err(AppError::on("REQUIRED", "amount")),
                };
                if !amount.is_positive() {
                    return Err(AppError::on("AMOUNT_NOT_POSITIVE", "amount"));
                }
                stock_row = Some(kk_stock::KkStockMoveRow {
                    id: self.new_id(),
                    item_id: item_id.clone(),
                    kind: "PURCHASE".into(),
                    occurred_on: ymd(on),
                    qty,
                    amount_minor: Some(amount.minor()),
                    wallet: None,
                    income_id: None,
                    reason: Some(a.row.party_name.clone()),
                });
                amount
            }
            None => given.ok_or(AppError::on("REQUIRED", "amount"))?,
        };
        let row = kk_staff::KkDeliveryRow {
            id: self.new_id(),
            agreement_id: id.to_string(),
            delivered_on: ymd(on),
            amount_minor: amount.minor(),
            currency: cur.code().to_string(),
            due_days: i64::from(p.payment_days),
            stock_move_id: stock_row.as_ref().map(|r| r.id.clone()),
            note: clean_opt(input.note.as_deref()),
        };
        let meta = self.meta();
        self.db.write(|tx| {
            if let Some(m) = &stock_row {
                kk_stock::insert_move(tx, &scope, m, &meta)?;
            }
            kk_staff::insert_delivery(tx, &scope, &row, &meta)
        })?;
        self.publish(Some(space_id), &[Topic::Kasbkor]);
        self.kk_suppliers(space_id)
    }

    /// Ta'minotchiga to'lov: eng erta muddatdan yopiladi; qoldiqdan ko'p to'lanmaydi. Summa bo'lmasa — eng
    /// yaqin muddatdagi qoldiq.
    pub fn kk_supply_payment(
        &self,
        space_id: &str,
        id: &str,
        input: KkSupplyPaymentInput,
    ) -> Result<KkSuppliersDto, AppError> {
        let ctx = self.ctx()?;
        let scope = self.kk_scope(&ctx, space_id)?;
        let (a, p) = self.signed_supplier(&ctx, &scope, id)?;
        let w = wallet(&input.wallet, "wallet")?;
        let on = self.date_or_today(&ctx, input.paid_on.as_deref(), "paidOn")?;
        let deliveries: Vec<_> = self
            .db
            .read(|c| kk_staff::deliveries(c, &scope))?
            .into_iter()
            .filter(|x| x.agreement_id == id)
            .collect();
        let mut payments: Vec<_> = self
            .db
            .read(|c| kk_staff::supply_payments(c, &scope))?
            .into_iter()
            .filter(|x| x.agreement_id == id)
            .collect();
        let amount = match opt_amount(&ctx, input.amount.as_deref(), "amount")? {
            Some(m) => m,
            None => {
                self.supplier_state(&ctx, &deliveries, &payments, on)?
                    .next_due
                    .ok_or(AppError::on("NOTHING_OWED", "amount"))?
                    .1
            }
        };
        self.kk_ensure_open(&scope, &ymd(on), "paidOn")?;
        self.kk_ensure_cash_open(&scope, &ymd(on), w.as_str() == "CASH")?;
        let exp = match p.item_id {
            Some(_) => None,
            None => {
                let cat = self.category_id(&scope, MATERIALS_KEY)?;
                Some(self.expense_row(
                    &ctx,
                    &cat,
                    amount,
                    w.as_str(),
                    &ymd(on),
                    Some(a.row.party_name.clone()),
                ))
            }
        };
        let row = kk_staff::KkSupplyPaymentRow {
            id: self.new_id(),
            agreement_id: id.to_string(),
            paid_on: ymd(on),
            amount_minor: amount.minor(),
            currency: ctx.currency.code().to_string(),
            wallet: w.as_str().to_string(),
            expense_id: exp.as_ref().map(|e| e.id.clone()),
            note: clean_opt(input.note.as_deref()),
        };
        payments.push(row.clone());
        self.supplier_state(&ctx, &deliveries, &payments, on)?;
        let meta = self.meta();
        self.db.write(|tx| {
            if let Some(e) = &exp {
                expenses::insert(tx, &scope, e, &meta)?;
            }
            kk_staff::insert_supply_payment(tx, &scope, &row, &meta)
        })?;
        let topics: &[Topic] = if exp.is_some() {
            &[Topic::Expenses, Topic::Kasbkor]
        } else {
            &[Topic::Kasbkor]
        };
        self.publish(Some(space_id), topics);
        self.kk_suppliers(space_id)
    }

    /// Hamyondan to'langan, chiqim emas (tovar bog'langan) ta'minot to'lovlari `[from, to)`: (to'lov, ta'minotchi).
    pub(crate) fn kk_supply_stock_payments(
        &self,
        ctx: &Ctx,
        scope: &SpaceScope,
        from: &str,
        to: &str,
    ) -> Result<Vec<(kk_staff::KkSupplyPaymentRow, String)>, AppError> {
        let names: Vec<_> = self
            .db
            .read(|c| kk_staff::agreements(c, scope))?
            .into_iter()
            .map(|a| (a.id, a.party_name))
            .collect();
        Ok(self
            .db
            .read(|c| kk_staff::supply_payments(c, scope))?
            .into_iter()
            .filter(|p| {
                p.expense_id.is_none()
                    && p.currency == ctx.currency.code()
                    && p.paid_on.as_str() >= from
                    && p.paid_on.as_str() < to
            })
            .filter_map(|p| {
                names
                    .iter()
                    .find(|(id, _)| id == &p.agreement_id)
                    .map(|(_, n)| (p.clone(), n.clone()))
            })
            .collect())
    }

    // ---- PDF ----

    /// Kelishuv PDF: oxirgi imzolangan versiya; imzolanmagan bo'lsa — joriy qoralama («QORALAMA»).
    pub fn kk_agreement_pdf(&self, space_id: &str, id: &str) -> Result<Vec<u8>, AppError> {
        let ctx = self.ctx()?;
        let scope = self.kk_scope(&ctx, space_id)?;
        let a = self.any_agreement(&ctx, &scope, id)?;
        let t = template(&a.row.kind)?;
        let last = a.last_signed();
        let json = last.map_or(a.row.terms_json.as_str(), |v| v.terms_json.as_str());
        let business = self
            .db
            .read(household::get_household)?
            .map(|h| h.name)
            .unwrap_or_default();
        let money = |m: i64| self.money_dto(&ctx, Money::new(m, ctx.currency)).formatted;
        let opt = |o: &Option<String>, fallback: &str| -> (String, bool) {
            match o {
                Some(v) => (v.clone(), false),
                None => (fallback.to_string(), true),
            }
        };
        // Qiymatlar: matn yoki (yorliq kaliti — `true`).
        let mut values: Vec<(String, (String, bool))> = vec![
            ("owner".into(), (business.clone(), false)),
            ("party".into(), (a.row.party_name.clone(), false)),
            ("startedOn".into(), (show(&a.row.started_on), false)),
        ];
        let (review_on, kind_values) = if a.row.kind == EMPLOYMENT {
            let p: EmploymentP = serde_json::from_str(json).map_err(|_| corrupt())?;
            (
                p.review_on.clone(),
                vec![
                    ("role".into(), opt(&p.role, "tpl.agreed")),
                    ("duties".into(), opt(&p.duties, "tpl.agreed")),
                    ("hours".into(), opt(&p.hours, "tpl.agreed")),
                    ("salary".into(), (money(p.salary), false)),
                    ("payDay".into(), (p.pay_day.to_string(), false)),
                    ("noticeDays".into(), (p.notice_days.to_string(), false)),
                    (
                        "maxAdvance".into(),
                        opt(&p.max_advance.map(money), "tpl.noLimit"),
                    ),
                    (
                        "maxInstallments".into(),
                        (p.max_installments.to_string(), false),
                    ),
                    ("arbiter".into(), opt(&p.arbiter, "tpl.noArbiter")),
                ],
            )
        } else {
            let p: SupplyP = serde_json::from_str(json).map_err(|_| corrupt())?;
            let item = match &p.item_id {
                Some(i) => self
                    .db
                    .read(|c| kk_stock::items(c, &scope))?
                    .into_iter()
                    .find(|x| &x.id == i),
                None => None,
            };
            let goods = match (&p.goods, &item) {
                (Some(g), _) => Some(g.clone()),
                (None, Some(i)) => Some(i.name.clone()),
                _ => None,
            };
            let price = p.unit_price.map(|u| match &item {
                Some(i) => format!("{} / {}", money(u), unit_word(&i.unit)),
                None => money(u),
            });
            (
                p.review_on.clone(),
                vec![
                    ("goods".into(), opt(&goods, "tpl.agreed")),
                    ("unitPrice".into(), opt(&price, "tpl.priceEach")),
                    ("paymentDays".into(), (p.payment_days.to_string(), false)),
                    ("delivery".into(), opt(&p.delivery, "tpl.agreed")),
                    ("returns".into(), opt(&p.returns, "tpl.returnsDefault")),
                    ("arbiter".into(), opt(&p.arbiter, "tpl.noArbiter")),
                ],
            )
        };
        values.extend(kind_values);
        values.push(("reviewOn".into(), (show(&review_on), false)));
        let label = |k: &str| k.strip_prefix("pdf.").unwrap_or(k).to_string();
        let doc = KkAgreementDoc {
            ident: last.map_or_else(|| a.row.id.clone(), |v| v.id.clone()),
            locale: pdf_locale(ctx.locale),
            kind: a.row.kind.clone(),
            business,
            party: a.row.party_name.clone(),
            version: last.map(|v| v.seq.to_string()),
            signed_on: last.map(|v| show(&v.signed_on)),
            effective_from: last.map(|v| show(&v.effective_from)),
            hash_code: last.map(|v| v.terms_hash.get(..8).unwrap_or_default().to_uppercase()),
            review_pending: last.map_or(t.review_status.as_str(), |v| v.template_review.as_str())
                == "PENDING",
            clauses: t
                .clauses
                .iter()
                .map(|c| KkClauseLine {
                    n: c.n,
                    label: label(&c.label),
                    text: label(&c.text),
                })
                .collect(),
            values,
            disclaimer: label(&t.disclaimer),
        };
        let today = self.today(&ctx);
        Ok(doc
            .render(engine(), today)
            .map_err(|e| AppError::new(e.code))?
            .pdf)
    }

    /// Oylik hisob varaqchasi (imzo joyi bilan): `month` — davr ichidagi istalgan sana.
    pub fn kk_payslip_pdf(
        &self,
        space_id: &str,
        id: &str,
        month: String,
    ) -> Result<Vec<u8>, AppError> {
        let ctx = self.ctx()?;
        let scope = self.kk_scope(&ctx, space_id)?;
        let a = self.kk_agreement(&ctx, &scope, id, EMPLOYMENT)?;
        let events: Vec<_> = self
            .db
            .read(|c| kk_staff::staff_events(c, &scope))?
            .into_iter()
            .filter(|e| e.agreement_id == id)
            .collect();
        let day = parse_day(&month, "month")?;
        let (periods, r) = self.employee_payroll(&ctx, &a, &events, day)?;
        let i = periods
            .iter()
            .position(|(s, e)| day >= *s && day < *e)
            .ok_or(AppError::on("INVALID_DATE", "month"))?;
        let m = r.months.get(i).ok_or_else(corrupt)?;
        let (s, e) = periods[i];
        let cur = ctx.currency;
        let f = |x: Money| self.money_dto(&ctx, x).formatted;
        let opening = if i == 0 {
            Money::new(a.row.opening_balance_minor, cur)
        } else {
            r.months.get(i - 1).ok_or_else(corrupt)?.balance
        };
        let last = e.pred_opt().ok_or(AppError::new("INVALID_PERIOD"))?;
        // Oy oxiridagi ushlanmagan avans: shu oygacha berilgani − shu oygacha ushlangani.
        let given = events
            .iter()
            .filter(|ev| ev.kind == "ADVANCE" && ev.occurred_on < ymd(e))
            .try_fold(Money::zero(cur), |s, ev| {
                s.checked_add(Money::new(ev.amount_minor, cur))
            })?;
        let deducted = r.months[..=i]
            .iter()
            .try_fold(Money::zero(cur), |s, x| s.checked_add(x.deducted))?;
        let outstanding = given.checked_sub(deducted)?;
        let p: EmploymentP = serde_json::from_str(&a.row.terms_json).map_err(|_| corrupt())?;
        let payments = events
            .iter()
            .filter(|ev| ev.occurred_on >= ymd(s) && ev.occurred_on < ymd(e))
            .map(|ev| {
                (
                    show(&ev.occurred_on),
                    format!("kkslip.kind.{}", ev.kind),
                    f(Money::new(ev.amount_minor, cur)),
                )
            })
            .collect();
        let doc = KkPayslip {
            ident: format!("{}-{}", a.row.id, ymd(s)),
            locale: pdf_locale(ctx.locale),
            business: self
                .db
                .read(household::get_household)?
                .map(|h| h.name)
                .unwrap_or_default(),
            employee: a.row.party_name.clone(),
            role: p.role.clone(),
            period: format!("{} — {}", show(&ymd(s)), show(&ymd(last))),
            rows: vec![
                ("kkslip.opening".into(), f(opening)),
                ("kkslip.salary".into(), f(m.salary)),
                ("kkslip.deducted".into(), format!("− {}", f(m.deducted))),
                ("kkslip.net".into(), f(m.net)),
                ("kkslip.paid".into(), format!("− {}", f(m.paid))),
                ("kkslip.balance".into(), f(m.balance)),
                ("kkslip.advances".into(), f(outstanding)),
            ],
            payments,
        };
        Ok(doc
            .render(engine(), last)
            .map_err(|e| AppError::new(e.code))?
            .pdf)
    }
}

/// Narx yonidagi birlik (PDF uchun, tilga bog'liq emas).
fn unit_word(unit: &str) -> &'static str {
    match unit {
        "G" => "kg",
        "ML" => "l",
        "MM" => "m",
        _ => "1",
    }
}

/// `day` tushgan oyda hozir to'lanadigani: o'tgan oylar qoldig'i − shu oy to'langan (manfiy bo'lsa 0).
fn due_at(
    periods: &[(NaiveDate, NaiveDate)],
    r: &Payroll,
    day: NaiveDate,
) -> Result<Money, AppError> {
    let i = periods
        .iter()
        .position(|(s, e)| day >= *s && day < *e)
        .unwrap_or(periods.len().saturating_sub(1));
    let m = r.months.get(i).ok_or_else(corrupt)?;
    Ok(m.balance.checked_sub(m.net)?.clamp_non_negative())
}

/// `k`-davr boshi (xodim oylari 0 dan); hisoblangan davrlardan keyingilari qadamma-qadam.
fn period_start(
    ctx: &Ctx,
    periods: &[(NaiveDate, NaiveDate)],
    k: u32,
) -> Result<NaiveDate, AppError> {
    let k = usize::try_from(k).map_err(|_| corrupt())?;
    if let Some(p) = periods.get(k) {
        return Ok(p.0);
    }
    let mut s = periods.last().ok_or_else(corrupt)?.1;
    for _ in periods.len()..k {
        s = month_period(s, ctx.month_start_day)
            .ok_or(AppError::new("INVALID_PERIOD"))?
            .1;
    }
    Ok(s)
}

/// Oxirgi davr oxiridan `to` tushgan davrgacha nechta davr bor (kelajakdagi ushlash boshi uchun).
fn months_between(from: Option<NaiveDate>, to: NaiveDate, ctx: &Ctx) -> Result<usize, AppError> {
    let Some(mut s) = from else {
        return Ok(0);
    };
    let mut n = 0;
    while s <= to {
        let (_, e) = month_period(s, ctx.month_start_day).ok_or(AppError::new("INVALID_PERIOD"))?;
        if to < e {
            break;
        }
        s = e;
        n += 1;
        if n > 1200 {
            return Err(AppError::new("INVALID_PERIOD"));
        }
    }
    Ok(n)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn templates_have_review_status_and_nine_questions() {
        for kind in [EMPLOYMENT, SUPPLY] {
            let t = template(kind).unwrap();
            assert!(matches!(t.review_status.as_str(), "PENDING" | "APPROVED"));
            let mut ns: Vec<u32> = t.clauses.iter().map(|c| c.n).collect();
            ns.dedup();
            assert_eq!(ns, (1..=9).collect::<Vec<_>>(), "{kind}");
        }
    }
}
