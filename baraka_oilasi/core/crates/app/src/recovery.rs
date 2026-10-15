//! 4-qonun use-case'lari (U9): `DEBT_RECOVERY` 70/20/10 rejimi, qarzdan chiqish rejalovchisi,
//! yopish tartibi, «Qarzsiz kun», qarz to'lovchilari va sotiladigan buyumlar.
//!
//! Hisob `domain-uy::payoff` da (vektorlar `payoff_projection`, `payoff_plan`); bu yerda faqat
//! ma'lumotni yig'ish, saqlash va DTO. Natija — taxminiy hisob (bank shartlari farq qilishi mumkin).
use baraka_domain_common::month_period;
use baraka_domain_uy::debt::{due_between, true_cost, PlanKind, TrueCostInput};
use baraka_domain_uy::payoff::{default_order, payoff_plan, OrderKey, PlanDebt, PlanTotals};
use baraka_domain_uy::recovery::RecoverySplit;
use baraka_money::{format_percent_bp, Currency, Money};
use baraka_storage::repo::debts::{self, Owner};
use baraka_storage::repo::recovery::{self, BudgetRow, ContributorRow, ItemRow};
use baraka_storage::SpaceScope;

use crate::app::Ctx;
use crate::events::Topic;
use crate::receipt::{amount_in, positive, ymd};
use crate::text::{clean_opt, required};
use crate::*;

const STANDARD: &str = "STANDARD";
const DEBT_RECOVERY: &str = "DEBT_RECOVERY";

fn bp32(v: i64) -> Result<i32, AppError> {
    i32::try_from(v).map_err(|_| AppError::new("CORRUPT_ROW"))
}

/// Rejalovchiga kiradigan qarz.
pub(crate) struct Planned {
    row: debts::DebtRow,
    ribo: bool,
    cost_bp: i64,
    payoff: Option<chrono::NaiveDate>,
    fee_bp: i64,
    plan: PlanDebt,
}

impl App {
    /// Faol, asosiy valyutadagi qarzlar — yopish tartibida. Ikkinchi qiymat — boshqa valyutadagi
    /// faol qarzlar soni (rejaga kirmaydi).
    fn planned_debts(
        &self,
        ctx: &Ctx,
        scope: &SpaceScope,
    ) -> Result<(Vec<Planned>, u32), AppError> {
        let mut out = Vec::new();
        let mut foreign = 0u32;
        for d in self.db.read(|c| debts::list_debts(c, scope))? {
            if d.status != "ACTIVE" {
                continue;
            }
            if d.currency != ctx.currency.code() {
                foreign += 1;
                continue;
            }
            let l = self.debt_ledger(scope, &d)?;
            let v = self.view(ctx, &l, None)?;
            let bank = matches!(
                PlanKind::parse(&d.plan_kind),
                Some(PlanKind::Annuity | PlanKind::Differentiated)
            );
            let ribo = if bank {
                d.annual_bp > 0
            } else {
                d.markup_minor > 0
            };
            // Qarz «narxi»: bank qarzida yillik stavka, ustamalida ortiqcha to'lov ulushi.
            let cost_bp = if bank {
                d.annual_bp
            } else {
                let cur = l.currency;
                let paid = l.paid()?;
                true_cost(&TrueCostInput {
                    principal: Money::new(d.principal_minor, cur),
                    original_principal: Some(Money::new(d.original_principal_minor, cur)),
                    paid_before: Money::new(d.paid_before_minor, cur),
                    plan_total: paid.checked_add(v.status.remaining)?,
                    paid_since: paid,
                })?
                .overpay_bp
            };
            out.push(Planned {
                ribo,
                cost_bp,
                payoff: v.status.payoff_date,
                fee_bp: d.prepayment_fee_bp,
                plan: PlanDebt {
                    id: d.id.clone(),
                    state: v.state,
                    fee_bp: d.prepayment_fee_bp,
                },
                row: d,
            });
        }
        let order = default_order(
            &out.iter()
                .map(|p| OrderKey {
                    id: p.row.id.clone(),
                    ribo: p.ribo,
                    cost_bp: p.cost_bp,
                    payoff_date: p.payoff,
                    priority: p.row.priority,
                })
                .collect::<Vec<_>>(),
        );
        out.sort_by_key(|p| order.iter().position(|id| *id == p.row.id));
        Ok((out, foreign))
    }

