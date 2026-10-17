//! Uy makoni use-case'lari: daromad, «Kelajagim», xarajat, oylik audit, kelishuv jurnali.
use baraka_agreements::{check_completeness, AgreementDraft, AgreementType, Completeness};
use baraka_domain_common::{
    month_period, Channel, IncomeSourceType, Necessity, VaultReason, VaultType, WEEK_ANCHOR,
};
use baraka_domain_uy::allocation::{
    progressive_suggestion, suggest_share, AllocationRule, ProgressivePolicy,
};
use baraka_domain_uy::amortization::{compare, simulate, LoanTerms, ScheduleKind};
use baraka_domain_uy::audit::{unexplained_gap, GapInput};
use baraka_domain_uy::streak::compute_streak;
use baraka_journal::{
    short_code, verify_chain, ChainError, EntryKind, JournalAmount, JournalEntry,
};
use baraka_money::{parse_amount, Currency, Money};
use baraka_storage::repo::{
    agreements, assets, categories, expenses, incomes, journal, rules, vault,
};
use baraka_storage::SpaceScope;
use chrono::NaiveDate;

use crate::app::{parse_necessity, Ctx};
use crate::catalog::SADAQA_KEY;
use crate::events::Topic;
use crate::text::{clean_opt, required};
use crate::*;

pub(crate) fn positive(ctx: &Ctx, amount: &str, field: &str) -> Result<Money, AppError> {
    let m = parse_amount(amount, ctx.currency).map_err(|e| AppError::on(e.code(), field))?;
    if m.is_positive() {
        Ok(m)
    } else {
        Err(AppError::on("AMOUNT_NOT_POSITIVE", field))
    }
}

pub(crate) fn channel(s: &str) -> Result<Channel, AppError> {
    Channel::parse(s).ok_or(AppError::on("INVALID_CHANNEL", "channel"))
}

fn parse_agreement_type(s: &str) -> Result<AgreementType, AppError> {
    serde_json::from_value(serde_json::Value::String(s.to_string()))
        .map_err(|_| AppError::on("INVALID_AGREEMENT_TYPE", "type"))
}

fn ymd(d: NaiveDate) -> String {
    d.format("%Y-%m-%d").to_string()
}

fn sum(rows: impl Iterator<Item = i64>, c: Currency) -> Result<Money, AppError> {
    Ok(Money::sum(rows.map(|m| Money::new(m, c)), c)?)
}

impl App {
    pub(crate) fn vault_asset(&self, scope: &SpaceScope) -> Result<assets::AssetRow, AppError> {
        self.db
            .read(|c| assets::shared_vault(c, scope, VaultType::Qorovul.as_str()))?
            .ok_or(AppError::new("VAULT_NOT_FOUND"))
    }

    fn rule(
        &self,
        ctx: &Ctx,
        scope: &SpaceScope,
    ) -> Result<Option<(AllocationRule, AllocationRuleDto)>, AppError> {
        let Some(r) = self.db.read(|c| rules::active(c, scope))? else {
            return Ok(None);
        };
        let (rule, amount) = match (r.kind.as_str(), r.bp, r.amount_minor, r.currency.as_deref()) {
            ("PERCENT", Some(bp), _, _) => (AllocationRule::Percent(bp), None),
            ("FIXED", _, Some(minor), Some(cur)) => {
                let m = Money::new(minor, Currency::from_code(cur)?);
                (AllocationRule::Fixed(m), Some(self.money_dto(ctx, m)))
            }
            _ => return Err(AppError::new("CORRUPT_RULE")),
        };
        let bp =
            r.bp.map(|b| i32::try_from(b).map_err(|_| AppError::new("CORRUPT_RULE")))
                .transpose()?;
        Ok(Some((
            rule,
            AllocationRuleDto {
                kind: r.kind,
                bp,
                amount,
                progressive: r.progressive,
            },
        )))
    }

