//! Marosim smetasi (SPEC 2D.8, D11): byudjet qatorlari, manbalar bo'yicha jami va muhokama holati.
//! Matnlar — satr literallari; typst markup'i foydalanuvchi matnidan kirmaydi.

use crate::{FONT_FAMILY, lit, pairs_table, section};

/// Smeta hujjati — PDF uchun tayyor matnlar (hisob yo'q, faqat ko'rsatish).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CeremonyEstimate {
    /// Sarlavha (marosim nomi).
    pub title: String,
    /// Tur, sana va stsenariy satri, masalan «To'y · 12.03.2027 · 1 kun, 100 kishi».
    pub subtitle: String,
    /// Yaratilgan sana (`DD.MM.YYYY`).
    pub generated_on: String,
    /// Qatorlar: nomi, «miqdor × narx», manba, jami.
    pub lines: Vec<[String; 4]>,
    /// Jami: (nomi, summa) — umumiy va manbalar bo'yicha.
    pub summary: Vec<(String, String)>,
    /// Muhokama / holat izohi.
    pub note: String,
    /// Disklеymer.
    pub disclaimer: String,
}

/// Smetaning typst shabloni.
pub fn template(estimate: &CeremonyEstimate) -> String {
    let mut out = String::new();
    out.push_str("#set page(paper: \"a4\", margin: 2cm)\n");
    out.push_str(&format!(
        "#set text(font: \"{FONT_FAMILY}\", size: 11pt, lang: \"uz\")\n"
    ));
    out.push_str(&format!(
        "#align(center)[#text(size: 18pt, weight: \"bold\")[#({})]]\n",
        lit(&estimate.title)
    ));
    out.push_str(&format!(
        "#align(center)[#text(fill: luma(90))[#({})]]\n",
        lit(&estimate.subtitle)
    ));
    out.push_str(&format!(
        "#align(center)[#text(fill: luma(90))[#({})]]\n",
        lit(&format!("Tuzilgan sana: {}", estimate.generated_on))
    ));
    out.push_str("#v(1.2em)\n");
    out.push_str(&section("Byudjet qatorlari"));
    out.push_str(
        "#table(columns: (2fr, 1.2fr, 1fr, 1fr), stroke: (x: none, y: 0.4pt + luma(200)), inset: (x: 4pt, y: 5pt),\n",
    );
    out.push_str("  [*Nomi*], [*Miqdor × narx*], [*Manba*], [*Jami*],\n");
    for [name, calc, funding, total] in &estimate.lines {
        out.push_str(&format!(
            "  [#({})], [#({})], [#({})], [#({})],\n",
            lit(name),
            lit(calc),
            lit(funding),
            lit(total)
        ));
    }
    out.push_str(")\n");
    out.push_str("#v(0.8em)\n");
    out.push_str(&section("Jami"));
    out.push_str(&pairs_table(&estimate.summary));
    out.push_str("#v(0.8em)\n");
    out.push_str(&format!("#par[#({})]\n", lit(&estimate.note)));
    out.push_str("#v(2em)\n");
    out.push_str(&format!(
        "#text(size: 9pt, fill: luma(110))[#({})]\n",
        lit(&estimate.disclaimer)
    ));
    out
}
