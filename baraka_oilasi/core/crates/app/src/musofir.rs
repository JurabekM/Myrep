//! M1 — Musofir makoni (`docs/musofir/SPEC.md` 2–4): ish valyutasi va kurs, chet eldagi maosh va
//! xarajat, uyga yuborilgan, o'z ulushi va qaytish jamg'armasi.
//!
//! Hisob `domain-musofir` da (vektorlar `mf_month`, `mf_return_fund`); bu yerda ma'lumotni yig'ish,
//! saqlash va DTO. Maosh — `incomes` (`source_type = TER`), xarajat — `expenses`, qolgani — `mf_moves`.
use baraka_domain_common::{month_period, SpaceKind};
use baraka_domain_musofir::fund::{return_fund, ReturnFund};
use baraka_domain_musofir::month::{month_report, MfKind, MfMonth, MfMove};
use baraka_domain_musofir::rate::{format_rate, parse_rate};
use baraka_money::{format_percent_bp, percent_of, Currency, FxRate, Money};
use baraka_storage::repo::{categories, expenses, household, incomes, mf};
use baraka_storage::SpaceScope;
use chrono::NaiveDate;

use crate::access::Role;
use crate::app::Ctx;
use crate::events::Topic;
use crate::receipt::{positive, ymd};
use crate::text::clean_opt;
use crate::uy::channel;
use crate::*;

/// Maosh — mehnat daromadi (`incomes.source_type`); boshqa daromadda `NULL`.
const SALARY_SOURCE_TYPE: &str = "TER";
const BEGINNING: &str = "0000-01-01";
const END_OF_TIME: &str = "9999-12-31";
/// Kurs shu kundan eski bo'lsa — «yangilang» (OQ-MF4).
const STALE_RATE_DAYS: i64 = 30;
/// Prognoz uchun oxirgi to'liq oylar (yozuvi borlari).
const PROGNOSIS_MONTHS: usize = 3;
/// Standart o'z ulushi — 20 % (OQ-MF1).
const DEFAULT_SHARE_BP: i64 = 2_000;

/// Sozlangan makon: ish valyutasi va o'z ulushi.
struct Setup {
    work: Currency,
    share_bp: i64,
    row: mf::MfSettingsRow,
}

struct Book {
    moves: Vec<MfMove>,
    entries: Vec<MfEntryDto>,
}

/// `"20"`, `"12,5"`, `"20 %"` → bp (0–100 %, ko'pi bilan 2 kasr xonasi).
pub(crate) fn parse_percent_bp(s: &str) -> Result<i64, AppError> {
    let err = || AppError::on("INVALID_PERCENT", "sharePercent");
    let t: String = s
        .chars()
        .filter(|c| !c.is_whitespace() && *c != '%' && *c != '\u{a0}')
        .map(|c| if c == ',' { '.' } else { c })
        .collect();
    let (int, frac) = t.split_once('.').unwrap_or((t.as_str(), ""));
    if int.is_empty()
        || frac.len() > 2
        || !int.chars().all(|c| c.is_ascii_digit())
        || !frac.chars().all(|c| c.is_ascii_digit())
    {
        return Err(err());
    }
    let whole: i64 = int.parse().map_err(|_| err())?;
    let cents: i64 = format!("{frac:0<2}").parse().map_err(|_| err())?;
    let bp = whole
        .checked_mul(100)
        .and_then(|v| v.checked_add(cents))
        .ok_or_else(err)?;
    if (0..=10_000).contains(&bp) {
        Ok(bp)
    } else {
        Err(err())
    }
}

impl App {
    /// Musofirning shaxsiy bo'limlari: uydagi oila qurilmasida (ADR-0004) va sotuvchida yopiq.
    pub(crate) fn mf_scope(&self, ctx: &Ctx, space_id: &str) -> Result<SpaceScope, AppError> {
        if self.access(ctx)?.role == Role::Home {
            return Err(AppError::new("ROLE_FORBIDDEN"));
        }
        self.mf_space_check(ctx, space_id)
    }

