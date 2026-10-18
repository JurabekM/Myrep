//! K1 — Kasb-kor «ikki cho'ntak» (`docs/kasbkor/SPEC.md` 2): tushum, «egasi oldi», kapital kiritish,
//! hamyonlar (naqd kassa va karta), egasining qat'iy maoshi va uni Uy makoniga o'tkazish.
//!
//! Hisob `domain-kasbkor::owner` da (vektorlar `kk_owner_pay`); bu yerda ma'lumotni yig'ish,
//! saqlash va DTO. Chiqimlar — umumiy `record_expense` (Kasb-kor kategoriyalari bilan).
use baraka_domain_common::{month_period, SpaceKind};
use baraka_domain_kasbkor::owner::{month_report, MonthReport, Move, MoveKind, Wallet};
use baraka_domain_kasbkor::profit::{true_profit, ProfitInput, TrueProfit};
use baraka_money::Money;
use baraka_storage::repo::{expenses, household, incomes, kk, kk_ledger};
use baraka_storage::SpaceScope;
use chrono::NaiveDate;

use crate::app::Ctx;
use crate::events::Topic;
use crate::receipt::ymd;
use crate::text::clean_opt;
use crate::uy::{channel, positive};
use crate::*;

/// OQ-K2 (vaqtinchalik): egasi maoshi Uy'da mehnat daromadi.
const SALARY_SOURCE_TYPE: &str = "TER";
/// Uy makonidagi daromadning manbasi (makon nomi, barcha tillarda bir xil).
const SALARY_SOURCE: &str = "Kasb-kor";
const BEGINNING: &str = "0000-01-01";

pub(crate) fn wallet(s: &str, field: &str) -> Result<Wallet, AppError> {
    Wallet::parse(s).ok_or(AppError::on("INVALID_WALLET", field))
}

/// `CASH` / `CARD` kanal — hamyonning o'zi.
fn wallet_of_channel(s: &str) -> Wallet {
    Wallet::parse(s).unwrap_or(Wallet::Cash)
}

/// Bitta davr hisobi (`kk_period`).
pub(crate) struct Period {
    pub start: NaiveDate,
    pub last: NaiveDate,
    /// Belgilangan maosh (0 — yo'q).
    pub base_salary: Money,
    /// Shu oy maoshi: belgilangan − o'tgan oydan ushlangan.
    pub salary: Money,
    pub carry: Money,
    pub owner_labor: Money,
    pub r: MonthReport,
    pub p: TrueProfit,
    /// Sotilgan tovar tannarxi (K5).
    pub cogs: Money,
    pub entries: Vec<KkEntryDto>,
    pub has_activity: bool,
}

pub(crate) struct Book {
    pub opening_cash: Money,
    pub opening_card: Money,
    pub moves: Vec<Move>,
    pub entries: Vec<KkEntryDto>,
}

impl App {
    pub(crate) fn kk_scope(&self, ctx: &Ctx, space_id: &str) -> Result<SpaceScope, AppError> {
        let scope = self.scope(ctx, space_id)?;
        let kind = self
            .db
            .read(|c| household::list_spaces(c, &ctx.household_id))?
            .into_iter()
            .find(|s| s.id == space_id)
            .map(|s| s.kind);
        if kind.as_deref() != Some(SpaceKind::Kasbkor.as_str()) {
            return Err(AppError::on("NOT_KASBKOR_SPACE", "spaceId"));
        }
        Ok(scope)
    }

    fn kk_salary(&self, ctx: &Ctx, scope: &SpaceScope) -> Result<Money, AppError> {
        Ok(Money::new(
            self.db
                .read(|c| kk::settings(c, scope))?
                .map_or(0, |s| s.owner_salary_minor),
            ctx.currency,
        ))
    }

