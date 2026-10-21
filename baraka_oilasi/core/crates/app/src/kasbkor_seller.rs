//! Sotuvchi qurilmasi (K8, ADR-0003): katalogdan sotuv, bugungi o'z yozuvlari va smena.
//!
//! Sotuvchi qurilmasida tovar qoldig'i yo'q (xaridlar yuborilmaydi), shuning uchun sotuv qoldiqqa
//! shu yerda tekshirilmaydi — egasining importida tekshiriladi. Sotuv sanasi — faqat bugun; smena
//! yopilgandan keyin shu kuni naqd yoki karta yozuvi qo'shilmaydi.
use baraka_domain_kasbkor::cash::CashReason;
use baraka_domain_kasbkor::owner::Wallet;
use baraka_domain_kasbkor::shift::{shift_close, ShiftClose, ShiftIn, ShiftInKind};
use baraka_domain_kasbkor::stock::replacement;
use baraka_money::Money;
use baraka_storage::repo::{incomes, kk_stock, roles, sync};
use baraka_storage::SpaceScope;
use chrono::{Days, NaiveDate};
use serde_json::Value;

use crate::access::Role;
use crate::app::Ctx;
use crate::events::Topic;
use crate::kasbkor::wallet;
use crate::kasbkor_stock::{factor, parse_qty, show_qty};
use crate::receipt::ymd;
use crate::text::clean_opt;
use crate::uy::positive;
use crate::*;

/// Smena farqlari shu muddatda takrorlanuvchi kamomadga qaraladi (kunlik kassa kabi — 4 hafta).
const RECENT_DAYS: u64 = 28;

fn amount_opt(ctx: &Ctx, s: Option<&str>, field: &str) -> Result<Option<Money>, AppError> {
    match s.map(str::trim).filter(|t| !t.is_empty()) {
        None => Ok(None),
        Some(t) => Ok(Some(positive(ctx, t, field)?)),
    }
}

/// Bo'sh bo'lmasa — nol yoki musbat summa.
fn amount_zero_ok(ctx: &Ctx, s: Option<&str>, field: &str) -> Result<Option<Money>, AppError> {
    match s.map(str::trim).filter(|t| !t.is_empty()) {
        None => Ok(None),
        Some("0") => Ok(Some(Money::zero(ctx.currency))),
        Some(t) => Ok(Some(positive(ctx, t, field)?)),
    }
}

impl App {
    /// Sotuvchi faqat bugungi sana bilan yozadi.
    pub(crate) fn kk_ensure_seller_today(
        &self,
        ctx: &Ctx,
        on: NaiveDate,
        field: &str,
    ) -> Result<(), AppError> {
        if self.access(ctx)?.role == Role::Seller && on != self.today(ctx) {
            return Err(AppError::on("DATE_NOT_TODAY", field));
        }
        Ok(())
    }

    /// Shu qurilma shu kunning smenasini yopgan bo'lsa — yangi tushum yozilmaydi.
    pub(crate) fn kk_ensure_shift_open(
        &self,
        scope: &SpaceScope,
        day: &str,
    ) -> Result<(), AppError> {
        let closed = self
            .db
            .read(|c| roles::shifts(c, scope, Some(&self.device_id)))?
            .iter()
            .any(|s| s.day == day);
        if closed {
            Err(AppError::new("SHIFT_CLOSED"))
        } else {
            Ok(())
        }
    }

    /// Tovar katalogi: nomi, birligi, sotuv narxi (tannarxsiz).
    pub fn kk_catalog(&self, space_id: &str) -> Result<Vec<KkCatalogItemDto>, AppError> {
        let ctx = self.ctx()?;
        let scope = self.kk_scope_seller(&ctx, space_id)?;
        let mut items = self.db.read(|c| kk_stock::items(c, &scope))?;
        items.retain(|i| i.currency == ctx.currency.code());
        items.sort_by_key(|i| i.name.to_lowercase());
        Ok(items
            .into_iter()
            .map(|i| KkCatalogItemDto {
                sale_price: i
                    .sale_price_minor
                    .map(|p| self.money_dto(&ctx, Money::new(p, ctx.currency))),
                id: i.id,
                name: i.name,
                unit: i.unit,
            })
            .collect())
    }