    /// Musofir makoni ekanini tekshiradi (rol tekshiruvi — chaqiruvchida yoki umumiy `scope`da).
    pub(crate) fn mf_space_check(&self, ctx: &Ctx, space_id: &str) -> Result<SpaceScope, AppError> {
        let scope = self.scope(ctx, space_id)?;
        let kind = self
            .db
            .read(|c| household::list_spaces(c, &ctx.household_id))?
            .into_iter()
            .find(|s| s.id == space_id)
            .map(|s| s.kind);
        if kind.as_deref() != Some(SpaceKind::Musofir.as_str()) {
            return Err(AppError::on("NOT_MUSOFIR_SPACE", "spaceId"));
        }
        Ok(scope)
    }

    fn mf_setup(&self, scope: &SpaceScope) -> Result<Option<Setup>, AppError> {
        let Some(row) = self.db.read(|c| mf::settings(c, scope))? else {
            return Ok(None);
        };
        let work =
            Currency::from_code(&row.work_currency).map_err(|_| AppError::new("CORRUPT_ROW"))?;
        Ok(Some(Setup {
            work,
            share_bp: row.share_bp,
            row,
        }))
    }

    fn mf_require(&self, scope: &SpaceScope) -> Result<Setup, AppError> {
        self.mf_setup(scope)?
            .ok_or(AppError::new("MF_NOT_CONFIGURED"))
    }

    /// `[from, to)` oralig'idagi yozuvlar (faqat ish valyutasidagilari). Jamg'arma harakatlari sana
    /// tartibida — domen jamg'armadan olishni qoldiq bilan tekshiradi.
    fn mf_book(
        &self,
        ctx: &Ctx,
        scope: &SpaceScope,
        work: Currency,
        from: &str,
        to: &str,
    ) -> Result<Book, AppError> {
        let m = |minor: i64| Money::new(minor, work);
        let mut book = Book {
            moves: Vec::new(),
            entries: Vec::new(),
        };
        for r in self
            .db
            .read(|c| incomes::list_between(c, scope, from, to))?
            .into_iter()
            .filter(|r| r.currency == work.code())
        {
            let kind = if r.source_type.as_deref() == Some(SALARY_SOURCE_TYPE) {
                MfKind::Salary
            } else {
                MfKind::OtherIncome
            };
            book.moves.push(MfMove {
                kind,
                amount: m(r.amount_minor),
                fee: None,
            });
            book.entries.push(MfEntryDto {
                id: r.id,
                kind: kind.as_str().to_string(),
                amount: self.money_dto(ctx, m(r.amount_minor)),
                fee: None,
                received: None,
                channel: Some(r.channel),
                category_id: None,
                occurred_on: r.occurred_on,
                note: clean_opt(r.note.as_deref()).or_else(|| clean_opt(Some(&r.source))),
            });
        }
        for r in self
            .db
            .read(|c| expenses::list_between(c, scope, from, to))?
            .into_iter()
            .filter(|r| r.currency == work.code())
        {
            book.moves.push(MfMove {
                kind: MfKind::Expense,
                amount: m(r.amount_minor),
                fee: None,
            });
            book.entries.push(MfEntryDto {
                id: r.id,
                kind: MfKind::Expense.as_str().to_string(),
                amount: self.money_dto(ctx, m(r.amount_minor)),
                fee: None,
                received: None,
                channel: Some(r.channel),
                category_id: Some(r.category_id),
                occurred_on: r.occurred_on,
                note: r.note,
            });
        }
        for r in self
            .db
            .read(|c| mf::moves_between(c, scope, from, to))?
            .into_iter()
            .filter(|r| r.currency == work.code())
        {
            let kind = MfKind::parse(&r.kind).ok_or(AppError::new("CORRUPT_ROW"))?;
            let fee = (r.fee_minor > 0).then(|| m(r.fee_minor));
            book.moves.push(MfMove {
                kind,
                amount: m(r.amount_minor),
                fee,
            });
            let received = match (r.received_minor, r.received_currency.as_deref()) {
                (Some(v), Some(c)) => Some(Money::new(
                    v,
                    Currency::from_code(c).map_err(|_| AppError::new("CORRUPT_ROW"))?,
                )),
                _ => None,
            };
            book.entries.push(MfEntryDto {
                id: r.id,
                kind: r.kind,
                amount: self.money_dto(ctx, m(r.amount_minor)),
                fee: fee.map(|f| self.money_dto(ctx, f)),
                received: received.map(|x| self.money_dto(ctx, x)),
                channel: None,
                category_id: None,
                occurred_on: r.occurred_on,
                note: r.note,
            });
        }
        book.entries
            .sort_by(|a, b| b.occurred_on.cmp(&a.occurred_on).then(b.id.cmp(&a.id)));
        Ok(book)
    }

