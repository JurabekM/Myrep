//! K7 — Kasb-kor «Kengayishga reja bilan chiq» va «Tarozingni to'g'ri tut» (`docs/kasbkor/SPEC.md` 6, 8):
//! kengayish darvozasi, «Hisob kuni» konvertlari, zakot hisobi (hisob, fatvo emas), yillik inventarizatsiya
//! va tarozi tekshiruvi.
//!
//! Hisob `domain-kasbkor::{gate, funds, zakat}` da (vektorlar `kk_expansion_gate`, `kk_funds`, `kk_zakat`);
//! «Zakot kuni» — jadvalli hijriy kalendar (`domain-common::hijri`, ±1–2 kun).
use std::sync::OnceLock;

use baraka_domain_common::hijri::{from_gregorian, hawl_complete, next_occurrence, HijriDate};
use baraka_domain_common::{month_period, SpaceKind};
use baraka_domain_kasbkor::credit::AgingBucket;
use baraka_domain_kasbkor::funds::{funds, Fund, FundEvent, FundState};
use baraka_domain_kasbkor::gate::{
    expansion_gate, GateInput, DEFAULT_MAX_BAD_BP, DEFAULT_RESERVE_MONTHS,
};
use baraka_domain_kasbkor::zakat::{zakat, ZakatInput, DEFAULT_NISAB_GRAMS};
use baraka_money::{format_percent_bp, Money};
use baraka_storage::repo::{
    categories, debts, expenses, household, kk_growth, kk_ledger, kk_stock, recovery, ventures,
};
use baraka_storage::SpaceScope;
use chrono::{Days, NaiveDate};
use serde::{Deserialize, Serialize};

use crate::app::Ctx;
use crate::debts::row_is_ribo;
use crate::events::Topic;
use crate::kasbkor_profit::parse_hundredths;
use crate::receipt::ymd;
use crate::text::{clean_opt, required};
use crate::uy::positive;
use crate::*;

const TAX_KEY: &str = "category.kk.tax";
const SCALE_EVERY_DAYS: u64 = 30;
const ZAKAT_LEAD_DAYS: i64 = 30;
const BEGINNING: &str = "0000-01-01";

/// Diniy matnlar ro'yxati (`shared/content/religious`): ulamo tasdig'isiz ko'rsatilmaydi (BARAKA_OILASI 2.3).
#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
struct ReligiousContent {
    religious_review_status: String,
    texts: Vec<String>,
}

const ZAKAT_CONTENT: &str = include_str!("../../../../shared/content/religious/kk_zakat.json");

fn zakat_content() -> Option<&'static ReligiousContent> {
    static C: OnceLock<Option<ReligiousContent>> = OnceLock::new();
    C.get_or_init(|| serde_json::from_str(ZAKAT_CONTENT).ok())
        .as_ref()
}

/// Tasdiqlangan diniy matn kaliti; tasdiqlanmagan bo'lsa — `None`.
fn approved_text(c: Option<&ReligiousContent>) -> Option<String> {
    c.filter(|c| c.religious_review_status == "APPROVED")
        .and_then(|c| c.texts.first().cloned())
}

fn corrupt() -> AppError {
    AppError::new("CORRUPT_ROW")
}

fn parse_day(s: &str, field: &str) -> Result<NaiveDate, AppError> {
    NaiveDate::parse_from_str(s, "%Y-%m-%d").map_err(|_| AppError::on("INVALID_DATE", field))
}

fn hijri_text(h: HijriDate) -> String {
    format!("{:04}-{:02}-{:02}", h.year, h.month, h.day)
}

/// Zakot snapshot'idagi kiritmalar (`inputs_json`).
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
struct ZakatRecord {
    v: u32,
    valuation: String,
    stock: i64,
    cash: i64,
    receivables: i64,
    payables: i64,
    wages_due: i64,
    gold_price: i64,
    nisab_grams: u32,
    hawl_complete: bool,
    hopeless_sale_ids: Vec<String>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
struct CountLine {
    item_id: String,
    name: String,
    unit: String,
    book: String,
    counted: String,
}

fn default_settings(ctx: &Ctx) -> kk_growth::KkGrowthSettingsRow {
    kk_growth::KkGrowthSettingsRow {
        reserve_months: i64::from(DEFAULT_RESERVE_MONTHS),
        max_bad_bp: DEFAULT_MAX_BAD_BP,
        zakat_month: None,
        zakat_day: None,
        gold_price_minor: None,
        nisab_grams: i64::from(DEFAULT_NISAB_GRAMS),
        stock_valuation: "REPLACEMENT".into(),
        scale_reminder: false,
        currency: ctx.currency.code().to_string(),
    }
}

impl App {
    fn kk_growth_row(
        &self,
        ctx: &Ctx,
        scope: &SpaceScope,
    ) -> Result<kk_growth::KkGrowthSettingsRow, AppError> {
        Ok(self
            .db
            .read(|c| kk_growth::growth_settings(c, scope))?
            .unwrap_or_else(|| default_settings(ctx)))
    }

