//! K5 — Kasb-kor «Tovar ham pul — u ham yotadi» (`docs/kasbkor/SPEC.md` 4.1–4.4): tovar kartochkasi,
//! harakatlar (xarid, sotuv, hisobdan chiqarish, inventarizatsiya), tannarx, qayta tiklash narxi va
//! muzlagan tovar.
//!
//! Hisob `domain-kasbkor::stock` da (vektorlar `kk_cogs`, `kk_replacement`). Tannarx har safar barcha
//! harakatlarni sana tartibida qayta o'ynab hisoblanadi; yangi harakat ham shu tarzda tekshiriladi
//! (orqa sanadagi harakat keyingi sotuvlarni «qoldiqdan ko'p» qilib qo'ymasligi uchun).
//! Sotuv — bitta tranzaksiyada Kasb-kor tushumi ham.
use std::collections::HashMap;

use baraka_domain_kasbkor::stock::{
    is_frozen, replacement, validate_factor, CostMethod, Stock, StockMove,
};
use baraka_money::{Currency, Money};
use baraka_storage::repo::{incomes, kk_stock};
use baraka_storage::SpaceScope;
use chrono::NaiveDate;

use crate::app::Ctx;
use crate::events::Topic;
use crate::kasbkor::wallet;
use crate::receipt::ymd;
use crate::text::{clean_opt, required};
use crate::uy::positive;
use crate::*;

const DEFAULT_FROZEN_DAYS: u32 = 90;

fn corrupt() -> AppError {
    AppError::new("CORRUPT_ROW")
}

/// Ko'rsatish birligi: kg, l, m — 1000 asosiy birlik; dona — 1.
pub(crate) fn factor(unit: &str) -> Result<i64, AppError> {
    let f = match unit {
        "G" | "ML" | "MM" => 1000,
        "PCS" => 1,
        _ => return Err(AppError::on("INVALID_UNIT", "unit")),
    };
    validate_factor(f)?;
    Ok(f)
}

/// «1,5» kg → 1500 g. Kasr — vergul yoki nuqta bilan, 1000 li birlikda 3 xonagacha; dona — butun.
pub(crate) fn parse_qty(s: &str, factor: i64, field: &str) -> Result<i64, AppError> {
    let err = || AppError::on("INVALID_QTY", field);
    let t: String = s
        .chars()
        .filter(|c| !c.is_whitespace() && *c != '\u{202f}')
        .collect();
    let (int, frac) = match t.split_once([',', '.']) {
        Some((i, f)) => (i, f),
        None => (t.as_str(), ""),
    };
    let digits = |p: &str| p.chars().all(|c| c.is_ascii_digit());
    if int.is_empty() && frac.is_empty() || !digits(int) || !digits(frac) {
        return Err(err());
    }
    let places = if factor == 1000 { 3 } else { 0 };
    if frac.len() > places {
        return Err(err());
    }
    let whole: i64 = if int.is_empty() {
        0
    } else {
        int.parse().map_err(|_| err())?
    };
    let mut part: i64 = if frac.is_empty() {
        0
    } else {
        frac.parse().map_err(|_| err())?
    };
    for _ in frac.len()..places {
        part *= 10;
    }
    whole
        .checked_mul(factor)
        .and_then(|w| w.checked_add(part))
        .ok_or_else(err)
}

/// 1500 g → «1,5»; −80000 g → «-80».
pub(crate) fn show_qty(q: i64, factor: i64) -> String {
    let sign = if q < 0 { "-" } else { "" };
    let a = q.unsigned_abs();
    let f = factor.unsigned_abs();
    let (whole, part) = (a / f, a % f);
    if part == 0 {
        return format!("{sign}{whole}");
    }
    let frac = format!("{part:03}");
    format!("{sign}{whole},{}", frac.trim_end_matches('0'))
}

fn parse_day(s: &str) -> Result<NaiveDate, AppError> {
    NaiveDate::parse_from_str(s, "%Y-%m-%d").map_err(|_| corrupt())
}

fn stock_move(r: &kk_stock::KkStockMoveRow, cur: Currency) -> Result<StockMove, AppError> {
    let amount = Money::new(r.amount_minor.unwrap_or(0), cur);
    Ok(match r.kind.as_str() {
        "PURCHASE" => StockMove::Purchase { qty: r.qty, amount },
        "SALE" => StockMove::Sale { qty: r.qty },
        "WRITE_OFF" => StockMove::WriteOff { qty: r.qty },
        "ADJUST" => StockMove::Adjust { qty: r.qty, amount },
        _ => return Err(corrupt()),
    })
}