    fn streak_of(
        &self,
        ctx: &Ctx,
        scope: &SpaceScope,
        vault_id: &str,
    ) -> Result<StreakDto, AppError> {
        let dates: Vec<NaiveDate> = self
            .db
            .read(|c| vault::deposit_dates(c, scope, vault_id))?
            .iter()
            .filter_map(|d| NaiveDate::parse_from_str(d, "%Y-%m-%d").ok())
            .collect();
        let s = compute_streak(&dates, self.today(ctx), WEEK_ANCHOR);
        Ok(StreakDto {
            current_weeks: s.current_weeks,
            longest_weeks: s.longest_weeks,
            total_weeks: s.total_weeks,
            current_week_done: s.current_week_done,
        })
    }

    /// Tez daromad kiritish + ulush taklifi (uy/SPEC 2.1).
    pub fn record_income(
        &self,
        space_id: &str,
        input: NewIncomeInput,
    ) -> Result<IncomeRecordedDto, AppError> {
        let ctx = self.ctx()?;
        let scope = self.scope(&ctx, space_id)?;
        let amount = positive(&ctx, &input.amount, "amount")?;
        let ch = channel(&input.channel)?;
        let source_type = match input.source_type.as_deref() {
            None => None,
            Some(t) => Some(
                IncomeSourceType::parse(t)
                    .ok_or(AppError::on("INVALID_SOURCE_TYPE", "sourceType"))?,
            ),
        };
        let date = self.date_or_today(&ctx, input.occurred_on.as_deref(), "occurredOn")?;
        self.kk_ensure_open(&scope, &ymd(date), "occurredOn")?;
        let row = incomes::IncomeRow {
            id: self.new_id(),
            member_id: input.member_id.clone(),
            amount_minor: amount.minor(),
            currency: amount.currency().code().to_string(),
            source: required(&input.source, "source")?,
            channel: ch.as_str().to_string(),
            source_type: source_type.map(|t| t.as_str().to_string()),
            occurred_on: ymd(date),
            note: clean_opt(input.note.as_deref()),
        };
        let meta = self.meta();
        self.db
            .write(|tx| incomes::insert(tx, &scope, &row, &meta))?;
        self.publish(Some(space_id), &[Topic::Incomes]);
        self.income_offer(&ctx, &scope, row, amount)
    }

    /// Saqlangan daromad va 1-qonun ulushi taklifi (progressiv rejim bilan).
    pub(crate) fn income_offer(
        &self,
        ctx: &Ctx,
        scope: &SpaceScope,
        row: incomes::IncomeRow,
        amount: Money,
    ) -> Result<IncomeRecordedDto, AppError> {
        let (suggested, progressive) = match self.rule(ctx, scope)? {
            Some((rule, dto)) => {
                let share = suggest_share(amount, rule)?;
                let prog = match (rule, dto.progressive) {
                    (AllocationRule::Percent(bp), true) => {
                        let vault_id = self.vault_asset(scope)?.id;
                        let streak = self.streak_of(ctx, scope, &vault_id)?;
                        progressive_suggestion(
                            bp,
                            streak.current_weeks,
                            ProgressivePolicy::default(),
                        )
                    }
                    _ => None,
                };
                (share, prog)
            }
            None => (Money::zero(amount.currency()), None),
        };
        Ok(IncomeRecordedDto {
            income: IncomeDto {
                id: row.id,
                amount: self.money_dto(ctx, amount),
                source: row.source,
                channel: row.channel,
                occurred_on: row.occurred_on,
            },
            suggested_share: self.money_dto(ctx, suggested),
            progressive_suggestion_bp: progressive.and_then(|v| i32::try_from(v).ok()),
            progressive_suggestion_percent: progressive.map(baraka_money::format_percent_bp),
        })
    }

    fn vault_insert(
        &self,
        ctx: &Ctx,
        space_id: &str,
        amount: Money,
        reason: VaultReason,
        income_id: Option<String>,
        note: Option<String>,
    ) -> Result<VaultTxDto, AppError> {
        let scope = self.scope(ctx, space_id)?;
        let vault_asset = self.vault_asset(&scope)?;
        let row = vault::VaultTxRow {
            id: self.new_id(),
            asset_id: vault_asset.id,
            amount_minor: amount.minor(),
            currency: amount.currency().code().to_string(),
            reason: reason.as_str().to_string(),
            income_id,
            note,
            occurred_on: ymd(self.today(ctx)),
        };
        let meta = self.meta();
        self.db.write(|tx| vault::insert(tx, &scope, &row, &meta))?;
        self.publish(Some(space_id), &[Topic::Vault]);
        Ok(VaultTxDto {
            id: row.id,
            amount: self.money_dto(ctx, amount),
            reason: row.reason,
            note: row.note,
            occurred_on: row.occurred_on,
        })
    }