    fn next_zakat_day(
        &self,
        row: &kk_growth::KkGrowthSettingsRow,
        today: NaiveDate,
    ) -> Option<NaiveDate> {
        let (m, d) = (row.zakat_month?, row.zakat_day?);
        next_occurrence(u32::try_from(m).ok()?, u32::try_from(d).ok()?, today)
    }

    fn settings_dto(
        &self,
        ctx: &Ctx,
        row: &kk_growth::KkGrowthSettingsRow,
    ) -> Result<KkGrowthSettingsDto, AppError> {
        let today = self.today(ctx);
        let u = |v: i64| u32::try_from(v).map_err(|_| corrupt());
        Ok(KkGrowthSettingsDto {
            reserve_months: u(row.reserve_months)?,
            max_bad_percent: format_percent_bp(row.max_bad_bp),
            zakat_month: row.zakat_month.map(u).transpose()?,
            zakat_day: row.zakat_day.map(u).transpose()?,
            next_zakat_day: self.next_zakat_day(row, today).map(ymd),
            gold_price: row
                .gold_price_minor
                .map(|g| self.money_dto(ctx, Money::new(g, ctx.currency))),
            nisab_grams: u(row.nisab_grams)?,
            stock_valuation: row.stock_valuation.clone(),
            scale_reminder: row.scale_reminder,
            today_hijri: hijri_text(from_gregorian(today)),
        })
    }

    pub fn kk_growth_settings(&self, space_id: &str) -> Result<KkGrowthSettingsDto, AppError> {
        let ctx = self.ctx()?;
        let scope = self.kk_scope(&ctx, space_id)?;
        let row = self.kk_growth_row(&ctx, &scope)?;
        self.settings_dto(&ctx, &row)
    }

    pub fn kk_set_growth_settings(
        &self,
        space_id: &str,
        input: KkGrowthSettingsInput,
    ) -> Result<KkGrowthSettingsDto, AppError> {
        let ctx = self.ctx()?;
        let scope = self.kk_scope(&ctx, space_id)?;
        if !(1..=24).contains(&input.reserve_months) {
            return Err(AppError::on("INVALID_MONTHS", "reserveMonths"));
        }
        let bad = parse_hundredths(&input.max_bad_percent, "INVALID_BP", "maxBadPercent")?;
        if !(0..=10_000).contains(&bad) {
            return Err(AppError::on("INVALID_BP", "maxBadPercent"));
        }
        let zakat_day = match (input.zakat_month, input.zakat_day) {
            (None, None) => None,
            (Some(m), Some(d)) if (1..=12).contains(&m) && (1..=30).contains(&d) => Some((m, d)),
            _ => return Err(AppError::on("INVALID_DATE", "zakatDay")),
        };
        if !(1..=1000).contains(&input.nisab_grams) {
            return Err(AppError::on("INVALID_NISAB", "nisabGrams"));
        }
        if !matches!(input.stock_valuation.as_str(), "REPLACEMENT" | "BOOK") {
            return Err(AppError::on("INVALID_VALUATION", "stockValuation"));
        }
        let gold = match input
            .gold_price
            .as_deref()
            .map(str::trim)
            .filter(|t| !t.is_empty())
        {
            None => None,
            Some(t) => Some(positive(&ctx, t, "goldPrice")?.minor()),
        };
        let row = kk_growth::KkGrowthSettingsRow {
            reserve_months: i64::from(input.reserve_months),
            max_bad_bp: bad,
            zakat_month: zakat_day.map(|(m, _)| i64::from(m)),
            zakat_day: zakat_day.map(|(_, d)| i64::from(d)),
            gold_price_minor: gold,
            nisab_grams: i64::from(input.nisab_grams),
            stock_valuation: input.stock_valuation,
            scale_reminder: input.scale_reminder,
            currency: ctx.currency.code().to_string(),
        };
        let id = self.new_id();
        let meta = self.meta();
        self.db
            .write(|tx| kk_growth::upsert_growth_settings(tx, &scope, &id, &row, &meta))?;
        self.publish(Some(space_id), &[Topic::Kasbkor]);
        self.settings_dto(&ctx, &row)
    }

