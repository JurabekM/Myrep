//! Qarz tilxati (D9, SPEC 2D.5): tomonlar, summa, muddat, to'lov jadvali, guvohlar va imzo joylari.
//! Imzo: sichqoncha/pero bilan chizilgan PNG yoki «chop etib qo'lda imzolash» (bo'sh chiziq).
//!
//! Hujjat «shaxsiy hisob uchun yozuv» — yuridik kuchi haqida va'da berilmaydi. Foydalanuvchi matnlari
//! typst string literal sifatida qo'yiladi (markup injection yo'q).

use crate::{minutes::lit, render_pdf_with_files, PdfError};

const PNG_MAGIC: &[u8] = b"\x89PNG\r\n\x1a\n";
/// Bitta imzo rasmi uchun chegara (xotira va PDF hajmi).
pub const MAX_SIGNATURE_BYTES: usize = 300 * 1024;

#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct ReceiptSignatures {
    /// Qarz bergan tomon imzosi (PNG). `None` — qo'lda imzolash uchun bo'sh joy.
    pub lender_png: Option<Vec<u8>>,
    pub borrower_png: Option<Vec<u8>>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct LoanReceiptDoc {
    pub lender: String,
    pub borrower: String,
    /// Formatlangan summa («3 000 000 so'm»).
    pub amount: String,
    pub given_on: String,
    pub due_on: Option<String>,
    pub reason: Option<String>,
    /// (sana, formatlangan summa)
    pub schedule: Vec<(String, String)>,
    /// Ustama bor bo'lsa ogohlantirish matni; `None` — foizsiz (qarzi hasana).
    pub markup_note: Option<String>,
    pub witnesses: Vec<String>,
    pub confirmed_by_counterparty: bool,
    pub legal_note: String,
    pub disclaimer: String,
}

fn text(s: &str) -> String {
    format!("[#{}]", lit(s))
}

fn check_png(bytes: &[u8]) -> Result<(), PdfError> {
    if !bytes.starts_with(PNG_MAGIC) {
        return Err(PdfError::Compile("imzo rasmi PNG bo'lishi kerak".into()));
    }
    if bytes.len() > MAX_SIGNATURE_BYTES {
        return Err(PdfError::Compile("imzo rasmi juda katta".into()));
    }
    Ok(())
}

fn signature_cell(who: &str, name: &str, image: Option<&str>) -> String {
    let img = image.map_or_else(
        || "#v(1.6cm)".to_owned(),
        |f| format!("#box(height: 1.6cm, image(\"{f}\", height: 1.6cm))"),
    );
    format!(
        "[{img}\n#line(length: 100%, stroke: 0.4pt)\n#text(size: 8pt)[#{} \u{2014} #{}]]",
        lit(who),
        lit(name)
    )
}