    /// «Ajratish» yoki «Boshqa summa»: daromaddan «Kelajagim»ga.
    pub fn allocate_to_vault(
        &self,
        space_id: &str,
        income_id: &str,
        amount: &str,
    ) -> Result<VaultTxDto, AppError> {
        let ctx = self.ctx()?;
        let scope = self.scope(&ctx, space_id)?;
        let income = self
            .db
            .read(|c| incomes::get(c, &scope, income_id))?
            .ok_or(AppError::on("NOT_FOUND", "incomeId"))?;
        let amount = positive(&ctx, amount, "amount")?;
        if amount.minor() > income.amount_minor {
            return Err(AppError::on("SHARE_EXCEEDS_INCOME", "amount"));
        }
        self.vault_insert(
            &ctx,
            space_id,
            amount,
            VaultReason::Allocation,
            Some(income.id),
            None,
        )
    }

    /// «Ro'molcha»: ilovadan oldin yig'ilgan jamg'arma — boshlang'ich balans.
    pub fn record_initial_balance(
        &self,
        space_id: &str,
        amount: &str,
    ) -> Result<VaultTxDto, AppError> {
        let ctx = self.ctx()?;
        let amount = positive(&ctx, amount, "amount")?;
        self.vault_insert(&ctx, space_id, amount, VaultReason::Initial, None, None)
    }

    pub fn deposit_to_vault(
        &self,
        space_id: &str,
        amount: &str,
        note: Option<&str>,
    ) -> Result<VaultTxDto, AppError> {
        let ctx = self.ctx()?;
        let amount = positive(&ctx, amount, "amount")?;
        self.vault_insert(
            &ctx,
            space_id,
            amount,
            VaultReason::Manual,
            None,
            clean_opt(note),
        )
    }

    /// Pul olish: sabab majburiy. PIN tasdig'i adapterda (qulf ekrani) so'raladi (uy/SPEC 2.2).
    pub fn withdraw_from_vault(
        &self,
        space_id: &str,
        amount: &str,
        reason: &str,
    ) -> Result<VaultTxDto, AppError> {
        let ctx = self.ctx()?;
        let scope = self.scope(&ctx, space_id)?;
        let amount = positive(&ctx, amount, "amount")?;
        let reason = required(reason, "reason")?;
        let vault_asset = self.vault_asset(&scope)?;
        let balance = self
            .db
            .read(|c| vault::balance(c, &scope, &vault_asset.id))?;
        if amount.minor() > balance {
            return Err(AppError::on("INSUFFICIENT_VAULT_BALANCE", "amount"));
        }
        self.vault_insert(
            &ctx,
            space_id,
            amount.checked_neg()?,
            VaultReason::Withdrawal,
            None,
            Some(reason),
        )
    }

    pub fn set_allocation_rule(
        &self,
        space_id: &str,
        input: AllocationRuleInput,
    ) -> Result<AllocationRuleDto, AppError> {
        let ctx = self.ctx()?;
        let scope = self.scope(&ctx, space_id)?;
        let row = match input.kind.as_str() {
            "PERCENT" => {
                let bp = i64::from(input.bp.ok_or(AppError::on("REQUIRED", "bp"))?);
                if !(0..=10_000).contains(&bp) {
                    return Err(AppError::on("INVALID_BP", "bp"));
                }
                rules::AllocationRuleRow {
                    id: self.new_id(),
                    kind: input.kind.clone(),
                    bp: Some(bp),
                    amount_minor: None,
                    currency: None,
                    progressive: input.progressive,
                }
            }
            "FIXED" => {
                let m = positive(&ctx, input.amount.as_deref().unwrap_or_default(), "amount")?;
                rules::AllocationRuleRow {
                    id: self.new_id(),
                    kind: input.kind.clone(),
                    bp: None,
                    amount_minor: Some(m.minor()),
                    currency: Some(m.currency().code().to_string()),
                    progressive: false,
                }
            }
            _ => return Err(AppError::on("INVALID_RULE_KIND", "kind")),
        };
        let meta = self.meta();
        self.db.write(|tx| rules::insert(tx, &scope, &row, &meta))?;
        self.publish(Some(space_id), &[Topic::AllocationRule]);
        self.rule(&ctx, &scope)?
            .map(|(_, dto)| dto)
            .ok_or(AppError::new("CORRUPT_RULE"))
    }