    // ---- konvertlar ----

    /// Konvertlar holati: bayonnomalar qo'shadi; soliq zaxirasidan — «Soliq» chiqimi (zaxira yetgancha),
    /// qolganlaridan — qayd etilgan foydalanish. `extra` — hali saqlanmagan foydalanish (tekshirish uchun).
    fn kk_fund_states(
        &self,
        ctx: &Ctx,
        scope: &SpaceScope,
        extra: Option<&kk_growth::KkFundUseRow>,
    ) -> Result<Vec<FundState>, AppError> {
        let cur = ctx.currency;
        // (sana, tartib, hodisa): bir kunda — avval bayonnoma, keyin foydalanish.
        let mut timeline: Vec<(String, u8, FundEvent)> = Vec::new();
        for f in self.kk_close_figures(ctx, scope)? {
            let m = |v: i64| Money::new(v, cur);
            let a = f.allocation;
            timeline.push((
                f.closed_on.clone(),
                0,
                FundEvent::Close([m(f.tax), m(a[0]), m(a[1]), m(a[2]), m(a[3])]),
            ));
        }
        let uses = self.db.read(|c| kk_growth::fund_uses(c, scope))?;
        for u in uses
            .iter()
            .chain(extra)
            .filter(|u| u.currency == cur.code())
        {
            let fund = Fund::parse(&u.fund).ok_or_else(corrupt)?;
            timeline.push((
                u.used_on.clone(),
                1,
                FundEvent::Use {
                    fund,
                    amount: Money::new(u.amount_minor, cur),
                },
            ));
        }
        let tax_cat = self
            .db
            .read(|c| categories::list(c, scope))?
            .into_iter()
            .find(|c| c.name_key == TAX_KEY)
            .map(|c| c.id);
        let mut taxes = Vec::new();
        if let Some(cat) = tax_cat {
            for e in self
                .db
                .read(|c| expenses::list_between(c, scope, BEGINNING, "9999-12-31"))?
                .into_iter()
                .filter(|e| e.category_id == cat && e.currency == cur.code())
            {
                taxes.push((e.occurred_on.clone(), Money::new(e.amount_minor, cur)));
            }
        }
        timeline.sort_by(|a, b| a.0.cmp(&b.0).then(a.1.cmp(&b.1)));
        // To'langan soliq — soliq zaxirasi yetgancha (zaxirasiz to'langan soliq ham xato emas).
        let mut events: Vec<FundEvent> = Vec::new();
        let mut ti = taxes.into_iter().peekable();
        for (day, _, ev) in timeline {
            while let Some((d, _)) = ti.peek() {
                if d.as_str() >= day.as_str() {
                    break;
                }
                let (_, amount) = ti.next().ok_or_else(corrupt)?;
                Self::push_tax(cur, &mut events, amount)?;
            }
            events.push(ev);
        }
        for (_, amount) in ti {
            Self::push_tax(cur, &mut events, amount)?;
        }
        Ok(funds(cur, &events)?)
    }

    fn push_tax(
        cur: baraka_money::Currency,
        events: &mut Vec<FundEvent>,
        paid: Money,
    ) -> Result<(), AppError> {
        let balance = funds(cur, events)?
            .into_iter()
            .find(|f| f.fund == Fund::Tax)
            .map_or(Money::zero(cur), |f| f.balance);
        let used = if paid.compare(&balance)?.is_lt() {
            paid
        } else {
            balance
        };
        if used.is_positive() {
            events.push(FundEvent::Use {
                fund: Fund::Tax,
                amount: used,
            });
        }
        Ok(())
    }

    fn fund_dtos(&self, ctx: &Ctx, states: &[FundState]) -> Vec<KkFundDto> {
        states
            .iter()
            .map(|f| KkFundDto {
                fund: f.fund.as_str().to_string(),
                added: self.money_dto(ctx, f.added),
                used: self.money_dto(ctx, f.used),
                balance: self.money_dto(ctx, f.balance),
            })
            .collect()
    }