    /// `debts_overview` uchun: tartiblangan rejalar (qo'shimcha to'lovsiz «Qarzsiz kun»).
    pub(crate) fn plan_debts(
        &self,
        ctx: &Ctx,
        scope: &SpaceScope,
    ) -> Result<(Vec<PlanDebt>, u32), AppError> {
        let (p, f) = self.planned_debts(ctx, scope)?;
        Ok((p.into_iter().map(|p| p.plan).collect(), f))
    }

    /// `DEBT_RECOVERY` dagi oylik qo'shimcha to'lov: daromadning `extra_debt_bp` ulushi.
    pub(crate) fn recovery_extra(
        &self,
        ctx: &Ctx,
        scope: &SpaceScope,
        b: &BudgetRow,
    ) -> Result<Money, AppError> {
        let income = self.monthly_income(ctx, scope)?;
        Ok(Self::split_of(Some(b)).apply(income)?.extra_debt)
    }

    fn split_of(b: Option<&BudgetRow>) -> RecoverySplit {
        b.map_or_else(RecoverySplit::default, |b| RecoverySplit {
            household_bp: b.household_bp,
            extra_debt_bp: b.extra_debt_bp,
            savings_bp: b.savings_bp,
        })
    }

    /// Byudjet rejimi va 70/20/10 bo'yicha shu oy taqsimoti.
    pub fn budget_mode(&self, space_id: &str) -> Result<BudgetModeDto, AppError> {
        let ctx = self.ctx()?;
        let scope = self.scope(&ctx, space_id)?;
        let b = self.db.read(|c| recovery::budget(c, &scope))?;
        let split = Self::split_of(b.as_ref());
        let mode = b.as_ref().map_or(STANDARD, |b| b.mode.as_str()).to_string();
        let has_active_debt = self
            .db
            .read(|c| debts::list_debts(c, &scope))?
            .iter()
            .any(|d| d.status == "ACTIVE");
        let income = self.monthly_income(&ctx, &scope)?;
        let parts = split.apply(income)?;
        let (start, end) = month_period(self.today(&ctx), ctx.month_start_day)
            .ok_or(AppError::new("INVALID_PERIOD"))?;
        let mut mandatory = Money::zero(ctx.currency);
        for p in self.planned_debts(&ctx, &scope)?.0 {
            let l = self.debt_ledger(&scope, &p.row)?;
            let v = self.view(&ctx, &l, None)?;
            mandatory =
                mandatory.checked_add(due_between(&v.installments, start, end, ctx.currency)?)?;
        }
        let after = parts.household.checked_sub(mandatory)?;
        let d = |m: Money| self.money_dto(&ctx, m);
        Ok(BudgetModeDto {
            suggested: has_active_debt && mode == STANDARD,
            mode,
            household_bp: bp32(split.household_bp)?,
            extra_debt_bp: bp32(split.extra_debt_bp)?,
            savings_bp: bp32(split.savings_bp)?,
            household_percent: format_percent_bp(split.household_bp),
            extra_debt_percent: format_percent_bp(split.extra_debt_bp),
            savings_percent: format_percent_bp(split.savings_bp),
            has_active_debt,
            monthly_income: income.is_positive().then(|| d(income)),
            household: d(parts.household),
            extra_debt: d(parts.extra_debt),
            savings: d(parts.savings),
            mandatory_debt_payments: d(mandatory),
            household_after_debts: d(after),
            household_short: after.is_negative(),
            changed_on: b.map(|b| b.changed_on),
        })
    }

