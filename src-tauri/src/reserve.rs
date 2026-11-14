//! D8 xizmati: «Qorovul» zaxirasi — maqsad (3 va 6 oy), necha oylik zaxira bor, tayyorgarlik darvozasi,
//! «Narx daftari» va shaxsiy inflyatsiya, «Inflyatsiya ta'siri». Hisob domen'da; bu yerda faqat yig'iladi.

use domain::calendar::month_of;
use domain::emergency::{AVERAGE_MONTHS, emergency_target};
use domain::inflation::{PriceDraft, PriceItem, personal_index, real_value, units_affordable};
use domain::readiness::readiness_gate;
use domain::{DomainError, Necessity};
use money::{Money, round_half_up_div};
use storage::{Database, ExpenseRepo, PriceRepo, StorageError};
use time::{Duration, OffsetDateTime};

use crate::dto::{MoneyDto, PriceItemDto, PriceItemInputDto, PricesDto, ReserveDto};
use crate::finance::{self, CURRENCY, Context, DEVICE_ID, UuidV7, parse_money};
use crate::session::SessionError;

/// To'liq maqsad: 6 oy (SPEC 2C.3).
const FULL_TARGET_MONTHS: i64 = 6;
/// Birinchi bosqich: 3 oy.
const FIRST_TARGET_MONTHS: i64 = 3;
/// O'rtacha uchun qaraladigan o'tgan oylar (joriy oy kirmaydi — u to'liq emas).
const LOOKBACK_MONTHS: usize = 12;

/// O'tgan oylarning `ZARUR + KERAK` jami, eng eskidan yangigacha (joriy oy kirmaydi).
pub(crate) fn monthly_essentials(db: &Database, ctx: &Context) -> Result<Vec<Money>, SessionError> {
    let repo = ExpenseRepo::new(db.connection());
    let mut period =
        month_of(ctx.today, ctx.household.month_start_day).ok_or(DomainError::InvalidDay)?;
    let mut months = Vec::with_capacity(LOOKBACK_MONTHS);
    for _ in 0..LOOKBACK_MONTHS {
        period = month_of(
            period.start - Duration::days(1),
            ctx.household.month_start_day,
        )
        .ok_or(DomainError::InvalidDay)?;
        let expenses = repo.list_in_range(&ctx.household.id, period)?;
        let minor = expenses
            .iter()
            .filter(|e| matches!(e.necessity, Necessity::Zarur | Necessity::Kerak))
            .fold(0_i64, |acc, e| acc.saturating_add(e.amount.minor()));
        months.push(Money::new(minor, CURRENCY));
    }
    months.reverse();
    Ok(months)
}

/// Zaxira holati: maqsadlar, oylik o'rtacha, necha oylik zaxira (o'ndan bir), darvoza.
/// Foizli qarz va chiqish rejasi — D9 gacha «yo'q» deb olinadi (MVP_PLAN: stub).
pub fn reserve(db: &Database, now: OffsetDateTime) -> Result<ReserveDto, SessionError> {
    let ctx = finance::context(db, now)?;
    let months = monthly_essentials(db, &ctx)?;
    let balance = finance::vault_balance(db, now)?;
    let target_full = emergency_target(CURRENCY, &months, FULL_TARGET_MONTHS)?;
    let target_first = emergency_target(CURRENCY, &months, FIRST_TARGET_MONTHS)?;
    // Oylik o'rtacha = 3 oylik maqsad / 3 (xuddi shu uchta ma'lumotli oy bo'yicha).
    let monthly_average = target_first
        .map(|target| -> Result<Money, DomainError> {
            let avg = round_half_up_div(i128::from(target.minor()), AVERAGE_MONTHS as i128)?;
            Ok(Money::new(i64::try_from(avg).unwrap_or(i64::MAX), CURRENCY))
        })
        .transpose()?;
    let reserve_tenths = monthly_average
        .filter(|avg| avg.minor() > 0)
        .map(|avg| -> Result<i64, DomainError> {
            let tenths =
                round_half_up_div(i128::from(balance.minor()) * 10, i128::from(avg.minor()))?;
            Ok(i64::try_from(tenths).unwrap_or(i64::MAX))
        })
        .transpose()?;
    let gate = readiness_gate(reserve_tenths.unwrap_or(0), false, false);
    Ok(ReserveDto {
        balance: MoneyDto::of(balance),
        monthly_average: monthly_average.map(MoneyDto::of),
        target_first: target_first.map(MoneyDto::of),
        target_full: target_full.map(MoneyDto::of),
        reserve_months_tenths: reserve_tenths.and_then(|t| u32::try_from(t).ok()),
        target_months: u32::try_from(FULL_TARGET_MONTHS).unwrap_or(6),
        gate: gate.state.code().to_owned(),
        reasons: gate.reasons.iter().map(|r| r.code().to_owned()).collect(),
        data_months: u32::try_from(months.iter().filter(|m| m.minor() > 0).count()).unwrap_or(0),
    })
}

fn item_dto(item: &PriceItem, change_bp: Option<i64>) -> PriceItemDto {
    PriceItemDto {
        id: item.id.clone(),
        name: item.name.clone(),
        base_price: MoneyDto::of(item.base_price),
        current_price: MoneyDto::of(item.current_price),
        weight_bp: u32::try_from(item.weight_bp).unwrap_or(0),
        change_bp: change_bp.and_then(|bp| i32::try_from(bp).ok()),
    }
}