    /// Sotuv: katalogdan (miqdor bilan) yoki erkin summa. Bugungi sana, shu qurilma nomidan.
    pub fn kk_seller_sale(
        &self,
        space_id: &str,
        input: KkSellerSaleInput,
    ) -> Result<KkSellerDayDto, AppError> {
        let ctx = self.ctx()?;
        let scope = self.kk_scope_seller(&ctx, space_id)?;
        let cur = ctx.currency;
        let w = wallet(&input.channel, "channel")?;
        let day = ymd(self.today(&ctx));
        self.kk_ensure_open(&scope, &day, "occurredOn")?;
        self.kk_ensure_cash_open(&scope, &day, w == Wallet::Cash)?;
        self.kk_ensure_shift_open(&scope, &day)?;
        let note = clean_opt(input.note.as_deref());
        let amount = amount_opt(&ctx, input.amount.as_deref(), "amount")?;
        let item_id = clean_opt(input.item_id.as_deref());
        let (income, stock_move) = match item_id {
            None => {
                let amount = amount.ok_or(AppError::on("REQUIRED", "amount"))?;
                let income = incomes::IncomeRow {
                    id: self.new_id(),
                    member_id: None,
                    amount_minor: amount.minor(),
                    currency: cur.code().to_string(),
                    source: note.clone().unwrap_or_default(),
                    channel: w.as_str().to_string(),
                    source_type: None,
                    occurred_on: day.clone(),
                    note: None,
                };
                (income, None)
            }
            Some(item_id) => {
                let item = self
                    .db
                    .read(|c| kk_stock::items(c, &scope))?
                    .into_iter()
                    .find(|i| i.id == item_id && i.currency == cur.code())
                    .ok_or(AppError::on("NOT_FOUND", "itemId"))?;
                let f = factor(&item.unit)?;
                let qty = parse_qty(input.qty.as_deref().unwrap_or_default(), f, "qty")?;
                if qty <= 0 {
                    return Err(AppError::on("INVALID_QTY", "qty"));
                }
                // Kasb-kor sotuvidagi kabi: summa bo'lmasa — sotuv narxi × miqdor.
                let revenue = match amount {
                    Some(a) => a,
                    None => {
                        let p = item
                            .sale_price_minor
                            .map(|p| Money::new(p, cur))
                            .ok_or(AppError::on("REQUIRED", "amount"))?;
                        let v = replacement(qty, Money::zero(cur), p, f, None)?.replacement_value;
                        if !v.is_positive() {
                            return Err(AppError::on("AMOUNT_NOT_POSITIVE", "amount"));
                        }
                        v
                    }
                };
                let income = incomes::IncomeRow {
                    id: self.new_id(),
                    member_id: None,
                    amount_minor: revenue.minor(),
                    currency: cur.code().to_string(),
                    source: match &note {
                        Some(n) => format!("{}: {n}", item.name),
                        None => item.name.clone(),
                    },
                    channel: w.as_str().to_string(),
                    source_type: None,
                    occurred_on: day.clone(),
                    note: None,
                };
                let mv = kk_stock::KkStockMoveRow {
                    id: self.new_id(),
                    item_id: item.id,
                    kind: "SALE".into(),
                    occurred_on: day.clone(),
                    qty,
                    amount_minor: Some(revenue.minor()),
                    wallet: Some(w.as_str().to_string()),
                    income_id: Some(income.id.clone()),
                    reason: None,
                };
                (income, Some(mv))
            }
        };
        let meta = self.meta();
        self.db.write(|tx| {
            incomes::insert(tx, &scope, &income, &meta)?;
            if let Some(mv) = &stock_move {
                kk_stock::insert_move(tx, &scope, mv, &meta)?;
            }
            Ok(())
        })?;
        self.publish(Some(space_id), &[Topic::Incomes, Topic::Kasbkor]);
        self.kk_seller_day(space_id)
    }

