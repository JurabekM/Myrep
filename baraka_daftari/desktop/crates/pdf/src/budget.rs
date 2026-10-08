//! Marosim smetasi (D11): chop etiladigan byudjet. Ma'lumotlar tayyor formatlangan matn.
//! Foydalanuvchi matnlari typst string literal sifatida qo'yiladi (markup injection yo'q).

use crate::{minutes::lit, render_pdf, PdfError};

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct BudgetLine {
    pub name: String,
    pub qty: String,
    pub unit_price: String,
    pub total: String,
    pub funding: String,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CeremonyBudgetDoc {
    pub title: String,
    /// «To'y · 2026-12-12 · Qoralama».
    pub subtitle: String,
    pub lines: Vec<BudgetLine>,
    /// (yorliq, qiymat): jami va manbalar bo'yicha.
    pub totals: Vec<(String, String)>,
    /// Qarz haqida ogohlantirish (bo'lsa).
    pub debt_note: Option<String>,
    pub discussion_note: Option<String>,
    pub disclaimer: String,
}

fn text(s: &str) -> String {
    format!("[#{}]", lit(s))
}

#[must_use]
pub fn budget_markup(d: &CeremonyBudgetDoc) -> String {
    let mut s = String::from(
        "#set page(paper: \"a4\", margin: (x: 2cm, y: 2cm))\n\
         #set text(font: \"DejaVu Sans\", size: 10pt, lang: \"uz\")\n\
         #set par(justify: false, leading: 0.6em)\n",
    );
    s.push_str(&format!(
        "#align(center)[#text(size: 16pt, weight: \"bold\")[#{}]]\n#align(center)[#{}]\n#v(0.8em)\n",
        lit(&d.title),
        lit(&d.subtitle)
    ));
    let mut cells: Vec<String> = ["Nomi", "Miqdor", "Narx", "Jami", "Manba"]
        .iter()
        .map(|h| format!("[*{h}*]"))
        .collect();
    for l in &d.lines {
        cells.extend([
            text(&l.name),
            text(&l.qty),
            text(&l.unit_price),
            text(&l.total),
            text(&l.funding),
        ]);
    }
    s.push_str(&format!(
        "#table(columns: (1fr, auto, auto, auto, auto), stroke: 0.4pt + luma(160), inset: 5pt,\n  {}\n)\n#v(0.8em)\n",
        cells.join(",\n  ")
    ));
    let rows: Vec<String> = d
        .totals
        .iter()
        .flat_map(|(k, v)| [text(k), text(v)])
        .collect();
    s.push_str(&format!(
        "#table(columns: (1fr, auto), stroke: 0.4pt + luma(160), inset: 5pt,\n  {}\n)\n",
        rows.join(",\n  ")
    ));
    if let Some(n) = &d.debt_note {
        s.push_str(&format!("#v(0.6em)#text(weight: \"bold\")[#{}]\n", lit(n)));
    }
    if let Some(n) = &d.discussion_note {
        s.push_str(&format!(
            "#v(0.4em)#{}\n",
            lit(&format!("Oilaviy muhokama: {n}"))
        ));
    }
    s.push_str(&format!(
        "#v(1fr)\n#text(size: 8pt, fill: luma(90))[#{}]\n",
        lit(&d.disclaimer)
    ));
    s
}

/// Smetani PDF qiladi.
///
/// # Errors
/// Shablon yoki eksport xatosi.
pub fn ceremony_budget(d: &CeremonyBudgetDoc) -> Result<Vec<u8>, PdfError> {
    render_pdf(&budget_markup(d))
}

#[cfg(test)]
mod tests {
    use super::*;

    fn sample() -> CeremonyBudgetDoc {
        CeremonyBudgetDoc {
            title: "O\u{2bb}g\u{2bb}il to\u{2bb}yi".into(),
            subtitle: "To'y · 2026-12-12 · Qoralama".into(),
            lines: vec![
                BudgetLine {
                    name: "Osh (mehmonlar)".into(),
                    qty: "200".into(),
                    unit_price: "150 000 so'm".into(),
                    total: "30 000 000 so'm".into(),
                    funding: "Jamg'arma".into(),
                },
                BudgetLine {
                    name: "Xonanda".into(),
                    qty: "1".into(),
                    unit_price: "5 000 000 so'm".into(),
                    total: "5 000 000 so'm".into(),
                    funding: "Qarz".into(),
                },
            ],
            totals: vec![
                ("Jami".into(), "35 000 000 so'm".into()),
                ("Qarz".into(), "5 000 000 so'm".into()),
            ],
            debt_note: Some("Diqqat: 5 000 000 so'm qarz bilan moliyalanadi.".into()),
            discussion_note: Some("Kichikroq doirada o'tkazamiz".into()),
            disclaimer: "Ta'limiy material. Fatvo yoki moliyaviy maslahat emas.".into(),
        }
    }

    #[test]
    fn budget_text_snapshot_keeps_uzbek_letters() {
        let pdf = ceremony_budget(&sample()).unwrap();
        let raw = pdf_extract::extract_text_from_mem(&pdf).unwrap();
        let t = raw.split_whitespace().collect::<Vec<_>>().join(" ");
        assert!(t.contains("O\u{2bb}g\u{2bb}il"), "{t}");
        insta::assert_snapshot!("ceremony_budget_text", t);
    }

    #[test]
    fn injection_and_empty_inputs_are_safe() {
        let mut d = sample();
        d.lines[0].name = "#panic(\"x\") $ * _ \"); #read(\"/etc/passwd\")".into();
        assert!(ceremony_budget(&d).is_ok());
        d.lines.clear();
        d.totals.clear();
        d.debt_note = None;
        d.discussion_note = None;
        assert!(ceremony_budget(&d).is_ok());
    }
}
