//! K3 — Kasb-kor «Hisob kuni» (`docs/kasbkor/SPEC.md` 4.5): soliq zaxirasi va taqsimot qoidasi,
//! oyni yopish, o'zgarmas bayonnoma (xesh zanjiri) va PDF. Yopilgan davr ichidagi sanaga yozuv
//! qo'shib, o'chirib bo'lmaydi — tuzatish keyingi oyga yoziladi.
//!
//! Hisob `domain-kasbkor::close` da (vektorlar `kk_month_close`).
use baraka_domain_common::month_period;
use baraka_domain_kasbkor::close::{month_close, CloseInput, SplitRule, TaxRule};
use baraka_journal::{short_code, GENESIS_HASH};
use baraka_money::{format_percent_bp, parse_amount, Money};
use baraka_pdf::KkCloseReport;
use baraka_storage::repo::{expenses, household, kk};
use baraka_storage::SpaceScope;
use chrono::NaiveDate;
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};

use crate::app::Ctx;
use crate::events::Topic;
use crate::kasbkor_profit::{parse_hundredths, show_hundredths};
use crate::partnership::engine;
use crate::receipt::{pdf_locale, ymd};
use crate::text::clean_opt;
use crate::venture::show;
use crate::*;

/// Bayonnoma ichidagi raqamlar (minor) — `result_json`. Maydon tartibi barqaror (serde_json kalitlarni
/// alifbo bo'yicha yozadi), xesh shu matndan olinadi.
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
struct CloseRecord {
    v: u32,
    period_start: String,
    period_end: String,
    currency: String,
    revenue: i64,
    expenses: i64,
    depreciation: i64,
    true_profit: i64,
    owner_salary: Option<i64>,
    owner_paid: i64,
    salary_remaining: Option<i64>,
    tax_base: String,
    tax_bp: i64,
    tax_fixed: i64,
    tax: i64,
    owner_pay: i64,
    overdrawn: i64,
    carry_forward: i64,
    remaining: i64,
    rule: [i64; 4],
    allocation: Option<[i64; 4]>,
    reserve_below_depreciation: bool,
    explanation: Option<String>,
    /// K9 (v2): o'z mehnati bahosi — egasi topgani `max(0, o'z mehnati + haqiqiy foyda)` shu qotirilgan
    /// raqamlardan olinadi. v1 bayonnomalarda yo'q.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    owner_labor: Option<i64>,
}

fn rules_or_default(row: Option<kk::KkCloseRulesRow>) -> kk::KkCloseRulesRow {
    row.unwrap_or_default()
}

fn tax_rule(
    r: &kk::KkCloseRulesRow,
    currency: baraka_money::Currency,
) -> Result<TaxRule, AppError> {
    Ok(match r.tax_base.as_str() {
        "NONE" => TaxRule::None,
        "REVENUE" => TaxRule::Revenue { bp: r.tax_bp },
        "PROFIT" => TaxRule::Profit { bp: r.tax_bp },
        "FIXED" => TaxRule::Fixed {
            amount: Money::new(r.tax_fixed_minor, currency),
        },
        _ => return Err(AppError::new("CORRUPT_ROW")),
    })
}

fn split(r: &kk::KkCloseRulesRow) -> SplitRule {
    SplitRule {
        reserve_bp: r.reserve_bp,
        working_bp: r.working_bp,
        expansion_bp: r.expansion_bp,
        sadaqa_bp: r.sadaqa_bp,
    }
}

fn hex(bytes: &[u8]) -> String {
    bytes.iter().map(|b| format!("{b:02x}")).collect()
}

fn content_hash(prev: &str, json: &str) -> String {
    let mut h = Sha256::new();
    h.update(prev.as_bytes());
    h.update(b"\n");
    h.update(json.as_bytes());
    hex(&h.finalize())
}

/// Bitta bayonnomaning K7 uchun kerakli raqamlari (minor).
pub(crate) struct CloseFigures {
    pub closed_on: String,
    pub tax: i64,
    /// Zaxira, aylanma, kengayish, sadaqa.
    pub allocation: [i64; 4],
    pub true_profit: i64,
}

