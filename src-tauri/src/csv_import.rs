//! CSV import ustasi (DESKTOP_PROMPT 7-bo'lim): bank ko'chirmasi yoki jadvaldan joylangan matn → xarajatlar.
//!
//! Bu ommaviy kiritish, bank integratsiyasi emas. Matn ilova ichida qoladi, tarmoqqa chiqmaydi.
//! Qoidalar:
//! * ajratuvchi avtomatik (`;`, `,`, tab) yoki tanlangan; qo'shtirnoqli maydonlar qo'llanadi;
//! * summa `money::parse_amount` bilan (manfiy belgi — chiqim; musbat satrlar `skip_positive` bilan tashlanadi);
//! * sana `YYYY-MM-DD`, `DD.MM.YYYY` yoki `DD/MM/YYYY`; bugundan kech yoki 24 oydan eski — xato;
//! * oldin to'liq ko'rib chiqiladi (`preview`), keyin hammasi bitta tranzaksiyada yoziladi (`import`).

use domain::calendar::month_of;
use domain::{DomainError, Expense, ExpenseDraft, Necessity, TaskTrigger};
use money::Money;
use storage::{CategoryRepo, Database, ExpenseRepo, StorageError};
use time::format_description::well_known::Iso8601;
use time::{Date, OffsetDateTime};

use crate::content;
use crate::dto::{CsvMappingDto, CsvPreviewDto, CsvRowDto, MoneyDto};
use crate::finance::{self, Context, DEVICE_ID, MAX_MONTHS_BACK, UuidV7, date_text, parse_money};
use crate::session::SessionError;

/// Bir importda maksimal satrlar soni.
pub const MAX_ROWS: usize = 500;

/// Satr tahlili natijasi (import uchun tayyor qism).
struct ParsedRow {
    occurred_on: Date,
    amount: Money,
    note: Option<String>,
}

/// Ajratuvchini aniqlaydi: birinchi satrda eng ko'p uchragan belgi (`;`, `,`, tab).
fn detect_delimiter(text: &str) -> char {
    let first = text
        .lines()
        .find(|line| !line.trim().is_empty())
        .unwrap_or("");
    let candidates = [';', ',', '\t'];
    candidates
        .into_iter()
        .max_by_key(|candidate| first.matches(*candidate).count())
        .filter(|candidate| first.contains(*candidate))
        .unwrap_or(';')
}

/// Bitta satrni maydonlarga ajratadi (qo'shtirnoq ichidagi ajratuvchi hisobga olinmaydi, `""` — bitta `"`).
pub fn split_fields(line: &str, delimiter: char) -> Vec<String> {
    let mut fields = Vec::new();
    let mut current = String::new();
    let mut in_quotes = false;
    let mut chars = line.chars().peekable();
    while let Some(character) = chars.next() {
        if character == '"' {
            if in_quotes && chars.peek() == Some(&'"') {
                current.push('"');
                chars.next();
            } else {
                in_quotes = !in_quotes;
            }
        } else if character == delimiter && !in_quotes {
            fields.push(current.trim().to_owned());
            current.clear();
        } else {
            current.push(character);
        }
    }
    fields.push(current.trim().to_owned());
    fields
}

/// Sana: `YYYY-MM-DD`, `DD.MM.YYYY` yoki `DD/MM/YYYY`.
pub fn parse_csv_date(text: &str) -> Option<Date> {
    let text = text.trim();
    if let Ok(date) = Date::parse(text, &Iso8601::DATE) {
        return Some(date);
    }
    let separator = if text.contains('.') { '.' } else { '/' };
    let mut parts = text.split(separator);
    let day: u8 = parts.next()?.trim().parse().ok()?;
    let month: u8 = parts.next()?.trim().parse().ok()?;
    let year: i32 = parts.next()?.trim().parse().ok()?;
    if parts.next().is_some() {
        return None;
    }
    Date::from_calendar_date(year, time::Month::try_from(month).ok()?, day).ok()
}

/// Eng eski ruxsat etilgan sana: joriy davrdan 24 oy orqaga.
fn earliest_allowed(ctx: &Context) -> Result<Date, SessionError> {
    let mut start = month_of(ctx.today, ctx.household.month_start_day)
        .ok_or(DomainError::InvalidDay)?
        .start;
    for _ in 0..MAX_MONTHS_BACK {
        start = month_of(
            start - time::Duration::days(1),
            ctx.household.month_start_day,
        )
        .ok_or(DomainError::InvalidDay)?
        .start;
    }
    Ok(start)
}

fn column(fields: &[String], index: u32) -> Option<&str> {
    fields.get(usize::try_from(index).ok()?).map(String::as_str)
}

