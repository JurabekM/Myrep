//! Sheriklik davr hisoboti (D13, SPEC 2E.3): sherik uchun PDF. Ma'lumotlar tayyor formatlangan matn;
//! foydalanuvchi matnlari typst string literal sifatida qo'yiladi.

use crate::{minutes::lit, render_pdf, PdfError};

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ReportEntry {
    pub date: String,
    pub kind: String,
    pub description: String,
    pub amount: String,
    pub force_majeure: bool,
    pub evidence: usize,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PeriodReportDoc {
    pub title: String,
    /// «1-davr · 2026-10-01 — 2026-10-31».
    pub subtitle: String,
    pub entries: Vec<ReportEntry>,
    /// (ko'rsatkich, qiymat): kirim, xarajat, sof natija.
    pub totals: Vec<(String, String)>,
    /// (tomon, qoida/rol, summa).
    pub distribution: Vec<(String, String, String)>,
    pub buyout_note: Option<String>,
    pub disclaimer: String,
}

fn text(s: &str) -> String {
    format!("[#{}]", lit(s))
}

#[must_use]
pub fn period_markup(d: &PeriodReportDoc) -> String {
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
    s.push_str(&format!("== #{}\n", lit("Kirim va xarajatlar")));
    let mut cells: Vec<String> = ["Sana", "Turi", "Izoh", "Summa"]
        .iter()
        .map(|h| format!("[*{h}*]"))
        .collect();
    for e in &d.entries {
        let mut desc = e.description.clone();
        if e.force_majeure {
            desc.push_str(" [fors-major]");
        }
        if e.evidence > 0 {
            desc.push_str(&format!(" (dalil: {})", e.evidence));
        }
        cells.extend([text(&e.date), text(&e.kind), text(&desc), text(&e.amount)]);
    }
    s.push_str(&format!(
        "#table(columns: (auto, auto, 1fr, auto), stroke: 0.4pt + luma(160), inset: 5pt,\n  {}\n)\n#v(0.6em)\n",
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
    s.push_str(&format!("== #{}\n", lit("Taqsimot")));
    let rows: Vec<String> = d
        .distribution
        .iter()
        .flat_map(|(a, b, c)| [text(a), text(b), text(c)])
        .collect();
    s.push_str(&format!(
        "#table(columns: (1fr, 1fr, auto), stroke: 0.4pt + luma(160), inset: 5pt,\n  {}\n)\n",
        rows.join(",\n  ")
    ));
    if let Some(b) = &d.buyout_note {
        s.push_str(&format!("#v(0.4em)#{}\n", lit(b)));
    }
    s.push_str(&format!(
        "#v(1fr)\n#text(size: 8pt, fill: luma(90))[#{}]\n",
        lit(&d.disclaimer)
    ));
    s
}

/// Davr hisobotini PDF qiladi.
///
/// # Errors
/// Shablon yoki eksport xatosi.
pub fn period_report(d: &PeriodReportDoc) -> Result<Vec<u8>, PdfError> {
    render_pdf(&period_markup(d))
}

#[cfg(test)]
mod tests {
    use super::*;

    fn sample() -> PeriodReportDoc {
        PeriodReportDoc {
            title: "Oshxona \u{b7} hisobot".into(),
            subtitle: "1-davr \u{b7} 2026-10-01 \u{2014} 2026-10-31".into(),
            entries: vec![
                ReportEntry {
                    date: "2026-10-05".into(),
                    kind: "Kirim".into(),
                    description: "Buyurtma (to\u{2bb}y)".into(),
                    amount: "5 000 000 so'm".into(),
                    force_majeure: false,
                    evidence: 1,
                },
                ReportEntry {
                    date: "2026-10-20".into(),
                    kind: "Xarajat".into(),
                    description: "Omborni suv bosdi".into(),
                    amount: "1 000 000 so'm".into(),
                    force_majeure: true,
                    evidence: 2,
                },
            ],
            totals: vec![
                ("Kirim".into(), "5 000 000 so'm".into()),
                ("Sof natija".into(), "4 000 000 so'm".into()),
            ],
            distribution: vec![
                (
                    "Karim aka".into(),
                    "Kapital egasi".into(),
                    "1 600 000 so'm".into(),
                ),
                ("Zamira".into(), "Ishchi".into(), "2 400 000 so'm".into()),
            ],
            buyout_note: Some("Buyout: 300 000 so'm sotuvchiga o'tdi".into()),
            disclaimer: "Ta'limiy material. Fatvo yoki moliyaviy maslahat emas.".into(),
        }
    }

    #[test]
    fn period_report_snapshot_and_safety() {
        let pdf = period_report(&sample()).unwrap();
        let raw = pdf_extract::extract_text_from_mem(&pdf).unwrap();
        let t = raw.split_whitespace().collect::<Vec<_>>().join(" ");
        assert!(t.contains("to\u{2bb}y"), "{t}");
        insta::assert_snapshot!("period_report_text", t);
        let mut d = sample();
        d.entries[0].description = "#panic(\"x\") $ * _ \"); #read(\"/etc/passwd\")".into();
        assert!(period_report(&d).is_ok());
        d.entries.clear();
        d.distribution.clear();
        d.buyout_note = None;
        assert!(period_report(&d).is_ok());
    }
}