    /// Konvertdan foydalanish (zaxira, aylanma, kengayish, sadaqa): qoldiqdan ko'p emas.
    pub fn kk_use_fund(
        &self,
        space_id: &str,
        input: KkFundUseInput,
    ) -> Result<KkGateDto, AppError> {
        let ctx = self.ctx()?;
        let scope = self.kk_scope(&ctx, space_id)?;
        let fund = Fund::parse(&input.fund)
            .filter(|f| *f != Fund::Tax)
            .ok_or(AppError::on("INVALID_FUND", "fund"))?;
        let amount = positive(&ctx, &input.amount, "amount")?;
        let on = self.date_or_today(&ctx, input.used_on.as_deref(), "usedOn")?;
        self.kk_ensure_open(&scope, &ymd(on), "usedOn")?;
        let row = kk_growth::KkFundUseRow {
            id: self.new_id(),
            fund: fund.as_str().to_string(),
            used_on: ymd(on),
            amount_minor: amount.minor(),
            currency: ctx.currency.code().to_string(),
            note: clean_opt(input.note.as_deref()),
        };
        self.kk_fund_states(&ctx, &scope, Some(&row))?;
        let meta = self.meta();
        self.db
            .write(|tx| kk_growth::insert_fund_use(tx, &scope, &row, &meta))?;
        self.publish(Some(space_id), &[Topic::Kasbkor]);
        self.kk_gate(space_id)
    }

    // ---- kengayish darvozasi ----

    /// Foizli qarz va qarzdan chiqish rejasi — Uy darvozasi qoidasi (xonadonning Uy makoni va shu makon).
    fn interest_debt_status(
        &self,
        ctx: &Ctx,
        scope: &SpaceScope,
    ) -> Result<(bool, bool), AppError> {
        let mut scopes = vec![scope.clone()];
        for s in self
            .db
            .read(|c| household::list_spaces(c, &ctx.household_id))?
            .into_iter()
            .filter(|s| s.kind == SpaceKind::Uy.as_str())
        {
            scopes.push(self.scope(ctx, &s.id)?);
        }
        let (mut debt, mut plan) = (false, false);
        for sc in &scopes {
            debt |= self
                .db
                .read(|c| debts::list_debts(c, sc))?
                .iter()
                .any(|d| d.status == "ACTIVE" && row_is_ribo(d));
            plan |= self
                .db
                .read(|c| recovery::budget(c, sc))?
                .is_some_and(|b| b.mode == "DEBT_RECOVERY");
        }
        Ok((debt, plan))
    }

    pub fn kk_gate(&self, space_id: &str) -> Result<KkGateDto, AppError> {
        let ctx = self.ctx()?;
        let scope = self.kk_scope(&ctx, space_id)?;
        let cur = ctx.currency;
        let d = |m: Money| self.money_dto(&ctx, m);
        let settings = self.kk_growth_row(&ctx, &scope)?;
        let states = self.kk_fund_states(&ctx, &scope, None)?;
        let reserve = states
            .iter()
            .find(|f| f.fund == Fund::Reserve)
            .map_or(Money::zero(cur), |f| f.balance);
        // Oxirgi 3 to'liq oy (yozuvi borlari) operatsion xarajati.
        let today = self.today(&ctx);
        let (mut start, _) =
            month_period(today, ctx.month_start_day).ok_or(AppError::new("INVALID_PERIOD"))?;
        let mut opex = Vec::new();
        for _ in 0..3 {
            let prev = start
                .checked_sub_days(Days::new(1))
                .ok_or(AppError::new("INVALID_PERIOD"))?;
            let p = self.kk_period(&ctx, &scope, prev)?;
            if p.has_activity {
                opex.push(p.r.expenses);
            }
            start = p.start;
        }
        let profits: Vec<Money> = self
            .kk_close_figures(&ctx, &scope)?
            .iter()
            .map(|f| Money::new(f.true_profit, cur))
            .collect();
        let states_credit = self.kk_credit_states(&ctx, &scope, today)?;
        let (mut total, mut d90) = (Money::zero(cur), Money::zero(cur));
        for (_, _, st) in &states_credit {
            total = total.checked_add(st.outstanding)?;
            if st.bucket == Some(AgingBucket::D90Plus) {
                d90 = d90.checked_add(st.outstanding)?;
            }
        }
        let (has_interest_debt, has_payoff_plan) = self.interest_debt_status(&ctx, &scope)?;
        let plans = self.db.read(|c| ventures::ideas(c, &scope))?.len();
        let required_months = u32::try_from(settings.reserve_months).map_err(|_| corrupt())?;
        let r = expansion_gate(&GateInput {
            reserve,
            opex_months: opex,
            required_months,
            true_profits: profits.clone(),
            receivables: total,
            receivables_90: d90,
            max_bad_bp: settings.max_bad_bp,
            has_interest_debt,
            has_payoff_plan,
            has_plan: plans > 0,
        })?;
        Ok(KkGateDto {
            open: r.open,
            conditions: r
                .conditions
                .iter()
                .map(|(c, ok)| KkGateConditionDto {
                    code: c.as_str().to_string(),
                    ok: *ok,
                })
                .collect(),
            reasons: r.reasons().iter().map(|c| c.as_str().to_string()).collect(),
            reserve: d(reserve),
            average_opex: r.average_opex.map(d),
            required_reserve: r.required_reserve.map(d),
            coverage_months: r.coverage_centi_months.map(format_percent_bp),
            required_months,
            true_profits: profits.iter().rev().take(3).rev().map(|m| d(*m)).collect(),
            receivables: d(total),
            receivables_90: d(d90),
            bad_debt_percent: format_percent_bp(r.bad_debt_bp),
            max_bad_percent: format_percent_bp(settings.max_bad_bp),
            has_interest_debt,
            has_payoff_plan,
            plans: u32::try_from(plans).map_err(|_| corrupt())?,
            funds: self.fund_dtos(&ctx, &states),
        })
    }

