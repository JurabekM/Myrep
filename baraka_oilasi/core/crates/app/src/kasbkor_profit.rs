//! K2 — Kasb-kor «Haqiqiy foydani bil» (`docs/kasbkor/SPEC.md` 3): o'z mehnati bahosi, uskunalar va
//! eskirish, oilaviy mehnat, buyurtma kalkulyatori.
//!
//! Hisob `domain-kasbkor::{equipment, profit, quote}` da (vektorlar `kk_depreciation`,
//! `kk_true_profit`, `kk_order_quote`); bu yerda kiritilgan matnni o'qish, saqlash va DTO.
use baraka_domain_common::month_period;
use baraka_domain_kasbkor::equipment::{Disposal, Equipment};
use baraka_domain_kasbkor::profit::{hours_value, FamilyLabor};
use baraka_domain_kasbkor::quote::{order_quote, QuoteInput};
use baraka_money::{parse_amount, Money};
use baraka_storage::repo::kk;
use baraka_storage::SpaceScope;
use chrono::{Datelike, NaiveDate};

use crate::app::Ctx;
use crate::events::Topic;
use crate::kasbkor::wallet;
use crate::receipt::ymd;
use crate::text::{clean_opt, required};
use crate::uy::positive;
use crate::*;

/// `80`, `2,5`, `2.25` → yuzdan birlarda (8000, 250, 225). Ko'pi bilan 2 kasr raqam.
fn parse_hundredths(s: &str, code: &str, field: &str) -> Result<i64, AppError> {
    let err = || AppError::on(code, field);
    let t = s.trim().replace(',', ".");
    let (int, frac) = t.split_once('.').unwrap_or((&t, ""));
    if int.is_empty()
        || int.len() > 9
        || frac.len() > 2
        || !(int.chars().chain(frac.chars())).all(|c| c.is_ascii_digit())
    {
        return Err(err());
    }
    let int: i64 = int.parse().map_err(|_| err())?;
    let frac: i64 = if frac.is_empty() {
        0
    } else {
        format!("{frac:0<2}").parse().map_err(|_| err())?
    };
    Ok(int * 100 + frac)
}

/// 250 → `2,5`; 8000 → `80`.
fn show_hundredths(h: i64) -> String {
    let (int, frac) = (h / 100, h % 100);
    match frac {
        0 => int.to_string(),
        f if f % 10 == 0 => format!("{int},{}", f / 10),
        f => format!("{int},{f:02}"),
    }
}

/// Bo'sh bo'lsa — 0; manfiy — xato.
fn amount_or_zero(ctx: &Ctx, s: Option<&str>, field: &str) -> Result<Money, AppError> {
    match s.map(str::trim).filter(|t| !t.is_empty()) {
        None => Ok(Money::zero(ctx.currency)),
        Some(t) => {
            let m = parse_amount(t, ctx.currency).map_err(|e| AppError::on(e.code(), field))?;
            if m.is_negative() {
                Err(AppError::on("AMOUNT_NEGATIVE", field))
            } else {
                Ok(m)
            }
        }
    }
}

fn amount_opt(ctx: &Ctx, s: Option<&str>, field: &str) -> Result<Option<Money>, AppError> {
    if s.map(str::trim).is_none_or(str::is_empty) {
        return Ok(None);
    }
    amount_or_zero(ctx, s, field).map(Some)
}

/// Ikki oy boshi orasidagi oylar soni.
fn months_between(a: NaiveDate, b: NaiveDate) -> i64 {
    (i64::from(b.year()) * 12 + i64::from(b.month0()))
        - (i64::from(a.year()) * 12 + i64::from(a.month0()))
}

fn date(s: &str) -> Result<NaiveDate, AppError> {
    NaiveDate::parse_from_str(s, "%Y-%m-%d").map_err(|_| AppError::new("CORRUPT_ROW"))
}

impl App {
    pub(crate) fn kk_save_settings(
        &self,
        ctx: &Ctx,
        scope: &SpaceScope,
        salary_minor: i64,
        labor_minor: i64,
    ) -> Result<(), AppError> {
        let id = self.new_id();
        let meta = self.meta();
        self.db.write(|tx| {
            kk::upsert_settings(
                tx,
                scope,
                &id,
                &kk::KkSettingsRow {
                    owner_salary_minor: salary_minor,
                    owner_labor_minor: labor_minor,
                    currency: ctx.currency.code().to_string(),
                },
                &meta,
            )
        })?;
        Ok(())
    }

