//! Byudjet rejimi: `STANDARD` va `DEBT_RECOVERY` (70/20/10) — SPEC 2D.1.
//! Barcha qarzlar yopilganda rejim avtomatik `STANDARD` ga qaytadi va bo'shagan 20% ni
//! qorovul/o'sadigan pulga yo'naltirish taklif qilinadi (UI).
use domain::{recovery_split, BudgetMode, RecoverySplit, SplitAmounts};
use money::Money;
use storage::Connection;
use storage::Database;

use crate::{
    debts,
    learning::{put_setting, setting},
    Ctx, Env, ServiceError,
};

const KEY_MODE: &str = "budget.mode";
const KEY_SPLIT: &str = "budget.split";
const KEY_NOTICE: &str = "budget.reverted_notice";

/// # Errors
/// Baza xatosi.
pub fn mode(conn: &Connection, ctx: &Ctx) -> Result<BudgetMode, ServiceError> {
    Ok(setting(conn, ctx, KEY_MODE)?
        .and_then(|s| BudgetMode::parse(&s.value))
        .unwrap_or(BudgetMode::Standard))
}

/// Saqlangan taqsimot (yo'q yoki buzilgan bo'lsa 70/20/10).
///
/// # Errors
/// Baza xatosi.
pub fn split(conn: &Connection, ctx: &Ctx) -> Result<RecoverySplit, ServiceError> {
    let parsed = setting(conn, ctx, KEY_SPLIT)?.and_then(|s| {
        let mut it = s.value.split('/').map(|p| p.parse::<u32>().ok());
        let (l, e, sv) = (it.next()??, it.next()??, it.next()??);
        RecoverySplit {
            living_bp: l,
            extra_bp: e,
            savings_bp: sv,
        }
        .validate()
        .ok()
    });
    Ok(parsed.unwrap_or(RecoverySplit::DEFAULT))
}

#[derive(Debug, Clone)]
pub struct Status {
    pub mode: BudgetMode,
    pub split: RecoverySplit,
    /// Faol qarz bor, lekin rejim hali `STANDARD`: ilova `DEBT_RECOVERY` ni taklif qiladi.
    pub suggest_recovery: bool,
    /// Qarzlar yopilgani uchun rejim avtomatik qaytgan (bir marta ko'rsatiladi).
    pub reverted_notice: bool,
    /// Oylik daromadning taqsimoti (daromad ma'lum bo'lsa).
    pub amounts: Option<SplitAmounts>,
}

/// Rejim holati. Faol qarz qolmagan bo'lsa rejimni avtomatik `STANDARD` ga qaytaradi.
///
/// # Errors
/// Baza xatosi.
pub fn status(db: &mut Database, env: &Env<'_>, ctx: &Ctx) -> Result<Status, ServiceError> {
    sync(db, env, ctx)?;
    let m = mode(db.conn(), ctx)?;
    let sp = split(db.conn(), ctx)?;
    let active = debts::overview(db.conn(), env, ctx)?.active_count;
    let amounts = match debts::reference_income(db.conn(), env, ctx)? {
        Some(inc) => Some(recovery_split(inc, sp)?),
        None => None,
    };
    Ok(Status {
        mode: m,
        split: sp,
        suggest_recovery: active > 0 && m == BudgetMode::Standard,
        reverted_notice: setting(db.conn(), ctx, KEY_NOTICE)?.is_some_and(|s| s.value == "1"),
        amounts,
    })
}

/// Bildirishnomani «ko'rildi» deb belgilaydi.
///
/// # Errors
/// Baza xatosi.
pub fn dismiss_notice(db: &mut Database, env: &Env<'_>, ctx: &Ctx) -> Result<(), ServiceError> {
    put_setting(db.conn(), env, ctx, KEY_NOTICE, "0")
}

/// Faol qarz qolmasa rejim `STANDARD` ga qaytadi. Qaytganda `true`.
///
/// # Errors
/// Baza xatosi.
pub fn sync(db: &mut Database, env: &Env<'_>, ctx: &Ctx) -> Result<bool, ServiceError> {
    if mode(db.conn(), ctx)? == BudgetMode::DebtRecovery
        && debts::overview(db.conn(), env, ctx)?.active_count == 0
    {
        db.transaction::<(), ServiceError>(|tx| {
            put_setting(tx, env, ctx, KEY_MODE, BudgetMode::Standard.as_str())?;
            put_setting(tx, env, ctx, KEY_NOTICE, "1")
        })?;
        return Ok(true);
    }
    Ok(false)
}

/// # Errors
/// `DEBT_RECOVERY` ni faol qarzsiz yoqib bo'lmaydi.
pub fn set_mode(
    db: &mut Database,
    env: &Env<'_>,
    ctx: &Ctx,
    new: BudgetMode,
) -> Result<(), ServiceError> {
    if new == BudgetMode::DebtRecovery && debts::overview(db.conn(), env, ctx)?.active_count == 0 {
        return Err(ServiceError::Invalid(
            "«Qarzdan chiqish» rejimi uchun faol qarz kerak",
        ));
    }
    db.transaction::<(), ServiceError>(|tx| {
        put_setting(tx, env, ctx, KEY_MODE, new.as_str())?;
        put_setting(tx, env, ctx, KEY_NOTICE, "0")
    })
}

/// # Errors
/// Yig'indi 100% emas yoki jamg'arma ulushi 1% dan kam bo'lsa.
pub fn set_split(
    db: &mut Database,
    env: &Env<'_>,
    ctx: &Ctx,
    new: RecoverySplit,
) -> Result<(), ServiceError> {
    let s = new.validate().map_err(|e| match e {
        domain::PlanError::SavingsTooLow => {
            ServiceError::Invalid("jamg'arma ulushi kamida 1% bo'lishi kerak")
        }
        _ => ServiceError::Invalid("ulushlar yig'indisi 100% bo'lishi kerak"),
    })?;
    put_setting(
        db.conn(),
        env,
        ctx,
        KEY_SPLIT,
        &format!("{}/{}/{}", s.living_bp, s.extra_bp, s.savings_bp),
    )
}

/// `DEBT_RECOVERY` rejimida daromaddan «Kelajagim»ga ajratiladigan ulush (jamg'arma ulushi, kamida 1%).
///
/// # Errors
/// Baza xatosi.
pub(crate) fn savings_share(
    conn: &Connection,
    ctx: &Ctx,
    amount: Money,
) -> Result<Option<Money>, ServiceError> {
    if mode(conn, ctx)? != BudgetMode::DebtRecovery {
        return Ok(None);
    }
    Ok(Some(recovery_split(amount, split(conn, ctx)?)?.savings))
}
