//! Oila kengashi (SPEC 2B.3 / DESKTOP 7): oyni ko'rib chiqish → toifalar → havas chegarasi → bayonnoma.
use domain::{Category, Household, MemberRole, Necessity, NecessityChange};
use money::{format_money, Locale, Money};
use pdf::{CouncilMinutes, MinutesCategory, MinutesConsent};
use storage::{repo, Connection};

use crate::{audit, categories, havas, local_date, members, Ctx, Env, ServiceError, YearMonth};

const LOCALE: Locale = Locale::Uz;

fn fmt(m: Money) -> String {
    format_money(m, LOCALE)
}

const fn necessity_label(n: Option<Necessity>) -> &'static str {
    match n {
        Some(Necessity::Zarur) => "Zarur",
        Some(Necessity::Kerak) => "Kerak",
        Some(Necessity::Havas) => "Havas",
        None => "belgilanmagan",
    }
}

const fn role_label(r: MemberRole) -> &'static str {
    match r {
        MemberRole::Adult => "Katta",
        MemberRole::Child => "Bola",
        MemberRole::Viewer => "Kuzatuvchi",
    }
}

fn last_change(
    conn: &Connection,
    ctx: &Ctx,
    history: &[NecessityChange],
    category_id: &str,
) -> Result<Option<String>, ServiceError> {
    let Some(h) = history.iter().rev().find(|h| h.category_id == category_id) else {
        return Ok(None);
    };
    let who = members::list(conn, ctx)?
        .into_iter()
        .find(|m| m.meta.id == h.changed_by)
        .map_or_else(|| "?".to_owned(), |m| m.display_name);
    let on = domain::date_to_string(local_date(h.meta.created_at)).unwrap_or_default();
    Ok(Some(format!("{who}, {on}")))
}

/// Bayonnoma ma'lumotlari (formatlangan matn). `ym` — ko'rib chiqilgan oy.
///
/// # Errors
/// Baza xatosi.
pub fn minutes_data(
    conn: &Connection,
    env: &Env<'_>,
    ctx: &Ctx,
    ym: YearMonth,
) -> Result<CouncilMinutes, ServiceError> {
    let overview = audit::overview(conn, ctx, ym)?;
    let report = havas::report(conn, ctx, ym)?;
    let household = repo::list_all::<Household>(conn)?
        .into_iter()
        .find(|h| h.meta.id == ctx.household_id)
        .map_or_else(|| "Oila".to_owned(), |h| h.name);
    let all_members = members::list(conn, ctx)?;
    let adults = members::adults(conn, ctx)?;
    let history = categories::history(conn, ctx, None)?;

    let mut review = vec![
        ("Daromad".to_owned(), fmt(overview.income)),
        ("Majburiyatlar".to_owned(), fmt(overview.obligations)),
        ("Xarajatlar".to_owned(), fmt(overview.expenses)),
        ("«Kelajagim»ga ajratilgan".to_owned(), fmt(overview.savings)),
        ("Oy yakuni".to_owned(), fmt(overview.month_result)),
        ("Izohsiz qolgan".to_owned(), fmt(overview.unexplained)),
        ("Havas sarfi".to_owned(), fmt(report.spent)),
    ];
    if report.debt_funded.minor() > 0 {
        review.push((
            "shundan qarz bilan qilingan".to_owned(),
            fmt(report.debt_funded),
        ));
    }
    if report.gifts_excluded.minor() > 0 {
        review.push((
            "Sovg'alar (havas hisobiga kirmaydi)".to_owned(),
            fmt(report.gifts_excluded),
        ));
    }
    if report.ostentation.minor() > 0 {
        review.push(("Obro' uchun xarajatlar".to_owned(), fmt(report.ostentation)));
    }
    if report.charity.minor() > 0 {
        review.push(("Sadaqa (isrof emas)".to_owned(), fmt(report.charity)));
    }

    let categories = repo::list::<Category>(conn, &ctx.household_id)?
        .into_iter()
        .map(|c| {
            Ok(MinutesCategory {
                necessity: necessity_label(c.necessity).to_owned(),
                last_change: last_change(conn, ctx, &history, &c.meta.id)?,
                name: c.name,
            })
        })
        .collect::<Result<Vec<_>, ServiceError>>()?;

    let (limit_amount, limit_status, consents) = if let Some(limit) = report.limit {
        let consent_rows = consent_rows(conn, ctx, &adults, None)?;
        (
            Some(fmt(limit)),
            "Faol: barcha kattalar rozi".to_owned(),
            consent_rows,
        )
    } else if let Some(p) = &report.pending {
        let names: Vec<&str> = p.missing.iter().map(|m| m.display_name.as_str()).collect();
        (
            Some(fmt(p.amount)),
            format!("Kuchga kirmagan: rozilik bermagan — {}", names.join(", ")),
            consent_rows(conn, ctx, &adults, Some(&p.limit_id))?,
        )
    } else {
        (None, "Belgilanmagan".to_owned(), Vec::new())
    };

    Ok(CouncilMinutes {
        household,
        date: domain::date_to_string(local_date(env.clock.now())).unwrap_or_default(),
        month: ym.text(),
        attendees: all_members
            .iter()
            .map(|m| (m.display_name.clone(), role_label(m.role).to_owned()))
            .collect(),
        review,
        categories,
        limit_amount,
        limit_status,
        consents,
        signers: adults.iter().map(|m| m.display_name.clone()).collect(),
        disclaimer: "Ta'limiy material. Fatvo yoki moliyaviy maslahat emas.".to_owned(),
    })
}

/// Rozilik jadvali: `limit_id = None` — faol chegara (eng so'nggi to'liq kelishilgan).
fn consent_rows(
    conn: &Connection,
    ctx: &Ctx,
    adults: &[domain::Member],
    limit_id: Option<&str>,
) -> Result<Vec<MinutesConsent>, ServiceError> {
    let id = match limit_id {
        Some(id) => id.to_owned(),
        None => match havas::effective_and_pending(conn, ctx)?.0 {
            Some(l) => l.meta.id,
            None => return Ok(Vec::new()),
        },
    };
    let consents = repo::list::<domain::LimitConsent>(conn, &ctx.household_id)?;
    Ok(adults
        .iter()
        .map(|a| MinutesConsent {
            name: a.display_name.clone(),
            at: consents
                .iter()
                .find(|c| c.limit_id == id && c.member_id == a.meta.id)
                .and_then(|c| domain::date_to_string(local_date(c.consented_at)).ok()),
        })
        .collect())
}

/// Bayonnomani PDF baytlari sifatida qaytaradi.
///
/// # Errors
/// Baza yoki PDF xatosi.
pub fn minutes_pdf(
    conn: &Connection,
    env: &Env<'_>,
    ctx: &Ctx,
    ym: YearMonth,
) -> Result<Vec<u8>, ServiceError> {
    let data = minutes_data(conn, env, ctx, ym)?;
    pdf::council_minutes(&data)
        .map_err(|_| ServiceError::Invalid("bayonnoma PDF'ini yaratib bo'lmadi"))
}