/// Bitta tovarning qayta o'ynalgan holati.
pub(crate) struct ItemState {
    pub item: kk_stock::KkItemRow,
    pub factor: i64,
    pub stock: Stock,
    pub last_sale: Option<NaiveDate>,
    pub first_purchase: Option<NaiveDate>,
    /// Oxirgi xarid narxi, ko'rsatish birligiga.
    pub last_price: Option<Money>,
    /// Harakatlar va ularning tannarxi (sana tartibida).
    pub costs: Vec<(kk_stock::KkStockMoveRow, Money)>,
}

impl ItemState {
    fn new(item: kk_stock::KkItemRow, cur: Currency) -> Result<Self, AppError> {
        let method = CostMethod::parse(&item.method).ok_or_else(corrupt)?;
        Ok(Self {
            factor: factor(&item.unit)?,
            stock: Stock::new(method, cur),
            item,
            last_sale: None,
            first_purchase: None,
            last_price: None,
            costs: Vec::new(),
        })
    }

    fn apply(&mut self, r: kk_stock::KkStockMoveRow, cur: Currency) -> Result<(), AppError> {
        let m = stock_move(&r, cur)?;
        let cost = self.stock.apply(m)?;
        let on = parse_day(&r.occurred_on)?;
        match m {
            StockMove::Purchase { qty, amount } => {
                self.first_purchase = Some(self.first_purchase.map_or(on, |d| d.min(on)));
                let mut one = Stock::new(CostMethod::Average, cur);
                one.apply(StockMove::Purchase { qty, amount })?;
                self.last_price = one.unit_cost(self.factor)?;
            }
            StockMove::Sale { .. } => self.last_sale = Some(on),
            _ => {}
        }
        self.costs.push((r, cost));
        Ok(())
    }

    /// Qayta tiklash narxi: qo'lda kiritilgan yoki oxirgi xarid narxi.
    fn price(&self, cur: Currency) -> Option<Money> {
        self.item
            .replacement_price_minor
            .map(|p| Money::new(p, cur))
            .or(self.last_price)
    }
}

/// Makondagi tovarlar holati (`ctx.currency` dagilari), harakatlar sana tartibida qayta o'ynalgan.
fn replay(
    items: Vec<kk_stock::KkItemRow>,
    mut moves: Vec<kk_stock::KkStockMoveRow>,
    cur: Currency,
) -> Result<Vec<ItemState>, AppError> {
    let mut states = Vec::new();
    let mut index = HashMap::new();
    for item in items.into_iter().filter(|i| i.currency == cur.code()) {
        index.insert(item.id.clone(), states.len());
        states.push(ItemState::new(item, cur)?);
    }
    // `moves` allaqachon tovar, sana va yozilish tartibida.
    for r in moves.drain(..) {
        if let Some(&i) = index.get(&r.item_id) {
            states[i].apply(r, cur)?;
        }
    }
    Ok(states)
}

/// Harakat turi bo'yicha davr summalari.
pub(crate) struct StockPeriod {
    /// Sotilgan tovar tannarxi.
    pub cogs: Money,
    /// Hisobdan chiqarish + inventarizatsiya farqi (manfiy — ortiqcha).
    pub losses: Money,
    pub has_moves: bool,
}

impl App {
    fn kk_stock_states(&self, ctx: &Ctx, scope: &SpaceScope) -> Result<Vec<ItemState>, AppError> {
        let items = self.db.read(|c| kk_stock::items(c, scope))?;
        let moves = self.db.read(|c| kk_stock::moves(c, scope))?;
        replay(items, moves, ctx.currency)
    }

    /// `[from, to)` dagi sotuv tannarxi va yo'qotishlar (`kk_period` uchun).
    pub(crate) fn kk_stock_period(
        &self,
        ctx: &Ctx,
        scope: &SpaceScope,
        from: &str,
        to: &str,
    ) -> Result<StockPeriod, AppError> {
        let zero = Money::zero(ctx.currency);
        let mut p = StockPeriod {
            cogs: zero,
            losses: zero,
            has_moves: false,
        };
        for s in self.kk_stock_states(ctx, scope)? {
            for (r, cost) in s
                .costs
                .iter()
                .filter(|(r, _)| r.occurred_on.as_str() >= from && r.occurred_on.as_str() < to)
            {
                p.has_moves = true;
                match r.kind.as_str() {
                    "SALE" => p.cogs = p.cogs.checked_add(*cost)?,
                    "WRITE_OFF" | "ADJUST" => p.losses = p.losses.checked_add(*cost)?,
                    _ => {}
                }
            }
        }
        Ok(p)
    }

