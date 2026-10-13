//! 6-qonun: umumiy kelishuv hujjati (SPEC 2F.2): 9 savol bo'limlari oddiy tilda, tasdiq bloklari bilan.
//!
//! Hujjat «ta'limiy material» — yuridik kuchi haqida va'da berilmaydi. Foydalanuvchi matnlari typst string
//! literal sifatida qo'yiladi (markup injection yo'q). Shablon tasdiqlanmagan bo'lsa, servis qatlamida
//! `templates_releasable` bilan bloklanadi (SPEC 8, OPEN_QUESTIONS 65).

use crate::{minutes::lit, render_pdf_with_files, PdfError};

/// PDF uchun tayyor ma'lumot: barcha sanalar, summalar va foizlar satr ko'rinishida (servis formatlaydi).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct AgreementPdfDoc {
    pub title: String,
    /// «Sheriklik (mudaraba)», «Qarz tilxati» ...
    pub kind: String,
    pub version: u32,
    /// «Qoralama» | «Imzolangan» | «Faol» | «Yopilgan».
    pub status: String,
    pub effective_from: String,
    /// (ism, rol)
    pub parties: Vec<(String, String)>,
    /// Hissa qatorlari: «Anvar — Pul: 300 000 000 so'm».
    pub contributions: Vec<String>,
    /// (vazifa, mas'ul tomon, bajarilmasa)
    pub duties: Vec<(String, String, String)>,
    /// Foyda ulushlari: «Anvar — 50%».
    pub profit: Vec<String>,
    pub loss: String,
    /// (pul joyi va hisob yurituvchi, ko'rik davriyligi)
    pub custody: Option<(String, String)>,
    pub exit: String,
    /// Hakam ismi; `None` — tegishli emas.
    pub arbiter: Option<String>,
    /// «12 oy; yangilash sanasi: 2027-10-01».
    pub term: String,
    pub witnesses: Vec<String>,
    /// (kim, tasdiq sanasi — imzolanmagan bo'lsa `None`)
    pub signatures: Vec<(String, Option<String>)>,
    pub legal_note: String,
    pub disclaimer: String,
}

fn text(s: &str) -> String {
    format!("[#{}]", lit(s))
}

fn section(title: &str) -> String {
    format!("== #{}\n", lit(title))
}

fn table(rows: &[Vec<String>]) -> String {
    let cells: Vec<String> = rows.iter().flatten().map(|c| text(c)).collect();
    format!(
        "#table(columns: (auto, 1fr), stroke: 0.4pt + luma(160), inset: 5pt,\n  {}\n)\n",
        cells.join(",\n  ")
    )
}

fn bullets(items: &[String]) -> String {
    items
        .iter()
        .map(|i| format!("- #{}\n", lit(i)))
        .collect::<String>()
}

/// Typst manbasi (snapshot testi shuni va matnni solishtiradi).
#[must_use]
pub fn agreement_markup(d: &AgreementPdfDoc) -> String {
    let mut s = String::new();
    s.push_str(
        "#set page(paper: \"a4\", margin: (x: 2cm, y: 2cm))\n\
         #set text(font: \"DejaVu Sans\", size: 10pt, lang: \"uz\")\n\
         #set par(justify: false, leading: 0.6em)\n",
    );
    s.push_str(&format!(
        "#align(center)[#text(size: 16pt, weight: \"bold\")[#{}]]\n#v(0.4em)\n#align(center)[#text(size: 9pt)[#{}]]\n#v(0.8em)\n",
        lit(&d.title),
        lit("Kelishuv hujjati — qoralama holatida bo'lishi mumkin")
    ));
    s.push_str(&table(&[
        vec!["Turi".to_owned(), d.kind.clone()],
        vec!["Versiya".to_owned(), format!("{}-versiya", d.version)],
        vec!["Holat".to_owned(), d.status.clone()],
        vec!["Kuchga kirish sanasi".to_owned(), d.effective_from.clone()],
    ]));
    s.push_str(&section("1. Tomonlar"));
    s.push_str(&table(
        &d.parties
            .iter()
            .map(|(n, r)| vec![n.clone(), r.clone()])
            .collect::<Vec<_>>(),
    ));
    s.push_str(&section("2. Kim nima qo'shadi"));
    s.push_str(&bullets(&d.contributions));
    s.push_str(&section("3. Kim nima qiladi"));
    for (task, owner, if_not_done) in &d.duties {
        s.push_str(&format!(
            "- #{} — mas'ul: #{}. Bajarilmasa: #{}\n",
            lit(task),
            lit(owner),
            lit(if_not_done)
        ));
    }
    s.push_str(&section("4. Foyda qanday bo'linadi"));
    s.push_str(&bullets(&d.profit));
    s.push_str(&section("5. Zarar bo'lsa"));
    s.push_str(&format!("#{}\n", lit(&d.loss)));
    s.push_str(&section("6. Pul va hisob"));
    match &d.custody {
        Some((place, every)) => {
            s.push_str(&format!("#{}\n\n", lit(place)));
            s.push_str(&format!("Ko'rik davriyligi: #{}\n", lit(every)));
        }
        None => s.push_str(&format!("#{}\n", lit("Kelishilmagan"))),
    }
    s.push_str(&section("7. Qanday ajralib chiqiladi"));
    s.push_str(&format!("#{}\n", lit(&d.exit)));
    s.push_str(&section("8. Kelisha olmasak, kim hakam"));
    match &d.arbiter {
        Some(name) => s.push_str(&format!("#{}\n", lit(name))),
        None => s.push_str(&format!("#{}\n", lit("Hakam kerak emas"))),
    }
    s.push_str(&section("9. Qachon yangilanadi"));
    s.push_str(&format!("#{}\n", lit(&d.term)));
    s.push_str(&section("Guvohlar"));
    s.push_str(&bullets(&d.witnesses));
    s.push_str(&section("Tasdiqlar"));
    for (who, when) in &d.signatures {
        let mark = when.as_ref().map_or_else(
            || "imzo kutilmoqda".to_owned(),
            |w| format!("tasdiqlangan: {w}"),
        );
        s.push_str(&format!("- #{} — #{}\n", lit(who), lit(&mark)));
    }
    s.push_str(&format!(
        "\n#v(1em)\n#text(size: 8pt)[#{}]\n#text(size: 8pt)[#{}]\n",
        lit(&d.legal_note),
        lit(&d.disclaimer)
    ));
    s
}