/// typst manbasi (snapshot/matn testi uchun).
#[must_use]
pub fn receipt_markup(d: &LoanReceiptDoc, sig: &ReceiptSignatures) -> String {
    let mut s = String::new();
    s.push_str(
        "#set page(paper: \"a4\", margin: (x: 2cm, y: 2cm))\n\
         #set text(font: \"DejaVu Sans\", size: 10pt, lang: \"uz\")\n\
         #set par(justify: false, leading: 0.6em)\n",
    );
    s.push_str(&format!(
        "#align(center)[#text(size: 16pt, weight: \"bold\")[#{}]]\n#v(0.8em)\n",
        lit("Qarz tilxati")
    ));
    let mut facts = vec![
        vec!["Qarz bergan".to_owned(), d.lender.clone()],
        vec!["Qarz olgan".to_owned(), d.borrower.clone()],
        vec!["Summa".to_owned(), d.amount.clone()],
        vec!["Berilgan sana".to_owned(), d.given_on.clone()],
        vec![
            "Qaytarish muddati".to_owned(),
            d.due_on.clone().unwrap_or_else(|| "kelishilmagan".into()),
        ],
    ];
    if let Some(r) = &d.reason {
        facts.push(vec!["Sababi".to_owned(), r.clone()]);
    }
    let cells: Vec<String> = facts.iter().flatten().map(|c| text(c)).collect();
    s.push_str(&format!(
        "#table(columns: (auto, 1fr), stroke: 0.4pt + luma(160), inset: 5pt,\n  {}\n)\n#v(0.6em)\n",
        cells.join(",\n  ")
    ));
    s.push_str(&format!(
        "#{}\n#v(0.4em)\n",
        lit(&d.markup_note.clone().unwrap_or_else(|| {
            "Qarz foizsiz (qarzi hasana): qaytariladigan summa berilgan summaga teng.".to_owned()
        }))
    ));
    if !d.schedule.is_empty() {
        s.push_str(&format!("== #{}\n", lit("To'lov jadvali")));
        let cells: Vec<String> = d
            .schedule
            .iter()
            .flat_map(|(a, b)| [text(a), text(b)])
            .collect();
        s.push_str(&format!(
            "#table(columns: (1fr, auto), stroke: 0.4pt + luma(160), inset: 5pt,\n  {}\n)\n",
            cells.join(",\n  ")
        ));
    }
    s.push_str(&format!("== #{}\n", lit("Guvohlar")));
    let witnesses: Vec<String> = (0..d.witnesses.len().max(2))
        .map(|i| {
            let name = d.witnesses.get(i).map_or("", String::as_str);
            format!(
                "[#v(1cm)#line(length: 100%, stroke: 0.4pt)#text(size: 8pt)[#{}]]",
                lit(&format!("Guvoh {}: {name}", i + 1))
            )
        })
        .collect();
    s.push_str(&format!(
        "#grid(columns: (1fr, 1fr), gutter: 1em, row-gutter: 0.8em,\n  {}\n)\n",
        witnesses.join(",\n  ")
    ));
    s.push_str(&format!("== #{}\n", lit("Imzolar")));
    s.push_str(&format!(
        "#grid(columns: (1fr, 1fr), gutter: 1em,\n  {},\n  {}\n)\n",
        signature_cell(
            "Qarz bergan",
            &d.lender,
            sig.lender_png.as_ref().map(|_| "sig-lender.png")
        ),
        signature_cell(
            "Qarz olgan",
            &d.borrower,
            sig.borrower_png.as_ref().map(|_| "sig-borrower.png")
        ),
    ));
    s.push_str(&format!(
        "#v(0.6em)#{}\n",
        lit(if d.confirmed_by_counterparty {
            "Ikkinchi tomon ilovada yozuvni tasdiqlagan."
        } else {
            "Ikkinchi tomon tasdig'i: hali yo'q."
        })
    ));
    s.push_str(&format!(
        "#v(1fr)\n#text(size: 8pt, fill: luma(90))[#{} #{}]\n",
        lit(&d.legal_note),
        lit(&d.disclaimer)
    ));
    s
}