    /// Hamyondan to'langan xaridlar `[from, to)`: (id, hamyon, summa, sana, tovar nomi).
    pub(crate) fn kk_stock_purchases(
        &self,
        ctx: &Ctx,
        scope: &SpaceScope,
        from: &str,
        to: &str,
    ) -> Result<Vec<(kk_stock::KkStockMoveRow, String)>, AppError> {
        let names: HashMap<String, String> = self
            .db
            .read(|c| kk_stock::items(c, scope))?
            .into_iter()
            .filter(|i| i.currency == ctx.currency.code())
            .map(|i| (i.id, i.name))
            .collect();
        Ok(self
            .db
            .read(|c| kk_stock::moves(c, scope))?
            .into_iter()
            .filter(|r| {
                r.kind == "PURCHASE"
                    && r.wallet.is_some()
                    && r.occurred_on.as_str() >= from
                    && r.occurred_on.as_str() < to
            })
            .filter_map(|r| names.get(&r.item_id).map(|n| (r.clone(), n.clone())))
            .collect())
    }

    fn kk_stock_dto(&self, ctx: &Ctx, states: Vec<ItemState>) -> Result<KkStockDto, AppError> {
        let cur = ctx.currency;
        let zero = Money::zero(cur);
        let d = |m: Money| self.money_dto(ctx, m);
        let today = self.today(ctx);
        let (mut value, mut repl, mut frozen_value, mut frozen_count) = (zero, zero, zero, 0u32);
        let mut items = Vec::new();
        for s in states {
            let f = s.factor;
            let sale_price = s.item.sale_price_minor.map(|p| Money::new(p, cur));
            let price = s.price(cur);
            let r = price
                .map(|p| replacement(s.stock.qty, s.stock.value, p, f, sale_price))
                .transpose()?;
            let shown = r.map_or(s.stock.value, |r| r.replacement_value);
            let days = u32::try_from(s.item.frozen_days).map_err(|_| corrupt())?;
            let frozen = is_frozen(
                s.stock.qty,
                s.last_sale,
                s.first_purchase,
                today,
                i64::from(days),
            );
            value = value.checked_add(s.stock.value)?;
            repl = repl.checked_add(shown)?;
            if frozen {
                frozen_value = frozen_value.checked_add(shown)?;
                frozen_count += 1;
            }
            let moves = s
                .costs
                .iter()
                .rev()
                .map(|(m, cost)| {
                    let signed = match m.kind.as_str() {
                        "SALE" | "WRITE_OFF" => -m.qty,
                        _ => m.qty,
                    };
                    KkStockMoveDto {
                        id: m.id.clone(),
                        kind: m.kind.clone(),
                        occurred_on: m.occurred_on.clone(),
                        qty: show_qty(signed, f),
                        amount: m.amount_minor.map(|a| d(Money::new(a, cur))),
                        cost: d(*cost),
                        wallet: m.wallet.clone(),
                        reason: m.reason.clone(),
                    }
                })
                .collect();
            items.push(KkItemDto {
                id: s.item.id.clone(),
                name: s.item.name.clone(),
                unit: s.item.unit.clone(),
                method: s.item.method.clone(),
                qty: show_qty(s.stock.qty, f),
                value: d(s.stock.value),
                unit_cost: s.stock.unit_cost(f)?.map(d),
                sale_price: sale_price.map(d),
                replacement_price_input: s
                    .item
                    .replacement_price_minor
                    .map(|p| d(Money::new(p, cur))),
                replacement_price: price.map(d),
                replacement_value: r.map(|r| d(r.replacement_value)),
                inflation_gap: r.map(|r| d(r.inflation_gap)),
                sale_below_replacement: r.is_some_and(|r| r.sale_below_replacement),
                min_qty: s.item.min_qty.map(|q| show_qty(q, f)),
                below_min: s.item.min_qty.is_some_and(|q| s.stock.qty < q),
                frozen_days: days,
                last_sale_on: s.last_sale.map(ymd),
                frozen,
                note: s.item.note.clone(),
                moves,
            });
        }
        Ok(KkStockDto {
            items,
            value: d(value),
            replacement_value: d(repl),
            inflation_gap: d(repl.checked_sub(value)?),
            frozen_value: d(frozen_value),
            frozen_count,
        })
    }