    /// `[start, end)` oy hisoboti: oy boshidagi qo'ldagi pul va jamg'arma — oldingi barcha yozuvlardan.
    fn mf_month_of(
        &self,
        ctx: &Ctx,
        scope: &SpaceScope,
        setup: &Setup,
        start: NaiveDate,
        end: NaiveDate,
    ) -> Result<(MfMonth, Book), AppError> {
        let zero = Money::zero(setup.work);
        let before = self.mf_book(ctx, scope, setup.work, BEGINNING, &ymd(start))?;
        let prior = month_report(zero, zero, 0, &before.moves)?;
        let book = self.mf_book(ctx, scope, setup.work, &ymd(start), &ymd(end))?;
        let r = month_report(
            prior.pocket,
            prior.fund_balance,
            setup.share_bp,
            &book.moves,
        )?;
        Ok((r, book))
    }

    /// Ish valyutasidan uy valyutasiga amaldagi kurs (bir xil valyutada — 1).
    fn mf_rate(
        &self,
        ctx: &Ctx,
        scope: &SpaceScope,
        work: Currency,
    ) -> Result<Option<(FxRate, MfRateDto)>, AppError> {
        let today = self.today(ctx);
        if work == ctx.currency {
            let fx = FxRate {
                from: work,
                to: work,
                rate_num: 1,
                rate_den: 1,
            };
            return Ok(Some((
                fx,
                MfRateDto {
                    from_currency: work.code().to_string(),
                    to_currency: work.code().to_string(),
                    rate: "1".to_string(),
                    rate_on: ymd(today),
                    source: None,
                    stale: false,
                    identity: true,
                },
            )));
        }
        let Some(r) = self
            .db
            .read(|c| mf::rate_on(c, scope, work.code(), ctx.currency.code(), &ymd(today)))?
        else {
            return Ok(None);
        };
        let on = NaiveDate::parse_from_str(&r.rate_on, "%Y-%m-%d")
            .map_err(|_| AppError::new("CORRUPT_ROW"))?;
        let fx = FxRate {
            from: work,
            to: ctx.currency,
            rate_num: r.rate_num,
            rate_den: r.rate_den,
        };
        Ok(Some((
            fx,
            MfRateDto {
                from_currency: r.from_currency,
                to_currency: r.to_currency,
                rate: format_rate(r.rate_num, r.rate_den),
                rate_on: r.rate_on,
                source: r.source,
                stale: (today - on).num_days() > STALE_RATE_DAYS,
                identity: false,
            },
        )))
    }

    fn mf_settings_dto(
        &self,
        ctx: &Ctx,
        scope: &SpaceScope,
        s: &Setup,
    ) -> Result<MfSettingsDto, AppError> {
        let target = match (s.row.target_minor, s.row.target_currency.as_deref()) {
            (Some(v), Some(c)) => Some(self.money_dto(
                ctx,
                Money::new(
                    v,
                    Currency::from_code(c).map_err(|_| AppError::new("CORRUPT_ROW"))?,
                ),
            )),
            _ => None,
        };
        let locked = self.db.read(|c| mf::has_records(c, scope))?;
        Ok(MfSettingsDto {
            country: s.row.country.clone(),
            work_currency: s.work.code().to_string(),
            home_currency: ctx.currency.code().to_string(),
            share_bp: i32::try_from(s.share_bp).map_err(|_| AppError::new("CORRUPT_ROW"))?,
            share_percent: format_percent_bp(s.share_bp),
            target,
            return_on: s.row.return_on.clone(),
            currency_locked: locked,
        })
    }