/// Tilxatni PDF qiladi.
///
/// # Errors
/// Imzo PNG emas/juda katta bo'lsa yoki shablon/eksport xatosi.
pub fn loan_receipt(d: &LoanReceiptDoc, sig: &ReceiptSignatures) -> Result<Vec<u8>, PdfError> {
    let mut files: Vec<(&str, Vec<u8>)> = Vec::new();
    if let Some(b) = &sig.lender_png {
        check_png(b)?;
        files.push(("sig-lender.png", b.clone()));
    }
    if let Some(b) = &sig.borrower_png {
        check_png(b)?;
        files.push(("sig-borrower.png", b.clone()));
    }
    render_pdf_with_files(&receipt_markup(d, sig), &files)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn sample() -> LoanReceiptDoc {
        LoanReceiptDoc {
            lender: "Karim aka".into(),
            borrower: "Anvar".into(),
            amount: "3 000 000 so'm".into(),
            given_on: "2026-10-07".into(),
            due_on: Some("2027-01-07".into()),
            reason: Some("ro'zg'or".into()),
            schedule: vec![
                ("2026-11-07".into(), "1 000 000 so'm".into()),
                ("2026-12-07".into(), "1 000 000 so'm".into()),
                ("2027-01-07".into(), "1 000 000 so'm".into()),
            ],
            markup_note: None,
            witnesses: vec!["Dilshod".into(), "Sanjar".into()],
            confirmed_by_counterparty: false,
            legal_note:
                "Bu hujjat shaxsiy hisob uchun yozuv; yuridik kuchi haqida va'da berilmaydi.".into(),
            disclaimer: "Ta'limiy material. Fatvo yoki moliyaviy maslahat emas.".into(),
        }
    }

    /// 1x1 shaffof PNG.
    fn tiny_png() -> Vec<u8> {
        vec![
            0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A, 0x00, 0x00, 0x00, 0x0D, 0x49, 0x48,
            0x44, 0x52, 0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01, 0x08, 0x06, 0x00, 0x00,
            0x00, 0x1F, 0x15, 0xC4, 0x89, 0x00, 0x00, 0x00, 0x0B, 0x49, 0x44, 0x41, 0x54, 0x78,
            0x9C, 0x63, 0x60, 0x00, 0x02, 0x00, 0x00, 0x05, 0x00, 0x01, 0x7A, 0x5E, 0xAB, 0x3F,
            0x00, 0x00, 0x00, 0x00, 0x49, 0x45, 0x4E, 0x44, 0xAE, 0x42, 0x60, 0x82,
        ]
    }

    fn text_of(pdf: &[u8]) -> String {
        let raw = pdf_extract::extract_text_from_mem(pdf).unwrap();
        raw.split_whitespace().collect::<Vec<_>>().join(" ")
    }

    /// Qabul mezoni (D9): tilxat PDF matni snapshot bilan qotirilgan; ʻ/ʼ belgilari saqlanadi.
    #[test]
    fn receipt_text_snapshot_keeps_uzbek_letters() {
        let mut d = sample();
        d.lender = "O\u{2bb}ktam g\u{2bb}ofur".into();
        d.witnesses = vec!["Dilshod".into()];
        let pdf = loan_receipt(&d, &ReceiptSignatures::default()).unwrap();
        let t = text_of(&pdf);
        assert!(t.contains("O\u{2bb}ktam g\u{2bb}ofur"), "{t}");
        insta::assert_snapshot!("loan_receipt_text", t);
    }

    #[test]
    fn markup_warning_replaces_interest_free_statement() {
        let mut d = sample();
        d.markup_note = Some("Diqqat: jadval jami asosiy summadan ko'p (ustama bor).".into());
        let t = text_of(&loan_receipt(&d, &ReceiptSignatures::default()).unwrap());
        assert!(t.contains("ustama bor"));
        assert!(!t.contains("qarzi hasana"));
    }

    #[test]
    fn at_least_two_witness_lines_even_without_names() {
        let mut d = sample();
        d.witnesses.clear();
        let t = text_of(&loan_receipt(&d, &ReceiptSignatures::default()).unwrap());
        assert!(t.contains("Guvoh 1") && t.contains("Guvoh 2"));
    }

    #[test]
    fn drawn_signatures_are_embedded_and_bad_images_rejected() {
        let d = sample();
        let blank = loan_receipt(&d, &ReceiptSignatures::default()).unwrap();
        let signed = loan_receipt(
            &d,
            &ReceiptSignatures {
                lender_png: Some(tiny_png()),
                borrower_png: Some(tiny_png()),
            },
        )
        .unwrap();
        assert!(signed.len() > blank.len(), "rasm PDF'ga qo'shilmadi");
        let bad = ReceiptSignatures {
            lender_png: Some(b"not a png".to_vec()),
            borrower_png: None,
        };
        assert!(loan_receipt(&d, &bad).is_err());
        let huge = ReceiptSignatures {
            lender_png: Some([PNG_MAGIC, &vec![0; MAX_SIGNATURE_BYTES]].concat()),
            borrower_png: None,
        };
        assert!(loan_receipt(&d, &huge).is_err());
    }

    #[test]
    fn user_text_cannot_inject_markup() {
        let mut d = sample();
        d.borrower = "#panic(\"x\") $ * _ \"); #read(\"/etc/passwd\")".into();
        d.witnesses = vec!["`raw` <label> @ref".into()];
        assert!(loan_receipt(&d, &ReceiptSignatures::default()).is_ok());
    }
}