/// Matnni satrma-satr tahlil qiladi: har satr uchun yo tayyor yozuv, yo xato kodi.
fn parse_rows(
    ctx: &Context,
    text: &str,
    mapping: &CsvMappingDto,
) -> Result<(Vec<ParsedRow>, Vec<CsvRowDto>), SessionError> {
    let delimiter = mapping
        .delimiter
        .as_deref()
        .and_then(|value| value.chars().next())
        .unwrap_or_else(|| detect_delimiter(text));
    let earliest = earliest_allowed(ctx)?;
    let mut parsed = Vec::new();
    let mut preview = Vec::new();
    let mut seen = 0_usize;
    for (index, line) in text.lines().enumerate() {
        if line.trim().is_empty() || (mapping.has_header && index == 0) {
            continue;
        }
        seen += 1;
        if seen > MAX_ROWS {
            return Err(DomainError::InvalidRule.into());
        }
        let line_no = u32::try_from(index + 1).unwrap_or(u32::MAX);
        let fields = split_fields(line, delimiter);
        let date_text_raw = column(&fields, mapping.date_column).unwrap_or("");
        let amount_text = column(&fields, mapping.amount_column).unwrap_or("");
        let note = mapping
            .note_column
            .and_then(|note_column| column(&fields, note_column))
            .filter(|value| !value.is_empty())
            .map(str::to_owned);

        let mut row = CsvRowDto {
            line: line_no,
            date: date_text_raw.to_owned(),
            amount: None,
            note: note.clone(),
            error: None,
            skipped: false,
        };

        let Some(occurred_on) = parse_csv_date(date_text_raw) else {
            row.error = Some("CSV_BAD_DATE".to_owned());
            preview.push(row);
            continue;
        };
        if occurred_on > ctx.today || occurred_on < earliest {
            row.error = Some("CSV_DATE_OUT_OF_RANGE".to_owned());
            preview.push(row);
            continue;
        }
        let Ok(amount) = parse_money(amount_text) else {
            row.error = Some("CSV_BAD_AMOUNT".to_owned());
            preview.push(row);
            continue;
        };
        if amount.minor() == 0 {
            row.error = Some("CSV_BAD_AMOUNT".to_owned());
            preview.push(row);
            continue;
        }
        if amount.minor() > 0 && mapping.skip_positive {
            row.amount = Some(MoneyDto::of(amount));
            row.skipped = true;
            preview.push(row);
            continue;
        }
        let expense_amount = Money::new(amount.minor().abs(), amount.currency());
        row.date = date_text(occurred_on);
        row.amount = Some(MoneyDto::of(expense_amount));
        preview.push(row);
        parsed.push(ParsedRow {
            occurred_on,
            amount: expense_amount,
            note,
        });
    }
    Ok((parsed, preview))
}

/// Ko'rib chiqish: nima import bo'ladi, nima tashlanadi, qaysi satrda xato.
pub fn preview(
    db: &Database,
    now: OffsetDateTime,
    text: &str,
    mapping: &CsvMappingDto,
) -> Result<CsvPreviewDto, SessionError> {
    let ctx = finance::context(db, now)?;
    let (parsed, rows) = parse_rows(&ctx, text, mapping)?;
    let skipped = rows.iter().filter(|row| row.skipped).count();
    let failed = rows.iter().filter(|row| row.error.is_some()).count();
    Ok(CsvPreviewDto {
        rows,
        importable: u32::try_from(parsed.len()).unwrap_or(u32::MAX),
        skipped: u32::try_from(skipped).unwrap_or(u32::MAX),
        failed: u32::try_from(failed).unwrap_or(u32::MAX),
    })
}

/// Import: xatoli satr bo'lsa hech narsa yozilmaydi (`CSV_HAS_ERRORS`); hammasi bitta tranzaksiyada.
pub fn import(
    db: &Database,
    now: OffsetDateTime,
    text: &str,
    mapping: &CsvMappingDto,
) -> Result<u32, SessionError> {
    let ctx = finance::context(db, now)?;
    let (parsed, rows) = parse_rows(&ctx, text, mapping)?;
    if rows.iter().any(|row| row.error.is_some()) {
        return Err(DomainError::CsvHasErrors.into());
    }
    if parsed.is_empty() {
        return Ok(0);
    }
    let categories = CategoryRepo::new(db.connection()).list(&ctx.household.id)?;
    let necessity = match mapping.category_id.as_deref() {
        Some(id) => categories
            .iter()
            .find(|category| category.id == id)
            .map(|category| category.necessity)
            .ok_or(StorageError::NotFound)?,
        None => Necessity::Kerak,
    };
    let mut expenses = Vec::with_capacity(parsed.len());
    for row in &parsed {
        expenses.push(Expense::create(
            &domain::IdGen::next_id(&UuidV7),
            &ctx.household.id,
            ExpenseDraft {
                member_id: ctx.owner_id.clone(),
                category_id: mapping.category_id.clone(),
                amount: row.amount,
                occurred_on: row.occurred_on,
                note: row.note.clone(),
                necessity,
                is_gift: false,
                is_ostentation: false,
                funded_by_debt: false,
            },
            now,
            DEVICE_ID,
        )?);
    }
    let tx = db
        .connection()
        .unchecked_transaction()
        .map_err(StorageError::from)?;
    {
        let repo = ExpenseRepo::new(&tx);
        for expense in &expenses {
            repo.insert(expense)?;
        }
    }
    tx.commit().map_err(StorageError::from)?;
    content::record_event(db, now, TaskTrigger::ExpenseRecorded)?;
    Ok(u32::try_from(expenses.len()).unwrap_or(u32::MAX))
}