    /// Rejimni o'zgartirish. Jamg'arma ulushi 1% dan kam bo'lmaydi; `DEBT_RECOVERY` faqat
    /// faol qarz bo'lsa yoqiladi.
    pub fn set_budget_mode(
        &self,
        space_id: &str,
        input: BudgetModeInput,
    ) -> Result<BudgetModeDto, AppError> {
        let ctx = self.ctx()?;
        let scope = self.scope(&ctx, space_id)?;
        if input.mode != STANDARD && input.mode != DEBT_RECOVERY {
            return Err(AppError::on("INVALID_MODE", "mode"));
        }
        let split = RecoverySplit {
            household_bp: i64::from(input.household_bp),
            extra_debt_bp: i64::from(input.extra_debt_bp),
            savings_bp: i64::from(input.savings_bp),
        };
        split.validate()?;
        if input.mode == DEBT_RECOVERY
            && !self
                .db
                .read(|c| debts::list_debts(c, &scope))?
                .iter()
                .any(|d| d.status == "ACTIVE")
        {
            return Err(AppError::on("NO_ACTIVE_DEBT", "mode"));
        }
        let row = BudgetRow {
            mode: input.mode,
            household_bp: split.household_bp,
            extra_debt_bp: split.extra_debt_bp,
            savings_bp: split.savings_bp,
            changed_on: ymd(self.today(&ctx)),
        };
        let id = self.new_id();
        let meta = self.meta();
        self.db
            .write(|tx| recovery::upsert_budget(tx, &scope, &id, &row, &meta))?;
        self.publish(Some(space_id), &[Topic::Budget]);
        self.budget_mode(space_id)
    }

    fn totals_dto(&self, ctx: &Ctx, t: &PlanTotals) -> PlanTotalsDto {
        PlanTotalsDto {
            payoff_date: t.payoff_date.map(ymd),
            months: t.months,
            interest: self.money_dto(ctx, t.interest),
            fees: self.money_dto(ctx, t.fees),
            paid: self.money_dto(ctx, t.paid),
        }
    }

    /// Qarzdan chiqish rejalovchisi: odatiy va qo'shimcha to'lovli prognoz yonma-yon,
    /// «N oy erta», «X so'm tejaldi», har bir qarz va umumiy «Qarzsiz kun».
    pub fn payoff_planner(
        &self,
        space_id: &str,
        input: PlannerInput,
    ) -> Result<PlannerDto, AppError> {
        let ctx = self.ctx()?;
        let scope = self.scope(&ctx, space_id)?;
        let cur = ctx.currency;
        let today = self.today(&ctx);
        let (planned, foreign) = self.planned_debts(&ctx, &scope)?;
        let (extra, source) = match input.extra_per_month.as_deref().map(str::trim) {
            Some(s) if !s.is_empty() => {
                let m = amount_in(s, cur, "extraPerMonth")?;
                if m.is_negative() {
                    return Err(AppError::on("EXTRA_NEGATIVE", "extraPerMonth"));
                }
                (m, "MANUAL")
            }
            _ => match self.db.read(|c| recovery::budget(c, &scope))? {
                Some(b) if b.mode == DEBT_RECOVERY => {
                    (self.recovery_extra(&ctx, &scope, &b)?, "RECOVERY_SHARE")
                }
                _ => (Money::zero(cur), "NONE"),
            },
        };
        let plans = || planned.iter().map(|p| p.plan.clone()).collect::<Vec<_>>();
        let (base_per, base) = payoff_plan(plans(), today, Money::zero(cur))?;
        let (acc_per, acc) = payoff_plan(plans(), today, extra)?;
        let interest_saved = base.interest.checked_sub(acc.interest)?;
        let d = |m: Money| self.money_dto(&ctx, m);
        let debts = planned
            .iter()
            .zip(base_per.iter().zip(acc_per.iter()))
            .zip(1u32..)
            .map(|((p, (b, a)), order)| {
                Ok(PlannerDebtDto {
                    id: p.row.id.clone(),
                    creditor: p.row.creditor.clone(),
                    is_ribo: p.ribo,
                    order,
                    manual_order: p.row.priority.is_some(),
                    balance: d(p.plan.state.balance()),
                    base_payoff: b.payoff_date.map(ymd),
                    accelerated_payoff: a.payoff_date.map(ymd),
                    months_saved: i32::try_from(i64::from(b.months) - i64::from(a.months))
                        .map_err(|_| AppError::new("OVERFLOW"))?,
                    interest_saved: d(b.interest.checked_sub(a.interest)?),
                    fees: d(a.fees),
                    prepayment_fee_bp: bp32(p.fee_bp)?,
                })
            })
            .collect::<Result<Vec<_>, AppError>>()?;
        let n = base.timeline.len().max(acc.timeline.len());
        let zero = Money::zero(cur);
        let timeline = (0..n)
            .filter_map(|i| {
                let month = base
                    .timeline
                    .get(i)
                    .or_else(|| acc.timeline.get(i))
                    .map(|w| w.month)?;
                Some(TimelinePointDto {
                    month: ymd(month),
                    base_balance: d(base.timeline.get(i).map_or(zero, |w| w.balance)),
                    accelerated_balance: d(acc.timeline.get(i).map_or(zero, |w| w.balance)),
                })
            })
            .collect();
        let schedule = acc
            .timeline
            .iter()
            .map(|w| TimelineRowDto {
                month: ymd(w.month),
                due: d(w.due),
                interest: d(w.interest),
                extra: d(w.extra),
                fee: d(w.fee),
                balance: d(w.balance),
            })
            .collect();
        Ok(PlannerDto {
            extra_per_month: d(extra),
            extra_source: source.to_string(),
            months_saved: i32::try_from(i64::from(base.months) - i64::from(acc.months))
                .map_err(|_| AppError::new("OVERFLOW"))?,
            net_saved: d(interest_saved.checked_sub(acc.fees)?),
            interest_saved: d(interest_saved),
            base: self.totals_dto(&ctx, &base),
            accelerated: self.totals_dto(&ctx, &acc),
            debts,
            timeline,
            schedule,
            excluded_foreign: foreign,
        })
    }