impl App {
    /// Yopilgan davr ichidagi sanaga yozib bo'lmaydi (bayonnoma o'zgarmas). Faqat Kasb-kor makonlarida
    /// bayonnoma bo'ladi, boshqa makonlar uchun tekshiruv doim o'tadi.
    pub(crate) fn kk_ensure_open(
        &self,
        scope: &SpaceScope,
        date: &str,
        field: &str,
    ) -> Result<(), AppError> {
        match self.db.read(|c| kk::closed_until(c, scope))? {
            Some(until) if date <= until.as_str() => Err(AppError::on("PERIOD_CLOSED", field)),
            _ => Ok(()),
        }
    }

    /// O'tgan davr yopilmagan va unda yozuvlar bo'lsa — uning boshi («Hisob kuni» eslatmasi).
    pub(crate) fn kk_close_due(
        &self,
        ctx: &Ctx,
        scope: &SpaceScope,
        start: NaiveDate,
        closed_until: Option<&str>,
    ) -> Result<Option<String>, AppError> {
        let prev = self.kk_period(
            ctx,
            scope,
            start.pred_opt().ok_or(AppError::new("INVALID_PERIOD"))?,
        )?;
        if closed_until.is_some_and(|u| u >= ymd(prev.start).as_str()) || !prev.has_activity {
            return Ok(None);
        }
        Ok(Some(ymd(prev.start)))
    }

    fn rules_dto(&self, ctx: &Ctx, r: &kk::KkCloseRulesRow) -> KkCloseRulesDto {
        KkCloseRulesDto {
            tax_base: r.tax_base.clone(),
            tax_percent: show_hundredths(r.tax_bp),
            tax_fixed: (r.tax_base == "FIXED")
                .then(|| self.money_dto(ctx, Money::new(r.tax_fixed_minor, ctx.currency))),
            reserve_percent: show_hundredths(r.reserve_bp),
            working_percent: show_hundredths(r.working_bp),
            expansion_percent: show_hundredths(r.expansion_bp),
            sadaqa_percent: show_hundredths(r.sadaqa_bp),
        }
    }

    pub fn kk_close_rules(&self, space_id: &str) -> Result<KkCloseRulesDto, AppError> {
        let ctx = self.ctx()?;
        let scope = self.kk_scope(&ctx, space_id)?;
        let r = rules_or_default(self.db.read(|c| kk::close_rules(c, &scope))?);
        Ok(self.rules_dto(&ctx, &r))
    }

    /// Soliq zaxirasi (egasi kiritadi — ilova stavka tavsiya qilmaydi, OQ-K3) va taqsimot qoidasi.
    pub fn kk_set_close_rules(
        &self,
        space_id: &str,
        input: KkCloseRulesInput,
    ) -> Result<KkCloseRulesDto, AppError> {
        let ctx = self.ctx()?;
        let scope = self.kk_scope(&ctx, space_id)?;
        let pct = |s: &str, field: &str| -> Result<i64, AppError> {
            let bp = parse_hundredths(s, "INVALID_PERCENT", field)?;
            if bp > 10_000 {
                return Err(AppError::on("INVALID_PERCENT", field));
            }
            Ok(bp)
        };
        let (tax_bp, tax_fixed_minor) = match input.tax_base.as_str() {
            "NONE" => (0, 0),
            "REVENUE" | "PROFIT" => (
                pct(
                    input.tax_percent.as_deref().unwrap_or_default(),
                    "taxPercent",
                )?,
                0,
            ),
            "FIXED" => {
                let raw = input.tax_fixed.as_deref().unwrap_or_default();
                let m = parse_amount(raw, ctx.currency)
                    .map_err(|e| AppError::on(e.code(), "taxFixed"))?;
                if m.is_negative() {
                    return Err(AppError::on("AMOUNT_NEGATIVE", "taxFixed"));
                }
                (0, m.minor())
            }
            _ => return Err(AppError::on("INVALID_TAX_BASE", "taxBase")),
        };
        let row = kk::KkCloseRulesRow {
            tax_base: input.tax_base.clone(),
            tax_bp,
            tax_fixed_minor,
            reserve_bp: pct(&input.reserve_percent, "reservePercent")?,
            working_bp: pct(&input.working_percent, "workingPercent")?,
            expansion_bp: pct(&input.expansion_percent, "expansionPercent")?,
            sadaqa_bp: pct(&input.sadaqa_percent, "sadaqaPercent")?,
        };
        split(&row).validate()?;
        let id = self.new_id();
        let meta = self.meta();
        self.db.write(|tx| {
            kk::upsert_close_rules(tx, &scope, &id, ctx.currency.code(), &row, &meta)
        })?;
        self.publish(Some(space_id), &[Topic::Kasbkor]);
        Ok(self.rules_dto(&ctx, &row))
    }