    // ---- tarozi ----

    fn scale_due(
        &self,
        ctx: &Ctx,
        reminder: bool,
        checks: &[kk_growth::KkScaleCheckRow],
    ) -> Result<bool, AppError> {
        if !reminder {
            return Ok(false);
        }
        let limit = self
            .today(ctx)
            .checked_sub_days(Days::new(SCALE_EVERY_DAYS))
            .ok_or(AppError::new("INVALID_DATE"))?;
        Ok(checks.first().is_none_or(|c| c.checked_on < ymd(limit)))
    }

    pub fn kk_scale(&self, space_id: &str) -> Result<KkScaleDto, AppError> {
        let ctx = self.ctx()?;
        let scope = self.kk_scope(&ctx, space_id)?;
        let reminder = self.kk_growth_row(&ctx, &scope)?.scale_reminder;
        let checks = self.db.read(|c| kk_growth::scale_checks(c, &scope))?;
        Ok(KkScaleDto {
            due: self.scale_due(&ctx, reminder, &checks)?,
            reminder,
            checks: checks
                .into_iter()
                .map(|c| KkScaleCheckDto {
                    id: c.id,
                    checked_on: c.checked_on,
                    result: c.result,
                    note: c.note,
                })
                .collect(),
        })
    }

    /// Tarozi etalon og'irlik bilan tekshirildi — natija qayd etiladi (ilova o'lchamaydi).
    pub fn kk_scale_check(
        &self,
        space_id: &str,
        input: KkScaleCheckInput,
    ) -> Result<KkScaleDto, AppError> {
        let ctx = self.ctx()?;
        let scope = self.kk_scope(&ctx, space_id)?;
        if !matches!(input.result.as_str(), "OK" | "ADJUSTED" | "FAULTY") {
            return Err(AppError::on("INVALID_RESULT", "result"));
        }
        let note = clean_opt(input.note.as_deref());
        if input.result != "OK" && note.is_none() {
            return Err(AppError::on("REQUIRED", "note"));
        }
        let on = self.date_or_today(&ctx, input.checked_on.as_deref(), "checkedOn")?;
        let row = kk_growth::KkScaleCheckRow {
            id: self.new_id(),
            checked_on: ymd(on),
            result: input.result,
            note,
        };
        let meta = self.meta();
        self.db
            .write(|tx| kk_growth::insert_scale_check(tx, &scope, &row, &meta))?;
        self.publish(Some(space_id), &[Topic::Kasbkor]);
        self.kk_scale(space_id)
    }

    /// Bosh sahifa eslatmalari: «Zakot kuni» 30 kun ichida bo'lsa — sanasi; tarozi tekshiruvi vaqti.
    pub(crate) fn kk_growth_reminders(
        &self,
        ctx: &Ctx,
        scope: &SpaceScope,
    ) -> Result<(Option<String>, bool), AppError> {
        let row = self.kk_growth_row(ctx, scope)?;
        let today = self.today(ctx);
        let zakat = self
            .next_zakat_day(&row, today)
            .filter(|d| (*d - today).num_days() <= ZAKAT_LEAD_DAYS)
            .map(ymd);
        let checks = self.db.read(|c| kk_growth::scale_checks(c, scope))?;
        Ok((zakat, self.scale_due(ctx, row.scale_reminder, &checks)?))
    }

