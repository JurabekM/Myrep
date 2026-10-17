//! Oila kengashi bayonnomasi ma'lumoti (DESKTOP_PROMPT.md 7-bo'lim): hisob backend'da, PDF `baraka-pdf` da.
//!
//! Matnlar tayyor (o'zbekcha, formatlangan) holda beriladi; bu yerda faqat ma'lumot yig'iladi.

use domain::Necessity;
use storage::CategoryRepo;
use storage::Database;
use time::Date;
use time::OffsetDateTime;
use time::format_description::well_known::Iso8601;

use crate::dto::HavasLimitDto;
use crate::family;
use crate::finance;
use crate::session::SessionError;

/// Bayonnoma sarlavhasi.
const TITLE: &str = "Oila kengashi bayonnomasi";
/// Ta'limiy material belgisi (SPEC 3, DESKTOP_PROMPT.md 8).
const DISCLAIMER: &str = "Taʼlimiy material. Fatvo yoki moliyaviy maslahat emas.";

/// Bayonnoma ma'lumotini yig'adi (joriy oy).
pub fn council_report(
    db: &Database,
    now: OffsetDateTime,
) -> Result<pdf::CouncilReport, SessionError> {
    let summary = family::month_summary(db, now)?;
    let limit = family::havas_limit(db, now)?;
    let ctx = finance::context(db, now)?;
    let categories = CategoryRepo::new(db.connection()).list(&ctx.household.id)?;
    let end = Date::parse(&summary.period_end, &Iso8601::DATE)
        .ok()
        .and_then(Date::previous_day)
        .map_or_else(|| summary.period_end.clone(), dotted);
    Ok(pdf::CouncilReport {
        title: TITLE.to_owned(),
        period: format!("{} — {}", dotted_text(&summary.period_start), end),
        generated_on: dotted_text(&summary.today),
        summary: vec![
            ("Zarur".to_owned(), summary.zarur.formatted.clone()),
            ("Kerak".to_owned(), summary.kerak.formatted.clone()),
            (
                "Havas (sovg'a va sadaqasiz)".to_owned(),
                summary.havas.formatted.clone(),
            ),
            (
                "Sadaqa (havas hisobiga kirmaydi)".to_owned(),
                summary.sadaqa.formatted.clone(),
            ),
            (
                "Sovg'alar (hisobga kirmaydi)".to_owned(),
                summary.gifts.formatted.clone(),
            ),
        ],
        categories: categories
            .iter()
            .map(|c| (c.name.clone(), necessity_label(c.necessity).to_owned()))
            .collect(),
        limit_status: limit_status(&limit),
        adults: limit
            .adults
            .iter()
            .map(|a| {
                let state = if a.consented {
                    "rozi"
                } else {
                    "hali rozi emas"
                };
                (a.name.clone(), state.to_owned())
            })
            .collect(),
        disclaimer: DISCLAIMER.to_owned(),
    })
}

/// Bayonnomani PDF baytlariga aylantiradi.
pub fn council_pdf(db: &Database, now: OffsetDateTime) -> Result<Vec<u8>, SessionError> {
    let report = council_report(db, now)?;
    Ok(pdf::render_council_report(&report)?)
}

fn necessity_label(necessity: Necessity) -> &'static str {
    match necessity {
        Necessity::Zarur => "Zarur",
        Necessity::Kerak => "Kerak",
        Necessity::Havas => "Havas",
    }
}

fn limit_status(limit: &HavasLimitDto) -> String {
    match (&limit.limit, limit.active) {
        (None, _) => "Chegara o'rnatilmagan.".to_owned(),
        (Some(monthly), true) => format!(
            "Chegara faol: {}. Shu oy sarfi: {}.",
            monthly.formatted, limit.spent.formatted
        ),
        (Some(monthly), false) => format!(
            "Chegara faol emas: barcha kattalar rozi bo'lishi kerak. Chegara: {}.",
            monthly.formatted
        ),
    }
}

/// `YYYY-MM-DD` → `DD.MM.YYYY`; noto'g'ri shakl bo'lsa — matn o'zgarishsiz.
fn dotted_text(iso: &str) -> String {
    Date::parse(iso, &Iso8601::DATE).map_or_else(|_| iso.to_owned(), dotted)
}

fn dotted(date: Date) -> String {
    format!(
        "{:02}.{:02}.{}",
        date.day(),
        u8::from(date.month()),
        date.year()
    )
}

#[cfg(test)]
mod tests {
    #![allow(clippy::expect_used, clippy::unwrap_used)]

    use security::SecretKey;
    use time::macros::datetime;

    use super::*;

    fn database() -> Database {
        Database::open_in_memory(&SecretKey::from_array([9; 32])).expect("xotirada baza")
    }

    #[test]
    fn bayonnoma_ma_lumoti_yigiladi() {
        let db = database();
        let now = datetime!(2026-10-15 06:00 UTC);
        let report = council_report(&db, now).expect("bayonnoma");
        assert_eq!(report.title, TITLE);
        assert_eq!(report.generated_on, "15.10.2026");
        assert_eq!(report.period, "01.10.2026 — 31.10.2026");
        assert_eq!(report.summary.len(), 5);
        assert!(!report.categories.is_empty(), "standart kategoriyalar bor");
        assert_eq!(report.limit_status, "Chegara o'rnatilmagan.");
        assert_eq!(report.disclaimer, DISCLAIMER);
    }

    #[test]
    fn bayonnoma_pdf_baytlari_qaytadi() {
        let db = database();
        let bytes = council_pdf(&db, datetime!(2026-10-15 06:00 UTC)).expect("pdf");
        assert!(bytes.starts_with(b"%PDF-"));
    }
}