    /// Bosh sahifa uchun: (hisobdagi qiymat, muzlagan qiymat, muzlagan soni).
    pub(crate) fn kk_stock_summary(
        &self,
        ctx: &Ctx,
        scope: &SpaceScope,
    ) -> Result<(Money, Money, u32), AppError> {
        let s = self.kk_stock_dto(ctx, self.kk_stock_states(ctx, scope)?)?;
        let m = |d: &MoneyDto| -> Result<Money, AppError> {
            Ok(Money::new(
                d.minor.parse().map_err(|_| corrupt())?,
                ctx.currency,
            ))
        };
        Ok((m(&s.value)?, m(&s.frozen_value)?, s.frozen_count))
    }

    /// Tovarlar sahifasi.
    pub fn kk_stock(&self, space_id: &str) -> Result<KkStockDto, AppError> {
        let ctx = self.ctx()?;
        let scope = self.kk_scope(&ctx, space_id)?;
        let states = self.kk_stock_states(&ctx, &scope)?;
        self.kk_stock_dto(&ctx, states)
    }

    fn kk_item_row(
        &self,
        ctx: &Ctx,
        id: String,
        input: &KkItemInput,
    ) -> Result<kk_stock::KkItemRow, AppError> {
        let name = required(&input.name, "name")?;
        if name.chars().count() > 100 {
            return Err(AppError::on("TOO_LONG", "name"));
        }
        let f = factor(&input.unit)?;
        let method = match input.method.as_deref() {
            None => CostMethod::Average,
            Some(m) => CostMethod::parse(m).ok_or(AppError::on("INVALID_METHOD", "method"))?,
        };
        let price = |s: Option<&str>, field: &str| -> Result<Option<i64>, AppError> {
            match s.map(str::trim).filter(|t| !t.is_empty()) {
                None => Ok(None),
                Some(t) => Ok(Some(positive(ctx, t, field)?.minor())),
            }
        };
        let min_qty = match input
            .min_qty
            .as_deref()
            .map(str::trim)
            .filter(|t| !t.is_empty())
        {
            None => None,
            Some(t) => Some(parse_qty(t, f, "minQty")?),
        };
        let frozen_days = input.frozen_days.unwrap_or(DEFAULT_FROZEN_DAYS);
        if !(1..=3650).contains(&frozen_days) {
            return Err(AppError::on("INVALID_DAYS", "frozenDays"));
        }
        Ok(kk_stock::KkItemRow {
            id,
            name,
            unit: input.unit.clone(),
            method: method.as_str().to_string(),
            currency: ctx.currency.code().to_string(),
            sale_price_minor: price(input.sale_price.as_deref(), "salePrice")?,
            replacement_price_minor: price(input.replacement_price.as_deref(), "replacementPrice")?,
            min_qty,
            frozen_days: i64::from(frozen_days),
            note: clean_opt(input.note.as_deref()),
        })
    }

    pub fn kk_add_item(&self, space_id: &str, input: KkItemInput) -> Result<KkStockDto, AppError> {
        let ctx = self.ctx()?;
        let scope = self.kk_scope(&ctx, space_id)?;
        let row = self.kk_item_row(&ctx, self.new_id(), &input)?;
        let meta = self.meta();
        self.db
            .write(|tx| kk_stock::insert_item(tx, &scope, &row, &meta))?;
        self.publish(Some(space_id), &[Topic::Kasbkor]);
        self.kk_stock(space_id)
    }

    /// Birlik o'zgarmaydi; tannarx usuli — faqat harakat yo'q bo'lsa.
    pub fn kk_update_item(
        &self,
        space_id: &str,
        item_id: &str,
        input: KkItemInput,
    ) -> Result<KkStockDto, AppError> {
        let ctx = self.ctx()?;
        let scope = self.kk_scope(&ctx, space_id)?;
        let states = self.kk_stock_states(&ctx, &scope)?;
        let old = states
            .iter()
            .find(|s| s.item.id == item_id)
            .ok_or(AppError::on("NOT_FOUND", "itemId"))?;
        let row = self.kk_item_row(&ctx, item_id.to_string(), &input)?;
        if row.unit != old.item.unit {
            return Err(AppError::on("UNIT_LOCKED", "unit"));
        }
        if row.method != old.item.method && !old.costs.is_empty() {
            return Err(AppError::on("METHOD_LOCKED", "method"));
        }
        let meta = self.meta();
        self.db
            .write(|tx| kk_stock::update_item(tx, &scope, &row, &meta))?;
        self.publish(Some(space_id), &[Topic::Kasbkor]);
        self.kk_stock(space_id)
    }