    // ---- zakot ----

    fn kk_zakat_compute(
        &self,
        ctx: &Ctx,
        scope: &SpaceScope,
        space_id: &str,
        input: &KkZakatInput,
    ) -> Result<(KkZakatDto, Option<ZakatRecord>), AppError> {
        let cur = ctx.currency;
        let d = |m: Money| self.money_dto(ctx, m);
        let settings = self.kk_growth_row(ctx, scope)?;
        let today = self.today(ctx);
        let valuation = input
            .valuation
            .clone()
            .unwrap_or_else(|| settings.stock_valuation.clone());
        if !matches!(valuation.as_str(), "REPLACEMENT" | "BOOK") {
            return Err(AppError::on("INVALID_VALUATION", "valuation"));
        }
        let stock_dto = self.kk_stock(space_id)?;
        let pick = if valuation == "BOOK" {
            &stock_dto.value
        } else {
            &stock_dto.replacement_value
        };
        let stock = Money::new(pick.minor.parse().map_err(|_| corrupt())?, cur);
        let o = self.kk_overview(space_id, None)?;
        let minor = |m: &MoneyDto| -> Result<Money, AppError> {
            Ok(Money::new(m.minor.parse().map_err(|_| corrupt())?, cur))
        };
        let cash = minor(&o.cash)?
            .clamp_non_negative()
            .checked_add(minor(&o.card)?.clamp_non_negative())?;
        let payables = minor(&o.payables)?;
        let wages_due = minor(&o.wages_owed)?;
        // Nasiya: umidsiz deb belgilangan 90+ lar bazaga kirmaydi.
        let customers = self.db.read(|c| kk_ledger::customers(c, scope))?;
        let mut receivables = Money::zero(cur);
        let mut lines = Vec::new();
        for (sale, _, st) in self.kk_credit_states(ctx, scope, today)? {
            if !st.outstanding.is_positive() {
                continue;
            }
            let d90 = st.bucket == Some(AgingBucket::D90Plus);
            let hopeless = input.hopeless_sale_ids.contains(&sale.id);
            if hopeless && !d90 {
                return Err(AppError::on("HOPELESS_NOT_90", "hopelessSaleIds"));
            }
            if !hopeless {
                receivables = receivables.checked_add(st.outstanding)?;
            }
            lines.push(KkZakatReceivableDto {
                sale_id: sale.id.clone(),
                customer: customers
                    .iter()
                    .find(|c| c.id == sale.customer_id)
                    .map(|c| c.name.clone())
                    .unwrap_or_default(),
                item: sale.item.clone(),
                outstanding: d(st.outstanding),
                overdue_days: u32::try_from(st.overdue_days).unwrap_or(0),
                d90_plus: d90,
                hopeless,
            });
        }
        let debts = payables.checked_add(wages_due)?;
        // Hawl: oxirgi zakot hisobi yoki birinchi yozuvdan bir qamariy yil.
        let last_calc = self
            .db
            .read(|c| kk_growth::zakat_calcs(c, scope))?
            .into_iter()
            .next()
            .map(|c| c.calculated_on);
        let since = match last_calc {
            Some(d) => Some(d),
            None => self.db.read(|c| kk_growth::first_activity(c, scope))?,
        };
        let hawl_suggested = since
            .as_deref()
            .map(|s| parse_day(s, "since"))
            .transpose()?
            .is_some_and(|s| hawl_complete(s, today));
        let hawl = input.hawl_complete.unwrap_or(hawl_suggested);
        let grams = input
            .nisab_grams
            .unwrap_or(u32::try_from(settings.nisab_grams).map_err(|_| corrupt())?);
        let gold = match input
            .gold_price
            .as_deref()
            .map(str::trim)
            .filter(|t| !t.is_empty())
        {
            Some(t) => Some(positive(ctx, t, "goldPrice")?),
            None => settings.gold_price_minor.map(|g| Money::new(g, cur)),
        };
        let mut dto = KkZakatDto {
            calculated_on: ymd(today),
            hijri_date: hijri_text(from_gregorian(today)),
            valuation: valuation.clone(),
            stock: d(stock),
            cash: d(cash),
            receivables: d(receivables),
            payables: d(payables),
            wages_due: d(wages_due),
            debts: d(debts),
            gold_price: gold.map(d),
            nisab_grams: grams,
            nisab: None,
            base: d(stock
                .checked_add(cash)?
                .checked_add(receivables)?
                .checked_sub(debts)?),
            zakat: d(Money::zero(cur)),
            due: false,
            reason: Some("GOLD_PRICE_MISSING".into()),
            hawl_complete: hawl,
            hawl_suggested,
            hawl_since: since,
            receivable_lines: lines,
            religious_note: approved_text(zakat_content()),
            religious_review: zakat_content()
                .map_or("PENDING", |c| c.religious_review_status.as_str())
                .to_string(),
        };
        let Some(gold) = gold else {
            return Ok((dto, None));
        };
        let r = zakat(&ZakatInput {
            stock,
            cash,
            receivables,
            debts,
            gold_price: gold,
            nisab_grams: grams,
            hawl_complete: hawl,
        })?;
        dto.nisab = Some(d(r.nisab));
        dto.base = d(r.base);
        dto.zakat = d(r.zakat);
        dto.due = r.reason.is_none();
        dto.reason = r.reason.map(|x| x.as_str().to_string());
        let mut hopeless = input.hopeless_sale_ids.clone();
        hopeless.sort();
        let rec = ZakatRecord {
            v: 1,
            valuation,
            stock: stock.minor(),
            cash: cash.minor(),
            receivables: receivables.minor(),
            payables: payables.minor(),
            wages_due: wages_due.minor(),
            gold_price: gold.minor(),
            nisab_grams: grams,
            hawl_complete: hawl,
            hopeless_sale_ids: hopeless,
        };
        Ok((dto, Some(rec)))
    }