    /// «Kelajagim» ekrani.
    pub fn vault(&self, space_id: &str) -> Result<VaultDto, AppError> {
        let ctx = self.ctx()?;
        let scope = self.scope(&ctx, space_id)?;
        let vault_asset = self.vault_asset(&scope)?;
        let balance = self
            .db
            .read(|c| vault::balance(c, &scope, &vault_asset.id))?;
        let history = self.db.read(|c| vault::list(c, &scope, &vault_asset.id))?;
        let cur = Currency::from_code(vault_asset.currency.as_deref().unwrap_or("UZS"))?;
        Ok(VaultDto {
            streak: self.streak_of(&ctx, &scope, &vault_asset.id)?,
            balance: self.money_dto(&ctx, Money::new(balance, cur)),
            rule: self.rule(&ctx, &scope)?.map(|(_, d)| d),
            history: history
                .into_iter()
                .map(|v| VaultTxDto {
                    id: v.id,
                    amount: self.money_dto(&ctx, Money::new(v.amount_minor, cur)),
                    reason: v.reason,
                    note: v.note,
                    occurred_on: v.occurred_on,
                })
                .collect(),
        })
    }

    /// Tez xarajat kiritish. Toifa kategoriyadan olinadi, o'zgartirish mumkin (uy/SPEC 2B).
    pub fn record_expense(
        &self,
        space_id: &str,
        input: NewExpenseInput,
    ) -> Result<ExpenseDto, AppError> {
        let ctx = self.ctx()?;
        let scope = self.scope(&ctx, space_id)?;
        let amount = positive(&ctx, &input.amount, "amount")?;
        let ch = channel(&input.channel)?;
        let category = self
            .db
            .read(|c| categories::get(c, &scope, &input.category_id))?
            .ok_or(AppError::on("NOT_FOUND", "categoryId"))?;
        let necessity = match parse_necessity(input.necessity.as_deref())? {
            Some(n) => Some(n.as_str().to_string()),
            None => category.default_necessity.clone(),
        };
        let date = self.date_or_today(&ctx, input.occurred_on.as_deref(), "occurredOn")?;
        self.kk_ensure_open(&scope, &ymd(date), "occurredOn")?;
        let row = expenses::ExpenseRow {
            id: self.new_id(),
            category_id: category.id,
            member_id: input.member_id,
            amount_minor: amount.minor(),
            currency: amount.currency().code().to_string(),
            channel: ch.as_str().to_string(),
            occurred_on: ymd(date),
            necessity,
            obligation_id: input.obligation_id,
            is_gift: input.is_gift,
            is_ostentation: input.is_ostentation,
            funded_by_debt: input.funded_by_debt,
            note: clean_opt(input.note.as_deref()),
        };
        let meta = self.meta();
        self.db
            .write(|tx| expenses::insert(tx, &scope, &row, &meta))?;
        self.publish(Some(space_id), &[Topic::Expenses]);
        Ok(ExpenseDto {
            id: row.id,
            amount: self.money_dto(&ctx, amount),
            category_id: row.category_id,
            necessity: row.necessity,
            occurred_on: row.occurred_on,
            funded_by_debt: row.funded_by_debt,
        })
    }

    pub fn delete_expense(&self, space_id: &str, expense_id: &str) -> Result<(), AppError> {
        let ctx = self.ctx()?;
        let scope = self.scope(&ctx, space_id)?;
        if let Some(on) = self
            .db
            .read(|c| expenses::occurred_on(c, &scope, expense_id))?
        {
            self.kk_ensure_open(&scope, &on, "id")?;
        }
        let meta = self.meta();
        self.db
            .write(|tx| expenses::soft_delete(tx, &scope, expense_id, &meta))?;
        self.publish(Some(space_id), &[Topic::Expenses]);
        Ok(())
    }