    /// Yopish tartibini qo'lda belgilash: ro'yxatdagi birinchi qarz — 1.
    pub fn set_debt_order(&self, space_id: &str, debt_ids: Vec<String>) -> Result<(), AppError> {
        let ctx = self.ctx()?;
        let scope = self.scope(&ctx, space_id)?;
        let meta = self.meta();
        self.db.write(|tx| {
            for (id, n) in debt_ids.iter().zip(1i64..) {
                debts::set_priority(tx, &scope, id, Some(n), &meta)?;
            }
            Ok(())
        })?;
        self.publish(Some(space_id), &[Topic::Debts]);
        Ok(())
    }

    /// Standart tartibga qaytish (foizli qarzlar birinchi).
    pub fn reset_debt_order(&self, space_id: &str) -> Result<(), AppError> {
        let ctx = self.ctx()?;
        let scope = self.scope(&ctx, space_id)?;
        let ids: Vec<String> = self
            .db
            .read(|c| debts::list_debts(c, &scope))?
            .into_iter()
            .filter(|d| d.priority.is_some())
            .map(|d| d.id)
            .collect();
        let meta = self.meta();
        self.db.write(|tx| {
            for id in &ids {
                debts::set_priority(tx, &scope, id, None, &meta)?;
            }
            Ok(())
        })?;
        self.publish(Some(space_id), &[Topic::Debts]);
        Ok(())
    }

    /// Qarzni to'lashga yelkadosh (masalan, alohida yashaydigan o'g'il).
    pub fn add_contributor(
        &self,
        space_id: &str,
        debt_id: &str,
        input: NewContributorInput,
    ) -> Result<ContributorDto, AppError> {
        let ctx = self.ctx()?;
        let scope = self.scope(&ctx, space_id)?;
        let d = self
            .db
            .read(|c| debts::get_debt(c, &scope, debt_id))?
            .ok_or(AppError::on("NOT_FOUND", "debtId"))?;
        let cur = Currency::from_code(&d.currency)?;
        let share = match input.monthly_share.as_deref().map(str::trim) {
            None | Some("") => None,
            Some(s) => Some(positive(s, cur, "monthlyShare")?),
        };
        let row = ContributorRow {
            id: self.new_id(),
            debt_id: d.id,
            name: required(&input.name, "name")?,
            monthly_share_minor: share.map(|m| m.minor()),
            currency: cur.code().to_string(),
        };
        let meta = self.meta();
        self.db
            .write(|tx| recovery::insert_contributor(tx, &scope, &row, &meta))?;
        self.publish(Some(space_id), &[Topic::Debts]);
        Ok(ContributorDto {
            id: row.id,
            name: row.name,
            monthly_share: share.map(|m| self.money_dto(&ctx, m)),
            paid: self.money_dto(&ctx, Money::zero(cur)),
        })
    }