    /// Yopiladigan davr: berilgan sana tushgan davr, yoki — o'tgan davr. Davr tugagan, hali yopilmagan
    /// va undan keyingi davr yopilmagan bo'lishi shart.
    fn kk_close_period(
        &self,
        ctx: &Ctx,
        scope: &SpaceScope,
        period_start: Option<&str>,
    ) -> Result<NaiveDate, AppError> {
        let today = self.today(ctx);
        let day = match period_start {
            Some(p) => NaiveDate::parse_from_str(p, "%Y-%m-%d")
                .map_err(|_| AppError::on("INVALID_DATE", "periodStart"))?,
            None => {
                let (start, _) = month_period(today, ctx.month_start_day)
                    .ok_or(AppError::new("INVALID_PERIOD"))?;
                start.pred_opt().ok_or(AppError::new("INVALID_PERIOD"))?
            }
        };
        let (start, end) =
            month_period(day, ctx.month_start_day).ok_or(AppError::new("INVALID_PERIOD"))?;
        if end > today {
            return Err(AppError::on("PERIOD_NOT_ENDED", "periodStart"));
        }
        let closes = self.db.read(|c| kk::closes(c, scope))?;
        if closes.iter().any(|c| c.period_start == ymd(start)) {
            return Err(AppError::on("ALREADY_CLOSED", "periodStart"));
        }
        if closes.iter().any(|c| c.period_start > ymd(start)) {
            return Err(AppError::on("LATER_PERIOD_CLOSED", "periodStart"));
        }
        Ok(start)
    }

    fn kk_close_record(
        &self,
        ctx: &Ctx,
        scope: &SpaceScope,
        start: NaiveDate,
        carry: bool,
        explanation: Option<String>,
    ) -> Result<CloseRecord, AppError> {
        let p = self.kk_period(ctx, scope, start)?;
        let rules = rules_or_default(self.db.read(|c| kk::close_rules(c, scope))?);
        // K5: tovar xaridi emas, sotilgan tovar tannarxi va tovar yo'qotishlari chiqimga qo'shiladi.
        let expenses =
            p.r.expenses
                .checked_add(p.cogs)?
                .checked_add(p.p.stock_losses)?
                .clamp_non_negative();
        let c = month_close(CloseInput {
            revenue: p.r.revenue,
            expenses,
            depreciation: p.p.depreciation,
            owner_salary: p.salary,
            owner_paid: p.r.owner_paid,
            tax: tax_rule(&rules, ctx.currency)?,
            rule: split(&rules),
            carry_overdraw: carry,
        })?;
        Ok(CloseRecord {
            v: 2,
            period_start: ymd(p.start),
            period_end: ymd(p.last),
            currency: ctx.currency.code().to_string(),
            revenue: p.r.revenue.minor(),
            expenses: expenses.minor(),
            depreciation: p.p.depreciation.minor(),
            true_profit: p.p.true_profit.minor(),
            owner_salary: p.base_salary.is_positive().then(|| p.salary.minor()),
            owner_paid: p.r.owner_paid.minor(),
            salary_remaining: p.r.salary_remaining.map(|m| m.minor()),
            tax_base: rules.tax_base.clone(),
            tax_bp: rules.tax_bp,
            tax_fixed: rules.tax_fixed_minor,
            tax: c.tax.minor(),
            owner_pay: c.owner_pay.minor(),
            overdrawn: c.overdrawn.minor(),
            carry_forward: c.carry_forward.minor(),
            remaining: c.remaining.minor(),
            rule: [
                rules.reserve_bp,
                rules.working_bp,
                rules.expansion_bp,
                rules.sadaqa_bp,
            ],
            allocation: c.allocation.map(|a| {
                [
                    a.reserve.minor(),
                    a.working.minor(),
                    a.expansion.minor(),
                    a.sadaqa.minor(),
                ]
            }),
            reserve_below_depreciation: c.reserve_below_depreciation,
            explanation,
            owner_labor: Some(p.owner_labor.minor()),
        })
    }