    /// Faqat harakati yo'q tovar (adashib qo'shilgan) o'chiriladi.
    pub fn kk_delete_item(&self, space_id: &str, item_id: &str) -> Result<KkStockDto, AppError> {
        let ctx = self.ctx()?;
        let scope = self.kk_scope(&ctx, space_id)?;
        let state = self
            .kk_stock_states(&ctx, &scope)?
            .into_iter()
            .find(|s| s.item.id == item_id)
            .ok_or(AppError::on("NOT_FOUND", "itemId"))?;
        if !state.costs.is_empty() {
            return Err(AppError::on("ITEM_HAS_MOVES", "itemId"));
        }
        let meta = self.meta();
        self.db
            .write(|tx| kk_stock::delete_item(tx, &scope, item_id, &meta))?;
        self.publish(Some(space_id), &[Topic::Kasbkor]);
        self.kk_stock(space_id)
    }

    /// Xarid, sotuv, hisobdan chiqarish yoki inventarizatsiya. Harakat tovarning barcha harakatlari
    /// orasiga sana bo'yicha qo'yilib qayta o'ynaladi: keyingi biror chiqim qoldiqdan oshsa — rad etiladi.
    pub fn kk_stock_move(
        &self,
        space_id: &str,
        item_id: &str,
        input: KkStockMoveInput,
    ) -> Result<KkStockDto, AppError> {
        let ctx = self.ctx()?;
        let cur = ctx.currency;
        let scope = self.kk_scope(&ctx, space_id)?;
        let items = self.db.read(|c| kk_stock::items(c, &scope))?;
        let item = items
            .into_iter()
            .find(|i| i.id == item_id && i.currency == cur.code())
            .ok_or(AppError::on("NOT_FOUND", "itemId"))?;
        let f = factor(&item.unit)?;
        let on = self.date_or_today(&ctx, input.occurred_on.as_deref(), "occurredOn")?;
        let day = ymd(on);
        let all: Vec<_> = self
            .db
            .read(|c| kk_stock::moves(c, &scope))?
            .into_iter()
            .filter(|m| m.item_id == item_id)
            .collect();
        // Shu sanagacha (shu kun ham) bo'lgan holat — inventarizatsiya va qiymat uchun.
        let split = all.partition_point(|m| m.occurred_on <= day);
        let mut before = ItemState::new(item.clone(), cur)?;
        for m in all[..split].iter().cloned() {
            before.apply(m, cur)?;
        }
        let qty_in = || parse_qty(&input.qty, f, "qty");
        let reason = || required(input.reason.as_deref().unwrap_or_default(), "reason");
        let amount_opt = |field: &str| -> Result<Option<Money>, AppError> {
            match input
                .amount
                .as_deref()
                .map(str::trim)
                .filter(|t| !t.is_empty())
            {
                None => Ok(None),
                Some(t) => Ok(Some(positive(&ctx, t, field)?)),
            }
        };
        let w = input
            .wallet
            .as_deref()
            .map(|w| wallet(w, "wallet"))
            .transpose()?;
        let mut row = kk_stock::KkStockMoveRow {
            id: self.new_id(),
            item_id: item_id.to_string(),
            kind: String::new(),
            occurred_on: day.clone(),
            qty: 0,
            amount_minor: None,
            wallet: None,
            income_id: None,
            reason: None,
        };
        let positive_qty = |q: i64| {
            if q > 0 {
                Ok(q)
            } else {
                Err(AppError::on("INVALID_QTY", "qty"))
            }
        };
        let mut income = None;
        match input.kind.as_str() {
            "PURCHASE" => {
                row.kind = "PURCHASE".into();
                row.qty = positive_qty(qty_in()?)?;
                row.amount_minor = Some(
                    amount_opt("amount")?
                        .ok_or(AppError::on("REQUIRED", "amount"))?
                        .minor(),
                );
                row.wallet = w.map(|w| w.as_str().to_string());
            }
            "SALE" => {
                row.kind = "SALE".into();
                row.qty = positive_qty(qty_in()?)?;
                let w = w.ok_or(AppError::on("REQUIRED", "wallet"))?;
                let revenue = match amount_opt("amount")? {
                    Some(a) => a,
                    None => {
                        let p = item
                            .sale_price_minor
                            .map(|p| Money::new(p, cur))
                            .ok_or(AppError::on("REQUIRED", "amount"))?;
                        let v =
                            replacement(row.qty, Money::zero(cur), p, f, None)?.replacement_value;
                        if !v.is_positive() {
                            return Err(AppError::on("AMOUNT_NOT_POSITIVE", "amount"));
                        }
                        v
                    }
                };
                let inc = incomes::IncomeRow {
                    id: self.new_id(),
                    member_id: None,
                    amount_minor: revenue.minor(),
                    currency: cur.code().to_string(),
                    source: item.name.clone(),
                    channel: w.as_str().to_string(),
                    source_type: None,
                    occurred_on: day.clone(),
                    note: None,
                };
                row.amount_minor = Some(revenue.minor());
                row.wallet = Some(w.as_str().to_string());
                row.income_id = Some(inc.id.clone());
                income = Some(inc);
            }
            "WRITE_OFF" => {
                row.kind = "WRITE_OFF".into();
                row.qty = positive_qty(qty_in()?)?;
                row.reason = Some(reason()?);
            }
            "COUNT" => {
                row.kind = "ADJUST".into();
                let counted = qty_in()?;
                row.qty = counted
                    .checked_sub(before.stock.qty)
                    .ok_or(AppError::on("INVALID_QTY", "qty"))?;
                if row.qty == 0 {
                    return Err(AppError::on("NO_DIFFERENCE", "qty"));
                }
                if row.qty > 0 {
                    // Topilgan tovar: o'rtacha tannarxda, qoldiq bo'lmasa — qayta tiklash narxida.
                    let value = match amount_opt("amount")? {
                        Some(a) => a,
                        None => {
                            let p = before
                                .stock
                                .unit_cost(f)?
                                .or(before.price(cur))
                                .ok_or(AppError::on("REQUIRED", "amount"))?;
                            replacement(row.qty, Money::zero(cur), p, f, None)?.replacement_value
                        }
                    };
                    row.amount_minor = Some(value.minor());
                }
                row.reason = Some(reason()?);
            }
            _ => return Err(AppError::on("INVALID_KIND", "kind")),
        }
        self.kk_ensure_open(&scope, &day, "occurredOn")?;
        let touches_cash = row.wallet.as_deref() == Some("CASH");
        self.kk_ensure_cash_open(&scope, &day, touches_cash)?;
        // To'liq qayta o'ynash: yangi harakat o'z sanasidagi oxirgi o'rinda.
        let mut check = before;
        check.apply(row.clone(), cur)?;
        for m in all[split..].iter().cloned() {
            check.apply(m, cur)?;
        }
        let meta = self.meta();
        self.db.write(|tx| {
            if let Some(inc) = &income {
                incomes::insert(tx, &scope, inc, &meta)?;
            }
            kk_stock::insert_move(tx, &scope, &row, &meta)
        })?;
        let topics: &[Topic] = if income.is_some() {
            &[Topic::Incomes, Topic::Kasbkor]
        } else {
            &[Topic::Kasbkor]
        };
        self.publish(Some(space_id), topics);
        self.kk_stock(space_id)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn qty_text_roundtrip() {
        assert_eq!(parse_qty("1,5", 1000, "qty").unwrap(), 1500);
        assert_eq!(parse_qty("80", 1000, "qty").unwrap(), 80_000);
        assert_eq!(parse_qty("0.125", 1000, "qty").unwrap(), 125);
        assert_eq!(parse_qty("1 200", 1, "qty").unwrap(), 1200);
        assert!(parse_qty("1,5", 1, "qty").is_err());
        assert!(parse_qty("1,2345", 1000, "qty").is_err());
        assert!(parse_qty("-3", 1000, "qty").is_err());
        assert!(parse_qty("", 1000, "qty").is_err());
        assert_eq!(show_qty(1500, 1000), "1,5");
        assert_eq!(show_qty(-80_000, 1000), "-80");
        assert_eq!(show_qty(125, 1000), "0,125");
        assert_eq!(show_qty(7, 1), "7");
    }
}