    /// Oylik audit va bosh ekran KPI'lari. `date` — davr ichidagi istalgan sana (standart — bugun),
    /// `balance_delta` — naqd va karta qoldig'i o'zgarishi (standart — 0).
    pub fn monthly_summary(
        &self,
        space_id: &str,
        date: Option<&str>,
        balance_delta: Option<&str>,
    ) -> Result<MonthlySummaryDto, AppError> {
        let ctx = self.ctx()?;
        let scope = self.scope(&ctx, space_id)?;
        let cur = ctx.currency;
        let day = self.date_or_today(&ctx, date, "date")?;
        let (start, end) =
            month_period(day, ctx.month_start_day).ok_or(AppError::new("INVALID_PERIOD"))?;
        let (from, to) = (ymd(start), ymd(end));
        let delta = match balance_delta {
            None => Money::zero(cur),
            Some(s) => parse_amount(s, cur).map_err(|e| AppError::on(e.code(), "balanceDelta"))?,
        };

        let inc = self
            .db
            .read(|c| incomes::list_between(c, &scope, &from, &to))?;
        let exp = self
            .db
            .read(|c| expenses::list_between(c, &scope, &from, &to))?;
        let cats = self.db.read(|c| categories::list(c, &scope))?;
        let sadaqa_ids: Vec<&str> = cats
            .iter()
            .filter(|c| c.name_key == SADAQA_KEY)
            .map(|c| c.id.as_str())
            .collect();
        let vault_asset = self.vault_asset(&scope)?;
        let vtx: Vec<vault::VaultTxRow> = self
            .db
            .read(|c| vault::list(c, &scope, &vault_asset.id))?
            .into_iter()
            .filter(|v| {
                v.occurred_on >= from
                    && v.occurred_on < to
                    && v.reason != VaultReason::Initial.as_str()
            })
            .collect();

        let income = sum(inc.iter().map(|r| r.amount_minor), cur)?;
        let obligations = sum(
            exp.iter()
                .filter(|e| e.obligation_id.is_some())
                .map(|e| e.amount_minor),
            cur,
        )?;
        let others: Vec<&expenses::ExpenseRow> =
            exp.iter().filter(|e| e.obligation_id.is_none()).collect();
        let expenses_total = sum(others.iter().map(|e| e.amount_minor), cur)?;
        let by = |n: Option<Necessity>| -> Result<Money, AppError> {
            sum(
                others
                    .iter()
                    .filter(|e| !sadaqa_ids.contains(&e.category_id.as_str()))
                    .filter(|e| e.necessity.as_deref() == n.map(Necessity::as_str))
                    .map(|e| e.amount_minor),
                cur,
            )
        };
        let sadaqa = sum(
            others
                .iter()
                .filter(|e| sadaqa_ids.contains(&e.category_id.as_str()))
                .map(|e| e.amount_minor),
            cur,
        )?;
        let vault_net = sum(vtx.iter().map(|v| v.amount_minor), cur)?;
        let paid_to_self = sum(
            vtx.iter()
                .filter(|v| v.amount_minor > 0)
                .map(|v| v.amount_minor),
            cur,
        )?;
        let gap = unexplained_gap(&GapInput {
            income,
            obligations_paid: obligations,
            expenses: expenses_total,
            vault_net,
            balance_delta: delta,
        })?;
        let month_result = income
            .checked_sub(obligations)?
            .checked_sub(expenses_total)?;
        let d = |m: Money| self.money_dto(&ctx, m);
        Ok(MonthlySummaryDto {
            period_start: from,
            period_end: to,
            income: d(income),
            paid_to_self: d(paid_to_self),
            obligations_paid: d(obligations),
            expenses: d(expenses_total),
            by_necessity: NecessityTotalsDto {
                zarur: d(by(Some(Necessity::Zarur))?),
                kerak: d(by(Some(Necessity::Kerak))?),
                havas: d(by(Some(Necessity::Havas))?),
                sadaqa: d(sadaqa),
                unclassified: d(by(None)?),
            },
            vault_net: d(vault_net),
            balance_delta: d(delta),
            unexplained_gap: d(gap),
            month_result: d(month_result),
        })
    }