    /// Yopilgan oylar raqamlari (eskisi birinchi): konvertlar va kengayish darvozasi uchun (K7).
    pub(crate) fn kk_close_figures(
        &self,
        ctx: &Ctx,
        scope: &SpaceScope,
    ) -> Result<Vec<CloseFigures>, AppError> {
        let mut out = Vec::new();
        for row in self
            .db
            .read(|c| kk::closes(c, scope))?
            .into_iter()
            .filter(|r| r.currency == ctx.currency.code())
            .rev()
        {
            let r: CloseRecord =
                serde_json::from_str(&row.result_json).map_err(|_| AppError::new("CORRUPT_ROW"))?;
            out.push(CloseFigures {
                closed_on: row.closed_at.get(..10).unwrap_or_default().to_string(),
                tax: r.tax,
                allocation: r.allocation.unwrap_or([0; 4]),
                true_profit: r.true_profit,
            });
        }
        Ok(out)
    }

    /// «Sarmoya (o'qish)» belgili chiqimlar jami (K9, 8A.3) har davr `[boshi, oxirgi kun]` uchun —
    /// barcha davrlar bitta so'rov bilan. Yopilgan oy yozuvlari o'zgarmaydi, shuning uchun qator
    /// bayonnoma xeshiga kirmaydi va har safar hisoblanadi.
    pub(crate) fn kk_self_investment_totals(
        &self,
        ctx: &Ctx,
        scope: &SpaceScope,
        periods: &[(String, String)],
    ) -> Result<Vec<Money>, AppError> {
        let cur = ctx.currency;
        let (Some(from), Some(last)) = (
            periods.iter().map(|p| p.0.as_str()).min(),
            periods.iter().map(|p| p.1.as_str()).max(),
        ) else {
            return Ok(Vec::new());
        };
        let rows = self
            .db
            .read(|c| expenses::self_investment_between(c, scope, from, last))?;
        periods
            .iter()
            .map(|(start, end)| {
                Money::sum(
                    rows.iter()
                        .filter(|(on, c, _)| c == cur.code() && on >= start && on <= end)
                        .map(|(_, _, v)| Money::new(*v, cur)),
                    cur,
                )
                .map_err(AppError::from)
            })
            .collect()
    }

    fn kk_self_investment(
        &self,
        ctx: &Ctx,
        scope: &SpaceScope,
        r: &CloseRecord,
    ) -> Result<Money, AppError> {
        let one = [(r.period_start.clone(), r.period_end.clone())];
        Ok(self.kk_self_investment_totals(ctx, scope, &one)?[0])
    }

    /// Oxirgi ko'pi bilan `n` ta yopilgan oy (yangisidan eskisiga): qotirilgan bayonnoma raqamlari —
    /// (boshi, oxirgi kun, o'z mehnati bahosi, haqiqiy foyda). v1 bayonnomada o'z mehnati saqlanmagan —
    /// hozirgi sozlama olinadi (kasbkor/SPEC 8A.4).
    pub(crate) fn kk_closed_owner_months(
        &self,
        ctx: &Ctx,
        scope: &SpaceScope,
        n: usize,
    ) -> Result<Vec<(String, String, Money, Money)>, AppError> {
        let cur = ctx.currency;
        let current_labor = self
            .db
            .read(|c| kk::settings(c, scope))?
            .map_or(0, |s| s.owner_labor_minor);
        self.db
            .read(|c| kk::closes(c, scope))?
            .iter()
            .filter(|r| r.currency == cur.code())
            .take(n)
            .map(|row| {
                let r = Self::close_record(row)?;
                Ok((
                    r.period_start,
                    r.period_end,
                    Money::new(r.owner_labor.unwrap_or(current_labor), cur),
                    Money::new(r.true_profit, cur),
                ))
            })
            .collect()
    }