    fn month_start(&self, ctx: &Ctx, d: NaiveDate) -> Result<NaiveDate, AppError> {
        Ok(month_period(d, ctx.month_start_day)
            .ok_or(AppError::new("INVALID_PERIOD"))?
            .0)
    }

    /// Uskunaning domen ko'rinishi va xarid oyi boshi.
    fn kk_equipment_model(
        &self,
        ctx: &Ctx,
        r: &kk::KkEquipmentRow,
    ) -> Result<(Equipment, NaiveDate), AppError> {
        let m = |minor: i64| Money::new(minor, ctx.currency);
        let acquired = self.month_start(ctx, date(&r.acquired_on)?)?;
        let disposal = match (r.disposed_on.as_deref(), r.disposal_proceeds_minor) {
            (Some(on), Some(p)) => {
                let k = months_between(acquired, self.month_start(ctx, date(on)?)?);
                Some(Disposal {
                    month: u32::try_from(k).map_err(|_| AppError::new("CORRUPT_ROW"))?,
                    proceeds: m(p),
                })
            }
            _ => None,
        };
        let e = Equipment {
            cost: m(r.cost_minor),
            salvage: m(r.salvage_minor),
            useful_months: u32::try_from(r.useful_months)
                .map_err(|_| AppError::new("CORRUPT_ROW"))?,
            disposal,
        };
        Ok((e, acquired))
    }

    /// `start` oyidagi jami eskirish va uskuna chiqib ketishi.
    pub(crate) fn kk_depreciation_in(
        &self,
        ctx: &Ctx,
        scope: &SpaceScope,
        start: NaiveDate,
    ) -> Result<(Money, Money), AppError> {
        let zero = Money::zero(ctx.currency);
        let (mut dep, mut disp) = (zero, zero);
        for r in self
            .db
            .read(|c| kk::equipment(c, scope))?
            .into_iter()
            .filter(|r| r.currency == ctx.currency.code())
        {
            let (e, acquired) = self.kk_equipment_model(ctx, &r)?;
            let Ok(k) = u32::try_from(months_between(acquired, start)) else {
                continue;
            };
            let month = e.month(k)?;
            dep = dep.checked_add(month.depreciation)?;
            disp = disp.checked_add(month.disposal)?;
        }
        Ok((dep, disp))
    }

    pub(crate) fn kk_family_rows(
        &self,
        ctx: &Ctx,
        scope: &SpaceScope,
        start: NaiveDate,
        end: NaiveDate,
    ) -> Result<Vec<(kk::KkFamilyLaborRow, FamilyLabor)>, AppError> {
        Ok(self
            .db
            .read(|c| kk::family_labor_between(c, scope, &ymd(start), &ymd(end)))?
            .into_iter()
            .filter(|r| r.currency == ctx.currency.code())
            .map(|r| {
                let f = FamilyLabor {
                    hours100: r.hours100,
                    hourly_rate: Money::new(r.hourly_rate_minor, ctx.currency),
                    paid: r.paid,
                };
                (r, f)
            })
            .collect())
    }

    /// O'z mehnati bahosi (SPEC 3.1, OQ-K5): egasi o'z ishini yollanma odamga topshirsa, oyiga qancha
    /// to'lardi. Bo'sh — kiritilmagan (0).
    pub fn kk_set_owner_labor(
        &self,
        space_id: &str,
        amount: String,
    ) -> Result<KkOverviewDto, AppError> {
        let ctx = self.ctx()?;
        let scope = self.kk_scope(&ctx, space_id)?;
        let labor = amount_or_zero(&ctx, Some(&amount), "amount")?;
        let salary = self
            .db
            .read(|c| kk::settings(c, &scope))?
            .map_or(0, |s| s.owner_salary_minor);
        self.kk_save_settings(&ctx, &scope, salary, labor.minor())?;
        self.publish(Some(space_id), &[Topic::Kasbkor]);
        self.kk_overview(space_id, None)
    }

