//! 6-qonun: hakam uchun ish papkasi (SPEC 2F.8). Bitta PDF: mundarija va sahifa raqamlari bilan
//! kelishuv versiyalari, hisob yozuvlari, zanjir tekshiruvi, ko'rik bayonnomalari, vazifa hodisalari,
//! tomonlarning talablari va hakam qarorlari.
//!
//! Hujjat «ta'limiy material»: hakamning qarorini almashtirmaydi va yuridik kuch haqida va'da bermaydi.

use crate::agreement::{bullets, table};
use crate::{minutes::lit, render_pdf_with_files, PdfError};

/// Papka uchun tayyor ma'lumot (servis formatlaydi).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct DisputeFolderDoc {
    pub title: String,
    /// «Nizoli», «Faol», «Yopilgan» ...
    pub status: String,
    /// «Zanjir buzilmagan (14 ta yozuv)» yoki «Zanjir buzilgan: yozuv #5».
    pub chain_status: String,
    /// Joriy zanjir boshi.
    pub chain_head: String,
    /// «v2 · 2026-10-01 · xesh 3f9a…».
    pub versions: Vec<String>,
    /// «#3 · 2026-10-12 · Kirim · Anvar · 500 000 so'm — izoh».
    pub entries: Vec<String>,
    /// «2026-10 · yopilgan boshi: a3f1… · boshi mos keladi».
    pub reviews: Vec<String>,
    /// «2026-10-14 · Dilshod · Yo'l yopiq edi. Taklif: …».
    pub incidents: Vec<String>,
    /// «2026-10-15 · Dilshod · Foyda hisobi: 50/50 bo'lsin».
    pub claims: Vec<String>,
    /// Hakam qarorlari.
    pub decisions: Vec<String>,
    pub legal_note: String,
    pub disclaimer: String,
}

fn chapter(title: &str) -> String {
    format!("= #{}\n", lit(title))
}

fn list_or(items: &[String], empty: &str) -> String {
    if items.is_empty() {
        format!("#{}\n", lit(empty))
    } else {
        bullets(items)
    }
}

/// Typst manbasi (snapshot testi shuni va matnni solishtiradi).
#[must_use]
pub fn dispute_folder_markup(d: &DisputeFolderDoc) -> String {
    let mut s = String::new();
    s.push_str(
        "#set page(paper: \"a4\", margin: (x: 2cm, y: 2cm), numbering: \"1\")\n\
         #set text(font: \"DejaVu Sans\", size: 10pt, lang: \"uz\")\n\
         #set par(justify: false, leading: 0.6em)\n\
         #show heading.where(level: 1): set text(size: 12pt)\n",
    );
    s.push_str(&format!(
        "#align(center)[#text(size: 16pt, weight: \"bold\")[#{}]]\n#v(0.4em)\n#align(center)[#text(size: 9pt)[#{}]]\n#v(0.8em)\n",
        lit("Hakam uchun ish papkasi"),
        lit(&d.title)
    ));
    s.push_str(&table(&[
        vec!["Holat".to_owned(), d.status.clone()],
        vec!["Zanjir holati".to_owned(), d.chain_status.clone()],
        vec!["Zanjir boshi (chainHead)".to_owned(), d.chain_head.clone()],
    ]));
    s.push_str("#v(1em)\n#outline(title: [Mundarija], depth: 1)\n#pagebreak()\n");
    s.push_str(&chapter("1. Kelishuv versiyalari"));
    s.push_str(&list_or(&d.versions, "Versiyalar yo'q"));
    s.push_str(&chapter("2. Hisob yozuvlari"));
    s.push_str(&list_or(&d.entries, "Yozuv yo'q"));
    s.push_str(&chapter("3. Ko'rik bayonnomalari"));
    s.push_str(&list_or(&d.reviews, "Yopilgan ko'rik yo'q"));
    s.push_str(&chapter("4. Vazifa hodisalari"));
    s.push_str(&list_or(&d.incidents, "Hodisa qayd etilmagan"));
    s.push_str(&chapter("5. Tomonlarning talablari"));
    s.push_str(&list_or(&d.claims, "Talab qayd etilmagan"));
    s.push_str(&chapter("6. Hakam qarori"));
    s.push_str(&list_or(&d.decisions, "Qaror hali yozilmagan"));
    s.push_str(&format!(
        "\n#v(1em)\n#text(size: 8pt)[#{}]\n#text(size: 8pt)[#{}]\n",
        lit(&d.legal_note),
        lit(&d.disclaimer)
    ));
    s
}

/// Hakam ish papkasi PDF'i.
///
/// # Errors
/// Typst kompilyatsiya xatosi.
pub fn dispute_folder_pdf(d: &DisputeFolderDoc) -> Result<Vec<u8>, PdfError> {
    render_pdf_with_files(&dispute_folder_markup(d), &[])
}

#[cfg(test)]
mod tests {
    use super::*;

    fn sample() -> DisputeFolderDoc {
        DisputeFolderDoc {
            title: "Yetkazib berish musharakasi".into(),
            status: "Nizoli".into(),
            chain_status: "Zanjir buzilmagan (7 ta yozuv)".into(),
            chain_head: "9c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f60718293a4b5c6d7e8f9a0b1c2d3e4f5".into(),
            versions: vec![
                "v1 · 2026-10-01 · xesh 3f9a1b2c3d4e".into(),
                "v2 · 2026-10-05 · xesh 77ab09cd11ef".into(),
            ],
            entries: vec!["#3 · 2026-10-12 · Kirim · Anvar · 500 000 so'm — Buyurtma 1".into()],
            reviews: vec!["2026-09 · yopilgan boshi: a3f1c0d2e4b5 · boshi mos keladi".into()],
            incidents: vec![
                "2026-10-14 · Dilshod · Yo'l yopiq edi. Taklif: ertaga topshiraman".into(),
            ],
            claims: vec!["2026-10-15 · Anvar · Foyda hisobi: ulush 50/50 bo'lsin".into()],
            decisions: vec!["Hakam Usta Olim: ulush 60/40 shartnoma bo'yicha qoladi".into()],
            legal_note: "Shablon yurist va ulamo tasdig'idan o'tmagan.".into(),
            disclaimer: "Ta'limiy material. Fatvo yoki moliyaviy maslahat emas.".into(),
        }
    }

    fn text_of(pdf: &[u8]) -> String {
        let raw = pdf_extract::extract_text_from_mem(pdf).unwrap();
        raw.split_whitespace().collect::<Vec<_>>().join(" ")
    }

    /// D13A: papka bo'limlari va mundarija bor; matn snapshot bilan qotirilgan.
    #[test]
    fn dispute_folder_snapshot_has_toc_and_all_six_sections() {
        let pdf = dispute_folder_pdf(&sample()).unwrap();
        assert!(pdf.starts_with(b"%PDF"));
        let t = text_of(&pdf);
        for section in [
            "1. Kelishuv versiyalari",
            "2. Hisob yozuvlari",
            "3. Ko'rik bayonnomalari",
            "4. Vazifa hodisalari",
            "5. Tomonlarning talablari",
            "6. Hakam qarori",
        ] {
            assert!(t.contains(section), "{section} yo'q: {t}");
        }
        assert!(t.contains("Mundarija"), "{t}");
        insta::assert_snapshot!("dispute_folder_text", t);
    }
}