    fn draft_dto(&self, ctx: &Ctx, r: &CloseRecord, self_investment: Money) -> KkCloseDraftDto {
        let m = |minor: i64| self.money_dto(ctx, Money::new(minor, ctx.currency));
        let rules = kk::KkCloseRulesRow {
            tax_base: r.tax_base.clone(),
            tax_bp: r.tax_bp,
            tax_fixed_minor: r.tax_fixed,
            reserve_bp: r.rule[0],
            working_bp: r.rule[1],
            expansion_bp: r.rule[2],
            sadaqa_bp: r.rule[3],
        };
        KkCloseDraftDto {
            period_start: r.period_start.clone(),
            period_end: r.period_end.clone(),
            revenue: m(r.revenue),
            expenses: m(r.expenses),
            depreciation: m(r.depreciation),
            true_profit: m(r.true_profit),
            owner_salary: r.owner_salary.map(m),
            owner_paid: m(r.owner_paid),
            salary_remaining: r.salary_remaining.map(m),
            rules: self.rules_dto(ctx, &rules),
            tax: m(r.tax),
            owner_pay: m(r.owner_pay),
            overdrawn: (r.overdrawn > 0).then(|| m(r.overdrawn)),
            remaining: m(r.remaining),
            needs_explanation: r.remaining < 0,
            allocation: r.allocation.map(|a| KkAllocationDto {
                reserve: m(a[0]),
                working: m(a[1]),
                expansion: m(a[2]),
                sadaqa: m(a[3]),
            }),
            reserve_below_depreciation: r.reserve_below_depreciation,
            self_investment: self.money_dto(ctx, self_investment),
        }
    }

    fn close_record(row: &kk::KkCloseRow) -> Result<CloseRecord, AppError> {
        serde_json::from_str(&row.result_json).map_err(|_| AppError::new("CORRUPT_ROW"))
    }

    fn close_dto(
        &self,
        ctx: &Ctx,
        row: &kk::KkCloseRow,
        r: &CloseRecord,
        self_investment: Money,
    ) -> KkMonthCloseDto {
        KkMonthCloseDto {
            id: row.id.clone(),
            closed_at: row.closed_at.clone(),
            summary: self.draft_dto(ctx, r, self_investment),
            carry_forward: self.money_dto(ctx, Money::new(row.carry_minor, ctx.currency)),
            explanation: row.explanation.clone(),
            short_code: short_code(&row.content_hash),
        }
    }

    /// «Hisob kuni» hisobi (hech narsa saqlanmaydi). `period_start` bo'lmasa — o'tgan oy.
    pub fn kk_close_draft(
        &self,
        space_id: &str,
        period_start: Option<String>,
    ) -> Result<KkCloseDraftDto, AppError> {
        let ctx = self.ctx()?;
        let scope = self.kk_scope(&ctx, space_id)?;
        let start = self.kk_close_period(&ctx, &scope, period_start.as_deref())?;
        let r = self.kk_close_record(&ctx, &scope, start, false, None)?;
        let invested = self.kk_self_investment(&ctx, &scope, &r)?;
        Ok(self.draft_dto(&ctx, &r, invested))
    }