#[cfg(test)]
mod tests {
    use super::*;
    use security::SecretKey;
    use time::macros::datetime;

    const NOW: OffsetDateTime = datetime!(2026-10-15 06:00 UTC);

    fn database() -> Database {
        Database::open_in_memory(&SecretKey::from_array([21; 32])).expect("xotirada baza")
    }

    fn mapping() -> CsvMappingDto {
        CsvMappingDto {
            delimiter: None,
            has_header: true,
            date_column: 0,
            amount_column: 1,
            note_column: Some(2),
            category_id: None,
            skip_positive: true,
        }
    }

    #[test]
    fn maydonlar_qoshtirnoq_bilan_ajratiladi() {
        assert_eq!(
            split_fields("\"Bozor; non\";-15 000;\"a \"\"b\"\"\"", ';'),
            vec!["Bozor; non", "-15 000", "a \"b\""]
        );
    }

    #[test]
    fn sana_uch_formatda_oqiladi() {
        let expected = Date::from_calendar_date(2026, time::Month::October, 3).expect("sana");
        assert_eq!(parse_csv_date("2026-10-03"), Some(expected));
        assert_eq!(parse_csv_date("03.10.2026"), Some(expected));
        assert_eq!(parse_csv_date("03/10/2026"), Some(expected));
        assert_eq!(parse_csv_date("2026/10/03/1"), None);
    }

    #[test]
    fn korib_chiqish_xato_va_tashlangan_satrlarni_ajratadi() {
        let db = database();
        let text = "Sana;Summa;Izoh\n10.10.2026;-15 000;Non\n11.10.2026;250 000;Maosh\n2026-13-01;-5;Xato\n12.10.2026;-0;Nol\n";
        let result = preview(&db, NOW, text, &mapping()).expect("ko'rib chiqish");
        assert_eq!(result.importable, 1);
        assert_eq!(result.skipped, 1);
        assert_eq!(result.failed, 2);
        assert_eq!(result.rows[0].date, "2026-10-10");
        assert_eq!(
            result.rows[0].amount.as_ref().map(|m| m.minor.as_str()),
            Some("1500000")
        );
        assert_eq!(result.rows[2].error.as_deref(), Some("CSV_BAD_DATE"));
        assert_eq!(result.rows[3].error.as_deref(), Some("CSV_BAD_AMOUNT"));
    }

    #[test]
    fn xatoli_matn_import_qilinmaydi_togrisi_bitta_tranzaksiyada_yoziladi() {
        let db = database();
        let bad = "10.10.2026;-15 000\nxato;-5\n";
        let mut no_header = mapping();
        no_header.has_header = false;
        no_header.note_column = None;
        assert!(matches!(
            import(&db, NOW, bad, &no_header),
            Err(SessionError::Domain(DomainError::CsvHasErrors))
        ));
        let good = "10.10.2026;-15 000\n2026-09-30;-7 500\n";
        assert_eq!(import(&db, NOW, good, &no_header).expect("import"), 2);
        let summary = crate::family::month_summary(&db, NOW).expect("xulosa");
        // Ikkala satr ham KERAK: bitta oktabrda (15 000), ikkinchisi sentabrda (joriy oyga kirmaydi).
        assert_eq!(summary.kerak.minor, "1500000");
    }

    #[test]
    fn bugundan_kech_va_juda_eski_sana_rad_etiladi() {
        let db = database();
        let text = "16.10.2026;-1 000\n01.01.2020;-1 000\n";
        let mut no_header = mapping();
        no_header.has_header = false;
        let result = preview(&db, NOW, text, &no_header).expect("ko'rib chiqish");
        assert!(
            result
                .rows
                .iter()
                .all(|row| row.error.as_deref() == Some("CSV_DATE_OUT_OF_RANGE"))
        );
    }
}
