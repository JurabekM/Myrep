//! Marosim kengashi bayonnomasi (D11): «Buni qarzsiz qanday o'tkazamiz?» muhokamasi — stsenariylar
//! taqqoslanadi, qaror matni va kattalar roziligi qayd etiladi. Matnlar — satr literallari.

use crate::{FONT_FAMILY, lit, pairs_table, section};

/// Bayonnoma — PDF uchun tayyor matnlar.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct DiscussionMinutes {
    /// Sarlavha (marosim nomi).
    pub title: String,
    /// Tur va sana satri.
    pub subtitle: String,
    /// Yaratilgan sana (`DD.MM.YYYY`).
    pub generated_on: String,
    /// Taqqoslash ustun sarlavhalari: birinchisi — ko'rsatkich nomi, qolganlari — stsenariylar.
    pub headers: Vec<String>,
    /// Taqqoslash qatorlari: ko'rsatkich nomi va har stsenariy uchun qiymat (`headers` uzunligida).
    pub rows: Vec<Vec<String>>,
    /// Qaror: (nomi, qiymat) — tanlangan stsenariy, qaror matni, boshlangan va yakunlangan sana.
    pub decision: Vec<(String, String)>,
    /// Kattalar: nomi va rozilik matni.
    pub adults: Vec<(String, String)>,
    /// Disklеymer.
    pub disclaimer: String,
}

/// Bayonnomaning typst shabloni.
pub fn template(minutes: &DiscussionMinutes) -> String {
    let mut out = String::new();
    out.push_str("#set page(paper: \"a4\", margin: 2cm)\n");
    out.push_str(&format!(
        "#set text(font: \"{FONT_FAMILY}\", size: 11pt, lang: \"uz\")\n"
    ));
    out.push_str(&format!(
        "#align(center)[#text(size: 18pt, weight: \"bold\")[#({})]]\n",
        lit("Oila kengashi bayonnomasi")
    ));
    out.push_str(&format!(
        "#align(center)[#text(size: 13pt)[#({})]]\n",
        lit(&minutes.title)
    ));
    out.push_str(&format!(
        "#align(center)[#text(fill: luma(90))[#({})]]\n",
        lit(&minutes.subtitle)
    ));
    out.push_str(&format!(
        "#align(center)[#text(fill: luma(90))[#({})]]\n",
        lit(&format!("Tuzilgan sana: {}", minutes.generated_on))
    ));
    out.push_str("#v(1.2em)\n");
    out.push_str(&section("Stsenariylar taqqoslandi"));
    let columns = minutes.headers.len().max(1);
    let spec = std::iter::once("1.4fr")
        .chain(std::iter::repeat_n("1fr", columns.saturating_sub(1)))
        .collect::<Vec<_>>()
        .join(", ");
    out.push_str(&format!(
        "#table(columns: ({spec}), stroke: (x: none, y: 0.4pt + luma(200)), inset: (x: 4pt, y: 5pt),\n"
    ));
    out.push_str("  ");
    for header in &minutes.headers {
        out.push_str(&format!("[*#({})*], ", lit(header)));
    }
    out.push('\n');
    for row in &minutes.rows {
        out.push_str("  ");
        for cell in row.iter().take(columns) {
            out.push_str(&format!("[#({})], ", lit(cell)));
        }
        for _ in row.len()..columns {
            out.push_str("[], ");
        }
        out.push('\n');
    }
    out.push_str(")\n");
    out.push_str("#v(0.8em)\n");
    out.push_str(&section("Qaror: «Buni qarzsiz qanday o'tkazamiz?»"));
    out.push_str(&pairs_table(&minutes.decision));
    out.push_str("#v(0.8em)\n");
    out.push_str(&section("Kattalar roziligi (har biri o'z PIN'i bilan)"));
    out.push_str(&pairs_table(&minutes.adults));
    out.push_str("#v(2em)\n");
    out.push_str(&format!(
        "#text(size: 9pt, fill: luma(110))[#({})]\n",
        lit(&minutes.disclaimer)
    ));
    out
}