    /// Oyni yopish: bayonnoma yoziladi va o'zgarmaydi. Qolgan pul manfiy bo'lsa — izoh majburiy.
    pub fn kk_close_month(
        &self,
        space_id: &str,
        input: KkCloseInput,
    ) -> Result<KkMonthCloseDto, AppError> {
        let ctx = self.ctx()?;
        let scope = self.kk_scope(&ctx, space_id)?;
        let start = self.kk_close_period(&ctx, &scope, Some(&input.period_start))?;
        let explanation = clean_opt(input.explanation.as_deref());
        if explanation
            .as_ref()
            .is_some_and(|e| e.chars().count() > 1000)
        {
            return Err(AppError::on("TOO_LONG", "explanation"));
        }
        let r = self.kk_close_record(
            &ctx,
            &scope,
            start,
            input.carry_overdraw,
            explanation.clone(),
        )?;
        if r.remaining < 0 && explanation.is_none() {
            return Err(AppError::on("REQUIRED", "explanation"));
        }
        let json = serde_json::to_string(&r).map_err(|_| AppError::new("CORRUPT_ROW"))?;
        let prev = self
            .db
            .read(|c| kk::closes(c, &scope))?
            .into_iter()
            .next()
            .map_or_else(|| GENESIS_HASH.to_string(), |c| c.content_hash);
        let row = kk::KkCloseRow {
            id: self.new_id(),
            period_start: r.period_start.clone(),
            period_end: r.period_end.clone(),
            currency: r.currency.clone(),
            remaining_minor: r.remaining,
            carry_minor: r.carry_forward,
            reserve_minor: r.allocation.map_or(0, |a| a[0]),
            explanation,
            content_hash: content_hash(&prev, &json),
            result_json: json,
            prev_hash: prev,
            closed_at: self.meta().now,
        };
        let meta = self.meta();
        self.db
            .write(|tx| kk::insert_close(tx, &scope, &row, &meta))?;
        self.publish(Some(space_id), &[Topic::Kasbkor]);
        let invested = self.kk_self_investment(&ctx, &scope, &r)?;
        Ok(self.close_dto(&ctx, &row, &r, invested))
    }

    /// Bayonnomalar (yangisi birinchi).
    pub fn kk_month_closes(&self, space_id: &str) -> Result<Vec<KkMonthCloseDto>, AppError> {
        let ctx = self.ctx()?;
        let scope = self.kk_scope(&ctx, space_id)?;
        let rows: Vec<kk::KkCloseRow> = self
            .db
            .read(|c| kk::closes(c, &scope))?
            .into_iter()
            .filter(|r| r.currency == ctx.currency.code())
            .collect();
        let records = rows
            .iter()
            .map(Self::close_record)
            .collect::<Result<Vec<_>, _>>()?;
        // «Sarmoya (o'qish)» qatori — barcha bayonnomalar uchun bitta so'rov.
        let periods: Vec<(String, String)> = records
            .iter()
            .map(|r| (r.period_start.clone(), r.period_end.clone()))
            .collect();
        let invested = self.kk_self_investment_totals(&ctx, &scope, &periods)?;
        Ok(rows
            .iter()
            .zip(&records)
            .zip(invested)
            .map(|((row, r), m)| self.close_dto(&ctx, row, r, m))
            .collect())
    }