    /// `[from, to)` oralig'idagi barcha harakatlar; `OPENING` — boshlang'ich qoldiqqa.
    pub(crate) fn kk_book(
        &self,
        ctx: &Ctx,
        scope: &SpaceScope,
        from: &str,
        to: &str,
    ) -> Result<Book, AppError> {
        let cur = ctx.currency;
        let m = |minor: i64| Money::new(minor, cur);
        let mut book = Book {
            opening_cash: Money::zero(cur),
            opening_card: Money::zero(cur),
            moves: Vec::new(),
            entries: Vec::new(),
        };
        let entry =
            |id: &str, kind: &str, wallet: Wallet, to: Option<&str>, minor: i64, on: &str| {
                KkEntryDto {
                    id: id.to_string(),
                    kind: kind.to_string(),
                    wallet: wallet.as_str().to_string(),
                    to_wallet: to.map(str::to_string),
                    amount: self.money_dto(ctx, m(minor)),
                    occurred_on: on.to_string(),
                    note: None,
                    category_id: None,
                }
            };
        for r in self
            .db
            .read(|c| incomes::list_between(c, scope, from, to))?
            .into_iter()
            .filter(|r| r.currency == cur.code())
        {
            let w = wallet_of_channel(&r.channel);
            book.moves.push(Move {
                kind: MoveKind::Sale,
                wallet: w,
                amount: m(r.amount_minor),
            });
            let mut e = entry(&r.id, "SALE", w, None, r.amount_minor, &r.occurred_on);
            e.note = clean_opt(r.note.as_deref()).or_else(|| clean_opt(Some(&r.source)));
            book.entries.push(e);
        }
        for r in self
            .db
            .read(|c| expenses::list_between(c, scope, from, to))?
            .into_iter()
            .filter(|r| r.currency == cur.code())
        {
            let w = wallet_of_channel(&r.channel);
            book.moves.push(Move {
                kind: MoveKind::Expense,
                wallet: w,
                amount: m(r.amount_minor),
            });
            let mut e = entry(&r.id, "EXPENSE", w, None, r.amount_minor, &r.occurred_on);
            e.note = r.note.clone();
            e.category_id = Some(r.category_id.clone());
            book.entries.push(e);
        }
        for r in self
            .db
            .read(|c| kk::moves_between(c, scope, from, to))?
            .into_iter()
            .filter(|r| r.currency == cur.code())
        {
            let w = wallet(&r.wallet, "wallet")?;
            let mut e = entry(
                &r.id,
                &r.kind,
                w,
                r.to_wallet.as_deref(),
                r.amount_minor,
                &r.occurred_on,
            );
            e.note = r.note.clone();
            book.entries.push(e);
            let kind = match r.kind.as_str() {
                "OPENING" => {
                    match w {
                        Wallet::Cash => {
                            book.opening_cash = book.opening_cash.checked_add(m(r.amount_minor))?
                        }
                        Wallet::Card => {
                            book.opening_card = book.opening_card.checked_add(m(r.amount_minor))?
                        }
                    }
                    continue;
                }
                "OWNER_DRAW" => MoveKind::OwnerDraw,
                "OWNER_CONTRIBUTION" => MoveKind::OwnerContribution,
                "OWNER_SALARY" => MoveKind::OwnerSalary,
                "TRANSFER" => MoveKind::Transfer {
                    to: wallet(r.to_wallet.as_deref().unwrap_or_default(), "toWallet")?,
                },
                _ => return Err(AppError::new("CORRUPT_ROW")),
            };
            book.moves.push(Move {
                kind,
                wallet: w,
                amount: m(r.amount_minor),
            });
        }
        // Kassa yopishdagi farq (K4): naqd kassani tuzatadi, pul oqimiga kirmaydi.
        for r in self
            .db
            .read(|c| kk_ledger::cash_days_between(c, scope, from, to))?
            .into_iter()
            .filter(|r| r.currency == cur.code() && r.difference_minor != 0)
        {
            let (kind, k) = if r.difference_minor < 0 {
                (MoveKind::CashShort, "CASH_SHORT")
            } else {
                (MoveKind::CashOver, "CASH_OVER")
            };
            let amount = r
                .difference_minor
                .checked_abs()
                .ok_or(AppError::new("CORRUPT_ROW"))?;
            book.moves.push(Move {
                kind,
                wallet: Wallet::Cash,
                amount: m(amount),
            });
            let mut e = entry(&r.id, k, Wallet::Cash, None, amount, &r.day);
            e.note = r.note.clone();
            book.entries.push(e);
        }
        // Uskuna xaridi va sotuvi (K2): hamyondan pul chiqqan yoki tushgan bo'lsa.
        let in_range = |d: &str| d >= from && d < to;
        for r in self
            .db
            .read(|c| kk::equipment(c, scope))?
            .into_iter()
            .filter(|r| r.currency == cur.code())
        {
            if let Some(w) = r.wallet.as_deref().filter(|_| in_range(&r.acquired_on)) {
                let w = wallet(w, "wallet")?;
                book.moves.push(Move {
                    kind: MoveKind::EquipmentPurchase,
                    wallet: w,
                    amount: m(r.cost_minor),
                });
                let mut e = entry(
                    &r.id,
                    "EQUIPMENT_PURCHASE",
                    w,
                    None,
                    r.cost_minor,
                    &r.acquired_on,
                );
                e.note = Some(r.name.clone());
                book.entries.push(e);
            }
            if let (Some(on), Some(w), Some(p)) = (
                r.disposed_on.as_deref(),
                r.disposal_wallet.as_deref(),
                r.disposal_proceeds_minor,
            ) {
                if in_range(on) {
                    let w = wallet(w, "wallet")?;
                    book.moves.push(Move {
                        kind: MoveKind::EquipmentSale,
                        wallet: w,
                        amount: m(p),
                    });
                    let mut e = entry(&format!("{}-sale", r.id), "EQUIPMENT_SALE", w, None, p, on);
                    e.note = Some(r.name.clone());
                    book.entries.push(e);
                }
            }
        }
        // Tovar xaridi (K5): hamyondan to'langan bo'lsa.
        for (r, name) in self.kk_stock_purchases(ctx, scope, from, to)? {
            let w = wallet(r.wallet.as_deref().unwrap_or_default(), "wallet")?;
            let amount = r.amount_minor.ok_or(AppError::new("CORRUPT_ROW"))?;
            book.moves.push(Move {
                kind: MoveKind::StockPurchase,
                wallet: w,
                amount: m(amount),
            });
            let mut e = entry(&r.id, "STOCK_PURCHASE", w, None, amount, &r.occurred_on);
            e.note = Some(name);
            book.entries.push(e);
        }
        book.entries
            .sort_by(|a, b| b.occurred_on.cmp(&a.occurred_on).then(b.id.cmp(&a.id)));
        Ok(book)
    }