    /// Zakot hisobi (saqlanmaydi). Hisob, fatvo emas.
    pub fn kk_zakat_draft(
        &self,
        space_id: &str,
        input: KkZakatInput,
    ) -> Result<KkZakatDto, AppError> {
        let ctx = self.ctx()?;
        let scope = self.kk_scope(&ctx, space_id)?;
        Ok(self.kk_zakat_compute(&ctx, &scope, space_id, &input)?.0)
    }

    /// Hisobni o'zgarmas snapshot sifatida saqlash (keyingi yil hawl shu sanadan).
    pub fn kk_save_zakat(
        &self,
        space_id: &str,
        input: KkZakatInput,
    ) -> Result<Vec<KkZakatCalcDto>, AppError> {
        let ctx = self.ctx()?;
        let scope = self.kk_scope(&ctx, space_id)?;
        let (dto, rec) = self.kk_zakat_compute(&ctx, &scope, space_id, &input)?;
        let rec = rec.ok_or(AppError::on("REQUIRED", "goldPrice"))?;
        let minor =
            |m: &MoneyDto| -> Result<i64, AppError> { m.minor.parse().map_err(|_| corrupt()) };
        let row = kk_growth::KkZakatCalcRow {
            id: self.new_id(),
            calculated_on: dto.calculated_on.clone(),
            hijri_date: dto.hijri_date.clone(),
            currency: ctx.currency.code().to_string(),
            inputs_json: serde_json::to_string(&rec).map_err(|_| corrupt())?,
            base_minor: minor(&dto.base)?,
            nisab_minor: minor(dto.nisab.as_ref().ok_or_else(corrupt)?)?,
            zakat_minor: minor(&dto.zakat)?,
            reason: dto.reason.clone(),
        };
        let meta = self.meta();
        self.db
            .write(|tx| kk_growth::insert_zakat_calc(tx, &scope, &row, &meta))?;
        self.publish(Some(space_id), &[Topic::Kasbkor]);
        self.kk_zakat_history(space_id)
    }

    pub fn kk_zakat_history(&self, space_id: &str) -> Result<Vec<KkZakatCalcDto>, AppError> {
        let ctx = self.ctx()?;
        let scope = self.kk_scope(&ctx, space_id)?;
        let m = |v: i64| self.money_dto(&ctx, Money::new(v, ctx.currency));
        Ok(self
            .db
            .read(|c| kk_growth::zakat_calcs(c, &scope))?
            .into_iter()
            .filter(|r| r.currency == ctx.currency.code())
            .map(|r| KkZakatCalcDto {
                id: r.id,
                calculated_on: r.calculated_on,
                hijri_date: r.hijri_date,
                base: m(r.base_minor),
                nisab: m(r.nisab_minor),
                zakat: m(r.zakat_minor),
                reason: r.reason,
            })
            .collect())
    }

    // ---- yillik inventarizatsiya ----

