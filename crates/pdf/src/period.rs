//! Sherik uchun davr hisoboti (SPEC 2E.3, D13): davr yozuvlari, yakun, taqsimot, zanjir boshi.
//! Matnlar — satr literallari; typst markup'i foydalanuvchi matnidan kirmaydi.

use crate::{FONT_FAMILY, lit, pairs_table, section};

/// Davr hisoboti — PDF uchun tayyor matnlar.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PeriodReport {
    /// Sarlavha (sheriklik nomi).
    pub title: String,
    /// Davr matni, masalan «01.11.2026 — 30.11.2026».
    pub period: String,
    /// Yaratilgan sana (`DD.MM.YYYY`).
    pub generated_on: String,
    /// Yozuvlar: sana, tur, tomon, summa.
    pub entries: Vec<[String; 4]>,
    /// Yakun: (nomi, summa).
    pub summary: Vec<(String, String)>,
    /// Taqsimot: (tomon, summa va izoh).
    pub distribution: Vec<(String, String)>,
    /// Zanjir boshi (hex) — bayonnoma dalili.
    pub chain_head: String,
    /// Izoh (fors-major va h.k.).
    pub note: String,
    /// Disklеymer.
    pub disclaimer: String,
}

/// Davr hisobotining typst shabloni.
pub fn template(report: &PeriodReport) -> String {
    let mut out = String::new();
    out.push_str("#set page(paper: \"a4\", margin: 2cm)\n");
    out.push_str(&format!(
        "#set text(font: \"{FONT_FAMILY}\", size: 11pt, lang: \"uz\")\n"
    ));
    out.push_str(&format!(
        "#align(center)[#text(size: 18pt, weight: \"bold\")[#({})]]\n",
        lit(&report.title)
    ));
    out.push_str(&format!(
        "#align(center)[#text(fill: luma(90))[#({})]]\n",
        lit(&format!("Davr hisoboti · {}", report.period))
    ));
    out.push_str(&format!(
        "#align(center)[#text(fill: luma(90))[#({})]]\n",
        lit(&format!("Tuzilgan sana: {}", report.generated_on))
    ));
    out.push_str("#v(1.2em)\n");
    out.push_str(&section("Davr yozuvlari"));
    out.push_str(
        "#table(columns: (1fr, 1.4fr, 1.4fr, 1.2fr), stroke: (x: none, y: 0.4pt + luma(200)), inset: (x: 4pt, y: 5pt),\n",
    );
    out.push_str("  [*Sana*], [*Tur*], [*Tomon*], [*Summa*],\n");
    for [date, kind, party, amount] in &report.entries {
        out.push_str(&format!(
            "  [#({})], [#({})], [#({})], [#({})],\n",
            lit(date),
            lit(kind),
            lit(party),
            lit(amount)
        ));
    }
    out.push_str(")\n");
    out.push_str("#v(0.8em)\n");
    out.push_str(&section("Davr yakuni"));
    out.push_str(&pairs_table(&report.summary));
    out.push_str("#v(0.8em)\n");
    out.push_str(&section("Taqsimot"));
    out.push_str(&pairs_table(&report.distribution));
    out.push_str("#v(0.8em)\n");
    out.push_str(&format!("#par[#({})]\n", lit(&report.note)));
    out.push_str("#v(0.6em)\n");
    out.push_str(&format!(
        "#text(size: 9pt, fill: luma(90))[#({})]\n",
        lit(&format!("Zanjir boshi (SHA-256): {}", report.chain_head))
    ));
    out.push_str("#v(2em)\n");
    out.push_str(&format!(
        "#text(size: 9pt, fill: luma(110))[#({})]\n",
        lit(&report.disclaimer)
    ));
    out
}