    /// `day` tushgan davr hisobi: hamyonlar, egasi maoshi (o'tgan «Hisob kuni»da ushlangan summa
    /// ayirilgan), haqiqiy foyda va yozuvlar. Bosh sahifa va «Hisob kuni» uchun umumiy.
    pub(crate) fn kk_period(
        &self,
        ctx: &Ctx,
        scope: &SpaceScope,
        day: NaiveDate,
    ) -> Result<Period, AppError> {
        let (start, end) =
            month_period(day, ctx.month_start_day).ok_or(AppError::new("INVALID_PERIOD"))?;
        let last = end.pred_opt().ok_or(AppError::new("INVALID_PERIOD"))?;
        let zero = Money::zero(ctx.currency);
        // Oy boshidagi qoldiq — oldingi barcha harakatlar (maoshsiz hisob).
        let before = self.kk_book(ctx, scope, BEGINNING, &ymd(start))?;
        let prior = month_report(
            ctx.currency,
            before.opening_cash,
            before.opening_card,
            zero,
            &before.moves,
        )?;
        let month = self.kk_book(ctx, scope, &ymd(start), &ymd(end))?;
        let base_salary = self.kk_salary(ctx, scope)?;
        // O'tgan oy «Hisob kuni»da maoshdan ortig'i ushlansa — shu oy maoshidan ayiriladi.
        let prev_last = ymd(start.pred_opt().ok_or(AppError::new("INVALID_PERIOD"))?);
        let carry = Money::new(
            self.db
                .read(|c| kk::closes(c, scope))?
                .into_iter()
                .find(|c| c.period_end == prev_last && c.currency == ctx.currency.code())
                .map_or(0, |c| c.carry_minor),
            ctx.currency,
        );
        let salary = if base_salary.is_positive() {
            base_salary.checked_sub(carry)?.clamp_non_negative()
        } else {
            zero
        };
        let settings = self.db.read(|c| kk::settings(c, scope))?;
        let owner_labor = Money::new(settings.map_or(0, |s| s.owner_labor_minor), ctx.currency);
        let r = month_report(
            ctx.currency,
            prior.cash.checked_add(month.opening_cash)?,
            prior.card.checked_add(month.opening_card)?,
            salary,
            &month.moves,
        )?;
        let (depreciation, disposal) = self.kk_depreciation_in(ctx, scope, start)?;
        let family = self.kk_family_rows(ctx, scope, start, end)?;
        let stock = self.kk_stock_period(ctx, scope, &ymd(start), &ymd(end))?;
        let p = true_profit(
            ctx.currency,
            ProfitInput {
                revenue: r.revenue,
                cogs: stock.cogs,
                operating_expenses: r.expenses,
                owner_labor,
                depreciation,
                disposal,
                stock_losses: stock.losses,
            },
            &family.iter().map(|(_, f)| *f).collect::<Vec<_>>(),
        )?;
        let has_activity = !month.entries.is_empty() || !family.is_empty() || stock.has_moves;
        Ok(Period {
            start,
            last,
            base_salary,
            salary,
            carry,
            owner_labor,
            r,
            p,
            cogs: stock.cogs,
            entries: month.entries,
            has_activity,
        })
    }