    /// Bugungi o'z yozuvlari (savdo va nasiya to'lovlari), naqd va karta jami, smena holati.
    pub fn kk_seller_day(&self, space_id: &str) -> Result<KkSellerDayDto, AppError> {
        let ctx = self.ctx()?;
        let scope = self.kk_scope_seller(&ctx, space_id)?;
        let day = ymd(self.today(&ctx));
        let rows = self
            .db
            .read(|c| roles::own_day_incomes(c, &scope, &self.device_id, &day))?;
        let (mut cash, mut card) = (Money::zero(ctx.currency), Money::zero(ctx.currency));
        let mut sales = Vec::new();
        for r in rows {
            let m = Money::new(r.amount_minor, ctx.currency);
            if r.channel == "CASH" {
                cash = cash.checked_add(m)?;
            } else {
                card = card.checked_add(m)?;
            }
            let qty = match (r.qty, r.unit.as_deref()) {
                (Some(q), Some(u)) => Some(show_qty(q, factor(u)?)),
                _ => None,
            };
            sales.push(KkSellerSaleDto {
                id: r.id,
                kind: if r.is_payment {
                    "CREDIT_PAYMENT"
                } else {
                    "SALE"
                }
                .into(),
                label: r.source,
                qty,
                amount: self.money_dto(&ctx, m),
                channel: r.channel,
            });
        }
        Ok(KkSellerDayDto {
            shift_closed: self.kk_ensure_shift_open(&scope, &day).is_err(),
            day,
            sales,
            cash: self.money_dto(&ctx, cash),
            card: self.money_dto(&ctx, card),
        })
    }

    /// Smena hisobi: ochilish (oldingi smenada qolgani yoki kiritilgan), bugungi o'z tushumlari.
    fn kk_shift_compute(
        &self,
        ctx: &Ctx,
        scope: &SpaceScope,
        input: &KkShiftInput,
    ) -> Result<(KkShiftDto, Option<Result<ShiftClose, AppError>>), AppError> {
        let cur = ctx.currency;
        let d = |m: Money| self.money_dto(ctx, m);
        let today = self.today(ctx);
        let day = ymd(today);
        let mine = self
            .db
            .read(|c| roles::shifts(c, scope, Some(&self.device_id)))?;
        let closed = mine.iter().any(|s| s.day == day);
        let last = mine.iter().find(|s| s.day < day);
        let opening = match last {
            Some(s) => Money::new(s.counted_minor - s.handed_over_minor, cur),
            None => amount_zero_ok(ctx, input.opening.as_deref(), "opening")?
                .unwrap_or(Money::zero(cur)),
        };
        let since = ymd(today
            .checked_sub_days(Days::new(RECENT_DAYS))
            .ok_or(AppError::new("INVALID_DATE"))?);
        let recent: Vec<Money> = mine
            .iter()
            .filter(|s| s.day >= since && s.day < day)
            .map(|s| Money::new(s.difference_minor, cur))
            .collect();
        let ins: Vec<ShiftIn> = self
            .db
            .read(|c| roles::own_day_incomes(c, scope, &self.device_id, &day))?
            .into_iter()
            .map(|r| ShiftIn {
                kind: if r.is_payment {
                    ShiftInKind::CreditPayment
                } else {
                    ShiftInKind::Sale
                },
                wallet: if r.channel == "CASH" {
                    Wallet::Cash
                } else {
                    Wallet::Card
                },
                amount: Money::new(r.amount_minor, cur),
            })
            .collect();
        let counted = amount_zero_ok(ctx, input.counted.as_deref(), "counted")?;
        let handed = amount_zero_ok(ctx, input.handed_over.as_deref(), "handedOver")?
            .unwrap_or(Money::zero(cur));
        let reason = match clean_opt(input.reason.as_deref()) {
            Some(r) => Some(CashReason::parse(&r).ok_or(AppError::on("INVALID_REASON", "reason"))?),
            None => None,
        };
        // Sanalgan kiritilmagan bo'lsa — kutilganni ko'rsatish uchun shu summa bilan hisoblanadi.
        let base = shift_close(
            opening,
            &ins,
            Money::zero(cur),
            Money::zero(cur),
            Some(CashReason::Unknown),
            &[],
        )?;
        let mut dto = KkShiftDto {
            day,
            opening: d(opening),
            opening_known: last.is_some(),
            cash_sales: d(base.cash_sales),
            credit_payments: d(base.credit_payments),
            card_in: d(base.card_in),
            expected: d(base.expected),
            counted: None,
            difference: None,
            status: None,
            handed_over: None,
            left: None,
            suggest_search: false,
            closed,
        };
        let Some(counted) = counted else {
            return Ok((dto, None));
        };
        // Sabab hali tanlanmagan bo'lsa ham farq ko'rinsin.
        let preview = shift_close(
            opening,
            &ins,
            counted,
            handed,
            reason.or(Some(CashReason::Unknown)),
            &recent,
        )?;
        dto.counted = Some(d(counted));
        dto.difference = Some(d(preview.difference));
        dto.status = Some(preview.status.as_str().to_string());
        dto.handed_over = Some(d(preview.handed_over));
        dto.left = Some(d(preview.left));
        dto.suggest_search = preview.suggest_search;
        let real =
            shift_close(opening, &ins, counted, handed, reason, &recent).map_err(AppError::from);
        Ok((dto, Some(real)))
    }