    /// Uskunalar ro'yxati: shu oy eskirishi va balans qiymati bilan.
    pub fn kk_equipment(&self, space_id: &str) -> Result<Vec<KkEquipmentDto>, AppError> {
        let ctx = self.ctx()?;
        let scope = self.kk_scope(&ctx, space_id)?;
        let start = self.month_start(&ctx, self.today(&ctx))?;
        let d = |m: Money| self.money_dto(&ctx, m);
        let mut out = Vec::new();
        for r in self
            .db
            .read(|c| kk::equipment(c, &scope))?
            .into_iter()
            .filter(|r| r.currency == ctx.currency.code())
        {
            let (e, acquired) = self.kk_equipment_model(&ctx, &r)?;
            let k = months_between(acquired, start);
            let (month_depreciation, book_value, months_left) = match u32::try_from(k) {
                // Kelgusi oyda xarid qilingan: hali eskirmagan.
                Err(_) => (Money::zero(ctx.currency), e.cost, e.useful_months),
                Ok(k) => {
                    let mo = e.month(k)?;
                    (
                        mo.depreciation,
                        mo.book_value,
                        e.useful_months.saturating_sub(k.saturating_add(1)),
                    )
                }
            };
            let status = if r.disposed_on.is_some() {
                "DISPOSED"
            } else if months_left == 0 && k >= 0 {
                "DEPRECIATED"
            } else {
                "ACTIVE"
            };
            out.push(KkEquipmentDto {
                id: r.id,
                name: r.name,
                cost: d(e.cost),
                salvage: d(e.salvage),
                useful_months: e.useful_months,
                acquired_on: r.acquired_on,
                wallet: r.wallet,
                month_depreciation: d(month_depreciation),
                book_value: d(book_value),
                months_left: if status == "DISPOSED" { 0 } else { months_left },
                status: status.to_string(),
                disposed_on: r.disposed_on,
                disposal_proceeds: r
                    .disposal_proceeds_minor
                    .map(|p| d(Money::new(p, ctx.currency))),
            });
        }
        Ok(out)
    }

    /// Uskuna qo'shish (SPEC 3.3). Hamyon ko'rsatilsa — xarid shu hamyondan (pul oqimiga kirmaydi).
    pub fn kk_add_equipment(
        &self,
        space_id: &str,
        input: KkEquipmentInput,
    ) -> Result<Vec<KkEquipmentDto>, AppError> {
        let ctx = self.ctx()?;
        let scope = self.kk_scope(&ctx, space_id)?;
        let name = required(&input.name, "name")?;
        if name.chars().count() > 200 {
            return Err(AppError::on("TOO_LONG", "name"));
        }
        let cost = positive(&ctx, &input.cost, "cost")?;
        let salvage = amount_or_zero(&ctx, input.salvage.as_deref(), "salvage")?;
        Equipment {
            cost,
            salvage,
            useful_months: input.useful_months,
            disposal: None,
        }
        .validate()?;
        let w = input
            .wallet
            .as_deref()
            .map(|w| wallet(w, "wallet"))
            .transpose()?;
        let acquired = self.date_or_today(&ctx, input.acquired_on.as_deref(), "acquiredOn")?;
        let row = kk::KkEquipmentRow {
            id: self.new_id(),
            name,
            cost_minor: cost.minor(),
            salvage_minor: salvage.minor(),
            useful_months: i64::from(input.useful_months),
            currency: ctx.currency.code().to_string(),
            acquired_on: ymd(acquired),
            wallet: w.map(|w| w.as_str().to_string()),
            disposed_on: None,
            disposal_proceeds_minor: None,
            disposal_wallet: None,
        };
        let meta = self.meta();
        self.db
            .write(|tx| kk::insert_equipment(tx, &scope, &row, &meta))?;
        self.publish(Some(space_id), &[Topic::Kasbkor]);
        self.kk_equipment(space_id)
    }