    /// Yangi kelishuv qoralamasi. Jurnalni faqat shu qurilma yuritadi (6.6).
    pub fn create_agreement(
        &self,
        space_id: &str,
        agreement_type: &str,
        title: &str,
    ) -> Result<AgreementDto, AppError> {
        let ctx = self.ctx()?;
        let scope = self.scope(&ctx, space_id)?;
        parse_agreement_type(agreement_type)?;
        let row = agreements::AgreementRow {
            id: self.new_id(),
            agreement_type: agreement_type.to_string(),
            status: "DRAFT".to_string(),
            title: required(title, "title")?,
            keeper_device_id: self.device_id.clone(),
        };
        let meta = self.meta();
        self.db
            .write(|tx| agreements::insert(tx, &scope, &row, &meta))?;
        self.publish(Some(space_id), &[Topic::Agreements]);
        Ok(AgreementDto {
            id: row.id,
            agreement_type: row.agreement_type,
            status: row.status,
            title: row.title,
            keeper_device_id: row.keeper_device_id,
        })
    }

    /// 9 savol to'liqligi (sof funksiya — UI har o'zgarishda chaqiradi).
    pub fn check_agreement(
        &self,
        agreement_type: &str,
        draft: AgreementDraft,
    ) -> Result<Completeness, AppError> {
        Ok(check_completeness(
            parse_agreement_type(agreement_type)?,
            &draft,
        ))
    }

    fn journal_dto(
        &self,
        ctx: &Ctx,
        s: &journal::StoredEntry,
    ) -> Result<JournalEntryDto, AppError> {
        let amount = match &s.entry.amount {
            Some(a) => {
                Some(self.money_dto(ctx, Money::new(a.minor, Currency::from_code(&a.currency)?)))
            }
            None => None,
        };
        Ok(JournalEntryDto {
            id: s.entry.id.clone(),
            seq: u32::try_from(s.seq).map_err(|_| AppError::new("CORRUPT_ROW"))?,
            kind: s.entry.kind.as_str().to_string(),
            party_id: s.entry.party_id.clone(),
            amount,
            date: s.entry.date.clone(),
            note: s.entry.note.clone(),
            corrects_entry_id: s.entry.corrects_entry_id.clone(),
            hash: s.hash.clone(),
            short_code: short_code(&s.hash),
        })
    }

    /// Jurnalga yozuv qo'shish (append-only). Faqat hisob yurituvchi qurilma yozadi.
    pub fn append_journal(
        &self,
        space_id: &str,
        agreement_id: &str,
        input: NewJournalEntryInput,
    ) -> Result<JournalEntryDto, AppError> {
        let ctx = self.ctx()?;
        let scope = self.scope(&ctx, space_id)?;
        let agreement = self
            .db
            .read(|c| agreements::get(c, &scope, agreement_id))?
            .ok_or(AppError::on("NOT_FOUND", "agreementId"))?;
        if agreement.keeper_device_id != self.device_id {
            return Err(AppError::new("NOT_JOURNAL_KEEPER"));
        }
        let kind =
            EntryKind::parse(&input.kind).ok_or(AppError::on("INVALID_ENTRY_KIND", "kind"))?;
        let amount = match (&input.amount, &input.currency) {
            (None, _) => None,
            (Some(a), cur) => {
                let c = match cur {
                    Some(code) => Currency::from_code(code)?,
                    None => ctx.currency,
                };
                let m = parse_amount(a, c).map_err(|e| AppError::on(e.code(), "amount"))?;
                Some(JournalAmount {
                    minor: m.minor(),
                    currency: c.code().to_string(),
                })
            }
        };
        let date = self.date_or_today(&ctx, input.date.as_deref(), "date")?;
        let entry = JournalEntry {
            id: self.new_id(),
            agreement_id: agreement.id,
            kind,
            party_id: clean_opt(input.party_id.as_deref()),
            amount,
            date: ymd(date),
            note: clean_opt(input.note.as_deref()),
            corrects_entry_id: clean_opt(input.corrects_entry_id.as_deref()),
            refs: input
                .refs
                .iter()
                .filter_map(|r| clean_opt(Some(r)))
                .collect(),
        };
        entry.validate()?;
        let meta = self.meta();
        let stored = self
            .db
            .write(|tx| journal::append(tx, &scope, &entry, &meta))?;
        self.publish(Some(space_id), &[Topic::Journal]);
        self.journal_dto(&ctx, &stored)
    }