    fn item_dto(&self, ctx: &Ctx, i: ItemRow) -> Result<SellableItemDto, AppError> {
        let cur = Currency::from_code(&i.currency)?;
        Ok(SellableItemDto {
            id: i.id,
            title: i.title,
            estimated: self.money_dto(ctx, Money::new(i.estimated_minor, cur)),
            status: i.status,
            sold: i
                .sold_minor
                .map(|m| self.money_dto(ctx, Money::new(m, cur))),
            sold_on: i.sold_on,
            debt_id: i.debt_id,
        })
    }

    pub fn sellable_items(&self, space_id: &str) -> Result<Vec<SellableItemDto>, AppError> {
        let ctx = self.ctx()?;
        let scope = self.scope(&ctx, space_id)?;
        self.db
            .read(|c| recovery::items(c, &scope))?
            .into_iter()
            .map(|i| self.item_dto(&ctx, i))
            .collect()
    }

    /// Uyda ishlatilmayotgan buyum (uy/SPEC 2D.7).
    pub fn add_sellable_item(
        &self,
        space_id: &str,
        input: NewSellableItemInput,
    ) -> Result<SellableItemDto, AppError> {
        let ctx = self.ctx()?;
        let scope = self.scope(&ctx, space_id)?;
        let cur = Currency::from_code(&input.currency)?;
        let row = ItemRow {
            id: self.new_id(),
            title: required(&input.title, "title")?,
            estimated_minor: positive(&input.estimated, cur, "estimated")?.minor(),
            currency: cur.code().to_string(),
            status: "LISTED".to_string(),
            sold_minor: None,
            sold_on: None,
            debt_id: None,
            repayment_id: None,
        };
        let meta = self.meta();
        self.db
            .write(|tx| recovery::insert_item(tx, &scope, &row, &meta))?;
        self.publish(Some(space_id), &[Topic::Debts]);
        self.item_dto(&ctx, row)
    }

    /// Buyum sotildi. `debt_id` bo'lsa, pul shu qarzga muddatidan oldingi to'lov sifatida
    /// bir bosishda yo'naltiriladi (bitta tranzaksiyada).
    pub fn sell_item(
        &self,
        space_id: &str,
        item_id: &str,
        input: SellItemInput,
    ) -> Result<SellResultDto, AppError> {
        let ctx = self.ctx()?;
        let scope = self.scope(&ctx, space_id)?;
        let item = self
            .db
            .read(|c| recovery::get_item(c, &scope, item_id))?
            .ok_or(AppError::on("NOT_FOUND", "itemId"))?;
        if item.status != "LISTED" {
            return Err(AppError::new("ALREADY_SOLD"));
        }
        let cur = Currency::from_code(&item.currency)?;
        let price = positive(&input.price, cur, "price")?;
        let sold_on = ymd(self.date_or_today(&ctx, input.date.as_deref(), "date")?);
        let prepared = match input.debt_id.as_deref() {
            Some(debt_id) => Some(self.prepare_repayment(
                &ctx,
                &scope,
                Owner::Debt,
                debt_id,
                &RepaymentInput {
                    amount: input.price.clone(),
                    date: Some(sold_on.clone()),
                    is_prepayment: true,
                    note: clean_opt(Some(&item.title)),
                    contributor_id: None,
                },
            )?),
            None => None,
        };
        let meta = self.meta();
        let stored = self.db.write(|tx| {
            let stored = match &prepared {
                Some(p) => Some(Self::apply_repayment(tx, &scope, p, &meta)?),
                None => None,
            };
            recovery::mark_sold(
                tx,
                &scope,
                item_id,
                (price.minor(), &sold_on),
                (
                    input.debt_id.as_deref(),
                    prepared.as_ref().map(|p| p.row.id.as_str()),
                ),
                &meta,
            )?;
            Ok(stored)
        })?;
        let mut topics = vec![Topic::Debts];
        if prepared.is_some() {
            topics.extend([Topic::Journal, Topic::Budget]);
        }
        self.publish(Some(space_id), &topics);
        let item = self
            .db
            .read(|c| recovery::get_item(c, &scope, item_id))?
            .ok_or(AppError::new("NOT_FOUND"))?;
        Ok(SellResultDto {
            item: self.item_dto(&ctx, item)?,
            repayment: match (prepared, stored) {
                (Some(p), Some(s)) => Some(self.repayment_result(&ctx, p, s)),
                _ => None,
            },
        })
    }
}