    /// Sanalgan tovarlar: farqi borlari `ADJUST` harakati, hammasi bitta tranzaksiyada va snapshot bilan.
    pub fn kk_inventory(
        &self,
        space_id: &str,
        input: KkInventoryInput,
    ) -> Result<KkStockDto, AppError> {
        let ctx = self.ctx()?;
        let scope = self.kk_scope(&ctx, space_id)?;
        let reason = required(&input.reason, "reason")?;
        let on = self.date_or_today(&ctx, input.counted_on.as_deref(), "countedOn")?;
        let before = self.kk_stock(space_id)?;
        let mut rows = Vec::new();
        let mut lines = Vec::new();
        for (idx, l) in input.lines.iter().enumerate() {
            if l.counted.trim().is_empty() {
                continue;
            }
            let item = before
                .items
                .iter()
                .find(|i| i.id == l.item_id)
                .ok_or(AppError::on("NOT_FOUND", &format!("lines.{idx}")))?;
            let mv = KkStockMoveInput {
                kind: "COUNT".into(),
                qty: l.counted.clone(),
                amount: None,
                wallet: None,
                occurred_on: Some(ymd(on)),
                reason: Some(reason.clone()),
            };
            match self.kk_stock_prepare(&ctx, &scope, &l.item_id, &mv) {
                Ok((row, _)) => rows.push(row),
                Err(e) if e.code == "NO_DIFFERENCE" => {}
                Err(e) => return Err(AppError::on(&e.code, &format!("lines.{idx}"))),
            }
            lines.push(CountLine {
                item_id: item.id.clone(),
                name: item.name.clone(),
                unit: item.unit.clone(),
                book: item.qty.clone(),
                counted: l.counted.trim().to_string(),
            });
        }
        if lines.is_empty() {
            return Err(AppError::on("REQUIRED", "lines"));
        }
        let value_before: i64 = before.value.minor.parse().map_err(|_| corrupt())?;
        let after = self.kk_stock_value_with(&ctx, &scope, &rows)?;
        let snap = kk_growth::KkStockCountRow {
            id: self.new_id(),
            counted_on: ymd(on),
            currency: ctx.currency.code().to_string(),
            lines_json: serde_json::to_string(&lines).map_err(|_| corrupt())?,
            value_before_minor: value_before,
            value_after_minor: after.minor(),
        };
        let meta = self.meta();
        self.db.write(|tx| {
            for r in &rows {
                kk_stock::insert_move(tx, &scope, r, &meta)?;
            }
            kk_growth::insert_stock_count(tx, &scope, &snap, &meta)
        })?;
        self.publish(Some(space_id), &[Topic::Kasbkor]);
        self.kk_stock(space_id)
    }

    pub fn kk_stock_counts(&self, space_id: &str) -> Result<Vec<KkStockCountDto>, AppError> {
        let ctx = self.ctx()?;
        let scope = self.kk_scope(&ctx, space_id)?;
        let moves = self.db.read(|c| kk_stock::moves(c, &scope))?;
        let m = |v: i64| self.money_dto(&ctx, Money::new(v, ctx.currency));
        self.db
            .read(|c| kk_growth::stock_counts(c, &scope))?
            .into_iter()
            .filter(|r| r.currency == ctx.currency.code())
            .map(|r| {
                let lines: Vec<CountLine> =
                    serde_json::from_str(&r.lines_json).map_err(|_| corrupt())?;
                let changed = moves
                    .iter()
                    .filter(|mv| mv.kind == "ADJUST" && mv.occurred_on == r.counted_on)
                    .filter(|mv| lines.iter().any(|l| l.item_id == mv.item_id))
                    .count();
                Ok(KkStockCountDto {
                    id: r.id,
                    counted_on: r.counted_on,
                    value_before: m(r.value_before_minor),
                    value_after: m(r.value_after_minor),
                    counted: u32::try_from(lines.len()).map_err(|_| corrupt())?,
                    changed: u32::try_from(changed).map_err(|_| corrupt())?,
                })
            })
            .collect()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn religious_text_hidden_until_approved() {
        let pending = ReligiousContent {
            religious_review_status: "PENDING".into(),
            texts: vec!["rel.kk.zakat.note".into()],
        };
        assert_eq!(approved_text(Some(&pending)), None);
        let approved = ReligiousContent {
            religious_review_status: "APPROVED".into(),
            ..pending
        };
        assert_eq!(
            approved_text(Some(&approved)).as_deref(),
            Some("rel.kk.zakat.note")
        );
        // Kontentdagi joriy holat — ko'rikdan o'tmagan.
        assert_eq!(zakat_content().unwrap().religious_review_status, "PENDING");
    }
}