    /// Bayonnoma PDF'i (chop etish uchun oq fonda). Zanjir boshi QR va qisqa kod bilan.
    pub fn kk_month_close_pdf(&self, space_id: &str, close_id: &str) -> Result<Vec<u8>, AppError> {
        let ctx = self.ctx()?;
        let scope = self.kk_scope(&ctx, space_id)?;
        let row = self
            .db
            .read(|c| kk::closes(c, &scope))?
            .into_iter()
            .find(|r| r.id == close_id)
            .ok_or(AppError::on("NOT_FOUND", "id"))?;
        let r = Self::close_record(&row)?;
        let invested = self.kk_self_investment(&ctx, &scope, &r)?;
        let d = self.draft_dto(&ctx, &r, invested);
        let business = self
            .db
            .read(household::get_household)?
            .map(|h| h.name)
            .unwrap_or_default();
        let neg = |s: &str| format!("− {s}");
        let mut totals = vec![
            ("kkclose.revenue".to_string(), d.revenue.formatted.clone()),
            ("kkclose.tax".to_string(), neg(&d.tax.formatted)),
            ("kkclose.expenses".to_string(), neg(&d.expenses.formatted)),
            ("kkclose.ownerPay".to_string(), neg(&d.owner_pay.formatted)),
            (
                "kkclose.remaining".to_string(),
                d.remaining.formatted.clone(),
            ),
            (
                "kkclose.trueProfit".to_string(),
                d.true_profit.formatted.clone(),
            ),
            (
                "kkclose.depreciation".to_string(),
                d.depreciation.formatted.clone(),
            ),
        ];
        if d.self_investment.minor != "0" {
            totals.push((
                "kkclose.selfInvestment".to_string(),
                d.self_investment.formatted.clone(),
            ));
        }
        if let Some(o) = &d.overdrawn {
            totals.push(("kkclose.overdrawn".to_string(), o.formatted.clone()));
        }
        if row.carry_minor > 0 {
            totals.push((
                "kkclose.carry".to_string(),
                self.money_dto(&ctx, Money::new(row.carry_minor, ctx.currency))
                    .formatted,
            ));
        }
        let tax_rule = match r.tax_base.as_str() {
            "REVENUE" | "PROFIT" => format!("{} %", format_percent_bp(r.tax_bp)),
            "FIXED" => {
                self.money_dto(&ctx, Money::new(r.tax_fixed, ctx.currency))
                    .formatted
            }
            _ => "—".to_string(),
        };
        let rule = vec![
            (format!("kkclose.taxBase.{}", r.tax_base), tax_rule),
            (
                "kkclose.split".to_string(),
                r.rule
                    .iter()
                    .map(|bp| format_percent_bp(*bp))
                    .collect::<Vec<_>>()
                    .join(" / ")
                    + " %",
            ),
        ];
        let allocation = d.allocation.as_ref().map(|a| {
            vec![
                ("kkclose.reserve".to_string(), a.reserve.formatted.clone()),
                ("kkclose.working".to_string(), a.working.formatted.clone()),
                (
                    "kkclose.expansion".to_string(),
                    a.expansion.formatted.clone(),
                ),
                ("kkclose.sadaqa".to_string(), a.sadaqa.formatted.clone()),
            ]
        });
        let mut notes = Vec::new();
        if r.reserve_below_depreciation {
            notes.push("kkclose.reserveBelowDepreciation".to_string());
        }
        let doc = KkCloseReport {
            ident: row.id.clone(),
            locale: pdf_locale(ctx.locale),
            business,
            period: format!("{} — {}", show(&r.period_start), show(&r.period_end)),
            closed_on: show(row.closed_at.get(..10).unwrap_or_default()),
            totals,
            rule,
            allocation,
            notes,
            explanation: row.explanation.clone(),
            chain_head: row.content_hash.clone(),
            chain_short_code: short_code(&row.content_hash),
        };
        let today = NaiveDate::parse_from_str(&r.period_end, "%Y-%m-%d")
            .map_err(|_| AppError::new("CORRUPT_ROW"))?;
        let rendered = doc
            .render(engine(), today)
            .map_err(|e| AppError::new(e.code))?;
        Ok(rendered.pdf)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    /// v1 bayonnoma (K9 dan oldin) o'z mehnatisiz o'qiladi va qayta yozilmaydi (xesh — saqlangan matndan).
    #[test]
    fn v1_record_has_no_owner_labor() {
        let v1 = r#"{"v":1,"period_start":"2026-11-01","period_end":"2026-11-30","currency":"UZS",
            "revenue":1,"expenses":0,"depreciation":0,"true_profit":1,"owner_salary":null,"owner_paid":0,
            "salary_remaining":null,"tax_base":"NONE","tax_bp":0,"tax_fixed":0,"tax":0,"owner_pay":0,
            "overdrawn":0,"carry_forward":0,"remaining":1,"rule":[10000,0,0,0],"allocation":null,
            "reserve_below_depreciation":false,"explanation":null}"#;
        let r: CloseRecord = serde_json::from_str(v1).unwrap();
        assert_eq!(r.owner_labor, None);
        let v2 = serde_json::to_string(&CloseRecord {
            v: 2,
            owner_labor: Some(5),
            ..r
        })
        .unwrap();
        assert!(v2.ends_with(r#""owner_labor":5}"#));
    }

    #[test]
    fn hash_chains_previous() {
        let a = content_hash(GENESIS_HASH, "{}");
        assert_eq!(a.len(), 64);
        assert_ne!(a, content_hash(&a, "{}"));
    }
}