/// «Narx daftari»: yozuvlar, shaxsiy indeks, «Inflyatsiya ta'siri» (balansning real qiymati va misol).
pub fn prices(db: &Database, now: OffsetDateTime) -> Result<PricesDto, SessionError> {
    let ctx = finance::context(db, now)?;
    let items = PriceRepo::new(db.connection()).list(&ctx.household.id)?;
    let balance = finance::vault_balance(db, now)?;
    let weighted = items.iter().filter(|i| i.weight_bp > 0).count();
    let index = if weighted == 0 {
        None
    } else {
        let changes: Vec<_> = items.iter().map(PriceItem::change).collect();
        Some(personal_index(&changes)?)
    };
    let item_dtos = items
        .iter()
        .enumerate()
        .map(|(position, item)| {
            let bp = index
                .as_ref()
                .and_then(|idx| idx.item_bps.get(position).copied());
            item_dto(item, bp)
        })
        .collect();
    let index_bp = index.as_ref().map(|idx| idx.index_bp);
    let real = index_bp.map(|bp| real_value(balance, bp)).transpose()?;
    // Misol: birinchi yozuv bo'yicha bazaviy va joriy narxda nechta birlik.
    let example = items.first().map(|item| -> Result<_, DomainError> {
        Ok((
            item.name.clone(),
            units_affordable(balance, item.base_price)?,
            units_affordable(balance, item.current_price)?,
        ))
    });
    let example = example.transpose()?;
    Ok(PricesDto {
        items: item_dtos,
        index_bp: index_bp.and_then(|bp| i32::try_from(bp).ok()),
        balance: MoneyDto::of(balance),
        real_value: real.map(MoneyDto::of),
        example_name: example.as_ref().map(|(name, _, _)| name.clone()),
        example_units_before: example
            .as_ref()
            .map(|(_, before, _)| u32::try_from(*before).unwrap_or(u32::MAX)),
        example_units_now: example
            .as_ref()
            .map(|(_, _, now)| u32::try_from(*now).unwrap_or(u32::MAX)),
    })
}

/// Yozuv qo'shadi.
pub fn add_price_item(
    db: &Database,
    now: OffsetDateTime,
    input: PriceItemInputDto,
) -> Result<PricesDto, SessionError> {
    let ctx = finance::context(db, now)?;
    let item = PriceItem::create(
        &domain::IdGen::next_id(&UuidV7),
        &ctx.household.id,
        PriceDraft {
            name: input.name,
            base_price: parse_money(&input.base_price)?,
            current_price: parse_money(&input.current_price)?,
            weight_bp: i64::from(input.weight_bp),
        },
        now,
        DEVICE_ID,
    )?;
    PriceRepo::new(db.connection()).insert(&item)?;
    prices(db, now)
}

/// Joriy narxni yangilaydi.
pub fn update_price(
    db: &Database,
    now: OffsetDateTime,
    id: &str,
    current_price: &str,
) -> Result<PricesDto, SessionError> {
    let repo = PriceRepo::new(db.connection());
    let item = repo
        .find(id)?
        .ok_or_else(|| SessionError::from(StorageError::NotFound))?
        .with_current_price(parse_money(current_price)?, now)?;
    repo.update_current(&item)?;
    prices(db, now)
}

/// Yozuvni o'chiradi (mantiqiy).
pub fn remove_price_item(
    db: &Database,
    now: OffsetDateTime,
    id: &str,
) -> Result<PricesDto, SessionError> {
    PriceRepo::new(db.connection()).delete(id, now)?;
    prices(db, now)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::dto::PriceItemInputDto;
    use security::SecretKey;
    use time::macros::datetime;

    const NOW: OffsetDateTime = datetime!(2026-10-15 06:00 UTC);

    fn database() -> Database {
        Database::open_in_memory(&SecretKey::from_array([31; 32])).expect("xotirada baza")
    }

    #[test]
    fn malumotsiz_xonadonda_maqsad_yoq_darvoza_yopiq() {
        let db = database();
        let view = reserve(&db, NOW).expect("zaxira");
        assert_eq!(view.target_full, None);
        assert_eq!(view.reserve_months_tenths, None);
        assert_eq!(view.gate, "LOCKED");
        assert_eq!(view.reasons, vec!["RESERVE_BELOW_TARGET".to_owned()]);
    }

    #[test]
    fn narx_daftari_indeks_va_real_qiymat() {
        let db = database();
        let view = add_price_item(
            &db,
            NOW,
            PriceItemInputDto {
                name: "go'sht, 1 kg".to_owned(),
                base_price: "80 000".to_owned(),
                current_price: "130 000".to_owned(),
                weight_bp: 5_000,
            },
        )
        .expect("qo'shildi");
        assert_eq!(view.items[0].change_bp, Some(6_250));
        assert_eq!(view.index_bp, Some(6_250));
        assert_eq!(view.example_name.as_deref(), Some("go'sht, 1 kg"));
        let id = view.items[0].id.clone();
        let updated = update_price(&db, NOW, &id, "160 000").expect("yangilandi");
        assert_eq!(updated.items[0].change_bp, Some(10_000));
        let removed = remove_price_item(&db, NOW, &id).expect("o'chirildi");
        assert!(removed.items.is_empty());
        assert_eq!(removed.index_bp, None);
    }
}
