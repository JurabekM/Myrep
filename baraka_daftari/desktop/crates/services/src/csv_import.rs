//! CSV import (bank ko'chirmasi → xarajatlar): ommaviy kiritish uchun, bank integratsiyasi emas.
//! Fayl Rust tomonida o'qiladi; frontendga faqat ko'rik (dastlabki qatorlar) beriladi.
use domain::{Date, Expense, Meta, PaymentChannel};
use money::{parse_signed_amount, Money};
use storage::{repo, Connection, Database};

use crate::{expenses, local_date, Ctx, Env, ServiceError};

pub const MAX_BYTES: usize = 5 * 1024 * 1024;
pub const MAX_ROWS: usize = 20_000;
pub const PREVIEW_ROWS: usize = 20;

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Table {
    pub headers: Vec<String>,
    pub rows: Vec<Vec<String>>,
    pub delimiter: char,
}

/// Ajratgich: birinchi qatordagi eng ko'p uchragan (`,` `;` tab `|`); teng bo'lsa `;`... ro'yxat tartibida birinchisi.
fn detect_delimiter(first_line: &str) -> char {
    [',', ';', '\t', '|']
        .into_iter()
        .max_by_key(|d| (first_line.matches(*d).count(), std::cmp::Reverse(*d as u32)))
        .filter(|d| first_line.contains(*d))
        .unwrap_or(',')
}

/// UTF-8 (BOM bilan yoki BOM'siz) CSV'ni jadvalga aylantiradi. Birinchi qator — sarlavha.
///
/// # Errors
/// Fayl juda katta, UTF-8 emas, bo'sh yoki qatorlar soni chegaradan oshsa.
pub fn parse_table(bytes: &[u8]) -> Result<Table, ServiceError> {
    if bytes.len() > MAX_BYTES {
        return Err(ServiceError::Invalid("fayl juda katta (5 MB gacha)"));
    }
    let text = std::str::from_utf8(bytes)
        .map_err(|_| ServiceError::Invalid("fayl UTF-8 kodirovkasida bo'lishi kerak"))?;
    let text = text.strip_prefix('\u{feff}').unwrap_or(text);
    let first_line = text.lines().next().unwrap_or("");
    if first_line.trim().is_empty() {
        return Err(ServiceError::Invalid("fayl bo'sh"));
    }
    let delimiter = detect_delimiter(first_line);
    let mut reader = csv::ReaderBuilder::new()
        .delimiter(u8::try_from(u32::from(delimiter)).unwrap_or(b','))
        .has_headers(true)
        .flexible(true)
        .trim(csv::Trim::All)
        .from_reader(text.as_bytes());
    let headers: Vec<String> = reader
        .headers()
        .map_err(|_| ServiceError::Invalid("CSV sarlavhasini o'qib bo'lmadi"))?
        .iter()
        .map(str::to_owned)
        .collect();
    let mut rows = Vec::new();
    for rec in reader.records() {
        let rec = rec.map_err(|_| ServiceError::Invalid("CSV qatori noto'g'ri"))?;
        if rec.iter().all(str::is_empty) {
            continue;
        }
        if rows.len() >= MAX_ROWS {
            return Err(ServiceError::Invalid("qatorlar juda ko'p (20 000 gacha)"));
        }
        rows.push(rec.iter().map(str::to_owned).collect());
    }
    if headers.is_empty() || rows.is_empty() {
        return Err(ServiceError::Invalid("fayl'da ma'lumot qatorlari yo'q"));
    }
    Ok(Table {
        headers,
        rows,
        delimiter,
    })
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum DateFormat {
    /// `2026-10-07`
    Iso,
    /// `07.10.2026`
    DayMonthYearDots,
    /// `07/10/2026`
    DayMonthYearSlashes,
    /// `2026/10/07`
    YearMonthDaySlashes,
}

impl DateFormat {
    #[must_use]
    pub fn parse(s: &str) -> Option<Self> {
        match s {
            "ISO" => Some(Self::Iso),
            "DMY_DOTS" => Some(Self::DayMonthYearDots),
            "DMY_SLASHES" => Some(Self::DayMonthYearSlashes),
            "YMD_SLASHES" => Some(Self::YearMonthDaySlashes),
            _ => None,
        }
    }
}

/// Qaysi ishorali qatorlar xarajat hisoblanadi.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum SignRule {
    /// Bank ko'chirmasi: chiqim manfiy (`-150 000`), kirim musbat — kirimlar o'tkazib yuboriladi.
    NegativeAreExpenses,
    /// Chiqim musbat yozilgan ko'chirma: manfiylar (qaytarish) o'tkazib yuboriladi.
    PositiveAreExpenses,
    /// Ishoradan qat'i nazar modul.
    AbsoluteAll,
}