    /// Kasb-kor bosh sahifasi: shu oy (yoki `date` tushgan oy) hisobi va hamyonlar.
    pub fn kk_overview(
        &self,
        space_id: &str,
        date: Option<String>,
    ) -> Result<KkOverviewDto, AppError> {
        let ctx = self.ctx()?;
        let scope = self.kk_scope(&ctx, space_id)?;
        let day = self.date_or_today(&ctx, date.as_deref(), "date")?;
        let Period {
            start,
            last,
            base_salary,
            salary,
            carry,
            owner_labor,
            r,
            p,
            cogs,
            entries,
            ..
        } = self.kk_period(&ctx, &scope, day)?;
        let d = |m: Money| self.money_dto(&ctx, m);
        let (stock_value, stock_frozen, stock_frozen_count) =
            self.kk_stock_summary(&ctx, &scope)?;
        let profit = KkProfitDto {
            revenue: d(r.revenue),
            cogs: d(cogs),
            stock_losses: d(p.stock_losses),
            operating_expenses: d(r.expenses),
            visible_profit: d(p.visible_profit),
            owner_labor: owner_labor.is_positive().then(|| d(owner_labor)),
            family_labor: d(p.family_labor),
            family_labor_paid: d(p.family_labor_paid),
            depreciation: d(p.depreciation),
            disposal: d(p.disposal),
            true_profit: d(p.true_profit),
        };
        let closed_until = self.db.read(|c| kk::closed_until(c, &scope))?;
        let (receivables, receivables_overdue) = self.kk_receivables(&ctx, &scope)?;
        let close_due = self.kk_close_due(&ctx, &scope, start, closed_until.as_deref())?;
        Ok(KkOverviewDto {
            period_start: ymd(start),
            period_end: ymd(last),
            owner_salary: base_salary.is_positive().then(|| d(salary)),
            salary_carry: (base_salary.is_positive() && carry.is_positive()).then(|| d(carry)),
            revenue: d(r.revenue),
            expenses: d(r.expenses),
            cash_flow: d(r.cash_flow),
            owner_draws: d(r.owner_draws),
            owner_salary_transferred: d(r.owner_salary_transferred),
            contributions: d(r.contributions),
            owner_paid: d(r.owner_paid),
            salary_remaining: r.salary_remaining.map(d),
            overdrawn: r.overdrawn.filter(Money::is_positive).map(d),
            cash: d(r.cash),
            card: d(r.card),
            equipment_purchases: d(r.equipment_purchases),
            equipment_sales: d(r.equipment_sales),
            stock_purchases: d(r.stock_purchases),
            stock_value: d(stock_value),
            stock_frozen_value: d(stock_frozen),
            stock_frozen_count,
            profit,
            negative_wallets: r
                .negative_wallets
                .iter()
                .map(|w| w.as_str().to_string())
                .collect(),
            entries,
            closed_until,
            close_due,
            cash_closed_until: self.db.read(|c| kk_ledger::cash_closed_until(c, &scope))?,
            receivables: d(receivables),
            receivables_overdue: d(receivables_overdue),
        })
    }

