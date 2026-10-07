//! Oila kengashi bayonnomasi (D6). Ma'lumotlar tayyor formatlangan matn sifatida keladi:
//! pul va sana formatlash `money`/`services` da, bu yerda faqat sahifa tuzilmasi.
//!
//! Foydalanuvchi matnlari (ism, kategoriya nomi) typst markup'iga **string literal** sifatida
//! qo'yiladi (`#"..."`), shuning uchun ularda `#`, `$`, `*`, `_` kabi belgilar markup bo'lib ketmaydi.

use crate::{render_pdf, PdfError};

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct MinutesCategory {
    pub name: String,
    /// «Zarur» / «Kerak» / «Havas» yoki «belgilanmagan».
    pub necessity: String,
    /// Oxirgi o'zgarish: «Dilshod, 2026-10-07».
    pub last_change: Option<String>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct MinutesConsent {
    pub name: String,
    /// Rozilik sanasi; `None` — hali rozi bo'lmagan.
    pub at: Option<String>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CouncilMinutes {
    pub household: String,
    /// Kengash sanasi (`YYYY-MM-DD`).
    pub date: String,
    /// Ko'rib chiqilgan oy (`YYYY-MM`).
    pub month: String,
    /// (ism, rol)
    pub attendees: Vec<(String, String)>,
    /// (ko'rsatkich, qiymat)
    pub review: Vec<(String, String)>,
    pub categories: Vec<MinutesCategory>,
    /// Havas chegarasi summasi (taklif qilingan yoki faol), formatlangan.
    pub limit_amount: Option<String>,
    /// «Faol» yoki «Kuchga kirmagan: ... rozilik bermagan».
    pub limit_status: String,
    pub consents: Vec<MinutesConsent>,
    /// Imzo qatorlari uchun kattalar ismlari.
    pub signers: Vec<String>,
    pub disclaimer: String,
}

/// typst string literal: `\` va `"` ekranlanadi, boshqaruv belgilari olib tashlanadi.
fn lit(s: &str) -> String {
    let mut out = String::with_capacity(s.len() + 2);
    out.push('"');
    for c in s.chars() {
        match c {
            '\\' => out.push_str("\\\\"),
            '"' => out.push_str("\\\""),
            '\n' | '\r' | '\t' => out.push(' '),
            c if c.is_control() => {}
            c => out.push(c),
        }
    }
    out.push('"');
    out
}

fn text(s: &str) -> String {
    format!("[#{}]", lit(s))
}

fn table(rows: &[Vec<String>], columns: &str) -> String {
    let cells: Vec<String> = rows.iter().flatten().map(|c| text(c)).collect();
    format!(
        "#table(columns: {columns}, stroke: 0.4pt + luma(160), inset: 5pt,\n  {}\n)\n",
        cells.join(",\n  ")
    )
}

/// typst manbasini quradi (snapshot testi shuni solishtiradi).
#[must_use]
pub fn council_markup(m: &CouncilMinutes) -> String {
    let mut s = String::new();
    s.push_str(
        "#set page(paper: \"a4\", margin: (x: 2cm, y: 2cm))\n\
         #set text(font: \"DejaVu Sans\", size: 10pt, lang: \"uz\")\n\
         #set par(justify: false, leading: 0.6em)\n\
         #show heading: set text(weight: \"bold\")\n",
    );
    s.push_str(&format!(
        "#align(center)[#text(size: 16pt, weight: \"bold\")[#{}]]\n",
        lit("Oila kengashi bayonnomasi")
    ));
    s.push_str(&format!(
        "#align(center)[#{}]\n#v(0.6em)\n",
        lit(&format!("{} · {} · {}", m.household, m.month, m.date))
    ));

    s.push_str(&format!("== #{}\n", lit("Qatnashchilar")));
    let rows: Vec<Vec<String>> = m
        .attendees
        .iter()
        .map(|(n, r)| vec![n.clone(), r.clone()])
        .collect();
    s.push_str(&table(&rows, "(1fr, auto)"));

    s.push_str(&format!("== #{}\n", lit("Oy ko'rsatkichlari")));
    let rows: Vec<Vec<String>> = m
        .review
        .iter()
        .map(|(k, v)| vec![k.clone(), v.clone()])
        .collect();
    s.push_str(&table(&rows, "(1fr, auto)"));

    s.push_str(&format!(
        "== #{}\n",
        lit("Xarajat toifalari (Zarur / Kerak / Havas)")
    ));
    let rows: Vec<Vec<String>> = m
        .categories
        .iter()
        .map(|c| {
            vec![
                c.name.clone(),
                c.necessity.clone(),
                c.last_change.clone().unwrap_or_default(),
            ]
        })
        .collect();
    s.push_str(&table(&rows, "(1fr, auto, 1fr)"));

    s.push_str(&format!("== #{}\n", lit("Havas uchun oylik chegara")));
    let amount = m
        .limit_amount
        .clone()
        .unwrap_or_else(|| "belgilanmagan".to_owned());
    s.push_str(&format!(
        "#{}\n#v(0.3em)\n",
        lit(&format!("Chegara: {amount}. Holati: {}", m.limit_status))
    ));
    let rows: Vec<Vec<String>> = m
        .consents
        .iter()
        .map(|c| {
            vec![
                c.name.clone(),
                c.at.clone()
                    .unwrap_or_else(|| "rozilik berilmagan".to_owned()),
            ]
        })
        .collect();
    s.push_str(&table(&rows, "(1fr, auto)"));

    s.push_str(&format!("== #{}\n#v(1.2em)\n", lit("Imzolar")));
    for name in &m.signers {
        s.push_str(&format!("#grid(columns: (1fr, 1fr), gutter: 1em, [#line(length: 100%, stroke: 0.4pt)], [#{}])\n#v(1.4em)\n", lit(name)));
    }
    s.push_str(&format!(
        "#v(1fr)\n#text(size: 8pt, fill: luma(90))[#{}]\n",
        lit(&m.disclaimer)
    ));
    s
}

/// Bayonnomani PDF qiladi.
///
/// # Errors
/// Shablon yoki eksport xatosi.
pub fn council_minutes(m: &CouncilMinutes) -> Result<Vec<u8>, PdfError> {
    render_pdf(&council_markup(m))
}

#[cfg(test)]
mod tests {
    use super::*;

    pub fn sample() -> CouncilMinutes {
        CouncilMinutes {
            household: "Karimovlar oilasi".into(),
            date: "2026-10-09".into(),
            month: "2026-09".into(),
            attendees: vec![
                ("Karim aka".into(), "Katta".into()),
                ("Dilnoza".into(), "Katta".into()),
            ],
            review: vec![
                ("Daromad".into(), "8 000 000 so'm".into()),
                ("Havas sarfi".into(), "950 000 so'm".into()),
            ],
            categories: vec![
                MinutesCategory {
                    name: "Oziq-ovqat".into(),
                    necessity: "Zarur".into(),
                    last_change: None,
                },
                MinutesCategory {
                    name: "Gazak va ichimlik".into(),
                    necessity: "Havas".into(),
                    last_change: Some("Dilnoza, 2026-10-09".into()),
                },
            ],
            limit_amount: Some("1 000 000 so'm".into()),
            limit_status: "Faol: barcha kattalar rozi".into(),
            consents: vec![
                MinutesConsent {
                    name: "Karim aka".into(),
                    at: Some("2026-10-09".into()),
                },
                MinutesConsent {
                    name: "Dilnoza".into(),
                    at: Some("2026-10-09".into()),
                },
            ],
            signers: vec!["Karim aka".into(), "Dilnoza".into()],
            disclaimer: "Ta'limiy material. Fatvo yoki moliyaviy maslahat emas.".into(),
        }
    }

    #[test]
    fn string_literals_neutralize_markup_injection() {
        assert_eq!(lit("a\"b\\c\nd"), "\"a\\\"b\\\\c d\"");
        let mut m = sample();
        m.attendees[0].0 = "#panic(\"x\") $ * _ [ ] ` @ < >".into();
        m.categories[0].name = "\"); #read(\"/etc/passwd\") //".into();
        let pdf = council_minutes(&m).unwrap();
        assert!(pdf.starts_with(b"%PDF-"));
    }

    #[test]
    fn renders_a_nonempty_pdf() {
        let pdf = council_minutes(&sample()).unwrap();
        assert!(pdf.starts_with(b"%PDF-") && pdf.len() > 5_000);
    }

    #[test]
    fn empty_lists_still_render() {
        let mut m = sample();
        m.attendees.clear();
        m.categories.clear();
        m.consents.clear();
        m.signers.clear();
        m.limit_amount = None;
        assert!(council_minutes(&m).is_ok());
    }

    /// Qabul mezoni (D6): bayonnoma PDF'ida o'zbekcha belgilar (ʻ U+02BB, ʼ U+02BC) to'g'ri chiqadi.
    /// PDF'dan matn ajratib olinib, snapshot bilan solishtiriladi.
    #[test]
    fn pdf_text_snapshot_keeps_uzbek_modifier_letters() {
        let mut m = sample();
        m.review.push((
            "O\u{2bb}zbekiston \u{b7} g\u{2bb}oya \u{b7} o\u{2bc}rik".into(),
            "1 000 so'm".into(),
        ));
        let pdf = council_minutes(&m).unwrap();
        let raw = pdf_extract::extract_text_from_mem(&pdf).unwrap();
        let text = raw.split_whitespace().collect::<Vec<_>>().join(" ");
        assert!(text.contains("O\u{2bb}zbekiston"), "ʻ yo'qolgan: {text}");
        assert!(
            text.contains("g\u{2bb}oya") && text.contains("o\u{2bc}rik"),
            "{text}"
        );
        insta::assert_snapshot!("council_minutes_text", text);
    }
}
