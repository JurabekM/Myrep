//! Birinchi ishga tushirish: xonadon, a'zo, standart kategoriyalar, "Kelajagim" va 5% qoidasi.
use domain::{
    AllocationKind, AllocationRule, Asset, AssetType, Category, Household, Member, MemberRole,
    Meta, MoneyOwner, Necessity, VaultType,
};
use money::Currency;
use storage::{repo, Database};

use crate::{Ctx, Env, ServiceError};

/// Standart kategoriya: nom, standart toifa (oila o'zgartira oladi), «Kimning puli?» egasi, sadaqa belgisi.
pub struct DefaultCategory {
    pub name: &'static str,
    pub necessity: Necessity,
    pub owner: Option<MoneyOwner>,
    pub is_charity: bool,
}

const fn dc(
    name: &'static str,
    necessity: Necessity,
    owner: Option<MoneyOwner>,
    is_charity: bool,
) -> DefaultCategory {
    DefaultCategory {
        name,
        necessity,
        owner,
        is_charity,
    }
}

pub const DEFAULT_CATEGORIES: [DefaultCategory; 13] = [
    dc("Oziq-ovqat", Necessity::Zarur, None, false),
    dc("Yo'lkira", Necessity::Zarur, None, false),
    dc("Benzin", Necessity::Zarur, Some(MoneyOwner::Fuel), false),
    dc("Kommunal", Necessity::Zarur, Some(MoneyOwner::State), false),
    dc("Telefon", Necessity::Kerak, None, false),
    dc("Gazak va ichimlik", Necessity::Havas, None, false),
    dc("Kiyim", Necessity::Kerak, None, false),
    dc("Bolalar", Necessity::Kerak, None, false),
    dc("Salomatlik", Necessity::Zarur, None, false),
    dc(
        "Nasiya to'lovi",
        Necessity::Zarur,
        Some(MoneyOwner::Shop),
        false,
    ),
    dc("Sadaqa", Necessity::Kerak, None, true),
    dc("Juma shirinligi", Necessity::Havas, None, false),
    dc("Boshqa", Necessity::Kerak, None, false),
];

pub const TREAT_CATEGORY: &str = "Juma shirinligi";

pub const NASIYA_CATEGORY: &str = "Nasiya to'lovi";

/// Xonadon bor bo'lsa uni qaytaradi, yo'q bo'lsa hammasini bitta tranzaksiyada yaratadi.
///
/// # Errors
/// Baza xatosi.
pub fn ensure_household(db: &mut Database, env: &Env<'_>) -> Result<Ctx, ServiceError> {
    if let Some(ctx) = find(db)? {
        ensure_defaults(db, env, &ctx)?;
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
        for d in &DEFAULT_CATEGORIES {
            repo::insert(
                tx,
                &Category {
                    meta: Meta::new(env.ids, env.clock, &hid, env.device_id),
                    name: d.name.into(),
                    necessity: Some(d.necessity),
                    owner: d.owner,
                    is_charity: d.is_charity,
                    is_habit: false,
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
                vault_type: Some(VaultType::Qorovul),
            },
        )?;
        insert_growing(tx, env, &hid)?;
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

/// Eski bazalar (D4/D5) uchun: yetishmayotgan standart kategoriyalarni qo'shadi va toifasi hali
/// belgilanmagan standart kategoriyalarga standart toifani qo'yadi. Foydalanuvchi belgilagan
/// toifaga tegmaydi. Idempotent.
fn ensure_defaults(db: &mut Database, env: &Env<'_>, ctx: &Ctx) -> Result<(), ServiceError> {
    let existing = repo::list::<Category>(db.conn(), &ctx.household_id)?;
    let has_growing = repo::list::<Asset>(db.conn(), &ctx.household_id)?
        .iter()
        .any(|a| a.vault_type == Some(VaultType::Osadigan));
    db.transaction::<(), ServiceError>(|tx| {
        if !has_growing {
            insert_growing(tx, env, &ctx.household_id)?;
        }
        for d in &DEFAULT_CATEGORIES {
            match existing.iter().find(|c| c.name == d.name) {
                None => repo::insert(
                    tx,
                    &Category {
                        meta: Meta::new(env.ids, env.clock, &ctx.household_id, env.device_id),
                        name: d.name.into(),
                        necessity: Some(d.necessity),
                        owner: d.owner,
                        is_charity: d.is_charity,
                        is_habit: false,
                    },
                )?,
                Some(c) if c.necessity.is_none() || (d.is_charity && !c.is_charity) => {
                    let mut c = c.clone();
                    c.necessity.get_or_insert(d.necessity);
                    c.is_charity |= d.is_charity;
                    repo::update(tx, &c, env.clock.now())?;
                }
                Some(_) => {}
            }
        }
        Ok(())
    })
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

/// «O'sadigan» bo'lim (SPEC 2C.3): balansi 0 dan boshlanadi; darvoza ochilmaguncha unga pul tushmaydi.
fn insert_growing(
    conn: &storage::Connection,
    env: &Env<'_>,
    household_id: &str,
) -> Result<(), ServiceError> {
    repo::insert(
        conn,
        &Asset {
            meta: Meta::new(env.ids, env.clock, household_id, env.device_id),
            asset_type: AssetType::Vault,
            name: "O'sadigan pul".into(),
            quantity: 0,
            unit: "tiyin".into(),
            currency: Some(Currency::Uzs),
            acquired_at: env.clock.now(),
            vault_type: Some(VaultType::Osadigan),
        },
    )?;
    Ok(())
}