/// Kelishuv PDF'i.
///
/// # Errors
/// Typst kompilyatsiya xatosi.
pub fn agreement_pdf(d: &AgreementPdfDoc) -> Result<Vec<u8>, PdfError> {
    render_pdf_with_files(&agreement_markup(d), &[])
}

#[cfg(test)]
mod tests {
    use super::*;

    fn sample() -> AgreementPdfDoc {
        AgreementPdfDoc {
            title: "Yetkazib berish musharakasi".into(),
            kind: "Musharaka (ikkala tomon kapital kiritadi)".into(),
            version: 2,
            status: "Imzolangan".into(),
            effective_from: "2026-10-01".into(),
            parties: vec![
                ("Anvar".into(), "Sherik".into()),
                ("Dilshod".into(), "Sherik".into()),
            ],
            contributions: vec![
                "Anvar — Pul: 300 000 000 so'm".into(),
                "Dilshod — Mehnat (ish)".into(),
            ],
            duties: vec![(
                "Yetkazib berish va hisobot".into(),
                "Dilshod".into(),
                "1 kun ichida xabar beradi va o'rnini topadi".into(),
            )],
            profit: vec!["Anvar — 50%".into(), "Dilshod — 50%".into()],
            loss: "Zarar har bir tomon kiritgan kapitaliga mutanosib taqsimlanadi.".into(),
            custody: Some(("Anvar hisobi, Dilshod ko'chirma oladi".into(), "har oy".into())),
            exit: "30 kun oldin xabar; mol-mulk teng bo'linadi".into(),
            arbiter: Some("Usta Olim".into()),
            term: "12 oy; yangilash sanasi: 2027-10-01".into(),
            witnesses: vec!["Karim aka".into()],
            signatures: vec![
                ("Anvar".into(), Some("2026-10-02".into())),
                ("Dilshod".into(), Some("2026-10-02".into())),
                ("Usta Olim".into(), None),
            ],
            legal_note: "Shablon yurist va ulamo tasdig'idan o'tmagan: yuridik kuchi va islomiy muvofiqligi haqida va'da berilmaydi.".into(),
            disclaimer: "Ta'limiy material. Fatvo yoki moliyaviy maslahat emas.".into(),
        }
    }

    fn text_of(pdf: &[u8]) -> String {
        let raw = pdf_extract::extract_text_from_mem(pdf).unwrap();
        raw.split_whitespace().collect::<Vec<_>>().join(" ")
    }

    /// D8A qabul mezoni: kelishuv PDF matni snapshot bilan qotirilgan; o'zbekcha harflar saqlanadi.
    #[test]
    fn agreement_text_snapshot_keeps_nine_sections_and_uzbek_letters() {
        let mut d = sample();
        d.parties[0].0 = "O\u{2bb}ktam g\u{2bb}ofur".into();
        let pdf = agreement_pdf(&d).unwrap();
        assert!(pdf.starts_with(b"%PDF"));
        let t = text_of(&pdf);
        for section in [
            "1. Tomonlar",
            "3. Kim nima qiladi",
            "8. Kelisha olmasak",
            "9. Qachon yangilanadi",
        ] {
            assert!(t.contains(section), "{section} yo'q: {t}");
        }
        assert!(t.contains("O\u{2bb}ktam g\u{2bb}ofur"), "{t}");
        insta::assert_snapshot!("agreement_text", t);
    }

    /// Foydalanuvchi matni markup emas, matn sifatida chiqadi (kod sifatida bajarilmaydi).
    #[test]
    fn user_text_is_printed_not_executed() {
        let mut d = sample();
        d.exit = "#panic() \"x\"".into();
        let t = text_of(&agreement_pdf(&d).unwrap());
        assert!(t.contains("#panic()"), "{t}");
    }

    #[test]
    fn unsigned_arbiter_is_marked_as_pending() {
        let t = text_of(&agreement_pdf(&sample()).unwrap());
        assert!(t.contains("imzo kutilmoqda"), "{t}");
    }
}