    pub fn journal(
        &self,
        space_id: &str,
        agreement_id: &str,
    ) -> Result<Vec<JournalEntryDto>, AppError> {
        let ctx = self.ctx()?;
        let scope = self.scope(&ctx, space_id)?;
        let stored = self.db.read(|c| journal::list(c, &scope, agreement_id))?;
        stored.iter().map(|s| self.journal_dto(&ctx, s)).collect()
    }

    /// Zanjirni qayta hisoblab tekshirish (oylik ko'rik, import, hakam papkasi).
    pub fn verify_journal(
        &self,
        space_id: &str,
        agreement_id: &str,
    ) -> Result<ChainStatusDto, AppError> {
        let ctx = self.ctx()?;
        let scope = self.scope(&ctx, space_id)?;
        let stored = self.db.read(|c| journal::list(c, &scope, agreement_id))?;
        let entries: Vec<JournalEntry> = stored.iter().map(|s| s.entry.clone()).collect();
        let hashes: Vec<String> = stored.iter().map(|s| s.hash.clone()).collect();
        let count = u32::try_from(entries.len()).map_err(|_| AppError::new("OVERFLOW"))?;
        Ok(match verify_chain(&entries, &hashes) {
            Ok(head) => ChainStatusDto {
                ok: true,
                entries: count,
                short_code: Some(short_code(&head)),
                head: Some(head),
                first_broken_seq: None,
            },
            Err(ChainError::FirstBroken { seq }) | Err(ChainError::InvalidEntry { seq, .. }) => {
                ChainStatusDto {
                    ok: false,
                    entries: count,
                    head: None,
                    short_code: None,
                    first_broken_seq: u32::try_from(seq).ok(),
                }
            }
            Err(e) => return Err(e.into()),
        })
    }

    /// Qarzdan chiqish rejalovchisi: odatiy va tezlashtirilgan grafik (sof hisob).
    pub fn simulate_loan(&self, input: LoanSimulationInput) -> Result<LoanSimulationDto, AppError> {
        let ctx = self.ctx()?;
        let cur = Currency::from_code(&input.currency)?;
        let principal =
            parse_amount(&input.principal, cur).map_err(|e| AppError::on(e.code(), "principal"))?;
        let extra = parse_amount(&input.extra_per_month, cur)
            .map_err(|e| AppError::on(e.code(), "extraPerMonth"))?;
        let kind = match input.kind.as_str() {
            "ANNUITY" => ScheduleKind::Annuity,
            "DIFFERENTIATED" => ScheduleKind::Differentiated,
            _ => return Err(AppError::on("UNSUPPORTED_SCHEDULE_KIND", "kind")),
        };
        let terms = LoanTerms {
            principal,
            annual_bp: i64::from(input.annual_bp),
            months: input.months,
            kind,
        };
        let base = simulate(&terms, Money::zero(cur))?;
        let fast = simulate(&terms, extra)?;
        let acc = compare(&base, &fast)?;
        let d = |m: Money| self.money_dto(&ctx, m);
        Ok(LoanSimulationDto {
            payment: d(base.payment),
            base_months: base.months(),
            base_total_interest: d(base.total_interest),
            accelerated_months: fast.months(),
            accelerated_total_interest: d(fast.total_interest),
            months_saved: acc.months_saved,
            interest_saved: d(acc.interest_saved),
            accelerated_schedule: fast
                .rows
                .iter()
                .map(|r| ScheduleRowDto {
                    month: r.month,
                    interest: d(r.interest),
                    principal: d(r.principal),
                    extra: d(r.extra),
                    balance: d(r.balance),
                })
                .collect(),
        })
    }
}