    /// Uskuna sotildi (narx bilan) yoki yaroqsiz bo'ldi (narxsiz): qolgan balans bir martalik xarajat.
    pub fn kk_dispose_equipment(
        &self,
        space_id: &str,
        id: &str,
        input: KkDisposeInput,
    ) -> Result<Vec<KkEquipmentDto>, AppError> {
        let ctx = self.ctx()?;
        let scope = self.kk_scope(&ctx, space_id)?;
        let row = self
            .db
            .read(|c| kk::equipment(c, &scope))?
            .into_iter()
            .find(|r| r.id == id)
            .ok_or(AppError::on("NOT_FOUND", "id"))?;
        if row.disposed_on.is_some() {
            return Err(AppError::on("ALREADY_DISPOSED", "id"));
        }
        let proceeds = amount_or_zero(&ctx, input.proceeds.as_deref(), "proceeds")?;
        let w = if proceeds.is_positive() {
            Some(wallet(
                input
                    .wallet
                    .as_deref()
                    .ok_or(AppError::on("REQUIRED", "wallet"))?,
                "wallet",
            )?)
        } else {
            None
        };
        let on = self.date_or_today(&ctx, input.disposed_on.as_deref(), "disposedOn")?;
        if ymd(on) < row.acquired_on {
            return Err(AppError::on("BEFORE_ACQUIRED", "disposedOn"));
        }
        let meta = self.meta();
        self.db.write(|tx| {
            kk::dispose_equipment(
                tx,
                &scope,
                id,
                &ymd(on),
                proceeds.minor(),
                w.map(|w| w.as_str()),
                &meta,
            )
        })?;
        self.publish(Some(space_id), &[Topic::Kasbkor]);
        self.kk_equipment(space_id)
    }

    /// Xato kiritilgan uskunani o'chirish (sinxronlashda o'chirish ham uzatiladi).
    pub fn kk_delete_equipment(
        &self,
        space_id: &str,
        id: &str,
    ) -> Result<Vec<KkEquipmentDto>, AppError> {
        let ctx = self.ctx()?;
        let scope = self.kk_scope(&ctx, space_id)?;
        let meta = self.meta();
        self.db
            .write(|tx| kk::delete_equipment(tx, &scope, id, &meta))?;
        self.publish(Some(space_id), &[Topic::Kasbkor]);
        self.kk_equipment(space_id)
    }

    /// Shu oy (yoki `date` tushgan oy) oilaviy mehnati.
    pub fn kk_family_labor(
        &self,
        space_id: &str,
        date: Option<String>,
    ) -> Result<Vec<KkFamilyLaborDto>, AppError> {
        let ctx = self.ctx()?;
        let scope = self.kk_scope(&ctx, space_id)?;
        let day = self.date_or_today(&ctx, date.as_deref(), "date")?;
        let (start, end) =
            month_period(day, ctx.month_start_day).ok_or(AppError::new("INVALID_PERIOD"))?;
        let mut out = Vec::new();
        for (r, f) in self.kk_family_rows(&ctx, &scope, start, end)? {
            out.push(KkFamilyLaborDto {
                id: r.id,
                person: r.person,
                worked_on: r.worked_on,
                hours: show_hundredths(r.hours100),
                hourly_rate: self.money_dto(&ctx, f.hourly_rate),
                value: self.money_dto(&ctx, hours_value(f.hours100, f.hourly_rate)?),
                paid: r.paid,
                note: r.note,
            });
        }
        Ok(out)
    }

    /// Oilaviy mehnat yozuvi (SPEC 3.1): a'zo, soat, soat bahosi. To'langan bo'lsa — u chiqimda bor.
    pub fn kk_add_family_labor(
        &self,
        space_id: &str,
        input: KkFamilyLaborInput,
    ) -> Result<Vec<KkFamilyLaborDto>, AppError> {
        let ctx = self.ctx()?;
        let scope = self.kk_scope(&ctx, space_id)?;
        let person = required(&input.person, "person")?;
        if person.chars().count() > 100 {
            return Err(AppError::on("TOO_LONG", "person"));
        }
        let hours100 = parse_hundredths(&input.hours, "INVALID_HOURS", "hours")?;
        if hours100 == 0 {
            return Err(AppError::on("INVALID_HOURS", "hours"));
        }
        let rate = amount_or_zero(&ctx, Some(&input.hourly_rate), "hourlyRate")?;
        // Qiymat sig'ishini oldindan tekshirish.
        hours_value(hours100, rate)?;
        let on = self.date_or_today(&ctx, input.worked_on.as_deref(), "workedOn")?;
        let row = kk::KkFamilyLaborRow {
            id: self.new_id(),
            person,
            member_id: None,
            worked_on: ymd(on),
            hours100,
            hourly_rate_minor: rate.minor(),
            currency: ctx.currency.code().to_string(),
            paid: input.paid,
            note: clean_opt(input.note.as_deref()),
        };
        let meta = self.meta();
        self.db
            .write(|tx| kk::insert_family_labor(tx, &scope, &row, &meta))?;
        self.publish(Some(space_id), &[Topic::Kasbkor]);
        self.kk_family_labor(space_id, Some(row.worked_on))
    }

