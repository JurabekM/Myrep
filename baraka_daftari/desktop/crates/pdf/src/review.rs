//! 6-qonun: oylik ochiq hisob ko'rigi bayonnomasi (SPEC 2F.5, 2F.6). Bayonnomada har bir tomonning javobi
//! (ko'rdim, roziman yoki e'tiroz + izoh), davr yozuvlari, vazifa hodisalari va zanjir boshi (`chainHead`) bor.
//!
//! Hujjat «ta'limiy material»: yuridik kuchi haqida va'da berilmaydi. Foydalanuvchi matnlari typst string
//! literal sifatida qo'yiladi (markup injection yo'q).

use crate::agreement::{bullets, section, table};
use crate::{minutes::lit, render_pdf_with_files, PdfError};

/// Bayonnoma uchun tayyor ma'lumot: sanalar, summalar va holatlar matn ko'rinishida (servis formatlaydi).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ReviewPdfDoc {
    pub title: String,
    /// «2026 yil, oktyabr».
    pub period: String,
    /// Yakunlangan bo'lsa `true`; aks holda qoralama.
    pub closed: bool,
    /// «Zanjir buzilmagan (12 ta yozuv)» yoki «Zanjir buzilgan: yozuv #5».
    pub chain_status: String,
    /// Bayonnomadagi zanjir boshi (yopilganda qayd etilgan; hali yopilmagan bo'lsa joriy).
    pub chain_head: String,
    /// «Yopilgandagi zanjir boshi bilan mos keladi» yoki «MOS KELMAYDI: …».
    pub head_status: String,
    /// (ism, javob).
    pub parties: Vec<(String, String)>,
    /// Davr yozuvlari: «2026-10-12 · Kirim · Anvar · 500 000 so'm — izoh».
    pub ledger: Vec<String>,
    /// Vazifa hodisalari: «2026-10-14 · Dilshod · Yo'l yopiq edi. Taklif: …».
    pub incidents: Vec<String>,
    pub legal_note: String,
    pub disclaimer: String,
}

/// Typst manbasi (snapshot testi shuni va matnni solishtiradi).
#[must_use]
pub fn review_markup(d: &ReviewPdfDoc) -> String {
    let mut s = String::new();
    s.push_str(
        "#set page(paper: \"a4\", margin: (x: 2cm, y: 2cm))\n\
         #set text(font: \"DejaVu Sans\", size: 10pt, lang: \"uz\")\n\
         #set par(justify: false, leading: 0.6em)\n",
    );
    s.push_str(&format!(
        "#align(center)[#text(size: 16pt, weight: \"bold\")[#{}]]\n#v(0.4em)\n#align(center)[#text(size: 9pt)[#{}]]\n#v(0.8em)\n",
        lit("Ko'rik bayonnomasi"),
        lit(&d.title)
    ));
    let status = if d.closed {
        "Yakunlangan"
    } else {
        "Qoralama: hali yakunlanmagan"
    };
    s.push_str(&table(&[
        vec!["Davr".to_owned(), d.period.clone()],
        vec!["Holat".to_owned(), status.to_owned()],
        vec!["Zanjir holati".to_owned(), d.chain_status.clone()],
        vec!["Zanjir boshi (chainHead)".to_owned(), d.chain_head.clone()],
        vec!["Bayonnoma va zanjir".to_owned(), d.head_status.clone()],
    ]));
    s.push_str(&section("1. Tomonlar javobi"));
    if d.parties.is_empty() {
        s.push_str(&format!("#{}\n", lit("Tomonlar yo'q")));
    } else {
        let rows: Vec<Vec<String>> = d
            .parties
            .iter()
            .map(|(name, answer)| vec![name.clone(), answer.clone()])
            .collect();
        s.push_str(&table(&rows));
    }
    s.push_str(&section("2. Davr yozuvlari"));
    if d.ledger.is_empty() {
        s.push_str(&format!("#{}\n", lit("Bu davrda yozuv yo'q")));
    } else {
        s.push_str(&bullets(&d.ledger));
    }
    s.push_str(&section("3. Vazifa hodisalari"));
    if d.incidents.is_empty() {
        s.push_str(&format!("#{}\n", lit("Hodisa qayd etilmagan")));
    } else {
        s.push_str(&bullets(&d.incidents));
    }
    s.push_str(&format!(
        "\n#v(1em)\n#text(size: 8pt)[#{}]\n#text(size: 8pt)[#{}]\n",
        lit(&d.legal_note),
        lit(&d.disclaimer)
    ));
    s
}

/// Ko'rik bayonnomasi PDF'i.
///
/// # Errors
/// Typst kompilyatsiya xatosi.
pub fn review_pdf(d: &ReviewPdfDoc) -> Result<Vec<u8>, PdfError> {
    render_pdf_with_files(&review_markup(d), &[])
}

#[cfg(test)]
mod tests {
    use super::*;

    fn sample(head_status: &str) -> ReviewPdfDoc {
        ReviewPdfDoc {
            title: "Yetkazib berish musharakasi".into(),
            period: "2026 yil, oktyabr".into(),
            closed: true,
            chain_status: "Zanjir buzilmagan (9 ta yozuv)".into(),
            chain_head: "a3f1c0d2e4b5a6978869504132211009f8e7d6c5b4a39281706f5e4d3c2b1a09".into(),
            head_status: head_status.into(),
            parties: vec![
                ("Anvar".into(), "Ko'rdim, roziman".into()),
                (
                    "Dilshod".into(),
                    "E'tiroz: yo'l xarajati hisobga olinmagan".into(),
                ),
            ],
            ledger: vec!["2026-10-12 · Kirim · Anvar · 500 000 so'm — Buyurtma 1".into()],
            incidents: vec![
                "2026-10-14 · Dilshod · Yo'l yopiq edi. Taklif: ertaga topshiraman".into(),
            ],
            legal_note: "Shablon yurist va ulamo tasdig'idan o'tmagan.".into(),
            disclaimer: "Ta'limiy material. Fatvo yoki moliyaviy maslahat emas.".into(),
        }
    }

    fn text_of(pdf: &[u8]) -> String {
        let raw = pdf_extract::extract_text_from_mem(pdf).unwrap();
        raw.split_whitespace().collect::<Vec<_>>().join(" ")
    }

    /// D13A: bayonnoma matni snapshot bilan qotirilgan; tomonlar javobi va zanjir boshi chiqadi.
    #[test]
    fn review_text_snapshot_keeps_answers_and_chain_head() {
        let pdf = review_pdf(&sample("Yopilgandagi zanjir boshi bilan mos keladi")).unwrap();
        assert!(pdf.starts_with(b"%PDF"));
        let t = text_of(&pdf);
        assert!(t.contains("E'tiroz: yo'l xarajati"), "{t}");
        assert!(t.contains("a3f1c0d2e4b5a6978869504132211009"), "{t}");
        insta::assert_snapshot!("review_text", t);
    }

    /// Yozuv o'zgargan bo'lsa, bayonnoma buni ochiq ko'rsatadi (zanjir boshi mos kelmaydi).
    #[test]
    fn head_mismatch_is_printed_as_a_warning() {
        let t = text_of(
            &review_pdf(&sample("MOS KELMAYDI: yozuvlar o'zgargan bo'lishi mumkin")).unwrap(),
        );
        assert!(t.contains("MOS KELMAYDI"), "{t}");
    }
}