    /// Musofir bosh sahifasi: sozlamalar, shu oy (yoki `date` tushgan oy) hisobi, qaytish
    /// jamg'armasi prognozi va kurs.
    pub fn mf_overview(
        &self,
        space_id: &str,
        date: Option<String>,
    ) -> Result<MfOverviewDto, AppError> {
        let ctx = self.ctx()?;
        let scope = self.mf_scope(&ctx, space_id)?;
        let day = self.date_or_today(&ctx, date.as_deref(), "date")?;
        let (start, end) =
            month_period(day, ctx.month_start_day).ok_or(AppError::new("INVALID_PERIOD"))?;
        let last = end.pred_opt().ok_or(AppError::new("INVALID_PERIOD"))?;
        let Some(setup) = self.mf_setup(&scope)? else {
            return Ok(MfOverviewDto {
                settings: None,
                default_share_percent: format_percent_bp(DEFAULT_SHARE_BP),
                period_start: ymd(start),
                period_end: ymd(last),
                month: None,
                fund: None,
                rate: None,
                entries: Vec::new(),
            });
        };
        let (r, book) = self.mf_month_of(&ctx, &scope, &setup, start, end)?;
        let rate = self.mf_rate(&ctx, &scope, setup.work)?;
        // Prognoz: oxirgi to'liq oylarning (yozuvi borlari) sof jamg'armasi.
        let mut monthly = Vec::new();
        let mut cursor = start;
        for _ in 0..PROGNOSIS_MONTHS {
            let Some(prev_day) = cursor.pred_opt() else {
                break;
            };
            let (p_start, p_end) = month_period(prev_day, ctx.month_start_day)
                .ok_or(AppError::new("INVALID_PERIOD"))?;
            let (pr, pb) = self.mf_month_of(&ctx, &scope, &setup, p_start, p_end)?;
            if !pb.entries.is_empty() {
                monthly.push(pr.fund_net);
            }
            cursor = p_start;
        }
        let target = match (setup.row.target_minor, setup.row.target_currency.as_deref()) {
            (Some(v), Some(c)) if c == ctx.currency.code() => Some(Money::new(v, ctx.currency)),
            _ => None,
        };
        let return_on = setup
            .row
            .return_on
            .as_deref()
            .and_then(|d| NaiveDate::parse_from_str(d, "%Y-%m-%d").ok());
        let f: ReturnFund = return_fund(
            r.fund_balance,
            rate.as_ref().map(|(fx, _)| fx),
            target,
            &monthly,
            self.today(&ctx),
            return_on,
        )?;
        let d = |m: Money| self.money_dto(&ctx, m);
        let pct = |bp: Option<i64>| bp.map(format_percent_bp);
        let month = MfMonthDto {
            income: d(r.income),
            expenses: d(r.expenses),
            sent_home: d(r.sent_home),
            fees: d(r.fees),
            fund_in: d(r.fund_in),
            fund_out: d(r.fund_out),
            fund_net: d(r.fund_net),
            pocket: d(r.pocket),
            share_target: d(r.share_target),
            share_gap: d(r.share_gap),
            expenses_percent: pct(r.expenses_bp),
            sent_percent: pct(r.sent_bp),
            fund_percent: pct(r.fund_bp),
            warnings: r.warnings.iter().map(|w| w.as_str().to_string()).collect(),
        };
        let fund = MfFundDto {
            balance: d(r.fund_balance),
            avg_monthly: f.avg_monthly.map(d),
            months_used: u32::try_from(monthly.len()).unwrap_or(0),
            months_until_return: f.months_until_return.and_then(|v| i32::try_from(v).ok()),
            balance_home: f.balance_home.map(d),
            avg_monthly_home: f.avg_monthly_home.map(d),
            target: target.map(d),
            remaining_home: f.remaining_home.map(d),
            progress_bp: f.progress_bp.and_then(|v| i32::try_from(v).ok()),
            progress_percent: pct(f.progress_bp),
            months_to_target: f.months_to_target.and_then(|v| i32::try_from(v).ok()),
            projected_home: f.projected_home.map(d),
            shortfall_at_return: f.shortfall_at_return.map(d),
            status: f.status.as_str().to_string(),
        };
        Ok(MfOverviewDto {
            settings: Some(self.mf_settings_dto(&ctx, &scope, &setup)?),
            default_share_percent: format_percent_bp(DEFAULT_SHARE_BP),
            period_start: ymd(start),
            period_end: ymd(last),
            month: Some(month),
            fund: Some(fund),
            rate: rate.map(|(_, dto)| dto),
            entries: book.entries,
        })
    }