    pub fn kk_delete_family_labor(
        &self,
        space_id: &str,
        id: &str,
    ) -> Result<Vec<KkFamilyLaborDto>, AppError> {
        let ctx = self.ctx()?;
        let scope = self.kk_scope(&ctx, space_id)?;
        let meta = self.meta();
        self.db
            .write(|tx| kk::delete_family_labor(tx, &scope, id, &meta))?;
        self.publish(Some(space_id), &[Topic::Kasbkor]);
        self.kk_family_labor(space_id, None)
    }

    /// Buyurtma kalkulyatori (SPEC 3.2) — hech narsa saqlanmaydi.
    pub fn kk_order_quote(
        &self,
        space_id: &str,
        input: KkQuoteInput,
    ) -> Result<KkQuoteDto, AppError> {
        let ctx = self.ctx()?;
        self.kk_scope(&ctx, space_id)?;
        let hours100 = match input
            .hours
            .as_deref()
            .map(str::trim)
            .filter(|t| !t.is_empty())
        {
            None => 0,
            Some(h) => parse_hundredths(h, "INVALID_HOURS", "hours")?,
        };
        let reserve_bp = match input
            .reserve_percent
            .as_deref()
            .map(str::trim)
            .filter(|t| !t.is_empty())
        {
            None => 0,
            Some(p) => parse_hundredths(p, "INVALID_PERCENT", "reservePercent")?,
        };
        if reserve_bp > 10_000 {
            return Err(AppError::on("INVALID_PERCENT", "reservePercent"));
        }
        let q = order_quote(QuoteInput {
            material: amount_or_zero(&ctx, input.material.as_deref(), "material")?,
            hours100,
            hourly_rate: amount_or_zero(&ctx, input.hourly_rate.as_deref(), "hourlyRate")?,
            travel: amount_or_zero(&ctx, input.travel.as_deref(), "travel")?,
            depreciation: amount_or_zero(&ctx, input.depreciation.as_deref(), "depreciation")?,
            reserve_bp,
            price: amount_opt(&ctx, input.price.as_deref(), "price")?,
            advance: amount_opt(&ctx, input.advance.as_deref(), "advance")?,
        })?;
        let d = |m: Money| self.money_dto(&ctx, m);
        Ok(KkQuoteDto {
            labor: d(q.labor),
            subtotal: d(q.subtotal),
            reserve: d(q.reserve),
            cost: d(q.cost),
            margin: q.price.map(|p| d(p.margin)),
            labor_paid: q.price.map(|p| d(p.labor_paid)),
            below_cost: q.price.map(|p| p.below_cost),
            effective_hourly_rate: q.price.and_then(|p| p.effective_hourly_rate).map(d),
            material_shortfall: q.advance.map(|a| d(a.material_shortfall)),
            advance_after_material: q.advance.map(|a| d(a.advance_after_material)),
        })
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn hundredths_parse_and_show() {
        assert_eq!(parse_hundredths("80", "X", "h"), Ok(8000));
        assert_eq!(parse_hundredths(" 2,5 ", "X", "h"), Ok(250));
        assert_eq!(parse_hundredths("0.25", "X", "h"), Ok(25));
        for bad in ["", "2,555", "-1", "1,2,3", ",5", "abc", "1 000"] {
            assert!(parse_hundredths(bad, "X", "h").is_err(), "{bad}");
        }
        assert_eq!(show_hundredths(8000), "80");
        assert_eq!(show_hundredths(250), "2,5");
        assert_eq!(show_hundredths(225), "2,25");
        assert_eq!(show_hundredths(5), "0,05");
    }
}