    /// Egasining oylik qat'iy maoshi (0 — belgilanmagan).
    pub fn kk_set_owner_salary(
        &self,
        space_id: &str,
        amount: String,
    ) -> Result<KkOverviewDto, AppError> {
        let ctx = self.ctx()?;
        let scope = self.kk_scope(&ctx, space_id)?;
        let salary = if amount.trim().is_empty() {
            Money::zero(ctx.currency)
        } else {
            let m = baraka_money::parse_amount(&amount, ctx.currency)
                .map_err(|e| AppError::on(e.code(), "amount"))?;
            if m.is_negative() {
                return Err(AppError::on("AMOUNT_NOT_POSITIVE", "amount"));
            }
            m
        };
        let labor = self
            .db
            .read(|c| kk::settings(c, &scope))?
            .map_or(0, |s| s.owner_labor_minor);
        self.kk_save_settings(&ctx, &scope, salary.minor(), labor)?;
        self.publish(Some(space_id), &[Topic::Kasbkor]);
        self.kk_overview(space_id, None)
    }

    /// Tushum (savdo, xizmat). Uy'dagidan farqli: «Kelajagim» ulushi taklif qilinmaydi.
    pub fn kk_record_sale(
        &self,
        space_id: &str,
        input: KkSaleInput,
    ) -> Result<KkOverviewDto, AppError> {
        let ctx = self.ctx()?;
        let scope = self.kk_scope(&ctx, space_id)?;
        let amount = positive(&ctx, &input.amount, "amount")?;
        let ch = channel(&input.channel)?;
        let date = self.date_or_today(&ctx, input.occurred_on.as_deref(), "occurredOn")?;
        self.kk_ensure_open(&scope, &ymd(date), "occurredOn")?;
        self.kk_ensure_cash_open(&scope, &ymd(date), ch.as_str() == "CASH")?;
        let row = incomes::IncomeRow {
            id: self.new_id(),
            member_id: None,
            amount_minor: amount.minor(),
            currency: amount.currency().code().to_string(),
            source: clean_opt(input.note.as_deref()).unwrap_or_default(),
            channel: ch.as_str().to_string(),
            source_type: None,
            occurred_on: ymd(date),
            note: None,
        };
        let meta = self.meta();
        self.db
            .write(|tx| incomes::insert(tx, &scope, &row, &meta))?;
        self.publish(Some(space_id), &[Topic::Incomes, Topic::Kasbkor]);
        self.kk_overview(space_id, Some(row.occurred_on))
    }

    /// Ilovagacha qoldiq, «egasi oldi», kapital kiritish yoki hamyonlar orasida o'tkazma.
    pub fn kk_record_move(
        &self,
        space_id: &str,
        input: KkMoveInput,
    ) -> Result<KkOverviewDto, AppError> {
        let ctx = self.ctx()?;
        let scope = self.kk_scope(&ctx, space_id)?;
        let kind = input.kind.as_str();
        if !matches!(
            kind,
            "OPENING" | "OWNER_DRAW" | "OWNER_CONTRIBUTION" | "TRANSFER"
        ) {
            return Err(AppError::on("INVALID_KIND", "kind"));
        }
        let amount = positive(&ctx, &input.amount, "amount")?;
        let from = wallet(&input.wallet, "wallet")?;
        let to = match (kind, input.to_wallet.as_deref()) {
            ("TRANSFER", Some(t)) => {
                let t = wallet(t, "toWallet")?;
                if t == from {
                    return Err(AppError::on("SAME_WALLET", "toWallet"));
                }
                Some(t)
            }
            ("TRANSFER", None) => return Err(AppError::on("REQUIRED", "toWallet")),
            _ => None,
        };
        let date = self.date_or_today(&ctx, input.occurred_on.as_deref(), "occurredOn")?;
        self.kk_ensure_open(&scope, &ymd(date), "occurredOn")?;
        self.kk_ensure_cash_open(
            &scope,
            &ymd(date),
            from == Wallet::Cash || to == Some(Wallet::Cash),
        )?;
        let row = kk::KkMoveRow {
            id: self.new_id(),
            kind: kind.to_string(),
            wallet: from.as_str().to_string(),
            to_wallet: to.map(|w| w.as_str().to_string()),
            amount_minor: amount.minor(),
            currency: ctx.currency.code().to_string(),
            occurred_on: ymd(date),
            note: clean_opt(input.note.as_deref()),
            transfer_id: None,
        };
        let meta = self.meta();
        self.db
            .write(|tx| kk::insert_move(tx, &scope, &row, &meta))?;
        self.publish(Some(space_id), &[Topic::Kasbkor]);
        self.kk_overview(space_id, Some(row.occurred_on))
    }