    /// Sozlash ustasi va keyingi o'zgartirishlar. Ish valyutasi yozuvlar paydo bo'lgach o'zgarmaydi.
    pub fn mf_set_settings(
        &self,
        space_id: &str,
        input: MfSettingsInput,
    ) -> Result<MfOverviewDto, AppError> {
        let ctx = self.ctx()?;
        let scope = self.mf_scope(&ctx, space_id)?;
        let work = Currency::from_code(input.work_currency.trim())
            .map_err(|_| AppError::on("INVALID_CURRENCY", "workCurrency"))?;
        let share_bp = parse_percent_bp(&input.share_percent)?;
        let target = match input
            .target
            .as_deref()
            .map(str::trim)
            .filter(|t| !t.is_empty())
        {
            None => None,
            Some(t) => Some(positive(t, ctx.currency, "target")?),
        };
        let return_on = match clean_opt(input.return_on.as_deref()) {
            None => None,
            Some(d) => Some(ymd(NaiveDate::parse_from_str(&d, "%Y-%m-%d")
                .map_err(|_| AppError::on("INVALID_DATE", "returnOn"))?)),
        };
        if self
            .db
            .read(|c| mf::has_records_other_than(c, &scope, work.code()))?
        {
            return Err(AppError::on("WORK_CURRENCY_LOCKED", "workCurrency"));
        }
        let row = mf::MfSettingsRow {
            country: clean_opt(input.country.as_deref()),
            work_currency: work.code().to_string(),
            share_bp,
            target_minor: target.map(|t| t.minor()),
            target_currency: target.map(|t| t.currency().code().to_string()),
            return_on,
        };
        let id = self.new_id();
        let meta = self.meta();
        self.db
            .write(|tx| mf::upsert_settings(tx, &scope, &id, &row, &meta))?;
        self.publish(Some(space_id), &[Topic::Musofir]);
        self.mf_overview(space_id, None)
    }

    /// Kurs: «1 KRW = 9,1 soʻm» (sana va manba bilan). Bir xil valyutada kurs kerak emas.
    pub fn mf_set_rate(
        &self,
        space_id: &str,
        input: MfRateInput,
    ) -> Result<MfOverviewDto, AppError> {
        let ctx = self.ctx()?;
        let scope = self.mf_scope(&ctx, space_id)?;
        let setup = self.mf_require(&scope)?;
        if setup.work == ctx.currency {
            return Err(AppError::on("RATE_NOT_NEEDED", "rate"));
        }
        let (num, den) =
            parse_rate(&input.rate).map_err(|_| AppError::on("INVALID_FX_RATE", "rate"))?;
        let on = self.date_or_today(&ctx, input.rate_on.as_deref(), "rateOn")?;
        if on > self.today(&ctx) {
            return Err(AppError::on("FUTURE_DATE", "rateOn"));
        }
        let row = mf::MfRateRow {
            id: self.new_id(),
            rate_on: ymd(on),
            from_currency: setup.work.code().to_string(),
            to_currency: ctx.currency.code().to_string(),
            rate_num: num,
            rate_den: den,
            source: clean_opt(input.source.as_deref()),
        };
        let meta = self.meta();
        self.db
            .write(|tx| mf::insert_rate(tx, &scope, &row, &meta))?;
        self.publish(Some(space_id), &[Topic::Musofir]);
        self.mf_overview(space_id, None)
    }