impl SignRule {
    #[must_use]
    pub fn parse(s: &str) -> Option<Self> {
        match s {
            "NEGATIVE_ARE_EXPENSES" => Some(Self::NegativeAreExpenses),
            "POSITIVE_ARE_EXPENSES" => Some(Self::PositiveAreExpenses),
            "ABSOLUTE_ALL" => Some(Self::AbsoluteAll),
            _ => None,
        }
    }
}

#[derive(Debug, Clone, Copy)]
pub struct Mapping {
    pub date_col: usize,
    pub amount_col: usize,
    pub note_col: Option<usize>,
    pub date_format: DateFormat,
    pub sign: SignRule,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ParsedRow {
    /// Fayldagi qator raqami (sarlavha = 1).
    pub line: usize,
    pub date: Date,
    pub amount: Money,
    pub note: Option<String>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct RowError {
    pub line: usize,
    pub reason: &'static str,
}

#[derive(Debug, Default, PartialEq, Eq)]
pub struct Parsed {
    pub rows: Vec<ParsedRow>,
    pub errors: Vec<RowError>,
    /// Ishora qoidasiga ko'ra xarajat emas (masalan, kirim).
    pub skipped_sign: usize,
}

fn parse_date(text: &str, f: DateFormat) -> Option<Date> {
    let sep = match f {
        DateFormat::Iso => '-',
        DateFormat::DayMonthYearDots => '.',
        DateFormat::DayMonthYearSlashes | DateFormat::YearMonthDaySlashes => '/',
    };
    let parts: Vec<&str> = text.trim().split(sep).collect();
    let [a, b, c] = parts.as_slice() else {
        return None;
    };
    let (y, m, d) = match f {
        DateFormat::Iso | DateFormat::YearMonthDaySlashes => (a, b, c),
        DateFormat::DayMonthYearDots | DateFormat::DayMonthYearSlashes => (c, b, a),
    };
    if y.len() != 4 || !(1..=2).contains(&m.len()) || !(1..=2).contains(&d.len()) {
        return None;
    }
    let month = time::Month::try_from(m.parse::<u8>().ok()?).ok()?;
    Date::from_calendar_date(y.parse().ok()?, month, d.parse().ok()?).ok()
}

/// Jadvalni xaritalash bo'yicha qatorlarga o'giradi. Xato qatorlar `errors` ga tushadi, qolganlari davom etadi.
#[must_use]
pub fn parse_rows(
    table: &Table,
    mapping: &Mapping,
    currency: money::Currency,
    today: Date,
) -> Parsed {
    let mut out = Parsed::default();
    for (i, row) in table.rows.iter().enumerate() {
        let line = i + 2;
        let cell = |col: usize| row.get(col).map(String::as_str);
        let Some(date) = cell(mapping.date_col).and_then(|t| parse_date(t, mapping.date_format))
        else {
            out.errors.push(RowError {
                line,
                reason: "sana noto'g'ri",
            });
            continue;
        };
        if date > today {
            out.errors.push(RowError {
                line,
                reason: "sana kelajakda",
            });
            continue;
        }
        let Some((negative, amount)) =
            cell(mapping.amount_col).and_then(|t| parse_signed_amount(t, currency).ok())
        else {
            out.errors.push(RowError {
                line,
                reason: "summa noto'g'ri",
            });
            continue;
        };
        let is_expense = match mapping.sign {
            SignRule::NegativeAreExpenses => negative,
            SignRule::PositiveAreExpenses => !negative,
            SignRule::AbsoluteAll => true,
        };
        if !is_expense {
            out.skipped_sign += 1;
            continue;
        }
        if amount.minor() == 0 {
            out.errors.push(RowError {
                line,
                reason: "summa nol",
            });
            continue;
        }
        let note = mapping
            .note_col
            .and_then(cell)
            .map(|t| t.trim().chars().take(120).collect::<String>())
            .filter(|t| !t.is_empty());
        out.rows.push(ParsedRow {
            line,
            date,
            amount,
            note,
        });
    }
    out
}

#[derive(Debug, Default, PartialEq, Eq)]
pub struct ImportOutcome {
    pub imported: usize,
    pub duplicates: usize,
    pub skipped_sign: usize,
    pub errors: Vec<RowError>,
}

fn already_imported(existing: &[Expense], row: &ParsedRow) -> bool {
    existing.iter().any(|e| {
        e.spent_on == row.date && e.amount == row.amount && e.note.as_deref() == row.note.as_deref()
    })
}

/// Qatorlarni xarajat sifatida yozadi. Kategoriya: izohdan (oldingi shunday izohli xarajat) yoki
/// `default_category_id`. Bir xil (sana, summa, izoh) yozuv bor bo'lsa — takror deb o'tkazib yuboriladi
/// (faylni ikki marta yuklash ikki marta yozmaydi). Hammasi bitta tranzaksiyada.
///
/// # Errors
/// Kategoriya topilmasa yoki baza xatosi.
pub fn import(
    db: &mut Database,
    env: &Env<'_>,
    ctx: &Ctx,
    parsed: Parsed,
    default_category_id: &str,
) -> Result<ImportOutcome, ServiceError> {
    if !crate::categories::list(db.conn(), ctx)?
        .iter()
        .any(|c| c.meta.id == default_category_id)
    {
        return Err(ServiceError::NotFound);
    }
    let today = local_date(env.clock.now());
    let mut existing = repo::list::<Expense>(db.conn(), &ctx.household_id)?;
    let mut outcome = ImportOutcome {
        skipped_sign: parsed.skipped_sign,
        errors: parsed.errors,
        ..ImportOutcome::default()
    };
    let mut fresh: Vec<Expense> = Vec::new();
    for row in parsed.rows {
        if row.date > today {
            outcome.errors.push(RowError {
                line: row.line,
                reason: "sana kelajakda",
            });
            continue;
        }
        if already_imported(&existing, &row) {
            outcome.duplicates += 1;
            continue;
        }
        let category_id = match &row.note {
            Some(n) => expenses::suggest_category(db.conn(), ctx, n)?,
            None => None,
        }
        .unwrap_or_else(|| default_category_id.to_owned());
        let e = Expense {
            meta: Meta::new(env.ids, env.clock, &ctx.household_id, env.device_id),
            member_id: ctx.member_id.clone(),
            category_id,
            amount: row.amount,
            spent_on: row.date,
            payment_channel: PaymentChannel::Card,
            necessity: None,
            envelope_id: None,
            is_gift: Some(false),
            is_ostentation: Some(false),
            funded_by_debt: Some(false),
            audit_month: None,
            note: row.note,
        };
        existing.push(e.clone());
        fresh.push(e);
    }
    outcome.imported = fresh.len();
    db.transaction::<(), ServiceError>(|tx| {
        for e in &fresh {
            repo::insert(tx, e)?;
        }
        Ok(())
    })?;
    Ok(outcome)
}

/// Ko'rik uchun dastlabki qatorlar.
#[must_use]
pub fn preview(table: &Table) -> Vec<Vec<String>> {
    table.rows.iter().take(PREVIEW_ROWS).cloned().collect()
}

/// Ishlatilmaydigan import ogohlantirishini oldini olish uchun (ulanish ma'lumoti).
#[allow(dead_code)]
fn _conn(_: &Connection) {}

#[cfg(test)]
mod tests {
    use money::Currency;
    use time::macros::date;

    use super::*;

    fn table(csv: &str) -> Table {
        parse_table(csv.as_bytes()).unwrap()
    }

    #[test]
    fn detects_delimiters_and_strips_bom() {
        let semi = table("\u{feff}Sana;Summa;Izoh\n07.10.2026;-15 000,50;Somsa\n");
        assert_eq!(
            (semi.delimiter, semi.headers.len(), semi.rows.len()),
            (';', 3, 1)
        );
        assert_eq!(semi.headers[0], "Sana");
        assert_eq!(table("a,b\n1,2\n").delimiter, ',');
        assert_eq!(table("a\tb\n1\t2\n").delimiter, '\t');
        assert_eq!(table("a|b\n1|2\n").delimiter, '|');
    }

    #[test]
    fn quoted_fields_with_delimiters_survive() {
        let t = table("Sana,Summa,Izoh\n2026-10-07,-100,\"non, somsa\"\n");
        assert_eq!(t.rows[0][2], "non, somsa");
    }

    #[test]
    fn rejects_bad_files() {
        assert!(parse_table(b"").is_err());
        assert!(parse_table(b"\n\n").is_err());
        assert!(
            parse_table(b"Sana;Summa\n").is_err(),
            "ma'lumot qatori yo'q"
        );
        assert!(parse_table(&[0xff, 0xfe, 0x00]).is_err(), "UTF-8 emas");
        assert!(parse_table(&vec![b'a'; MAX_BYTES + 1]).is_err());
        let mut big = String::from("a,b\n");
        for _ in 0..=MAX_ROWS {
            big.push_str("1,2\n");
        }
        assert!(parse_table(big.as_bytes()).is_err());
    }

    #[test]
    fn blank_rows_are_skipped_and_short_rows_tolerated() {
        let t = table("Sana,Summa,Izoh\n\n2026-10-07,-5\n,,\n");
        assert_eq!(t.rows.len(), 1);
        assert_eq!(t.rows[0].len(), 2);
    }

    #[test]
    fn dates_in_all_formats_and_rejects_nonsense() {
        assert_eq!(
            parse_date("2026-10-07", DateFormat::Iso),
            Some(date!(2026 - 10 - 07))
        );
        assert_eq!(
            parse_date("07.10.2026", DateFormat::DayMonthYearDots),
            Some(date!(2026 - 10 - 07))
        );
        assert_eq!(
            parse_date("7/10/2026", DateFormat::DayMonthYearSlashes),
            Some(date!(2026 - 10 - 07))
        );
        assert_eq!(
            parse_date("2026/10/07", DateFormat::YearMonthDaySlashes),
            Some(date!(2026 - 10 - 07))
        );
        for (t, f) in [
            ("31.02.2026", DateFormat::DayMonthYearDots),
            ("2026-13-01", DateFormat::Iso),
            ("07.10.26", DateFormat::DayMonthYearDots),
            ("07-10-2026", DateFormat::DayMonthYearDots),
            ("", DateFormat::Iso),
            ("2026-10", DateFormat::Iso),
        ] {
            assert_eq!(parse_date(t, f), None, "{t}");
        }
    }

    fn mapping(sign: SignRule) -> Mapping {
        Mapping {
            date_col: 0,
            amount_col: 1,
            note_col: Some(2),
            date_format: DateFormat::DayMonthYearDots,
            sign,
        }
    }

    #[test]
    fn rows_follow_sign_rule_and_collect_errors_without_aborting() {
        let t = table(
            "Sana;Summa;Izoh\n\
             07.10.2026;-15 000,50;Somsa\n\
             06.10.2026;+8 000 000;Oylik\n\
             05.10.2026;abc;Xato\n\
             99.10.2026;-1;Sana\n\
             08.10.2026;-5;Kelajak\n\
             04.10.2026;-0;Nol\n\
             03.10.2026;-200;\n",
        );
        let today = date!(2026 - 10 - 07);
        let p = parse_rows(
            &t,
            &mapping(SignRule::NegativeAreExpenses),
            Currency::Uzs,
            today,
        );
        assert_eq!(p.rows.len(), 2);
        assert_eq!(
            (
                p.rows[0].line,
                p.rows[0].amount.minor(),
                p.rows[0].note.as_deref()
            ),
            (2, 1_500_050, Some("Somsa"))
        );
        assert_eq!(
            (p.rows[1].amount.minor(), p.rows[1].note.clone()),
            (20_000, None)
        );
        assert_eq!(
            p.skipped_sign, 2,
            "kirim va «-0» (manfiy emas) o'tkazib yuboriladi"
        );
        let reasons: Vec<_> = p.errors.iter().map(|e| (e.line, e.reason)).collect();
        assert_eq!(
            reasons,
            [
                (4, "summa noto'g'ri"),
                (5, "sana noto'g'ri"),
                (6, "sana kelajakda")
            ]
        );

        let pos = parse_rows(
            &t,
            &mapping(SignRule::PositiveAreExpenses),
            Currency::Uzs,
            today,
        );
        assert_eq!(pos.rows.len(), 1, "faqat kirim (+) xarajat deb olinadi");
        assert!(pos.errors.iter().any(|e| e.reason == "summa nol"));
        let all = parse_rows(&t, &mapping(SignRule::AbsoluteAll), Currency::Uzs, today);
        assert_eq!(all.rows.len(), 3);
    }

    #[test]
    fn missing_columns_are_row_errors_not_panics() {
        let t = table("a,b\n1,2\n");
        let m = Mapping {
            date_col: 5,
            amount_col: 6,
            note_col: Some(9),
            date_format: DateFormat::Iso,
            sign: SignRule::AbsoluteAll,
        };
        let p = parse_rows(&t, &m, Currency::Uzs, date!(2026 - 10 - 07));
        assert_eq!((p.rows.len(), p.errors.len()), (0, 1));
    }

    #[test]
    fn long_notes_are_truncated() {
        let long = "x".repeat(300);
        let t = table(&format!("d,a,n\n2026-10-07,-5,{long}\n"));
        let m = Mapping {
            date_col: 0,
            amount_col: 1,
            note_col: Some(2),
            date_format: DateFormat::Iso,
            sign: SignRule::NegativeAreExpenses,
        };
        let p = parse_rows(&t, &m, Currency::Uzs, date!(2026 - 10 - 07));
        assert_eq!(
            p.rows[0].note.as_ref().map(|n| n.chars().count()),
            Some(120)
        );
    }
}