    /// Smena hisobi (saqlanmaydi).
    pub fn kk_shift_draft(
        &self,
        space_id: &str,
        input: KkShiftInput,
    ) -> Result<KkShiftDto, AppError> {
        let ctx = self.ctx()?;
        let scope = self.kk_scope_seller(&ctx, space_id)?;
        Ok(self.kk_shift_compute(&ctx, &scope, &input)?.0)
    }

    /// Smenani yopish: kuniga bitta, o'zgarmas.
    pub fn kk_close_shift(
        &self,
        space_id: &str,
        input: KkShiftInput,
    ) -> Result<KkShiftDto, AppError> {
        let ctx = self.ctx()?;
        let scope = self.kk_scope_seller(&ctx, space_id)?;
        let (dto, close) = self.kk_shift_compute(&ctx, &scope, &input)?;
        if dto.closed {
            return Err(AppError::new("SHIFT_CLOSED"));
        }
        let r = close.ok_or(AppError::on("REQUIRED", "counted"))??;
        let row = roles::KkShiftRow {
            id: self.new_id(),
            device_id: self.device_id.clone(),
            day: dto.day.clone(),
            currency: ctx.currency.code().to_string(),
            opening_minor: r
                .expected
                .checked_sub(r.cash_sales)?
                .checked_sub(r.credit_payments)?
                .minor(),
            cash_sales_minor: r.cash_sales.minor(),
            credit_payments_minor: r.credit_payments.minor(),
            card_in_minor: r.card_in.minor(),
            expected_minor: r.expected.minor(),
            counted_minor: r.expected.checked_add(r.difference)?.minor(),
            difference_minor: r.difference.minor(),
            reason: r.reason.map(|x| x.as_str().to_string()),
            handed_over_minor: r.handed_over.minor(),
            note: clean_opt(input.note.as_deref()),
            closed_at: self.meta().now,
        };
        let meta = self.meta();
        self.db
            .write(|tx| roles::insert_shift(tx, &scope, &row, &meta))?;
        self.publish(Some(space_id), &[Topic::Kasbkor]);
        Ok(self
            .kk_shift_compute(
                &ctx,
                &scope,
                &KkShiftInput {
                    opening: None,
                    counted: None,
                    handed_over: None,
                    reason: None,
                    note: None,
                },
            )?
            .0)
    }

    /// Smenalar: egasi va hisobchi — hammasi, sotuvchi — o'ziniki.
    pub fn kk_shifts(&self, space_id: &str) -> Result<Vec<KkShiftRecordDto>, AppError> {
        let ctx = self.ctx()?;
        let scope = self.kk_scope_seller(&ctx, space_id)?;
        let mine = (self.access(&ctx)?.role == Role::Seller).then_some(self.device_id.as_str());
        let rows = self.db.read(|c| roles::shifts(c, &scope, mine))?;
        let devices = self
            .db
            .read(|c| sync::dump(c, &ctx.household_id, "devices"))?;
        let name_of = |id: &str| {
            devices
                .iter()
                .find(|d| d.get("id").and_then(Value::as_str) == Some(id))
                .and_then(|d| d.get("name").and_then(Value::as_str))
                .unwrap_or_default()
                .to_string()
        };
        let cur = ctx.currency;
        let d = |m: i64| self.money_dto(&ctx, Money::new(m, cur));
        Ok(rows
            .into_iter()
            .map(|r| KkShiftRecordDto {
                device_name: name_of(&r.device_id),
                status: match r.difference_minor {
                    0 => "EXACT",
                    x if x < 0 => "SHORT",
                    _ => "OVER",
                }
                .into(),
                opening: d(r.opening_minor),
                cash_sales: d(r.cash_sales_minor),
                credit_payments: d(r.credit_payments_minor),
                card_in: d(r.card_in_minor),
                expected: d(r.expected_minor),
                counted: d(r.counted_minor),
                difference: d(r.difference_minor),
                handed_over: d(r.handed_over_minor),
                left: d(r.counted_minor - r.handed_over_minor),
                id: r.id,
                device_id: r.device_id,
                day: r.day,
                reason: r.reason,
                note: r.note,
            })
            .collect())
    }
}