    /// Maosh yoki boshqa daromad (ish valyutasida) + o'z ulushi taklifi.
    pub fn mf_record_income(
        &self,
        space_id: &str,
        input: MfIncomeInput,
    ) -> Result<MfIncomeRecordedDto, AppError> {
        let ctx = self.ctx()?;
        let scope = self.mf_scope(&ctx, space_id)?;
        let setup = self.mf_require(&scope)?;
        let source_type = match input.kind.as_str() {
            "SALARY" => Some(SALARY_SOURCE_TYPE.to_string()),
            "OTHER_INCOME" => None,
            _ => return Err(AppError::on("INVALID_KIND", "kind")),
        };
        let amount = positive(&input.amount, setup.work, "amount")?;
        let ch = channel(&input.channel)?;
        let date = self.date_or_today(&ctx, input.occurred_on.as_deref(), "occurredOn")?;
        let row = incomes::IncomeRow {
            id: self.new_id(),
            member_id: None,
            amount_minor: amount.minor(),
            currency: setup.work.code().to_string(),
            source: clean_opt(input.note.as_deref()).unwrap_or_default(),
            channel: ch.as_str().to_string(),
            source_type,
            occurred_on: ymd(date),
            note: None,
        };
        let meta = self.meta();
        self.db
            .write(|tx| incomes::insert(tx, &scope, &row, &meta))?;
        self.publish(Some(space_id), &[Topic::Incomes, Topic::Musofir]);
        let share = percent_of(amount, setup.share_bp)?;
        Ok(MfIncomeRecordedDto {
            overview: self.mf_overview(space_id, Some(row.occurred_on))?,
            suggested_share: self.money_dto(&ctx, share),
        })
    }

    /// Chet eldagi xarajat (Musofir kategoriyalari bilan).
    pub fn mf_record_expense(
        &self,
        space_id: &str,
        input: MfExpenseInput,
    ) -> Result<MfOverviewDto, AppError> {
        let ctx = self.ctx()?;
        let scope = self.mf_scope(&ctx, space_id)?;
        let setup = self.mf_require(&scope)?;
        let amount = positive(&input.amount, setup.work, "amount")?;
        let ch = channel(&input.channel)?;
        let category = self
            .db
            .read(|c| categories::get(c, &scope, &input.category_id))?
            .ok_or(AppError::on("NOT_FOUND", "categoryId"))?;
        let date = self.date_or_today(&ctx, input.occurred_on.as_deref(), "occurredOn")?;
        let row = expenses::ExpenseRow {
            id: self.new_id(),
            category_id: category.id,
            member_id: None,
            amount_minor: amount.minor(),
            currency: setup.work.code().to_string(),
            channel: ch.as_str().to_string(),
            occurred_on: ymd(date),
            necessity: category.default_necessity,
            obligation_id: None,
            is_gift: false,
            is_ostentation: false,
            funded_by_debt: false,
            note: clean_opt(input.note.as_deref()),
        };
        let meta = self.meta();
        self.db
            .write(|tx| expenses::insert(tx, &scope, &row, &meta))?;
        self.publish(Some(space_id), &[Topic::Expenses, Topic::Musofir]);
        self.mf_overview(space_id, Some(row.occurred_on))
    }