    /// Maoshni Uy makoniga o'tkazish (`BARAKA_OILASI.md` 4.6): bitta tranzaksiyada Kasb-kor'da
    /// `OWNER_SALARY` va Uy'da daromad, umumiy `transfer_id` bilan. Summa bo'lmasa — maosh qoldig'i.
    pub fn kk_pay_owner_salary(
        &self,
        space_id: &str,
        input: KkSalaryInput,
    ) -> Result<KkSalaryPaidDto, AppError> {
        let ctx = self.ctx()?;
        let scope = self.kk_scope(&ctx, space_id)?;
        let from = wallet(&input.wallet, "wallet")?;
        let date = self.date_or_today(&ctx, input.occurred_on.as_deref(), "occurredOn")?;
        self.kk_ensure_open(&scope, &ymd(date), "occurredOn")?;
        self.kk_ensure_cash_open(&scope, &ymd(date), from == Wallet::Cash)?;
        let amount = match input
            .amount
            .as_deref()
            .map(str::trim)
            .filter(|s| !s.is_empty())
        {
            Some(a) => positive(&ctx, a, "amount")?,
            None => {
                let o = self.kk_overview(space_id, Some(ymd(date)))?;
                let left = o
                    .salary_remaining
                    .ok_or(AppError::on("OWNER_SALARY_NOT_SET", "amount"))?;
                let m = Money::new(
                    left.minor
                        .parse()
                        .map_err(|_| AppError::new("CORRUPT_ROW"))?,
                    ctx.currency,
                );
                if !m.is_positive() {
                    return Err(AppError::on("SALARY_ALREADY_PAID", "amount"));
                }
                m
            }
        };
        let uy = self
            .db
            .read(|c| household::list_spaces(c, &ctx.household_id))?
            .into_iter()
            .find(|s| s.kind == SpaceKind::Uy.as_str())
            .ok_or(AppError::new("UY_SPACE_REQUIRED"))?;
        let uy_scope = self.scope(&ctx, &uy.id)?;
        let transfer_id = self.new_id();
        let mv = kk::KkMoveRow {
            id: self.new_id(),
            kind: "OWNER_SALARY".to_string(),
            wallet: from.as_str().to_string(),
            to_wallet: None,
            amount_minor: amount.minor(),
            currency: ctx.currency.code().to_string(),
            occurred_on: ymd(date),
            note: clean_opt(input.note.as_deref()),
            transfer_id: Some(transfer_id.clone()),
        };
        let income = incomes::IncomeRow {
            id: self.new_id(),
            member_id: None,
            amount_minor: amount.minor(),
            currency: ctx.currency.code().to_string(),
            source: SALARY_SOURCE.to_string(),
            channel: from.as_str().to_string(),
            source_type: Some(SALARY_SOURCE_TYPE.to_string()),
            occurred_on: ymd(date),
            note: None,
        };
        let meta = self.meta();
        self.db.write(|tx| {
            kk::insert_move(tx, &scope, &mv, &meta)?;
            incomes::insert_with_transfer(tx, &uy_scope, &income, &transfer_id, &meta)
        })?;
        self.publish(Some(space_id), &[Topic::Kasbkor]);
        self.publish(Some(&uy.id), &[Topic::Incomes]);
        let uy_income = self.income_offer(&ctx, &uy_scope, income, amount)?;
        Ok(KkSalaryPaidDto {
            overview: self.kk_overview(space_id, Some(ymd(date)))?,
            uy_space_id: uy.id,
            uy_income,
        })
    }
}
