//! Birinchi ishga tushirish: xonadon, a'zo, standart kategoriyalar, "Kelajagim" va 5% qoidasi.
use domain::{
    AllocationKind, AllocationRule, Asset, AssetType, Category, Household, Member, MemberRole,
    Meta, MoneyOwner,
};
use money::Currency;
use storage::{repo, Database};

use crate::{Ctx, Env, ServiceError};

/// Standart kategoriyalar: (nom, "Kimning puli?" egasi). Toifa (`Necessity`) D6 da qo'yiladi.
pub const DEFAULT_CATEGORIES: [(&str, Option<MoneyOwner>); 11] = [
    ("Oziq-ovqat", None),
    ("Yo'lkira", None),
    ("Benzin", Some(MoneyOwner::Fuel)),
    ("Kommunal", Some(MoneyOwner::State)),
    ("Telefon", None),
    ("Gazak va ichimlik", None),
    ("Kiyim", None),
    ("Bolalar", None),
    ("Salomatlik", None),
    ("Nasiya to'lovi", Some(MoneyOwner::Shop)),
    ("Boshqa", None),
];

pub const NASIYA_CATEGORY: &str = "Nasiya to'lovi";

/// Xonadon bor bo'lsa uni qaytaradi, yo'q bo'lsa hammasini bitta tranzaksiyada yaratadi.
///
/// # Errors
/// Baza xatosi.
pub fn ensure_household(db: &mut Database, env: &Env<'_>) -> Result<Ctx, ServiceError> {
    if let Some(ctx) = find(db)? {
        return Ok(ctx);
    }
    db.transaction::<(), ServiceError>(|tx| {
        let mut hm = Meta::new(env.ids, env.clock, "", env.device_id);
        hm.household_id.clone_from(&hm.id);
        let hid = hm.id.clone();
        repo::insert(
            tx,
            &Household {
                meta: hm,
                name: "Oila".into(),
                base_currency: Currency::Uzs,
            },
        )?;
        let member = Member {
            meta: Meta::new(env.ids, env.clock, &hid, env.device_id),
            display_name: "Men".into(),
            role: MemberRole::Adult,
        };
        repo::insert(tx, &member)?;
        for (name, owner) in DEFAULT_CATEGORIES {
            repo::insert(
                tx,
                &Category {
                    meta: Meta::new(env.ids, env.clock, &hid, env.device_id),
                    name: name.into(),
                    necessity: None,
                    owner,
                },
            )?;
        }
        repo::insert(
            tx,
            &Asset {
                meta: Meta::new(env.ids, env.clock, &hid, env.device_id),
                asset_type: AssetType::Vault,
                name: "Kelajagim".into(),
                quantity: 0,
                unit: "tiyin".into(),
                currency: Some(Currency::Uzs),
                acquired_at: env.clock.now(),
            },
        )?;
        repo::insert(
            tx,
            &AllocationRule {
                meta: Meta::new(env.ids, env.clock, &hid, env.device_id),
                kind: AllocationKind::Percent,
                value: i64::from(domain::START_BP),
                currency: None,
            },
        )?;
        Ok(())
    })?;
    find(db)?.ok_or(ServiceError::NotFound)
}

fn find(db: &Database) -> Result<Option<Ctx>, ServiceError> {
    let Some(h) = repo::list_all::<Household>(db.conn())?.into_iter().next() else {
        return Ok(None);
    };
    let member = repo::list::<Member>(db.conn(), &h.meta.id)?
        .into_iter()
        .next()
        .ok_or(ServiceError::NotFound)?;
    Ok(Some(Ctx {
        household_id: h.meta.id,
        member_id: member.meta.id,
        currency: h.base_currency,
    }))
}