    /// Uyga yuborilgan, jamg'armaga / jamg'armadan, boshlang'ich qoldiqlar.
    pub fn mf_record_move(
        &self,
        space_id: &str,
        input: MfMoveInput,
    ) -> Result<MfOverviewDto, AppError> {
        let ctx = self.ctx()?;
        let scope = self.mf_scope(&ctx, space_id)?;
        let setup = self.mf_require(&scope)?;
        let kind = match MfKind::parse(&input.kind) {
            Some(
                k @ (MfKind::Opening
                | MfKind::SentHome
                | MfKind::FundIn
                | MfKind::FundOut
                | MfKind::FundOpening),
            ) => k,
            _ => return Err(AppError::on("INVALID_KIND", "kind")),
        };
        let amount = positive(&input.amount, setup.work, "amount")?;
        let opt = |s: Option<&str>| {
            s.map(str::trim)
                .filter(|t| !t.is_empty())
                .map(str::to_string)
        };
        let (fee, received) = if kind == MfKind::SentHome {
            let fee = match opt(input.fee.as_deref()) {
                None => Money::zero(setup.work),
                Some(f) => {
                    let m = baraka_money::parse_amount(&f, setup.work)
                        .map_err(|e| AppError::on(e.code(), "fee"))?;
                    if m.is_negative() {
                        return Err(AppError::on("FEE_NEGATIVE", "fee"));
                    }
                    m
                }
            };
            let received = opt(input.received.as_deref())
                .map(|r| positive(&r, ctx.currency, "received"))
                .transpose()?;
            (fee, received)
        } else {
            if opt(input.fee.as_deref()).is_some()
                || opt(input.received.as_deref()).is_some()
                || input.purposes.is_some()
            {
                return Err(AppError::on("FIELD_NOT_ALLOWED", "fee"));
            }
            (Money::zero(setup.work), None)
        };
        // M2: yuborishning maqsadlari — berilgan, kelishuv shartlaridan yoki uy xarajati 100 %.
        let shares = if kind == MfKind::SentHome {
            match &input.purposes {
                Some(p) => crate::musofir_remit::shares_from_input(p)?,
                None => self.mf_default_shares(&scope)?,
            }
        } else {
            Vec::new()
        };
        let note = clean_opt(input.note.as_deref());
        if kind == MfKind::FundOut && note.is_none() {
            return Err(AppError::on("REASON_REQUIRED", "note"));
        }
        let date = self.date_or_today(&ctx, input.occurred_on.as_deref(), "occurredOn")?;
        let new_move = MfMove {
            kind,
            amount,
            fee: fee.is_positive().then_some(fee),
        };
        if kind == MfKind::FundOut {
            // Jamg'armadan olish — butun qoldiqdan oshmaydi (domen tekshiradi).
            let mut all = self
                .mf_book(&ctx, &scope, setup.work, BEGINNING, END_OF_TIME)?
                .moves;
            all.push(new_move);
            let zero = Money::zero(setup.work);
            month_report(zero, zero, 0, &all).map_err(|e| match e.code {
                "FUND_INSUFFICIENT" => AppError::on("RETURN_FUND_INSUFFICIENT", "amount"),
                c => AppError::on(c, "amount"),
            })?;
        }
        let row = mf::MfMoveRow {
            id: self.new_id(),
            kind: kind.as_str().to_string(),
            amount_minor: amount.minor(),
            currency: setup.work.code().to_string(),
            fee_minor: fee.minor(),
            received_minor: received.map(|r| r.minor()),
            received_currency: received.map(|r| r.currency().code().to_string()),
            occurred_on: ymd(date),
            note,
        };
        let parts: Vec<mf::MfPartRow> = shares
            .iter()
            .map(|s| mf::MfPartRow {
                id: self.new_id(),
                move_id: row.id.clone(),
                purpose: s.purpose.as_str().to_string(),
                share_bp: s.bp,
            })
            .collect();
        let meta = self.meta();
        self.db.write(|tx| {
            mf::insert_move(tx, &scope, &row, &meta)?;
            for p in &parts {
                mf::insert_part(tx, &scope, p, &meta)?;
            }
            Ok(())
        })?;
        self.publish(Some(space_id), &[Topic::Musofir]);
        self.mf_overview(space_id, Some(row.occurred_on))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn percent_parsing() {
        assert_eq!(parse_percent_bp("20").ok(), Some(2_000));
        assert_eq!(parse_percent_bp("12,5 %").ok(), Some(1_250));
        assert_eq!(parse_percent_bp("0").ok(), Some(0));
        assert_eq!(parse_percent_bp("100").ok(), Some(10_000));
        for bad in ["", "101", "-5", "1,234", "abc"] {
            assert!(parse_percent_bp(bad).is_err(), "{bad}");
        }
    }
}
