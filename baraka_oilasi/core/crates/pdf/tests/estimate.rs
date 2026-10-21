#![allow(clippy::unwrap_used, clippy::expect_used, clippy::panic)]
//! Marosim smetasi (U10): lokallar, determinizm, in'eksiyaga chidamlilik, PNG snapshot.

use baraka_pdf::{
    CeremonyEstimate, EstimateAgreement, EstimateAnswer, EstimateLine, EstimateTotal, PdfEngine,
    PdfLocale,
};
use chrono::NaiveDate;
use sha2::{Digest, Sha256};

fn today() -> NaiveDate {
    NaiveDate::from_ymd_opt(2026, 10, 15).unwrap()
}

fn line(title: &str, kind: &str, amount: &str, source: &str) -> EstimateLine {
    EstimateLine {
        title: title.into(),
        kind: kind.into(),
        unit: "250 000 soʻm".into(),
        guests: "150".into(),
        amount: amount.into(),
        source: source.into(),
    }
}

fn estimate(locale: PdfLocale) -> CeremonyEstimate {
    CeremonyEstimate {
        ident: "cer-0192a000".into(),
        locale,
        kind: "TOY".into(),
        title: "Sanjarning toʻyi".into(),
        date: Some("20.05.2027".into()),
        status: "DISCUSSED".into(),
        scenario: "Oʻrtacha, 150 kishi".into(),
        guests: "150".into(),
        lines: vec![
            line(
                "Osh va dasturxon",
                "PER_GUEST",
                "37 500 000 soʻm",
                "SAVINGS",
            ),
            line(
                "Sarpo, kiyim-kechak",
                "ONE_OFF",
                "10 000 000 soʻm",
                "FAMILY",
            ),
            line("Xonanda", "ONE_OFF", "5 000 000 soʻm", "DEBT"),
        ],
        totals: ["SAVINGS", "FAMILY", "EXPECTED_GIFTS", "DEBT"]
            .iter()
            .zip([
                "37 500 000 soʻm",
                "10 000 000 soʻm",
                "0 soʻm",
                "5 000 000 soʻm",
            ])
            .map(|(s, a)| EstimateTotal {
                source: (*s).into(),
                amount: a.into(),
            })
            .collect(),
        total: "52 500 000 soʻm".into(),
        payoff_months: Some("3".into()),
        payoff_date: Some("01.07.2027".into()),
        answers: vec![EstimateAnswer {
            key: "guests".into(),
            note: "200 dan 150 ga tushirdik. Ўзбекча: ў қ ғ ҳ".into(),
        }],
        agreed: vec![EstimateAgreement {
            name: "Karim".into(),
            date: "15.10.2026".into(),
        }],
        adults: vec!["Karim".into(), "Gulnora".into()],
    }
}

#[test]
fn estimate_renders_in_all_locales() {
    let engine = PdfEngine::new();
    let dir =
        std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("../../../target/pdf-snapshots");
    std::fs::create_dir_all(&dir).unwrap();
    for (locale, name) in [
        (PdfLocale::Uz, "uz"),
        (PdfLocale::UzCyrl, "uz-Cyrl"),
        (PdfLocale::Ru, "ru"),
    ] {
        let r = estimate(locale).render(&engine, today()).unwrap();
        assert!(r.warnings.is_empty(), "{name}: {:?}", r.warnings);
        assert!(r.pdf.starts_with(b"%PDF-"));
        let pixmap = typst_render::render(
            &r.document.pages()[0],
            &typst_render::RenderOptions::default(),
        );
        std::fs::write(
            dir.join(format!("ceremony_estimate-{name}.png")),
            pixmap.encode_png().unwrap(),
        )
        .unwrap();
    }
    let a = estimate(PdfLocale::Uz)
        .render(&engine, today())
        .unwrap()
        .pdf;
    let b = estimate(PdfLocale::Uz)
        .render(&PdfEngine::new(), today())
        .unwrap()
        .pdf;
    assert_eq!(Sha256::digest(&a), Sha256::digest(&b));
}

#[test]
fn estimate_user_text_is_not_code() {
    let mut e = estimate(PdfLocale::Uz);
    e.title = "#panic(\"x\") #read(\"/etc/hostname\")".into();
    e.lines[0].title = "$x^2$ *qalin* <lbl> @ref ]".into();
    e.answers[0].note = "#import \"/etc/passwd\"".into();
    let r = e.render(&PdfEngine::new(), today()).unwrap();
    assert!(r.warnings.is_empty(), "{:?}", r.warnings);
}
